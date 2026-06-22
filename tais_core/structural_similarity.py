"""
tais_core.structural_similarity
===============================

Structural similarity engine based on the Weisfeiler-Leman (WL) graph
kernel. This REPLACES the hand-coded role_compatibility() function in
memory.py and the surface-level type matching in analogize().

The WL kernel is a well-established method for measuring structural
similarity between graphs WITHOUT learning embeddings. It works by:

1. Assigning initial labels to nodes based on their type
2. Iteratively refining labels by aggregating neighbor labels
3. Comparing label histograms between two graphs
4. Similarity = dot product of histograms

This is O(V + E) per iteration, computationally cheap, and captures
multi-hop topology. It is exactly the "no gradient, no pretrained model"
approach the project claims to use — but currently doesn't.

Key property: WL similarity is INVARIANT to node/edge relabeling.
If you rename every entity and relation in a graph, WL similarity
doesn't change. This is what makes it suitable for genuine structural
transfer — it depends only on topology, not surface names.

References:
    - Weisfeiler, B. & Leman, A. (1968). Reduction of a graph to a
      canonical form and an algebra arising during this reduction.
    - Shervashidze, N. et al. (2011). Weisfeiler-Lehman graph kernels.
      JMLR 12:2539-2561.
"""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from .reality import Entity, GraphPattern, RealityGraph, Relation


# --- WL FEATURE EXTRACTION ----------------------------------------------------

def wl_relabeled_graph(
    graph: RealityGraph,
    iterations: int = 3,
    anonymize: bool = True,
) -> Dict[int, Counter]:
    """Compute Weisfeiler-Leman label histograms for a RealityGraph.

    Returns a dict mapping iteration -> label_histogram, where each
    histogram counts how many nodes have each label at that iteration.

    When anonymize=True (default), the initial labels are ANONYMIZED:
    entity types are replaced by positional indices sorted by frequency,
    and relation types are replaced similarly. This makes the WL kernel
    SURFACE-INVARIANT: two graphs with the same topology but different
    entity/relation names will produce the same histograms.

    When anonymize=False, the raw type names are used. This preserves
    surface similarity but breaks cross-domain transfer.

    The acid test requires anonymize=True: if you rename every entity
    and relation in a graph, WL similarity shouldn't change.
    """
    if not graph._entities:
        return {0: Counter()}

    # Iteration 0: initial labels
    if anonymize:
        # Anonymize entity types by frequency rank, breaking ties by
        # degree (structural role) instead of alphabetical type name.
        # This ensures surface-independence: two graphs with the same
        # topology but different type names get the same anonymization.
        etype_counts: Dict[str, int] = Counter(e.etype for e in graph.entities())

        # Compute average degree per type (for tie-breaking)
        degree_by_type: Dict[str, List[int]] = defaultdict(list)
        for entity in graph.entities():
            out_deg = len(list(graph.neighbors_out(entity.id)))
            in_deg = len(list(graph.neighbors_in(entity.id)))
            degree_by_type[entity.etype].append(out_deg + in_deg)

        avg_degree_by_type = {
            etype: sum(degs) / len(degs) for etype, degs in degree_by_type.items()
        }

        # Sort by (-count, -avg_degree) for structural tie-breaking
        sorted_etypes = sorted(
            etype_counts.items(),
            key=lambda x: (-x[1], -avg_degree_by_type.get(x[0], 0))
        )
        etype_to_idx = {etype: f"T{i}" for i, (etype, _) in enumerate(sorted_etypes)}

        # Anonymize relation types by frequency rank, breaking ties by
        # how often that relation type appears on high-degree vs low-degree entities
        rtype_counts: Dict[str, int] = Counter(r.rtype for r in graph.relations())

        # Compute average source degree per relation type (for tie-breaking)
        src_deg_by_rtype: Dict[str, List[int]] = defaultdict(list)
        for rel in graph.relations():
            src = graph.get_entity(rel.source)
            if src:
                src_deg = len(list(graph.neighbors_out(src.id))) + len(list(graph.neighbors_in(src.id)))
                src_deg_by_rtype[rel.rtype].append(src_deg)

        avg_src_deg_by_rtype = {
            rtype: sum(degs) / len(degs) for rtype, degs in src_deg_by_rtype.items()
        }

        sorted_rtypes = sorted(
            rtype_counts.items(),
            key=lambda x: (-x[1], -avg_src_deg_by_rtype.get(x[0], 0))
        )
        rtype_to_idx = {rtype: f"R{i}" for i, (rtype, _) in enumerate(sorted_rtypes)}

        labels: Dict[str, str] = {}
        for entity in graph.entities():
            labels[entity.id] = etype_to_idx.get(entity.etype, "T0")
    else:
        labels: Dict[str, str] = {}
        for entity in graph.entities():
            labels[entity.id] = entity.etype

    histograms: Dict[int, Counter] = {}
    histograms[0] = Counter(labels.values())

    for it in range(1, iterations + 1):
        new_labels: Dict[str, str] = {}
        for entity in graph.entities():
            eid = entity.id
            # Collect (neighbor_label, edge_direction_and_anon_type) pairs
            neighbor_labels: List[Tuple[str, str]] = []

            for rel, neighbor in graph.neighbors_out(eid):
                if anonymize:
                    edge_key = f"out:{rtype_to_idx.get(rel.rtype, 'R0')}"
                else:
                    edge_key = f"out:{rel.rtype}"
                neighbor_labels.append((labels.get(neighbor.id, ""), edge_key))
            for rel, neighbor in graph.neighbors_in(eid):
                if anonymize:
                    edge_key = f"in:{rtype_to_idx.get(rel.rtype, 'R0')}"
                else:
                    edge_key = f"in:{rel.rtype}"
                neighbor_labels.append((labels.get(neighbor.id, ""), edge_key))

            # Sort for determinism
            neighbor_labels.sort()

            # Create new label by hashing current label + sorted neighbor multiset
            payload = labels[eid] + "|" + "|".join(f"{nl}:{rt}" for nl, rt in neighbor_labels)
            new_labels[eid] = hashlib.md5(payload.encode()).hexdigest()[:12]

        labels = new_labels
        histograms[it] = Counter(labels.values())

    return histograms


