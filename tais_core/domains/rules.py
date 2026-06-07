"""Tiny rule satisfaction validation domain."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from ..reality import Consequence, Entity, RealityGraph, Relation, Transformation, WorldInterface


def make_rule_graph() -> RealityGraph:
    g = RealityGraph("rules", "modus_ponens_toy")
    g.add_entity(Entity("fact_a", "FACT", {"truth": True}))
    g.add_entity(Entity("fact_b", "FACT", {"truth": True}))
    g.add_entity(Entity("rule_ab", "RULE", {"kind": "implies"}))
    g.add_relation(Relation("fact_a", "SATISFIES", "rule_ab"))
    g.add_relation(Relation("rule_ab", "IMPLIES", "fact_b"))
    return g


class RuleWorld(WorldInterface):
    domain_name = "rules"

    def observe(self, graph: RealityGraph, mote_position: Any) -> RealityGraph:
        return graph.neighborhood("rule_ab", hops=2)

    def valid_actions(self, graph: RealityGraph, mote_state: Dict) -> List[Transformation]:
        return [
            Transformation("apply_implication", self.domain_name, "TRANSFORM", base_cost=0.4),
            Transformation("verify_rule", self.domain_name, "VERIFY", base_cost=0.2),
            Transformation("random_assert", self.domain_name, "MUTATE", base_cost=0.5),
        ]

    def act(self, graph: RealityGraph, transformation: Transformation, mote_state: Dict) -> Tuple[RealityGraph, Consequence]:
        if transformation.name == "apply_implication":
            if graph.get_relation("fact_a", "SATISFIES", "rule_ab") and graph.get_relation("rule_ab", "IMPLIES", "fact_b"):
                after = graph.snapshot()
                if not after.get_entity("fact_b_known"):
                    after.add_entity(Entity("fact_b_known", "FACT", {"truth": True, "derived": True}))
                    after.add_relation(Relation("fact_b", "SUPPORTS", "fact_b_known"))
                return after, Consequence(
                    reward=4.0,
                    valid=True,
                    concept_signals={"GOOD": 1.0, "TRUST": 0.6, "CONFIRM": 0.6},
                    explanation={"why": "valid implication applied"},
                    graph_delta=graph.diff(after),
                )
        if transformation.name == "verify_rule":
            ok = bool(graph.get_relation("rule_ab", "IMPLIES", "fact_b"))
            return graph, Consequence(
                reward=1.5 if ok else 0.0,
                penalty=0.0 if ok else 2.0,
                valid=ok,
                concept_signals={"CONFIRM": 0.7 if ok else 0.0, "BAD": 0.8 if not ok else 0.0},
                explanation={"why": "rule checked", "valid": ok},
            )
        if transformation.name == "random_assert":
            return graph, Consequence(
                penalty=3.0,
                valid=False,
                concept_signals={"BAD": 1.0, "DENY": 0.6},
                explanation={"why": "unsupported assertion"},
            )
        return graph, Consequence(penalty=1.0, valid=False, concept_signals={"BAD": 1.0})

    def evaluate(self, graph: RealityGraph, mote_state: Dict) -> float:
        return 10.0 if graph.get_entity("fact_b_known") else 0.0

    def concepts(self) -> List[str]:
        return ["GOOD", "BAD", "TRUST", "CONFIRM", "DENY"]
