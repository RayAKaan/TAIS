import importlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tais_core.reality import (
    Consequence,
    Entity,
    RealityGraph,
    Relation,
    Transformation,
    WorldInterface,
)
from .parser import load_spec
from .validator import validate_spec


def import_dotted(path: str):
    module_name, attr_name = path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, attr_name)


def load_domain_from_spec(path: str | Path) -> "BuiltinDSLWorld | DeclarativeDSLWorld":
    spec = load_spec(path)
    spec = validate_spec(spec)
    if "backend" in spec:
        return BuiltinDSLWorld(spec)
    return DeclarativeDSLWorld(spec)


class BuiltinDSLWorld(WorldInterface):
    _world: WorldInterface
    _graph_factory: Any
    _graph_factory_kwargs: Dict[str, Any]

    def __init__(self, spec: Dict[str, Any]):
        self.spec = spec
        self.domain_name = spec.get("domain_name", spec["name"].lower())
        backend = spec["backend"]
        world_cls = import_dotted(backend["world_class"])
        self._world = world_cls()
        self._graph_factory = import_dotted(backend["graph_factory"])
        self._graph_factory_kwargs = backend.get("graph_factory_kwargs", {})

    def initial_graph(self) -> RealityGraph:
        return self._graph_factory(**self._graph_factory_kwargs)

    def observe(self, graph: RealityGraph, mote_position: Any) -> RealityGraph:
        return self._world.observe(graph, mote_position)

    def valid_actions(self, graph: RealityGraph, mote_state: Dict[str, Any]) -> List[Transformation]:
        return self._world.valid_actions(graph, mote_state)

    def act(self, graph: RealityGraph, transformation: Transformation, mote_state: Dict[str, Any]) -> Tuple[RealityGraph, Consequence]:
        return self._world.act(graph, transformation, mote_state)

    def evaluate(self, graph: RealityGraph, mote_state: Dict[str, Any]) -> float:
        return self._world.evaluate(graph, mote_state)

    def concepts(self) -> List[str]:
        if hasattr(self._world, "concepts"):
            return self._world.concepts()
        return []


class DeclarativeDSLWorld(WorldInterface):
    _spec: Dict[str, Any]
    domain_name: str

    def __init__(self, spec: Dict[str, Any]):
        self._spec = spec
        self.domain_name = spec.get("domain_name", spec["name"].lower())

    def initial_graph(self) -> RealityGraph:
        g = self._spec.get("graph", {})
        graph_id = g.get("id", f"{self.domain_name}_initial")
        graph = RealityGraph(domain=self.domain_name, label=graph_id)
        for edef in g.get("entities", []):
            entity = Entity(
                id=edef["id"],
                etype=edef.get("type", "ENTITY"),
                properties=edef.get("properties", {}),
            )
            graph.add_entity(entity)
        for rdef in g.get("relations", []):
            rel = Relation(
                source=rdef["source"],
                rtype=rdef["type"],
                target=rdef["target"],
                directed=rdef.get("directed", True),
                properties=rdef.get("properties", {}),
            )
            graph.add_relation(rel)
        return graph

    def observe(self, graph: RealityGraph, mote_position: Any) -> RealityGraph:
        mote_id = str(mote_position) if mote_position else None
        if mote_id and mote_id in graph:
            hops = self._spec.get("world_defaults", {}).get("observe_hops", 1)
            return graph.neighborhood(mote_id, hops=hops)
        return graph

    def valid_actions(self, graph: RealityGraph, mote_state: Dict[str, Any]) -> List[Transformation]:
        actions = []
        for adef in self._spec.get("actions", []):
            actions.append(Transformation(
                name=adef["name"],
                domain=self.domain_name,
                universal_op=adef["universal_op"],
                base_cost=float(adef.get("base_cost", 1.0)),
                role_hint=adef.get("role_hint"),
            ))
        return actions

    def act(self, graph: RealityGraph, transformation: Transformation, mote_state: Dict[str, Any]) -> Tuple[RealityGraph, Consequence]:
        for adef in self._spec.get("actions", []):
            if adef["name"] == transformation.name:
                return self._apply_declarative_effect(graph, adef)
        return graph, Consequence(
            penalty=1.0,
            valid=False,
            concept_signals={"BAD": 1.0},
            explanation={"why": f"unknown action {transformation.name}"},
            task_signal="TASK_FAILURE",
        )

    def _apply_declarative_effect(self, graph: RealityGraph, adef: Dict[str, Any]) -> Tuple[RealityGraph, Consequence]:
        before = graph.snapshot()
        after = graph.snapshot()
        effects = adef.get("effects", {})
        for eid, eprops in _iter_entities_to_add(effects):
            after.add_entity(Entity(id=eid, etype=eprops.get("type", "ENTITY"), properties=eprops.get("properties", {})))
        for rdef in effects.get("add_relations", []):
            rel = Relation(
                source=rdef["source"],
                rtype=rdef["type"],
                target=rdef["target"],
                directed=rdef.get("directed", True),
                properties=rdef.get("properties", {}),
            )
            after.add_relation(rel)
        for sp in effects.get("set_properties", []):
            after.update_entity(sp["id"], **sp.get("properties", {}))
        delta = before.diff(after)
        consequence = Consequence(
            reward=float(adef.get("reward", 0.0)),
            penalty=float(adef.get("penalty", 0.0)),
            valid=adef.get("valid", True),
            concept_signals=adef.get("concept_signals", {}),
            task_signal=adef.get("task_signal"),
            graph_delta=delta,
        )
        return after, consequence

    def evaluate(self, graph: RealityGraph, mote_state: Dict[str, Any]) -> float:
        eval_block = self._spec.get("evaluation")
        if eval_block:
            success_entity = eval_block.get("success_entity")
            if success_entity and graph.get_entity(success_entity):
                return float(eval_block.get("success_score", 10.0))
            return float(eval_block.get("default_score", 0.0))
        return 0.0

    def concepts(self) -> List[str]:
        seen = set()
        for action in self._spec.get("actions", []):
            for key in action.get("concept_signals", {}):
                seen.add(key)
        return sorted(seen)


def _iter_entities_to_add(effects: Dict[str, Any]):
    for edef in effects.get("add_entities", []):
        yield edef["id"], edef
