"""
MoteV6 for TAIS Swarm V6.

Integration of:
- ThermodynamicState + ThermodynamicEngine (NO tick kwarg bug)
- TemporalMemory
- ReputationNetwork + GossipProtocol
- SpeechGenomeV6 + GrammarInnovator + UtteranceV6
- MetacognitiveEngine (prediction tracking, self-model)
- CausalReasoningEngine (Delta-P, counterfactuals)
- HierarchicalPlanner (backward chaining, plan library)
"""

from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional, Tuple

from ..engine.config import SwarmConfig
from ..engine.thermodynamics import ThermodynamicEngine, ThermodynamicState
from ..engine.world import WorldV6
from .memory_v6 import TemporalMemory
from .trust_v6 import ReputationNetwork, GossipProtocol
from .speech_v6 import (
    SpeechGenomeV6, GrammarInnovator, ChannelType,
    UtteranceV6, UtteranceV6Booklet,
)
from .metacognition import MetacognitiveEngine
from .causal import CausalReasoningEngine
from .planning import HierarchicalPlanner


_INTENT_TO_ACTION_TYPE = {
    "FOOD": "move",
    "WATER": "move",
    "EXPLORE": "move",
    "SOCIALIZE": "move",
    "REST": "listen",
}


class MoteV6:
    next_id = 0

    def __init__(self, x: float, y: float, config: SwarmConfig, mote_id: Optional[int] = None):
        if mote_id is not None:
            self.id = mote_id
            MoteV6.next_id = max(MoteV6.next_id, mote_id + 1)
        else:
            self.id = MoteV6.next_id
            MoteV6.next_id += 1

        self.x = x
        self.y = y
        self.age = 0
        self.alive = True
        self.parent_id = -1

        self.thermo = ThermodynamicEngine(config.thermo, shout_cost_mult=config.comm.shout_cost_mult)
        self.state = ThermodynamicState(
            energy=config.thermo.initial_energy,
            hydration=config.thermo.initial_hydration,
            toxicity=0.0,
            heat=20.0,
        )

        self.memory = TemporalMemory(config.memory)
        self.reputation = ReputationNetwork(config.comm)
        self.gossip = GossipProtocol(config.comm)
        self.genome = SpeechGenomeV6()
        self.grammar = GrammarInnovator(config.comm)
        self.vocab: List[str] = []
        self.inbox: List[UtteranceV6] = []

        self.metacog = MetacognitiveEngine()
        self.causal = CausalReasoningEngine()
        self.planner = HierarchicalPlanner()

        self._in_shelter: bool = False
        self._last_utterance: Optional[UtteranceV6] = None
        self._prediction_history: List[Tuple[int, str, Any, Any, bool]] = []

    def sense(self, world: WorldV6) -> dict:
        sensed = world.sense(self.x, self.y, radius=2.0)
        self._in_shelter = world.is_in_shelter(self.x, self.y)
        return sensed

    def derive_intent(self, sensed: dict, tick: int) -> str:
        strategies = ["forage_food", "forage_water", "explore", "socialize", "rest"]

        if not self.state.is_alive(self.thermo.cfg):
            return "REST"

        urgency = 0.5
        if self.state.energy < 30:
            urgency = 0.8
        elif self.state.hydration < 20:
            urgency = 0.7
        if self.state.heat > 50 or self.state.toxicity > 30:
            urgency = 0.6

        if self.metacog is not None:
            strategy = self.metacog.select_strategy(tick, strategies, urgency)
        else:
            strategy = random.choice(strategies)

        if strategy == "forage_food":
            return "FOOD"
        elif strategy == "forage_water":
            return "WATER"
        elif strategy == "explore":
            return "EXPLORE"
        elif strategy == "socialize":
            return "SOCIALIZE"
        elif strategy == "rest":
            return "REST"

        if self.state.energy < 40:
            return "FOOD"
        elif self.state.hydration < 30:
            return "WATER"
        elif self.state.heat > 50 or self.state.toxicity > 30:
            return "REST"
        return "EXPLORE"

    def speak(self, intent: str, sensed: dict, tick: int) -> Optional[UtteranceV6]:
        if self.state.energy < 5:
            return None
        if self.state.energy < 15:
            channel = ChannelType.WHISPER
        else:
            channel = self.genome.select_channel(self.state.energy)

        rule = self.genome.select_rule(urgency=0.5)
        tokens = self._compose_tokens(intent, rule.pattern)

        utt = UtteranceV6(
            tokens=tokens,
            speaker_id=self.id,
            target_id=None,
            intended_concept=intent,
            position=(self.x, self.y),
            channel=channel,
            fitness=self.state.vitality,
            energy=self.state.energy,
            tick=tick,
            confidence=self.metacog.get_confidence() if self.metacog is not None else 0.5,
        )
        self._last_utterance = utt
        return utt

    def _compose_tokens(self, intent: str, pattern: str) -> List[str]:
        slot_map = {
            "concept": intent,
            "direction": random.choice(["NORTH", "SOUTH", "EAST", "WEST"]),
            "distance": random.choice(["NEAR", "FAR"]),
            "risk": "DANGER" if self.state.energy < 25 else "SAFE",
            "landmark": "HERE",
            "urgency": "URGENT" if self.state.energy < 20 else "NORMAL",
        }
        slots = pattern.split("-")
        tokens = []
        for slot in slots[:self.genome.max_len]:
            concept = slot_map.get(slot)
            if concept:
                token = self._token_for_concept(concept)
                if token and (not tokens or tokens[-1] != token):
                    tokens.append(token)
        return tokens if tokens else [self._token_for_concept(intent) or "ka"]

    def _token_for_concept(self, concept: str) -> Optional[str]:
        if not self.vocab:
            return None
        for tok in self.vocab:
            if tok[0] == concept[0]:
                return tok
        return random.choice(self.vocab) if self.vocab else None

    def hear(self, utterances: List[UtteranceV6]):
        for utt in utterances:
            if utt.speaker_id == self.id:
                continue
            self.inbox.append(utt)

    def act_on_inbox(self, sensed: dict, tick: int):
        for utt in self.inbox:
            if self.causal is not None:
                self.causal.record_no_action(tick, utt.intended_concept, True)
            if self.metacog is not None:
                self.metacog.record_outcome(
                    "listen",
                    prediction={"speaker": utt.speaker_id, "concept": utt.intended_concept},
                    outcome={"heard": True},
                    correct=True,
                    tick=tick,
                )
        self.inbox.clear()

    def update_from_outcome(self, action: str, sensed_before: dict, sensed_after: dict, tick: int):
        positive = False
        if action == "forage_food":
            positive = sensed_after.get("food", 0) < sensed_before.get("food", 0)
        elif action == "forage_water":
            positive = sensed_after.get("water", 0) < sensed_before.get("water", 0)
        elif action in ("move_north", "move_south", "move_east", "move_west"):
            food_gain = sensed_after.get("food", 0) - sensed_before.get("food", 0)
            positive = food_gain > 0
        elif action == "explore":
            positive = sensed_after.get("food", 0) > sensed_before.get("food", 0)

        if self.causal is not None and action != "NO_ACTION":
            self.causal.record_action(tick, action, action, positive)

        if self.metacog is not None:
            self.metacog.record_outcome(
                action,
                prediction={"expected_energy_change": sensed_after.get("food", 0) - sensed_before.get("food", 0)},
                outcome={"energy_change": 0},
                correct=positive,
                tick=tick,
            )

    def _act(self, intent: str, sensed: dict) -> Tuple[str, float, float]:
        dd = 1.0
        if intent == "FOOD":
            dx = random.uniform(-dd, dd)
            dy = random.uniform(-dd, dd)
            return ("forage_food", dx, dy)
        elif intent == "WATER":
            dx = random.uniform(-dd, dd)
            dy = random.uniform(-dd, dd)
            return ("forage_water", dx, dy)
        elif intent == "EXPLORE":
            nx, ny = self.explore()
            dx = max(-dd, min(dd, nx - self.x))
            dy = max(-dd, min(dd, ny - self.y))
            return ("explore", dx, dy)
        elif intent == "SOCIALIZE":
            dx = random.uniform(-dd, dd)
            dy = random.uniform(-dd, dd)
            return ("socialize", dx, dy)
        else:
            return ("rest", 0.0, 0.0)

    def explore(self) -> Tuple[float, float]:
        tendency = self.metacog.self_model.exploration_tendency if self.metacog is not None else 0.3
        if random.random() < tendency:
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(0.5, 2.0)
            return (self.x + math.cos(angle) * dist, self.y + math.sin(angle) * dist)
        return (self.x + random.uniform(-1, 1), self.y + random.uniform(-1, 1))

    def reproduce(self) -> "MoteV6":
        if not self.state.can_reproduce(self.thermo.cfg):
            raise ValueError("Cannot reproduce")

        parent_state, child_state = self.thermo.reproduce(self.state)
        self.state = parent_state

        child = MoteV6.__new__(MoteV6)
        child.id = MoteV6.next_id
        MoteV6.next_id += 1
        child.parent_id = self.id
        child.x = self.x + random.uniform(-1, 1)
        child.y = self.y + random.uniform(-1, 1)
        child.age = 0
        child.alive = True

        child.thermo = self.thermo
        child.state = child_state
        child.memory = TemporalMemory(self.memory.cfg)
        child.reputation = ReputationNetwork(self.reputation.cfg)
        child.gossip = GossipProtocol(self.gossip.cfg)
        child.genome = self.genome.mutate()
        child.grammar = self.grammar
        child.vocab = list(self.vocab)
        child.inbox = []

        if self.metacog is not None:
            child.metacog = MetacognitiveEngine()
            child.metacog.self_model.learning_speed = self.metacog.self_model.learning_speed
            child.metacog.self_model.exploration_tendency = self.metacog.self_model.exploration_tendency
            child.metacog.self_model.memory_reliability = self.metacog.self_model.memory_reliability
        else:
            child.metacog = None

        if self.planner is not None:
            child.planner = HierarchicalPlanner()
            for goal, plans in self.planner._plan_library.items():
                child.planner._plan_library[goal] = list(plans)
        else:
            child.planner = None

        if self.causal is not None:
            child.causal = CausalReasoningEngine()
            for out, link in self.causal._links.items():
                if link.confidence > 0.3:
                    child.causal._links[out] = link
        else:
            child.causal = None

        child._in_shelter = False
        child._last_utterance = None
        child._prediction_history = []

        return child

    def step(self, world: WorldV6, tick: int) -> dict:
        if not self.alive:
            return {"status": "dead"}

        sensed = self.sense(world)

        # BUG FIX: metabolize does NOT accept tick parameter
        self.state = self.thermo.metabolize(self.state, sensed, in_shelter=self._in_shelter)

        if not self.state.is_alive(self.thermo.cfg):
            self.alive = False
            return {"status": "dead", "reason": "energy_depleted"}

        intent = self.derive_intent(sensed, tick)
        self.act_on_inbox(sensed, tick)

        action, dx, dy = self._act(intent, sensed)

        # Apply thermodynamic cost for the action
        action_type = _INTENT_TO_ACTION_TYPE.get(intent, "move")
        self.state = self.thermo.apply_action(self.state, action_type)

        if dx != 0 or dy != 0:
            self.x += dx
            self.y += dy
            self.x = max(0, min(self.x, world.size))
            self.y = max(0, min(self.y, world.size))

        # Deplete resources if foraging
        if intent == "FOOD":
            world.deplete_resource(self.x, self.y, "food", 1.0)
        elif intent == "WATER":
            world.deplete_resource(self.x, self.y, "water", 1.0)

        sensed_after = world.sense(self.x, self.y, radius=2.0)
        self.update_from_outcome(action, sensed, sensed_after, tick)

        self.age += 1

        return {
            "status": "alive",
            "intent": intent,
            "action": action,
            "x": round(self.x, 3),
            "y": round(self.y, 3),
            "energy": round(self.state.energy, 3),
            "hydration": round(self.state.hydration, 3),
            "heat": round(self.state.heat, 3),
            "toxicity": round(self.state.toxicity, 3),
        }

    def to_dict(self) -> dict:
        last_utt = self._last_utterance
        return {
            "id": self.id,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "age": self.age,
            "alive": self.alive,
            "parent_id": self.parent_id,
            "energy": round(self.state.energy, 2),
            "state": {
                "energy": round(self.state.energy, 2),
                "hydration": round(self.state.hydration, 2),
                "toxicity": round(self.state.toxicity, 2),
                "heat": round(self.state.heat, 2),
                "vitality": round(self.state.vitality, 2),
            },
            "in_shelter": self._in_shelter,
            "last_utterance": " ".join(last_utt.tokens) if last_utt else None,
            "last_utterance_tick": last_utt.tick if last_utt else None,
            "metacognition": self.metacog.to_dict(),
            "causal": self.causal.to_dict(),
            "planner": self.planner.to_dict(),
            "trust_vector": dict(self.reputation.vectors),
            "genome": {
                "max_len": self.genome.max_len,
                "rule_count": len(self.genome.rules),
            },
            "lexicon": {tok: {"token": tok, "concept": "UNKNOWN", "confidence": 0.0, "grounded_count": 0} for tok in self.vocab},
        }
