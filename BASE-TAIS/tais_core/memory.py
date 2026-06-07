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
        stat = self._action_stats.setdefault(name, {
            "total": 0.0, "count": 0, "min": float("inf"), "max": float("-inf"), "domains": set()
        })
        net = episode.consequence.net
        stat["total"] += net
        stat["count"] += 1
        stat["min"] = min(stat["min"], net)
        stat["max"] = max(stat["max"], net)
        stat["domains"].add(episode.domain)

    def action_value(self, transform_name: str) -> float:
        stat = self._action_stats.get(transform_name)
        return 0.0 if not stat or stat["count"] == 0 else stat["total"] / stat["count"]

    def action_risk(self, transform_name: str) -> float:
        stat = self._action_stats.get(transform_name)
        if not stat or stat["count"] < 2:
            return 1.0
        mean = stat["total"] / stat["count"]
        return (stat["max"] - stat["min"]) / max(1.0, abs(mean))

    def best_actions(self, n: int = 3) -> List[Tuple[str, float]]:
        vals = [(name, s["total"] / max(1, s["count"])) for name, s in self._action_stats.items()]
        return sorted(vals, key=lambda kv: -kv[1])[:n]

    def worst_actions(self, n: int = 3) -> List[Tuple[str, float]]:
        vals = [(name, s["total"] / max(1, s["count"])) for name, s in self._action_stats.items()]
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
                existing.update_confidence(consequence.net > 0)
                existing.consequence_signature = existing.consequence_signature or consequence.valence
                return True

        pattern.update_confidence(consequence.net > 0)
        pattern.consequence_signature = consequence.valence
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

    def query(self, domain: str, concept: Optional[str] = None, n: int = 5) -> List[Dict[str, Any]]:
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
    """Predicted consequence vs actual consequence."""

    def __init__(self):
        self._predictions: Deque[Tuple[float, float, float]] = deque(maxlen=64)
        self._per_transform: Dict[str, List[float]] = {}
        self._per_domain: Dict[str, List[float]] = {}

    def predict(self, transformation: Transformation, pattern_memory: PatternMemory, graph: RealityGraph) -> float:
        valence = pattern_memory.predict_consequence(graph)
        if valence == "GOOD":
            return 3.0
        if valence == "BAD":
            return -3.0
        return 0.0

    def record_outcome(self, predicted: float, actual: Consequence, transformation: Transformation, domain: str):
        error = abs(predicted - actual.net)
        self._predictions.append((predicted, actual.net, error))
        self._per_transform.setdefault(transformation.name, []).append(error)
        self._per_domain.setdefault(domain, []).append(error)

    def mean_error(self) -> float:
        if not self._predictions:
            return float("inf")
        return sum(e for _p, _a, e in self._predictions) / len(self._predictions)

    def domain_error(self, domain: str) -> float:
        vals = self._per_domain.get(domain, [])
        return sum(vals) / len(vals) if vals else float("inf")

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
    ):
        fp = self._graph_fingerprint(state_before)
        error = abs(predicted - consequence.net)
        ep = Episode(fp, transformation, consequence, predicted, error, domain, tick)
        self.episodic.record(ep)
        self.prediction.record_outcome(predicted, consequence, transformation, domain)

        if abs(consequence.net) > 1.0:
            pattern = GraphPattern(
                entities=list(state_before.entities())[:5],
                relations=list(state_before.relations())[:5],
                name=f"{transformation.name}_{consequence.valence}",
                source_domain=domain,
            )
            self.patterns.store(pattern, consequence)

    def predict_action(self, transformation: Transformation, graph: RealityGraph) -> float:
        return self.prediction.predict(transformation, self.patterns, graph)

    def best_action_from_history(self, candidates: List[Transformation]) -> Optional[Transformation]:
        if not candidates:
            return None
        best, best_score = None, float("-inf")
        for t in candidates:
            score = self.episodic.action_value(t.name) - 0.3 * self.episodic.action_risk(t.name)
            if score > best_score:
                best, best_score = t, score
        return best

    def should_explore(self, candidates: List[Transformation], curiosity: float = 0.3) -> bool:
        import random
        if not candidates:
            return False
        uncertainty = 0.0 if math.isinf(self.prediction.mean_error()) else min(0.4, self.prediction.mean_error() * 0.1)
        return random.random() < curiosity + uncertainty

    def transfer_patterns_to(self, target_graph: RealityGraph) -> List[Tuple[GraphPattern, AnalogyMapping]]:
        return self.patterns.transfer_to(target_graph)

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
