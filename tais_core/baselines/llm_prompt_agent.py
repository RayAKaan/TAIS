from __future__ import annotations

from typing import Any, Dict, List, Optional

from tais_core.reality import Consequence, RealityGraph, Transformation, WorldInterface


class LLMPromptAgent:
    name = "llm_prompt_stub"
    enabled = False

    def __init__(self):
        pass

    def reset(self, seed: int = 0):
        pass

    def choose_action(
        self,
        world: WorldInterface,
        graph: RealityGraph,
        actions: List[Transformation],
        mote_state: Dict[str, Any],
        tick: int,
    ) -> Optional[Transformation]:
        raise RuntimeError(
            "LLMPromptAgent requires external API configuration and is disabled by default."
        )

    def observe_outcome(
        self,
        world: WorldInterface,
        before: RealityGraph,
        action: Optional[Transformation],
        after: RealityGraph,
        consequence: Consequence,
        tick: int,
    ) -> None:
        raise RuntimeError(
            "LLMPromptAgent requires external API configuration and is disabled by default."
        )