def wl_pattern_histogram(
    pattern: GraphPattern,
    iterations: int = 3,
    anonymize: bool = True,
) -> Dict[int, Counter]:
    """Compute WL label histograms for a GraphPattern.

    Works the same as wl_relabeled_graph but on the pattern's
    entity/relation lists instead of a full RealityGraph.

    When anonymize=True, entity/relation types are replaced by frequency-rank
    indices, making this surface-invariant.
    """
    if not pattern.entities:
        return {0: Counter()}

    # Build adjacency from pattern relations
    adj_out: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    adj_in: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    for rel in pattern.relations:
        adj_out[rel.source].append((rel.target, rel.rtype))
        adj_in[rel.target].append((rel.source, rel.rtype))

    # Iteration 0: initial labels (anonymized if requested)
    if anonymize:
        etype_counts = Counter(e.etype for e in pattern.entities)

        # Tie-break by degree within the pattern
        degree_by_type: Dict[str, List[int]] = defaultdict(list)
        for entity in pattern.entities:
            out_deg = len(adj_out.get(entity.id, []))
            in_deg = len(adj_in.get(entity.id, []))
            degree_by_type[entity.etype].append(out_deg + in_deg)

        avg_degree_by_type = {
            etype: sum(degs) / len(degs) for etype, degs in degree_by_type.items()
        }

        sorted_etypes = sorted(
            etype_counts.items(),
            key=lambda x: (-x[1], -avg_degree_by_type.get(x[0], 0))
        )
        etype_to_idx = {etype: f"T{i}" for i, (etype, _) in enumerate(sorted_etypes)}

        rtype_counts = Counter(r.rtype for r in pattern.relations)

        # Tie-break by average source degree
        src_deg_by_rtype: Dict[str, List[int]] = defaultdict(list)
        for rel in pattern.relations:
            src = rel.source
            src_deg = len(adj_out.get(src, [])) + len(adj_in.get(src, []))
            src_deg_by_rtype[rel.rtype].append(src_deg)

        avg_src_deg_by_rtype = {
            rtype: sum(degs) / len(degs) for rtype, degs in src_deg_by_rtype.items()
        }

        sorted_rtypes = sorted(
            rtype_counts.items(),
            key=lambda x: (-x[1], -avg_src_deg_by_rtype.get(x[0], 0))
        )
        rtype_to_idx = {rtype: f"R{i}" for i, (rtype, _) in enumerate(sorted_rtypes)}

        labels: Dict[str, str] = {}
        for entity in pattern.entities:
            labels[entity.id] = etype_to_idx.get(entity.etype, "T0")
    else:
        labels: Dict[str, str] = {}
        for entity in pattern.entities:
            labels[entity.id] = entity.etype

    histograms: Dict[int, Counter] = {}
    histograms[0] = Counter(labels.values())

    entity_ids = {e.id for e in pattern.entities}

    for it in range(1, iterations + 1):
        new_labels: Dict[str, str] = {}
        for entity in pattern.entities:
            eid = entity.id
            neighbor_labels: List[Tuple[str, str]] = []

            for target, rtype in adj_out.get(eid, []):
                if target in entity_ids:
                    if anonymize:
                        edge_key = f"out:{rtype_to_idx.get(rtype, 'R0')}"
                    else:
                        edge_key = f"out:{rtype}"
                    neighbor_labels.append((labels.get(target, ""), edge_key))
            for source, rtype in adj_in.get(eid, []):
                if source in entity_ids:
                    if anonymize:
                        edge_key = f"in:{rtype_to_idx.get(rtype, 'R0')}"
                    else:
                        edge_key = f"in:{rtype}"
                    neighbor_labels.append((labels.get(source, ""), edge_key))

            neighbor_labels.sort()
            payload = labels[eid] + "|" + "|".join(f"{nl}:{rt}" for nl, rt in neighbor_labels)
            new_labels[eid] = hashlib.md5(payload.encode()).hexdigest()[:12]

        labels = new_labels
        histograms[it] = Counter(labels.values())

    return histograms


