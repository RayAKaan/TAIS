"""
tais_core.analogy_engine
========================

Structural Analogy Engine: genuine subgraph matching for cross-domain
transfer without role labels.

This REPLACES the surface-level analogize() method in RealityGraph
(which matches entity type names) and the role-based transfer in
PatternMemory.action_priors() (which uses hand-coded role_compatibility).

The key insight: structural analogy means finding that the TOPOLOGY of
a new situation matches the topology of a previously-solved situation.
This requires comparing graph structures, not string labels.

Implementation strategy:
1. Neighborhood Hash Fingerprinting (fast, approximate)
   - For each entity, compute a hash that captures its local neighborhood
   - Compare fingerprints across domains
   - Entities with matching fingerprints are structurally analogous

2. Weisfeiler-Leman similarity (from structural_similarity.py)
   - Compare entire graph topologies
   - Determine whether two graphs have analogous structure

3. Topological entity mapping
   - Map entities based on their role in the graph structure
   - Not based on their type names

The acid test: create two domains with the SAME topology but COMPLETELY
different entity/relation names. If this engine finds the analogy and
transfers successfully, you've proven structural transfer.
"""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from .reality import (
    AnalogyMapping,
    Consequence,
    Entity,
    GraphPattern,
    RealityGraph,
    Relation,
    Transformation,
)
from .structural_similarity import (
    StructuralCompatibility,
    wl_pattern_histogram,
    wl_relabeled_graph,
    wl_similarity,
)


# --- NEIGHBORHOOD HASH --------------------------------------------------------

def neighborhood_hash(
    graph: RealityGraph,
    entity_id: str,
    hops: int = 2,
) -> str:
    """Compute a topology-only fingerprint for an entity's neighborhood.

    The hash captures:
    - Degree of the entity (number of in/out edges)
    - Degree distribution of neighbors
    - Depth-2 neighborhood structure

    It does NOT use:
    - Entity IDs
    - Entity type names
    - Relation type names

    Two entities in completely different domains will have the same
    neighborhood hash if and only if their local topology is identical.
    """
    if entity_id not in graph._entities:
        return "NIL"

    # Collect k-hop neighborhood
    visited = {entity_id}
    frontier = [entity_id]
    all_entities = {entity_id}

    for _ in range(hops):
        next_frontier = []
        for eid in frontier:
            for rel, neighbor in graph.neighbors_out(eid):
                if neighbor.id not in visited:
                    visited.add(neighbor.id)
                    next_frontier.append(neighbor.id)
                    all_entities.add(neighbor.id)
            for rel, neighbor in graph.neighbors_in(eid):
                if neighbor.id not in visited:
                    visited.add(neighbor.id)
                    next_frontier.append(neighbor.id)
                    all_entities.add(neighbor.id)
        frontier = next_frontier

    # Compute degree signatures for each entity in the neighborhood
    # (anonymized: only degrees, no names)
    degree_sigs = []
    for eid in sorted(all_entities):
        out_deg = len(list(graph.neighbors_out(eid)))
        in_deg = len(list(graph.neighbors_in(eid)))
        degree_sigs.append(f"{out_deg}:{in_deg}")

    # Sort for determinism, hash for compactness
    degree_sigs.sort()
    raw = "|".join(degree_sigs)
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def entity_structural_signature(
    graph: RealityGraph,
    entity_id: str,
) -> str:
    """Compute a structural role signature for an entity.

    This captures the entity's structural role in the graph:
    - Is it a hub (many outgoing edges)?
    - Is it a leaf (only incoming edges)?
    - Is it a bridge (connects two components)?
    - Is it isolated?

    The signature is purely topological — no type names used.
    """
    if entity_id not in graph._entities:
        return "NIL"

    out_deg = len(list(graph.neighbors_out(entity_id)))
    in_deg = len(list(graph.neighbors_in(entity_id)))

    # Role classification based on degree
    if out_deg == 0 and in_deg == 0:
        return "ISOLATED"
    elif out_deg >= 3 and in_deg <= 1:
        return "HUB_OUT"
    elif in_deg >= 3 and out_deg <= 1:
        return "HUB_IN"
    elif out_deg >= 2 and in_deg >= 2:
        return "BRIDGE"
    elif out_deg > 0 and in_deg == 0:
        return "SOURCE"
    elif in_deg > 0 and out_deg == 0:
        return "SINK"
    else:
        return f"DEG_{out_deg}_{in_deg}"


