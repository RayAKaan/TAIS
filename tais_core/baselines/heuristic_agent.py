from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from tais_core.reality import Consequence, RealityGraph, Transformation, WorldInterface


OP_WEIGHTS = {
    "TRANSFORM": 2.0,
    "COMPOSE": 1.5,
    "VERIFY": 1.0,
    "TEST": 1.0,
    "MOVE_TOWARD": 0.5,
    "MOVE_AWAY": 0.5,
    "MUTATE": -0.5,
}


class HeuristicAgent:
    name = "heuristic"

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)

    def reset(self, seed: int = 0):
        self.rng = random.Random(seed)

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
        best = max(
            actions,
            key=lambda a: (
                OP_WEIGHTS.get(a.universal_op, 0.0)
                - 0.1 * a.base_cost
                + self.rng.uniform(-0.01, 0.01)
            ),
        )
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
        pass
