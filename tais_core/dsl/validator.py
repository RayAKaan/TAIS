from typing import Any, Dict, List

from tais_core.reality import Transformation


class DomainSpecError(ValueError):
    """Raised when a domain spec is invalid."""


_REQUIRED_TOP = {"name", "version"}


def validate_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    for field in _REQUIRED_TOP:
        if field not in spec:
            raise DomainSpecError(f"Missing required top-level field: {field!r}")
    has_backend = "backend" in spec
    has_declarative = all(k in spec for k in ("entities", "relations", "actions", "graph"))
    if not has_backend and not has_declarative:
        raise DomainSpecError(
            "Spec must have either 'backend' (builtin-backed) or complete declarative "
            "fields ('entities', 'relations', 'actions', 'graph')"
        )
    if has_backend:
        _validate_backend(spec)
    if has_declarative:
        _validate_declarative(spec)
    return spec


def _validate_backend(spec: Dict[str, Any]) -> None:
    backend = spec["backend"]
    if not isinstance(backend, dict):
        raise DomainSpecError("'backend' must be a dict")
    for field in ("world_class", "graph_factory"):
        if field not in backend:
            raise DomainSpecError(f"Missing 'backend.{field}'")
        if not isinstance(backend[field], str):
            raise DomainSpecError(f"'backend.{field}' must be a string")
    if "graph_factory_kwargs" in backend and not isinstance(backend["graph_factory_kwargs"], dict):
        raise DomainSpecError("'backend.graph_factory_kwargs' must be a dict")


def _validate_declarative(spec: Dict[str, Any]) -> None:
    entities = spec.get("entities", {})
    relations = spec.get("relations", {})
    actions = spec.get("actions", [])
    graph = spec.get("graph", {})

    if not isinstance(entities, dict):
        raise DomainSpecError("'entities' must be a dict")
    if not isinstance(relations, dict):
        raise DomainSpecError("'relations' must be a dict")
    if not isinstance(actions, list):
        raise DomainSpecError("'actions' must be a list")
    if not isinstance(graph, dict):
        raise DomainSpecError("'graph' must be a dict")

    action_names: List[str] = []
    for i, action in enumerate(actions):
        if not isinstance(action, dict):
            raise DomainSpecError(f"actions[{i}] must be a dict")
        if "name" not in action:
            raise DomainSpecError(f"actions[{i}] missing 'name'")
        if "universal_op" not in action:
            raise DomainSpecError(f"actions[{i}] missing 'universal_op'")
        op = action["universal_op"]
        valid_ops = getattr(Transformation, "VALID_OPS", frozenset())
        if valid_ops and op not in valid_ops:
            raise DomainSpecError(
                f"actions[{i}].universal_op {op!r} is not valid. "
                f"Valid ops: {sorted(valid_ops)}"
            )
        action_names.append(action["name"])

    action_roles = spec.get("action_roles", {})
    if action_roles is not None and not isinstance(action_roles, dict):
        raise DomainSpecError("'action_roles' must be a dict")
    if isinstance(action_roles, dict):
        for role_name, action_name in action_roles.items():
            if action_name not in action_names:
                raise DomainSpecError(
                    f"action_roles.{role_name} points to nonexistent action {action_name!r}"
                )

    ge = graph.get("entities", [])
    if not isinstance(ge, list):
        raise DomainSpecError("'graph.entities' must be a list")
    gr = graph.get("relations", [])
    if not isinstance(gr, list):
        raise DomainSpecError("'graph.relations' must be a list")
