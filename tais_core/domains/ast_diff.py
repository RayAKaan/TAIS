"""AST diff utility for comparing buggy vs correct Python code."""

import ast
from typing import Any, Dict, List, Optional


class ASTPatch:
    """Describes a single change needed to fix code at an AST node."""

    def __init__(self, path: str, attr: str, old_value: Any, new_value: Any,
                 node_type: str, description: str = ""):
        self.path = path
        self.attr = attr
        self.old_value = old_value
        self.new_value = new_value
        self.node_type = node_type
        self.description = description or f"change {node_type}.{attr} from {old_value!r} to {new_value!r}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "attr": self.attr,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "node_type": self.node_type,
            "description": self.description,
        }


def ast_diff(buggy_code: str, correct_code: str) -> List[ASTPatch]:
    """Compare two Python source strings and return a list of ASTPatches."""
    try:
        buggy_ast = ast.parse(buggy_code)
        correct_ast = ast.parse(correct_code)
    except SyntaxError:
        return []

    patches: List[ASTPatch] = []
    _walk_diff(buggy_ast, correct_ast, "root", patches)
    return patches


def _walk_diff(node_a: ast.AST, node_b: ast.AST, path: str, patches: List[ASTPatch]):
    if type(node_a) != type(node_b):
        return

    for field_name, field_value in ast.iter_fields(node_a):
        if isinstance(field_value, ast.AST):
            continue
        if isinstance(field_value, list):
            if field_value and isinstance(field_value[0], ast.AST):
                field_b = getattr(node_b, field_name, None)
                if field_b and len(field_value) == len(field_b):
                    for i, (fa, fb) in enumerate(zip(field_value, field_b)):
                        if type(fa) != type(fb):
                            old_name = type(fa).__name__
                            new_name = type(fb).__name__
                            patches.append(ASTPatch(
                                path=path, attr=field_name,
                                old_value=old_name, new_value=new_name,
                                node_type=type(node_a).__name__,
                                description=f"change operator from {old_name} to {new_name}",
                            ))
            continue
        field_b = getattr(node_b, field_name, None)
        if field_value != field_b:
            patches.append(ASTPatch(
                path=path, attr=field_name,
                old_value=field_value, new_value=field_b,
                node_type=type(node_a).__name__,
            ))

    children_a = list(ast.iter_child_nodes(node_a))
    children_b = list(ast.iter_child_nodes(node_b))
    for i, (ca, cb) in enumerate(zip(children_a, children_b)):
        _walk_diff(ca, cb, f"{path}_{i}", patches)


def apply_patches_to_source(source_code: str, patches: List[ASTPatch]) -> str:
    """Apply patches to a parsed AST and return the fixed source code."""
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return source_code

    for patch in patches:
        node = _navigate_ast(tree, patch.path)
        if node is None:
            continue

        field_value = getattr(node, patch.attr, None)
        if field_value is None:
            continue

        if patch.attr in ("ops", "op") and isinstance(field_value, (list, ast.AST)):
            op_cls = getattr(ast, patch.new_value, None)
            if op_cls is None:
                continue
            if isinstance(field_value, list):
                setattr(node, patch.attr, [op_cls()])
            else:
                setattr(node, patch.attr, op_cls())
        else:
            setattr(node, patch.attr, patch.new_value)

    return ast.unparse(tree)


def _navigate_ast(node: ast.AST, path: str) -> Optional[ast.AST]:
    """Navigate to an AST node by path like 'root_0_1'."""
    parts = path.split("_")
    if parts[0] != "root":
        return None
    current = node
    for part in parts[1:]:
        index = int(part)
        children = list(ast.iter_child_nodes(current))
        if index < len(children):
            current = children[index]
        else:
            return None
    return current
