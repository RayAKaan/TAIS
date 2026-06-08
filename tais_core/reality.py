"""
tais_core.reality
=================

The Universal Reality Substrate.

Every domain — chemistry, math, physics, rules, language — is represented as a
RealityGraph instantiated over the same base objects. Motes do not need domain
specific classes. They see entities, relations, transformations, constraints,
and consequences.

Base objects:
    Entity          — a node: anything that exists
    Relation        — a typed edge between entities
    GraphPattern    — a reusable subgraph fragment
    Transformation  — a candidate action
    Constraint      — a rule the world enforces
    Consequence     — what the world returns after an action

Core graph operations:
    diff()          — what changed between two graph states
    distance()      — approximate structural difference
    analogize()     — map a learned pattern onto a new graph/domain
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Set, Tuple


# ─── ENTITY ──────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Entity:
    """
    A node in the RealityGraph.

    id:         unique string within a graph, e.g. "atom_C1", "expr_x2"
    etype:      semantic type tag, e.g. "ATOM", "SYMBOL", "BODY", "RULE"
    properties: arbitrary key-value store. Domains define property semantics.
    """

    id: str
    etype: str
    properties: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.properties.get(key, default)

    def set(self, key: str, value: Any) -> "Entity":
        """Immutable-style update: return a new entity with one changed property."""
        props = dict(self.properties)
        props[key] = value
        return Entity(self.id, self.etype, props)

    def matches_pattern(self, pattern: "Entity") -> bool:
        """Wildcard etype '*' matches any. Pattern property value None is wildcard."""
        if pattern.etype != "*" and pattern.etype != self.etype:
            return False
        for k, v in pattern.properties.items():
            if v is not None and self.properties.get(k) != v:
                return False
        return True

    def fingerprint(self) -> str:
        payload = f"{self.etype}|{json.dumps(self.properties, sort_keys=True, default=str)}"
        return hashlib.md5(payload.encode()).hexdigest()[:10]

    def __hash__(self) -> int:  # frozen dataclass cannot hash dict by default
        return hash(self.id)


# ─── RELATION ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Relation:
    """
    A typed directed edge between two entities.

    source:     entity id
    rtype:      relation type, e.g. "BONDED_TO", "EQUALS", "SATISFIES"
    target:     entity id
    properties: optional metadata such as weight/confidence/time
    directed:   if False, RealityGraph stores reverse edge too
    """

    source: str
    rtype: str
    target: str
    properties: Dict[str, Any] = field(default_factory=dict)
    directed: bool = True

    def get(self, key: str, default: Any = None) -> Any:
        return self.properties.get(key, default)

    def matches_pattern(self, pattern: "Relation") -> bool:
        if pattern.rtype != "*" and pattern.rtype != self.rtype:
            return False
        if pattern.source != "*" and pattern.source != self.source:
            return False
        if pattern.target != "*" and pattern.target != self.target:
            return False
        for k, v in pattern.properties.items():
            if v is not None and self.properties.get(k) != v:
                return False
        return True

    def key(self) -> Tuple[str, str, str]:
        return (self.source, self.rtype, self.target)

    def __hash__(self) -> int:
        return hash(self.key())


# ─── GRAPH PATTERN ───────────────────────────────────────────────────────────

@dataclass
class GraphPattern:
    """
    Reusable subgraph fragment.

    Used for transformation preconditions, pattern memory, and cross-domain
    analogy. Entity/Relation objects may use wildcards.
    """

    entities: List[Entity]
    relations: List[Relation]
    name: Optional[str] = None
    confidence: float = 0.5
    consequence_signature: Optional[str] = None  # GOOD | BAD | DANGER | NEUTRAL
    source_domain: Optional[str] = None
    # v6 transfer bridge: what action made this pattern useful/harmful?
    successful_action_op: Optional[str] = None
    successful_action_name: Optional[str] = None
    successful_action_cost: float = 0.0
    failed_action_ops: List[str] = field(default_factory=list)
    failed_action_names: List[str] = field(default_factory=list)
    successful_action_role: Optional[str] = None
    failed_action_roles: List[str] = field(default_factory=list)
    mean_outcome_net: float = 0.0
    times_matched: int = 0
    times_confirmed: int = 0

    def entity_types(self) -> FrozenSet[str]:
        return frozenset(e.etype for e in self.entities)

    def relation_types(self) -> FrozenSet[str]:
        return frozenset(r.rtype for r in self.relations)

    def structural_key(self) -> str:
        etypes = sorted(e.etype for e in self.entities)
        rtypes = sorted(r.rtype for r in self.relations)
        return f"E[{','.join(etypes)}]R[{','.join(rtypes)}]"

    def update_confidence(self, outcome_good: bool):
        self.times_matched += 1
        if outcome_good:
            self.times_confirmed += 1
        self.confidence = self.times_confirmed / max(1, self.times_matched)


# ─── TRANSFORMATION / CONSTRAINT / CONSEQUENCE ──────────────────────────────

@dataclass
class Transformation:
    """A candidate action a mote can apply to a RealityGraph."""

    name: str
    domain: str
    universal_op: str
    base_cost: float = 1.0
    preconditions: Optional[GraphPattern] = None
    effects: Dict[str, Any] = field(default_factory=dict)
    role_hint: Optional[str] = None
    cost_fn: Any = None

    VALID_OPS = frozenset([
        "OBSERVE", "FOCUS", "COMPARE", "GROUP", "SPLIT",
        "TRANSFORM", "TEST", "PREDICT", "ASK", "ANSWER", "TEACH",
        "COPY", "MUTATE", "COMPOSE", "DECOMPOSE", "VERIFY",
        "STORE", "FORGET", "MOVE_TOWARD", "MOVE_AWAY", "SILENCE",
    ])

    def __post_init__(self):
        if self.universal_op not in self.VALID_OPS:
            raise ValueError(f"Unknown universal_op {self.universal_op!r}")

    def compute_cost(self, graph: "RealityGraph", mote_state: Dict[str, Any]) -> float:
        return float(self.cost_fn(graph, mote_state)) if self.cost_fn else self.base_cost


@dataclass
class Constraint:
    """A domain-enforced rule. check() returns violation score; 0 means valid."""

    name: str
    domain: str
    check_fn: Any
    hard: bool = True
    weight: float = 1.0

    def check(self, before: "RealityGraph", after: "RealityGraph", transformation: Transformation) -> float:
        try:
            return float(self.check_fn(before, after, transformation)) * self.weight
        except Exception:
            # Constraint code failing should not silently validate in final systems,
            # but for research runs this keeps the world alive and reports soft zero.
            return 0.0


@dataclass
class GraphDelta:
    """Exactly what changed between two graph states."""

    entities_added: List[Entity] = field(default_factory=list)
    entities_removed: List[str] = field(default_factory=list)
    entities_modified: List[Tuple[Entity, Entity]] = field(default_factory=list)
    relations_added: List[Relation] = field(default_factory=list)
    relations_removed: List[Relation] = field(default_factory=list)
    relations_modified: List[Tuple[Relation, Relation]] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not any([
            self.entities_added, self.entities_removed, self.entities_modified,
            self.relations_added, self.relations_removed, self.relations_modified,
        ])

    @property
    def magnitude(self) -> int:
        return (
            len(self.entities_added) + len(self.entities_removed) + len(self.entities_modified)
            + len(self.relations_added) + len(self.relations_removed) + len(self.relations_modified)
        )


@dataclass
class Consequence:
    """What the world says back after a mote acts.

    task_signal (added Phase 2): domain-agnostic structured tag the world emits
    when a *task-defining* event happens. Values currently used in TAIS:
        "TASK_SUCCESS"  — the target/goal entity has just been produced
        "TASK_PROGRESS" — measurable progress toward the goal
        "TASK_FAILURE"  — an action that strictly worsened goal state
        None            — no task-relevance signal (default)
    Runners and benchmark scripts can read this without having to special-case
    action names per domain. This was added so that strict metrics such as
    `first_apply_implication_tick` become domain-agnostic: the runner just watches
    for the first `TASK_SUCCESS`.
    """

    reward: float = 0.0
    penalty: float = 0.0
    valid: bool = True
    concept_signals: Dict[str, float] = field(default_factory=dict)
    explanation: Dict[str, Any] = field(default_factory=dict)
    prediction_error: float = 0.0
    graph_delta: Optional[GraphDelta] = None
    task_signal: Optional[str] = None

    @property
    def net(self) -> float:
        return self.reward - self.penalty

    @property
    def valence(self) -> str:
        if self.net > 1.0:
            return "GOOD"
        if self.net < -1.0:
            return "BAD"
        return "NEUTRAL"

    def top_concepts(self, n: int = 3) -> List[Tuple[str, float]]:
        return sorted(self.concept_signals.items(), key=lambda kv: abs(kv[1]), reverse=True)[:n]


# ─── ANALOGY MAPPING ─────────────────────────────────────────────────────────

@dataclass
class AnalogyMapping:
    """Result of mapping a GraphPattern onto a target graph."""

    source_pattern: GraphPattern
    target_graph: "RealityGraph"
    entity_map: Dict[str, str] = field(default_factory=dict)
    type_map: Dict[str, str] = field(default_factory=dict)
    relation_type_map: Dict[str, str] = field(default_factory=dict)
    confidence: float = 0.0
    explanation: str = ""

    @property
    def is_useful(self) -> bool:
        return self.confidence > 0.30 and bool(self.entity_map)


# ─── REALITY GRAPH ───────────────────────────────────────────────────────────

class RealityGraph:
    """Universal typed graph substrate."""

    def __init__(self, domain: str = "unknown", label: str = ""):
        self.domain = domain
        self.label = label
        self._entities: Dict[str, Entity] = {}
        self._relations: Dict[Tuple[str, str, str], Relation] = {}
        self._adj_out: Dict[str, Set[Tuple[str, str, str]]] = {}
        self._adj_in: Dict[str, Set[Tuple[str, str, str]]] = {}
        self._version = 0

    # Entity CRUD
    def add_entity(self, entity: Entity) -> "RealityGraph":
        self._entities[entity.id] = entity
        self._adj_out.setdefault(entity.id, set())
        self._adj_in.setdefault(entity.id, set())
        self._version += 1
        return self

    def remove_entity(self, entity_id: str) -> "RealityGraph":
        if entity_id not in self._entities:
            return self
        for key in list(self._adj_out.get(entity_id, set())):
            self.remove_relation(*key)
        for key in list(self._adj_in.get(entity_id, set())):
            self.remove_relation(*key)
        self._entities.pop(entity_id, None)
        self._adj_out.pop(entity_id, None)
        self._adj_in.pop(entity_id, None)
        self._version += 1
        return self

    def update_entity(self, entity_id: str, **props) -> "RealityGraph":
        if entity_id in self._entities:
            e = self._entities[entity_id]
            new_props = {**e.properties, **props}
            self._entities[entity_id] = Entity(e.id, e.etype, new_props)
            self._version += 1
        return self

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        return self._entities.get(entity_id)

    def entities(self, etype: Optional[str] = None) -> List[Entity]:
        vals = list(self._entities.values())
        return vals if etype is None else [e for e in vals if e.etype == etype]

    # Relation CRUD
    def add_relation(self, relation: Relation) -> "RealityGraph":
        if relation.source not in self._entities:
            raise ValueError(f"Source entity {relation.source!r} not in graph")
        if relation.target not in self._entities:
            raise ValueError(f"Target entity {relation.target!r} not in graph")
        self._add_relation_one_way(relation)
        if not relation.directed:
            rev = Relation(relation.target, relation.rtype, relation.source, dict(relation.properties), directed=False)
            self._add_relation_one_way(rev)
        self._version += 1
        return self

    def _add_relation_one_way(self, relation: Relation):
        key = relation.key()
        self._relations[key] = relation
        self._adj_out.setdefault(relation.source, set()).add(key)
        self._adj_in.setdefault(relation.target, set()).add(key)

    def remove_relation(self, source: str, rtype: str, target: str) -> "RealityGraph":
        key = (source, rtype, target)
        rel = self._relations.pop(key, None)
        if rel:
            self._adj_out.get(source, set()).discard(key)
            self._adj_in.get(target, set()).discard(key)
            if not rel.directed:
                rev = (target, rtype, source)
                self._relations.pop(rev, None)
                self._adj_out.get(target, set()).discard(rev)
                self._adj_in.get(source, set()).discard(rev)
            self._version += 1
        return self

    def get_relation(self, source: str, rtype: str, target: str) -> Optional[Relation]:
        return self._relations.get((source, rtype, target))

    def relations(self, rtype: Optional[str] = None) -> List[Relation]:
        vals = list(self._relations.values())
        return vals if rtype is None else [r for r in vals if r.rtype == rtype]

    def neighbors_out(self, entity_id: str, rtype: Optional[str] = None) -> List[Tuple[Relation, Entity]]:
        out: List[Tuple[Relation, Entity]] = []
        for key in self._adj_out.get(entity_id, set()):
            rel = self._relations.get(key)
            if rel and (rtype is None or rel.rtype == rtype):
                tgt = self._entities.get(rel.target)
                if tgt:
                    out.append((rel, tgt))
        return out

    def neighbors_in(self, entity_id: str, rtype: Optional[str] = None) -> List[Tuple[Relation, Entity]]:
        out: List[Tuple[Relation, Entity]] = []
        for key in self._adj_in.get(entity_id, set()):
            rel = self._relations.get(key)
            if rel and (rtype is None or rel.rtype == rtype):
                src = self._entities.get(rel.source)
                if src:
                    out.append((rel, src))
        return out

    # Subgraphs / attention
    def subgraph(self, entity_ids: Set[str]) -> "RealityGraph":
        g = RealityGraph(self.domain, f"{self.label}[sub]")
        for eid in entity_ids:
            e = self._entities.get(eid)
            if e:
                g.add_entity(copy.deepcopy(e))
        for rel in self._relations.values():
            if rel.source in entity_ids and rel.target in entity_ids:
                g.add_relation(copy.deepcopy(rel))
        return g

    def neighborhood(self, entity_id: str, hops: int = 1) -> "RealityGraph":
        visited = {entity_id}
        frontier = {entity_id}
        for _ in range(hops):
            nxt: Set[str] = set()
            for eid in frontier:
                for _rel, ent in self.neighbors_out(eid):
                    if ent.id not in visited:
                        visited.add(ent.id)
                        nxt.add(ent.id)
                for _rel, ent in self.neighbors_in(eid):
                    if ent.id not in visited:
                        visited.add(ent.id)
                        nxt.add(ent.id)
            frontier = nxt
        return self.subgraph(visited)

    # Core operations
    def diff(self, other: "RealityGraph") -> GraphDelta:
        delta = GraphDelta()
        self_ids, other_ids = set(self._entities), set(other._entities)
        for eid in other_ids - self_ids:
            delta.entities_added.append(copy.deepcopy(other._entities[eid]))
        for eid in self_ids - other_ids:
            delta.entities_removed.append(eid)
        for eid in self_ids & other_ids:
            before, after = self._entities[eid], other._entities[eid]
            if before.etype != after.etype or before.properties != after.properties:
                delta.entities_modified.append((copy.deepcopy(before), copy.deepcopy(after)))

        self_keys, other_keys = set(self._relations), set(other._relations)
        for key in other_keys - self_keys:
            delta.relations_added.append(copy.deepcopy(other._relations[key]))
        for key in self_keys - other_keys:
            delta.relations_removed.append(copy.deepcopy(self._relations[key]))
        for key in self_keys & other_keys:
            before, after = self._relations[key], other._relations[key]
            if before.properties != after.properties or before.directed != after.directed:
                delta.relations_modified.append((copy.deepcopy(before), copy.deepcopy(after)))
        return delta

    def distance(self, other: "RealityGraph") -> float:
        if not self._entities and not other._entities:
            return 0.0

        def counts(items: Iterable[str]) -> Dict[str, int]:
            d: Dict[str, int] = {}
            for it in items:
                d[it] = d.get(it, 0) + 1
            return d

        def jaccard(a: Dict[str, int], b: Dict[str, int]) -> float:
            keys = set(a) | set(b)
            if not keys:
                return 1.0
            inter = sum(min(a.get(k, 0), b.get(k, 0)) for k in keys)
            union = sum(max(a.get(k, 0), b.get(k, 0)) for k in keys)
            return inter / union if union else 1.0

        e_sim = jaccard(counts(e.etype for e in self._entities.values()), counts(e.etype for e in other._entities.values()))
        r_sim = jaccard(counts(r.rtype for r in self._relations.values()), counts(r.rtype for r in other._relations.values()))
        size_sim = min(len(self._entities), len(other._entities)) / max(len(self._entities), len(other._entities), 1)
        similarity = 0.42 * e_sim + 0.42 * r_sim + 0.16 * size_sim
        return round(1.0 - similarity, 4)

    def analogize(self, pattern: GraphPattern, max_candidates: int = 8) -> AnalogyMapping:
        if not pattern.entities or not self._entities:
            return AnalogyMapping(pattern, self, confidence=0.0)

        pattern_etypes = sorted(set(e.etype for e in pattern.entities))
        graph_etypes = sorted(set(e.etype for e in self._entities.values()))
        type_map: Dict[str, str] = {}
        for pe in pattern_etypes:
            if pe == "*":
                type_map[pe] = graph_etypes[0]
            elif pe in graph_etypes:
                type_map[pe] = pe
            else:
                # Lightweight structural analogy: choose graph type with closest frequency rank.
                type_map[pe] = graph_etypes[min(len(type_map), len(graph_etypes) - 1)]

        pattern_rtypes = sorted(set(r.rtype for r in pattern.relations))
        graph_rtypes = sorted(set(r.rtype for r in self._relations.values()))
        rel_type_map: Dict[str, str] = {}
        for i, pr in enumerate(pattern_rtypes):
            if pr in graph_rtypes:
                rel_type_map[pr] = pr
            elif graph_rtypes:
                rel_type_map[pr] = graph_rtypes[min(i, len(graph_rtypes) - 1)]

        entity_map: Dict[str, str] = {}
        score = 0.0
        for pe in pattern.entities[:max_candidates]:
            mapped_type = type_map.get(pe.etype, pe.etype)
            candidates = [e for e in self._entities.values() if mapped_type == "*" or e.etype == mapped_type]
            if not candidates:
                candidates = list(self._entities.values())
                local_score = 0.2
            else:
                local_score = 1.0 if pe.etype == mapped_type else 0.55
            chosen = candidates[0]
            entity_map[pe.id] = chosen.id
            score += local_score
        entity_score = score / max(1, min(max_candidates, len(pattern.entities)))

        if pattern_rtypes:
            exact_rel = sum(1 for r in pattern_rtypes if r in graph_rtypes) / len(pattern_rtypes)
            # Cross-domain analogies often have different relation names but the
            # same arity/shape. Give partial credit when both graphs have edge
            # structure even if labels differ: NEAR can analogize to ADJACENT_TO.
            structural_rel = min(len(pattern_rtypes), len(graph_rtypes)) / max(len(pattern_rtypes), len(graph_rtypes), 1) if graph_rtypes else 0.0
            r_overlap = max(exact_rel, 0.40 * structural_rel)
        else:
            r_overlap = 1.0
        exact_type = sum(1 for k, v in type_map.items() if k == v) / max(1, len(type_map))
        # Same reason: type labels differ across domains, but a two-node pattern
        # can still map onto a two-node target. Give structural type credit.
        structural_type = min(len(pattern_etypes), len(graph_etypes)) / max(len(pattern_etypes), len(graph_etypes), 1)
        type_exact = max(exact_type, 0.40 * structural_type)
        confidence = round(0.45 * entity_score + 0.30 * r_overlap + 0.25 * type_exact, 3)
        explanation = f"entity={entity_score:.2f} rtype={r_overlap:.2f} type={type_exact:.2f}"
        return AnalogyMapping(pattern, self, entity_map, type_map, rel_type_map, confidence, explanation)

    # Pattern matching
    def find_pattern(self, pattern: GraphPattern, max_matches: int = 128) -> List[Dict[str, str]]:
        if not pattern.entities:
            return [{}]
        matches: List[Dict[str, str]] = []

        def extend(i: int, mapping: Dict[str, str]):
            if len(matches) >= max_matches:
                return
            if i >= len(pattern.entities):
                if self._check_pattern_relations(pattern, mapping):
                    matches.append(dict(mapping))
                return
            pe = pattern.entities[i]
            for ent in self._entities.values():
                if ent.id in mapping.values():
                    continue
                if ent.matches_pattern(pe):
                    mapping[pe.id] = ent.id
                    extend(i + 1, mapping)
                    mapping.pop(pe.id, None)

        extend(0, {})
        return matches

    def _check_pattern_relations(self, pattern: GraphPattern, mapping: Dict[str, str]) -> bool:
        for pr in pattern.relations:
            src = mapping.get(pr.source, pr.source)
            tgt = mapping.get(pr.target, pr.target)
            if pr.rtype == "*":
                if not any(r.source == src and r.target == tgt for r in self._relations.values()):
                    return False
            elif (src, pr.rtype, tgt) not in self._relations:
                return False
        return True

    # Snapshot / introspection
    def snapshot(self) -> "RealityGraph":
        g = RealityGraph(self.domain, self.label)
        g._entities = {k: copy.deepcopy(v) for k, v in self._entities.items()}
        g._relations = {k: copy.deepcopy(v) for k, v in self._relations.items()}
        g._adj_out = {k: set(v) for k, v in self._adj_out.items()}
        g._adj_in = {k: set(v) for k, v in self._adj_in.items()}
        g._version = self._version
        return g

    def summary(self) -> Dict[str, Any]:
        etypes: Dict[str, int] = {}
        rtypes: Dict[str, int] = {}
        for e in self._entities.values():
            etypes[e.etype] = etypes.get(e.etype, 0) + 1
        for r in self._relations.values():
            rtypes[r.rtype] = rtypes.get(r.rtype, 0) + 1
        return {
            "domain": self.domain,
            "label": self.label,
            "entities": len(self._entities),
            "relations": len(self._relations),
            "version": self._version,
            "etypes": etypes,
            "rtypes": rtypes,
        }

    def __len__(self) -> int:
        return len(self._entities)

    def __contains__(self, entity_id: str) -> bool:
        return entity_id in self._entities

    def __repr__(self) -> str:
        return f"RealityGraph(domain={self.domain!r}, entities={len(self._entities)}, relations={len(self._relations)})"


# ─── WORLD INTERFACE ─────────────────────────────────────────────────────────

class WorldInterface:
    """
    The universal contract every domain must implement.

    Domains are thin lenses. Motes call these methods, not domain internals.
    """

    domain_name: str = "base"

    def observe(self, graph: RealityGraph, mote_position: Any) -> RealityGraph:
        raise NotImplementedError

    def valid_actions(self, graph: RealityGraph, mote_state: Dict[str, Any]) -> List[Transformation]:
        raise NotImplementedError

    def act(self, graph: RealityGraph, transformation: Transformation, mote_state: Dict[str, Any]) -> Tuple[RealityGraph, Consequence]:
        raise NotImplementedError

    def evaluate(self, graph: RealityGraph, mote_state: Dict[str, Any]) -> float:
        raise NotImplementedError

    def concepts(self) -> List[str]:
        return []

    def serialize(self, graph: RealityGraph) -> Dict[str, Any]:
        return graph.summary()
