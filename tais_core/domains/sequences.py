"""Tiny sequence prediction validation domain."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from ..reality import Consequence, Entity, RealityGraph, Relation, Transformation, WorldInterface


def make_sequence_graph(values=None, target_next: int | None = None) -> RealityGraph:
    values = values or [1, 2, 3]
    if target_next is None:
        target_next = values[-1] + (values[-1] - values[-2] if len(values) > 1 else 1)
    g = RealityGraph("sequence", "arithmetic")
    for i, v in enumerate(values):
        g.add_entity(Entity(f"v{i}", "VALUE", {"index": i, "value": v}))
        if i > 0:
            g.add_relation(Relation(f"v{i-1}", "NEXT", f"v{i}"))
            g.add_relation(Relation(f"v{i-1}", "DELTA", f"v{i}", {"delta": v - values[i-1]}))
    g.add_entity(Entity("target", "TARGET", {"next": target_next, "hidden": True}))
    return g


class SequenceWorld(WorldInterface):
    domain_name = "sequence"

    def observe(self, graph: RealityGraph, mote_position: Any) -> RealityGraph:
        # Hide target answer from observation.
        ids = {e.id for e in graph.entities() if e.etype != "TARGET"}
        return graph.subgraph(ids)

    def _last_value(self, graph: RealityGraph) -> int:
        vals = [e for e in graph.entities("VALUE")]
        vals.sort(key=lambda e: e.get("index"))
        return int(vals[-1].get("value"))

    def _target(self, graph: RealityGraph) -> int:
        t = graph.entities("TARGET")[0]
        return int(t.get("next"))

    def valid_actions(self, graph: RealityGraph, mote_state: Dict) -> List[Transformation]:
        last = self._last_value(graph)
        actions = []
        for delta in range(-2, 4):
            pred = last + delta
            actions.append(Transformation(
                name=f"predict_delta_{delta}",
                domain=self.domain_name,
                universal_op="PREDICT",
                base_cost=0.2,
                effects={"prediction": pred, "delta": delta},
            ))
        return actions

    def act(self, graph: RealityGraph, transformation: Transformation, mote_state: Dict) -> Tuple[RealityGraph, Consequence]:
        prediction = int(transformation.effects.get("prediction", 0))
        target = self._target(graph)
        error = abs(prediction - target)
        if error == 0:
            after = graph.snapshot()
            idx = len(after.entities("VALUE"))
            after.add_entity(Entity(f"v{idx}", "VALUE", {"index": idx, "value": prediction}))
            after.add_relation(Relation(f"v{idx-1}", "NEXT", f"v{idx}"))
            return after, Consequence(
                reward=4.0,
                valid=True,
                concept_signals={"GOOD": 1.0, "CONFIRM": 0.7},
                explanation={"why": "correct next value", "prediction": prediction, "target": target},
                graph_delta=graph.diff(after),
            )
        return graph, Consequence(
            penalty=min(4.0, float(error)),
            valid=True,
            concept_signals={"BAD": 0.7, "DENY": 0.6},
            explanation={"why": "wrong next value", "prediction": prediction, "target": target, "error": error},
        )

    def evaluate(self, graph: RealityGraph, mote_state: Dict) -> float:
        return float(len(graph.entities("VALUE")))

    def concepts(self) -> List[str]:
        return ["GOOD", "BAD", "CONFIRM", "DENY", "PREDICT"]
