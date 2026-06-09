"""HazardGraphWorld — intermediate-distance transfer domain.

Roadmap Phase 4. The domain the roadmap explicitly identifies as the missing
intermediate between GridGraphWorld (spatial survival, immediate consequence)
and RuleWorld (symbolic inference, target derivation).

Design goals:

- Share structural features with GridWorld so APPROACH_GOOD / AVOID_BAD action
  roles transfer naturally: there are RESOURCE nodes and HAZARD nodes that the
  agent should approach or avoid respectively.
- Share structural features with RuleWorld so the strict
  ``cons.task_signal == "TASK_SUCCESS"`` metric works: there is an explicit
  TARGET entity (the EXIT node) and the task is to reach it.
- Be a genuine new test: the agent navigates a multi-node graph (not a single
  neighborhood snapshot like Grid, not a fixed implication chain like Rule),
  so the policy has to actually *plan* multi-step movement.

Entities:
    AGENT          — the mote-in-the-world.
    NODE           — vanilla floor node, +0.05 per step.
    RESOURCE_NODE  — stepping into one yields +0.5 and TASK_PROGRESS.
    HAZARD_NODE    — stepping into one yields -3.0 and TASK_FAILURE.
    EXIT_NODE      — the target. First arrival yields +4.0 and TASK_SUCCESS.
    TARGET         — marker entity pointing at the EXIT_NODE id (mirrors RuleWorld).

Relations:
    AT             — agent-id  -> node-id  (current position; unique per graph).
    CONNECTED_TO   — node-id   -> node-id  (bidirectional, stored both ways).
    NEAR_HAZARD    — node-id   -> hazard-id (visibility hint for AVOID_BAD).

Actions (4):
    move_to_neighbor   — step to a random connected node. The workhorse action.
    approach_resource  — step toward a connected RESOURCE_NODE (or fall back to
                         move_to_neighbor if none adjacent).
    avoid_hazard       — step toward any connected NON-HAZARD neighbor that is
                         not currently adjacent to a hazard (or fall back).
    verify_node        — passive check, tiny reward, no movement.

Rewards (kept on the Phase 2 RuleWorld scale so the headline metric is
comparable across domains):

    Reach EXIT (first time)   :  +4.0   TASK_SUCCESS
    Reach EXIT (re-step)      :  +0.05  (no signal)
    Enter HAZARD              :  -3.0   TASK_FAILURE
    Enter RESOURCE            :  +0.5   TASK_PROGRESS
    Enter normal NODE         :  +0.05  (no signal)
    verify_node               :  +0.02  (no signal)

The agent does NOT die in HazardWorld — entering a hazard penalises but does
not absorb. This matches GridWorld's behavior and lets a 12-tick eval
horizon collect multiple datapoints per trial.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple

from ..reality import (
    Consequence,
    Entity,
    RealityGraph,
    Relation,
    Transformation,
    WorldInterface,
)


# ─── REWARD CONSTANTS ────────────────────────────────────────────────────────
# Pulled out for sensitivity sweeps; kept on Phase 2 RuleWorld scale for
# cross-domain headline-metric comparability.

EXIT_REWARD_FIRST = 4.0
EXIT_REWARD_REPEAT = 0.05
HAZARD_PENALTY = 3.0
RESOURCE_REWARD = 0.5
STEP_REWARD = 0.05
VERIFY_REWARD = 0.02
INVALID_PENALTY = 1.0


# ─── GRAPH BUILDERS ──────────────────────────────────────────────────────────

def _add_node(g: RealityGraph, nid: str, etype: str, **props):
    g.add_entity(Entity(nid, etype, props))


def _connect(g: RealityGraph, a: str, b: str):
    """Bidirectional edge. We store both directions so neighbors_out works
    symmetrically from either side and the analogy engine sees the same
    edge-type cardinality regardless of orientation."""
    g.add_relation(Relation(a, "CONNECTED_TO", b))
    g.add_relation(Relation(b, "CONNECTED_TO", a))


def _mark_near_hazards(g: RealityGraph):
    """For every (node, hazard) pair connected by an edge, add a NEAR_HAZARD
    edge from the node to the hazard. This gives observability to the
    avoid_hazard action without needing the mote to ground-truth-check.
    """
    hazard_ids = {e.id for e in g.entities("HAZARD_NODE")}
    if not hazard_ids:
        return
    for rel in list(g.relations("CONNECTED_TO")):
        if rel.target in hazard_ids and rel.source not in hazard_ids:
            # Avoid duplicate edges.
            if g.get_relation(rel.source, "NEAR_HAZARD", rel.target) is None:
                g.add_relation(Relation(rel.source, "NEAR_HAZARD", rel.target))


def _add_target(g: RealityGraph, exit_id: str):
    g.add_entity(Entity("TARGET", "TARGET", {"derive_id": exit_id}))


def make_hazard_graph_easy() -> RealityGraph:
    r"""A short 5-node corridor with one hazard, one resource, one exit.

    Topology (start at S)::

         S --- A --- R --- E
                \    /
                 H --

    S: start (NODE)        R: resource             E: exit (target)
    A: junction (NODE)     H: hazard (penalty)

    Greedy hazard-avoiding paths reach E in 3 steps; an unlucky random walker
    may bounce into H once or twice on the way.
    """
    g = RealityGraph("hazard", "hazard_easy")
    _add_node(g, "S", "NODE")
    _add_node(g, "A", "NODE")
    _add_node(g, "R", "RESOURCE_NODE")
    _add_node(g, "H", "HAZARD_NODE", danger=1.0)
    _add_node(g, "E", "EXIT_NODE")
    _add_node(g, "agent", "AGENT")
    g.add_relation(Relation("agent", "AT", "S"))
    _connect(g, "S", "A")
    _connect(g, "A", "R")
    _connect(g, "R", "E")
    _connect(g, "A", "H")
    _connect(g, "H", "R")
    _mark_near_hazards(g)
    _add_target(g, "E")
    return g


def make_hazard_graph_distractor() -> RealityGraph:
    r"""Larger map with multiple hazards and resources mixed in.

    Topology::

         S --- A --- B --- R --- E
                \    |     |
                 H1  H2   D (dead-end resource)
                 |
                 D2 (dead-end)

    Tests selection under distractors: there are two RESOURCE_NODE entities
    but only one leads to E; there are two HAZARD_NODEs the agent must learn
    to avoid; and there are dead-end branches that waste steps without
    advancing toward the target.
    """
    g = RealityGraph("hazard", "hazard_distractor")
    for nid in ["S", "A", "B"]:
        _add_node(g, nid, "NODE")
    _add_node(g, "R", "RESOURCE_NODE")
    _add_node(g, "D", "RESOURCE_NODE")
    _add_node(g, "H1", "HAZARD_NODE", danger=1.0)
    _add_node(g, "H2", "HAZARD_NODE", danger=1.0)
    _add_node(g, "D2", "NODE")
    _add_node(g, "E", "EXIT_NODE")
    _add_node(g, "agent", "AGENT")
    g.add_relation(Relation("agent", "AT", "S"))
    _connect(g, "S", "A")
    _connect(g, "A", "B")
    _connect(g, "B", "R")
    _connect(g, "R", "E")
    _connect(g, "A", "H1")
    _connect(g, "H1", "D2")
    _connect(g, "B", "H2")
    _connect(g, "B", "D")
    _mark_near_hazards(g)
    _add_target(g, "E")
    return g


# ─── WORLD ───────────────────────────────────────────────────────────────────

class HazardGraphWorld(WorldInterface):
    """Graph navigation with rewarding and dangerous nodes.

    The world is stateless across calls; ``mote_position`` is ignored
    (position is encoded in the AGENT --AT--> node edge in the graph itself).
    All randomness goes through Python's global random module so the existing
    `random.seed(seed)` discipline in experiments/ablation_runner.py applies
    without changes.
    """

    domain_name = "hazard"

    # ── helpers ──────────────────────────────────────────────────────────────

    def _target_id(self, graph: RealityGraph) -> str:
        tgt = graph.get_entity("TARGET")
        return tgt.get("derive_id", "E") if tgt else "E"

    def _agent_node(self, graph: RealityGraph) -> Optional[str]:
        for rel, ent in graph.neighbors_out("agent", "AT"):
            return ent.id
        return None

    def _neighbors(self, graph: RealityGraph, node_id: str) -> List[Entity]:
        return [ent for _rel, ent in graph.neighbors_out(node_id, "CONNECTED_TO")]

    def _move_agent(self, graph: RealityGraph, dest_id: str) -> RealityGraph:
        g = graph.snapshot()
        cur = self._agent_node(g)
        if cur is not None:
            g.remove_relation("agent", "AT", cur)
        g.add_relation(Relation("agent", "AT", dest_id))
        return g

    def _consequence_for_destination(self, graph_after: RealityGraph, dest: Entity, target_id: str, already_succeeded: bool) -> Consequence:
        if dest.etype == "EXIT_NODE":
            if already_succeeded:
                return Consequence(
                    reward=EXIT_REWARD_REPEAT,
                    valid=True,
                    concept_signals={"GOOD": 0.3, "CONFIRM": 0.2},
                    explanation={"why": "already at exit"},
                    task_signal=None,
                )
            return Consequence(
                reward=EXIT_REWARD_FIRST,
                valid=True,
                concept_signals={"GOOD": 1.0, "SAFE": 0.7, "CONFIRM": 0.6},
                explanation={"why": f"reached target exit {target_id}"},
                task_signal="TASK_SUCCESS",
            )
        if dest.etype == "HAZARD_NODE":
            return Consequence(
                penalty=HAZARD_PENALTY,
                valid=False,
                concept_signals={"DANGER": 1.0, "BAD": 0.8},
                explanation={"why": f"stepped into hazard {dest.id}"},
                task_signal="TASK_FAILURE",
            )
        if dest.etype == "RESOURCE_NODE":
            return Consequence(
                reward=RESOURCE_REWARD,
                valid=True,
                concept_signals={"RESOURCE": 1.0, "GOOD": 0.4},
                explanation={"why": f"reached resource {dest.id}"},
                task_signal="TASK_PROGRESS",
            )
        # plain NODE
        return Consequence(
            reward=STEP_REWARD,
            valid=True,
            concept_signals={"SAFE": 0.2},
            explanation={"why": f"stepped to {dest.id}"},
            task_signal=None,
        )

    def _has_succeeded(self, graph: RealityGraph) -> bool:
        """Did the agent already reach the target on a prior step?

        We record this by tagging the AGENT entity with `reached_target=True`
        on first arrival; checking that flag is cheaper than re-deriving from
        graph state and survives across consecutive `act()` calls.
        """
        agent = graph.get_entity("agent")
        return bool(agent and agent.get("reached_target", False))

    def _mark_succeeded(self, graph: RealityGraph) -> RealityGraph:
        g = graph.snapshot()
        g.update_entity("agent", reached_target=True)
        return g

    # ── universal contract ──────────────────────────────────────────────────

    def observe(self, graph: RealityGraph, mote_position: Any) -> RealityGraph:
        # Attention: agent's 2-hop neighborhood, which surfaces immediate
        # neighbors AND their neighbors (so the mote can see one step ahead).
        cur = self._agent_node(graph)
        if cur is None:
            return graph
        return graph.neighborhood(cur, hops=2)

    def valid_actions(self, graph: RealityGraph, mote_state: Dict) -> List[Transformation]:
        # Move-class actions are priced at 0.2 to match verify's cost, so a
        # mote choosing between "verify and stay" vs "step toward something"
        # is comparing rewards on equal cost ground. Pre-Phase 4-calibration
        # we used 0.4 here and found motes verify-spammed in place (the same
        # pathology Phase 2 hit in RuleWorld); 0.2 fixes it cleanly without
        # making any single move strictly profitable in expectation.
        return [
            Transformation("move_to_neighbor",  self.domain_name, "MOVE_TOWARD", base_cost=0.2),
            Transformation("approach_resource", self.domain_name, "MOVE_TOWARD", base_cost=0.2,
                           role_hint="APPROACH_GOOD"),
            Transformation("avoid_hazard",      self.domain_name, "MOVE_AWAY",   base_cost=0.2,
                           role_hint="AVOID_BAD"),
            Transformation("verify_node",       self.domain_name, "VERIFY",      base_cost=0.2,
                           role_hint="VERIFY_UNCERTAIN"),
        ]

    def act(self, graph: RealityGraph, transformation: Transformation, mote_state: Dict) -> Tuple[RealityGraph, Consequence]:
        target_id = self._target_id(graph)
        already_succeeded = self._has_succeeded(graph)

        # verify_node never moves the agent.
        if transformation.name == "verify_node":
            return graph, Consequence(
                reward=VERIFY_REWARD,
                valid=True,
                concept_signals={"CONFIRM": 0.4},
                explanation={"why": "node checked"},
                task_signal=None,
            )

        cur = self._agent_node(graph)
        if cur is None:
            return graph, Consequence(
                penalty=INVALID_PENALTY,
                valid=False,
                concept_signals={"BAD": 1.0},
                task_signal="TASK_FAILURE",
            )

        neighbors = self._neighbors(graph, cur)
        if not neighbors:
            return graph, Consequence(
                penalty=INVALID_PENALTY,
                valid=False,
                concept_signals={"BAD": 1.0, "VOID": 0.5},
                explanation={"why": "no neighbors to move to"},
                task_signal="TASK_FAILURE",
            )

        # Pick a destination based on the action's role.
        if transformation.name == "approach_resource":
            # Prefer a RESOURCE_NODE or EXIT_NODE neighbor; fall back to anything.
            preferred = [n for n in neighbors if n.etype in ("RESOURCE_NODE", "EXIT_NODE")]
            dest = random.choice(preferred) if preferred else random.choice(neighbors)
        elif transformation.name == "avoid_hazard":
            # Prefer a non-HAZARD non-near-hazard neighbor.
            hazard_ids = {e.id for e in graph.entities("HAZARD_NODE")}
            safe = [
                n for n in neighbors
                if n.etype != "HAZARD_NODE"
                and not any(
                    graph.get_relation(n.id, "NEAR_HAZARD", h) is not None
                    for h in hazard_ids
                )
            ]
            # If literally every neighbor is unsafe, prefer a non-hazard at least.
            if not safe:
                safe = [n for n in neighbors if n.etype != "HAZARD_NODE"]
            dest = random.choice(safe) if safe else random.choice(neighbors)
        else:  # move_to_neighbor
            dest = random.choice(neighbors)

        new_graph = self._move_agent(graph, dest.id)
        cons = self._consequence_for_destination(new_graph, dest, target_id, already_succeeded)
        if cons.task_signal == "TASK_SUCCESS":
            new_graph = self._mark_succeeded(new_graph)
        # Attach a graph_delta so downstream pattern memory sees the movement.
        cons.graph_delta = graph.diff(new_graph)
        return new_graph, cons

    def evaluate(self, graph: RealityGraph, mote_state: Dict) -> float:
        """Higher = closer to victory. 10 if exit reached, 5 if currently at
        a resource, 1 if at a normal node, -1 if at a hazard."""
        cur = self._agent_node(graph)
        if cur is None:
            return 0.0
        if self._has_succeeded(graph):
            return 10.0
        ent = graph.get_entity(cur)
        if ent is None:
            return 0.0
        if ent.etype == "EXIT_NODE":
            return 10.0
        if ent.etype == "RESOURCE_NODE":
            return 5.0
        if ent.etype == "HAZARD_NODE":
            return -1.0
        return 1.0

    def concepts(self) -> List[str]:
        return ["GOOD", "BAD", "DANGER", "SAFE", "RESOURCE", "CONFIRM", "VOID"]


class HazardGraphWorldLarge(HazardGraphWorld):
    """Large hazard navigation variant; use with ``make_hazard_graph_large``."""
    domain_name = "hazard_large"


def _random_connected_topology(rng: random.Random, n_nodes: int) -> List[Tuple[str, str]]:
    """Generate a random connected undirected graph on integer-labeled nodes.

    Guarantees connectivity by first building a random spanning tree (each new
    node attached to an existing one), then adding extra edges up to ~1.5x
    tree density.
    """
    nodes = [f"N{i}" for i in range(n_nodes)]
    edges: List[Tuple[str, str]] = []

    connected = [nodes[0]]
    remaining = nodes[1:]
    rng.shuffle(remaining)

    for node in remaining:
        parent = rng.choice(connected)
        edges.append((parent, node))
        connected.append(node)

    extra = rng.randint(0, max(1, n_nodes // 2))
    for _ in range(extra):
        a = rng.choice(nodes)
        b = rng.choice(nodes)
        if a != b and (a, b) not in edges and (b, a) not in edges:
            edges.append((a, b))

    return edges


def make_hazard_graph_large(seed: int = 0, n_nodes: int = 15, hazard_density: float = 0.2) -> RealityGraph:
    """Generates a larger hazard navigation graph. Deterministic from seed.

    Construction:
      1. Generate a random connected topology of *n_nodes* NODE entities.
      2. Pick the first node as start (S), last node as exit (E).
      3. Assign ~n_nodes * hazard_density nodes as HAZARD_NODE.
      4. Place 2-3 RESOURCE_NODE entities along the path.
      5. Mark NEAR_HAZARD edges for hazard neighbors.

    Compatible with existing HazardGraphWorld.act() — same entity types, actions.
    """
    rng = random.Random(seed)

    raw_edges = _random_connected_topology(rng, n_nodes)
    all_ids = sorted(set(e[0] for e in raw_edges) | set(e[1] for e in raw_edges))
    rng.shuffle(all_ids)

    start_id = "S"
    exit_id = "E"
    node_ids = [start_id] + all_ids[:n_nodes - 2] + [exit_id]

    n_hazards = max(1, int(n_nodes * hazard_density))
    hazard_ids = set(rng.sample(node_ids[1:-1], min(n_hazards, n_nodes - 2)))
    n_resources = rng.randint(2, 3)
    resource_candidates = [n for n in node_ids[1:-1] if n not in hazard_ids]
    resource_ids = set(rng.sample(resource_candidates, min(n_resources, len(resource_candidates))))

    g = RealityGraph("hazard", "hazard_large")
    for nid in node_ids:
        if nid == exit_id:
            _add_node(g, nid, "EXIT_NODE")
        elif nid in hazard_ids:
            _add_node(g, nid, "HAZARD_NODE", danger=1.0)
        elif nid in resource_ids:
            _add_node(g, nid, "RESOURCE_NODE")
        else:
            _add_node(g, nid, "NODE")
    _add_node(g, "agent", "AGENT")
    g.add_relation(Relation("agent", "AT", start_id))

    edge_map: Dict[str, set] = {n: set() for n in node_ids}
    for a, b in raw_edges:
        if a in edge_map and b in edge_map:
            _connect(g, a, b)
            edge_map[a].add(b)
            edge_map[b].add(a)

    _mark_near_hazards(g)
    _add_target(g, exit_id)
    return g


__all__ = [
    "HazardGraphWorld", "HazardGraphWorldLarge",
    "make_hazard_graph_easy",
    "make_hazard_graph_distractor",
    "make_hazard_graph_large",
    "EXIT_REWARD_FIRST",
    "EXIT_REWARD_REPEAT",
    "HAZARD_PENALTY",
    "RESOURCE_REWARD",
    "STEP_REWARD",
    "VERIFY_REWARD",
    "INVALID_PENALTY",
]