# --- WL KERNEL SIMILARITY -----------------------------------------------------

def wl_similarity(
    hist_a: Dict[int, Counter],
    hist_b: Dict[int, Counter],
    iterations: int = 3,
) -> float:
    """Compute WL kernel similarity between two sets of label histograms.

    The kernel is the sum of dot products of label histograms across
    all iterations. Normalized to [0, 1] by dividing by the geometric
    mean of the self-similarities.

    Returns a value in [0, 1] where:
    - 1.0 = identical topology
    - 0.0 = completely different topology
    """
    if not hist_a or not hist_b:
        return 0.0

    # Compute unnormalized kernel
    kernel = 0.0
    for it in range(iterations + 1):
        ha = hist_a.get(it, Counter())
        hb = hist_b.get(it, Counter())
        # Dot product of histograms
        common_keys = set(ha.keys()) | set(hb.keys())
        kernel += sum(ha.get(k, 0) * hb.get(k, 0) for k in common_keys)

    # Normalize by geometric mean of self-similarities
    self_a = sum(
        sum(c.get(k, 0) ** 2 for k in c)
        for it in range(iterations + 1)
        for c in [hist_a.get(it, Counter())]
    )
    self_b = sum(
        sum(c.get(k, 0) ** 2 for k in c)
        for it in range(iterations + 1)
        for c in [hist_b.get(it, Counter())]
    )

    norm = (self_a * self_b) ** 0.5
    if norm < 1e-9:
        return 0.0

    return min(1.0, kernel / norm)


# --- STRUCTURAL COMPATIBILITY ENGINE ------------------------------------------

