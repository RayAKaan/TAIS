"""LLM Grounding Engine for TAIS."""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from .reality import Entity, RealityGraph, Relation

class LLMGroundingEngine:
    """
    Perception/Translation layer that converts Natural Language to RealityGraphs.

    This allows TAIS to handle high-level instructions while maintaining its
    symbolic, domain-agnostic reasoning core.
    """

    def __init__(self, provider: str = "mock"):
        self.provider = provider

    def ground_goal(self, nl_goal: str, domain: str = "webnav") -> RealityGraph:
        """Converts a natural language goal into a RealityGraph with GOAL entities."""
        if self.provider == "mock":
            return self._mock_ground_goal(nl_goal, domain)

        raise NotImplementedError("Only 'mock' provider is currently supported.")

    def _mock_ground_goal(self, nl_goal: str, domain: str) -> RealityGraph:
        g = RealityGraph(domain, "grounded_goal")
        g.add_entity(Entity("nav", "NAVIGATION", {"depth": 0}))

        if "flight" in nl_goal.lower() or "submit" in nl_goal.lower():
            g.add_entity(Entity("goal", "GOAL", {
                "description": nl_goal,
                "target_id": "btn1",
                "satisfied": False
            }))
            g.add_entity(Entity("btn1", "ELEMENT", {"role": "submit", "text": "Submit"}))
            g.add_relation(Relation("goal", "TARGETS", "btn1"))

        return g

    def explain_trace(self, action_trace: List[Dict[str, Any]]) -> str:
        """Converts a sequence of RealityGraph transformations into NL explanation."""
        if not action_trace:
            return "No actions were taken."

        summary = f"The agent performed {len(action_trace)} actions. "
        successes = sum(1 for a in action_trace if a.get("consequence", {}).get("net", 0) > 0)
        summary += f"It had {successes} successful steps."

        return summary
