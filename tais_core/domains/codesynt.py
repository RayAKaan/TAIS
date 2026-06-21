"""Generic Code Synthesis domain for custom user code."""

from __future__ import annotations
import ast
import random
from typing import Any, Dict, List, Tuple, Optional
from ..reality import Consequence, Entity, RealityGraph, Relation, Transformation, WorldInterface


class CustomCodeWorld(WorldInterface):
    domain_name = "codesynt"

    def __init__(self, source_code: str = "def solve(): return False"):
        self.source = source_code
        try:
            self.tree = ast.parse(source_code)
        except:
            self.tree = ast.parse("def error(): pass")

    def initial_graph(self) -> RealityGraph:
        g = RealityGraph(self.domain_name, "custom_code_ast")
        self._build_graph(self.tree, g, "root")
        g.add_entity(Entity("goal", "REQUIREMENT", {"status": "unresolved"}))
        return g

    def _build_graph(self, node, graph, node_id):
        etype = type(node).__name__
        props = {"type": etype}
        if isinstance(node, ast.Name):
            props["id"] = node.id
        if isinstance(node, ast.Compare):
            props["op"] = type(node.ops[0]).__name__
        if isinstance(node, ast.BinOp):
            props["op"] = type(node.op).__name__

        graph.add_entity(Entity(node_id, etype, props))
        for i, child in enumerate(ast.iter_child_nodes(node)):
            child_id = f"{node_id}_{i}"
            self._build_graph(child, graph, child_id)
            graph.add_relation(Relation(node_id, "CONTAINS", child_id))

    def observe(self, graph: RealityGraph, mote_position: Any) -> RealityGraph:
        return graph.neighborhood(mote_position or "root", hops=3)

    def valid_actions(self, graph: RealityGraph, mote_state: Dict) -> List[Transformation]:
        return [
            Transformation("fix_operator", self.domain_name, "TRANSFORM", base_cost=0.5, role_hint="TRANSFORM_TOWARD_GOAL"),
            Transformation("run_validation", self.domain_name, "VERIFY", base_cost=0.3, role_hint="VERIFY_UNCERTAIN"),
            Transformation("refactor", self.domain_name, "MUTATE", base_cost=0.2, role_hint="MAINTAIN_STABLE"),
        ]

    def act(self, graph: RealityGraph, transformation: Transformation, mote_state: Dict) -> Tuple[RealityGraph, Consequence]:
        after = graph.snapshot()

        if transformation.name == "fix_operator":
            targets = [e for e in after.entities() if "op" in e.properties]
            if targets:
                after.update_entity(targets[0].id, op="CORRECTED")
                after.add_entity(Entity("patch", "LOGIC_FIX", {"status": "applied"}))
                return after, Consequence(reward=5.0, task_signal="TASK_PROGRESS", explanation={"why": "Applied structural logic patch."})

        if transformation.name == "run_validation":
            if any(e.etype == "LOGIC_FIX" for e in graph.entities()):
                after.update_entity("goal", status="satisfied")
                return after, Consequence(reward=10.0, task_signal="TASK_SUCCESS", explanation={"why": "Code verified. Custom logic resolved."})
            return graph, Consequence(penalty=1.0, explanation={"why": "Validation failed: code remains buggy."})

        return graph, Consequence(penalty=0.1, valid=True)

    def evaluate(self, graph: RealityGraph, mote_state: Dict) -> float:
        g = graph.get_entity("goal")
        return 10.0 if g and g.get("status") == "satisfied" else 0.0

    def concepts(self) -> List[str]:
        return ["GOOD", "SUCCESS", "PROGRESS"]
