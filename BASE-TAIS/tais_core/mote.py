"""
tais_core.mote
==============

V6 UniversalMote — the universal cognitive agent.

Composes:
    RealityGraph   — internal world model (built from observations)
    MoteMemory     — episodic + pattern + symbolic + prediction
    SpeechOrgan    — emergent communication
    WorldInterface — the domain it is embedded in

Lifecycle per tick:
    observe → think → predict → decide → act → learn → maybe_speak
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple

from .memory import MoteMemory
from .reality import (
    Consequence,
    Entity,
    GraphPattern,
    RealityGraph,
    Relation,
    Transformation,
    WorldInterface,
)
from .speech import SpeechOrgan


class UniversalMote:
    def __init__(
        self,
        mote_id: int = 0,
        world: Optional[WorldInterface] = None,
        memory: Optional[MoteMemory] = None,
        speech: Optional[SpeechOrgan] = None,
        energy: float = 100.0,
    ):
        self.mote_id = mote_id
        self.world = world
        self.memory = memory or MoteMemory(episodic_capacity=64, pattern_capacity=32)
        self.speech = speech or SpeechOrgan(mote_id)
        self.model: RealityGraph = RealityGraph("unknown", "mote_model")
        self.state: Dict[str, Any] = {
            "energy": energy,
            "fitness": 0.0,
            "position": [0, 0],
            "score": 0,
        }
        self.tick: int = 0
        self.current_domain: str = "unknown"
        self._last_consequence: Optional[Consequence] = None
        self._last_utterance: Any = None
        self._last_action: Optional[Transformation] = None
        self._exploration_count: int = 0
        self._exploitation_count: int = 0

    # ─── LIFE CYCLE ──────────────────────────────────────────────────────────

    def step(self, world: Optional[WorldInterface] = None) -> Dict[str, Any]:
        if world is not None:
            self.world = world
        if self.world is None:
            raise RuntimeError("UniversalMote needs a world to step in")

        self.tick += 1
        self.current_domain = self.world.domain_name

        observation = self.observe()
        self.think(observation)
        candidate_actions = self.world.valid_actions(self.model, self.state)
        chosen = self.decide(candidate_actions)
        g_next, consequence = self.act(chosen)
        self.learn(chosen, consequence)
        self.maybe_speak(consequence)

        self.state["energy"] = max(0.0, self.state.get("energy", 100) - 0.2)
        self.state["fitness"] = self.world.evaluate(g_next, self.state)

        return {
            "tick": self.tick,
            "domain": self.current_domain,
            "action": chosen.name if chosen else None,
            "reward": consequence.reward,
            "penalty": consequence.penalty,
            "valence": consequence.valence,
            "energy": self.state["energy"],
            "fitness": self.state["fitness"],
            "explored": self._last_action is not None and chosen.name not in [
                e.transformation.name for e in list(self.memory.episodic.episodes)[-5:]
            ] if self._last_action else True,
        }

    def run(self, steps: int = 10) -> List[Dict[str, Any]]:
        return [self.step() for _ in range(steps)]

    # ─── CORE LOOP STEPS ─────────────────────────────────────────────────────

    def observe(self) -> RealityGraph:
        world_graph = getattr(self.world, "graph", self.model)
        pos = self.state.get("position")
        return self.world.observe(world_graph, pos)

    def think(self, observation: RealityGraph) -> RealityGraph:
        for ent in observation.entities():
            if not self.model.get_entity(ent.id):
                self.model.add_entity(Entity(ent.id, ent.etype, dict(ent.properties)))
            else:
                self.model.update_entity(ent.id, **ent.properties)
        for rel in observation.relations():
            existing = self.model.get_relation(rel.source, rel.rtype, rel.target)
            if existing is None:
                try:
                    self.model.add_relation(Relation(rel.source, rel.rtype, rel.target, dict(rel.properties), rel.directed))
                except ValueError:
                    pass
        return self.model

    def predict(self, transformation: Transformation) -> float:
        return self.memory.predict_action(transformation, self.model)

    def decide(self, candidates: List[Transformation]) -> Optional[Transformation]:
        if not candidates:
            return None

        if self.memory.should_explore(candidates, curiosity=0.3):
            self._exploration_count += 1
            chosen = random.choice(candidates)
            self._last_action = chosen
            return chosen

        best, best_val = None, float("-inf")
        for t in candidates:
            predicted = self.predict(t)
            historical = self.memory.episodic.action_value(t.name)
            risk = self.memory.episodic.action_risk(t.name)
            score = 0.6 * predicted + 0.4 * historical - 0.2 * risk
            if score > best_val:
                best, best_val = t, score

        self._exploitation_count += 1
        self._last_action = best
        return best

    def act(self, transformation: Transformation) -> Tuple[RealityGraph, Consequence]:
        g_next, consequence = self.world.act(self.model, transformation, self.state)
        self._last_consequence = consequence
        return g_next, consequence

    def learn(self, transformation: Transformation, consequence: Consequence):
        predicted = self.predict(transformation)
        self.memory.record_episode(
            state_before=self.model,
            transformation=transformation,
            consequence=consequence,
            predicted=predicted,
            domain=self.current_domain,
            tick=self.tick,
        )
        self.speech.update_from_consequence(consequence, self._last_utterance)

    def maybe_speak(self, consequence: Consequence) -> Any:
        if self.world is None:
            return None

        intent = consequence.valence
        if consequence.concept_signals:
            intent = max(consequence.concept_signals, key=consequence.concept_signals.get)

        neighbors = []
        neediest_id = None

        utt = self.speech.compose(
            intent=intent,
            neighbors=neighbors,
            mote_state=self.state,
            domain=self.current_domain,
            tick=self.tick,
            info_delta=abs(consequence.net) if consequence else 0.0,
        )
        self._last_utterance = utt
        return utt

    # ─── CROSS-DOMAIN ────────────────────────────────────────────────────────

    def transfer_to(self, target_world: WorldInterface) -> List[Tuple[str, float]]:
        fake_graph = RealityGraph(target_world.domain_name, "target_probe")
        concepts = target_world.concepts()
        for i, c in enumerate(concepts):
            fake_graph.add_entity(Entity(f"probe_{i}", "CONCEPT", {"name": c}))

        results = []
        for pattern, mapping in self.memory.transfer_patterns_to(fake_graph):
            results.append((pattern.name or "unknown", mapping.confidence))
        return results

    def report_understanding(self) -> bool:
        return self.memory.prediction.is_understanding(threshold=1.5)

    # ─── REPRODUCTION ────────────────────────────────────────────────────────

    def spawn_child(self, child_id: int) -> "UniversalMote":
        child_speech = self.speech.spawn_child(child_id)
        child_memory = MoteMemory(
            episodic_capacity=self.memory.episodic.capacity,
            pattern_capacity=self.memory.patterns.capacity,
        )
        return UniversalMote(
            mote_id=child_id,
            world=self.world,
            memory=child_memory,
            speech=child_speech,
            energy=self.state.get("energy", 100) * 0.5,
        )

    # ─── INTROSPECTION ───────────────────────────────────────────────────────

    def summary(self) -> Dict[str, Any]:
        return {
            "id": self.mote_id,
            "tick": self.tick,
            "domain": self.current_domain,
            "state": {
                "energy": round(self.state.get("energy", 0), 1),
                "fitness": round(self.state.get("fitness", 0), 3),
            },
            "memory": self.memory.summary(),
            "speech": {
                "times_spoke": self.speech.times_spoke,
                "semantic_success": self.speech.audit.semantic_success_rate(),
                "lexicon_size": len(self.speech.lexicon.snapshot()),
            },
            "policy": {
                "explorations": self._exploration_count,
                "exploitations": self._exploitation_count,
            },
        }
