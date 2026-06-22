"""
tais_core.schema_learning
==========================

AGI Roadmap Step 3: Abstract Schema Learning.

Schemas are domain-agnostic structural patterns that capture the essence
of a situation WITHOUT referencing concrete entity type names.

Schema = variable slots + anonymous relations + expected outcomes + action mapping

This enables cross-domain transfer: the same schema (e.g. "resource near threat")
can be matched in GridWorld, NegoSim, or any other domain because it depends
only on topology, not surface names.

Three components:
    1. AbstractSchema — domain-agnostic pattern with variable slots
    2. SchemaLearner — learns/promotes/verifies schemas from observations
    3. SchemaComposition — multi-step strategies composed from schemas
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .reality import Consequence, Entity, GraphPattern, RealityGraph, Relation
from .structural_similarity import (
    wl_pattern_histogram,
    wl_relabeled_graph,
    wl_similarity,
)


# ─── ABSTRACT SCHEMA ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class VariableSlot:
    """A variable slot in an abstract schema.

    Instead of naming an entity type (e.g. "AGENT"), we describe it
    by its structural role and expected degree range.
    """

    slot_id: str
    structural_role: str  # e.g., "central", "peripheral", "bridge", "leaf"
    degree_range: Tuple[int, int]  # (min, max) degree in the pattern
    cardinality: str = "single"  # "single", "multiple", "optional"

    def matches_entity(self, entity: Entity, degree: int) -> bool:
        """Check if an entity matches this slot's structural profile."""
        if self.degree_range[0] <= degree <= self.degree_range[1]:
            return True
        return False

    def to_dict(self) -> dict:
        return {
            "slot_id": self.slot_id,
            "structural_role": self.structural_role,
            "degree_range": list(self.degree_range),
            "cardinality": self.cardinality,
        }


@dataclass(frozen=True)
class AnonymousRelation:
    """A relation in an abstract schema with anonymous types.

    Instead of "SEES" or "NEAR", we capture only the structural pattern
    of the connection: source role, target role, and whether it's
    directional.
    """

    source_role: str  # slot_id
    target_role: str  # slot_id
    directed: bool = True
    relation_type: str = "generic"  # "generic", "hierarchical", "sequential"

    def to_dict(self) -> dict:
        return {
            "source_role": self.source_role,
            "target_role": self.target_role,
            "directed": self.directed,
            "relation_type": self.relation_type,
        }


@dataclass
class AbstractSchema:
    """A domain-agnostic structural schema.

    Schemas capture the ESSENCE of a situation — the topology of
    interactions — without referencing any concrete entity or relation
    type names.

    Example: "threat_near_resource" schema
        Slots:
            'agent' (central, degree 2-5)
            'resource' (peripheral, degree 1-3)
            'threat' (peripheral, degree 1-3)
        Relations:
            threat -> resource (NEAR-type)
            threat -> agent (VISIBLE-type)
            resource -> agent (VISIBLE-type)
        Expected outcome: DANGER

    This schema matches any domain where a peripheral entity is
    adjacent to another peripheral entity and visible to a central
    entity, regardless of what those entities are named.
    """

    name: str
    slots: List[VariableSlot] = field(default_factory=list)
    relations: List[AnonymousRelation] = field(default_factory=list)
    expected_outcome_signature: str = "NEUTRAL"
    recommended_action_role: Optional[str] = None
    confidence: float = 0.5
    times_matched: int = 0
    times_confirmed: int = 0
    source_domains: Set[str] = field(default_factory=set)

    def structural_fingerprint(self) -> str:
        """Unique hash based on schema topology (not names)."""
        slot_info = sorted(
            (s.structural_role, s.degree_range, s.cardinality) for s in self.slots
        )
        rel_info = sorted(
            (r.source_role, r.target_role, r.relation_type) for r in self.relations
        )
        payload = (
            f"slots={slot_info}|rels={rel_info}|outcome={self.expected_outcome_signature}"
        )
        return hashlib.md5(payload.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "slots": [s.to_dict() for s in self.slots],
            "relations": [r.to_dict() for r in self.relations],
            "expected_outcome": self.expected_outcome_signature,
            "recommended_action": self.recommended_action_role,
            "confidence": round(self.confidence, 3),
            "times_matched": self.times_matched,
            "times_confirmed": self.times_confirmed,
            "source_domains": list(self.source_domains),
            "fingerprint": self.structural_fingerprint(),
        }


