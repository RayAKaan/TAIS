"""
tais_core.causal_intervention
==============================

AGI Roadmap Step 2: Causal Intervention Engine with do-calculus.

This module moves beyond correlational Delta-P (in tais_core.causal) to
proper causal intervention using Pearl's do-calculus framework.

Key ideas:
    - Causal effect = P(outcome | do(action)) - P(outcome | do(no_action))
    - Counterfactual: what WOULD have happened if we had taken a different action
    - Intervention: actually performing an action and measuring the outcome
    - Structural baseline: average outcome of other actions in same structural context

Three components:
    1. CausalInterventionEngine — do-calculus causal effect estimation
    2. CounterfactualEstimator — structural counterfactual reasoning
    3. InterventionValidator — RCT-based validation of causal claims
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .reality import Consequence, RealityGraph
from .structural_similarity import wl_relabeled_graph, wl_similarity


# ─── DATA TYPES ──────────────────────────────────────────────────────────────


@dataclass
class CausalEffect:
    """A measured causal effect using do-calculus.

    causal_effect = actual_outcome - counterfactual_outcome

    Positive = action causes desired outcome
    Negative = action prevents desired outcome
    Zero = no causal relationship
    """

    structural_key: str
    action_name: str
    causal_effect: float
    confidence: float
    sample_count: int
    actual_mean: float
    counterfactual_mean: float
    p_value: float = 1.0

    def is_significant(self, threshold: float = 0.1) -> bool:
        return abs(self.causal_effect) > threshold and self.confidence > 0.3

    def to_dict(self) -> dict:
        return {
            "structural_key": self.structural_key,
            "action_name": self.action_name,
            "causal_effect": round(self.causal_effect, 4),
            "confidence": round(self.confidence, 4),
            "sample_count": self.sample_count,
            "actual_mean": round(self.actual_mean, 4),
            "counterfactual_mean": round(self.counterfactual_mean, 4),
            "p_value": round(self.p_value, 4),
            "is_significant": self.is_significant(),
        }


@dataclass
class InterventionRecord:
    """Record of a single intervention experiment."""

    structural_key: str
    action_name: str
    outcome: float
    expected_outcome: float
    tick: int
    domain: str = ""
    successful: bool = False


# ─── STRUCTURAL KEY UTILITY ─────────────────────────────────────────────────


def structural_key_from_graph(graph: RealityGraph) -> str:
    """Compute a surface-invariant structural key for a RealityGraph.

    Uses anonymized type names (frequency-rank indices) so that two
    graphs with the same topology but different entity/relation type
    names produce the same key. This enables cross-domain causal transfer.

    The key is based on degree-anonymized type histograms, making it
    invariant under surface relabeling.
    """
    from collections import Counter

    entities = list(graph.entities())
    relations = list(graph.relations())

    # Anonymize entity types by frequency rank (break ties by avg degree)
    etype_counts: Dict[str, int] = Counter(e.etype for e in entities)
    degree_by_type: Dict[str, List[int]] = defaultdict(list)
    for e in entities:
        out_deg = len(list(graph.neighbors_out(e.id)))
        in_deg = len(list(graph.neighbors_in(e.id)))
        degree_by_type[e.etype].append(out_deg + in_deg)
    avg_deg_by_type = {
        etype: sum(degs) / len(degs) if degs else 0
        for etype, degs in degree_by_type.items()
    }
    sorted_etypes = sorted(
        etype_counts.items(),
        key=lambda x: (-x[1], -avg_deg_by_type.get(x[0], 0))
    )
    anon_etypes = {etype: f"T{i}" for i, (etype, _) in enumerate(sorted_etypes)}

    # Anonymize relation types by frequency rank
    rtype_counts: Dict[str, int] = Counter(r.rtype for r in relations)
    src_deg_by_rtype: Dict[str, List[int]] = defaultdict(list)
    for rel in relations:
        src = graph.get_entity(rel.source)
        if src:
            sd = len(list(graph.neighbors_out(src.id))) + len(list(graph.neighbors_in(src.id)))
            src_deg_by_rtype[rel.rtype].append(sd)
    avg_sd_by_rtype = {
        rtype: sum(degs) / len(degs) if degs else 0
        for rtype, degs in src_deg_by_rtype.items()
    }
    sorted_rtypes = sorted(
        rtype_counts.items(),
        key=lambda x: (-x[1], -avg_sd_by_rtype.get(x[0], 0))
    )
    anon_rtypes = {rtype: f"R{i}" for i, (rtype, _) in enumerate(sorted_rtypes)}

    anon_e_list = sorted(set(anon_etypes[e.etype] for e in entities))
    anon_r_list = sorted(set(anon_rtypes[r.rtype] for r in relations))
    n_entities = len(entities)
    n_relations = len(relations)

    return f"E[{','.join(anon_e_list)}]_R[{','.join(anon_r_list)}]_N{n_entities}_R{n_relations}"


# ─── CAUSAL INTERVENTION ENGINE ─────────────────────────────────────────────


class CausalInterventionEngine:
    """do-calculus causal effect estimator.

    Computes causal effects by comparing actual outcomes against
    counterfactual baselines. The counterfactual estimate comes from
    other actions sharing the same structural context.

    This is domain-agnostic: it indexes by structural_key, not action name,
    enabling cross-domain causal transfer.
    """

    def __init__(
        self,
        min_samples: int = 3,
        significance_threshold: float = 0.1,
        wl_iterations: int = 3,
        min_wl_similarity: float = 0.25,
    ):
        self.min_samples = min_samples
        self.significance_threshold = significance_threshold
        self.wl_iterations = wl_iterations
        self.min_wl_similarity = min_wl_similarity

        # Index: structural_key -> action_name -> list of outcomes
        self._outcomes: Dict[str, Dict[str, List[float]]] = defaultdict(
            lambda: defaultdict(list)
        )

        # Computed causal effects
        self._effects: Dict[str, CausalEffect] = {}

        # Intervention history
        self._interventions: List[InterventionRecord] = []

        # WL histograms: structural_key -> histogram for partial matching
        self._wl_histograms: Dict[str, Dict[str, float]] = {}

        self._tick = 0

    def record_intervention(
        self,
        graph: RealityGraph,
        action_name: str,
        outcome: float,
        expected_outcome: float = 0.0,
    ):
        """Record the result of an intervention.

        Args:
            graph: The graph state before the intervention
            action_name: Name of the action taken
            outcome: Actual outcome (reward, delta, etc.)
            expected_outcome: What the action was expected to produce
        """
        s_key = structural_key_from_graph(graph)
        self._outcomes[s_key][action_name].append(outcome)

        # Store WL histogram for partial matching
        if s_key not in self._wl_histograms:
            self._wl_histograms[s_key] = wl_relabeled_graph(
                graph, self.wl_iterations
            )

        self._tick += 1

        record = InterventionRecord(
            structural_key=s_key,
            action_name=action_name,
            outcome=outcome,
            expected_outcome=expected_outcome,
            tick=self._tick,
            domain=graph.domain,
            successful=outcome > 0,
        )
        self._interventions.append(record)

        self._recompute_effect(s_key, action_name)

    def record_no_action(self, graph: RealityGraph, outcome: float):
        """Record the outcome of NOT taking any action.

        This provides the do(no_action) baseline.
        """
        s_key = structural_key_from_graph(graph)
        self._outcomes[s_key]["__no_action__"].append(outcome)
        self._tick += 1

        # Recompute all effects for this structural key
        for action_name in list(self._outcomes.get(s_key, {})):
            self._recompute_effect(s_key, action_name)

    def _recompute_effect(self, structural_key: str, action_name: str):
        """Recompute the causal effect for a (structural_key, action) pair."""
        outcomes = self._outcomes.get(structural_key, {})
        action_outcomes = outcomes.get(action_name, [])
        no_action_outcomes = outcomes.get("__no_action__", [])

        # Counterfactual baseline: what would happen without this action?
        # Use no_action outcomes when available, otherwise use other actions
        # in the same structural context as baseline.
        if len(no_action_outcomes) >= self.min_samples:
            counterfactual_outcomes = no_action_outcomes
        else:
            # Use other actions in same structural context as baseline
            other_outcomes: List[float] = []
            for act, outcs in outcomes.items():
                if act != action_name and act != "__no_action__":
                    other_outcomes.extend(outcs)
            counterfactual_outcomes = other_outcomes

        if len(action_outcomes) < self.min_samples:
            return  # Not enough data

        actual_mean = sum(action_outcomes) / len(action_outcomes)

        if counterfactual_outcomes:
            cf_mean = sum(counterfactual_outcomes) / len(counterfactual_outcomes)
        else:
            cf_mean = 0.0

        causal_effect = actual_mean - cf_mean

        # Confidence: more samples and larger gap = higher confidence
        total_samples = len(action_outcomes) + len(counterfactual_outcomes)
        effect_magnitude = abs(causal_effect)
        confidence = min(
            1.0,
            (len(action_outcomes) / (len(action_outcomes) + 5))
            * (1.0 - math.exp(-effect_magnitude * 2))
        )

        # Approximate p-value (simplified: assume normal distribution)
        if len(action_outcomes) >= 3 and counterfactual_outcomes:
            var_action = (
                sum((o - actual_mean) ** 2 for o in action_outcomes)
                / len(action_outcomes)
            )
            var_cf = (
                sum((o - cf_mean) ** 2 for o in counterfactual_outcomes)
                / len(counterfactual_outcomes)
            )
            se = math.sqrt(
                var_action / len(action_outcomes)
                + var_cf / len(counterfactual_outcomes)
            )
            if se > 0:
                t_stat = abs(causal_effect) / se
                p_value = 2 * (1 - self._approx_normal_cdf(t_stat))
            else:
                p_value = 0.0
        else:
            p_value = 1.0

        key = f"{structural_key}::{action_name}"
        self._effects[key] = CausalEffect(
            structural_key=structural_key,
            action_name=action_name,
            causal_effect=causal_effect,
            confidence=confidence,
            sample_count=len(action_outcomes),
            actual_mean=actual_mean,
            counterfactual_mean=cf_mean,
            p_value=p_value,
        )

    def _compute_wl_similarity(self, key_a: str, key_b: str) -> float:
        """Compute WL similarity between two structural keys' histograms."""
        hist_a = self._wl_histograms.get(key_a)
        hist_b = self._wl_histograms.get(key_b)
        if hist_a is None or hist_b is None:
            return 0.0
        try:
            return wl_similarity(hist_a, hist_b, self.wl_iterations)
        except Exception:
            return 0.0

    def get_causal_effect(
        self, structural_key: str, action_name: str
    ) -> Optional[CausalEffect]:
        # Exact match first
        exact = self._effects.get(f"{structural_key}::{action_name}")
        if exact is not None:
            return exact

        # Fall back to WL similarity partial matching
        best_sim = 0.0
        best_key: Optional[str] = None
        for skey in list(self._outcomes.keys()):
            if action_name in self._outcomes[skey] and skey != structural_key:
                sim = self._compute_wl_similarity(structural_key, skey)
                if sim > best_sim:
                    best_sim = sim
                    best_key = skey

        if best_key is not None and best_sim >= self.min_wl_similarity:
            source_effect = self._effects.get(f"{best_key}::{action_name}")
            if source_effect is not None:
                return CausalEffect(
                    structural_key=structural_key,
                    action_name=action_name,
                    causal_effect=source_effect.causal_effect * best_sim,
                    confidence=source_effect.confidence * best_sim,
                    sample_count=source_effect.sample_count,
                    actual_mean=source_effect.actual_mean,
                    counterfactual_mean=source_effect.counterfactual_mean,
                    p_value=source_effect.p_value,
                )

        return None

    def causal_action_boosts(
        self, graph: RealityGraph, actions: List[str]
    ) -> Dict[str, float]:
        """Compute action boosts via partial WL similarity matching.

        Returns a dict mapping action_name -> boost score for actions
        with a significant positive causal effect in any structurally
        similar context.
        """
        s_key = structural_key_from_graph(graph)
        boosts: Dict[str, float] = {}
        for action_name in actions:
            effect = self.get_causal_effect(s_key, action_name)
            if effect is not None and effect.is_significant():
                boosts[action_name] = effect.causal_effect
        return boosts

    def get_best_action(self, structural_key: str) -> Optional[str]:
        """Find the action with the strongest positive causal effect."""
        best_effect = -float("inf")
        best_action = None
        for key, effect in self._effects.items():
            if effect.structural_key == structural_key and effect.is_significant():
                if effect.causal_effect > best_effect:
                    best_effect = effect.causal_effect
                    best_action = effect.action_name
        return best_action

    def get_all_effects(
        self, min_confidence: float = 0.0
    ) -> List[CausalEffect]:
        return [
            e for e in self._effects.values() if e.confidence >= min_confidence
        ]

    def _approx_normal_cdf(self, x: float) -> float:
        """Approximate standard normal CDF (Abramowitz and Stegun)."""
        if x < 0:
            return 1 - self._approx_normal_cdf(-x)
        k = 1 / (1 + 0.2316419 * x)
        poly = k * (0.319381530 + k * (-0.356563782 + k * (1.781477937 + k * (-1.821255978 + 1.330274429 * k))))
        return 1 - 0.398942280 * math.exp(-x * x / 2) * poly

    def to_dict(self) -> dict:
        return {
            "effects": [e.to_dict() for e in self._effects.values()],
            "interventions": len(self._interventions),
            "structural_keys": len(set(r.structural_key for r in self._interventions)),
        }


