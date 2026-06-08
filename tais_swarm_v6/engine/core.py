"""
Core tick loop for TAIS Swarm V6.

Integrates world, motes, event bus, persistence, and plan execution.
"""

from __future__ import annotations

import math
import random
import time
from typing import Any, Dict, List, Optional, Tuple

from .config import SwarmConfig, CONFIG_PRESETS
from .world import WorldV6
from .events import EventBus, Event, EventType
from .persistence import PersistenceLayer, TickRecord
from ..agents.mote_v6 import MoteV6
from ..agents.speech_v6 import UtteranceV6, UtteranceV6Booklet


class SwarmV6:
    def __init__(self, config: Optional[SwarmConfig] = None, seed: Optional[int] = None):
        self.config = config or CONFIG_PRESETS["standard"]
        if seed is not None:
            d = self.config.to_dict()
            d["seed"] = seed
            self.config = SwarmConfig.from_dict(d)
        self.world = WorldV6(self.config.world)
        self.motes: List[MoteV6] = []
        self.event_bus = EventBus()
        self.persistence = PersistenceLayer(self.config.db_path)
        self.tick = 0
        self.booklet = UtteranceV6Booklet()
        self._mote_factory = MoteV6

        if self.config.seed is not None:
            random.seed(self.config.seed)

    def set_mote_factory(self, factory):
        self._mote_factory = factory

    def add_mote(self, mote: MoteV6):
        self.motes.append(mote)
        self.world.spatial.insert_agent(mote.id, mote.x, mote.y, mote)
        self.event_bus.emit(Event(
            type=EventType.MOTE_BORN,
            tick=self.tick,
            mote_id=mote.id,
            data={"x": mote.x, "y": mote.y, "parent_id": mote.parent_id},
        ))

    def initialize_population(self, count: int = 20):
        for _ in range(count):
            x = random.uniform(self.world.size * 0.2, self.world.size * 0.8)
            y = random.uniform(self.world.size * 0.2, self.world.size * 0.8)
            mote = self._mote_factory(x, y, self.config)
            self.add_mote(mote)

    def init_population(self, count: int = 20):
        self.initialize_population(count)

    def get_motes(self) -> List[MoteV6]:
        return self.motes

    def step(self):
        self.tick += 1
        self.event_bus.emit(Event(
            type=EventType.TICK_START, tick=self.tick, mote_id=None, data={"tick": self.tick}
        ))

        # Phase 1: World step (ecosystem + seasons)
        self.world.step()
        self.booklet.clear()

        # Phase 2: Plan execution (before utterances — drives behavior, not reaction)
        for mote in self.motes:
            if not mote.alive or mote.planner is None:
                continue
            plan_step = mote.planner.next_step()
            if plan_step is not None:
                self._execute_plan_step(mote, plan_step)

        # Phase 3: Mote step (sense, metabolize, derive intent, act)
        mote_results: Dict[int, dict] = {}
        for mote in self.motes:
            if not mote.alive:
                mote_results[mote.id] = {"status": "dead"}
                continue
            result = mote.step(self.world, self.tick)
            mote_results[mote.id] = result
            if result["status"] == "dead":
                self.event_bus.emit(Event(
                    type=EventType.MOTE_DEATH,
                    tick=self.tick,
                    mote_id=mote.id,
                    data={"reason": result.get("reason", "unknown"), "age": mote.age},
                ))
                self.world.spatial.remove_agent(mote.id)

        # Phase 4: Utterance generation
        for mote in self.motes:
            if not mote.alive:
                continue
            result = mote_results.get(mote.id, {})
            if result.get("status") == "alive":
                intent = result.get("intent", "EXPLORE")
                utt = mote.speak(intent, {}, self.tick)
                if utt is not None:
                    self.booklet.add(utt)
                    self.event_bus.emit(Event(
                        type=EventType.UTTERANCE,
                        tick=self.tick,
                        mote_id=mote.id,
                        data=utt.to_dict(),
                    ))

        # Phase 5: Hear utterances
        for mote in self.motes:
            if not mote.alive:
                continue
            nearby = self.booklet.for_mote(mote.id)
            mote.hear(nearby)

        # Phase 6: Reproduction
        self._handle_reproduction()

        # Phase 7: Update spatial index for all motes
        for mote in self.motes:
            if mote.alive:
                self.world.spatial.update_agent(mote.id, mote.x, mote.y, mote)

        # Phase 8: Periodic persistence
        if self.tick % self.config.snapshot_interval == 0:
            self._snapshot()

        self.event_bus.emit(Event(
            type=EventType.TICK_END, tick=self.tick, mote_id=None,
            data={"population": sum(1 for m in self.motes if m.alive), "total": len(self.motes)}
        ))

    def _execute_plan_step(self, mote: MoteV6, step):
        _ = step  # Plan step execution hook — future expansion
        pass

    def _handle_reproduction(self):
        new_motes: List[MoteV6] = []
        for mote in self.motes:
            if not mote.alive:
                continue
            if mote.state.can_reproduce(mote.thermo.cfg) and random.random() < 0.05:
                try:
                    child = mote.reproduce()
                    new_motes.append(child)
                    self.event_bus.emit(Event(
                        type=EventType.MOTE_REPRODUCE,
                        tick=self.tick,
                        mote_id=mote.id,
                        data={"child_id": child.id, "x": child.x, "y": child.y},
                    ))
                except ValueError:
                    pass
        for child in new_motes:
            self.add_mote(child)

    def _snapshot(self):
        population = sum(1 for m in self.motes if m.alive)
        if population == 0:
            return
        avg_energy = sum(m.state.energy for m in self.motes if m.alive) / population
        avg_hydration = sum(m.state.hydration for m in self.motes if m.alive) / population
        avg_toxicity = sum(m.state.toxicity for m in self.motes if m.alive) / population
        record = TickRecord(
            tick=self.tick,
            timestamp=time.time(),
            population=population,
            avg_energy=round(avg_energy, 2),
            avg_hydration=round(avg_hydration, 2),
            avg_toxicity=round(avg_toxicity, 2),
            season=self.world.ecosystem.season.name,
            utterance_count=len(self.booklet),
            comprehension_success=0,
            comprehension_trials=0,
            semantic_rate=0.0,
            utility_rate=0.0,
            common_tokens_json="{}",
        )
        self.persistence.log_tick(record)

    def run(self, ticks: int, progress_interval: int = 100):
        for i in range(ticks):
            self.step()
            if progress_interval > 0 and (i + 1) % progress_interval == 0:
                alive = sum(1 for m in self.motes if m.alive)
                print(f"Tick {self.tick}: {alive}/{len(self.motes)} alive, "
                      f"avg energy={sum(m.state.energy for m in self.motes if m.alive) / max(alive, 1):.1f}")

    def tick_step(self) -> dict:
        self.step()
        alive = sum(1 for m in self.motes if m.alive)
        population = alive
        avg_energy = sum(m.state.energy for m in self.motes if m.alive) / max(alive, 1) if alive else 0.0
        avg_hydration = sum(m.state.hydration for m in self.motes if m.alive) / max(alive, 1) if alive else 0.0
        avg_pred_acc = sum(m.metacog.get_confidence() for m in self.motes if m.alive and m.metacog is not None) / max(alive, 1) if alive else 0.0

        plans_created = sum(len(m.planner._plan_library) for m in self.motes if m.alive and m.planner is not None)
        births = 0
        deaths = 0
        for event in self.event_bus.get_history(tick_start=self.tick, mote_id=None):
            if event.type == EventType.MOTE_BORN:
                births += 1
            elif event.type == EventType.MOTE_DEATH:
                deaths += 1

        return {
            "tick": self.tick,
            "population": population,
            "avg_energy": round(avg_energy, 2),
            "avg_hydration": round(avg_hydration, 2),
            "avg_prediction_accuracy": round(avg_pred_acc, 3),
            "plans_created": plans_created,
            "plans_completed": 0,
            "plans_failed": 0,
            "births": births,
            "deaths": deaths,
            "predator_kills": 0,
        }

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "motes": [m.to_dict() for m in self.motes],
            "world": self.world.to_dict(),
            "config": self.config.to_dict(),
        }

    def close(self):
        self.persistence.close()