# Convenience aliases for backward compatibility
Schema = AbstractSchema
SchemaSlot = VariableSlot


# ─── SCHEMA EXTRACTION ──────────────────────────────────────────────────────


class SchemaExtractor:
    """Extract abstract schemas from concrete observations.

    Converts a RealityGraph observation into an AbstractSchema by
    analyzing the structural roles of entities and relations.
    """

    def extract(self, graph: RealityGraph) -> Optional[AbstractSchema]:
        """Extract a schema from a single graph observation."""
        entities = list(graph.entities())
        if len(entities) < 2:
            return None

        # Compute degrees
        degrees: Dict[str, int] = {}
        for e in entities:
            out_deg = len(list(graph.neighbors_out(e.id)))
            in_deg = len(list(graph.neighbors_in(e.id)))
            degrees[e.id] = out_deg + in_deg

        if not degrees:
            return None

        max_deg = max(degrees.values())
        min_deg = min(degrees.values())

        # Assign structural roles based on degree
        slots: List[VariableSlot] = []
        for e in entities:
            deg = degrees[e.id]
            if deg == max_deg and max_deg > min_deg:
                role = "central"
            elif deg == min_deg:
                role = "leaf"
            elif deg > sum(degrees.values()) / len(degrees):
                role = "bridge"
            else:
                role = "peripheral"

            # Group by role
            slots.append(
                VariableSlot(
                    slot_id=e.id,
                    structural_role=role,
                    degree_range=(deg, deg),
                )
            )

        # Extract anonymous relations
        anon_relations: List[AnonymousRelation] = []
        slot_by_id: Dict[str, VariableSlot] = {s.slot_id: s for s in slots}

        for rel in graph.relations():
            if rel.source in slot_by_id and rel.target in slot_by_id:
                source_role = slot_by_id[rel.source].structural_role
                target_role = slot_by_id[rel.target].structural_role

                # Determine relation type from current type
                rtype = "generic"
                if rel.rtype in ("NEAR", "ADJACENT", "CLOSE", "TOUCHES"):
                    rtype = "hierarchical"
                elif rel.rtype in ("SEES", "OBSERVES", "WATCHES", "VISIBLE"):
                    rtype = "sequential"
                elif rel.rtype in ("REQUIRES", "NEEDS", "DEPENDS_ON", "CAUSES"):
                    rtype = "hierarchical"

                anon_relations.append(
                    AnonymousRelation(
                        source_role=source_role,
                        target_role=target_role,
                        directed=rel.directed,
                        relation_type=rtype,
                    )
                )

        if not slots:
            return None

        # Generate a name from the topology
        type_signature = Counter(s.structural_role for s in slots)
        name = "_".join(f"{r}{c}" for r, c in type_signature.most_common(3))

        return AbstractSchema(
            name=name,
            slots=slots,
            relations=anon_relations,
            expected_outcome_signature="NEUTRAL",
            source_domains={graph.domain},
        )

    def extract_from_pattern(self, pattern: GraphPattern) -> Optional[AbstractSchema]:
        """Extract a schema from a GraphPattern."""
        entities = list(pattern.entities)
        if len(entities) < 2:
            return None

        # Build adjacency
        adj_out: Dict[str, List[str]] = defaultdict(list)
        adj_in: Dict[str, List[str]] = defaultdict(list)
        for rel in pattern.relations:
            adj_out[rel.source].append(rel.target)
            adj_in[rel.target].append(rel.source)

        degrees: Dict[str, int] = {}
        for e in entities:
            degrees[e.id] = len(adj_out.get(e.id, [])) + len(adj_in.get(e.id, []))

        if not degrees:
            return None

        max_deg = max(degrees.values())
        min_deg = min(degrees.values())

        slots: List[VariableSlot] = []
        for e in entities:
            deg = degrees[e.id]
            if deg == max_deg and max_deg > min_deg:
                role = "central"
            elif deg == 0:
                role = "leaf"
            elif deg > sum(degrees.values()) / len(degrees):
                role = "bridge"
            else:
                role = "peripheral"

            slots.append(
                VariableSlot(
                    slot_id=e.id,
                    structural_role=role,
                    degree_range=(deg, deg),
                )
            )

        slot_by_id: Dict[str, VariableSlot] = {s.slot_id: s for s in slots}
        anon_relations: List[AnonymousRelation] = []
        for rel in pattern.relations:
            if rel.source in slot_by_id and rel.target in slot_by_id:
                source_role = slot_by_id[rel.source].structural_role
                target_role = slot_by_id[rel.target].structural_role
                rtype = "generic"
                if rel.rtype in ("NEAR", "ADJACENT", "CLOSE"):
                    rtype = "hierarchical"
                elif rel.rtype in ("SEES", "OBSERVES", "VISIBLE"):
                    rtype = "sequential"
                elif rel.rtype in ("REQUIRES", "NEEDS", "DEPENDS_ON"):
                    rtype = "hierarchical"
                anon_relations.append(
                    AnonymousRelation(
                        source_role=source_role,
                        target_role=target_role,
                        directed=rel.directed,
                        relation_type=rtype,
                    )
                )

        if not slots:
            return None

        type_signature = Counter(s.structural_role for s in slots)
        name = "_".join(f"{r}{c}" for r, c in type_signature.most_common(3))

        return AbstractSchema(
            name=name,
            slots=slots,
            relations=anon_relations,
            expected_outcome_signature=pattern.consequence_signature or "NEUTRAL",
            recommended_action_role=pattern.successful_action_role,
            source_domains={pattern.source_domain} if pattern.source_domain else set(),
        )


