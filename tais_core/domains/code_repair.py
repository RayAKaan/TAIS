"""Relational Code Repair domain."""

from __future__ import annotations
import ast
import random
from typing import Any, Dict, List, Tuple, Optional
from ..reality import Consequence, Entity, RealityGraph, Relation, Transformation, WorldInterface


class CodeRepairWorld(WorldInterface):
    domain_name = "code_repair"

    def __init__(self, buggy_code: str = "def f(a): return a < b", correct_code: str = "def f(a): return a <= b"):
        self.buggy_code = buggy_code
        self.correct_code = correct_code
        try:
            self.buggy_ast = ast.parse(buggy_code)
            self.correct_ast = ast.parse(correct_code)
        except:
            self.buggy_ast = ast.parse("pass")
            self.correct_ast = ast.parse("pass")

    def initial_graph(self) -> RealityGraph:
        g = RealityGraph(self.domain_name, "binary_search_bug")
        self._build_graph(self.buggy_ast, g, "root")
        g.add_entity(Entity("test_suite", "REQUIREMENT", {"status": "failing", "target": "BinarySearch"}))
        return g

    def _build_graph(self, node, graph, node_id):
        etype = type(node).__name__
        props = {"type": etype}
        if isinstance(node, ast.Compare):
            props["op"] = type(node.ops[0]).__name__

        graph.add_entity(Entity(node_id, etype, props))
        for i, child in enumerate(ast.iter_child_nodes(node)):
            child_id = f"{node_id}_{i}"
            self._build_graph(child, graph, child_id)
            graph.add_relation(Relation(node_id, "HAS_CHILD", child_id))

    def observe(self, graph: RealityGraph, mote_position: Any) -> RealityGraph:
        return graph.neighborhood(mote_position or "root", hops=3)

    def valid_actions(self, graph: RealityGraph, mote_state: Dict) -> List[Transformation]:
        return [
            Transformation("analyze_logic", self.domain_name, "VERIFY", base_cost=0.1),
            Transformation("fix_operator", self.domain_name, "TRANSFORM", base_cost=0.5),
            Transformation("run_unit_tests", self.domain_name, "TEST", base_cost=0.3),
            Transformation("ignore_node", self.domain_name, "SILENCE", base_cost=0.05),
        ]

    def act(self, graph: RealityGraph, transformation: Transformation, mote_state: Dict) -> Tuple[RealityGraph, Consequence]:
        after = graph.snapshot()

        if transformation.name == "analyze_logic":
            return graph, Consequence(reward=0.2, explanation={"why": "identified comparison nodes"})

        if transformation.name == "fix_operator":
            compares = [e for e in after.entities() if e.etype == "Compare" and e.get("op") == "Lt"]
            if compares:
                after.update_entity(compares[0].id, op="LtE")
                return after, Consequence(reward=2.0, concept_signals={"PROGRESS": 1.0}, explanation={"why": "fixed logic error"})

        if transformation.name == "run_unit_tests":
            if any(e.etype == "Compare" and e.get("op") == "LtE" for e in graph.entities()):
                after.update_entity("test_suite", status="passing")
                return after, Consequence(reward=10.0, task_signal="TASK_SUCCESS", explanation={"why": "ALL TESTS PASSED"})
            return graph, Consequence(penalty=2.0, explanation={"why": "tests failed: off-by-one error"})

        return graph, Consequence(penalty=0.5, valid=True)

    def evaluate(self, graph: RealityGraph, mote_state: Dict) -> float:
        ts = graph.get_entity("test_suite")
        return 10.0 if ts and ts.get("status") == "passing" else 0.0

    def concepts(self) -> List[str]:
        return ["CODE", "REPAIR", "LOGIC"]


def make_code_repair_graph(**kwargs):
    return CodeRepairWorld().initial_graph()
