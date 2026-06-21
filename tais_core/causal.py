"""
tais_core.causal
================

Causal reasoning engine for the universal mote.

Uses Delta-P (P(O|A) - P(O|~A)) to distinguish causation from
coincidence, with temporal windowing and counterfactual reasoning.

This is domain-agnostic: it records (action_name, outcome_concept, positive)
tuples and computes causal strengths. It does not know what the actions
or outcomes mean — only whether they co-occur reliably.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class CausalLink:
    """A measured causal relationship between an action and an outcome."""

    action: str
    outcome: str
    delta_p: float
    confidence: float
    sample_count: int
    p_given_action: float
    p_given_no_action: float

    @property
    def is_causal(self) -> bool:
        return abs(self.delta_p) > 0.15 and self.confidence > 0.15

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "outcome": self.outcome,
            "delta_p": round(self.delta_p, 3),
            "confidence": round(self.confidence, 3),
            "sample_count": self.sample_count,
            "p_given_action": round(self.p_given_action, 3),
            "p_given_no_action": round(self.p_given_no_action, 3),
            "is_causal": self.is_causal,
        }


@dataclass
class Counterfactual:
    """A computed counterfactual: what would happen without the action."""

    action: str
    outcome: str
    expected_result: float
    counterfactual_result: float
    tick: int

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "outcome": self.outcome,
            "expected": round(self.expected_result, 3),
            "counterfactual": round(self.counterfactual_result, 3),
            "tick": self.tick,
        }


class CausalReasoningEngine:
    """Domain-agnostic causal reasoning via Delta-P.

    Tracks each (action, outcome) pair independently so the planner
    can distinguish which action best drives a desired outcome.
    """

    def __init__(self, window_size: int = 5, min_confidence: float = 0.15):
        self.window_size = window_size
        self.min_confidence = min_confidence
        self._action_outcomes: Dict[Tuple[str, str], List[bool]] = defaultdict(list)
        self._no_action_outcomes: Dict[str, List[bool]] = defaultdict(list)
        self._links: Dict[Tuple[str, str], CausalLink] = {}
        self._counterfactuals: List[Counterfactual] = []
        self._event_log: List[Tuple[int, str, str, bool]] = []

    def record_action(self, tick: int, action: str, outcome_concept: str, positive_outcome: bool):
        """Record that performing action led to outcome_concept (positive or not)."""
        key = (action, outcome_concept)
        self._action_outcomes[key].append(positive_outcome)
        self._event_log.append((tick, action, outcome_concept, positive_outcome))
        self._recompute(action, outcome_concept)
        self._prune_log()

    def record_no_action(self, tick: int, outcome_concept: str, positive_outcome: bool):
        """Record that NOT performing any relevant action still led to outcome_concept."""
        self._no_action_outcomes[outcome_concept].append(positive_outcome)
        self._event_log.append((tick, "NO_ACTION", outcome_concept, positive_outcome))
        affected = {(a, o) for (a, o) in list(self._links) if o == outcome_concept}
        for act, outc in affected:
            self._recompute(act, outcome_concept)
        if not affected:
            self._recompute("NO_ACTION", outcome_concept)
        self._prune_log()

    def record_outcome(self, tick: int, outcome: str, delta: float, context: dict):
        """Convenience: record from a delta float (positive = good outcome)."""
        positive = delta > 0
        self.record_action(tick, "unknown", outcome, positive)

    def _recompute(self, action: str, outcome_concept: str):
        key = (action, outcome_concept)
        p_action = self._probability(self._action_outcomes.get(key, []))
        p_no_action = self._probability(self._no_action_outcomes.get(outcome_concept, []))
        delta = p_action - p_no_action
        n_action = len(self._action_outcomes.get(key, []))
        n_no_action = len(self._no_action_outcomes.get(outcome_concept, []))
        total = n_action + n_no_action
        confidence = min(1.0, total / (total + 10))
        self._links[key] = CausalLink(
            action=action,
            outcome=outcome_concept,
            delta_p=delta,
            confidence=confidence,
            sample_count=total,
            p_given_action=p_action,
            p_given_no_action=p_no_action,
        )

    def _probability(self, outcomes: List[bool]) -> float:
        if not outcomes:
            return 0.0
        return sum(1 for o in outcomes if o) / len(outcomes)

    def _prune_log(self):
        if len(self._event_log) > 1000:
            self._event_log = self._event_log[-500:]

    def get_causal_link(self, action: str, outcome_concept: str) -> Optional[CausalLink]:
        return self._links.get((action, outcome_concept))

    def get_all_links(self, min_confidence: Optional[float] = None) -> List[CausalLink]:
        threshold = min_confidence if min_confidence is not None else self.min_confidence
        return [link for link in self._links.values() if link.confidence >= threshold]

    def query_best_action(self, desired_outcome: str) -> Optional[str]:
        """What action should I take to achieve desired_outcome?"""
        candidates = []
        for link in self._links.values():
            if link.is_causal and link.delta_p > 0 and link.outcome == desired_outcome:
                candidates.append((link, link.delta_p))
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0].action

    def get_causal_strength(self, action: str, outcome_concept: str) -> float:
        link = self._links.get((action, outcome_concept))
        return link.delta_p if link else 0.0

    def get_max_causal_strength(self, outcome_concept: str) -> float:
        """Return the strongest delta_p across all actions for a given outcome."""
        best = 0.0
        for link in self._links.values():
            if link.outcome == outcome_concept and abs(link.delta_p) > abs(best):
                best = link.delta_p
        return best

    def compute_counterfactual(self, action: str, outcome_concept: str, tick: int) -> Optional[Counterfactual]:
        """What would happen if I did NOT take this action?"""
        link = self._links.get((action, outcome_concept))
        if link is None:
            return None
        expected = link.p_given_action
        counterfactual = link.p_given_no_action
        cf = Counterfactual(
            action=action,
            outcome=outcome_concept,
            expected_result=expected,
            counterfactual_result=counterfactual,
            tick=tick,
        )
        self._counterfactuals.append(cf)
        if len(self._counterfactuals) > 50:
            self._counterfactuals = self._counterfactuals[-50:]
        return cf

    def counterfactual(self, action: str, outcome_concept: str) -> Optional[dict]:
        """Convenience: returns dict or None."""
        cf = self.compute_counterfactual(action, outcome_concept, 0)
        if cf is None:
            return None
        return {
            "would_occur": cf.expected_result > cf.counterfactual_result,
            "strength": abs(cf.expected_result - cf.counterfactual_result),
        }

    @property
    def links(self) -> List[CausalLink]:
        return list(self._links.values())

    def to_dict(self) -> dict:
        return {
            "links": [l.to_dict() for l in self._links.values()],
            "counterfactuals": [c.to_dict() for c in self._counterfactuals[-10:]],
            "event_count": len(self._event_log),
        }
