"""Infer correct Python code from buggy code by detecting common bug patterns.

No target code needed — TAIS analyzes the source autonomously.
Walks the AST with path tracking so patches have graph-compatible paths.
"""

import ast
from typing import Any, Dict, List, Optional, Tuple


def infer_fix(source_code: str) -> Tuple[str, str, List[Dict[str, Any]]]:
    """Analyze source code, detect bugs, return (fixed_code, explanation, patches).

    Returns:
        Tuple of (fixed_source_code, explanation_string, patch_dicts).
        Each patch dict has 'path' (graph-compatible like 'root_0_1_0'),
        'attr', 'old_value', 'new_value', 'node_type', 'description'.
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return source_code, "Syntax error — cannot analyze.", []

    parent_map = _build_parent_map(tree)

    # Each raw patch: (path, attr, old_value, new_value, node_type, description)
    raw_patches: List[Tuple[str, str, Any, Any, str, str]] = []

    def _walk(node: ast.AST, path: str):
        if isinstance(node, ast.Compare) and node.ops:
            _check_comparator_bug(node, path, parent_map, raw_patches)
        elif isinstance(node, ast.BinOp):
            _check_arithmetic_bug(node, path, parent_map, raw_patches)
        for i, child in enumerate(ast.iter_child_nodes(node)):
            _walk(child, f"{path}_{i}")

    _walk(tree, "root")

    if not raw_patches:
        return source_code, "No common bug pattern detected.", []

    # Apply patches to a fresh tree for the fixed source
    try:
        fixed_tree = ast.parse(source_code)
        for path, attr, old_val, new_val, node_type, desc in raw_patches:
            target = _navigate_ast(fixed_tree, path)
            if target is None:
                continue
            field_value = getattr(target, attr, None)
            if field_value is None:
                continue
            if attr in ("ops", "op") and isinstance(field_value, (list, ast.AST)):
                op_cls = getattr(ast, new_val, None)
                if op_cls is None:
                    continue
                if isinstance(field_value, list):
                    setattr(target, attr, [op_cls()])
                else:
                    setattr(target, attr, op_cls())
            else:
                setattr(target, attr, new_val)
        fixed = ast.unparse(fixed_tree)
    except Exception:
        fixed = source_code

    patch_dicts = []
    for path, attr, old_val, new_val, node_type, desc in raw_patches:
        patch_dicts.append({
            "path": path,
            "attr": attr,
            "old_value": old_val,
            "new_value": new_val,
            "node_type": node_type,
            "description": desc,
        })

    explanation = _build_explanation(patch_dicts)
    return fixed, explanation, patch_dicts


def _navigate_ast(node: ast.AST, path: str) -> Optional[ast.AST]:
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


def _build_parent_map(tree: ast.AST) -> Dict[int, ast.AST]:
    parent_map: Dict[int, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parent_map[id(child)] = parent
    return parent_map


def _get_enclosing_func(node: ast.AST,
                        parent_map: Dict[int, ast.AST]) -> Optional[ast.FunctionDef]:
    while id(node) in parent_map:
        node = parent_map[id(node)]
        if isinstance(node, ast.FunctionDef):
            return node
    return None


# ─── detector: comparator bugs ──────────────────────────────────────────────

_INCLUSIVE_FUNCS = frozenset({
    "max", "maximum", "largest", "greatest", "longest", "tallest", "biggest",
    "min", "minimum", "smallest", "shortest", "least",
    "search", "binary_search", "find", "index_of", "index",
    "contains", "has_element", "has_value",
    "upper_bound", "lower_bound", "bound",
})

_EQUALITY_FUNCS = frozenset({
    "equals", "equal", "same_as", "matches", "equivalent",
})


def _check_comparator_bug(
    node: ast.Compare,
    path: str,
    parent_map: Dict[int, ast.AST],
    patches: List[Tuple[str, str, Any, Any, str, str]],
):
    op = node.ops[0]
    op_name = type(op).__name__
    func = _get_enclosing_func(node, parent_map)
    if func is None:
        return

    fn = func.name.lower()

    # != → ==  (equality check)
    if op_name == "NotEq" and fn in _EQUALITY_FUNCS:
        patches.append((path, "ops", "NotEq", "Eq", type(node).__name__,
            f"change != to == in '{func.name}' (function name suggests equality)"))
        return

    # < → <=  (inclusive bound)
    if op_name == "Lt" and fn in _INCLUSIVE_FUNCS:
        patches.append((path, "ops", "Lt", "LtE", type(node).__name__,
            f"change < to <= in '{func.name}' (likely needs inclusive bound)"))
        return

    # > → >=  (inclusive bound)
    if op_name == "Gt" and fn in _INCLUSIVE_FUNCS:
        patches.append((path, "ops", "Gt", "GtE", type(node).__name__,
            f"change > to >= in '{func.name}' (likely needs inclusive bound)"))
        return

    # <= → <  (strict bound when comparing against 0)
    if op_name == "LtE" and fn in _INCLUSIVE_FUNCS:
        has_zero = any(
            isinstance(c, ast.Constant) and c.value == 0
            for c in ast.walk(node)
        )
        if has_zero:
            patches.append((path, "ops", "LtE", "Lt", type(node).__name__,
                f"change <= to < in '{func.name}' (bound with 0 suggests strict)"))
        return

    # == → !=  (logic inversion in disjoint/different functions)
    if op_name == "Eq" and any(w in fn for w in ("disjoint", "different", "not_equal")):
        patches.append((path, "ops", "Eq", "NotEq", type(node).__name__,
            f"change == to != in '{func.name}' (logic inversion)"))
        return


# ─── detector: arithmetic bugs ──────────────────────────────────────────────

_ARITHMETIC_HINTS = {
    "Add": {"subtract", "difference", "minus", "decrease", "reduce", "less"},
    "Sub": {"add", "sum", "plus", "total", "increase", "append"},
    "Mult": {"divide", "quotient", "half"},
    "Div": {"multiply", "product", "double", "triple"},
}

_OPPOSITE = {
    "Add": "Sub", "Sub": "Add",
    "Mult": "Div", "Div": "Mult",
}


def _check_arithmetic_bug(
    node: ast.BinOp,
    path: str,
    parent_map: Dict[int, ast.AST],
    patches: List[Tuple[str, str, Any, Any, str, str]],
):
    op_name = type(node.op).__name__
    func = _get_enclosing_func(node, parent_map)
    if func is None:
        return

    hints = _ARITHMETIC_HINTS.get(op_name, set())
    if not hints:
        return

    fn = func.name.lower()
    matched = [w for w in hints if w in fn]
    if not matched:
        return

    new_op = _OPPOSITE.get(op_name)
    if new_op:
        patches.append((path, "op", op_name, new_op, type(node).__name__,
            f"change {op_name} to {new_op} in '{func.name}' (name suggests {matched[0]})"))


# ─── explanation builder ────────────────────────────────────────────────────

def _build_explanation(patch_dicts: List[Dict[str, Any]]) -> str:
    if not patch_dicts:
        return "No bugs detected."
    parts = [p["description"] for p in patch_dicts]
    return "TAIS analysis: " + "; ".join(parts) + "."
