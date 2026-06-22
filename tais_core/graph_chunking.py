"""
tais_core.graph_chunking
========================

AGI Roadmap Step 1: Hierarchical chunking for large-graph transfer.

Chunking compresses structurally redundant subgraphs into abstract
nodes, enabling the mote to transfer knowledge across large graphs
that would be too expensive to compare at full resolution.

Three components:
    1. CommunityDetection — modularity-based graph partitioning
    2. HierarchicalCompressor — multi-level compression
    3. ChunkedWLSimilarity — WL kernel on compressed graphs
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from .reality import Entity, GraphPattern, RealityGraph, Relation
from .structural_similarity import wl_relabeled_graph, wl_similarity


# ─── COMMUNITY DETECTION ─────────────────────────────────────────────────────


@dataclass
class Community:
    """A detected community (chunk) in a RealityGraph."""

    id: str
    entity_ids: Set[str]
    internal_relations: List[Relation]
    bridge_relations: List[Relation]
    density: float = 0.0
    modularity_contribution: float = 0.0


class CommunityDetection:
    """Modularity-based community detection for RealityGraphs.

    Uses a greedy agglomerative algorithm (Clauset-Newman-Moore style)
    to find communities that maximize modularity. This is O(V log² V)
    for sparse graphs.

    The communities form the chunks for hierarchical compression.
    """

    def __init__(self, resolution: float = 1.0, min_community_size: int = 3):
        self.resolution = resolution
        self.min_community_size = min_community_size

    def detect(self, graph: RealityGraph) -> List[Community]:
        """Partition graph into communities. Returns list of Community objects."""
        if len(graph._entities) == 0:
            return []

        n_entities = len(graph._entities)
        entity_ids = list(graph.entities())
        entity_id_set = {e.id for e in entity_ids}

        # Build adjacency
        adj: Dict[str, Set[str]] = defaultdict(set)
        edge_count = 0
        for e in entity_ids:
            for rel, neighbor in graph.neighbors_out(e.id):
                if neighbor.id in entity_id_set:
                    adj[e.id].add(neighbor.id)
                    adj[neighbor.id].add(e.id)
                    edge_count += 1

        m = edge_count  # total edges (undirected)

        if m == 0:
            # Fallback: each entity is its own community (filtered by min size)
            result = []
            for e in entity_ids:
                if 1 >= self.min_community_size:
                    result.append(
                        Community(
                            id=f"comm_{e.id}",
                            entity_ids={e.id},
                            internal_relations=[],
                            bridge_relations=[],
                            density=0.0,
                            modularity_contribution=0.0,
                        )
                    )
            return result

        # Initialize: each node in its own community
        community_of: Dict[str, int] = {}
        members: Dict[int, Set[str]] = {}
        for i, e in enumerate(entity_ids):
            community_of[e.id] = i
            members[i] = {e.id}

        # Degrees
        degree: Dict[str, int] = {e.id: len(adj[e.id]) for e in entity_ids}

        next_community_id = n_entities

        # Greedy merging
        improved = True
        while improved:
            improved = False
            best_delta_q = 0.0
            best_merge: Optional[Tuple[int, int]] = None

            # Check all pairs of communities that share an edge
            comm_pairs: Set[Tuple[int, int]] = set()
            for e in entity_ids:
                c1 = community_of[e.id]
                for nb in adj[e.id]:
                    if nb in community_of:
                        c2 = community_of[nb]
                        if c1 != c2:
                            comm_pairs.add((min(c1, c2), max(c1, c2)))

            for c1, c2 in comm_pairs:
                delta_q = self._modularity_delta(
                    c1, c2, community_of, members, degree, adj, m
                )
                if delta_q > best_delta_q:
                    best_delta_q = delta_q
                    best_merge = (c1, c2)

            if best_merge is not None and best_delta_q > 1e-6:
                c1, c2 = best_merge
                # Merge c2 into c1
                for eid in members[c2]:
                    community_of[eid] = c1
                    members[c1].add(eid)
                del members[c2]
                next_community_id += 1
                improved = True

        # Build Community objects
        communities: List[Community] = []
        for cid, member_set in members.items():
            if len(member_set) < self.min_community_size:
                continue

            internal_rels = []
            bridge_rels = []
            all_rels = list(graph.relations())

            for rel in all_rels:
                src_in = rel.source in member_set
                tgt_in = rel.target in member_set
                if src_in and tgt_in:
                    internal_rels.append(rel)
                elif src_in or tgt_in:
                    bridge_rels.append(rel)

            # Density: internal edges / possible internal edges
            n = len(member_set)
            density = (2 * len(internal_rels)) / (n * (n - 1)) if n > 1 else 0.0

            # Modularity contribution
            q_contrib = self._community_modularity_contribution(
                member_set, degree, adj, m
            )

            communities.append(
                Community(
                    id=f"comm_{cid}",
                    entity_ids=member_set,
                    internal_relations=internal_rels,
                    bridge_relations=bridge_rels,
                    density=density,
                    modularity_contribution=q_contrib,
                )
            )

        return communities

    def _modularity_delta(
        self,
        c1: int,
        c2: int,
        community_of: Dict[str, int],
        members: Dict[int, Set[str]],
        degree: Dict[str, int],
        adj: Dict[str, Set[str]],
        m: int,
    ) -> float:
        """Compute ΔQ for merging communities c1 and c2."""
        if m == 0:
            return 0.0

        # Sum of degrees in each community
        sum_deg_c1 = sum(degree[eid] for eid in members[c1])
        sum_deg_c2 = sum(degree[eid] for eid in members[c2])

        # Count edges between c1 and c2
        edges_between = 0
        for eid in members[c1]:
            for nb in adj[eid]:
                if nb in community_of and community_of[nb] == c2:
                    edges_between += 1

        res = self.resolution
        delta = (edges_between / m) - res * (sum_deg_c1 * sum_deg_c2) / (2 * m * m)
        return delta

    def _community_modularity_contribution(
        self,
        member_set: Set[str],
        degree: Dict[str, int],
        adj: Dict[str, Set[str]],
        m: int,
    ) -> float:
        """Compute the modularity contribution of a single community."""
        if m == 0:
            return 0.0

        sum_deg = sum(degree[eid] for eid in member_set)
        internal_edges = 0
        for eid in member_set:
            for nb in adj[eid]:
                if nb in member_set:
                    internal_edges += 1

        # Each undirected edge counted twice
        internal_edges //= 2

        res = self.resolution
        return (internal_edges / m) - res * (sum_deg / (2 * m)) ** 2


# ─── HIERARCHICAL COMPRESSION ────────────────────────────────────────────────


@dataclass
class CompressedGraph:
    """A hierarchically compressed RealityGraph.

    Each level compresses communities into abstract nodes, preserving
    bridge relations between communities.

    level_0: Original graph
    level_1: Communities compressed to abstract nodes
    level_2: Meta-communities compressed further (optional)
    """

    levels: Dict[int, "Level"]
    communities_by_level: Dict[int, List[Community]]
    compression_ratio: float = 1.0


@dataclass
class Level:
    """A single level in the compressed graph hierarchy."""

    entities: List[Entity]
    relations: List[Relation]
    level: int
    n_original_nodes: int = 0

    def to_graph(self, domain: str = "compressed") -> RealityGraph:
        g = RealityGraph(domain, f"level_{self.level}")
        for e in self.entities:
            g.add_entity(e)
        for r in self.relations:
            g.add_relation(r)
        return g


class HierarchicalCompressor:
    """Compress RealityGraphs by merging community chunks into abstract nodes.

    Each community becomes a single abstract entity whose type encodes
    the community's structural profile. Bridge relations between communities
    are preserved at the abstract level.
    """

    def __init__(self, community_detector: CommunityDetection = None):
        self.detector = community_detector or CommunityDetection()

    def compress(
        self,
        graph: RealityGraph,
        max_levels: int = 3,
    ) -> CompressedGraph:
        """Compress graph into a hierarchy of compressed levels."""
        levels: Dict[int, Level] = {}
        communities_by_level: Dict[int, List[Community]] = {}

        # Level 0: original
        original_entities = list(graph.entities())
        original_relations = list(graph.relations())
        levels[0] = Level(
            entities=original_entities,
            relations=original_relations,
            level=0,
            n_original_nodes=len(original_entities),
        )

        current_graph = graph
        for level in range(1, max_levels + 1):
            communities = self.detector.detect(current_graph)
            if not communities:
                break

            communities_by_level[level] = communities

            compressed_entities, compressed_relations = self._compress_level(
                current_graph, communities
            )

            levels[level] = Level(
                entities=compressed_entities,
                relations=compressed_relations,
                level=level,
                n_original_nodes=len(levels[0].entities),
            )

            # Build next iteration graph
            current_graph = RealityGraph(
                graph.domain, f"compressed_l{level}"
            )
            for e in compressed_entities:
                current_graph.add_entity(e)
            for r in compressed_relations:
                current_graph.add_relation(r)

            # Stop if no meaningful compression
            if len(compressed_entities) >= len(levels[level - 1].entities) * 0.9:
                break

        n0 = len(original_entities)
        n_last = len(levels[max(levels.keys())].entities) if levels else n0
        compression_ratio = n_last / n0 if n0 > 0 else 1.0

        return CompressedGraph(
            levels=levels,
            communities_by_level=communities_by_level,
            compression_ratio=compression_ratio,
        )

    def _compress_level(
        self,
        graph: RealityGraph,
        communities: List[Community],
    ) -> Tuple[List[Entity], List[Relation]]:
        """Compress one level: communities -> abstract nodes + bridge relations."""
        # Build community membership lookup
        entity_to_community: Dict[str, Community] = {}
        for comm in communities:
            for eid in comm.entity_ids:
                entity_to_community[eid] = comm

        # Create abstract entities for each community
        compressed_entities: Dict[str, Entity] = {}
        for comm in communities:
            # Entity type encodes community profile
            internal_types = Counter(
                graph.get_entity(eid).etype
                for eid in comm.entity_ids
                if graph.get_entity(eid)
            )
            type_signature = "_".join(
                f"{t}{c}" for t, c in internal_types.most_common(3)
            )
            abstract_etype = f"CHUNK_{type_signature}" if type_signature else "CHUNK"

            compressed_entities[comm.id] = Entity(
                id=comm.id,
                etype=abstract_etype,
                properties={
                    "n_entities": len(comm.entity_ids),
                    "density": round(comm.density, 3),
                    "modularity_q": round(comm.modularity_contribution, 4),
                    "member_ids": list(comm.entity_ids),
                },
            )

        # Bridge relations between communities
        compressed_relations: List[Relation] = []
        seen_relations: Set[Tuple[str, str, str]] = set()
        for comm in communities:
            for rel in comm.bridge_relations:
                src_comm = entity_to_community.get(rel.source)
                tgt_comm = entity_to_community.get(rel.target)
                if src_comm and tgt_comm and src_comm.id != tgt_comm.id:
                    key = (src_comm.id, rel.rtype, tgt_comm.id)
                    if key not in seen_relations:
                        seen_relations.add(key)
                        compressed_relations.append(
                            Relation(
                                source=src_comm.id,
                                rtype=rel.rtype,
                                target=tgt_comm.id,
                                properties={"bridge_count": 1},
                            )
                        )

        # Handle entities not in any community
        all_community_entities: Set[str] = set()
        for comm in communities:
            all_community_entities.update(comm.entity_ids)
        for e in graph.entities():
            if e.id not in all_community_entities:
                compressed_entities[e.id] = e

        return list(compressed_entities.values()), compressed_relations

    def decompress_chunk(
        self,
        compressed_graph: CompressedGraph,
        chunk_id: str,
        level: int = 1,
    ) -> RealityGraph:
        """Decompress a single chunk back to its original subgraph."""
        communities = compressed_graph.communities_by_level.get(level, [])
        target_comm = None
        for comm in communities:
            if comm.id == chunk_id:
                target_comm = comm
                break

        if target_comm is None:
            original_level = compressed_graph.levels.get(0)
            if original_level is None:
                return RealityGraph("empty", "empty")
            g = RealityGraph("decompressed", chunk_id)
            for e in original_level.entities:
                if e.id in chunk_id or True:
                    g.add_entity(e)
            # Try to find the original subgraph
            entity_set = {chunk_id} if chunk_id.startswith("e_") else set()
            for e in original_level.entities:
                nid = e.id
                for comm2 in communities:
                    if nid in comm2.entity_ids:
                        entity_set.add(nid)
            for e in original_level.entities:
                if e.id in entity_set:
                    g.add_entity(e)
            for r in original_level.relations:
                if r.source in entity_set and r.target in entity_set:
                    g.add_relation(r)
            return g

        # Found the community
        original_level = compressed_graph.levels.get(0)
        if original_level is None:
            return RealityGraph("empty", "empty")

        g = RealityGraph("decompressed", chunk_id)
        entity_ids = target_comm.entity_ids
        entity_map: Dict[str, Entity] = {}
        for e in original_level.entities:
            if e.id in entity_ids:
                g.add_entity(e)
                entity_map[e.id] = e
        for r in original_level.relations:
            if r.source in entity_ids and r.target in entity_ids:
                g.add_relation(r)

        return g


# ─── CHUNKED WL SIMILARITY ───────────────────────────────────────────────────


class ChunkedWLSimilarity:
    """Compute structural similarity at the compressed chunk level.

    This enables transfer across very large graphs by comparing their
    compressed representations (community structures) rather than
    individual entities.
    """

    def __init__(self, wl_iterations: int = 3):
        self.wl_iterations = wl_iterations

    def chunk_similarity(
        self,
        compressed_a: CompressedGraph,
        compressed_b: CompressedGraph,
        level: int = 1,
    ) -> float:
        """Compute WL similarity between two compressed graphs at a given level."""
        graph_a = compressed_a.levels.get(level)
        graph_b = compressed_b.levels.get(level)

        if graph_a is None or graph_b is None:
            return 0.0

        g_a = graph_a.to_graph()
        g_b = graph_b.to_graph()

        hist_a = wl_relabeled_graph(g_a, self.wl_iterations)
        hist_b = wl_relabeled_graph(g_b, self.wl_iterations)

        return wl_similarity(hist_a, hist_b, self.wl_iterations)

    def community_profile_similarity(
        self,
        compressed_a: CompressedGraph,
        compressed_b: CompressedGraph,
        level: int = 1,
    ) -> float:
        """Compare community profiles (type distributions) between two compressions.

        This captures structural similarity at the chunk level, rather than
        individual entity topology.
        """
        comms_a = compressed_a.communities_by_level.get(level, [])
        comms_b = compressed_b.communities_by_level.get(level, [])

        if not comms_a or not comms_b:
            return 0.0

        # Build community type histograms
        hist_a: Counter[str] = Counter()
        for comm in comms_a:
            hist_a[f"density={comm.density:.2f}|q={comm.modularity_contribution:.2f}"] += 1

        hist_b: Counter[str] = Counter()
        for comm in comms_b:
            hist_b[f"density={comm.density:.2f}|q={comm.modularity_contribution:.2f}"] += 1

        # Compute histogram intersection similarity
        all_keys = set(hist_a.keys()) | set(hist_b.keys())
        intersection = sum(min(hist_a.get(k, 0), hist_b.get(k, 0)) for k in all_keys)
        max_possible = max(sum(hist_a.values()), sum(hist_b.values()))

        return intersection / max_possible if max_possible > 0 else 0.0

    def chunk_transfer_score(
        self,
        source_graph: RealityGraph,
        target_graph: RealityGraph,
    ) -> float:
        """Compute a single transferability score between two graphs.

        Combines chunk-level and community-profile similarity into a
        single score in [0, 1].
        """
        compressor = HierarchicalCompressor()
        compressed_s = compressor.compress(source_graph)
        compressed_t = compressor.compress(target_graph)

        chunk_sim = self.chunk_similarity(compressed_s, compressed_t)
        profile_sim = self.community_profile_similarity(compressed_s, compressed_t)

        return 0.6 * chunk_sim + 0.4 * profile_sim
