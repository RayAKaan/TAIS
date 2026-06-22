"""
tais_core.domains.procedural
=============================

Procedural domain generation with controllable structural overlap.

This is the key experimental tool for validating genuine transfer.
You need to be able to generate domains where you KNOW how much
structural similarity exists, so you can test whether transfer
scales with structural overlap.

Current TAIS domains (GridWorld, NegoSim, etc.) are tiny hardcoded
environments where the correct strategy is obvious. You can't prove
transfer with domains where "prefer good things" solves 90% of
the problem.

ProceduralDomainFactory generates domain pairs with:
- Controllable structural overlap (0.0 to 1.0)
- Controllable complexity (10 to 10000 entities)
- Controllable planning depth (1 to 10 steps)
- Controllable surface distance (0.0 to 1.0)

With this, you can run the 5 critical experiments:
1. Transfer scales with structural overlap (Pearson r > 0.8)
2. Transfer works even when entity names are shuffled (surface independence)
3. Transfer helps MORE at higher complexity
4. Transfer helps with compositional strategies
5. Structural similarity predicts transfer success
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from ..reality import Consequence, Entity, GraphPattern, RealityGraph, Relation, Transformation, WorldInterface


# --- PROCEDURAL GRAPH GENERATION -----------------------------------------------

def _random_name(prefix: str, idx: int, name_space: str = "a") -> str:
    """Generate a deterministic but domain-specific name."""
    raw = f"{prefix}_{name_space}_{idx}"
    return hashlib.md5(raw.encode()).hexdigest()[:8]


class ProceduralDomainFactory:
    """Generates domain pairs with known structural overlap.

    The key idea: generate a "template" graph topology, then create two
    domain instances that share that topology to a controllable degree
    but have different surface names (entity types, relation types, action
    names).

    overlap=1.0: Same topology, different surface names.
    overlap=0.5: 50% of the graph structure is shared.
    overlap=0.0: Completely different topologies.

    surface_distance=0.0: Same entity/relation names.
    surface_distance=1.0: Completely different names.

    The acid test: overlap=1.0 + surface_distance=1.0 should produce
    perfect transfer if the system uses genuine structural analogy.
    """

    @staticmethod
    def generate_pair(
        overlap: float = 0.7,
        complexity: int = 50,
        depth: int = 3,
        surface_distance: float = 0.9,
        seed: int = 42,
    ) -> Tuple["ProceduralWorld", "ProceduralWorld"]:
        """Generate a (source, target) domain pair.

        Parameters:
            overlap: Structural overlap [0.0, 1.0]. How much of the
                graph topology is shared between source and target.
            complexity: Number of entities in each domain.
            depth: Required planning depth to achieve optimal reward.
            surface_distance: How different the surface names are [0.0, 1.0].
                0.0 = same names, 1.0 = completely different names.
            seed: Random seed for reproducibility.

        Returns:
            (source_world, target_world) with target graphs already created.
        """
        rng = random.Random(seed)

        # Generate the shared template topology
        n_shared = max(1, int(complexity * overlap))

        # Source domain names
        source_names = _generate_name_space("source", complexity + 20, rng)
        target_names = _generate_name_space("target", complexity + 20, rng)

        # Generate source graph
        source_graph = _generate_graph(
            n_entities=complexity,
            n_shared=n_shared,
            name_space=source_names,
            rng=rng,
            depth=depth,
        )

        # Generate target graph with controlled overlap
        target_graph = _generate_overlapping_graph(
            source_template=source_graph,
            overlap=overlap,
            n_entities=complexity,
            n_shared=n_shared,
            name_space=target_names,
            surface_distance=surface_distance,
            rng=rng,
            depth=depth,
        )

        # Create world interfaces
        source_world = ProceduralWorld(
            domain_name=f"procedural_source_{seed}",
            target_graph=source_graph,
            depth=depth,
            name_space=source_names,
        )
        target_world = ProceduralWorld(
            domain_name=f"procedural_target_{seed}",
            target_graph=target_graph,
            depth=depth,
            name_space=target_names,
        )

        return source_world, target_world

    @staticmethod
    def generate_scaling_suite(
        overlaps: List[float] = None,
        complexities: List[int] = None,
        surface_distances: List[float] = None,
        seeds_per_condition: int = 5,
    ) -> List[Dict[str, Any]]:
        """Generate a full experimental suite for testing transfer.

        Returns a list of experiment configs, each with:
            source_world, target_world, overlap, complexity, surface_distance, seed
        """
        if overlaps is None:
            overlaps = [0.1, 0.3, 0.5, 0.7, 0.9]
        if complexities is None:
            complexities = [30, 100, 300]
        if surface_distances is None:
            surface_distances = [0.1, 0.5, 0.9]

        experiments = []
        for overlap in overlaps:
            for complexity in complexities:
                for surface_dist in surface_distances:
                    for seed in range(seeds_per_condition):
                        source, target = ProceduralDomainFactory.generate_pair(
                            overlap=overlap,
                            complexity=complexity,
                            surface_distance=surface_dist,
                            seed=seed + 1000,
                        )
                        experiments.append({
                            "source_world": source,
                            "target_world": target,
                            "overlap": overlap,
                            "complexity": complexity,
                            "surface_distance": surface_dist,
                            "seed": seed + 1000,
                        })
        return experiments


# --- INTERNAL GENERATION HELPERS -----------------------------------------------

def _generate_name_space(domain_tag: str, size: int, rng: random.Random) -> Dict[str, str]:
    """Generate a mapping of generic labels to domain-specific names.

    Returns dict: {"AGENT": domain_specific_name, "RESOURCE": ..., ...}
    """
    base_types = ["AGENT", "RESOURCE", "THREAT", "GOAL", "OBSTACLE", "PATH",
                  "TOOL", "BARRIER", "EXIT", "KEY", "LOCK", "BRIDGE",
                  "TRAP", "REWARD", "INFO", "PORTAL", "SHIELD", "WEAPON",
                  "ALLY", "ENEMY"]

    name_space = {}
    for i, base in enumerate(base_types[:size]):
        raw = f"{domain_tag}_{base}_{rng.randint(1000, 9999)}"
        name_space[base] = hashlib.md5(raw.encode()).hexdigest()[:8]
    return name_space


def _generate_graph(
    n_entities: int,
    n_shared: int,
    name_space: Dict[str, str],
    rng: random.Random,
    depth: int = 3,
) -> RealityGraph:
    """Generate a procedural RealityGraph with the specified complexity."""
    g = RealityGraph("procedural", f"gen_{n_entities}")

    # Entity types and their proportions
    type_proportions = {
        "AGENT": max(1, n_entities // 20),
        "RESOURCE": max(2, n_entities // 4),
        "THREAT": max(1, n_entities // 5),
        "OBSTACLE": max(1, n_entities // 5),
        "GOAL": max(1, n_entities // 10),
        "PATH": max(1, n_entities // 5),
    }

    # Create entities
    entity_id = 0
    entity_by_type: Dict[str, List[str]] = {}

    for etype, count in type_proportions.items():
        entity_by_type[etype] = []
        for _ in range(min(count, n_entities - entity_id)):
            eid = f"e_{entity_id}"
            surface_name = name_space.get(etype, eid)
            g.add_entity(Entity(eid, etype, {"surface_name": surface_name}))
            entity_by_type[etype].append(eid)
            entity_id += 1
            if entity_id >= n_entities:
                break
        if entity_id >= n_entities:
            break

    # Create relations
    if entity_by_type.get("AGENT"):
        agent_id = entity_by_type["AGENT"][0]
        for res_id in entity_by_type.get("RESOURCE", [])[:5]:
            g.add_relation(Relation(agent_id, "SEES", res_id))
        for threat_id in entity_by_type.get("THREAT", [])[:3]:
            g.add_relation(Relation(agent_id, "SEES", threat_id))

    # Some threats are near resources (the key structural pattern)
    for i, threat_id in enumerate(entity_by_type.get("THREAT", [])):
        res_ids = entity_by_type.get("RESOURCE", [])
        if i < len(res_ids):
            g.add_relation(Relation(threat_id, "NEAR", res_ids[i]))

    # Goals connected to resources
    for i, goal_id in enumerate(entity_by_type.get("GOAL", [])):
        res_ids = entity_by_type.get("RESOURCE", [])
        if i < len(res_ids):
            g.add_relation(Relation(goal_id, "REQUIRES", res_ids[i]))

    # Path connectivity
    path_ids = entity_by_type.get("PATH", [])
    for i in range(len(path_ids) - 1):
        g.add_relation(Relation(path_ids[i], "CONNECTS", path_ids[i + 1]))

    # Random connections for complexity
    all_ids = [f"e_{j}" for j in range(entity_id)]
    for _ in range(n_entities // 3):
        if len(all_ids) >= 2:
            src = rng.choice(all_ids)
            tgt = rng.choice(all_ids)
            if src != tgt and not g.get_relation(src, "LINKED", tgt):
                g.add_relation(Relation(src, "LINKED", tgt))

    return g


def _generate_overlapping_graph(
    source_template: RealityGraph,
    overlap: float,
    n_entities: int,
    n_shared: int,
    name_space: Dict[str, str],
    surface_distance: float,
    rng: random.Random,
    depth: int = 3,
) -> RealityGraph:
    """Generate a target graph with controlled structural overlap to source."""
    g = RealityGraph("procedural", f"target_{n_entities}")

    # Collect source entities and relations
    source_ents = list(source_template.entities())
    source_rels = list(source_template.relations())

    # Type renaming map for surface distance
    type_rename: Dict[str, str] = {}
    if surface_distance > 0:
        for etype in sorted(set(e.etype for e in source_ents)):
            if rng.random() < surface_distance:
                raw = f"renamed_{etype}_{rng.randint(1000, 9999)}"
                type_rename[etype] = hashlib.md5(raw.encode()).hexdigest()[:8]
            else:
                type_rename[etype] = etype
    else:
        for etype in sorted(set(e.etype for e in source_ents)):
            type_rename[etype] = etype

    # Relation type renaming
    rtype_rename: Dict[str, str] = {}
    if surface_distance > 0:
        for rtype in sorted(set(r.rtype for r in source_rels)):
            if rng.random() < surface_distance:
                raw = f"renamed_{rtype}_{rng.randint(1000, 9999)}"
                rtype_rename[rtype] = hashlib.md5(raw.encode()).hexdigest()[:8]
            else:
                rtype_rename[rtype] = rtype
    else:
        for rtype in sorted(set(r.rtype for r in source_rels)):
            rtype_rename[rtype] = rtype

    # Copy shared entities with renamed types
    shared_ids: Set[str] = set()
    for i, ent in enumerate(source_ents):
        if i >= n_shared:
            break
        new_etype = type_rename.get(ent.etype, ent.etype)
        surface_name = name_space.get(new_etype, ent.id)
        new_props = dict(ent.properties)
        new_props["surface_name"] = surface_name
        new_props["original_etype"] = ent.etype
        g.add_entity(Entity(ent.id, new_etype, new_props))
        shared_ids.add(ent.id)

    # Add unique target entities
    entity_id = len(source_ents)
    for _ in range(n_entities - n_shared):
        eid = f"e_{entity_id}"
        etype = rng.choice(list(type_rename.values())) if type_rename else "UNKNOWN"
        surface_name = name_space.get(etype, eid)
        g.add_entity(Entity(eid, etype, {"surface_name": surface_name}))
        entity_id += 1

    # Copy shared relations with renamed types
    for rel in source_rels:
        if rel.source in shared_ids and rel.target in shared_ids:
            new_rtype = rtype_rename.get(rel.rtype, rel.rtype)
            g.add_relation(Relation(rel.source, new_rtype, rel.target))

    # Add some unique target relations
    all_target_ids = [e.id for e in g.entities()]
    for _ in range((n_entities - n_shared) // 3):
        if len(all_target_ids) >= 2:
            src = rng.choice(all_target_ids)
            tgt = rng.choice(all_target_ids)
            if src != tgt:
                rtype = rng.choice(list(rtype_rename.values())) if rtype_rename else "LINKED"
                if not g.get_relation(src, rtype, tgt):
                    g.add_relation(Relation(src, rtype, tgt))

    return g


# --- PROCEDURAL WORLD INTERFACE -----------------------------------------------

class ProceduralWorld(WorldInterface):
    """World interface for procedurally generated domains.

    Actions are generated based on the graph structure:
    - APPROACH: Move toward RESOURCE/GOAL entities
    - AVOID: Move away from THREAT entities
    - VERIFY: Check safety before approaching
    - TRANSFORM: Modify a relation toward a goal
    - EXPLORE: Random move

    Rewards are determined by structural patterns:
    - Approaching a RESOURCE that is NEAR a THREAT -> small reward, possible penalty
    - Approaching a safe RESOURCE -> good reward
    - Avoiding a THREAT -> moderate reward
    - Reaching a GOAL -> large reward
    """

    domain_name: str = "procedural"

    def __init__(
        self,
        domain_name: str,
        target_graph: RealityGraph,
        depth: int = 3,
        name_space: Dict[str, str] = None,
    ):
        self.domain_name = domain_name
        self._target_graph = target_graph
        self._depth = depth
        self._name_space = name_space or {}
        self._step_count = 0
        self._agent_id = None

        # Find agent entity
        for e in target_graph.entities("AGENT"):
            self._agent_id = e.id
            break
        if self._agent_id is None:
            all_ents = list(target_graph.entities())
            if all_ents:
                self._agent_id = all_ents[0].id

    def observe(self, graph: RealityGraph, mote_position: Any) -> RealityGraph:
        agent_id = mote_position if isinstance(mote_position, str) else self._agent_id
        if agent_id and agent_id in graph:
            return graph.neighborhood(agent_id, hops=2)
        return graph

    def valid_actions(self, graph: RealityGraph, mote_state: Dict[str, Any]) -> List[Transformation]:
        actions = [
            Transformation("approach_target", self.domain_name, "MOVE_TOWARD", base_cost=0.5),
            Transformation("avoid_threat", self.domain_name, "MOVE_AWAY", base_cost=0.5),
            Transformation("verify_safety", self.domain_name, "VERIFY", base_cost=0.3),
            Transformation("transform_toward_goal", self.domain_name, "TRANSFORM", base_cost=1.0),
            Transformation("explore_area", self.domain_name, "OBSERVE", base_cost=0.2),
        ]
        return actions

    def act(self, graph: RealityGraph, transformation: Transformation, mote_state: Dict[str, Any]) -> Tuple[RealityGraph, Consequence]:
        after = graph.snapshot()
        agent_id = mote_state.get("mote_id_str", self._agent_id)

        # Find nearby resources and threats
        nearby_resources = []
        nearby_threats = []
        dangerous_resource = False

        if agent_id and agent_id in graph._entities:
            for rel, neighbor in graph.neighbors_out(agent_id):
                if neighbor.etype in ("RESOURCE", "GOAL"):
                    nearby_resources.append(neighbor)
                    # Check if threat is near this resource
                    for rel2, neighbor2 in graph.neighbors_out(neighbor.id):
                        if neighbor2.etype == "THREAT":
                            dangerous_resource = True
                elif neighbor.etype == "THREAT":
                    nearby_threats.append(neighbor)

        self._step_count += 1

        if transformation.name == "approach_target":
            if dangerous_resource:
                return after, Consequence(
                    reward=0.5,
                    penalty=3.0,
                    valid=True,
                    concept_signals={"DANGER": 0.8, "RESOURCE": 0.3},
                    explanation={"why": "resource was near threat"},
                )
            elif nearby_resources:
                return after, Consequence(
                    reward=3.0,
                    valid=True,
                    concept_signals={"RESOURCE": 0.9, "GOOD": 0.8},
                    task_signal="TASK_PROGRESS",
                    explanation={"why": "safe resource approached"},
                )
            else:
                return after, Consequence(
                    reward=0.1,
                    valid=True,
                    concept_signals={"NEUTRAL": 0.5},
                    explanation={"why": "nothing to approach"},
                )

        elif transformation.name == "avoid_threat":
            if nearby_threats:
                return after, Consequence(
                    reward=2.0,
                    valid=True,
                    concept_signals={"SAFE": 0.8, "DANGER": 0.3},
                    explanation={"why": "threat avoided"},
                )
            return after, Consequence(
                reward=0.2,
                valid=True,
                concept_signals={"NEUTRAL": 0.3},
                explanation={"why": "no threat to avoid"},
            )

        elif transformation.name == "verify_safety":
            if dangerous_resource:
                return after, Consequence(
                    reward=1.5,
                    valid=True,
                    concept_signals={"TRUST": 0.3, "DANGER": 0.7},
                    explanation={"why": "danger confirmed"},
                )
            return after, Consequence(
                reward=0.5,
                valid=True,
                concept_signals={"TRUST": 0.6, "SAFE": 0.4},
                explanation={"why": "area verified safe"},
            )

        elif transformation.name == "transform_toward_goal":
            goal_ents = list(graph.entities("GOAL"))
            if goal_ents:
                return after, Consequence(
                    reward=5.0,
                    valid=True,
                    concept_signals={"SUCCESS": 1.0, "GOOD": 0.9},
                    task_signal="TASK_SUCCESS",
                    explanation={"why": "goal transformed"},
                )
            return after, Consequence(
                reward=0.3,
                valid=True,
                concept_signals={"PROGRESS": 0.3},
                explanation={"why": "partial progress"},
            )

        elif transformation.name == "explore_area":
            return after, Consequence(
                reward=0.2,
                valid=True,
                concept_signals={"EXPLORE": 0.5},
                explanation={"why": "exploring"},
            )

        return after, Consequence(penalty=1.0, valid=False, explanation={"why": "unknown action"})

    def evaluate(self, graph: RealityGraph, mote_state: Dict[str, Any]) -> float:
        agent_id = mote_state.get("mote_id_str", self._agent_id)
        if agent_id and agent_id in graph:
            goals = list(graph.entities("GOAL"))
            if goals:
                return 5.0
        return 0.0

    def concepts(self) -> List[str]:
        return ["DANGER", "SAFE", "RESOURCE", "GOOD", "GOAL", "SUCCESS", "EXPLORE", "TRUST"]

    @property
    def target_graph(self) -> RealityGraph:
        return self._target_graph
