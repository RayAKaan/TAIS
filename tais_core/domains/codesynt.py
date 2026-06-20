"""Code Synthesis domain implementation for TAIS."""

from __future__ import annotations
import random
from typing import Any, Dict, List, Tuple, Optional

from ..reality import Consequence, Entity, RealityGraph, Relation, Transformation, WorldInterface


def make_codesynt_graph() -> RealityGraph:
    """Creates a simulated AST (Abstract Syntax Tree) environment graph."""
    g = RealityGraph("codesynt", "ast_v1")

    # Requirements & Goal
    g.add_entity(Entity("req1", "REQUIREMENT", {"desc": "calculate area", "satisfied": False}))
    g.add_entity(Entity("goal", "GOAL", {"target_req": "req1"}))

    # Initial AST Structure (empty-ish function)
    g.add_entity(Entity("root", "MODULE", {}))
    g.add_entity(Entity("func1", "FUNCTION", {"name": "get_area", "args": ["w", "h"]}))
    g.add_relation(Relation("root", "HAS_BODY", "func1"))

    # Scope
    g.add_entity(Entity("scope1", "SCOPE", {"level": "local", "parent": "global"}))
    g.add_relation(Relation("func1", "DEFINES_SCOPE", "scope1"))

    return g


class CodeSyntWorld(WorldInterface):
    """
    Simulated Code Synthesis domain.

    Structural Transfer mappings:
    - RuleWorld: PREMISE -> CodeSynt: VARIABLE / TYPE
    - RuleWorld: IMPLICATION -> CodeSynt: FUNCTION_CALL / OPERATION
    - RuleWorld: VERIFY -> CodeSynt: RUN_TEST / TYPE_CHECK
    """
    domain_name = "codesynt"

    def observe(self, graph: RealityGraph, mote_position: Any) -> RealityGraph:
        pos = mote_position or "root"
        return graph.neighborhood(pos, hops=2)

    def valid_actions(self, graph: RealityGraph, mote_state: Dict) -> List[Transformation]:
        return [
            Transformation("add_variable", self.domain_name, "TRANSFORM", base_cost=0.3, role_hint="TRANSFORM_TOWARD_GOAL"),
            Transformation("add_operation", self.domain_name, "COMPOSE", base_cost=0.5, role_hint="TRANSFORM_TOWARD_GOAL"),
            Transformation("run_tests", self.domain_name, "VERIFY", base_cost=0.4, role_hint="VERIFY_UNCERTAIN"),
            Transformation("type_check", self.domain_name, "TEST", base_cost=0.2, role_hint="VERIFY_UNCERTAIN"),
            Transformation("refactor", self.domain_name, "MUTATE", base_cost=0.6, role_hint="EXPLORE_UNCERTAIN"),
        ]

    def act(self, graph: RealityGraph, transformation: Transformation, mote_state: Dict) -> Tuple[RealityGraph, Consequence]:
        after = graph.snapshot()

        func = graph.get_entity("func1")

        if transformation.name == "add_variable":
            var_id = f"var_{random.randint(100, 999)}"
            after.add_entity(Entity(var_id, "VARIABLE", {"name": "result", "type": "float"}))
            after.add_relation(Relation("func1", "HAS_VAR", var_id))
            return after, Consequence(
                reward=1.0,
                concept_signals={"PROGRESS": 0.5, "GOOD": 0.2},
                explanation={"why": "added variable declaration"}
            )

        if transformation.name == "add_operation":
            op_id = f"op_{random.randint(100, 999)}"
            after.add_entity(Entity(op_id, "OPERATION", {"op": "multiply", "inputs": ["w", "h"]}))
            after.add_relation(Relation("func1", "HAS_OP", op_id))
            return after, Consequence(
                reward=3.0,
                concept_signals={"PROGRESS": 1.0, "GOOD": 0.5},
                explanation={"why": "added multiplication operation"}
            )

        if transformation.name == "run_tests":
            has_var = any(r.target.startswith("var_") for r in graph.relations() if r.source == "func1")
            has_op = any(r.target.startswith("op_") for r in graph.relations() if r.source == "func1")

            if has_var and has_op:
                after.update_entity("req1", satisfied=True)
                return after, Consequence(
                    reward=10.0,
                    concept_signals={"SUCCESS": 1.0, "GOOD": 1.0},
                    task_signal="TASK_SUCCESS",
                    explanation={"why": "tests passed: function correctly calculates area"}
                )
            return graph, Consequence(penalty=2.0, concept_signals={"BAD": 0.5}, explanation={"why": "tests failed: incomplete logic"})

        if transformation.name == "type_check":
            return graph, Consequence(reward=0.5, concept_signals={"TRUST": 0.3}, explanation={"why": "types verified"})

        if transformation.name == "refactor":
            return graph, Consequence(reward=0.2, explanation={"why": "code refactored"})

        return graph, Consequence(penalty=1.0, valid=False)

    def evaluate(self, graph: RealityGraph, mote_state: Dict) -> float:
        req = graph.get_entity("req1")
        if req and req.get("satisfied"):
            return 10.0
        return 0.0

    def concepts(self) -> List[str]:
        return ["GOOD", "BAD", "PROGRESS", "SUCCESS", "TRUST"]
