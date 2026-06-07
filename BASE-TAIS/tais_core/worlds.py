"""
tais_core.worlds
================

Three tiny worlds demonstrating the universal reality substrate:

1. GridGraphWorld — spatial navigation with rewards and threats
2. SequencePredictionWorld — sequential pattern prediction
3. RuleSatisfactionWorld — rule-based constraint satisfaction
"""

from __future__ import annotations

import copy
import itertools
import random
from typing import Any, Dict, List, Optional, Set, Tuple

from .reality import (
    Consequence,
    Constraint,
    Entity,
    GraphDelta,
    GraphPattern,
    RealityGraph,
    Relation,
    Transformation,
    WorldInterface,
)

# ─── HELPERS ──────────────────────────────────────────────────────────────────

_TRANSFORM_NAMES: Dict[str, int] = {}


def _fresh(name: str) -> str:
    _TRANSFORM_NAMES[name] = _TRANSFORM_NAMES.get(name, 0) + 1
    return f"{name}_{_TRANSFORM_NAMES[name]}"


def _dirs() -> List[Tuple[int, int]]:
    return [(0, 1), (0, -1), (1, 0), (-1, 0)]


def _grid_id(x: int, y: int) -> str:
    return f"cell_{x}_{y}"


def _agent_pos(graph: RealityGraph) -> Tuple[int, int]:
    agent = graph.get_entity("agent")
    if agent is None:
        return (0, 0)
    return (agent.properties.get("x", 0), agent.properties.get("y", 0))


# ─── GRID GRAPH WORLD ────────────────────────────────────────────────────────