class StructuralCompatibility:
    """Predicts transferability between patterns based on graph topology.

    This is the drop-in replacement for the hand-coded role_compatibility()
    function. Instead of matching role labels, it:

    1. Computes WL histograms for both patterns/observations
    2. Measures topological similarity via WL kernel
    3. Checks consequence direction alignment
    4. Returns a compatibility score in [-1, 1]

    Positive = transfer should help
    Negative = transfer should hurt (anti-compatible)
    Zero = no transfer signal
    """

    def __init__(self, wl_iterations: int = 3):
        self.wl_iterations = wl_iterations
        self._histogram_cache: Dict[str, Dict[int, Counter]] = {}

    def _get_histograms(self, graph: RealityGraph) -> Dict[int, Counter]:
        """Get WL histograms with caching."""
        # Use a lightweight cache key
        cache_key = f"{graph.domain}:{len(graph._entities)}:{len(graph._relations)}:{graph._version}"
        if cache_key not in self._histogram_cache:
            self._histogram_cache[cache_key] = wl_relabeled_graph(graph, self.wl_iterations)
            # Bound cache size
            if len(self._histogram_cache) > 500:
                keys = list(self._histogram_cache.keys())
                for k in keys[:100]:
                    del self._histogram_cache[k]
        return self._histogram_cache[cache_key]

    def compatibility_graphs(
        self,
        source: RealityGraph,
        target: RealityGraph,
        source_valence: str = "GOOD",
        target_valence: str = "GOOD",
    ) -> float:
        """Compute structural compatibility between two RealityGraphs.

        Parameters:
            source: Source domain observation
            target: Target domain observation
            source_valence: "GOOD", "BAD", "NEUTRAL" — outcome direction in source
            target_valence: Expected outcome direction in target

        Returns:
            Compatibility score in [-1, 1].
            Positive = transfer should help.
            Negative = transfer should hurt.
        """
        hist_source = self._get_histograms(source)
        hist_target = self._get_histograms(target)

        topo_sim = wl_similarity(hist_source, hist_target, self.wl_iterations)

        # Valence alignment
        if source_valence == target_valence:
            valence_factor = 1.0
        elif source_valence == "NEUTRAL" or target_valence == "NEUTRAL":
            valence_factor = 0.3
        else:
            # GOOD <-> BAD = anti-compatible
            valence_factor = -0.5

        return topo_sim * valence_factor

    def compatibility_patterns(
        self,
        source_pattern: GraphPattern,
        target_pattern: GraphPattern,
    ) -> float:
        """Compute structural compatibility between two GraphPatterns.

        Same logic as compatibility_graphs but for patterns.
        """
        hist_source = wl_pattern_histogram(source_pattern, self.wl_iterations)
        hist_target = wl_pattern_histogram(target_pattern, self.wl_iterations)

        topo_sim = wl_similarity(hist_source, hist_target, self.wl_iterations)

        # Valence alignment from consequence signatures
        src_val = source_pattern.consequence_signature or "NEUTRAL"
        tgt_val = target_pattern.consequence_signature or "NEUTRAL"

        if src_val == tgt_val:
            valence_factor = 1.0
        elif src_val == "NEUTRAL" or tgt_val == "NEUTRAL":
            valence_factor = 0.3
        else:
            valence_factor = -0.5

        return topo_sim * valence_factor

    def similarity(self, graph_a: RealityGraph, graph_b: RealityGraph) -> float:
        """Pure topological similarity between two graphs (no valence)."""
        hist_a = self._get_histograms(graph_a)
        hist_b = self._get_histograms(graph_b)
        return wl_similarity(hist_a, hist_b, self.wl_iterations)

    def find_analogy(
        self,
        source_pattern: GraphPattern,
        target_graph: RealityGraph,
        min_similarity: float = 0.3,
    ) -> Optional[Dict[str, Any]]:
        """Find a structural analogy between a source pattern and target graph.

        This REPLACES the surface-level analogize() method in RealityGraph.
        Instead of matching entity type names, it uses WL kernel similarity
        to determine whether the target graph's topology matches the pattern.

        Returns:
            None if no good analogy found, or a dict with:
            - similarity: WL similarity score
            - source_pattern: the pattern
            - mapping_hint: suggested entity mapping based on topology
        """
        hist_pattern = wl_pattern_histogram(source_pattern, self.wl_iterations)
        hist_target = self._get_histograms(target_graph)

        sim = wl_similarity(hist_pattern, hist_target, self.wl_iterations)

        if sim < min_similarity:
            return None

        # Build a topology-based entity mapping
        mapping_hint: Dict[str, str] = {}
        pattern_labels: Dict[str, str] = {}
        target_labels: Dict[str, str] = {}

        p_adj_out: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        p_adj_in: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        for rel in source_pattern.relations:
            p_adj_out[rel.source].append((rel.target, rel.rtype))
            p_adj_in[rel.target].append((rel.source, rel.rtype))

        for entity in source_pattern.entities:
            eid = entity.id
            neighbor_labels: List[Tuple[str, str]] = []
            for target, rtype in p_adj_out.get(eid, []):
                neighbor_labels.append((entity.etype, f"out:{rtype}"))
            for source, rtype in p_adj_in.get(eid, []):
                neighbor_labels.append((entity.etype, f"in:{rtype}"))
            neighbor_labels.sort()
            payload = entity.etype + "|" + "|".join(f"{nl}:{rt}" for nl, rt in neighbor_labels)
            pattern_labels[eid] = hashlib.md5(payload.encode()).hexdigest()[:12]

        target_labels = _compute_node_labels(target_graph, self.wl_iterations)

        # Match by label
        used_targets: Set[str] = set()
        for peid, plabel in pattern_labels.items():
            for teid, tlabel in target_labels.items():
                if tlabel == plabel and teid not in used_targets:
                    mapping_hint[peid] = teid
                    used_targets.add(teid)
                    break

        return {
            "similarity": sim,
            "source_pattern": source_pattern,
            "mapping_hint": mapping_hint,
        }


def _compute_node_labels(graph: RealityGraph, iterations: int) -> Dict[str, str]:
    """Compute per-node WL labels for entity mapping."""
    if not graph._entities:
        return {}

    labels: Dict[str, str] = {}
    for entity in graph.entities():
        labels[entity.id] = entity.etype

    for it in range(1, iterations + 1):
        new_labels: Dict[str, str] = {}
        for entity in graph.entities():
            eid = entity.id
            neighbor_labels: List[Tuple[str, str]] = []
            for rel, neighbor in graph.neighbors_out(eid):
                neighbor_labels.append((labels.get(neighbor.id, ""), f"out:{rel.rtype}"))
            for rel, neighbor in graph.neighbors_in(eid):
                neighbor_labels.append((labels.get(neighbor.id, ""), f"in:{rel.rtype}"))
            neighbor_labels.sort()
            payload = labels[eid] + "|" + "|".join(f"{nl}:{rt}" for nl, rt in neighbor_labels)
            new_labels[eid] = hashlib.md5(payload.encode()).hexdigest()[:12]
        labels = new_labels

    return labels
