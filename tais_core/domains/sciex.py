"""Scientific Experiment Design domain implementation for TAIS."""

from __future__ import annotations
import random
from typing import Any, Dict, List, Tuple, Optional

from ..reality import Consequence, Entity, RealityGraph, Relation, Transformation, WorldInterface


def make_sciex_graph() -> RealityGraph:
    """Creates a simulated Scientific Experiment Design graph."""
    g = RealityGraph("sciex", "lab_v1")

    # Theory & Hypothesis
    g.add_entity(Entity("theory1", "THEORY", {"name": "Reaction Kinetics"}))
    g.add_entity(Entity("hyp1", "HYPOTHESIS", {"statement": "Temp increases rate", "tested": False, "confirmed": False}))
    g.add_relation(Relation("hyp1", "DERIVED_FROM", "theory1"))

    # Variables
    g.add_entity(Entity("var_temp", "VARIABLE", {"name": "Temperature", "role": "independent"}))
    g.add_entity(Entity("var_rate", "VARIABLE", {"name": "Reaction Rate", "role": "dependent"}))

    # Initial focus is the hypothesis
    g.add_entity(Entity("mote_focus", "FOCUS", {"target": "hyp1"}))

    return g


class SciExWorld(WorldInterface):
    """
    Simulated Scientific Experiment Design domain.

    Structural Transfer mappings:
    - GridWorld: THREAT -> SciEx: CONFOUNDING_VARIABLE (AVOID_BAD)
    - RuleWorld: IMPLICATION -> SciEx: HYPOTHESIS_LINK (TRANSFORM_TOWARD_GOAL)
    - CodeSynt: FUNCTION/OP -> SciEx: EXPERIMENT_DESIGN (TRANSFORM_TOWARD_GOAL)
    - All: VERIFY -> SciEx: RUN_EXPERIMENT / ANALYZE_DATA (VERIFY_UNCERTAIN)
    """
    domain_name = "sciex"

    def observe(self, graph: RealityGraph, mote_position: Any) -> RealityGraph:
        pos = mote_position or "hyp1"
        return graph.neighborhood(pos, hops=2)

    def valid_actions(self, graph: RealityGraph, mote_state: Dict) -> List[Transformation]:
        return [
            Transformation("formulate_experiment", self.domain_name, "COMPOSE", base_cost=0.5, role_hint="TRANSFORM_TOWARD_GOAL"),
            Transformation("control_variable", self.domain_name, "TRANSFORM", base_cost=0.4, role_hint="APPROACH_GOOD"),
            Transformation("run_experiment", self.domain_name, "TEST", base_cost=0.6, role_hint="VERIFY_UNCERTAIN"),
            Transformation("analyze_data", self.domain_name, "VERIFY", base_cost=0.3, role_hint="VERIFY_UNCERTAIN"),
            Transformation("revise_hypothesis", self.domain_name, "MUTATE", base_cost=0.4, role_hint="REPAIR_MISMATCH"),
        ]

    def act(self, graph: RealityGraph, transformation: Transformation, mote_state: Dict) -> Tuple[RealityGraph, Consequence]:
        after = graph.snapshot()

        if transformation.name == "formulate_experiment":
            exp_id = f"exp_{random.randint(100, 999)}"
            after.add_entity(Entity(exp_id, "EXPERIMENT", {"status": "designed"}))
            after.add_relation(Relation(exp_id, "TESTS", "hyp1"))
            return after, Consequence(
                reward=2.0,
                concept_signals={"PROGRESS": 1.0, "GOOD": 0.5},
                explanation={"why": "designed experiment for hypothesis"}
            )

        if transformation.name == "control_variable":
            exps = graph.entities("EXPERIMENT")
            if exps:
                exp = exps[0]
                after.add_relation(Relation(exp.id, "CONTROLS", "var_temp"))
                return after, Consequence(
                    reward=3.0,
                    concept_signals={"GOOD": 1.0, "TRUST": 0.5},
                    explanation={"why": "controlled independent variable"}
                )
            return graph, Consequence(penalty=0.5, explanation={"why": "no experiment to control"})

        if transformation.name == "run_experiment":
            exps = [e for e in graph.entities("EXPERIMENT") if any(r.target == "var_temp" for r in graph.relations() if r.source == e.id)]
            if exps:
                exp = exps[0]
                after.update_entity(exp.id, status="executed")
                res_id = f"res_{random.randint(100, 999)}"
                after.add_entity(Entity(res_id, "RESULT", {"p_value": 0.04, "significant": True}))
                after.add_relation(Relation(res_id, "PRODUCED_BY", exp.id))
                return after, Consequence(
                    reward=4.0,
                    concept_signals={"PROGRESS": 1.0, "TRUST": 0.8},
                    explanation={"why": "experiment executed, results generated"}
                )
            return graph, Consequence(penalty=2.0, explanation={"why": "experiment failed: uncontrolled variables"})

        if transformation.name == "analyze_data":
            results = [e for e in graph.entities("RESULT") if e.get("significant")]
            if results:
                after.update_entity("hyp1", tested=True, confirmed=True)
                return after, Consequence(
                    reward=10.0,
                    concept_signals={"SUCCESS": 1.0, "GOOD": 1.0},
                    task_signal="TASK_SUCCESS",
                    explanation={"why": "analysis confirmed hypothesis"}
                )
            return graph, Consequence(penalty=1.0, explanation={"why": "no significant results to analyze"})

        if transformation.name == "revise_hypothesis":
            return graph, Consequence(reward=0.5, explanation={"why": "hypothesis refined"})

        return graph, Consequence(penalty=1.0, valid=False)

    def evaluate(self, graph: RealityGraph, mote_state: Dict) -> float:
        hyp = graph.get_entity("hyp1")
        if hyp and hyp.get("confirmed"):
            return 10.0
        return 0.0

    def concepts(self) -> List[str]:
        return ["GOOD", "BAD", "PROGRESS", "SUCCESS", "TRUST", "DANGER"]
