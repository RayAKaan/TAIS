"""
tais_core.memory
================

Pattern memory is the mechanism for cross-domain transfer.

Memory types:
    EpisodicMemory  — what happened to me, sequentially
    PatternMemory   — recurring structural fragments with consequence signatures
    SymbolicMemory  — named concepts and graph fingerprints
    CulturalMemory  — archive that outlives individual motes
    PredictionEngine — predicted consequence vs actual consequence
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Tuple

from .reality import AnalogyMapping, Consequence, GraphPattern, RealityGraph, Transformation


ACTION_ROLES = [
    "APPROACH_GOOD",
    "AVOID_BAD",
    "VERIFY_UNCERTAIN",
    "TRANSFORM_TOWARD_GOAL",
    "EXPLORE_UNCERTAIN",
    "REPAIR_MISMATCH",
    "MAINTAIN_STABLE",
    "FAILED",
    "UNCLASSIFIED",
]


def infer_action_role(action: Transformation) -> str:
    """Domain-blind candidate role estimate from universal_op/role_hint."""
    if action.role_hint:
        return action.role_hint
    if action.universal_op == "MOVE_TOWARD":
        return "APPROACH_GOOD"
    if action.universal_op == "MOVE_AWAY":
        return "AVOID_BAD"
    if action.universal_op in {"VERIFY", "TEST"}:
        return "VERIFY_UNCERTAIN"
    if action.universal_op in {"TRANSFORM", "COMPOSE"}:
        return "TRANSFORM_TOWARD_GOAL"
    if action.universal_op in {"MUTATE", "OBSERVE", "FOCUS", "COMPARE"}:
        return "EXPLORE_UNCERTAIN"
    if action.universal_op in {"ASK", "ANSWER", "TEACH"}:
        return "REPAIR_MISMATCH"
    if action.universal_op == "SILENCE":
        return "MAINTAIN_STABLE"
    return "UNCLASSIFIED"


def role_compatibility(source_role: str, target_role: str) -> float:
    """How much a source role should boost a target role across domains."""
    if not source_role or not target_role:
        return 0.0
    if source_role == target_role:
        return 1.0
    # Functional analogies: moving toward a resource, applying a rule toward a
    # target fact, and adding a useful fragment are different ops but same role:
    # change state toward a good/evaluated target.
    approach_family = {"APPROACH_GOOD", "TRANSFORM_TOWARD_GOAL"}
    if source_role in approach_family and target_role in approach_family:
        return 0.70
    caution_family = {"AVOID_BAD", "VERIFY_UNCERTAIN", "MAINTAIN_STABLE"}
    if source_role in caution_family and target_role in caution_family:
        return 0.45
    if source_role == "EXPLORE_UNCERTAIN" and target_role in {"VERIFY_UNCERTAIN", "EXPLORE_UNCERTAIN"}:
        return 0.35
    if source_role == "FAILED" and target_role == "VERIFY_UNCERTAIN":
        return 0.25
    return 0.0


@dataclass
class Episode:
    state_fingerprint: str
    transformation: Transformation
    consequence: Consequence
    predicted_outcome: float = 0.0
    prediction_error: float = 0.0
    domain: str = "unknown"
    tick: int = 0
    context_concepts: List[str] = field(default_factory=list)

    @property
    def was_useful(self) -> bool:
        return self.consequence.net > 0.5

    @property
    def was_harmful(self) -> bool:
        return self.consequence.net < -0.5

    @property
    def was_surprising(self) -> bool:
        return self.prediction_error > 2.0


class EpisodicMemory:
    def __init__(self, capacity: int = 64):
        self.capacity = capacity
        self.episodes: Deque[Episode] = deque(maxlen=capacity)
        self._action_stats: Dict[str, Dict[str, Any]] = {}

    def record(self, episode: Episode):
        self.episodes.append(episode)
        name = episode.transformation.name
        stat = self._action_stats.setdefault((episode.domain, name), {
            "total": 0.0, "count": 0, "min": float("inf"), "max": float("-inf"), "domains": set()
        })
        net = episode.consequence.net
        stat["total"] += net
        stat["count"] += 1
        stat["min"] = min(stat["min"], net)
        stat["max"] = max(stat["max"], net)
        stat["domains"].add(episode.domain)

    def action_value(self, transform_name: str, domain: str = "unknown") -> float:
        stat = self._action_stats.get((domain, transform_name))
        return 0.0 if not stat or stat["count"] == 0 else stat["total"] / stat["count"]

    def action_risk(self, transform_name: str, domain: str = "unknown") -> float:
        stat = self._action_stats.get((domain, transform_name))
        if not stat or stat["count"] < 2:
            return 1.0
        mean = stat["total"] / stat["count"]
        return (stat["max"] - stat["min"]) / max(1.0, abs(mean))

    def best_actions(self, n: int = 3) -> List[Tuple[str, float]]:
        vals = [(name if isinstance(name, str) else name[1], s["total"] / max(1, s["count"])) for name, s in self._action_stats.items()]
        return sorted(vals, key=lambda kv: -kv[1])[:n]

    def worst_actions(self, n: int = 3) -> List[Tuple[str, float]]:
        vals = [(name if isinstance(name, str) else name[1], s["total"] / max(1, s["count"])) for name, s in self._action_stats.items()]
        return sorted(vals, key=lambda kv: kv[1])[:n]

    def prediction_error_trend(self) -> float:
        eps = list(self.episodes)
        if len(eps) < 4:
            return 0.0
        mid = len(eps) // 2
        early = sum(e.prediction_error for e in eps[:mid]) / mid
        late = sum(e.prediction_error for e in eps[mid:]) / (len(eps) - mid)
        return late - early

    def recent_concept_signals(self, n: int = 8) -> Dict[str, float]:
        agg: Dict[str, float] = {}
        for ep in list(self.episodes)[-n:]:
            for c, v in ep.consequence.concept_signals.items():
                agg[c] = agg.get(c, 0.0) + v
        total = max(1.0, sum(abs(v) for v in agg.values()))
        return {c: v / total for c, v in agg.items()}

    def __len__(self) -> int:
        return len(self.episodes)


class PatternMemory:
    """Stores GraphPatterns that reliably predict consequence signatures."""

    def __init__(self, capacity: int = 32):
        self.capacity = capacity
        self.patterns: List[GraphPattern] = []

    def _fingerprint(self, pattern: GraphPattern) -> str:
        return pattern.structural_key()

    def store(self, pattern: GraphPattern, consequence: Consequence) -> bool:
        fp = self._fingerprint(pattern)
        for existing in self.patterns:
            if self._fingerprint(existing) == fp:
                # Confidence means reliability of the signature, not positivity.
                # A consistently BAD pattern is just as important as a GOOD one.
                same_signature = existing.consequence_signature == consequence.valence
                existing.update_confidence(same_signature)
                existing.consequence_signature = existing.consequence_signature or consequence.valence
                n = max(1, existing.times_matched)
                existing.mean_outcome_net = ((existing.mean_outcome_net * (n - 1)) + consequence.net) / n
                # Merge action provenance.
                if pattern.successful_action_op and not existing.successful_action_op:
                    existing.successful_action_op = pattern.successful_action_op
                    existing.successful_action_name = pattern.successful_action_name
                    existing.successful_action_cost = pattern.successful_action_cost
                for op in pattern.failed_action_ops:
                    if op not in existing.failed_action_ops:
                        existing.failed_action_ops.append(op)
                for name in pattern.failed_action_names:
                    if name not in existing.failed_action_names:
                        existing.failed_action_names.append(name)
                if pattern.successful_action_role and not existing.successful_action_role:
                    existing.successful_action_role = pattern.successful_action_role
                for role in pattern.failed_action_roles:
                    if role not in existing.failed_action_roles:
                        existing.failed_action_roles.append(role)
                return True

        # New pattern: one observation, one confirmed signature.
        pattern.consequence_signature = consequence.valence
        pattern.times_matched = 1
        pattern.times_confirmed = 1
        pattern.confidence = 1.0
        pattern.mean_outcome_net = consequence.net
        if len(self.patterns) < self.capacity:
            self.patterns.append(pattern)
            return True
        weakest = min(self.patterns, key=lambda p: p.confidence)
        if pattern.confidence > weakest.confidence:
            self.patterns.remove(weakest)
            self.patterns.append(pattern)
            return True
        return False

    def lookup(self, graph: RealityGraph, min_confidence: float = 0.3) -> List[Tuple[GraphPattern, List[Dict[str, str]]]]:
        out = []
        for p in self.patterns:
            if p.confidence < min_confidence:
                continue
            matches = graph.find_pattern(p)
            if matches:
                out.append((p, matches))
        return out

    def transfer_to(self, target_graph: RealityGraph, min_confidence: float = 0.25) -> List[Tuple[GraphPattern, AnalogyMapping]]:
        out = []
        for p in self.patterns:
            if p.confidence < min_confidence:
                continue
            mapping = target_graph.analogize(p)
            if mapping.is_useful:
                out.append((p, mapping))
        return sorted(out, key=lambda pair: -pair[1].confidence)

    def predict_consequence(self, graph: RealityGraph) -> Optional[str]:
        matches = self.lookup(graph)
        if not matches:
            return None
        votes: Dict[str, float] = {}
        for p, _ in matches:
            v = p.consequence_signature or "NEUTRAL"
            votes[v] = votes.get(v, 0.0) + p.confidence
        return max(votes, key=votes.get)

    def action_priors(
        self,
        target_graph: RealityGraph,
        available_actions: List[Transformation],
        min_confidence: float = 0.30,
        min_analogy: float = 0.30,
    ) -> Tuple[Dict[str, float], int]:
        """
        Bridge representation to action.

        Pattern transfer alone says: this situation resembles an old situation.
        Action priors say: and in that old situation, this kind of action helped
        or hurt, so bias current action selection accordingly.

        Returns:
            ({action.name: boost}, number_of_transfer_patterns_used)
        """
        boosts: Dict[str, float] = {a.name: 0.0 for a in available_actions}
        used = 0
        transfers = self.transfer_to(target_graph, min_confidence=min_confidence)
        for pattern, mapping in transfers:
            if mapping.confidence < min_analogy:
                continue
            used += 1
            base = mapping.confidence * pattern.confidence * max(0.25, abs(pattern.mean_outcome_net))
            for action in available_actions:
                target_role = infer_action_role(action)
                # Positive transfer by action role first, universal_op second.
                if pattern.consequence_signature == "GOOD":
                    role_match = role_compatibility(pattern.successful_action_role or "", target_role)
                    if role_match:
                        boosts[action.name] += base * role_match
                    elif pattern.successful_action_op and action.universal_op == pattern.successful_action_op:
                        boosts[action.name] += base * 0.50
                # Negative transfer: avoid roles/ops that harmed in analogous contexts.
                if pattern.consequence_signature == "BAD":
                    if target_role in pattern.failed_action_roles:
                        boosts[action.name] -= base
                    if action.universal_op in pattern.failed_action_ops:
                        boosts[action.name] -= base * 0.50
                    # Generic safety bias for bad/danger patterns. This remains
                    # domain-agnostic: it boosts universal verification/caution roles.
                    if target_role in {"VERIFY_UNCERTAIN", "AVOID_BAD"}:
                        boosts[action.name] += base * 0.30
                    if target_role in {"EXPLORE_UNCERTAIN"}:
                        boosts[action.name] -= base * 0.20
        return boosts, used

    def prune(self, min_confidence: float = 0.15):
        self.patterns = [p for p in self.patterns if p.confidence >= min_confidence]

    def best_patterns(self, n: int = 5) -> List[GraphPattern]:
        return sorted(self.patterns, key=lambda p: -p.confidence)[:n]

    def __len__(self) -> int:
        return len(self.patterns)


class SymbolicMemory:
    """Named concepts grounded in graph fingerprints and repair events."""

    def __init__(self):
        self.concepts: Dict[str, Dict[str, Any]] = {}
        self.token_map: Dict[str, str] = {}
        self.repair_log: List[Dict[str, Any]] = []

    def associate(self, token: str, concept: str, graph_fp: str, success: bool):
        entry = self.concepts.setdefault(concept, {
            "token": token, "pattern_fps": set(), "concept": concept,
            "confidence": 0.5, "uses": 0, "successes": 0,
        })
        entry["pattern_fps"].add(graph_fp)
        entry["uses"] += 1
        if success:
            entry["successes"] += 1
        entry["confidence"] = entry["successes"] / max(1, entry["uses"])
        entry["token"] = token
        self.token_map[token] = concept

    def best_token_for(self, concept: str) -> Optional[str]:
        e = self.concepts.get(concept)
        return e["token"] if e else None

    def concept_for_token(self, token: str) -> Optional[str]:
        return self.token_map.get(token)

    def register_repair(self, sent_token: str, intended_concept: str, listener_action: str, outcome: str):
        self.repair_log.append({
            "token": sent_token,
            "intended": intended_concept,
            "listener_did": listener_action,
            "outcome": outcome,
            "timestamp": time.time(),
        })

    def token_reliability(self, token: str) -> float:
        repairs = [r for r in self.repair_log if r["token"] == token and r["outcome"] == "BAD"]
        concept = self.token_map.get(token)
        if concept and concept in self.concepts:
            return float(self.concepts[concept]["confidence"])
        return max(0.0, 0.5 - len(repairs) * 0.1)

    def stable_concepts(self, min_confidence: float = 0.6) -> List[str]:
        return [c for c, d in self.concepts.items() if d["confidence"] >= min_confidence]

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        out = {}
        for c, d in self.concepts.items():
            out[c] = {
                "token": d["token"],
                "confidence": round(float(d["confidence"]), 3),
                "uses": d["uses"],
                "successes": d["successes"],
            }
        return out


class CulturalMemory:
    """Shared archive that outlives motes."""

    def __init__(self, capacity_per_domain: int = 100):
        self.capacity = capacity_per_domain
        self._store: Dict[str, List[Dict[str, Any]]] = {}
        self._global: List[Dict[str, Any]] = []

    def write(self, domain: str, entry: Dict[str, Any], fitness: float):
        if fitness < 5.0:
            return
        tagged = {**entry, "fitness": fitness, "timestamp": time.time(), "domain": domain}
        self._store.setdefault(domain, []).append(tagged)
        if len(self._store[domain]) > self.capacity:
            self._store[domain] = sorted(self._store[domain], key=lambda e: -e["fitness"])[:self.capacity]

    def write_cross_domain(self, entry: Dict[str, Any], fitness: float):
        if fitness < 6.0:
            return
        self._global.append({**entry, "fitness": fitness, "timestamp": time.time()})
        if len(self._global) > self.capacity:
            self._global = sorted(self._global, key=lambda e: -e["fitness"])[:self.capacity]

    def query(self, domain: str, concept: Optional[str] = None, n: int = 5, energy_cost: float = 0.0) -> List[Dict[str, Any]]:
        entries = list(self._store.get(domain, []))
        if concept:
            entries = [e for e in entries if e.get("concept") == concept or concept in e.get("concepts", [])]
        return sorted(entries, key=lambda e: -e["fitness"])[:n]

    def query_cross_domain(self, n: int = 5) -> List[Dict[str, Any]]:
        return sorted(self._global, key=lambda e: -e["fitness"])[:n]

    def domain_summary(self) -> Dict[str, int]:
        return {d: len(v) for d, v in self._store.items()}

    def total_entries(self) -> int:
        return sum(len(v) for v in self._store.values()) + len(self._global)


class PredictionEngine:
    """Predicted consequence vs actual consequence.

    Phase 1.5 (2026-06): three calibration fixes after the v2 ablation
    diagnostic showed `no_prediction` *helps* on first_apply_implication_tick
    while *doubling* prediction error. Old behavior was:

    - Per-action history keyed by transformation name only, with no per-domain
      separation: a `move_toward` mean learned in GridWorld would leak into
      RuleWorld if a RuleWorld action shared the name.
    - Unweighted mean of the last 12 outcomes: a single +4 first solve gets
      drowned by twelve +0.05 repeats, so apply_implication's predicted value
      decays below verify_rule's predicted value within ~6 ticks.
    - Pattern-valence fallback hardcoded to +-3.0, calibrated for GridWorld
      resource-pickup-scale rewards. In RuleWorld where verify pays +0.02,
      every action seen by the mote for the first time in a "GOOD"-looking
      graph gets +3.0, so verify (cost 0.2) appears as +2.80 net score while
      apply_implication (cost 0.4) appears as +2.60 — verify wins.

    Fixes:

    1. Per-action history is keyed by (domain, name). Cross-domain analogy
       still works through pattern memory; it should not happen invisibly
       through per-action means.
    2. Outcomes are tracked as an exponentially-weighted running mean
       (alpha=0.4) instead of an unweighted sliding window. A first +4 solve
       stays informative for several ticks instead of being averaged away
       inside 12 samples.
    3. Pattern-valence fallback is cost-anchored: |prior| <= 1.5 * base_cost,
       clipped at +-3.0. An action that costs 0.4 gets at most +-0.6 of prior
       from valence alone — proportional to its skin in the game.
    4. Unseen-action prior is discounted by `_UNSEEN_DISCOUNT` (0.5). Prior
       uncertainty deserves a discount, not a full optimistic prior.

    These changes are local to predict()/record_outcome() and do not change
    the (predicted, actual, error) memory layout used by callers.
    """

    _UNSEEN_DISCOUNT: float = 0.5
    _EWM_ALPHA: float = 0.4

    def __init__(self):
        self._predictions: Deque[Tuple[float, float, float]] = deque(maxlen=64)
        self._per_transform: Dict[str, List[float]] = {}
        # Phase 1.5: keyed by (domain, name), and value is a running EW mean
        # plus sample count instead of an unbounded list.
        self._per_transform_net_ewm: Dict[Tuple[str, str], Tuple[float, int]] = {}
        self._per_domain: Dict[str, List[float]] = {}
        # Phase A: per-domain reward scale for prediction calibration
        self._domain_abs_mean: Dict[str, float] = {}
        self._domain_obs_count: Dict[str, int] = {}

    def _calibrate(self, raw: float, domain: str) -> float:
        """Scale prediction to match domain reward scale.

        For domains with tiny rewards (e.g. LogicWorld ~0.02), the
        cost-anchored prior (0.25) hugely overestimates the outcome,
        inflating prediction error.  We damp the prior proportionally
        to the domain's typical |reward| so the first prediction error
        is no larger than what no_prediction sees.
        """
        scale = self._domain_abs_mean.get(domain)
        if scale is not None and 0.0 < scale < 1.0:
            return raw * scale
        return raw

    def _update_domain_scale(self, domain: str, abs_net: float):
        old = self._domain_abs_mean.get(domain, 0.0)
        count = self._domain_obs_count.get(domain, 0)
        self._domain_abs_mean[domain] = (old * count + abs_net) / (count + 1)
        self._domain_obs_count[domain] = count + 1

    def predict(self, transformation: Transformation, pattern_memory: PatternMemory, graph: RealityGraph) -> float:
        key = (transformation.domain, transformation.name)
        cached = self._per_transform_net_ewm.get(key)
        if cached is not None:
            ewm, _n = cached
            return ewm

        # No per-action history yet. Use a cost-anchored, valence-shaped prior.
        valence = pattern_memory.predict_consequence(graph)
        # Reward scale that respects the action's own cost: a cheap action
        # shouldn't be promised a huge return, and an expensive action gets a
        # proportionally larger (but still bounded) prior.
        cap = max(0.5, min(3.0, 1.5 * float(transformation.base_cost or 1.0)))
        if valence == "GOOD":
            raw = cap * self._UNSEEN_DISCOUNT
        elif valence == "BAD":
            raw = -cap * self._UNSEEN_DISCOUNT
        else:
            raw = 0.0

        # Calibrate to domain reward scale (Phase A)
        return self._calibrate(raw, transformation.domain)

    def record_outcome(self, predicted: float, actual: Consequence, transformation: Transformation, domain: str):
        error = abs(predicted - actual.net)
        self._predictions.append((predicted, actual.net, error))
        self._per_transform.setdefault(transformation.name, []).append(error)
        # Phase 1.5: EWM with explicit alpha; first observation seeds the mean.
        key = (transformation.domain, transformation.name)
        cur = self._per_transform_net_ewm.get(key)
        if cur is None:
            self._per_transform_net_ewm[key] = (float(actual.net), 1)
        else:
            ewm, n = cur
            new_ewm = (1.0 - self._EWM_ALPHA) * ewm + self._EWM_ALPHA * float(actual.net)
            self._per_transform_net_ewm[key] = (new_ewm, n + 1)
        self._per_domain.setdefault(domain, []).append(error)
        # Phase A: update per-domain reward scale
        self._update_domain_scale(domain, abs(actual.net))

    def mean_error(self) -> float:
        if not self._predictions:
            return float("inf")
        return sum(e for _p, _a, e in self._predictions) / len(self._predictions)

    def domain_error(self, domain: str) -> float:
        vals = self._per_domain.get(domain, [])
        return sum(vals) / len(vals) if vals else float("inf")

    def domain_observation_count(self, domain: str) -> int:
        return self._domain_obs_count.get(domain, 0)

    def is_understanding(self, threshold: float = 1.5) -> bool:
        return len(self._predictions) >= 8 and self.mean_error() < threshold

    def error_trend(self) -> float:
        vals = list(self._predictions)
        if len(vals) < 4:
            return 0.0
        mid = len(vals) // 2
        early = sum(e for _p, _a, e in vals[:mid]) / mid
        late = sum(e for _p, _a, e in vals[mid:]) / (len(vals) - mid)
        return late - early


class MoteMemory:
    """Composite memory object owned by a universal mote."""

    def __init__(self, episodic_capacity: int = 64, pattern_capacity: int = 32):
        self.episodic = EpisodicMemory(episodic_capacity)
        self.patterns = PatternMemory(pattern_capacity)
        self.symbolic = SymbolicMemory()
        self.prediction = PredictionEngine()

    def record_episode(
        self,
        state_before: RealityGraph,
        transformation: Transformation,
        consequence: Consequence,
        predicted: float,
        domain: str,
        tick: int,
        action_role: str = "UNCLASSIFIED",
    ):
        fp = self._graph_fingerprint(state_before)
        error = abs(predicted - consequence.net)
        ep = Episode(fp, transformation, consequence, predicted, error, domain, tick)
        self.episodic.record(ep)
        self.prediction.record_outcome(predicted, consequence, transformation, domain)

        # Global Improvement: More sensitive pattern extraction.
        # Lower threshold for real-world domains where rewards are smaller.
        threshold = 1.0 if domain in ["grid", "rules"] else 0.4
        if abs(consequence.net) >= threshold:
            pattern = GraphPattern(
                entities=list(state_before.entities())[:5],
                relations=list(state_before.relations())[:5],
                name=f"{transformation.name}_{consequence.valence}",
                source_domain=domain,
                successful_action_op=transformation.universal_op if consequence.net > 0 else None,
                successful_action_name=transformation.name if consequence.net > 0 else None,
                successful_action_cost=transformation.base_cost if consequence.net > 0 else 0.0,
                failed_action_ops=[transformation.universal_op] if consequence.net < 0 else [],
                failed_action_names=[transformation.name] if consequence.net < 0 else [],
                successful_action_role=action_role if consequence.net > 0 else None,
                failed_action_roles=[action_role] if consequence.net < 0 else [],
                mean_outcome_net=consequence.net,
            )
            self.patterns.store(pattern, consequence)

    def predict_action(self, transformation: Transformation, graph: RealityGraph) -> float:
        return self.prediction.predict(transformation, self.patterns, graph)

    def best_action_from_history(self, candidates: List[Transformation]) -> Optional[Transformation]:
        if not candidates:
            return None
        best, best_score = None, float("-inf")
        for t in candidates:
            score = self.episodic.action_value(t.name, domain=t.domain) - 0.3 * self.episodic.action_risk(t.name, domain=t.domain)
            if score > best_score:
                best, best_score = t, score
        return best

    def should_explore(self, candidates: List[Transformation], curiosity: float = 0.3, domain: Optional[str] = None) -> bool:
        import random
        if not candidates:
            return False
        if domain is not None:
            err = self.prediction.domain_error(domain)
        else:
            err = self.prediction.mean_error()
        uncertainty = 0.0 if math.isinf(err) else min(0.2, err * 0.05)
        return random.random() < min(0.5, curiosity + uncertainty)

    def transfer_patterns_to(self, target_graph: RealityGraph) -> List[Tuple[GraphPattern, AnalogyMapping]]:
        return self.patterns.transfer_to(target_graph)

    def transfer_action_priors(self, target_graph: RealityGraph, available_actions: List[Transformation]) -> Tuple[Dict[str, float], int]:
        return self.patterns.action_priors(target_graph, available_actions)

    def _graph_fingerprint(self, graph: RealityGraph) -> str:
        return hashlib.md5(json.dumps(graph.summary(), sort_keys=True).encode()).hexdigest()[:12]

    def summary(self) -> Dict[str, Any]:
        return {
            "episodes": len(self.episodic),
            "patterns": len(self.patterns),
            "stable_concepts": self.symbolic.stable_concepts(),
            "best_actions": self.episodic.best_actions(3),
            "worst_actions": self.episodic.worst_actions(3),
            "mean_pred_error": None if math.isinf(self.prediction.mean_error()) else round(self.prediction.mean_error(), 3),
            "pred_improving": self.prediction.error_trend() < 0,
            "understands": self.prediction.is_understanding(),
        }