class GridGraphWorld(WorldInterface):
    """
    A 2D grid with resources (food), threats (predators), and obstacles.

    Entities:
        CELL     — each grid cell, properties: x, y, blocked (bool)
        AGENT   — the mote body, properties: x, y, energy
        RESOURCE — food items, properties: x, y, value
        THREAT — predators, properties: x, y, damage

    Relations:
        LEFT / RIGHT / ABOVE / BELOW — between cells
        AT — between agent/resource/threat and a cell
    """

    domain_name: str = "grid"

    def __init__(self, width: int = 8, height: int = 8):
        self.width = width
        self.height = height
        self._build_base_graph()

    def _build_base_graph(self):
        g = RealityGraph("grid", "grid_world")
        for y in range(self.height):
            for x in range(self.width):
                cell = Entity(
                    _grid_id(x, y), "CELL",
                    {"x": x, "y": y, "blocked": False},
                )
                g.add_entity(cell)

        for y in range(self.height):
            for x in range(self.width):
                if x + 1 < self.width:
                    g.add_relation(Relation(_grid_id(x, y), "RIGHT", _grid_id(x + 1, y), directed=False))
                if y + 1 < self.height:
                    g.add_relation(Relation(_grid_id(x, y), "ABOVE", _grid_id(x, y + 1), directed=False))

        agent = Entity("agent", "AGENT", {"x": 0, "y": 0, "energy": 100})
        g.add_entity(agent)
        g.add_relation(Relation("agent", "AT", _grid_id(0, 0)))

        self._seed_resources(g)
        self._graph = g

    def _seed_resources(self, g: RealityGraph, n_food: int = 5, n_threats: int = 3):
        cells = [(x, y) for x in range(self.width) for y in range(self.height) if (x, y) != (0, 0)]
        random.shuffle(cells)
        for i in range(n_food):
            x, y = cells[i]
            food = Entity(f"food_{i}", "RESOURCE", {"x": x, "y": y, "value": random.randint(1, 5)})
            g.add_entity(food)
            g.add_relation(Relation(food.id, "AT", _grid_id(x, y)))
        for i in range(n_threats):
            x, y = cells[n_food + i]
            threat = Entity(f"threat_{i}", "THREAT", {"x": x, "y": y, "damage": random.randint(1, 3)})
            g.add_entity(threat)
            g.add_relation(Relation(threat.id, "AT", _grid_id(x, y)))

    def observe(self, graph: RealityGraph, mote_position: Any = None) -> RealityGraph:
        if mote_position is not None:
            px, py = mote_position
        else:
            agent = self._graph.get_entity("agent")
            if agent:
                px, py = agent.properties.get("x", 0), agent.properties.get("y", 0)
            else:
                px, py = 0, 0
        nearby = set()
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                nx, ny = px + dx, py + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    nearby.add(_grid_id(nx, ny))
        nearby.add("agent")
        return self._graph.subgraph(nearby)

    def valid_actions(self, graph: RealityGraph, mote_state: Dict[str, Any]) -> List[Transformation]:
        agent = self._graph.get_entity("agent")
        if agent is None:
            return []
        x, y = agent.properties.get("x", 0), agent.properties.get("y", 0)
        actions = []
        for dx, dy in _dirs():
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                cell = graph.get_entity(_grid_id(nx, ny))
                if cell and not cell.properties.get("blocked", False):
                    name = f"move_{dx:+}_{dy:+}"
                    actions.append(Transformation(
                        name=name,
                        domain="grid",
                        universal_op="MOVE_TOWARD",
                        base_cost=1.0,
                        effects={"dx": dx, "dy": dy},
                    ))
        return actions

    def act(self, graph: RealityGraph, transformation: Transformation, mote_state: Dict[str, Any]) -> Tuple[RealityGraph, Consequence]:
        g = self._graph.snapshot()
        dx = transformation.effects.get("dx", 0)
        dy = transformation.effects.get("dy", 0)
        agent = g.get_entity("agent")
        if agent is None:
            return g, Consequence(reward=0, penalty=0, valid=False)
        x, y = agent.properties.get("x", 0), agent.properties.get("y", 0)
        nx, ny = x + dx, y + dy
        g.update_entity("agent", x=nx, y=ny)
        old_pos = _grid_id(x, y)
        new_pos = _grid_id(nx, ny)
        g.remove_relation("agent", "AT", old_pos)
        g.add_relation(Relation("agent", "AT", new_pos))

        reward = 0.0
        penalty = 0.0
        signals: Dict[str, float] = {}
        consumed = []
        for ent in list(g.entities()):
            if ent.id == "agent" or ent.etype not in ("RESOURCE", "THREAT"):
                continue
            if ent.properties.get("x") == nx and ent.properties.get("y") == ny:
                if ent.etype == "RESOURCE":
                    reward += ent.properties.get("value", 1)
                    signals["FOOD"] = signals.get("FOOD", 0) + 1
                    consumed.append(ent.id)
                elif ent.etype == "THREAT":
                    penalty += ent.properties.get("damage", 1)
                    signals["DANGER"] = signals.get("DANGER", 0) + 1
        for eid in consumed:
            g.remove_entity(eid)

        self._graph = g
        return g, Consequence(
            reward=reward,
            penalty=penalty,
            valid=True,
            concept_signals=signals,
        )

    def evaluate(self, graph: RealityGraph, mote_state: Dict[str, Any]) -> float:
        agent = self._graph.get_entity("agent")
        if agent is None:
            return 0.0
        return agent.properties.get("energy", 0) / 100.0

    def concepts(self) -> List[str]:
        return ["FOOD", "DANGER", "EMPTY", "WALL"]

    def reset(self):
        _TRANSFORM_NAMES.clear()
        self._build_base_graph()

    @property
    def graph(self) -> RealityGraph:
        return self._graph


# ─── SEQUENCE PREDICTION WORLD ──────────────────────────────────────────────