# ─── SCHEMA LEARNER ──────────────────────────────────────────────────────────


class SchemaLearner:
    """Learn, promote, and verify abstract schemas from experience.

    The learner:
    1. Extracts candidate schemas from observations
    2. Matches new observations against known schemas
    3. Updates confidence based on outcome alignment
    4. Promotes high-confidence schemas for cross-domain transfer
    """

    def __init__(
        self,
        min_confidence: float = 0.3,
        promote_threshold: float = 0.7,
        wl_iterations: int = 3,
        wl_match_threshold: float = 0.4,
    ):
        self.min_confidence = min_confidence
        self.promote_threshold = promote_threshold
        self.wl_iterations = wl_iterations
        self.wl_match_threshold = wl_match_threshold
        self._schemas: Dict[str, AbstractSchema] = {}
        self._extractor = SchemaExtractor()

    def observe(
        self,
        graph: RealityGraph,
        consequence: Optional[Consequence] = None,
    ) -> Optional[str]:
        """Observe a graph and learn/update schemas.

        Returns the name of the matched or created schema, or None.
        """
        # Extract candidate schema
        candidate = self._extractor.extract(graph)
        if candidate is None:
            return None

        # Set expected outcome from consequence
        if consequence:
            if consequence.reward > 0 and consequence.penalty <= 0:
                candidate.expected_outcome_signature = "GOOD"
            elif consequence.penalty > 0:
                candidate.expected_outcome_signature = "BAD"
            elif consequence.reward == 0 and consequence.penalty == 0:
                candidate.expected_outcome_signature = "NEUTRAL"
            else:
                candidate.expected_outcome_signature = "MIXED"

        fp = candidate.structural_fingerprint()

        # Check if we already have a matching schema
        existing = self._find_matching_schema(candidate)
        if existing is not None:
            self._update_schema(existing, candidate, consequence)
            return existing.name

        # New schema
        self._schemas[fp] = candidate
        return candidate.name

    def _schema_to_synthetic_graph(self, schema: AbstractSchema) -> RealityGraph:
        """Build a synthetic graph from a schema for WL comparison."""
        g = RealityGraph("schema", f"synth_{schema.name}")
        for slot in schema.slots:
            g.add_entity(
                Entity(slot.slot_id, slot.structural_role)
            )
        for rel in schema.relations:
            g.add_relation(
                Relation(
                    rel.source_role, rel.relation_type, rel.target_role,
                    directed=rel.directed,
                )
            )
        return g

    def _schema_wl_similarity(
        self, a: AbstractSchema, b: AbstractSchema
    ) -> float:
        """WL similarity between two schemas' structural patterns."""
        g_a = self._schema_to_synthetic_graph(a)
        g_b = self._schema_to_synthetic_graph(b)
        hist_a = wl_relabeled_graph(g_a, self.wl_iterations)
        hist_b = wl_relabeled_graph(g_b, self.wl_iterations)
        try:
            return wl_similarity(hist_a, hist_b, self.wl_iterations)
        except Exception:
            return 0.0

    def _partial_slot_match(
        self,
        a_slots: List[VariableSlot],
        b_slots: List[VariableSlot],
    ) -> bool:
        """Relaxed slot matching with role compatibility and degree tolerance."""
        compatible_roles: Dict[str, Set[str]] = {
            "central": {"central", "bridge"},
            "bridge": {"central", "bridge", "peripheral"},
            "peripheral": {"bridge", "peripheral", "leaf"},
            "leaf": {"peripheral", "leaf"},
        }

        if len(a_slots) == 0 or len(b_slots) == 0:
            return False

        matched = 0
        used_b: Set[int] = set()
        for a_slot in a_slots:
            for j, b_slot in enumerate(b_slots):
                if j in used_b:
                    continue
                if b_slot.structural_role in compatible_roles.get(
                    a_slot.structural_role, {a_slot.structural_role}
                ):
                    a_min, a_max = a_slot.degree_range
                    b_min, b_max = b_slot.degree_range
                    overlap = min(a_max, b_max) - max(a_min, b_min)
                    width = max(a_max - a_min, b_max - b_min, 1)
                    if overlap / width >= -0.5:
                        matched += 1
                        used_b.add(j)
                        break

        match_ratio = matched / max(len(a_slots), len(b_slots))
        return match_ratio >= 0.5

    def _find_matching_schema(
        self, candidate: AbstractSchema
    ) -> Optional[AbstractSchema]:
        """Find an existing schema that matches this candidate.

        Tries exact match first, then falls back to WL similarity
        and partial slot matching.
        """
        # Phase 1: exact match
        for schema in self._schemas.values():
            if self._schemas_match(schema, candidate):
                return schema

        # Phase 2: partial match via WL similarity + relaxed slots
        best_sim = 0.0
        best_schema: Optional[AbstractSchema] = None
        for schema in self._schemas.values():
            if self._partial_slot_match(schema.slots, candidate.slots):
                wl_sim = self._schema_wl_similarity(schema, candidate)
                if wl_sim > best_sim:
                    best_sim = wl_sim
                    best_schema = schema

        if best_schema is not None and best_sim >= self.wl_match_threshold:
            return best_schema

        return None

    def _schemas_match(
        self, a: AbstractSchema, b: AbstractSchema
    ) -> bool:
        """Check if two schemas have the same structure (ignoring variable IDs)."""
        a_slots = sorted(
            (s.structural_role, s.cardinality) for s in a.slots
        )
        b_slots = sorted(
            (s.structural_role, s.cardinality) for s in b.slots
        )
        if a_slots != b_slots:
            return False

        a_rels = sorted(
            (r.source_role, r.target_role, r.relation_type) for r in a.relations
        )
        b_rels = sorted(
            (r.source_role, r.target_role, r.relation_type) for r in b.relations
        )
        if a_rels != b_rels:
            return False

        return True

    def _update_schema(
        self,
        existing: AbstractSchema,
        candidate: AbstractSchema,
        consequence: Optional[Consequence],
    ):
        """Update an existing schema with new evidence."""
        existing.times_matched += 1
        existing.source_domains.add(candidate.name)

        if consequence:
            outcome_good = consequence.reward > consequence.penalty
            if outcome_good:
                existing.times_confirmed += 1
            existing.confidence = existing.times_confirmed / max(1, existing.times_matched)

    def match_graph(
        self, graph: RealityGraph
    ) -> List[Tuple[AbstractSchema, float]]:
        """Match a graph against all known schemas.

        Returns list of (schema, match_score) pairs, sorted by score.
        """
        candidate = self._extractor.extract(graph)
        if candidate is None:
            return []

        matches: List[Tuple[AbstractSchema, float]] = []
        for schema in self._schemas.values():
            score = self._schema_match_score(schema, candidate)
            if score >= self.min_confidence:
                matches.append((schema, score))

        matches.sort(key=lambda x: x[1], reverse=True)
        return matches

    def _schema_match_score(
        self, schema: AbstractSchema, candidate: AbstractSchema
    ) -> float:
        """Compute how well a candidate matches a known schema."""
        if not self._schemas_match(schema, candidate):
            return 0.0

        # Base score from confidence
        base = schema.confidence

        # Outcome alignment bonus
        if schema.expected_outcome_signature == candidate.expected_outcome_signature:
            base += 0.2
        elif "NEUTRAL" in (schema.expected_outcome_signature, candidate.expected_outcome_signature):
            base += 0.1
        else:
            base -= 0.1

        return max(0.0, min(1.0, base))

    def learn_from_episode(
        self,
        graph: RealityGraph,
        action: Any,
        consequence: Consequence,
        domain: str,
        tick: int = 0,
    ) -> Optional[AbstractSchema]:
        """Learn a schema from an episode (graph + action + outcome)."""
        schema_name = self.observe(graph, consequence)
        if schema_name is None:
            return None

        schema = self.get_schema(schema_name)
        if schema is not None:
            schema.source_domains.add(domain)
        return schema

    def get_promoted_schemas(self) -> List[AbstractSchema]:
        """Get schemas confident enough for cross-domain transfer."""
        return [
            s for s in self._schemas.values()
            if s.confidence >= self.promote_threshold
        ]

    def get_all_schemas(self) -> List[AbstractSchema]:
        return list(self._schemas.values())

    def get_schema(self, name: str) -> Optional[AbstractSchema]:
        for s in self._schemas.values():
            if s.name == name:
                return s
        return None

    def to_dict(self) -> dict:
        return {
            "schemas": [s.to_dict() for s in self._schemas.values()],
            "promoted": len(self.get_promoted_schemas()),
        }


