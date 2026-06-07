"""Tiny graph GridWorld validation domain."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from ..reality import Consequence, Entity, RealityGraph, Relation, Transformation, WorldInterface


def make_grid_graph(threat_near_resource: bool = True) -> RealityGraph:
    g = RealityGraph("grid", "tiny_grid")
    g.add_entity(Entity("mote", "AGENT", {"x": 0, "y": 0}))
    g.add_entity(Entity("food", "RESOURCE", {"kind": "food", "value": 8.0}))
    g.add_entity(Entity("pred", "THREAT", {"kind": "predator", "danger": 1.0}))
    g.add_relation(Relation("mote", "SEES", "food"))
    g.add_relation(Relation("mote", "SEES", "pred"))
    if threat_near_resource:
        g.add_relation(Relation("pred", "NEAR", "food"))
    return g


class GridGraphWorld(WorldInterface):
    domain_name = "grid"

    def observe(self, graph: RealityGraph, mote_position: Any) -> RealityGraph:
        return graph.neighborhood("mote", hops=1)

    def valid_actions(self, graph: RealityGraph, mote_state: Dict) -> List[Transformation]:
        return [
            Transformation("approach_resource", self.domain_name, "MOVE_TOWARD", base_cost=0.5),
            Transformation("avoid_threat", self.domain_name, "MOVE_AWAY", base_cost=0.5),
            Transformation("verify_safety", self.domain_name, "VERIFY", base_cost=0.2),
        ]

    def act(self, graph: RealityGraph, transformation: Transformation, mote_state: Dict) -> Tuple[RealityGraph, Consequence]:
        if transformation.name == "approach_resource":
            if graph.get_relation("pred", "NEAR", "food"):
                return graph, Consequence(
                    reward=1.0,
                    penalty=5.0,
                    valid=True,
                    concept_signals={"DANGER": 1.0, "BAD": 0.7},
                    explanation={"why": "resource was near threat"},
                )
            return graph, Consequence(
                reward=5.0,
                valid=True,
                concept_signals={"RESOURCE": 1.0, "GOOD": 0.8},
                explanation={"why": "safe resource approached"},
            )
        if transformation.name == "avoid_threat":
            return graph, Consequence(
                reward=4.0,
                valid=True,
                concept_signals={"DANGER": 1.0, "SAFE": 0.7},
                explanation={"why": "threat avoided"},
            )
        if transformation.name == "verify_safety":
            reward = 2.0 if graph.get_relation("pred", "NEAR", "food") else 1.0
            return graph, Consequence(
                reward=reward,
                valid=True,
                concept_signals={"TRUST": 0.4, "DANGER": 0.4 if reward > 1 else 0.0},
                explanation={"why": "safety checked"},
            )
        return graph, Consequence(penalty=1.0, valid=False, concept_signals={"BAD": 1.0})

    def evaluate(self, graph: RealityGraph, mote_state: Dict) -> float:
        return -1.0 if graph.get_relation("pred", "NEAR", "food") else 5.0

    def concepts(self) -> List[str]:
        return ["DANGER", "SAFE", "RESOURCE", "GOOD", "BAD"]
