from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple

from tais_core.reality import Consequence, RealityGraph, Transformation, WorldInterface


def graph_structural_key(graph: RealityGraph) -> str:
    ents = sorted(
        f"{e.etype}:{sorted((k, str(v)) for k, v in e.properties.items())}"
        for e in graph.entities()
    )
    rels = sorted(
        f"{r.rtype}:{r.source}->{r.target}:{sorted((k, str(v)) for k, v in r.properties.items())}"
        for r in graph.relations()
    )
    return f"E:{'|'.join(ents)}||R:{'|'.join(rels)}"


class TabularQAgent:
    name = "tabular_q"

    def __init__(self, seed: int = 0, alpha: float = 0.3, gamma: float = 0.9, epsilon: float = 0.2):
        self.rng = random.Random(seed)
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.q_table: Dict[Tuple[str, str], float] = {}
        self._prev_state: Optional[str] = None
        self._prev_action: Optional[str] = None

    def reset(self, seed: int = 0):
        self.rng = random.Random(seed)
        self.q_table.clear()
        self._prev_state = None
        self._prev_action = None

    def _q(self, state: str, action: str) -> float:
        return self.q_table.get((state, action), 0.0)

    def choose_action(
        self,
        world: WorldInterface,
        graph: RealityGraph,
        actions: List[Transformation],
        mote_state: Dict[str, Any],
        tick: int,
    ) -> Optional[Transformation]:
        if not actions:
            return None
        if self.rng.random() < self.epsilon:
            return self.rng.choice(actions)
        state = graph_structural_key(graph)
        best = max(actions, key=lambda a: self._q(state, a.name))
        return best

    def observe_outcome(
        self,
        world: WorldInterface,
        before: RealityGraph,
        action: Optional[Transformation],
        after: RealityGraph,
        consequence: Consequence,
        tick: int,
    ) -> None:
        if action is None:
            self._prev_state = None
            self._prev_action = None
            return
        prev_state = graph_structural_key(before)
        prev_action = action.name
        reward = consequence.net
        next_state = graph_structural_key(after)
        max_next = max(
            (self._q(next_state, a.name) for a in world.valid_actions(after, {})),
            default=0.0,
        )
        current_q = self._q(prev_state, prev_action)
        new_q = current_q + self.alpha * (reward + self.gamma * max_next - current_q)
        self.q_table[(prev_state, prev_action)] = new_q
        self._prev_state = next_state
        self._prev_action = None
