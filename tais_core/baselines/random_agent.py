from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from tais_core.reality import Consequence, RealityGraph, Transformation, WorldInterface


class RandomAgent:
    name = "random"

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
        return self.rng.choice(actions)

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