class SequencePredictionWorld(WorldInterface):
    """
    A world that generates a repeating pattern sequence.

    The mote observes elements and must predict the next one.

    Entities:
        SEQ_ELT  — each element in the observed sequence, properties: value, position
        MARKER   — points to the current position

    Relations:
        NEXT — between consecutive sequence elements
        AT   — between marker and current element
    """

    domain_name: str = "sequence"

    def __init__(self, pattern: Optional[List[str]] = None, seed: int = 0):
        self._rng = random.Random(seed)
        self._pattern: List[str] = pattern or ["A", "B", "C"]
        self._position = 0
        self._total_steps = 0
        self._build_initial_graph()

    def _build_initial_graph(self):
        g = RealityGraph("sequence", "seq_world")
        for i, val in enumerate(self._pattern):
            elt = Entity(f"elt_{i}", "SEQ_ELT", {"value": val, "position": i})
            g.add_entity(elt)
        for i in range(len(self._pattern) - 1):
            g.add_relation(Relation(f"elt_{i}", "NEXT", f"elt_{i + 1}"))
        g.add_entity(Entity("marker", "MARKER", {}))
        g.add_relation(Relation("marker", "AT", "elt_0"))
        self._graph = g

    def observe(self, graph: RealityGraph, mote_position: Any = None) -> RealityGraph:
        g = RealityGraph("sequence", "seq_observation")
        g.add_entity(Entity("marker", "MARKER", {}))
        marker_rels = self._graph.relations("AT")
        if marker_rels:
            mr = marker_rels[0]
            current = self._graph.get_entity(mr.target)
            if current:
                g.add_entity(copy.deepcopy(current))
                pos = current.properties.get("position", 0)
                for offset in range(-1, 3):
                    idx = pos + offset
                    if 0 <= idx < len(self._pattern):
                        e = self._graph.get_entity(f"elt_{idx}")
                        if e:
                            g.add_entity(copy.deepcopy(e))
                g.add_relation(copy.deepcopy(mr))
                for rel in self._graph.relations("NEXT"):
                    src = g.get_entity(rel.source)
                    tgt = g.get_entity(rel.target)
                    if src and tgt:
                        g.add_relation(copy.deepcopy(rel))
        return g

    def valid_actions(self, graph: RealityGraph, mote_state: Dict[str, Any]) -> List[Transformation]:
        return [
            Transformation("predict_A", "sequence", "PREDICT", base_cost=0.5, effects={"prediction": "A"}),
            Transformation("predict_B", "sequence", "PREDICT", base_cost=0.5, effects={"prediction": "B"}),
            Transformation("predict_C", "sequence", "PREDICT", base_cost=0.5, effects={"prediction": "C"}),
        ]

    def act(self, graph: RealityGraph, transformation: Transformation, mote_state: Dict[str, Any]) -> Tuple[RealityGraph, Consequence]:
        predicted = transformation.effects.get("prediction", "")
        actual_idx = self._position % len(self._pattern)
        actual = self._pattern[actual_idx]
        correct = predicted == actual

        g = self._graph.snapshot()
        next_idx = (self._position + 1) % len(self._pattern)
        if not g.get_entity(f"elt_{next_idx}"):
            elt = Entity(f"elt_{next_idx}", "SEQ_ELT", {"value": actual, "position": next_idx})
            g.add_entity(elt)
            prev_idx = (next_idx - 1) % len(self._pattern)
            g.add_relation(Relation(f"elt_{prev_idx}", "NEXT", f"elt_{next_idx}"))

        old_rel = g.relations("AT")
        if old_rel:
            g.remove_relation("marker", "AT", old_rel[0].target)
        g.add_relation(Relation("marker", "AT", f"elt_{next_idx}"))

        reward = 5.0 if correct else 0.0
        penalty = 0.0 if correct else 1.0
        signals = {"CORRECT": 1.0} if correct else {"WRONG": 1.0}

        self._position = next_idx
        self._total_steps += 1
        self._graph = g

        return g, Consequence(
            reward=reward,
            penalty=penalty,
            valid=True,
            concept_signals=signals,
            explanation={"predicted": predicted, "actual": actual, "position": self._position},
        )

    def evaluate(self, graph: RealityGraph, mote_state: Dict[str, Any]) -> float:
        if self._total_steps == 0:
            return 0.0
        return min(1.0, mote_state.get("score", 0) / max(1, self._total_steps))

    def concepts(self) -> List[str]:
        return ["CORRECT", "WRONG", "NEXT", "PATTERN"]

    def reset(self):
        self._position = 0
        self._total_steps = 0
        self._build_initial_graph()

    @property
    def graph(self) -> RealityGraph:
        return self._graph


