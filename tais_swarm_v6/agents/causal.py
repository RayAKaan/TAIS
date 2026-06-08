"""
Causal reasoning engine for TAIS Swarm V6.

Delta-P: P(O|A) - P(O|~A) — distinguishes causation from coincidence
using temporal precedence and counterfactuals.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class CausalLink:
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
    def __init__(self, window_size: int = 5, min_confidence: float = 0.15):
        self.window_size = window_size
        self.min_confidence = min_confidence
        self._action_outcomes: Dict[str, List[bool]] = defaultdict(list)
        self._no_action_outcomes: Dict[str, List[bool]] = defaultdict(list)
        self._links: Dict[str, CausalLink] = {}
        self._counterfactuals: List[Counterfactual] = []
        self._event_log: List[Tuple[int, str, str, bool]] = []

    def record_action(self, tick: int, action: str, outcome_concept: str, positive_outcome: bool):
        self._action_outcomes[outcome_concept].append(positive_outcome)
        self._event_log.append((tick, action, outcome_concept, positive_outcome))
        self._recompute(outcome_concept)
        self._prune_log()

    def record_no_action(self, tick: int, outcome_concept: str, positive_outcome: bool):
        self._no_action_outcomes[outcome_concept].append(positive_outcome)
        self._event_log.append((tick, "NO_ACTION", outcome_concept, positive_outcome))
        self._recompute(outcome_concept)
        self._prune_log()

    def _recompute(self, outcome_concept: str):
        p_action = self._probability(self._action_outcomes.get(outcome_concept, []))
        p_no_action = self._probability(self._no_action_outcomes.get(outcome_concept, []))
        delta = p_action - p_no_action
        n_action = len(self._action_outcomes.get(outcome_concept, []))
        n_no_action = len(self._no_action_outcomes.get(outcome_concept, []))
        total = n_action + n_no_action
        confidence = min(1.0, total / (total + 10))
        self._links[outcome_concept] = CausalLink(
            action="ANY", outcome=outcome_concept,
            delta_p=delta, confidence=confidence,
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

    def get_causal_link(self, outcome_concept: str) -> Optional[CausalLink]:
        return self._links.get(outcome_concept)

    def get_all_links(self, min_confidence: Optional[float] = None) -> List[CausalLink]:
        threshold = min_confidence if min_confidence is not None else self.min_confidence
        return [link for link in self._links.values() if link.confidence >= threshold]

    def query_best_action(self, desired_outcome: str) -> Optional[str]:
        candidates = []
        for out, link in self._links.items():
            if link.is_causal and link.delta_p > 0 and out == desired_outcome:
                candidates.append((link, link.delta_p))
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0].action

    def compute_counterfactual(self, action: str, outcome_concept: str, tick: int) -> Optional[Counterfactual]:
        link = self._links.get(outcome_concept)
        if link is None:
            return None
        expected = link.p_given_action
        counterfactual = link.p_given_no_action
        cf = Counterfactual(
            action=action, outcome=outcome_concept,
            expected_result=expected,
            counterfactual_result=counterfactual,
            tick=tick,
        )
        self._counterfactuals.append(cf)
        if len(self._counterfactuals) > 50:
            self._counterfactuals = self._counterfactuals[-50:]
        return cf

    def to_dict(self) -> dict:
        return {
            "links": [l.to_dict() for l in self._links.values()],
            "counterfactuals": [c.to_dict() for c in self._counterfactuals[-10:]],
            "event_count": len(self._event_log),
        }
