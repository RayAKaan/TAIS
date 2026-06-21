"""Generic Code Synthesis domain for custom user code.

Supports two modes:
  1. Dynamic (target_code provided) — computes AST diff, creates apply_patch_N actions
  2. Static (no target_code)         — falls back to hardcoded fix_operator behaviour
"""

from __future__ import annotations
import ast
from typing import Any, Dict, List, Tuple, Optional
from ..reality import Consequence, Entity, RealityGraph, Relation, Transformation, WorldInterface


def make_custom_code_graph(**kwargs):
    return CustomCodeWorld(**kwargs).initial_graph()


class CustomCodeWorld(WorldInterface):
    domain_name = "codesynt"

    def __init__(self, source_code: str = "def solve(): return False",
                 target_code: str = ""):
        self.source = source_code
        self.target = target_code
        try:
            self.tree = ast.parse(source_code)
        except SyntaxError:
            self.tree = ast.parse("def error(): pass")

        self.patches = []
        self.applied_patches: set[int] = set()
        self.fixed_source: Optional[str] = None
        self.inference_explanation: str = ""

        if target_code:
            from .ast_diff import ast_diff
            self.patches = ast_diff(source_code, target_code)
        else:
            from .bug_inference import infer_fix
            fixed, explanation, patch_dicts = infer_fix(source_code)
            if patch_dicts:
                from .ast_diff import ASTPatch
                for pd in patch_dicts:
                    self.patches.append(ASTPatch(
                        path=pd["path"],
                        attr=pd["attr"],
                        old_value=pd["old_value"],
                        new_value=pd["new_value"],
                        node_type=pd["node_type"],
                        description=pd["description"],
                    ))
                self.inference_explanation = explanation
                self.fixed_source = fixed

    # ------------------------------------------------------------------
    # Graph building
    # ------------------------------------------------------------------
    def initial_graph(self) -> RealityGraph:
        g = RealityGraph(self.domain_name, "custom_code_ast")
        self._build_graph(self.tree, g, "root")
        g.add_entity(Entity("goal", "REQUIREMENT", {"status": "unresolved"}))

        for i, patch in enumerate(self.patches):
            g.add_entity(Entity(f"patch_{i}", "PATCH", {
                "description": patch.description,
                "applied": False,
            }))
        return g

    def _build_graph(self, node: ast.AST, graph: RealityGraph, node_id: str):
        etype = type(node).__name__
        props: Dict[str, Any] = {"type": etype}
        for field_name, field_value in ast.iter_fields(node):
            if isinstance(field_value, ast.AST):
                continue
            if isinstance(field_value, list):
                if field_value and isinstance(field_value[0], ast.AST):
                    props[field_name] = type(field_value[0]).__name__
                continue
            props[field_name] = field_value

        graph.add_entity(Entity(node_id, etype, props))
        for i, child in enumerate(ast.iter_child_nodes(node)):
            child_id = f"{node_id}_{i}"
            self._build_graph(child, graph, child_id)
            graph.add_relation(Relation(node_id, "CONTAINS", child_id))

    # ------------------------------------------------------------------
    # World interface
    # ------------------------------------------------------------------
    def observe(self, graph: RealityGraph, mote_position: Any) -> RealityGraph:
        return graph.neighborhood(mote_position or "root", hops=3)

    def valid_actions(self, graph: RealityGraph,
                      mote_state: Dict) -> List[Transformation]:
        actions: List[Transformation] = []

        if self.patches:
            for i in range(len(self.patches)):
                if i not in self.applied_patches:
                    actions.append(Transformation(
                        f"apply_patch_{i}", self.domain_name, "TRANSFORM",
                        base_cost=0.3, role_hint="TRANSFORM_TOWARD_GOAL",
                    ))
            if self.applied_patches:
                actions.append(Transformation(
                    "verify", self.domain_name, "VERIFY",
                    base_cost=0.2, role_hint="VERIFY_UNCERTAIN",
                ))
        else:
            actions.extend([
                Transformation("fix_operator", self.domain_name, "TRANSFORM",
                               base_cost=0.5, role_hint="TRANSFORM_TOWARD_GOAL"),
                Transformation("run_validation", self.domain_name, "VERIFY",
                               base_cost=0.3, role_hint="VERIFY_UNCERTAIN"),
                Transformation("refactor", self.domain_name, "MUTATE",
                               base_cost=0.4, role_hint="MAINTAIN_STABLE"),
            ])

        return actions

    def act(self, graph: RealityGraph, transformation: Transformation,
            mote_state: Dict) -> Tuple[RealityGraph, Consequence]:
        after = graph.snapshot()
        name = transformation.name

        # ---- dynamic mode ----
        if self.patches:
            if name.startswith("apply_patch_"):
                return self._apply_patch(after, name)
            if name == "verify":
                return self._verify(after)
            return graph, Consequence(penalty=0.1, valid=True)

        # ---- static fallback ----
        if name == "fix_operator":
            targets = [e for e in after.entities()
                       if "op" in e.properties or "ops" in e.properties]
            if targets:
                target = targets[0]
                prop = "ops" if "ops" in target.properties else "op"
                after.update_entity(target.id, **{prop: "CORRECTED"})
                after.add_entity(Entity("patch", "LOGIC_FIX", {"status": "applied"}))
                return after, Consequence(
                    reward=5.0, task_signal="TASK_PROGRESS",
                    explanation={"why": "Applied structural logic patch."},
                )

        if name == "run_validation":
            if any(e.etype == "LOGIC_FIX" for e in graph.entities()):
                after.update_entity("goal", status="satisfied")
                return after, Consequence(
                    reward=10.0, task_signal="TASK_SUCCESS",
                    explanation={"why": "Code verified. Custom logic resolved."},
                )
            return graph, Consequence(
                penalty=1.0,
                explanation={"why": "Validation failed: code remains buggy."},
            )

        return graph, Consequence(penalty=0.1, valid=True)

    # ------------------------------------------------------------------
    # Dynamic patch helpers
    # ------------------------------------------------------------------
    def _apply_patch(self, after: RealityGraph,
                     action_name: str) -> Tuple[RealityGraph, Consequence]:
        idx = int(action_name.split("_")[-1])
        if idx >= len(self.patches) or idx in self.applied_patches:
            return after, Consequence(penalty=0.1, valid=True)

        patch = self.patches[idx]
        target = after.get_entity(patch.path)
        if target is None:
            return after, Consequence(
                penalty=0.5,
                explanation={"why": f"target node {patch.path} not found"},
            )

        after.update_entity(patch.path, **{patch.attr: patch.new_value})
        self.applied_patches.add(idx)

        patch_ent = after.get_entity(f"patch_{idx}")
        if patch_ent:
            after.update_entity(f"patch_{idx}", applied=True)

        return after, Consequence(
            reward=2.0, task_signal="TASK_PROGRESS",
            concept_signals={"PROGRESS": 1.0},
            explanation={"why": patch.description},
        )

    def _verify(self, after: RealityGraph) -> Tuple[RealityGraph, Consequence]:
        all_applied = (len(self.applied_patches) == len(self.patches)
                       and len(self.patches) > 0)
        if all_applied:
            after.update_entity("goal", status="satisfied")
            if not self.fixed_source:
                from .ast_diff import apply_patches_to_source
                self.fixed_source = apply_patches_to_source(self.source, self.patches)
            why = self.inference_explanation or "All patches applied. Code matches target."
            return after, Consequence(
                reward=10.0, task_signal="TASK_SUCCESS",
                explanation={"why": why},
            )
        remaining = len(self.patches) - len(self.applied_patches)
        num_patches = len(self.patches)
        return after, Consequence(
            penalty=0.5,
            explanation={
                "why": f"Verification failed: {remaining}/{num_patches} patch(es) remaining",
            },
        )

    # ------------------------------------------------------------------
    # Evaluation / concepts
    # ------------------------------------------------------------------
    def evaluate(self, graph: RealityGraph, mote_state: Dict) -> float:
        g = graph.get_entity("goal")
        return 10.0 if g and g.get("status") == "satisfied" else 0.0

    def concepts(self) -> List[str]:
        return ["GOOD", "SUCCESS", "PROGRESS"]