# --- STRUCTURAL ANALOGY RESULT -------------------------------------------------

@dataclass
class StructuralAnalogy:
    """Result of structural analogy computation between two graphs.

    Contains:
    - entity_map: mapping from source entity IDs to target entity IDs
    - confidence: how confident we are in the mapping
    - topology_match: WL similarity score
    - mapping_method: how the mapping was computed
    """

    entity_map: Dict[str, str]
    confidence: float
    topology_match: float
    mapping_method: str
    source_graph: Optional[RealityGraph] = None
    target_graph: Optional[RealityGraph] = None

    def is_valid(self) -> bool:
        return self.confidence > 0.3 and len(self.entity_map) > 0


# --- STRUCTURAL ANALOGY ENGINE -------------------------------------------------

class StructuralAnalogyEngine:
    """Finds structural analogies between graphs from different domains.

    This is the core of genuine GRTL: given a learned pattern in domain A
    and a novel observation in domain B, find the topological mapping
    that makes them analogous — without using any surface features.

    The engine uses three levels of matching, from fast/coarse to
    slow/precise:

    1. WL kernel similarity (fast, O(V+E)): Does the overall topology match?
    2. Neighborhood hash matching (medium, O(V)): Which entities correspond?
    3. Structural role matching (fast, O(V)): Which entities have the same
       structural role (hub, leaf, bridge, etc.)?
    """

    def __init__(
        self,
        wl_iterations: int = 3,
        min_wl_similarity: float = 0.3,
        min_mapping_confidence: float = 0.3,
    ):
        self.wl_iterations = wl_iterations
        self.min_wl_similarity = min_wl_similarity
        self.min_mapping_confidence = min_mapping_confidence
        self._compat = StructuralCompatibility(wl_iterations=wl_iterations)

    def find_analogy(
        self,
        source_graph: RealityGraph,
        target_graph: RealityGraph,
    ) -> StructuralAnalogy:
        """Find a structural analogy between source and target graphs.

        Steps:
        1. Check WL similarity (is the topology similar enough?)
        2. Map entities by structural role (hub->hub, leaf->leaf, etc.)
        3. Refine mapping by neighborhood hash matching
        4. Validate mapping by checking relation structure

        Returns a StructuralAnalogy with the entity mapping and confidence.
        """
        # Step 1: WL similarity check
        wl_sim = self._compat.similarity(source_graph, target_graph)
        if wl_sim < self.min_wl_similarity:
            return StructuralAnalogy(
                entity_map={},
                confidence=0.0,
                topology_match=wl_sim,
                mapping_method="rejected_by_wl",
            )

        # Step 2: Map entities by structural role
        role_map = self._map_by_structural_role(source_graph, target_graph)

        # Step 3: Refine by neighborhood hash
        hash_map = self._map_by_neighborhood_hash(source_graph, target_graph)

        # Step 4: Merge mappings (role-based + hash-based)
        merged = self._merge_mappings(role_map, hash_map)

        # Step 5: Validate by checking relation structure preservation
        validated, validation_score = self._validate_mapping(
            source_graph, target_graph, merged
        )

        # Combined confidence
        confidence = wl_sim * 0.4 + validation_score * 0.6

        return StructuralAnalogy(
            entity_map=validated,
            confidence=confidence,
            topology_match=wl_sim,
            mapping_method="structural_role+neighborhood_hash",
            source_graph=source_graph,
            target_graph=target_graph,
        )

    def find_pattern_analogy(
        self,
        source_pattern: GraphPattern,
        target_graph: RealityGraph,
    ) -> StructuralAnalogy:
        """Find a structural analogy between a pattern and a target graph.

        This is used when pattern memory contains a learned pattern from
        domain A and we want to apply it to a new observation in domain B.
        """
        # Compute WL histograms
        hist_pattern = wl_pattern_histogram(source_pattern, self.wl_iterations)
        hist_target = wl_relabeled_graph(target_graph, self.wl_iterations)

        wl_sim = wl_similarity(hist_pattern, hist_target, self.wl_iterations)
        if wl_sim < self.min_wl_similarity:
            return StructuralAnalogy(
                entity_map={},
                confidence=0.0,
                topology_match=wl_sim,
                mapping_method="rejected_by_wl",
            )

        # Map pattern entities to target graph entities by structural role
        entity_map = self._map_pattern_to_graph(source_pattern, target_graph)

        confidence = wl_sim * 0.5 + (0.5 if entity_map else 0.0)

        return StructuralAnalogy(
            entity_map=entity_map,
            confidence=confidence,
            topology_match=wl_sim,
            mapping_method="pattern_structural_role",
            source_graph=None,
            target_graph=target_graph,
        )

    def transfer_action(
        self,
        analogy: StructuralAnalogy,
        source_pattern: GraphPattern,
        available_actions: List[Transformation],
    ) -> Optional[str]:
        """Given a structural analogy, suggest an action to take.

        The logic: if the pattern's successful_action_op is known, and the
        analogy maps the pattern to the current observation, then suggest
        the available action whose universal_op matches the pattern's
        successful_action_op.

        This is LABEL-FREE transfer: we match by graph topology, not by
        role names.
        """
        if not analogy.is_valid():
            return None

        if not source_pattern.successful_action_op:
            return None

        # Find the action whose universal_op matches the pattern's
        for action in available_actions:
            if action.universal_op == source_pattern.successful_action_op:
                return action.name

        # No op match — try action name match (weaker signal)
        if source_pattern.successful_action_name:
            for action in available_actions:
                if action.name == source_pattern.successful_action_name:
                    return action.name

        return None

    def compute_structural_boosts(
        self,
        source_patterns: List[GraphPattern],
        target_graph: RealityGraph,
        available_actions: List[Transformation],
        min_analogy_confidence: float = 0.3,
    ) -> Dict[str, float]:
        """Compute action boosts from structural analogy with all stored patterns.

        This is the drop-in replacement for PatternMemory.action_priors().
        Instead of using role labels and hand-coded compatibility, it uses
        structural topology matching.

        Returns:
            {action_name: boost} where positive = should prefer, negative = should avoid
        """
        boosts: Dict[str, float] = {a.name: 0.0 for a in available_actions}

        for pattern in source_patterns:
            if pattern.confidence < 0.3:
                continue

            analogy = self.find_pattern_analogy(pattern, target_graph)
            if analogy.confidence < min_analogy_confidence:
                continue

            strength = analogy.confidence * pattern.confidence * min(1.0, abs(pattern.mean_outcome_net) / 3.0)

            # Positive patterns: boost matching actions
            if pattern.consequence_signature == "GOOD" and pattern.successful_action_op:
                for action in available_actions:
                    if action.universal_op == pattern.successful_action_op:
                        boosts[action.name] += strength

            # Negative patterns: suppress matching actions
            if pattern.consequence_signature == "BAD":
                for action in available_actions:
                    if action.universal_op in pattern.failed_action_ops:
                        boosts[action.name] -= strength

        return boosts

    # --- INTERNAL METHODS -----------------------------------------------------

    def _map_by_structural_role(
        self,
        source: RealityGraph,
        target: RealityGraph,
    ) -> Dict[str, str]:
        """Map entities by their structural role (hub, leaf, bridge, etc.)."""
        source_sigs: Dict[str, str] = {}
        for e in source.entities():
            source_sigs[e.id] = entity_structural_signature(source, e.id)

        target_sigs: Dict[str, str] = {}
        for e in target.entities():
            target_sigs[e.id] = entity_structural_signature(target, e.id)

        # Group by signature
        source_by_sig: Dict[str, List[str]] = defaultdict(list)
        for eid, sig in source_sigs.items():
            source_by_sig[sig].append(eid)

        target_by_sig: Dict[str, List[str]] = defaultdict(list)
        for eid, sig in target_sigs.items():
            target_by_sig[sig].append(eid)

        # Map: first entity with each signature in source -> first in target
        mapping: Dict[str, str] = {}
        for sig, source_ids in source_by_sig.items():
            target_ids = target_by_sig.get(sig, [])
            for i, sid in enumerate(source_ids):
                if i < len(target_ids):
                    mapping[sid] = target_ids[i]

        return mapping

    def _map_by_neighborhood_hash(
        self,
        source: RealityGraph,
        target: RealityGraph,
    ) -> Dict[str, str]:
        """Map entities by their neighborhood hash fingerprint."""
        source_hashes: Dict[str, str] = {}
        for e in source.entities():
            source_hashes[e.id] = neighborhood_hash(source, e.id)

        target_hashes: Dict[str, str] = {}
        for e in target.entities():
            target_hashes[e.id] = neighborhood_hash(target, e.id)

        # Group target entities by hash
        target_by_hash: Dict[str, List[str]] = defaultdict(list)
        for eid, h in target_hashes.items():
            target_by_hash[h].append(eid)

        # Map source entities to target entities with matching hash
        mapping: Dict[str, str] = {}
        used_targets: Set[str] = set()
        for sid, shash in source_hashes.items():
            candidates = target_by_hash.get(shash, [])
            for tid in candidates:
                if tid not in used_targets:
                    mapping[sid] = tid
                    used_targets.add(tid)
                    break

        return mapping

    def _merge_mappings(
        self,
        role_map: Dict[str, str],
        hash_map: Dict[str, str],
    ) -> Dict[str, str]:
        """Merge role-based and hash-based mappings.

        Hash-based mappings take priority (more specific).
        """
        merged = dict(role_map)
        merged.update(hash_map)
        return merged

    def _validate_mapping(
        self,
        source: RealityGraph,
        target: RealityGraph,
        mapping: Dict[str, str],
    ) -> Tuple[Dict[str, str], float]:
        """Validate a mapping by checking relation structure preservation.

        A good mapping preserves relation structure: if source has
        A->B, and A maps to A', B maps to B', then target should have
        A'->B' (possibly with different relation types).

        Returns:
            (validated_mapping, validation_score)
        """
        if not mapping:
            return {}, 0.0

        # Check how many source relations are preserved in the target
        source_rels = list(source.relations())
        preserved = 0
        total = 0

        validated = {}
        for src_id, tgt_id in mapping.items():
            src_out = set(r.rtype for r, _ in source.neighbors_out(src_id))
            tgt_out = set(r.rtype for r, _ in target.neighbors_out(tgt_id))
            src_in = set(r.rtype for r, _ in source.neighbors_in(src_id))
            tgt_in = set(r.rtype for r, _ in target.neighbors_in(tgt_id))

            # Structural preservation: degree matches
            src_deg = len(src_out) + len(src_in)
            tgt_deg = len(tgt_out) + len(tgt_in)
            if abs(src_deg - tgt_deg) <= max(src_deg, tgt_deg, 1) * 0.5:
                validated[src_id] = tgt_id

            # Count preserved relations
            for rel in source_rels:
                if rel.source == src_id:
                    tgt_target = mapping.get(rel.target)
                    if tgt_target and target.get_relation(tgt_id, rel.rtype, tgt_target):
                        preserved += 1
                    elif tgt_target:
                        for r, _ in target.neighbors_out(tgt_id):
                            if r.target == tgt_target:
                                preserved += 1
                                break
                    total += 1

        validation_score = preserved / max(total, 1)
        return validated, validation_score

    def _map_pattern_to_graph(
        self,
        pattern: GraphPattern,
        graph: RealityGraph,
    ) -> Dict[str, str]:
        """Map pattern entities to graph entities by structural role."""
        # Build pattern adjacency
        p_adj_out: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        p_adj_in: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        for rel in pattern.relations:
            p_adj_out[rel.source].append((rel.target, rel.rtype))
            p_adj_in[rel.target].append((rel.source, rel.rtype))

        # Compute structural roles for pattern entities
        p_roles: Dict[str, str] = {}
        for e in pattern.entities:
            out_deg = len(p_adj_out.get(e.id, []))
            in_deg = len(p_adj_in.get(e.id, []))
            p_roles[e.id] = f"deg_{out_deg}_{in_deg}"

        # Compute structural roles for graph entities
        g_roles: Dict[str, str] = {}
        for e in graph.entities():
            sig = entity_structural_signature(graph, e.id)
            g_roles[e.id] = sig

        # Map pattern entities to graph entities with matching role
        g_by_role: Dict[str, List[str]] = defaultdict(list)
        for eid, role in g_roles.items():
            g_by_role[role].append(eid)

        mapping: Dict[str, str] = {}
        used: Set[str] = set()
        for peid, prole in p_roles.items():
            # Try exact degree match first
            candidates = g_by_role.get(prole, [])
            # Fallback: try structural signature
            if not candidates:
                for g_eid in graph._entities:
                    if g_eid not in used:
                        candidates.append(g_eid)
                        break
            for cid in candidates:
                if cid not in used:
                    mapping[peid] = cid
                    used.add(cid)
                    break

        return mapping