# ─── SCHEMA COMPOSITION ──────────────────────────────────────────────────────


@dataclass
class SchemaStep:
    """A single step in a schema composition."""

    schema_name: str
    action_role: str
    expected_transition: str  # what outcome this step produces
    order: int


@dataclass
class SchemaComposition:
    """A multi-step strategy composed from multiple schemas.

    Enables the mote to plan sequences: Schema A → Schema B → Schema C.
    """

    name: str
    steps: List[SchemaStep] = field(default_factory=list)
    overall_outcome: str = "NEUTRAL"
    confidence: float = 0.5
    times_used: int = 0
    times_successful: int = 0

    def add_step(
        self,
        schema_name: str,
        action_role: str,
        expected_transition: str,
    ):
        step = SchemaStep(
            schema_name=schema_name,
            action_role=action_role,
            expected_transition=expected_transition,
            order=len(self.steps),
        )
        self.steps.append(step)

    def record_use(self, successful: bool):
        self.times_used += 1
        if successful:
            self.times_successful += 1
        self.confidence = self.times_successful / max(1, self.times_used)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "steps": [
                {
                    "schema": s.schema_name,
                    "action": s.action_role,
                    "transition": s.expected_transition,
                    "order": s.order,
                }
                for s in sorted(self.steps, key=lambda x: x.order)
            ],
            "overall_outcome": self.overall_outcome,
            "confidence": round(self.confidence, 3),
            "times_used": self.times_used,
            "success_rate": (
                round(self.times_successful / max(1, self.times_used), 3)
            ),
        }


class CompositionLearner:
    """Learn multi-step schema compositions from successful sequences."""

    def __init__(self):
        self._compositions: Dict[str, SchemaComposition] = {}

    def record_sequence(
        self,
        schema_names: List[str],
        action_roles: List[str],
        outcomes: List[str],
        final_success: bool,
    ):
        """Record a sequence of schemas that led to success/failure."""
        if len(schema_names) < 2:
            return

        # Create a composition key
        key = "->".join(schema_names)

        if key not in self._compositions:
            comp = SchemaComposition(
                name=key,
                overall_outcome="GOOD" if final_success else "BAD",
            )
            for i, (sn, ar, oc) in enumerate(zip(schema_names, action_roles, outcomes)):
                comp.add_step(sn, ar, oc)
            comp.record_use(final_success)
            self._compositions[key] = comp
        else:
            self._compositions[key].record_use(final_success)

    def get_compositions(self, min_confidence: float = 0.0) -> List[SchemaComposition]:
        return [
            c for c in self._compositions.values()
            if c.confidence >= min_confidence
        ]

    def to_dict(self) -> dict:
        return {
            "compositions": [c.to_dict() for c in self._compositions.values()],
        }