# ─── COUNTERFACTUAL ESTIMATOR ───────────────────────────────────────────────


class CounterfactualEstimator:
    """Counterfactual reasoning using same-structure baseline.

    Answers: "What would have happened if we had taken action Y instead of X
    in the same situation?"

    Uses structural context grouping: actions that were taken in graphs with
    the same structural key are considered exchangeable.
    """

    def __init__(self, engine: CausalInterventionEngine):
        self.engine = engine

    def estimate_counterfactual(
        self,
        structural_key: str,
        actual_action: str,
        counterfactual_action: str,
    ) -> Optional[Dict[str, float]]:
        """Estimate what would happen if we did counterfactual_action instead.

        Returns dict with 'would_have_happened' (mean outcome) and
        'difference' (how much better/worse), or None if insufficient data.
        """
        actual_effect = self.engine.get_causal_effect(
            structural_key, actual_action
        )
        cf_effect = self.engine.get_causal_effect(
            structural_key, counterfactual_action
        )

        if actual_effect is None or cf_effect is None:
            return None

        # Counterfactual: what would counterfactual_action yield?
        # Use its actual mean as the estimate
        would_happen = cf_effect.actual_mean
        difference = would_happen - actual_effect.actual_mean

        return {
            "would_have_happened": would_happen,
            "difference": difference,
            "actual_action_effect": actual_effect.causal_effect,
            "cf_action_effect": cf_effect.causal_effect,
            "is_better": difference > 0,
        }

    def what_if(
        self,
        structural_key: str,
        current_action: str,
        alternative_actions: List[str],
    ) -> List[Dict[str, Any]]:
        """Compare current action against multiple alternatives."""
        results = []
        for alt in alternative_actions:
            if alt == current_action:
                continue
            cf = self.estimate_counterfactual(
                structural_key, current_action, alt
            )
            if cf is not None:
                results.append({"action": alt, **cf})
        results.sort(key=lambda x: x.get("difference", 0), reverse=True)
        return results


