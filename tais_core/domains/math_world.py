"""Math domain for elementary arithmetic.

TAIS discovers the evaluate action sequence — no answer is hardcoded.
The world enforces arithmetic rules (Add = +, Mult = *) in act().
"""

from __future__ import annotations
import ast
from typing import Any, Dict, List, Optional, Tuple
from ..reality import Consequence, Entity, RealityGraph, Relation, Transformation, WorldInterface


def make_math_graph(**kwargs):
    return MathWorld(**kwargs).initial_graph()


_OP_FN = {
    "Add": lambda a, b: a + b,
    "Sub": lambda a, b: a - b,
    "Mult": lambda a, b: a * b,
    "Div": lambda a, b: a / b,
    "FloorDiv": lambda a, b: a // b,
    "Pow": lambda a, b: a ** b,
    "Mod": lambda a, b: a % b,
    "Lt": lambda a, b: a < b,
    "Gt": lambda a, b: a > b,
    "LtE": lambda a, b: a <= b,
    "GtE": lambda a, b: a >= b,
    "Eq": lambda a, b: a == b,
    "NotEq": lambda a, b: a != b,
}

_UNARY_OP_FN = {
    "UAdd": lambda a: a,
    "USub": lambda a: -a,
}


class MathWorld(WorldInterface):
    domain_name = "math"

    def __init__(self, expression_str: str = ""):
        self.expr_str = expression_str.strip()
        self.answer: Any = None
        self._result_id_counter = 0

    def initial_graph(self) -> RealityGraph:
        g = RealityGraph(self.domain_name, "math_expression")
        try:
            tree = ast.parse(self.expr_str, mode="eval")
            self._build_expr(g, tree.body, "root")
        except (SyntaxError, ValueError):
            g.add_entity(Entity("error", "ERROR", {"message": f"cannot parse: {self.expr_str}"}))
        g.add_entity(Entity("goal", "GOAL", {"target": "computed", "status": "unresolved"}))
        return g

    def _build_expr(self, g: RealityGraph, node: ast.AST, node_id: str):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, bool)):
            g.add_entity(Entity(node_id, "NUMBER", {"value": node.value}))
            return

        if isinstance(node, ast.BinOp):
            op_name = type(node.op).__name__
            g.add_entity(Entity(node_id, "EXPRESSION", {"op": op_name}))
            left_id = f"{node_id}_l"
            right_id = f"{node_id}_r"
            self._build_expr(g, node.left, left_id)
            self._build_expr(g, node.right, right_id)
            g.add_relation(Relation(node_id, "HAS_LEFT", left_id))
            g.add_relation(Relation(node_id, "HAS_RIGHT", right_id))
            return

        if isinstance(node, ast.UnaryOp):
            op_name = type(node.op).__name__
            if op_name in _UNARY_OP_FN:
                operand_id = f"{node_id}_o"
                self._build_expr(g, node.operand, operand_id)
                g.add_entity(Entity(node_id, "EXPRESSION", {"op": op_name}))
                g.add_relation(Relation(node_id, "HAS_LEFT", operand_id))
            return

        if isinstance(node, ast.Compare):
            op_name = type(node.ops[0]).__name__
            g.add_entity(Entity(node_id, "EXPRESSION", {"op": op_name}))
            left_id = f"{node_id}_l"
            right_id = f"{node_id}_r"
            self._build_expr(g, node.left, left_id)
            self._build_expr(g, node.comparators[0], right_id)
            g.add_relation(Relation(node_id, "HAS_LEFT", left_id))
            g.add_relation(Relation(node_id, "HAS_RIGHT", right_id))
            return

        raise ValueError(f"unsupported AST node: {type(node).__name__}")

    # ------------------------------------------------------------------
    # World interface
    # ------------------------------------------------------------------
    def observe(self, graph: RealityGraph, mote_position: Any) -> RealityGraph:
        return graph.neighborhood(mote_position or "root", hops=5)

    def valid_actions(self, graph: RealityGraph,
                      mote_state: Dict) -> List[Transformation]:
        actions: List[Transformation] = []

        evaluable = self._find_evaluable(graph)
        if evaluable:
            actions.append(Transformation(
                "evaluate", self.domain_name, "TRANSFORM",
                base_cost=0.3,
            ))

            actions.append(Transformation(
                "verify", self.domain_name, "VERIFY",
                base_cost=0.2,
            ))

        return actions

    def act(self, graph: RealityGraph, transformation: Transformation,
            mote_state: Dict) -> Tuple[RealityGraph, Consequence]:
        name = transformation.name

        if name == "evaluate":
            return self._act_evaluate(graph)
        if name == "verify":
            return self._act_verify(graph)

        return graph, Consequence(penalty=0.1, valid=True)

    # ------------------------------------------------------------------
    # Evaluate
    # ------------------------------------------------------------------
    def _find_evaluable(self, graph: RealityGraph) -> Optional[str]:
        for expr in graph.entities("EXPRESSION"):
            left = self._get_child_by_role(graph, expr.id, "HAS_LEFT")
            right = self._get_child_by_role(graph, expr.id, "HAS_RIGHT")
            has_right = right is not None
            # Binary: both operands must be NUMBERs
            if has_right and left and left.etype == "NUMBER" and right.etype == "NUMBER":
                return expr.id
            # Unary: single operand must be NUMBER
            if not has_right and left and left.etype == "NUMBER":
                return expr.id
        return None

    def _get_child_by_role(self, graph: RealityGraph, parent_id: str,
                           role: str) -> Optional[Entity]:
        for rel in graph.relations():
            if rel.source == parent_id and rel.rtype == role:
                return graph.get_entity(rel.target)
        return None

    def _act_evaluate(self, graph: RealityGraph) -> Tuple[RealityGraph, Consequence]:
        after = graph.snapshot()
        expr_id = self._find_evaluable(after)
        if expr_id is None:
            return after, Consequence(penalty=0.5,
                explanation={"why": "no evaluable expression found"})

        expr = after.get_entity(expr_id)
        left = self._get_child_by_role(after, expr_id, "HAS_LEFT")
        right = self._get_child_by_role(after, expr_id, "HAS_RIGHT")

        op = expr.get("op")
        left_val = left.get("value")
        right_val = right.get("value") if right else None

        try:
            result = self._compute(op, left_val, right_val)
        except Exception as e:
            return after, Consequence(penalty=0.5,
                explanation={"why": f"computation failed: {e}"})

        result_id = f"num_{self._result_id_counter}"
        self._result_id_counter += 1
        after.add_entity(Entity(result_id, "NUMBER", {"value": result}))

        # Redirect parent relations to the new result
        for rel in list(after.relations()):
            if rel.target == expr_id and rel.rtype in ("HAS_LEFT", "HAS_RIGHT"):
                after.add_relation(Relation(rel.source, rel.rtype, result_id))
                after.remove_relation(rel.source, rel.rtype, rel.target)

        # Remove evaluated expression and its operands
        to_remove = [expr_id, left.id]
        if right:
            to_remove.append(right.id)
        for eid in to_remove:
            for rel in list(after.relations()):
                if rel.source == eid or rel.target == eid:
                    after.remove_relation(rel.source, rel.rtype, rel.target)
            after.remove_entity(eid)

        op_symbol = {"Add": "+", "Sub": "-", "Mult": "*", "Div": "/",
                     "Pow": "**", "USub": "-", "UAdd": "+"}.get(op, op)
        expr_str = f"{op_symbol}{left_val}" if right_val is None else f"{left_val} {op_symbol} {right_val}"
        return after, Consequence(
            reward=2.0, task_signal="TASK_PROGRESS",
            concept_signals={"PROGRESS": 1.0},
            explanation={"why": f"evaluated {expr_str} = {result}"},
        )

    # ------------------------------------------------------------------
    # Verify
    # ------------------------------------------------------------------
    def _act_verify(self, graph: RealityGraph) -> Tuple[RealityGraph, Consequence]:
        after = graph.snapshot()
        numbers = after.entities("NUMBER")
        exprs = after.entities("EXPRESSION")

        if numbers and not exprs:
            n = numbers[0]
            result = n.get("value")
            self.answer = result
            after.update_entity("goal", status="satisfied")
            return after, Consequence(
                reward=10.0, task_signal="TASK_SUCCESS",
                explanation={"why": f"Expression evaluated to {result}."},
            )

        if exprs:
            remaining = len(exprs)
            return after, Consequence(penalty=0.5,
                explanation={"why": f"Verification failed: {remaining} expression(s) remain"})

        return after, Consequence(penalty=0.5,
            explanation={"why": "Verification failed: no result found"})

    # ------------------------------------------------------------------
    # Computation
    # ------------------------------------------------------------------
    def _compute(self, op: str, left: Any, right: Any = None) -> Any:
        if op in _OP_FN:
            return _OP_FN[op](left, right)
        if op in _UNARY_OP_FN:
            return _UNARY_OP_FN[op](left)
        raise ValueError(f"unknown operator: {op}")

    # ------------------------------------------------------------------
    # Evaluation / concepts
    # ------------------------------------------------------------------
    def evaluate(self, graph: RealityGraph, mote_state: Dict) -> float:
        g = graph.get_entity("goal")
        return 10.0 if g and g.get("status") == "satisfied" else 0.0

    def concepts(self) -> List[str]:
        return ["QUANTITY", "EQUALS", "TRANSFORM"]