# ─── RULE SATISFACTION WORLD ────────────────────────────────────────────────


class RuleSatisfactionWorld(WorldInterface):
    """
    A world of rules and propositions.

    The mote proposes propositions and the world checks which rules are satisfied.

    Entities:
        RULE  — a rule with a description
        PROP  — a proposition with a statement and truth value

    Relations:
        APPLIES_TO — between a rule and a proposition
        SATISFIES — between a proposition and a rule
        VIOLATES  — between a proposition and a rule
    """

    domain_name: str = "rules"

    def __init__(self, seed: int = 0):
        self._rng = random.Random(seed)
        self._rules: List[Entity] = []
        self._build_initial_graph()

    def _build_initial_graph(self):
        g = RealityGraph("rules", "rule_world")
        rule_data = [
            ("r1", "must_not_harm", "No entity may cause harm to another"),
            ("r2", "must_share", "Resources must be shared evenly"),
            ("r3", "must_obey_gravity", "Objects must be supported"),
        ]
        for rid, etype, desc in rule_data:
            r = Entity(rid, "RULE", {"description": desc})
            self._rules.append(r)
            g.add_entity(r)
        self._graph = g
        self._proposition_counter = 0

    def observe(self, graph: RealityGraph, mote_position: Any = None) -> RealityGraph:
        return self._graph.snapshot()

    def valid_actions(self, graph: RealityGraph, mote_state: Dict[str, Any]) -> List[Transformation]:
        actions = []
        for rid in ["r1", "r2", "r3"]:
            for val in [True, False]:
                name = f"propose_{rid}_{val}"
                actions.append(Transformation(
                    name=name,
                    domain="rules",
                    universal_op="TEST",
                    base_cost=0.5,
                    effects={"rule": rid, "satisfies": val},
                ))
        return actions

    def act(self, graph: RealityGraph, transformation: Transformation, mote_state: Dict[str, Any]) -> Tuple[RealityGraph, Consequence]:
        g = self._graph.snapshot()
        rule_id = transformation.effects.get("rule", "")
        satisfies = transformation.effects.get("satisfies", False)
        rule = g.get_entity(rule_id)
        if rule is None:
            return g, Consequence(reward=0, penalty=2, valid=False)

        self._proposition_counter += 1
        prop_id = f"prop_{self._proposition_counter}"
        desc = f"{rule.properties.get('description', '?')}={'yes' if satisfies else 'no'}"
        prop = Entity(prop_id, "PROP", {"statement": desc, "truth": satisfies})
        g.add_entity(prop)
        g.add_relation(Relation(prop_id, "APPLIES_TO", rule_id))
        if satisfies:
            g.add_relation(Relation(prop_id, "SATISFIES", rule_id))
        else:
            g.add_relation(Relation(prop_id, "VIOLATES", rule_id))

        satisfied_count = len(g.relations("SATISFIES"))
        total = max(1, satisfied_count + len(g.relations("VIOLATES")))
        score = satisfied_count / total
        reward = score * 5.0
        penalty = (1 - score) * 2.0

        self._graph = g

        return g, Consequence(
            reward=reward,
            penalty=penalty,
            valid=True,
            concept_signals={"COMPLIANCE": score},
            explanation={"rule": rule_id, "satisfied": satisfies, "score": score},
        )

    def evaluate(self, graph: RealityGraph, mote_state: Dict[str, Any]) -> float:
        satisfied = len(self._graph.relations("SATISFIES"))
        violated = len(self._graph.relations("VIOLATES"))
        total = satisfied + violated
        return satisfied / max(1, total)

    def concepts(self) -> List[str]:
        return ["RULE", "PROPOSITION", "COMPLIANCE", "VIOLATION"]

    def reset(self):
        self._proposition_counter = 0
        self._build_initial_graph()

    @property
    def graph(self) -> RealityGraph:
        return self._graph
