"""
TAIS Phase 2: Real-World Grounding Pilot.
Domain: PythonASTWorld - Grounding RealityGraph in real Python source code.
"""

import ast
from typing import Any, Dict, List, Tuple
from tais_core.reality import Entity, Relation, RealityGraph, Transformation, WorldInterface, Consequence


class PythonASTWorld(WorldInterface):
    """
    World where the graph is a real Python Abstract Syntax Tree.
    """

    domain_name = "python_ast"

    def __init__(self, source_code: str = "x = 1 + 2"):
        self.source = source_code
        self.tree = ast.parse(source_code)

    def initial_graph(self) -> RealityGraph:
        g = RealityGraph(self.domain_name, "source_tree")
        self._build_graph(self.tree, g, "root")
        return g

    def _build_graph(self, node, graph, node_id):
        etype = type(node).__name__
        props = {"lineno": getattr(node, "lineno", 0)}
        if isinstance(node, ast.Name):
            props["id"] = node.id
        if isinstance(node, ast.Constant):
            props["value"] = node.value

        graph.add_entity(Entity(node_id, etype, props))

        for i, child in enumerate(ast.iter_child_nodes(node)):
            child_id = f"{node_id}_{i}"
            self._build_graph(child, graph, child_id)
            graph.add_relation(Relation(node_id, "CONTAINS", child_id))

    def observe(self, graph: RealityGraph, mote_position: Any) -> RealityGraph:
        pos = mote_position or "root"
        return graph.neighborhood(pos, hops=2)

    def valid_actions(self, graph: RealityGraph, mote_state: Dict) -> List[Transformation]:
        return [
            Transformation("analyze_node", self.domain_name, "VERIFY", base_cost=0.1,
                           role_hint="VERIFY_UNCERTAIN"),
            Transformation("mutate_constant", self.domain_name, "TRANSFORM", base_cost=0.5,
                           role_hint="TRANSFORM_TOWARD_GOAL"),
            Transformation("add_comment", self.domain_name, "MUTATE", base_cost=0.2,
                           role_hint="MAINTAIN_STABLE"),
        ]

    def act(self, graph: RealityGraph, transformation: Transformation,
            mote_state: Dict) -> Tuple[RealityGraph, Consequence]:
        if transformation.name == "analyze_node":
            return graph, Consequence(reward=0.2, valid=True,
                                      explanation={"why": "node structure verified"})

        if transformation.name == "mutate_constant":
            after = graph.snapshot()
            constants = [e for e in after.entities() if e.type == "Constant"]
            if constants:
                after.update_entity(constants[0].id, value="MODIFIED")
                return after, Consequence(reward=1.0, valid=True,
                                          task_signal="TASK_SUCCESS",
                                          explanation={"why": "code modified"})

        return graph, Consequence(penalty=0.5, valid=False,
                                  explanation={"why": "invalid action"})

    def evaluate(self, graph: RealityGraph, mote_state: Dict) -> float:
        for e in graph.entities():
            if e.type == "Constant" and e.get("value") == "MODIFIED":
                return 10.0
        return 0.0

    def concepts(self) -> List[str]:
        return ["CODE", "STRUCTURE", "VALUE"]
