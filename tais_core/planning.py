"""
tais_core.planning
==================

Hierarchical planner for the universal mote.

Backward chaining from causal model, plan library with reuse,
rollback, and replanning. Operates on action-role strings and
causal links from CausalReasoningEngine — completely domain-agnostic.

Usage in UniversalMote.step():
    1. Before choosing action: if active plan exists, use its next step
    2. After consequence: advance_step() on success, rollback() on failure
    3. Periodically: create_plan() from causal links toward a goal
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class PlanStep:
    action: str
    target_concept: str
    expected_outcome: str
    conditions: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "target_concept": self.target_concept,
            "expected_outcome": self.expected_outcome,
            "conditions": self.conditions,
        }


@dataclass
class Plan:
    steps: List[PlanStep]
    goal: str
    expected_utility: float
    tick_created: int
    is_active: bool = True
    current_step: int = 0
    times_used: int = 0
    times_successful: int = 0
    creator_id: Optional[int] = None

    @property
    def success_rate(self) -> float:
        return self.times_successful / max(1, self.times_used)

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "expected_utility": round(self.expected_utility, 3),
            "tick_created": self.tick_created,
            "is_active": self.is_active,
            "current_step": self.current_step,
            "times_used": self.times_used,
            "times_successful": self.times_successful,
            "success_rate": round(self.success_rate, 3),
        }


class HierarchicalPlanner:
    """Goal-directed planning via backward chaining through causal links."""

    def __init__(self, planning_cost: float = 2.0):
        self.planning_cost = planning_cost
        self._plan_library: Dict[str, List[Plan]] = defaultdict(list)
        self._active_plan: Optional[Plan] = None
        self._plan_history: List[Tuple[int, str, bool]] = []

    def create_plan(self, goal: str, causal_links: List[Tuple[str, str, float]], tick: int) -> Optional[Plan]:
        steps = self._backward_chain(goal, causal_links)
        if not steps:
            return None
        utility = self._estimate_utility(steps, causal_links)
        plan = Plan(steps=steps, goal=goal, expected_utility=utility, tick_created=tick)
        self._plan_library[goal].append(plan)
        return plan

    def _backward_chain(self, goal: str, causal_links: List[Tuple[str, str, float]]) -> List[PlanStep]:
        """Single-step backward chaining.

        Finds the action that most directly increases the probability of
        *goal*. Multi-step plans require precondition tracking (future work).
        """
        best: Optional[Tuple[List[PlanStep], float]] = None
        for action, outcome, delta_p in causal_links:
            if outcome == goal and delta_p > 0.15:
                step = PlanStep(action=action, target_concept=goal, expected_outcome=outcome)
                if best is None or delta_p > best[1]:
                    best = ([step], delta_p)
        if best is None:
            return []
        return best[0]

    def _estimate_utility(self, steps: List[PlanStep], causal_links: List[Tuple[str, str, float]]) -> float:
        if not steps:
            return 0.0
        avg_delta = 0.0
        n = 0
        for action, outcome, delta_p in causal_links:
            for step in steps:
                if step.action == action and step.expected_outcome == outcome:
                    avg_delta += delta_p
                    n += 1
        if n == 0:
            return 0.3
        return avg_delta / n * (1 - 0.1 * len(steps))

    def select_plan(self, goal: str, min_utility: float = 0.0) -> Optional[Plan]:
        plans = self._plan_library.get(goal, [])
        if not plans:
            return None
        scored = [(p, p.expected_utility * (1 + 0.2 * p.success_rate)) for p in plans if p.is_active]
        scored.sort(key=lambda x: x[1], reverse=True)
        for plan, score in scored:
            if score >= min_utility:
                return plan
        return scored[0][0] if scored else None

    def start_plan(self, plan: Plan) -> bool:
        if not plan.is_active:
            return False
        self._active_plan = plan
        plan.current_step = 0
        plan.times_used += 1
        return True

    def next_step(self) -> Optional[PlanStep]:
        if self._active_plan is None:
            return None
        if self._active_plan.current_step >= len(self._active_plan.steps):
            self._active_plan = None
            return None
        return self._active_plan.steps[self._active_plan.current_step]

    def advance_step(self):
        if self._active_plan is not None:
            self._active_plan.current_step += 1
            if self._active_plan.current_step >= len(self._active_plan.steps):
                self._active_plan.times_successful += 1
                self._plan_history.append((self._active_plan.tick_created, self._active_plan.goal, True))
                self._active_plan = None

    def execute_step(self) -> Optional[PlanStep]:
        step = self.next_step()
        if step is not None:
            self.advance_step()
        return step

    def rollback(self):
        if self._active_plan is not None:
            self._plan_history.append((self._active_plan.tick_created, self._active_plan.goal, False))
            self._active_plan = None

    def replan(self, goal: str, new_causal_links: List[Tuple[str, str, float]], tick: int) -> Optional[Plan]:
        old_plan = self._active_plan
        if old_plan is not None:
            old_plan.is_active = False
        return self.create_plan(goal, new_causal_links, tick)

    @property
    def active_plan(self) -> Optional[Plan]:
        return self._active_plan

    @active_plan.setter
    def active_plan(self, plan: Optional[Plan]):
        self._active_plan = plan

    def get_next_step(self) -> Optional[str]:
        """Convenience: return just the action name of the next planned step."""
        step = self.next_step()
        return step.action if step else None

    def plan_for_goal(self, goal: dict, causal_engine) -> Optional[Plan]:
        """Create a plan from a goal dict and a CausalReasoningEngine."""
        links = causal_engine.get_all_links() if hasattr(causal_engine, "get_all_links") else []
        causal_links = [(l.action, l.outcome, l.delta_p) for l in links if l.is_causal]
        if not causal_links:
            return None
        goal_str = goal.get("type", str(goal)) if isinstance(goal, dict) else str(goal)
        return self.create_plan(goal_str, causal_links, 0)

    def to_dict(self) -> dict:
        return {
            "active_plan": self._active_plan.to_dict() if self._active_plan else None,
            "plan_library": {g: [p.to_dict() for p in plans] for g, plans in self._plan_library.items()},
            "history": [(t, g, s) for t, g, s in self._plan_history[-20:]],
        }