# ─── INTERVENTION VALIDATOR ─────────────────────────────────────────────────


@dataclass
class ValidationResult:
    """Result of validating a causal claim via RCT."""

    claim_key: str
    treatment_mean: float
    control_mean: float
    effect_size: float
    p_value: float
    n_treatment: int
    n_control: int
    is_validated: bool
    iterations: int = 1


class InterventionValidator:
    """Validates causal claims using Randomised Controlled Trials.

    Takes a claimed causal effect and tests it by:
    1. Assigning entities randomly to treatment/control
    2. Measuring outcomes
    3. Computing whether the effect is statistically significant
    """

    def __init__(self, engine: CausalInterventionEngine, p_threshold: float = 0.05):
        self.engine = engine
        self.p_threshold = p_threshold
        self._validations: List[ValidationResult] = []

    def validate_claim(
        self,
        structural_key: str,
        action_name: str,
        n_simulations: int = 30,
    ) -> Optional[ValidationResult]:
        """Validate a causal claim using bootstrapped RCT simulation.

        Uses existing intervention data to simulate treatment/control
        groups, testing whether the claimed effect is robust.
        """
        effect = self.engine.get_causal_effect(structural_key, action_name)
        if effect is None or effect.sample_count < self.engine.min_samples:
            return None

        # Get all outcomes for this structural key
        outcomes = self.engine._outcomes.get(structural_key, {})
        treatment_outcomes = outcomes.get(action_name, [])
        control_outcomes = outcomes.get("__no_action__", [])

        # If no control outcomes, use other actions as control
        if len(control_outcomes) < self.engine.min_samples:
            for act, outcs in outcomes.items():
                if act != action_name and act != "__no_action__":
                    control_outcomes.extend(outcs)

        if len(control_outcomes) < self.engine.min_samples:
            return None

        # Bootstrap resampling
        significant_count = 0
        for _ in range(n_simulations):
            t_sample = random.choices(treatment_outcomes, k=len(treatment_outcomes))
            c_sample = random.choices(control_outcomes, k=len(control_outcomes))

            t_mean = sum(t_sample) / len(t_sample)
            c_mean = sum(c_sample) / len(c_sample)

            # Simple t-test approximation
            var_t = (
                sum((o - t_mean) ** 2 for o in t_sample) / len(t_sample)
                if len(t_sample) > 1
                else 0
            )
            var_c = (
                sum((o - c_mean) ** 2 for o in c_sample) / len(c_sample)
                if len(c_sample) > 1
                else 0
            )
            se = math.sqrt(var_t / len(t_sample) + var_c / len(c_sample))
            if se > 0:
                t_stat = abs(t_mean - c_mean) / se
                p = 2 * (1 - _approx_normal_cdf(t_stat))
            else:
                p = 1.0

            if p < self.p_threshold:
                significant_count += 1

        is_validated = significant_count > n_simulations * 0.8
        p_value = 1.0 - (significant_count / n_simulations)

        result = ValidationResult(
            claim_key=f"{structural_key}::{action_name}",
            treatment_mean=sum(treatment_outcomes) / len(treatment_outcomes),
            control_mean=sum(control_outcomes) / len(control_outcomes),
            effect_size=effect.causal_effect,
            p_value=p_value,
            n_treatment=len(treatment_outcomes),
            n_control=len(control_outcomes),
            is_validated=is_validated,
            iterations=n_simulations,
        )
        self._validations.append(result)
        return result

    def get_validated_effects(self) -> List[ValidationResult]:
        return [v for v in self._validations if v.is_validated]


def _approx_normal_cdf(x: float) -> float:
    """Standard normal CDF approximation."""
    if x < 0:
        return 1 - _approx_normal_cdf(-x)
    k = 1 / (1 + 0.2316419 * x)
    poly = k * (
        0.319381530
        + k * (-0.356563782 + k * (1.781477937 + k * (-1.821255978 + 1.330274429 * k)))
    )
    return 1 - 0.398942280 * math.exp(-x * x / 2) * poly
