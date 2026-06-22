"""
tais_core.role_discovery
========================

Role Discovery Engine: discovers functional action roles from experience
by clustering (structural_pattern, action, consequence) triples.

This REPLACES the hand-coded role system:
  - No role_hint on Transformations
  - No fixed 9-role taxonomy (APPROACH_GOOD, AVOID_BAD, ...)
  - No infer_action_role() mapping from universal_op -> role
  - No hand-coded role_compatibility() table

Instead, roles emerge from the topology of the observation plus the
outcome of the action. A "role" is defined as:

    "In graphs with topology SHAPE_X, action ACTION_Y produces
     consequence in direction Z"

The key insight: roles are defined by the STRUCTURE of the situation
plus the OUTCOME of the action, not by a label someone gave it.

This enables genuine transfer: if GridWorld has a pattern
  [THREAT--NEAR-->RESOURCE]
and NegoSim has a pattern
  [UNFAIR_PROPOSAL--FROM-->COUNTERPART]
these have no label overlap, but if they have the same graph topology
(2 entities, 1 relation, same degree distribution), the role discovery
engine will cluster them together — enabling transfer without labels.

Algorithm:
  1. After each episode, extract the structural key of the observation
  2. Group episodes by structural key (topology of what the agent saw)
  3. Within each structural group, identify which actions consistently
     produce positive vs negative outcomes
  4. Cluster by (structural_key, outcome_direction) to form discovered roles
  5. Assign stable role IDs based on cluster membership
  6. Use cluster overlap for transfer — no hand-coded compatibility needed
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from .reality import Consequence, GraphPattern, RealityGraph, Transformation


# --- DISCOVERED ROLE ----------------------------------------------------------

@dataclass
class DiscoveredRole:
    """A functional role discovered from interaction experience.

    Not assigned by code — discovered by clustering observations,
    actions, and consequences.
    """

    role_id: str                          # Stable identifier: "role_0", "role_1", ...
    structural_key: str                   # Topology signature of the observation
    outcome_valence: str                  # "POSITIVE", "NEGATIVE", "NEUTRAL"
    action_names: Set[str]                # Actions that produced this role
    universal_ops: Set[str]               # Universal ops that produced this role
    entity_type_set: FrozenSet[str]       # Entity types seen in observations
    relation_type_set: FrozenSet[str]     # Relation types seen in observations
    mean_outcome: float                   # Average consequence.net
    sample_count: int                     # How many episodes support this role
    confidence: float                     # Reliability (0-1)
    source_domains: Set[str]              # Which domains contributed to this role
    outcome_concepts: Dict[str, float]    # Aggregated concept signals

    def to_dict(self) -> dict:
        return {
            "role_id": self.role_id,
            "structural_key": self.structural_key,
            "outcome_valence": self.outcome_valence,
            "action_names": sorted(self.action_names),
            "universal_ops": sorted(self.universal_ops),
            "entity_type_set": sorted(self.entity_type_set),
            "relation_type_set": sorted(self.relation_type_set),
            "mean_outcome": round(self.mean_outcome, 3),
            "sample_count": self.sample_count,
            "confidence": round(self.confidence, 3),
            "source_domains": sorted(self.source_domains),
            "outcome_concepts": {k: round(v, 3) for k, v in self.outcome_concepts.items()},
        }


# --- EPISODIAL RECORD FOR ROLE DISCOVERY -------------------------------------

@dataclass
class RoleDiscoveryRecord:
    """One (observation, action, consequence) triple for clustering."""

    structural_key: str            # Topology signature of the observation
    entity_types: FrozenSet[str]   # Entity types in observation
    relation_types: FrozenSet[str] # Relation types in observation
    action_name: str
    universal_op: str
    domain: str
    outcome_net: float
    outcome_valence: str           # "POSITIVE", "NEGATIVE", "NEUTRAL"
    concept_signals: Dict[str, float]
    tick: int


# --- ROLE DISCOVERY ENGINE ----------------------------------------------------

class RoleDiscoveryEngine:
    """Discovers functional roles by clustering experience records.

    The clustering key is (structural_key, outcome_valence) — i.e., the
    topology of the situation plus whether the outcome was good or bad.

    This is the core mechanism that replaces hand-coded role taxonomies.
    If two situations have the same topology and the same outcome direction,
    the actions that work in one should transfer to the other — regardless
    of what the actions are called or what domain they come from.
    """

    def __init__(
        self,
        min_cluster_size: int = 2,
        max_roles: int = 64,
        concept_weight: float = 0.3,
        structural_weight: float = 0.5,
        valence_weight: float = 0.2,
    ):
        self.min_cluster_size = min_cluster_size
        self.max_roles = max_roles
        self.concept_weight = concept_weight
        self.structural_weight = structural_weight
        self.valence_weight = valence_weight

        # Raw experience records
        self._records: List[RoleDiscoveryRecord] = []
        self._max_records: int = 2000

        # Clusters: keyed by (structural_key, outcome_valence)
        self._clusters: Dict[Tuple[str, str], List[RoleDiscoveryRecord]] = defaultdict(list)

        # Discovered roles: stable role objects
        self._roles: Dict[str, DiscoveredRole] = {}
        self._next_role_id: int = 0

        # Cache: structural_key -> computed key (for quick lookup)
        self._structural_key_cache: Dict[str, str] = {}

    def compute_structural_key(self, graph: RealityGraph) -> str:
        """Compute a topology-only signature for a graph.

        This uses ONLY the structural properties of the graph:
        - Number of entities per type (anonymized)
        - Number of relations per type (anonymized)
        - Degree distribution

        It does NOT use entity IDs, relation names, or any domain-specific
        labels. Two graphs with the same topology but completely different
        surface names will produce the same structural key.

        This is the foundation of genuine structural transfer: if two
        observations have the same structural key, they are structurally
        analogous regardless of what domain they come from.
        """
        if graph is None:
            return "EMPTY"

        # Count entity types (sorted by count for stability)
        etype_counts: Dict[str, int] = defaultdict(int)
        for e in graph.entities():
            etype_counts[e.etype] += 1

        # Count relation types (sorted by count for stability)
        rtype_counts: Dict[str, int] = defaultdict(int)
        for r in graph.relations():
            rtype_counts[r.rtype] += 1

        # Degree distribution: how many entities have degree 0, 1, 2, ...
        degree_counts: Dict[int, int] = defaultdict(int)
        for ent in graph.entities():
            eid_str = ent.id
            out_deg = len(list(graph.neighbors_out(eid_str)))
            in_deg = len(list(graph.neighbors_in(eid_str)))
            degree_counts[out_deg + in_deg] += 1

        # Build topology string — sorted for determinism
        # Key: we anonymize the TYPE NAMES themselves, replacing them with
        # positional indices sorted by count. This is what makes the key
        # surface-independent: "THREAT" and "UNFAIR_PROPOSAL" both become
        # "etype_0" if they appear with the same frequency.
        etype_sig = ",".join(
            f"e{i}:{c}" for i, (_, c) in
            enumerate(sorted(etype_counts.items(), key=lambda x: (-x[1], x[0])))
        )
        rtype_sig = ",".join(
            f"r{i}:{c}" for i, (_, c) in
            enumerate(sorted(rtype_counts.items(), key=lambda x: (-x[1], x[0])))
        )
        degree_sig = ",".join(
            f"d{k}:{v}" for k, v in sorted(degree_counts.items())
        )

        # Hash for compactness
        raw = f"|{etype_sig}|{rtype_sig}|{degree_sig}|"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    def compute_structural_key_rich(self, graph: RealityGraph) -> Tuple[str, FrozenSet[str], FrozenSet[str]]:
        """Compute structural key AND return the type sets for richer matching.

        Returns:
            (structural_key, entity_type_set, relation_type_set)
        """
        skey = self.compute_structural_key(graph)
        etypes = frozenset(e.etype for e in graph.entities())
        rtypes = frozenset(r.rtype for r in graph.relations())
        return skey, etypes, rtypes

    def record_experience(
        self,
        observation: RealityGraph,
        action: Transformation,
        consequence: Consequence,
        domain: str,
        tick: int,
    ) -> Optional[str]:
        """Record an (observation, action, consequence) experience.

        Returns the discovered role_id if a role was formed or updated,
        or None if the record was stored but no role yet (too few samples).
        """
        if observation is None or action is None:
            return None

        skey, etypes, rtypes = self.compute_structural_key_rich(observation)

        # Determine outcome valence
        if consequence.net > 0.5:
            valence = "POSITIVE"
        elif consequence.net < -0.5:
            valence = "NEGATIVE"
        else:
            valence = "NEUTRAL"

        record = RoleDiscoveryRecord(
            structural_key=skey,
            entity_types=etypes,
            relation_types=rtypes,
            action_name=action.name,
            universal_op=action.universal_op,
            domain=domain,
            outcome_net=consequence.net,
            outcome_valence=valence,
            concept_signals=dict(consequence.concept_signals),
            tick=tick,
        )

        self._records.append(record)
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records:]

        # Add to cluster
        cluster_key = (skey, valence)
        self._clusters[cluster_key].append(record)

        # Try to form/update a role from this cluster
        return self._update_role_for_cluster(cluster_key)

    def _update_role_for_cluster(self, cluster_key: Tuple[str, str]) -> Optional[str]:
        """Form or update a DiscoveredRole from a cluster of records."""
        records = self._clusters[cluster_key]
        if len(records) < self.min_cluster_size:
            return None

        skey, valence = cluster_key

        # Check if a role already exists for this cluster
        existing_role_id = None
        for rid, role in self._roles.items():
            if role.structural_key == skey and role.outcome_valence == valence:
                existing_role_id = rid
                break

        # Aggregate cluster statistics
        action_names: Set[str] = set()
        universal_ops: Set[str] = set()
        entity_types: Set[str] = set()
        relation_types: Set[str] = set()
        source_domains: Set[str] = set()
        outcome_concepts: Dict[str, float] = defaultdict(float)
        total_net = 0.0

        for rec in records:
            action_names.add(rec.action_name)
            universal_ops.add(rec.universal_op)
            entity_types.update(rec.entity_types)
            relation_types.update(rec.relation_types)
            source_domains.add(rec.domain)
            total_net += rec.outcome_net
            for concept, val in rec.concept_signals.items():
                outcome_concepts[concept] += val

        mean_outcome = total_net / len(records)
        # Confidence: how consistent is the valence?
        valence_matches = sum(
            1 for r in records
            if (r.outcome_valence == valence) or
               (valence == "POSITIVE" and r.outcome_net > 0) or
               (valence == "NEGATIVE" and r.outcome_net < 0)
        )
        confidence = valence_matches / len(records)

        # Normalize concept signals
        total_concept = sum(abs(v) for v in outcome_concepts.values())
        if total_concept > 0:
            outcome_concepts = {k: v / total_concept for k, v in outcome_concepts.items()}

        if existing_role_id is not None:
            # Update existing role
            role = self._roles[existing_role_id]
            role.action_names = action_names
            role.universal_ops = universal_ops
            role.entity_type_set = frozenset(entity_types)
            role.relation_type_set = frozenset(relation_types)
            role.mean_outcome = mean_outcome
            role.sample_count = len(records)
            role.confidence = confidence
            role.source_domains = source_domains
            role.outcome_concepts = dict(outcome_concepts)
            return existing_role_id
        else:
            # Create new role
            role_id = f"role_{self._next_role_id}"
            self._next_role_id += 1
            role = DiscoveredRole(
                role_id=role_id,
                structural_key=skey,
                outcome_valence=valence,
                action_names=action_names,
                universal_ops=universal_ops,
                entity_type_set=frozenset(entity_types),
                relation_type_set=frozenset(relation_types),
                mean_outcome=mean_outcome,
                sample_count=len(records),
                confidence=confidence,
                source_domains=source_domains,
                outcome_concepts=dict(outcome_concepts),
            )
            self._roles[role_id] = role
            return role_id

    def discover_roles(self) -> List[DiscoveredRole]:
        """Return all discovered roles sorted by confidence x sample_count."""
        return sorted(
            self._roles.values(),
            key=lambda r: r.confidence * r.sample_count,
            reverse=True,
        )

    def get_role(self, role_id: str) -> Optional[DiscoveredRole]:
        return self._roles.get(role_id)

    def find_matching_roles(
        self,
        observation: RealityGraph,
        min_confidence: float = 0.3,
    ) -> List[Tuple[DiscoveredRole, float]]:
        """Find roles whose structural key matches the observation.

        Returns list of (role, match_quality) tuples sorted by match quality.

        The match quality is based on:
        1. Exact structural key match (primary)
        2. Structural similarity for partial matches (secondary)

        This is how transfer happens: the agent encounters a new observation,
        finds roles with matching structural keys from OTHER domains, and
        uses those roles to bias action selection. No role labels needed.
        """
        if observation is None:
            return []

        obs_skey, obs_etypes, obs_rtypes = self.compute_structural_key_rich(observation)
        results: List[Tuple[DiscoveredRole, float]] = []

        for role in self._roles.values():
            if role.confidence < min_confidence:
                continue

            # Exact structural key match — strongest signal
            if role.structural_key == obs_skey:
                results.append((role, 1.0))
                continue

            # Partial structural match via type overlap
            etype_overlap = len(role.entity_type_set & obs_etypes) / max(
                len(role.entity_type_set | obs_etypes), 1
            )
            rtype_overlap = len(role.relation_type_set & obs_rtypes) / max(
                len(role.relation_type_set | obs_rtypes), 1
            )

            # Topology-independent structural similarity:
            # Compare entity/relation counts (anonymized)
            obs_etype_counts = defaultdict(int)
            for e in observation.entities():
                obs_etype_counts[e.etype] += 1
            obs_rtype_counts = defaultdict(int)
            for r in observation.relations():
                obs_rtype_counts[r.rtype] += 1

            # Build anonymized count vectors and compare
            obs_e_sig = sorted(obs_etype_counts.values(), reverse=True)
            obs_r_sig = sorted(obs_rtype_counts.values(), reverse=True)

            # For the role, we reconstruct from entity/relation type sets
            # (approximate: assume count 1 for each type if we don't have counts)
            role_e_sig = [1] * len(role.entity_type_set)
            role_r_sig = [1] * len(role.relation_type_set)

            # Shape similarity: compare the sorted count distributions
            e_shape_sim = self._distribution_similarity(obs_e_sig, role_e_sig)
            r_shape_sim = self._distribution_similarity(obs_r_sig, role_r_sig)

            # Combined similarity: structural shape + type overlap
            structural_sim = 0.4 * e_shape_sim + 0.4 * r_shape_sim + 0.1 * etype_overlap + 0.1 * rtype_overlap

            if structural_sim > 0.3:
                results.append((role, structural_sim))

        return sorted(results, key=lambda x: -x[1])

    def _distribution_similarity(self, a: List[int], b: List[int]) -> float:
        """Compare two sorted integer distributions.

        Uses a simple histogram intersection normalized by union.
        """
        if not a and not b:
            return 1.0
        if not a or not b:
            return 0.0

        # Pad shorter with zeros
        max_len = max(len(a), len(b))
        a_padded = a + [0] * (max_len - len(a))
        b_padded = b + [0] * (max_len - len(b))

        # Normalized histogram intersection
        intersection = sum(min(ai, bi) for ai, bi in zip(a_padded, b_padded))
        union = sum(max(ai, bi) for ai, bi in zip(a_padded, b_padded))

        return intersection / max(union, 1)

    def transfer_action_boosts(
        self,
        observation: RealityGraph,
        available_actions: List[Transformation],
        min_confidence: float = 0.3,
        min_match_quality: float = 0.3,
    ) -> Tuple[Dict[str, float], int]:
        """Compute action boosts based on discovered role transfer.

        This REPLACES the hand-coded role_compatibility + infer_action_role
        transfer mechanism. Instead of matching role labels, we:

        1. Find roles whose structural key matches the observation
        2. For positive-valence roles: boost actions that match the role's
           action patterns (universal_op overlap)
        3. For negative-valence roles: suppress actions that match
        4. Weight by match quality x role confidence

        No role labels are used. Transfer is purely structural.
        """
        boosts: Dict[str, float] = {a.name: 0.0 for a in available_actions}
        used = 0

        matching_roles = self.find_matching_roles(observation, min_confidence)
        if not matching_roles:
            return boosts, 0

        for role, match_quality in matching_roles:
            if match_quality < min_match_quality:
                continue

            used += 1
            strength = match_quality * role.confidence * min(1.0, abs(role.mean_outcome) / 3.0)

            for action in available_actions:
                # Match by universal_op overlap with role's known ops
                op_match = 1.0 if action.universal_op in role.universal_ops else 0.0
                # Match by action name overlap (same-domain transfer)
                name_match = 1.0 if action.name in role.action_names else 0.0
                # Combined match
                action_match = max(op_match, name_match * 0.7)

                if action_match < 0.1:
                    continue

                if role.outcome_valence == "POSITIVE":
                    boosts[action.name] += strength * action_match
                elif role.outcome_valence == "NEGATIVE":
                    boosts[action.name] -= strength * action_match

        return boosts, used

    def structural_compatibility(self, source_role: DiscoveredRole, target_role: DiscoveredRole) -> float:
        """Compute structural compatibility between two discovered roles.

        This REPLACES the hand-coded role_compatibility() function.

        Two roles are compatible if:
        1. They have the same or similar structural keys (topology match)
        2. They have the same outcome valence (both positive or both negative)
        3. They share universal_op patterns (action similarity)

        No role labels are consulted. Compatibility is derived from
        the structure of the experiences that formed each role.
        """
        # Exact structural key match
        if source_role.structural_key == target_role.structural_key:
            skey_match = 1.0
        else:
            # Partial: compare entity/relation type overlap
            etype_overlap = len(source_role.entity_type_set & target_role.entity_type_set) / max(
                len(source_role.entity_type_set | target_role.entity_type_set), 1
            )
            rtype_overlap = len(source_role.relation_type_set & target_role.relation_type_set) / max(
                len(source_role.relation_type_set | target_role.relation_type_set), 1
            )
            skey_match = 0.5 * etype_overlap + 0.5 * rtype_overlap

        # Valence alignment
        if source_role.outcome_valence == target_role.outcome_valence:
            valence_match = 1.0
        elif (source_role.outcome_valence == "POSITIVE" and target_role.outcome_valence == "NEUTRAL") or \
             (source_role.outcome_valence == "NEUTRAL" and target_role.outcome_valence == "POSITIVE"):
            valence_match = 0.5
        else:
            # Positive <-> Negative = anti-compatible
            valence_match = -0.5

        # Action overlap (universal_ops)
        if source_role.universal_ops and target_role.universal_ops:
            op_overlap = len(source_role.universal_ops & target_role.universal_ops) / max(
                len(source_role.universal_ops | target_role.universal_ops), 1
            )
        else:
            op_overlap = 0.0

        # Weighted combination
        return (
            self.structural_weight * skey_match +
            self.valence_weight * valence_match +
            self.concept_weight * op_overlap
        )

    def prune(self, min_confidence: float = 0.2, min_samples: int = 2):
        """Remove low-quality roles."""
        to_remove = [
            rid for rid, role in self._roles.items()
            if role.confidence < min_confidence or role.sample_count < min_samples
        ]
        for rid in to_remove:
            del self._roles[rid]

        # Prune clusters too
        to_prune = [
            key for key, records in self._clusters.items()
            if len(records) < min_samples
        ]
        for key in to_prune:
            del self._clusters[key]

    def to_dict(self) -> dict:
        return {
            "num_roles": len(self._roles),
            "num_records": len(self._records),
            "roles": [r.to_dict() for r in self.discover_roles()],
        }

    def summary(self) -> Dict[str, Any]:
        roles = self.discover_roles()
        return {
            "num_roles": len(roles),
            "num_records": len(self._records),
            "num_clusters": len(self._clusters),
            "top_roles": [r.to_dict() for r in roles[:5]],
        }
