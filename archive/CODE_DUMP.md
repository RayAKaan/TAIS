

# FILE: CODEBASE_MANIFEST.md

```text
# TAIS Current Codebase Manifest

This archive contains the current working TAIS research codebase from this workspace.

## Core universal substrate

- `tais_core/reality.py` — Entity, Relation, RealityGraph, Transformation, Constraint, Consequence, GraphDelta, analogy, WorldInterface.
- `tais_core/memory.py` — EpisodicMemory, PatternMemory, SymbolicMemory, CulturalMemory, PredictionEngine, MoteMemory, ActionRole helpers currently integrated here.
- `tais_core/speech.py` — Lexicon, SpeechGenome, Utterance, RepairSignal, UnderstandingAudit, SpeechOrgan.
- `tais_core/mote.py` — UniversalMote and MetaGenes.
- `tais_core/domains/gridworld.py` — GridGraphWorld.
- `tais_core/domains/sequences.py` — SequenceWorld.
- `tais_core/domains/rules.py` — RuleWorld.

## Swarm systems

- `swarm_v5.py` — V5.5 ecological swarm/server/UI backend with query mode, audit, action role transfer.
- `swarm_v4.py` — V4 world/memory/reference version.
- `swarm_v3.py` — V3 living speech version.
- `swarm_server.py` — older codebook conversational server.
- `tais_lang_v2_predator.py` — predator/silence/deception simulation.

## Experiments

- `experiments_cross_domain_transfer.py` — 50-seed/variable transfer experiment runner.
- `experiments_statistical_replication.py` — 200-seed paired replication of mixed GridWorld → RuleWorld.

## Tests

- `tests/test_tais_core.py` — core unit tests.
- `tests/test_base_validation.py` — base validation tests.

## Frontend

- `src/App.jsx` — current React UI.
- `src/main.jsx`
- `index.html`
- `package.json`
- `package-lock.json`

## Reports / docs

- `README.md`
- `TAIS_UNIVERSAL_ROADMAP.md`
- `TAIS_BASE_MODEL_CRITERIA.md`
- `TEST_REPORT.md`
- `CROSS_DOMAIN_TRANSFER_REPORT.md`
- `ANALOGY_ACTION_PRIOR_REPORT.md`

## Outputs

- `cross_domain_transfer_results.json`
- `statistical_replication_results.json`
- `colonies/*.json` smoke-test colonies

## Run tests

```bash
python3 -m pip install -r requirements.txt
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

## Run V5.5 interactive backend

```bash
python3 swarm_v5.py
```

Then frontend:

```bash
npm install
npm run dev
```

## Run replication

```bash
PYTHONPATH=. python3 experiments_statistical_replication.py
```

```


# FILE: README.md

```text
# TAIS-LANG v5.5: Conversation · Query · Culture

No LLM. No pretrained language model. No codebook sentence generation.

v5.5 keeps the v5 understanding audit, then makes the system much more usable as a conversation environment.

## New in v5.5

- **Conversation filters** in the UI: hide/show biological noise such as births/deaths and audit events.
- **Birth aggregation**: birth spam is summarized as `N births nearby` instead of flooding the conversation.
- **Query mode**: ask nearby motes about a concept. They answer from their own memory maps.
- **Quick asks**: `FOOD`, `WATER`, `PREDATOR`, `SHELTER`, `SAFE`.
- **Teaching warnings**: accidental bad grounding like `food → GO` returns a warning.
- **Corrective teaching**: teaching suppresses conflicting old meanings for that word in nearby motes.
- **Understanding audit** remains: speaker intent, listener interpretation, action, outcome, trust change.

## What v5.5 measures

Every acted-on utterance can produce an audit record:

```text
speaker intent
listener interpretation
action: toward / away
energy/hydration before and after
trust before and after
outcome
utility success
semantic match
```

Metrics:

- `utility_rate`: acting helped or avoided harm
- `semantic_rate`: listener interpretation/outcome matched speaker intent

## Files

- `swarm_v5.py` — v5.5 backend + headless trainer
- `src/App.jsx` — v5.5 React interface
- `swarm_v4.py` — previous world/memory/reference version
- `swarm_v3.py` — previous living-speech version

## Interactive run

Terminal 1:

```bash
python3 -m pip install -r requirements.txt
python3 swarm_v5.py
```

Terminal 2:

```bash
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

Backend:

```text
http://localhost:5123
```

## Headless training

```bash
python3 swarm_v5.py --headless --ticks 10000 --world 32 --population 80 --report 1000 --save colonies/v55_10k.json
```

Load a saved colony:

```bash
python3 swarm_v5.py --load colonies/v55_10k.json
```

## Useful endpoints

- `GET /stream` — SSE live state
- `GET /state` — full JSON snapshot
- `GET /audit` — latest understanding audits
- `GET /health` — health check
- `POST /player/move` — `{ "x": 5, "y": 5 }`
- `POST /player/speak` — `{ "text": "water north", "concept": "WATER", "value": 10, "x": 5, "y": 8 }`
- `POST /player/teach` — `{ "word": "water", "concept": "WATER", "value": 10 }`
- `POST /player/query` — `{ "text": "food?", "concept": "FOOD" }`
- `GET /mote/<id>/lexicon` — inspect private lexicon and memories
- `POST /save` — save colony JSON
- `POST /reset` — reset world

## Good teaching curriculum

Use consistent grounding:

```text
food   → FOOD
water  → WATER
danger → PREDATOR
home   → SHELTER
safe   → SAFE
come   → COME
go     → GO
```

Avoid accidentally teaching `food → GO` or `food → SHELTER` unless you intentionally want to create a dialect/confusion experiment.

## Validation completed

- `swarm_v5.py` compiles
- headless training runs
- `/player/teach` returns warnings for mismatched prior meanings
- `/player/query` works
- `/audit` works
- frontend builds with `npm run build`

```


# FILE: requirements.txt

```text
Flask>=3.0.0
flask-cors>=4.0.0

```


# FILE: package.json

```json
{
  "scripts": {
    "dev": "vite --host 0.0.0.0 --port 5173",
    "build": "vite build",
    "preview": "vite preview --host 0.0.0.0 --port 4173"
  },
  "dependencies": {
    "@vitejs/plugin-react": "latest",
    "vite": "latest",
    "react": "latest",
    "react-dom": "latest"
  },
  "devDependencies": {}
}

```


# FILE: index.html

```text
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>TAIS-LANG Conversational Swarm</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>

```


# FILE: tais_core/__init__.py

```python
"""TAIS Core: universal reality, memory, and speech substrate."""

from .reality import (
    Entity,
    Relation,
    GraphPattern,
    Transformation,
    Constraint,
    Consequence,
    GraphDelta,
    AnalogyMapping,
    RealityGraph,
    WorldInterface,
)

__all__ = [
    "Entity",
    "Relation",
    "GraphPattern",
    "Transformation",
    "Constraint",
    "Consequence",
    "GraphDelta",
    "AnalogyMapping",
    "RealityGraph",
    "WorldInterface",
]

```


# FILE: tais_core/reality.py

```python
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
    """What the world says back after a mote acts."""

    reward: float = 0.0
    penalty: float = 0.0
    valid: bool = True
    concept_signals: Dict[str, float] = field(default_factory=dict)
    explanation: Dict[str, Any] = field(default_factory=dict)
    prediction_error: float = 0.0
    graph_delta: Optional[GraphDelta] = None

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

```


# FILE: tais_core/memory.py

```python
"""
tais_core.memory
================

Pattern memory is the mechanism for cross-domain transfer.

Memory types:
    EpisodicMemory  — what happened to me, sequentially
    PatternMemory   — recurring structural fragments with consequence signatures
    SymbolicMemory  — named concepts and graph fingerprints
    CulturalMemory  — archive that outlives individual motes
    PredictionEngine — predicted consequence vs actual consequence
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Tuple

from .reality import AnalogyMapping, Consequence, GraphPattern, RealityGraph, Transformation


ACTION_ROLES = [
    "APPROACH_GOOD",
    "AVOID_BAD",
    "VERIFY_UNCERTAIN",
    "TRANSFORM_TOWARD_GOAL",
    "EXPLORE_UNCERTAIN",
    "REPAIR_MISMATCH",
    "MAINTAIN_STABLE",
    "FAILED",
    "UNCLASSIFIED",
]


def infer_action_role(action: Transformation) -> str:
    """Domain-blind candidate role estimate from universal_op/role_hint."""
    if action.role_hint:
        return action.role_hint
    if action.universal_op == "MOVE_TOWARD":
        return "APPROACH_GOOD"
    if action.universal_op == "MOVE_AWAY":
        return "AVOID_BAD"
    if action.universal_op in {"VERIFY", "TEST"}:
        return "VERIFY_UNCERTAIN"
    if action.universal_op in {"TRANSFORM", "COMPOSE"}:
        return "TRANSFORM_TOWARD_GOAL"
    if action.universal_op in {"MUTATE", "OBSERVE", "FOCUS", "COMPARE"}:
        return "EXPLORE_UNCERTAIN"
    if action.universal_op in {"ASK", "ANSWER", "TEACH"}:
        return "REPAIR_MISMATCH"
    if action.universal_op == "SILENCE":
        return "MAINTAIN_STABLE"
    return "UNCLASSIFIED"


def role_compatibility(source_role: str, target_role: str) -> float:
    """How much a source role should boost a target role across domains."""
    if not source_role or not target_role:
        return 0.0
    if source_role == target_role:
        return 1.0
    # Functional analogies: moving toward a resource, applying a rule toward a
    # target fact, and adding a useful fragment are different ops but same role:
    # change state toward a good/evaluated target.
    approach_family = {"APPROACH_GOOD", "TRANSFORM_TOWARD_GOAL"}
    if source_role in approach_family and target_role in approach_family:
        return 0.70
    caution_family = {"AVOID_BAD", "VERIFY_UNCERTAIN", "MAINTAIN_STABLE"}
    if source_role in caution_family and target_role in caution_family:
        return 0.45
    if source_role == "EXPLORE_UNCERTAIN" and target_role in {"VERIFY_UNCERTAIN", "EXPLORE_UNCERTAIN"}:
        return 0.35
    if source_role == "FAILED" and target_role == "VERIFY_UNCERTAIN":
        return 0.25
    return 0.0


@dataclass
class Episode:
    state_fingerprint: str
    transformation: Transformation
    consequence: Consequence
    predicted_outcome: float = 0.0
    prediction_error: float = 0.0
    domain: str = "unknown"
    tick: int = 0
    context_concepts: List[str] = field(default_factory=list)

    @property
    def was_useful(self) -> bool:
        return self.consequence.net > 0.5

    @property
    def was_harmful(self) -> bool:
        return self.consequence.net < -0.5

    @property
    def was_surprising(self) -> bool:
        return self.prediction_error > 2.0


class EpisodicMemory:
    def __init__(self, capacity: int = 64):
        self.capacity = capacity
        self.episodes: Deque[Episode] = deque(maxlen=capacity)
        self._action_stats: Dict[str, Dict[str, Any]] = {}

    def record(self, episode: Episode):
        self.episodes.append(episode)
        name = episode.transformation.name
        stat = self._action_stats.setdefault(name, {
            "total": 0.0, "count": 0, "min": float("inf"), "max": float("-inf"), "domains": set()
        })
        net = episode.consequence.net
        stat["total"] += net
        stat["count"] += 1
        stat["min"] = min(stat["min"], net)
        stat["max"] = max(stat["max"], net)
        stat["domains"].add(episode.domain)

    def action_value(self, transform_name: str) -> float:
        stat = self._action_stats.get(transform_name)
        return 0.0 if not stat or stat["count"] == 0 else stat["total"] / stat["count"]

    def action_risk(self, transform_name: str) -> float:
        stat = self._action_stats.get(transform_name)
        if not stat or stat["count"] < 2:
            return 1.0
        mean = stat["total"] / stat["count"]
        return (stat["max"] - stat["min"]) / max(1.0, abs(mean))

    def best_actions(self, n: int = 3) -> List[Tuple[str, float]]:
        vals = [(name, s["total"] / max(1, s["count"])) for name, s in self._action_stats.items()]
        return sorted(vals, key=lambda kv: -kv[1])[:n]

    def worst_actions(self, n: int = 3) -> List[Tuple[str, float]]:
        vals = [(name, s["total"] / max(1, s["count"])) for name, s in self._action_stats.items()]
        return sorted(vals, key=lambda kv: kv[1])[:n]

    def prediction_error_trend(self) -> float:
        eps = list(self.episodes)
        if len(eps) < 4:
            return 0.0
        mid = len(eps) // 2
        early = sum(e.prediction_error for e in eps[:mid]) / mid
        late = sum(e.prediction_error for e in eps[mid:]) / (len(eps) - mid)
        return late - early

    def recent_concept_signals(self, n: int = 8) -> Dict[str, float]:
        agg: Dict[str, float] = {}
        for ep in list(self.episodes)[-n:]:
            for c, v in ep.consequence.concept_signals.items():
                agg[c] = agg.get(c, 0.0) + v
        total = max(1.0, sum(abs(v) for v in agg.values()))
        return {c: v / total for c, v in agg.items()}

    def __len__(self) -> int:
        return len(self.episodes)


class PatternMemory:
    """Stores GraphPatterns that reliably predict consequence signatures."""

    def __init__(self, capacity: int = 32):
        self.capacity = capacity
        self.patterns: List[GraphPattern] = []

    def _fingerprint(self, pattern: GraphPattern) -> str:
        return pattern.structural_key()

    def store(self, pattern: GraphPattern, consequence: Consequence) -> bool:
        fp = self._fingerprint(pattern)
        for existing in self.patterns:
            if self._fingerprint(existing) == fp:
                # Confidence means reliability of the signature, not positivity.
                # A consistently BAD pattern is just as important as a GOOD one.
                same_signature = existing.consequence_signature == consequence.valence
                existing.update_confidence(same_signature)
                existing.consequence_signature = existing.consequence_signature or consequence.valence
                n = max(1, existing.times_matched)
                existing.mean_outcome_net = ((existing.mean_outcome_net * (n - 1)) + consequence.net) / n
                # Merge action provenance.
                if pattern.successful_action_op and not existing.successful_action_op:
                    existing.successful_action_op = pattern.successful_action_op
                    existing.successful_action_name = pattern.successful_action_name
                    existing.successful_action_cost = pattern.successful_action_cost
                for op in pattern.failed_action_ops:
                    if op not in existing.failed_action_ops:
                        existing.failed_action_ops.append(op)
                for name in pattern.failed_action_names:
                    if name not in existing.failed_action_names:
                        existing.failed_action_names.append(name)
                if pattern.successful_action_role and not existing.successful_action_role:
                    existing.successful_action_role = pattern.successful_action_role
                for role in pattern.failed_action_roles:
                    if role not in existing.failed_action_roles:
                        existing.failed_action_roles.append(role)
                return True

        # New pattern: one observation, one confirmed signature.
        pattern.consequence_signature = consequence.valence
        pattern.times_matched = 1
        pattern.times_confirmed = 1
        pattern.confidence = 1.0
        pattern.mean_outcome_net = consequence.net
        if len(self.patterns) < self.capacity:
            self.patterns.append(pattern)
            return True
        weakest = min(self.patterns, key=lambda p: p.confidence)
        if pattern.confidence > weakest.confidence:
            self.patterns.remove(weakest)
            self.patterns.append(pattern)
            return True
        return False

    def lookup(self, graph: RealityGraph, min_confidence: float = 0.3) -> List[Tuple[GraphPattern, List[Dict[str, str]]]]:
        out = []
        for p in self.patterns:
            if p.confidence < min_confidence:
                continue
            matches = graph.find_pattern(p)
            if matches:
                out.append((p, matches))
        return out

    def transfer_to(self, target_graph: RealityGraph, min_confidence: float = 0.25) -> List[Tuple[GraphPattern, AnalogyMapping]]:
        out = []
        for p in self.patterns:
            if p.confidence < min_confidence:
                continue
            mapping = target_graph.analogize(p)
            if mapping.is_useful:
                out.append((p, mapping))
        return sorted(out, key=lambda pair: -pair[1].confidence)

    def predict_consequence(self, graph: RealityGraph) -> Optional[str]:
        matches = self.lookup(graph)
        if not matches:
            return None
        votes: Dict[str, float] = {}
        for p, _ in matches:
            v = p.consequence_signature or "NEUTRAL"
            votes[v] = votes.get(v, 0.0) + p.confidence
        return max(votes, key=votes.get)

    def action_priors(
        self,
        target_graph: RealityGraph,
        available_actions: List[Transformation],
        min_confidence: float = 0.30,
        min_analogy: float = 0.30,
    ) -> Tuple[Dict[str, float], int]:
        """
        Bridge representation to action.

        Pattern transfer alone says: this situation resembles an old situation.
        Action priors say: and in that old situation, this kind of action helped
        or hurt, so bias current action selection accordingly.

        Returns:
            ({action.name: boost}, number_of_transfer_patterns_used)
        """
        boosts: Dict[str, float] = {a.name: 0.0 for a in available_actions}
        used = 0
        transfers = self.transfer_to(target_graph, min_confidence=min_confidence)
        for pattern, mapping in transfers:
            if mapping.confidence < min_analogy:
                continue
            used += 1
            base = mapping.confidence * pattern.confidence * max(0.25, abs(pattern.mean_outcome_net))
            for action in available_actions:
                target_role = infer_action_role(action)
                # Positive transfer by action role first, universal_op second.
                if pattern.consequence_signature == "GOOD":
                    role_match = role_compatibility(pattern.successful_action_role or "", target_role)
                    if role_match:
                        boosts[action.name] += base * role_match
                    elif pattern.successful_action_op and action.universal_op == pattern.successful_action_op:
                        boosts[action.name] += base * 0.50
                # Negative transfer: avoid roles/ops that harmed in analogous contexts.
                if pattern.consequence_signature == "BAD":
                    if target_role in pattern.failed_action_roles:
                        boosts[action.name] -= base
                    if action.universal_op in pattern.failed_action_ops:
                        boosts[action.name] -= base * 0.50
                    # Generic safety bias for bad/danger patterns. This remains
                    # domain-blind: it boosts universal verification/caution roles.
                    if target_role in {"VERIFY_UNCERTAIN", "AVOID_BAD"}:
                        boosts[action.name] += base * 0.30
                    if target_role in {"EXPLORE_UNCERTAIN"}:
                        boosts[action.name] -= base * 0.20
        return boosts, used

    def prune(self, min_confidence: float = 0.15):
        self.patterns = [p for p in self.patterns if p.confidence >= min_confidence]

    def best_patterns(self, n: int = 5) -> List[GraphPattern]:
        return sorted(self.patterns, key=lambda p: -p.confidence)[:n]

    def __len__(self) -> int:
        return len(self.patterns)


class SymbolicMemory:
    """Named concepts grounded in graph fingerprints and repair events."""

    def __init__(self):
        self.concepts: Dict[str, Dict[str, Any]] = {}
        self.token_map: Dict[str, str] = {}
        self.repair_log: List[Dict[str, Any]] = []

    def associate(self, token: str, concept: str, graph_fp: str, success: bool):
        entry = self.concepts.setdefault(concept, {
            "token": token, "pattern_fps": set(), "concept": concept,
            "confidence": 0.5, "uses": 0, "successes": 0,
        })
        entry["pattern_fps"].add(graph_fp)
        entry["uses"] += 1
        if success:
            entry["successes"] += 1
        entry["confidence"] = entry["successes"] / max(1, entry["uses"])
        entry["token"] = token
        self.token_map[token] = concept

    def best_token_for(self, concept: str) -> Optional[str]:
        e = self.concepts.get(concept)
        return e["token"] if e else None

    def concept_for_token(self, token: str) -> Optional[str]:
        return self.token_map.get(token)

    def register_repair(self, sent_token: str, intended_concept: str, listener_action: str, outcome: str):
        self.repair_log.append({
            "token": sent_token,
            "intended": intended_concept,
            "listener_did": listener_action,
            "outcome": outcome,
            "timestamp": time.time(),
        })

    def token_reliability(self, token: str) -> float:
        repairs = [r for r in self.repair_log if r["token"] == token and r["outcome"] == "BAD"]
        concept = self.token_map.get(token)
        if concept and concept in self.concepts:
            return float(self.concepts[concept]["confidence"])
        return max(0.0, 0.5 - len(repairs) * 0.1)

    def stable_concepts(self, min_confidence: float = 0.6) -> List[str]:
        return [c for c, d in self.concepts.items() if d["confidence"] >= min_confidence]

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        out = {}
        for c, d in self.concepts.items():
            out[c] = {
                "token": d["token"],
                "confidence": round(float(d["confidence"]), 3),
                "uses": d["uses"],
                "successes": d["successes"],
            }
        return out


class CulturalMemory:
    """Shared archive that outlives motes."""

    def __init__(self, capacity_per_domain: int = 100):
        self.capacity = capacity_per_domain
        self._store: Dict[str, List[Dict[str, Any]]] = {}
        self._global: List[Dict[str, Any]] = []

    def write(self, domain: str, entry: Dict[str, Any], fitness: float):
        if fitness < 5.0:
            return
        tagged = {**entry, "fitness": fitness, "timestamp": time.time(), "domain": domain}
        self._store.setdefault(domain, []).append(tagged)
        if len(self._store[domain]) > self.capacity:
            self._store[domain] = sorted(self._store[domain], key=lambda e: -e["fitness"])[:self.capacity]

    def write_cross_domain(self, entry: Dict[str, Any], fitness: float):
        if fitness < 6.0:
            return
        self._global.append({**entry, "fitness": fitness, "timestamp": time.time()})
        if len(self._global) > self.capacity:
            self._global = sorted(self._global, key=lambda e: -e["fitness"])[:self.capacity]

    def query(self, domain: str, concept: Optional[str] = None, n: int = 5) -> List[Dict[str, Any]]:
        entries = list(self._store.get(domain, []))
        if concept:
            entries = [e for e in entries if e.get("concept") == concept or concept in e.get("concepts", [])]
        return sorted(entries, key=lambda e: -e["fitness"])[:n]

    def query_cross_domain(self, n: int = 5) -> List[Dict[str, Any]]:
        return sorted(self._global, key=lambda e: -e["fitness"])[:n]

    def domain_summary(self) -> Dict[str, int]:
        return {d: len(v) for d, v in self._store.items()}

    def total_entries(self) -> int:
        return sum(len(v) for v in self._store.values()) + len(self._global)


class PredictionEngine:
    """Predicted consequence vs actual consequence."""

    def __init__(self):
        self._predictions: Deque[Tuple[float, float, float]] = deque(maxlen=64)
        self._per_transform: Dict[str, List[float]] = {}
        self._per_transform_net: Dict[str, List[float]] = {}
        self._per_domain: Dict[str, List[float]] = {}

    def predict(self, transformation: Transformation, pattern_memory: PatternMemory, graph: RealityGraph) -> float:
        # If this exact transformation has history, use its learned expected net.
        # This is the local anti-superstition model: prediction is about the
        # action's consequence, not merely reward after the fact.
        nets = self._per_transform_net.get(transformation.name, [])
        if nets:
            return sum(nets[-12:]) / len(nets[-12:])

        valence = pattern_memory.predict_consequence(graph)
        if valence == "GOOD":
            return 3.0
        if valence == "BAD":
            return -3.0
        return 0.0

    def record_outcome(self, predicted: float, actual: Consequence, transformation: Transformation, domain: str):
        error = abs(predicted - actual.net)
        self._predictions.append((predicted, actual.net, error))
        self._per_transform.setdefault(transformation.name, []).append(error)
        self._per_transform_net.setdefault(transformation.name, []).append(actual.net)
        self._per_domain.setdefault(domain, []).append(error)

    def mean_error(self) -> float:
        if not self._predictions:
            return float("inf")
        return sum(e for _p, _a, e in self._predictions) / len(self._predictions)

    def domain_error(self, domain: str) -> float:
        vals = self._per_domain.get(domain, [])
        return sum(vals) / len(vals) if vals else float("inf")

    def is_understanding(self, threshold: float = 1.5) -> bool:
        return len(self._predictions) >= 8 and self.mean_error() < threshold

    def error_trend(self) -> float:
        vals = list(self._predictions)
        if len(vals) < 4:
            return 0.0
        mid = len(vals) // 2
        early = sum(e for _p, _a, e in vals[:mid]) / mid
        late = sum(e for _p, _a, e in vals[mid:]) / (len(vals) - mid)
        return late - early


class MoteMemory:
    """Composite memory object owned by a universal mote."""

    def __init__(self, episodic_capacity: int = 64, pattern_capacity: int = 32):
        self.episodic = EpisodicMemory(episodic_capacity)
        self.patterns = PatternMemory(pattern_capacity)
        self.symbolic = SymbolicMemory()
        self.prediction = PredictionEngine()

    def record_episode(
        self,
        state_before: RealityGraph,
        transformation: Transformation,
        consequence: Consequence,
        predicted: float,
        domain: str,
        tick: int,
        action_role: str = "UNCLASSIFIED",
    ):
        fp = self._graph_fingerprint(state_before)
        error = abs(predicted - consequence.net)
        ep = Episode(fp, transformation, consequence, predicted, error, domain, tick)
        self.episodic.record(ep)
        self.prediction.record_outcome(predicted, consequence, transformation, domain)

        if abs(consequence.net) > 1.0:
            pattern = GraphPattern(
                entities=list(state_before.entities())[:5],
                relations=list(state_before.relations())[:5],
                name=f"{transformation.name}_{consequence.valence}",
                source_domain=domain,
                successful_action_op=transformation.universal_op if consequence.net > 0 else None,
                successful_action_name=transformation.name if consequence.net > 0 else None,
                successful_action_cost=transformation.base_cost if consequence.net > 0 else 0.0,
                failed_action_ops=[transformation.universal_op] if consequence.net < 0 else [],
                failed_action_names=[transformation.name] if consequence.net < 0 else [],
                successful_action_role=action_role if consequence.net > 0 else None,
                failed_action_roles=[action_role] if consequence.net < 0 else [],
                mean_outcome_net=consequence.net,
            )
            self.patterns.store(pattern, consequence)

    def predict_action(self, transformation: Transformation, graph: RealityGraph) -> float:
        return self.prediction.predict(transformation, self.patterns, graph)

    def best_action_from_history(self, candidates: List[Transformation]) -> Optional[Transformation]:
        if not candidates:
            return None
        best, best_score = None, float("-inf")
        for t in candidates:
            score = self.episodic.action_value(t.name) - 0.3 * self.episodic.action_risk(t.name)
            if score > best_score:
                best, best_score = t, score
        return best

    def should_explore(self, candidates: List[Transformation], curiosity: float = 0.3) -> bool:
        import random
        if not candidates:
            return False
        uncertainty = 0.0 if math.isinf(self.prediction.mean_error()) else min(0.4, self.prediction.mean_error() * 0.1)
        return random.random() < curiosity + uncertainty

    def transfer_patterns_to(self, target_graph: RealityGraph) -> List[Tuple[GraphPattern, AnalogyMapping]]:
        return self.patterns.transfer_to(target_graph)

    def transfer_action_priors(self, target_graph: RealityGraph, available_actions: List[Transformation]) -> Tuple[Dict[str, float], int]:
        return self.patterns.action_priors(target_graph, available_actions)

    def _graph_fingerprint(self, graph: RealityGraph) -> str:
        return hashlib.md5(json.dumps(graph.summary(), sort_keys=True).encode()).hexdigest()[:12]

    def summary(self) -> Dict[str, Any]:
        return {
            "episodes": len(self.episodic),
            "patterns": len(self.patterns),
            "stable_concepts": self.symbolic.stable_concepts(),
            "best_actions": self.episodic.best_actions(3),
            "worst_actions": self.episodic.worst_actions(3),
            "mean_pred_error": None if math.isinf(self.prediction.mean_error()) else round(self.prediction.mean_error(), 3),
            "pred_improving": self.prediction.error_trend() < 0,
            "understands": self.prediction.is_understanding(),
        }

```


# FILE: tais_core/speech.py

```python
"""
tais_core.speech
================

Emergent speech system for universal motes.

No codebook. No LLM. No pretraining.

Meaning emerges from consequences, repair, teaching, and understanding audits.
"""

from __future__ import annotations

import random
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional

from .reality import Consequence


BASE_TOKENS = [
    "ka", "mi", "tor", "lum", "sha", "nek", "vo", "pra",
    "tel", "du", "ra", "si", "fel", "nox", "wen", "bru",
    "ya", "ko", "dex", "ith", "um", "zal", "pho", "rei",
]

UNIVERSAL_CONCEPTS = [
    "GOOD", "BAD", "DANGER", "SAFE", "RESOURCE", "VOID",
    "COME", "GO", "HERE", "THERE", "NORTH", "SOUTH", "EAST", "WEST",
    "STRONG", "WEAK", "TRUST", "DOUBT", "QUERY", "CONFIRM", "DENY", "UNKNOWN",
]
C_IDX = {c: i for i, c in enumerate(UNIVERSAL_CONCEPTS)}


class Lexicon:
    """Private token→concept weight table."""

    def __init__(self, vocab: Optional[List[str]] = None):
        self.vocab = list(vocab or BASE_TOKENS)
        self.table: Dict[str, Dict[str, float]] = {
            tok: {c: random.uniform(-0.02, 0.02) for c in UNIVERSAL_CONCEPTS}
            for tok in self.vocab
        }
        self.update_count = 0

    def ensure(self, token: str):
        if token not in self.table:
            self.table[token] = {c: 0.0 for c in UNIVERSAL_CONCEPTS}
            if token not in self.vocab:
                self.vocab.append(token)

    def weight(self, token: str, concept: str) -> float:
        return self.table.get(token, {}).get(concept, 0.0)

    def top_concept(self, token: str, threshold: float = 0.08) -> Optional[str]:
        if token not in self.table:
            return None
        best = max(self.table[token], key=self.table[token].get)
        return best if self.table[token][best] > threshold else None

    def top_token(self, concept: str, available: Optional[List[str]] = None, threshold: float = 0.08) -> Optional[str]:
        pool = available or self.vocab
        best_tok, best_w = None, threshold
        for tok in pool:
            w = self.weight(tok, concept)
            if w > best_w:
                best_tok, best_w = tok, w
        return best_tok

    def interpret(self, tokens: List[str]) -> Dict[str, float]:
        vec = {c: 0.0 for c in UNIVERSAL_CONCEPTS}
        for tok in tokens:
            if tok in self.table:
                for c, w in self.table[tok].items():
                    vec[c] += w
        total = max(1.0, sum(abs(v) for v in vec.values()))
        return {c: v / total for c, v in vec.items()}

    def dominant_concept(self, tokens: List[str], threshold: float = 0.10) -> Optional[str]:
        vec = self.interpret(tokens)
        best = max(vec, key=vec.get)
        return best if vec[best] > threshold else None

    def update(self, token: str, concept: str, delta: float, lr: float = 0.12):
        if concept not in C_IDX:
            return
        self.ensure(token)
        self.table[token][concept] = max(-1.0, min(1.0, self.table[token].get(concept, 0.0) + delta * lr))
        self.update_count += 1

    def update_from_consequence(self, tokens: List[str], consequence: Consequence, lr: float = 0.10):
        sign = 1.0 if consequence.net > 0 else -0.5
        for concept, signal in consequence.concept_signals.items():
            if concept not in C_IDX:
                continue
            for tok in tokens:
                self.update(tok, concept, signal * sign, lr)

    def apply_repair(self, tokens: List[str], intended_concept: str, lr: float = 0.15):
        if intended_concept not in C_IDX:
            return
        for tok in tokens:
            current = self.top_concept(tok)
            if current and current != intended_concept:
                self.update(tok, current, -1.0, lr * 0.5)
            self.update(tok, intended_concept, 1.0, lr)

    def teach(self, token: str, concept: str, strength: float = 0.4, corrective: bool = True):
        if concept not in C_IDX:
            return
        self.ensure(token)
        self.table[token][concept] = min(1.0, self.table[token].get(concept, 0.0) + strength)
        if corrective:
            for c in UNIVERSAL_CONCEPTS:
                if c != concept:
                    self.table[token][c] = max(-1.0, self.table[token][c] - strength * 0.25)
        self.update_count += 1

    def inherit_from(self, parent: "Lexicon", noise: float = 0.02):
        for tok in set(self.vocab) | set(parent.vocab):
            self.ensure(tok)
            if tok in parent.table:
                for concept in UNIVERSAL_CONCEPTS:
                    self.table[tok][concept] = max(-1.0, min(1.0, parent.table[tok].get(concept, 0.0) + random.gauss(0, noise)))

    def divergence(self, other: "Lexicon") -> float:
        toks = set(self.vocab) | set(other.vocab)
        total, count = 0.0, 0
        for tok in toks:
            for concept in UNIVERSAL_CONCEPTS:
                total += abs(self.weight(tok, concept) - other.weight(tok, concept))
                count += 1
        return total / max(1, count) / 2.0

    def snapshot(self, threshold: float = 0.10) -> Dict[str, Dict[str, Any]]:
        out = {}
        for tok, weights in self.table.items():
            best = max(weights, key=weights.get)
            if weights[best] > threshold:
                out[tok] = {"concept": best, "weight": round(weights[best], 3)}
        return out


class SpeechGenome:
    """Heritable grammar structure."""

    ORDERS = [
        "thing", "thing-direction", "direction-thing", "risk-thing",
        "thing-risk-direction", "thing-thing", "query-thing",
    ]

    def __init__(self):
        self.order = random.choice(self.ORDERS)
        self.max_length = random.randint(1, 3)
        self.repetition_urgency = random.random() < 0.25
        self.silence_bias = random.uniform(0.3, 0.85)
        self.danger_suppression = random.random() < 0.6
        self.vocab_size = random.randint(6, len(BASE_TOKENS))
        self.query_bias = random.uniform(0.0, 0.3)
        self.metaphor_bias = random.uniform(0.0, 0.15)

    def mutate(self, rate: float = 0.07) -> "SpeechGenome":
        child = SpeechGenome()
        child.order = self.order if random.random() > rate else random.choice(self.ORDERS)
        child.max_length = max(1, min(4, self.max_length + random.choice([-1, 0, 0, 1])))
        child.repetition_urgency = self.repetition_urgency if random.random() > rate else not self.repetition_urgency
        child.silence_bias = max(0.1, min(0.95, self.silence_bias + random.gauss(0, 0.04)))
        child.danger_suppression = self.danger_suppression if random.random() > rate else not self.danger_suppression
        child.vocab_size = max(4, min(len(BASE_TOKENS), self.vocab_size + random.choice([-1, 0, 0, 1])))
        child.query_bias = max(0.0, min(0.6, self.query_bias + random.gauss(0, 0.03)))
        child.metaphor_bias = max(0.0, min(0.4, self.metaphor_bias + random.gauss(0, 0.02)))
        return child

    def active_vocab(self) -> List[str]:
        return BASE_TOKENS[: self.vocab_size]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order": self.order,
            "max_length": self.max_length,
            "repetition_urgency": self.repetition_urgency,
            "silence_bias": round(self.silence_bias, 3),
            "danger_suppression": self.danger_suppression,
            "vocab_size": self.vocab_size,
            "query_bias": round(self.query_bias, 3),
            "metaphor_bias": round(self.metaphor_bias, 3),
        }


@dataclass
class Utterance:
    tokens: List[str]
    speaker_id: int
    target_id: Optional[int]
    intended_concept: str
    position: List[float]
    fitness: float
    energy: float
    domain: str = "unknown"
    tick: int = 0
    is_silence: bool = False
    is_query: bool = False
    is_repair: bool = False
    is_teaching: bool = False
    confidence: float = 0.5

    @property
    def text(self) -> str:
        return " ".join(self.tokens)

    @property
    def is_directed(self) -> bool:
        return self.target_id is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tokens": self.tokens,
            "text": self.text,
            "speaker": self.speaker_id,
            "target": self.target_id,
            "concept": self.intended_concept,
            "pos": [round(p, 2) for p in self.position],
            "fitness": round(self.fitness, 2),
            "energy": round(self.energy, 1),
            "domain": self.domain,
            "tick": self.tick,
            "silence": self.is_silence,
            "query": self.is_query,
            "repair": self.is_repair,
            "teaching": self.is_teaching,
            "conf": round(self.confidence, 2),
        }


@dataclass
class RepairSignal:
    original_utterance: Utterance
    speaker_id: int
    listener_id: int
    correct_concept: str
    tick: int

    def to_repair_utterance(self, genome: SpeechGenome, lexicon: Lexicon) -> Utterance:
        deny_tok = lexicon.top_token("DENY", genome.active_vocab()) or random.choice(genome.active_vocab())
        correct_tok = lexicon.top_token(self.correct_concept, genome.active_vocab()) or random.choice(genome.active_vocab())
        return Utterance(
            tokens=[deny_tok, correct_tok][:genome.max_length],
            speaker_id=self.speaker_id,
            target_id=self.listener_id,
            intended_concept="DENY",
            position=self.original_utterance.position,
            fitness=self.original_utterance.fitness,
            energy=0.0,
            domain=self.original_utterance.domain,
            tick=self.tick,
            is_repair=True,
            confidence=0.8,
        )


class UnderstandingAudit:
    def __init__(self, capacity: int = 100):
        self.events: Deque[Dict[str, Any]] = deque(maxlen=capacity)

    def record_sent(self, utterance: Utterance):
        self.events.append({
            "tick": utterance.tick,
            "speaker": utterance.speaker_id,
            "target": utterance.target_id,
            "tokens": list(utterance.tokens),
            "concept": utterance.intended_concept,
            "received": False,
            "acted_on": False,
            "aligned": False,
            "outcome": None,
        })

    def record_received(self, utterance: Utterance, listener_id: int):
        for ev in reversed(self.events):
            if ev["speaker"] == utterance.speaker_id and ev["tokens"] == utterance.tokens and not ev["received"]:
                ev["received"] = True
                ev["listener"] = listener_id
                break

    def record_acted_on(self, utterance_tokens: List[str], speaker_id: int, listener_id: int, listener_action: str, aligned: bool, outcome: str):
        for ev in reversed(self.events):
            if ev["speaker"] == speaker_id and ev["tokens"] == utterance_tokens and ev["received"]:
                ev["acted_on"] = True
                ev["listener"] = listener_id
                ev["listener_action"] = listener_action
                ev["aligned"] = aligned
                ev["outcome"] = outcome
                break

    def semantic_success_rate(self, last_n: int = 20) -> float:
        recent = [e for e in list(self.events)[-last_n:] if e["acted_on"]]
        if not recent:
            return 0.5
        return sum(1 for e in recent if e["aligned"]) / len(recent)

    def delivery_rate(self, last_n: int = 20) -> float:
        recent = list(self.events)[-last_n:]
        if not recent:
            return 0.0
        return sum(1 for e in recent if e["received"]) / len(recent)

    def summary(self) -> Dict[str, Any]:
        return {
            "total_sent": len(self.events),
            "semantic_success": round(self.semantic_success_rate(), 3),
            "delivery_rate": round(self.delivery_rate(), 3),
        }


class SpeechOrgan:
    """Unified speech interface: genome + lexicon + audit + repair."""

    def __init__(self, mote_id: int, genome: Optional[SpeechGenome] = None, lexicon: Optional[Lexicon] = None):
        self.mote_id = mote_id
        self.genome = genome or SpeechGenome()
        self.lexicon = lexicon or Lexicon(self.genome.active_vocab())
        self.audit = UnderstandingAudit()
        self.silence_reason: Optional[str] = None
        self._last_utterance: Optional[Utterance] = None
        self.times_spoke = 0
        self.times_silent_choice = 0
        self.times_silent_fear = 0
        self.times_directed = 0
        self.times_broadcast = 0
        self.times_repair = 0
        self.times_queried = 0
        self.times_taught = 0
        self._recent_utts: Deque[Utterance] = deque(maxlen=8)

    def compose(
        self,
        intent: str,
        neighbors: List[Any],
        mote_state: Dict[str, Any],
        domain: str,
        tick: int,
        info_delta: float = 0.0,
    ) -> Optional[Utterance]:
        self.silence_reason = None
        if self.genome.danger_suppression and mote_state.get("nearest_threat", 99) < 1.8:
            self.times_silent_fear += 1
            self.silence_reason = "fear"
            return None
        if mote_state.get("energy", 0) < 5.0:
            self.silence_reason = "energy"
            return None
        if not neighbors:
            self.silence_reason = "alone"
            return None
        if info_delta < self.genome.silence_bias * 1.8:
            self.times_silent_choice += 1
            self.silence_reason = "no_info"
            return None

        vocab = self.genome.active_vocab()
        tokens = self._compose_tokens(intent, mote_state, vocab)
        target_id = None
        neediest = mote_state.get("neediest_neighbor_id")
        if neediest is not None and random.random() > self.genome.silence_bias * 0.6:
            target_id = neediest
            self.times_directed += 1
        else:
            self.times_broadcast += 1
        is_query = random.random() < self.genome.query_bias
        if is_query:
            self.times_queried += 1
        confidence = max(0.1, min(1.0, info_delta / 5.0))
        utt = Utterance(
            tokens=tokens,
            speaker_id=self.mote_id,
            target_id=target_id,
            intended_concept=intent,
            position=mote_state.get("position", [0.0, 0.0]),
            fitness=mote_state.get("fitness", 0.0),
            energy=mote_state.get("energy", 0.0),
            domain=domain,
            tick=tick,
            is_query=is_query,
            confidence=confidence,
        )
        self.audit.record_sent(utt)
        self._last_utterance = utt
        self._recent_utts.append(utt)
        self.times_spoke += 1
        return utt

    def _compose_tokens(self, intent: str, mote_state: Dict[str, Any], vocab: List[str]) -> List[str]:
        slots = self.genome.order.split("-")
        slot_concepts = {
            "thing": intent,
            "direction": mote_state.get("gradient_concept", "EAST"),
            "risk": "DANGER" if mote_state.get("nearest_threat", 99) < 3.5 else None,
            "query": "QUERY" if self.genome.query_bias > 0.2 else None,
        }
        tokens: List[str] = []
        for slot in slots[:self.genome.max_length]:
            concept = slot_concepts.get(slot)
            if concept is None:
                continue
            tok = self.lexicon.top_token(concept, vocab) or random.choice(vocab)
            if not tokens or tokens[-1] != tok:
                tokens.append(tok)
        if self.genome.repetition_urgency and mote_state.get("energy", 100) < 30 and tokens:
            tokens = [tokens[0], tokens[0]]
        if self.genome.metaphor_bias > 0.1 and random.random() < self.genome.metaphor_bias and len(tokens) < self.genome.max_length:
            extra = self.lexicon.top_token(random.choice(UNIVERSAL_CONCEPTS), vocab)
            if extra and extra not in tokens:
                tokens.append(extra)
        return tokens or [random.choice(vocab)]

    def receive(self, utterance: Utterance) -> Dict[str, float]:
        self.audit.record_received(utterance, self.mote_id)
        return self.lexicon.interpret(utterance.tokens)

    def record_action_outcome(self, utterance: Utterance, action_taken: str, aligned: bool, outcome: str):
        self.audit.record_acted_on(utterance.tokens, utterance.speaker_id, self.mote_id, action_taken, aligned, outcome)

    def fire_repair(self, original: Utterance, listener_id: int, tick: int) -> Optional[Utterance]:
        self.times_repair += 1
        return RepairSignal(original, self.mote_id, listener_id, original.intended_concept, tick).to_repair_utterance(self.genome, self.lexicon)

    def receive_repair(self, repair_utt: Utterance):
        if repair_utt.is_repair and repair_utt.intended_concept in UNIVERSAL_CONCEPTS:
            self.lexicon.apply_repair(repair_utt.tokens, repair_utt.intended_concept)

    def teach(self, token: str, concept: str, strength: float = 0.4):
        self.lexicon.teach(token, concept, strength)
        self.times_taught += 1

    def update_from_consequence(self, consequence: Consequence, utterance_that_led_here: Optional[Utterance]):
        if utterance_that_led_here:
            self.lexicon.update_from_consequence(utterance_that_led_here.tokens, consequence)

    def spawn_child(self, child_id: int) -> "SpeechOrgan":
        child_genome = self.genome.mutate()
        child_lexicon = Lexicon(child_genome.active_vocab())
        child_lexicon.inherit_from(self.lexicon, noise=0.015)
        return SpeechOrgan(child_id, child_genome, child_lexicon)

    def recent_speech(self, n: int = 3) -> List[str]:
        return [u.text for u in list(self._recent_utts)[-n:]]

    def stats(self) -> Dict[str, Any]:
        total = self.times_spoke + self.times_silent_choice + self.times_silent_fear
        return {
            "id": self.mote_id,
            "spoke": self.times_spoke,
            "silent_choice": self.times_silent_choice,
            "silent_fear": self.times_silent_fear,
            "directed": self.times_directed,
            "broadcast": self.times_broadcast,
            "repairs_sent": self.times_repair,
            "queries": self.times_queried,
            "taught": self.times_taught,
            "speak_rate": round(self.times_spoke / max(1, total), 3),
            "direct_rate": round(self.times_directed / max(1, self.times_spoke), 3),
            "semantic_success": self.audit.semantic_success_rate(),
            "genome": self.genome.to_dict(),
            "lexicon": self.lexicon.snapshot(),
            "recent": self.recent_speech(),
        }

```


# FILE: tais_core/mote.py

```python
"""
tais_core.mote
==============

Universal domain-blind mote.

This is intentionally small. It does not know chemistry, math, physics, or
GridWorld. It knows only:

    observe through a WorldInterface
    choose a Transformation
    predict consequence
    act
    receive Consequence
    update memory and energy

If this class must be edited to add a new domain, the base model has failed.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .memory import MoteMemory
from .reality import Consequence, RealityGraph, Transformation, WorldInterface
from .speech import SpeechOrgan


@dataclass
class MetaGenes:
    curiosity: float = 0.25
    skepticism: float = 0.25
    risk_tolerance: float = 0.35
    teaching_bias: float = 0.20
    memory_compression: float = 0.30
    analogy_bias: float = 0.35

    def mutate(self, sigma: float = 0.04) -> "MetaGenes":
        def clamp(x):
            return max(0.0, min(1.0, x))
        return MetaGenes(
            curiosity=clamp(self.curiosity + random.gauss(0, sigma)),
            skepticism=clamp(self.skepticism + random.gauss(0, sigma)),
            risk_tolerance=clamp(self.risk_tolerance + random.gauss(0, sigma)),
            teaching_bias=clamp(self.teaching_bias + random.gauss(0, sigma)),
            memory_compression=clamp(self.memory_compression + random.gauss(0, sigma)),
            analogy_bias=clamp(self.analogy_bias + random.gauss(0, sigma)),
        )


class UniversalMote:
    """A domain-blind mote operating over any WorldInterface."""

    _id = 0

    def __init__(self, energy: float = 100.0, parent_id: int = -1):
        UniversalMote._id += 1
        self.id = UniversalMote._id
        self.parent_id = parent_id
        self.energy = energy
        self.age = 0
        self.alive = True
        self.memory = MoteMemory()
        self.speech = SpeechOrgan(self.id)
        self.meta = MetaGenes()
        self.domain_history: List[str] = []
        self.total_reward = 0.0
        self.total_penalty = 0.0
        self.actions_taken = 0
        self.invalid_actions = 0
        self.last_prediction = 0.0
        self.last_consequence: Optional[Consequence] = None
        self.transfer_prior_uses = 0
        self.transfer_prior_total_strength = 0.0
        self.transfer_prior_correct = 0
        self.transfer_prior_incorrect = 0
        self._last_chosen_transfer_boost = 0.0
        self.domain_action_counts: Dict[str, int] = {}

    def state(self, **extra) -> Dict[str, Any]:
        base = {
            "mote_id": self.id,
            "energy": self.energy,
            "age": self.age,
            "curiosity": self.meta.curiosity,
            "skepticism": self.meta.skepticism,
            "risk_tolerance": self.meta.risk_tolerance,
        }
        base.update(extra)
        return base

    def classify_action_role(
        self,
        action: Transformation,
        world: WorldInterface,
        graph_before: RealityGraph,
        graph_after: RealityGraph,
        consequence: Consequence,
        mote_state: Dict[str, Any],
        predicted: float,
    ) -> str:
        """Classify functional action role from consequence and evaluate() delta."""
        try:
            score_before = world.evaluate(graph_before, mote_state)
            score_after = world.evaluate(graph_after, mote_state)
        except Exception:
            score_before = score_after = 0.0
        delta_score = score_after - score_before
        pred_error = abs(predicted - consequence.net)

        if not consequence.valid or consequence.net < -0.5:
            return "FAILED"
        if action.role_hint:
            return action.role_hint
        if delta_score > 0.25 and consequence.net > 0:
            if action.universal_op in {"TRANSFORM", "COMPOSE"}:
                return "TRANSFORM_TOWARD_GOAL"
            return "APPROACH_GOOD"
        if action.universal_op == "MOVE_TOWARD" and consequence.net > 0:
            return "APPROACH_GOOD"
        if action.universal_op in {"VERIFY", "TEST"} and consequence.net >= 0:
            return "VERIFY_UNCERTAIN"
        if action.universal_op == "MOVE_AWAY" and consequence.net > 0:
            return "AVOID_BAD"
        if pred_error > 2.0 and consequence.net >= -0.5:
            return "EXPLORE_UNCERTAIN"
        if consequence.net >= 0:
            return "MAINTAIN_STABLE"
        return "UNCLASSIFIED"

    def choose_action(self, observation: RealityGraph, actions: List[Transformation]) -> Optional[Transformation]:
        if not actions:
            return None

        # Explore if the memory says uncertainty is high or curiosity fires.
        if self.memory.should_explore(actions, curiosity=self.meta.curiosity):
            return random.choice(actions)

        transfer_boosts, transfer_used = self.memory.transfer_action_priors(observation, actions)
        if transfer_used:
            self.transfer_prior_uses += transfer_used
            self.transfer_prior_total_strength += sum(abs(v) for v in transfer_boosts.values())

        # Transfer priors should help early in a new domain, then yield to local
        # evidence. Otherwise old-domain confidence becomes negative transfer.
        local_exp = self.domain_action_counts.get(observation.domain, 0)
        transfer_decay_rate = 0.08
        effective_analogy_weight = self.meta.analogy_bias / (1.0 + transfer_decay_rate * local_exp)

        best_action = None
        best_score = float("-inf")
        best_transfer = 0.0
        for action in actions:
            predicted = self.memory.predict_action(action, observation)
            historical = self.memory.episodic.action_value(action.name)
            risk = self.memory.episodic.action_risk(action.name)
            cost = action.compute_cost(observation, self.state())
            transfer = effective_analogy_weight * transfer_boosts.get(action.name, 0.0)
            score = predicted + historical + transfer - cost - self.meta.skepticism * risk
            if score > best_score:
                best_score = score
                best_action = action
                best_transfer = transfer
        self._last_chosen_transfer_boost = best_transfer
        return best_action or random.choice(actions)

    def step(
        self,
        world: WorldInterface,
        graph: RealityGraph,
        mote_position: Any = None,
        tick: int = 0,
        extra_state: Optional[Dict[str, Any]] = None,
    ) -> Tuple[RealityGraph, Consequence, Optional[Transformation]]:
        """One observe→predict→act→learn cycle."""
        if not self.alive:
            return graph, Consequence(valid=False, penalty=999, explanation={"why": "dead"}), None

        mote_state = self.state(**(extra_state or {}))
        observation = world.observe(graph, mote_position)
        actions = world.valid_actions(observation, mote_state)
        action = self.choose_action(observation, actions)
        if action is None:
            cons = Consequence(penalty=0.2, valid=False, concept_signals={"VOID": 1.0}, explanation={"why": "no actions"})
            self.energy += cons.net
            self.last_consequence = cons
            return graph, cons, None

        predicted = self.memory.predict_action(action, observation)
        self.last_prediction = predicted
        new_graph, cons = world.act(graph, action, mote_state)
        action_role = self.classify_action_role(action, world, graph, new_graph, cons, mote_state, predicted)
        action_cost = action.compute_cost(observation, mote_state)
        self.energy += cons.net - action_cost
        self.total_reward += cons.reward
        self.total_penalty += cons.penalty + action_cost
        self.actions_taken += 1
        self.invalid_actions += 0 if cons.valid else 1
        self.domain_action_counts[world.domain_name] = self.domain_action_counts.get(world.domain_name, 0) + 1
        if abs(self._last_chosen_transfer_boost) > 1e-9:
            if cons.net > 0:
                self.transfer_prior_correct += 1
            elif cons.net < 0:
                self.transfer_prior_incorrect += 1
        self.age += 1
        self.last_consequence = cons
        self.domain_history.append(world.domain_name)

        self.memory.record_episode(
            state_before=observation,
            transformation=action,
            consequence=cons,
            predicted=predicted,
            domain=world.domain_name,
            tick=tick,
            action_role=action_role,
        )

        if self.energy <= 0:
            self.alive = False

        return new_graph, cons, action

    def reproduce(self) -> "UniversalMote":
        self.energy /= 2
        child = UniversalMote(energy=self.energy, parent_id=self.id)
        child.meta = self.meta.mutate()
        child.speech = self.speech.spawn_child(child.id)
        # Pattern/episodic memory is not copied wholesale. The child receives
        # speech priors genetically; cultural memory is a separate mechanism.
        return child

    def metrics(self) -> Dict[str, Any]:
        mean_pred = self.memory.prediction.mean_error()
        return {
            "id": self.id,
            "energy": round(self.energy, 3),
            "age": self.age,
            "alive": self.alive,
            "actions": self.actions_taken,
            "invalid_actions": self.invalid_actions,
            "total_reward": round(self.total_reward, 3),
            "total_penalty": round(self.total_penalty, 3),
            "mean_prediction_error": None if mean_pred == float("inf") else round(mean_pred, 3),
            "prediction_improving": self.memory.prediction.error_trend() < 0,
            "transfer_prior_uses": self.transfer_prior_uses,
            "transfer_prior_total_strength": round(self.transfer_prior_total_strength, 3),
            "transfer_prior_correct": self.transfer_prior_correct,
            "transfer_prior_incorrect": self.transfer_prior_incorrect,
            "transfer_prior_precision": round(self.transfer_prior_correct / max(1, self.transfer_prior_correct + self.transfer_prior_incorrect), 3),
            "memory": self.memory.summary(),
            "speech": self.speech.stats(),
            "domains": sorted(set(self.domain_history)),
        }

```


# FILE: tais_core/domains/__init__.py

```python
"""Tiny validation domains for the TAIS universal base."""

from .gridworld import GridGraphWorld, make_grid_graph
from .sequences import SequenceWorld, make_sequence_graph
from .rules import RuleWorld, make_rule_graph

__all__ = [
    "GridGraphWorld",
    "make_grid_graph",
    "SequenceWorld",
    "make_sequence_graph",
    "RuleWorld",
    "make_rule_graph",
]

```


# FILE: tais_core/domains/gridworld.py

```python
"""Tiny graph GridWorld validation domain."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from ..reality import Consequence, Entity, RealityGraph, Relation, Transformation, WorldInterface


def make_grid_graph(threat_near_resource: bool = True) -> RealityGraph:
    g = RealityGraph("grid", "tiny_grid")
    g.add_entity(Entity("mote", "AGENT", {"x": 0, "y": 0}))
    g.add_entity(Entity("food", "RESOURCE", {"kind": "food", "value": 8.0}))
    g.add_entity(Entity("pred", "THREAT", {"kind": "predator", "danger": 1.0}))
    g.add_relation(Relation("mote", "SEES", "food"))
    g.add_relation(Relation("mote", "SEES", "pred"))
    if threat_near_resource:
        g.add_relation(Relation("pred", "NEAR", "food"))
    return g


class GridGraphWorld(WorldInterface):
    domain_name = "grid"

    def observe(self, graph: RealityGraph, mote_position: Any) -> RealityGraph:
        return graph.neighborhood("mote", hops=1)

    def valid_actions(self, graph: RealityGraph, mote_state: Dict) -> List[Transformation]:
        return [
            Transformation("approach_resource", self.domain_name, "MOVE_TOWARD", base_cost=0.5),
            Transformation("avoid_threat", self.domain_name, "MOVE_AWAY", base_cost=0.5),
            Transformation("verify_safety", self.domain_name, "VERIFY", base_cost=0.2),
        ]

    def act(self, graph: RealityGraph, transformation: Transformation, mote_state: Dict) -> Tuple[RealityGraph, Consequence]:
        if transformation.name == "approach_resource":
            if graph.get_relation("pred", "NEAR", "food"):
                return graph, Consequence(
                    reward=1.0,
                    penalty=5.0,
                    valid=True,
                    concept_signals={"DANGER": 1.0, "BAD": 0.7},
                    explanation={"why": "resource was near threat"},
                )
            return graph, Consequence(
                reward=5.0,
                valid=True,
                concept_signals={"RESOURCE": 1.0, "GOOD": 0.8},
                explanation={"why": "safe resource approached"},
            )
        if transformation.name == "avoid_threat":
            return graph, Consequence(
                reward=4.0,
                valid=True,
                concept_signals={"DANGER": 1.0, "SAFE": 0.7},
                explanation={"why": "threat avoided"},
            )
        if transformation.name == "verify_safety":
            reward = 2.0 if graph.get_relation("pred", "NEAR", "food") else 1.0
            return graph, Consequence(
                reward=reward,
                valid=True,
                concept_signals={"TRUST": 0.4, "DANGER": 0.4 if reward > 1 else 0.0},
                explanation={"why": "safety checked"},
            )
        return graph, Consequence(penalty=1.0, valid=False, concept_signals={"BAD": 1.0})

    def evaluate(self, graph: RealityGraph, mote_state: Dict) -> float:
        return -1.0 if graph.get_relation("pred", "NEAR", "food") else 5.0

    def concepts(self) -> List[str]:
        return ["DANGER", "SAFE", "RESOURCE", "GOOD", "BAD"]

```


# FILE: tais_core/domains/sequences.py

```python
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

```


# FILE: tais_core/domains/rules.py

```python
"""Tiny rule satisfaction validation domain."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from ..reality import Consequence, Entity, RealityGraph, Relation, Transformation, WorldInterface


def make_rule_graph() -> RealityGraph:
    g = RealityGraph("rules", "modus_ponens_toy")
    g.add_entity(Entity("fact_a", "FACT", {"truth": True}))
    g.add_entity(Entity("fact_b", "FACT", {"truth": True}))
    g.add_entity(Entity("rule_ab", "RULE", {"kind": "implies"}))
    g.add_relation(Relation("fact_a", "SATISFIES", "rule_ab"))
    g.add_relation(Relation("rule_ab", "IMPLIES", "fact_b"))
    return g


class RuleWorld(WorldInterface):
    domain_name = "rules"

    def observe(self, graph: RealityGraph, mote_position: Any) -> RealityGraph:
        return graph.neighborhood("rule_ab", hops=2)

    def valid_actions(self, graph: RealityGraph, mote_state: Dict) -> List[Transformation]:
        return [
            Transformation("apply_implication", self.domain_name, "TRANSFORM", base_cost=0.4),
            Transformation("verify_rule", self.domain_name, "VERIFY", base_cost=0.2),
            Transformation("random_assert", self.domain_name, "MUTATE", base_cost=0.5),
        ]

    def act(self, graph: RealityGraph, transformation: Transformation, mote_state: Dict) -> Tuple[RealityGraph, Consequence]:
        if transformation.name == "apply_implication":
            if graph.get_relation("fact_a", "SATISFIES", "rule_ab") and graph.get_relation("rule_ab", "IMPLIES", "fact_b"):
                after = graph.snapshot()
                if not after.get_entity("fact_b_known"):
                    after.add_entity(Entity("fact_b_known", "FACT", {"truth": True, "derived": True}))
                    after.add_relation(Relation("fact_b", "SUPPORTS", "fact_b_known"))
                return after, Consequence(
                    reward=4.0,
                    valid=True,
                    concept_signals={"GOOD": 1.0, "TRUST": 0.6, "CONFIRM": 0.6},
                    explanation={"why": "valid implication applied"},
                    graph_delta=graph.diff(after),
                )
        if transformation.name == "verify_rule":
            ok = bool(graph.get_relation("rule_ab", "IMPLIES", "fact_b"))
            return graph, Consequence(
                reward=1.5 if ok else 0.0,
                penalty=0.0 if ok else 2.0,
                valid=ok,
                concept_signals={"CONFIRM": 0.7 if ok else 0.0, "BAD": 0.8 if not ok else 0.0},
                explanation={"why": "rule checked", "valid": ok},
            )
        if transformation.name == "random_assert":
            return graph, Consequence(
                penalty=3.0,
                valid=False,
                concept_signals={"BAD": 1.0, "DENY": 0.6},
                explanation={"why": "unsupported assertion"},
            )
        return graph, Consequence(penalty=1.0, valid=False, concept_signals={"BAD": 1.0})

    def evaluate(self, graph: RealityGraph, mote_state: Dict) -> float:
        return 10.0 if graph.get_entity("fact_b_known") else 0.0

    def concepts(self) -> List[str]:
        return ["GOOD", "BAD", "TRUST", "CONFIRM", "DENY"]

```


# FILE: tests/test_tais_core.py

```python
import math
import unittest

from tais_core.reality import (
    Entity,
    Relation,
    RealityGraph,
    GraphPattern,
    Transformation,
    Constraint,
    Consequence,
    WorldInterface,
)
from tais_core.memory import MoteMemory, CulturalMemory
from tais_core.speech import SpeechOrgan, Lexicon, Utterance


class TinyRuleWorld(WorldInterface):
    """Minimal domain lens used to test the universal four-function contract."""

    domain_name = "tiny_rules"

    def observe(self, graph, mote_position):
        # The attention mechanism: observe only the focused entity's neighborhood.
        return graph.neighborhood(mote_position, hops=1)

    def valid_actions(self, graph, mote_state):
        return [
            Transformation("apply_rule", self.domain_name, "TRANSFORM", base_cost=1.0),
            Transformation("verify", self.domain_name, "VERIFY", base_cost=0.5),
        ]

    def act(self, graph, transformation, mote_state):
        before = graph.snapshot()
        after = graph.snapshot()
        if transformation.name == "apply_rule":
            # if fact_a IMPLIES fact_b, add inferred fact_b_known
            if after.get_relation("fact_a", "IMPLIES", "fact_b"):
                after.add_entity(Entity("fact_b_known", "FACT", {"truth": True}))
                after.add_relation(Relation("fact_b", "SUPPORTS", "fact_b_known"))
                cons = Consequence(
                    reward=4.0,
                    valid=True,
                    concept_signals={"GOOD": 1.0, "TRUST": 0.5},
                    explanation={"why": "valid implication applied"},
                    graph_delta=before.diff(after),
                )
                return after, cons
        return graph, Consequence(penalty=2.0, valid=False, concept_signals={"BAD": 1.0}, explanation={"why": "invalid action"})

    def evaluate(self, graph, mote_state):
        return 10.0 if graph.get_entity("fact_b_known") else 0.0

    def concepts(self):
        return ["GOOD", "BAD", "TRUST"]


class RealityGraphTests(unittest.TestCase):
    def make_grid_graph(self):
        g = RealityGraph("grid", "danger_food")
        g.add_entity(Entity("pred", "THREAT", {"kind": "predator", "danger": 1.0}))
        g.add_entity(Entity("food", "RESOURCE", {"kind": "food", "value": 8.0}))
        g.add_relation(Relation("pred", "NEAR", "food"))
        return g

    def make_chem_graph(self):
        g = RealityGraph("chem", "toxic_binding")
        g.add_entity(Entity("tox", "TOXIC_GROUP", {"kind": "nitro", "danger": 1.0}))
        g.add_entity(Entity("site", "BINDING_SITE", {"kind": "pocket", "value": 8.0}))
        g.add_relation(Relation("tox", "ADJACENT_TO", "site"))
        return g

    def test_crud_neighborhood_and_diff(self):
        g = self.make_grid_graph()
        self.assertEqual(len(g.entities()), 2)
        self.assertEqual(len(g.relations()), 1)
        self.assertIsNotNone(g.get_relation("pred", "NEAR", "food"))

        n = g.neighborhood("pred", hops=1)
        self.assertEqual(len(n.entities()), 2)
        self.assertEqual(len(n.relations()), 1)

        g2 = g.snapshot()
        g2.update_entity("food", value=10.0)
        delta = g.diff(g2)
        self.assertEqual(delta.magnitude, 1)
        self.assertEqual(len(delta.entities_modified), 1)

        g3 = g.snapshot()
        g3.add_entity(Entity("water", "RESOURCE", {"kind": "water"}))
        g3.add_relation(Relation("food", "NEXT_TO", "water"))
        delta2 = g.diff(g3)
        self.assertEqual(len(delta2.entities_added), 1)
        self.assertEqual(len(delta2.relations_added), 1)

    def test_pattern_matching(self):
        g = self.make_grid_graph()
        pattern = GraphPattern(
            entities=[Entity("a", "THREAT", {}), Entity("b", "RESOURCE", {})],
            relations=[Relation("a", "NEAR", "b")],
        )
        matches = g.find_pattern(pattern)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["a"], "pred")
        self.assertEqual(matches[0]["b"], "food")

    def test_distance_and_analogy(self):
        grid = self.make_grid_graph()
        chem = self.make_chem_graph()
        self.assertGreater(grid.distance(chem), 0.0)

        pattern = GraphPattern(grid.entities(), grid.relations(), name="danger_near_resource", source_domain="grid")
        mapping = chem.analogize(pattern)
        self.assertTrue(mapping.is_useful)
        self.assertIn("pred", mapping.entity_map)
        self.assertIn("food", mapping.entity_map)

    def test_constraint(self):
        def no_more_than_two_entities(before, after, transformation):
            return 1.0 if len(after.entities()) > 2 else 0.0

        g = self.make_grid_graph()
        g2 = g.snapshot().add_entity(Entity("extra", "THING", {}))
        c = Constraint("max_two", "test", no_more_than_two_entities, hard=True)
        self.assertEqual(c.check(g, g, Transformation("noop", "test", "TEST")), 0.0)
        self.assertGreater(c.check(g, g2, Transformation("add", "test", "TRANSFORM")), 0.0)


class MemoryTests(unittest.TestCase):
    def make_pattern_graphs(self):
        grid = RealityGraph("grid")
        grid.add_entity(Entity("pred", "THREAT", {}))
        grid.add_entity(Entity("food", "RESOURCE", {}))
        grid.add_relation(Relation("pred", "NEAR", "food"))

        chem = RealityGraph("chem")
        chem.add_entity(Entity("tox", "TOXIC_GROUP", {}))
        chem.add_entity(Entity("site", "BINDING_SITE", {}))
        chem.add_relation(Relation("tox", "ADJACENT_TO", "site"))
        return grid, chem

    def test_episode_prediction_and_pattern_transfer(self):
        grid, chem = self.make_pattern_graphs()
        memory = MoteMemory()
        tr = Transformation("avoid", "grid", "MOVE_AWAY", base_cost=1.0)
        cons = Consequence(reward=5.0, concept_signals={"DANGER": 1.0}, explanation={"why": "avoided threat"})

        memory.record_episode(grid, tr, cons, predicted=0.0, domain="grid", tick=1)
        self.assertEqual(len(memory.episodic), 1)
        self.assertGreater(memory.episodic.action_value("avoid"), 0.0)
        self.assertEqual(len(memory.patterns), 1)

        transfers = memory.transfer_patterns_to(chem)
        self.assertTrue(transfers)
        self.assertTrue(transfers[0][1].is_useful)

    def test_cultural_memory(self):
        archive = CulturalMemory(capacity_per_domain=2)
        archive.write("chem", {"concept": "GOOD", "token": "lum"}, fitness=6.0)
        archive.write("chem", {"concept": "BAD", "token": "ka"}, fitness=7.0)
        archive.write("chem", {"concept": "GOOD", "token": "mi"}, fitness=8.0)
        self.assertEqual(len(archive.query("chem")), 2)
        self.assertEqual(archive.query("chem")[0]["token"], "mi")
        self.assertEqual(len(archive.query("chem", concept="GOOD")), 1)


class SpeechTests(unittest.TestCase):
    def test_lexicon_teaching_interpretation_and_repair(self):
        lx = Lexicon()
        lx.teach("ka", "DANGER", strength=0.8)
        self.assertEqual(lx.top_concept("ka"), "DANGER")
        interp = lx.interpret(["ka"])
        self.assertEqual(max(interp, key=interp.get), "DANGER")

        # Repair pushes token toward intended concept.
        lx.teach("lum", "GOOD", strength=0.5)
        before = lx.weight("lum", "BAD")
        lx.apply_repair(["lum"], "BAD", lr=0.5)
        self.assertGreater(lx.weight("lum", "BAD"), before)

    def test_speech_compose_receive_audit(self):
        speaker = SpeechOrgan(1)
        listener = SpeechOrgan(2)
        speaker.teach("ka", "DANGER", strength=0.8)
        listener.teach("ka", "DANGER", strength=0.8)

        utt = speaker.compose(
            intent="DANGER",
            neighbors=[2],
            mote_state={
                "energy": 50,
                "fitness": 5,
                "nearest_threat": 3.0,
                "position": [1.0, 2.0],
                "neediest_neighbor_id": 2,
            },
            domain="grid",
            tick=1,
            info_delta=5.0,
        )
        self.assertIsNotNone(utt)
        concepts = listener.receive(utt)
        self.assertEqual(max(concepts, key=concepts.get), "DANGER")
        listener.record_action_outcome(utt, "MOVE_AWAY", aligned=True, outcome="GOOD")
        self.assertGreaterEqual(listener.audit.semantic_success_rate(), 0.5)

    def test_repair_utterance(self):
        speaker = SpeechOrgan(1)
        speaker.teach("no", "DENY", strength=0.8)
        speaker.teach("ka", "DANGER", strength=0.8)
        original = Utterance(["ka"], 1, 2, "DANGER", [0, 0], 1.0, 50.0, domain="grid", tick=1)
        repair = speaker.fire_repair(original, listener_id=2, tick=2)
        self.assertIsNotNone(repair)
        self.assertTrue(repair.is_repair)
        self.assertEqual(repair.target_id, 2)


class WorldInterfaceTests(unittest.TestCase):
    def test_tiny_rule_world_four_function_contract(self):
        g = RealityGraph("tiny_rules")
        g.add_entity(Entity("fact_a", "FACT", {"truth": True}))
        g.add_entity(Entity("fact_b", "FACT", {"truth": True}))
        g.add_relation(Relation("fact_a", "IMPLIES", "fact_b"))
        world = TinyRuleWorld()

        obs = world.observe(g, "fact_a")
        self.assertEqual(len(obs.entities()), 2)
        actions = world.valid_actions(obs, {})
        self.assertEqual({a.universal_op for a in actions}, {"TRANSFORM", "VERIFY"})
        after, cons = world.act(g, actions[0], {})
        self.assertTrue(cons.valid)
        self.assertGreater(cons.net, 0)
        self.assertIsNotNone(after.get_entity("fact_b_known"))
        self.assertGreater(world.evaluate(after, {}), world.evaluate(g, {}))


if __name__ == "__main__":
    unittest.main(verbosity=2)

```


# FILE: tests/test_base_validation.py

```python
import random
import unittest

from tais_core.mote import UniversalMote
from tais_core.domains import (
    GridGraphWorld,
    SequenceWorld,
    RuleWorld,
    make_grid_graph,
    make_sequence_graph,
    make_rule_graph,
)
from tais_core.reality import RealityGraph, Entity, Transformation, Consequence, WorldInterface


class EmptyNovelWorld(WorldInterface):
    """A deliberately new domain to test injection without mote edits."""

    domain_name = "novel_empty"

    def observe(self, graph, mote_position):
        return graph

    def valid_actions(self, graph, mote_state):
        return [Transformation("verify_empty", self.domain_name, "VERIFY", base_cost=0.1)]

    def act(self, graph, transformation, mote_state):
        return graph, Consequence(reward=1.0, valid=True, concept_signals={"GOOD": 1.0}, explanation={"why": "empty verified"})

    def evaluate(self, graph, mote_state):
        return 1.0


def run_sequence_training(mote, episodes=24):
    world = SequenceWorld()
    errors = []
    for i in range(episodes):
        # same rule: +1. The named action predict_delta_1 can accumulate value.
        start = 1 + (i % 5)
        g = make_sequence_graph([start, start + 1, start + 2], target_next=start + 3)
        _g2, cons, action = mote.step(world, g, tick=i)
        errors.append(abs(mote.last_prediction - cons.net))
    return errors, mote


class BaseValidationBattery(unittest.TestCase):
    def test_same_universal_mote_runs_three_domains(self):
        random.seed(7)
        mote = UniversalMote(energy=100)

        grid = GridGraphWorld()
        g = make_grid_graph(threat_near_resource=True)
        for t in range(5):
            g, _cons, _action = mote.step(grid, g, mote_position="mote", tick=t)

        seq_errors, _ = run_sequence_training(mote, episodes=12)

        rules = RuleWorld()
        rg = make_rule_graph()
        for t in range(5):
            rg, _cons, _action = mote.step(rules, rg, mote_position="rule_ab", tick=100 + t)

        self.assertIn("grid", mote.domain_history)
        self.assertIn("sequence", mote.domain_history)
        self.assertIn("rules", mote.domain_history)
        self.assertGreater(mote.actions_taken, 10)
        self.assertTrue(mote.alive)

    def test_prediction_error_reduces_in_sequence_world(self):
        random.seed(11)
        mote = UniversalMote(energy=100)
        errors, mote = run_sequence_training(mote, episodes=40)
        early = sum(errors[:10]) / 10
        late = sum(errors[-10:]) / 10
        # This is a weak criterion because exploration remains stochastic.
        # It should improve substantially in the tiny repeated +1 domain.
        self.assertLess(late, early)
        self.assertLess(mote.memory.prediction.error_trend(), 0.0)

    def test_transfer_advantage_sequence_pretraining(self):
        random.seed(13)
        trained = UniversalMote(energy=100)
        fresh = UniversalMote(energy=100)
        run_sequence_training(trained, episodes=30)

        trained_errors, _ = run_sequence_training(trained, episodes=10)
        fresh_errors, _ = run_sequence_training(fresh, episodes=10)
        trained_mean = sum(trained_errors) / len(trained_errors)
        fresh_mean = sum(fresh_errors) / len(fresh_errors)
        self.assertLess(trained_mean, fresh_mean)

    def test_pattern_transfer_grid_to_rules_or_sequence_exists(self):
        random.seed(17)
        mote = UniversalMote(energy=100)
        grid = GridGraphWorld()
        g = make_grid_graph(threat_near_resource=True)
        for t in range(8):
            g, _cons, _action = mote.step(grid, g, mote_position="mote", tick=t)

        rule_graph = make_rule_graph()
        transfers = mote.memory.transfer_patterns_to(rule_graph)
        self.assertTrue(transfers)
        self.assertGreater(transfers[0][1].confidence, 0.0)

    def test_new_domain_injection_without_mote_modification(self):
        random.seed(19)
        mote = UniversalMote(energy=20)
        world = EmptyNovelWorld()
        graph = RealityGraph("novel_empty")
        graph.add_entity(Entity("empty", "VOID", {}))
        graph, cons, action = mote.step(world, graph, mote_position=None, tick=1)
        self.assertTrue(cons.valid)
        self.assertEqual(action.name, "verify_empty")
        self.assertIn("novel_empty", mote.domain_history)
        self.assertGreater(mote.energy, 20)


if __name__ == "__main__":
    unittest.main(verbosity=2)

```


# FILE: tests/test_core.py

```python
from tais_core.reality import Entity, Relation, RealityGraph, GraphPattern, Transformation, Consequence
from tais_core.memory import MoteMemory
from tais_core.speech import SpeechOrgan


def build_grid_graph():
    g = RealityGraph("grid", "danger_food")
    g.add_entity(Entity("pred", "THREAT", {"kind": "predator"}))
    g.add_entity(Entity("food", "RESOURCE", {"kind": "food"}))
    g.add_relation(Relation("pred", "NEAR", "food"))
    return g


def build_chem_graph():
    g = RealityGraph("chem", "toxic_binding")
    g.add_entity(Entity("tox", "TOXIC_GROUP", {"kind": "nitro"}))
    g.add_entity(Entity("site", "BINDING_SITE", {"kind": "pocket"}))
    g.add_relation(Relation("tox", "ADJACENT_TO", "site"))
    return g


def main():
    g1 = build_grid_graph()
    g2 = g1.snapshot()
    g2.update_entity("food", value=10)
    delta = g1.diff(g2)
    assert delta.magnitude == 1
    assert g1.distance(g2) == 0.0  # same structure; property diff not in distance

    pattern = GraphPattern(g1.entities(), g1.relations(), name="danger_near_resource", source_domain="grid")
    chem = build_chem_graph()
    analogy = chem.analogize(pattern)
    print("analogy", analogy.confidence, analogy.explanation, analogy.entity_map)
    assert analogy.confidence > 0

    mem = MoteMemory()
    tr = Transformation("avoid_pattern", "grid", "MOVE_AWAY", base_cost=1.0)
    cons = Consequence(reward=5, concept_signals={"DANGER": 1.0}, explanation={"why": "avoided threat"})
    mem.record_episode(g1, tr, cons, predicted=0.0, domain="grid", tick=1)
    transfers = mem.transfer_patterns_to(chem)
    print("transfers", [(p.name, m.confidence) for p, m in transfers])
    assert transfers

    s1 = SpeechOrgan(1)
    s2 = SpeechOrgan(2)
    s1.teach("ka", "DANGER", strength=0.8)
    utt = s1.compose(
        intent="DANGER",
        neighbors=[2],
        mote_state={"energy": 50, "fitness": 5, "nearest_threat": 3, "position": [0, 0], "neediest_neighbor_id": 2},
        domain="grid",
        tick=1,
        info_delta=5,
    )
    assert utt is not None
    interpreted = s2.receive(utt)
    print("utterance", utt.text, "top", max(interpreted, key=interpreted.get))
    s2.record_action_outcome(utt, "MOVE_AWAY", aligned=True, outcome="GOOD")
    print("speech stats", s2.stats()["semantic_success"])


if __name__ == "__main__":
    main()

```


# FILE: experiments_cross_domain_transfer.py

```python
"""
Cross-domain transfer experiment for TAIS core.

Question:
    Does GridWorld pretraining improve RuleWorld learning vs fresh motes?

This is intentionally an experiment, not a unit test. It is allowed to fail.
A failure means the architecture has not yet demonstrated cross-domain transfer
performance, even if the graph analogy mechanism exists.

Run:
    PYTHONPATH=. python3 experiments_cross_domain_transfer.py
"""

from __future__ import annotations

import json
import random
import statistics
from dataclasses import asdict, dataclass
from typing import List, Optional

from tais_core.mote import UniversalMote
from tais_core.domains import GridGraphWorld, RuleWorld, make_grid_graph, make_rule_graph


@dataclass
class TrialResult:
    seed: int
    condition: str
    total_reward: float
    invalid_actions: int
    actions_taken: int
    first_apply_tick: Optional[int]
    final_energy: float
    mean_prediction_error: Optional[float]
    transfer_prior_uses: int
    transfer_prior_total_strength: float
    transfer_prior_correct: int
    transfer_prior_incorrect: int
    transfer_prior_precision: float
    actions: List[str]


def pretrain_grid(mote: UniversalMote, ticks: int, seed: int, mixed: bool = False):
    random.seed(seed)
    world = GridGraphWorld()
    graph = make_grid_graph(threat_near_resource=True)
    for t in range(ticks):
        # Mixed curriculum exposes both AVOID_BAD and APPROACH_GOOD roles.
        if mixed:
            graph = make_grid_graph(threat_near_resource=(t % 2 == 0))
        graph, _cons, _action = mote.step(world, graph, mote_position="mote", tick=t)
    return mote


def run_rule_trial(mote: UniversalMote, ticks: int, seed: int, condition: str) -> TrialResult:
    random.seed(seed)
    world = RuleWorld()
    graph = make_rule_graph()
    total_reward = 0.0
    actions: List[str] = []
    first_apply_tick = None
    for t in range(ticks):
        graph, cons, action = mote.step(world, graph, mote_position="rule_ab", tick=t)
        total_reward += cons.net
        name = action.name if action else "NONE"
        actions.append(name)
        if name == "apply_implication" and first_apply_tick is None:
            first_apply_tick = t
    metrics = mote.metrics()
    return TrialResult(
        seed=seed,
        condition=condition,
        total_reward=round(total_reward, 4),
        invalid_actions=mote.invalid_actions,
        actions_taken=mote.actions_taken,
        first_apply_tick=first_apply_tick,
        final_energy=round(mote.energy, 4),
        mean_prediction_error=metrics["mean_prediction_error"],
        transfer_prior_uses=metrics.get("transfer_prior_uses", 0),
        transfer_prior_total_strength=metrics.get("transfer_prior_total_strength", 0.0),
        transfer_prior_correct=metrics.get("transfer_prior_correct", 0),
        transfer_prior_incorrect=metrics.get("transfer_prior_incorrect", 0),
        transfer_prior_precision=metrics.get("transfer_prior_precision", 0.0),
        actions=actions,
    )


def mean(xs):
    return statistics.mean(xs) if xs else None


def summarize(results: List[TrialResult]) -> dict:
    return {
        "n": len(results),
        "mean_total_reward": mean([r.total_reward for r in results]),
        "mean_invalid_actions": mean([r.invalid_actions for r in results]),
        "mean_first_apply_tick": mean([r.first_apply_tick for r in results if r.first_apply_tick is not None]),
        "never_applied": sum(1 for r in results if r.first_apply_tick is None),
        "mean_final_energy": mean([r.final_energy for r in results]),
        "mean_prediction_error": mean([r.mean_prediction_error for r in results if r.mean_prediction_error is not None]),
        "mean_transfer_prior_uses": mean([r.transfer_prior_uses for r in results]),
        "mean_transfer_prior_strength": mean([r.transfer_prior_total_strength for r in results]),
        "mean_transfer_prior_correct": mean([r.transfer_prior_correct for r in results]),
        "mean_transfer_prior_incorrect": mean([r.transfer_prior_incorrect for r in results]),
        "mean_transfer_prior_precision": mean([r.transfer_prior_precision for r in results]),
    }


def run_experiment(seeds=50, pretrain_ticks=20, rule_ticks=12, mixed_pretraining: bool = False) -> dict:
    fresh: List[TrialResult] = []
    pretrained: List[TrialResult] = []

    for seed in range(seeds):
        fresh_mote = UniversalMote(energy=100)
        fresh.append(run_rule_trial(fresh_mote, rule_ticks, seed=10_000 + seed, condition="fresh"))

        pre_mote = UniversalMote(energy=100)
        pretrain_grid(pre_mote, pretrain_ticks, seed=20_000 + seed, mixed=mixed_pretraining)
        condition = "grid_mixed_pretrained" if mixed_pretraining else "grid_pretrained"
        pretrained.append(run_rule_trial(pre_mote, rule_ticks, seed=10_000 + seed, condition=condition))

    summary = {
        "experiment": "grid_pretraining_to_ruleworld",
        "seeds": seeds,
        "pretrain_ticks": pretrain_ticks,
        "rule_ticks": rule_ticks,
        "mixed_pretraining": mixed_pretraining,
        "fresh": summarize(fresh),
        "grid_pretrained": summarize(pretrained),
        "deltas_pretrained_minus_fresh": {},
        "interpretation": "",
        "trials": [asdict(r) for r in fresh + pretrained],
    }
    for key in ["mean_total_reward", "mean_final_energy"]:
        summary["deltas_pretrained_minus_fresh"][key] = summary["grid_pretrained"][key] - summary["fresh"][key]
    for key in ["mean_invalid_actions", "mean_first_apply_tick", "mean_prediction_error", "mean_transfer_prior_uses", "mean_transfer_prior_strength", "mean_transfer_prior_correct", "mean_transfer_prior_incorrect", "mean_transfer_prior_precision"]:
        a = summary["grid_pretrained"][key]
        b = summary["fresh"][key]
        summary["deltas_pretrained_minus_fresh"][key] = None if a is None or b is None else a - b

    reward_delta = summary["deltas_pretrained_minus_fresh"]["mean_total_reward"]
    first_apply_delta = summary["deltas_pretrained_minus_fresh"]["mean_first_apply_tick"]
    invalid_delta = summary["deltas_pretrained_minus_fresh"]["mean_invalid_actions"]

    if reward_delta > 0 and (first_apply_delta is None or first_apply_delta < 0) and invalid_delta <= 0:
        interp = "PASS: grid pretraining improved RuleWorld reward and did not increase invalid actions."
    elif reward_delta > 0:
        interp = "MIXED: grid pretraining improved reward but other metrics are not clearly better."
    else:
        interp = "FAIL/INCONCLUSIVE: grid pretraining did not improve RuleWorld reward."
    summary["interpretation"] = interp
    return summary


if __name__ == "__main__":
    result = run_experiment(seeds=50, pretrain_ticks=20, rule_ticks=12)
    print(json.dumps({k: v for k, v in result.items() if k != "trials"}, indent=2))
    with open("cross_domain_transfer_results.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print("saved → cross_domain_transfer_results.json")

```


# FILE: experiments_statistical_replication.py

```python
"""
200-seed statistical replication for the first positive TAIS transfer signal.

Question:
    Does mixed GridWorld pretraining improve early RuleWorld performance?

Design:
    Paired seeds.
    For each seed:
      A) fresh mote -> RuleWorld for 12 ticks
      B) mixed GridWorld-pretrained mote -> RuleWorld for 12 ticks
    Compare pretrained - fresh.

Statistics:
    - paired mean delta
    - bootstrap 95% CI
    - paired Cohen's d
    - sign-flip permutation p-value

Run:
    PYTHONPATH=. python3 experiments_statistical_replication.py
"""

from __future__ import annotations

import json
import math
import random
import statistics
from typing import Callable, Dict, List, Optional

from tais_core.mote import UniversalMote
from experiments_cross_domain_transfer import pretrain_grid, run_rule_trial


def paired_trials(seeds: int = 200, pretrain_ticks: int = 20, rule_ticks: int = 12):
    rows = []
    for seed in range(seeds):
        eval_seed = 100_000 + seed
        pre_seed = 200_000 + seed

        fresh = UniversalMote(energy=100)
        fresh_res = run_rule_trial(fresh, rule_ticks, seed=eval_seed, condition="fresh")

        pre = UniversalMote(energy=100)
        pretrain_grid(pre, pretrain_ticks, seed=pre_seed, mixed=True)
        pre_res = run_rule_trial(pre, rule_ticks, seed=eval_seed, condition="mixed_grid_pretrained")

        rows.append({"seed": seed, "fresh": fresh_res, "pretrained": pre_res})
    return rows


def first_apply_value(x: Optional[int], rule_ticks: int) -> int:
    # lower is better; never applied is worst and encoded as rule_ticks
    return rule_ticks if x is None else x


def metric_delta(row: dict, metric: str, rule_ticks: int) -> float:
    f = row["fresh"]
    p = row["pretrained"]
    if metric == "first_apply_tick":
        return first_apply_value(p.first_apply_tick, rule_ticks) - first_apply_value(f.first_apply_tick, rule_ticks)
    return float(getattr(p, metric)) - float(getattr(f, metric))


def bootstrap_ci(values: List[float], samples: int = 10000, alpha: float = 0.05, seed: int = 1234):
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(samples):
        means.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    lo = means[int((alpha / 2) * samples)]
    hi = means[int((1 - alpha / 2) * samples)]
    return lo, hi


def sign_flip_pvalue(values: List[float], samples: int = 50000, seed: int = 4321) -> float:
    """Two-sided paired randomization test under sign-flip null."""
    rng = random.Random(seed)
    observed = abs(sum(values) / len(values))
    count = 0
    for _ in range(samples):
        mean = sum((v if rng.random() < 0.5 else -v) for v in values) / len(values)
        if abs(mean) >= observed:
            count += 1
    return (count + 1) / (samples + 1)


def cohen_d_paired(values: List[float]) -> Optional[float]:
    if len(values) < 2:
        return None
    sd = statistics.stdev(values)
    if sd == 0:
        return None
    return statistics.mean(values) / sd


def summarize_metric(rows: List[dict], metric: str, rule_ticks: int, higher_is_better: bool = True):
    diffs = [metric_delta(r, metric, rule_ticks) for r in rows]
    mean_delta = statistics.mean(diffs)
    ci = bootstrap_ci(diffs)
    p = sign_flip_pvalue(diffs)
    d = cohen_d_paired(diffs)
    direction_ok = mean_delta > 0 if higher_is_better else mean_delta < 0
    return {
        "metric": metric,
        "n": len(diffs),
        "mean_delta_pretrained_minus_fresh": round(mean_delta, 6),
        "bootstrap_95ci": [round(ci[0], 6), round(ci[1], 6)],
        "sign_flip_p_two_sided": round(p, 6),
        "paired_cohens_d": None if d is None else round(d, 6),
        "direction_expected": "higher" if higher_is_better else "lower",
        "direction_matched": bool(direction_ok),
    }


def run(seeds: int = 200, pretrain_ticks: int = 20, rule_ticks: int = 12):
    rows = paired_trials(seeds=seeds, pretrain_ticks=pretrain_ticks, rule_ticks=rule_ticks)
    metrics = [
        ("total_reward", True),
        ("final_energy", True),
        ("invalid_actions", False),
        ("first_apply_tick", False),
        ("mean_prediction_error", False),
        ("transfer_prior_uses", True),
        ("transfer_prior_total_strength", True),
        ("transfer_prior_precision", True),
    ]
    summaries = {m: summarize_metric(rows, m, rule_ticks, higher_is_better=hib) for m, hib in metrics}

    # Raw group means for readability.
    group_means: Dict[str, Dict[str, float]] = {"fresh": {}, "pretrained": {}}
    for m, _hib in metrics:
        for group in ["fresh", "pretrained"]:
            vals = []
            for r in rows:
                obj = r[group]
                if m == "first_apply_tick":
                    vals.append(first_apply_value(obj.first_apply_tick, rule_ticks))
                else:
                    vals.append(float(getattr(obj, m)))
            group_means[group][m] = round(statistics.mean(vals), 6)

    result = {
        "experiment": "mixed_gridworld_to_ruleworld_200seed_replication",
        "seeds": seeds,
        "pretrain_ticks": pretrain_ticks,
        "rule_ticks": rule_ticks,
        "group_means": group_means,
        "paired_statistics": summaries,
        "interpretation": interpret(summaries),
        "rows": [
            {
                "seed": r["seed"],
                "fresh": r["fresh"].__dict__,
                "pretrained": r["pretrained"].__dict__,
            }
            for r in rows
        ],
    }
    return result


def interpret(summaries: Dict[str, dict]) -> str:
    reward = summaries["total_reward"]
    ci = reward["bootstrap_95ci"]
    p = reward["sign_flip_p_two_sided"]
    if ci[0] > 0 and p < 0.05:
        return "PASS: mixed GridWorld pretraining significantly improves early RuleWorld reward."
    if reward["mean_delta_pretrained_minus_fresh"] > 0:
        return "SUGGESTIVE: reward delta is positive, but CI/p-value do not establish significance."
    return "FAIL/INCONCLUSIVE: no positive early RuleWorld reward advantage."


if __name__ == "__main__":
    result = run()
    printable = {k: v for k, v in result.items() if k != "rows"}
    print(json.dumps(printable, indent=2))
    with open("statistical_replication_results.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print("saved → statistical_replication_results.json")

```


# FILE: swarm_v5.py

```python
"""
TAIS-LANG v5.5: Conversation · Query · Culture
=========================================

No LLM. No pretrained language model. No codebook sentence generation.

v5 expands the ecological speech world with a hard audit layer: speech is only
counted as communication when a listener interprets it, acts, and the outcome
is measured. The world still forces motes to talk about absent things:

  - Large structured world with food, water, shelter, poison, landmarks
  - Multi-need survival: energy, hydration, toxicity, predation
  - Mote place-memory: remembered resources/dangers away from current position
  - Referential utterances: concept + direction/near/far/landmark-ish tokens
  - Private lexicons inherited through reproduction and updated by outcomes
  - Human teaching: words are grounded into nearby motes' private lexicons
  - Headless evolution mode with save/load colonies

Core loop:
  world sensing → memory update → intent/reference selection → utterance/silence
  → listener interpretation/action → survival outcome → lexicon/trust update
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import threading
import time
from collections import Counter, deque
from dataclasses import asdict, dataclass
from typing import Deque, Dict, Iterable, List, Optional, Tuple

from flask import Flask, Response, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ─── VOCABULARY / CONCEPTS ───────────────────────────────────────────────────

TOKENS = [
    "ka", "mi", "tor", "lum", "sha", "nek", "vo", "pra", "tel", "du",
    "ra", "si", "fel", "nox", "wen", "bru", "ya", "ko", "dex", "ith",
    "zu", "mar", "ol", "tri", "ban", "esh", "ulo", "kir", "sam", "vai",
    "oro", "tin", "bez", "ari", "mun", "lef", "qor", "hal", "iva", "ruk",
]

CONCEPTS = [
    "FOOD", "WATER", "SHELTER", "POISON", "PREDATOR", "SAFE",
    "COME", "GO", "HELP", "TRUST",
    "NORTH", "SOUTH", "EAST", "WEST", "NEAR", "FAR", "HERE", "LANDMARK",
    "DYING", "STRONG", "UNKNOWN",
]
C_IDX = {c: i for i, c in enumerate(CONCEPTS)}
RESOURCE_CONCEPTS = {"FOOD", "WATER", "SHELTER", "POISON"}
DIRECTION_CONCEPTS = ["NORTH", "SOUTH", "EAST", "WEST"]

# Human teaching priors are not a language model. They are safety rails for the
# teacher UI so accidental bad grounding like `food → GO` can be warned/avoided.
HUMAN_WORD_PRIORS = {
    "food": "FOOD", "eat": "FOOD", "yum": "FOOD",
    "water": "WATER", "drink": "WATER", "wet": "WATER",
    "danger": "PREDATOR", "pred": "PREDATOR", "run": "PREDATOR",
    "home": "SHELTER", "nest": "SHELTER", "shelter": "SHELTER", "hide": "SHELTER", "cover": "SHELTER",
    "safe": "SAFE", "come": "COME", "go": "GO", "help": "HELP",
    "north": "NORTH", "south": "SOUTH", "east": "EAST", "west": "WEST",
}

# ─── CONFIG ──────────────────────────────────────────────────────────────────

CFG = {
    "world_size": 32.0,
    "population": 80,
    "max_population": 220,
    "predator_count": 6,
    "landmark_count": 28,
    "resource_count": 125,
    "ticks_per_sec": 4.0,
    "signal_range": 4.5,
    "player_range": 6.0,
    "memory_slots": 32,
    "initial_energy": 90.0,
    "initial_hydration": 90.0,
    "death_threshold": 0.0,
    "mitosis_thresh": 145.0,
    # Need dynamics
    "base_decay": 1.05,
    "hydration_decay": 0.78,
    "toxicity_decay": 0.94,
    "toxicity_energy_damage": 0.035,
    "dehydration_damage": 1.8,
    "food_gain": 5.8,
    "water_gain": 6.8,
    "shelter_decay_mult": 0.38,
    "poison_gain": 1.05,
    # Movement / predators
    "mote_step_min": 0.35,
    "mote_step_max": 1.0,
    "predator_speed": 0.72,
    "predator_contact": 0.88,
    "predator_damage": 16.0,
    "predator_broadcast_detect": 7.0,
    "predator_directed_detect": 2.4,
    "predator_wander": 1.25,
    # Speech economics
    "speak_cost": 3.7,
    "direct_cost": 1.8,
    "silence_bonus": 0.75,
    "min_speech_energy": 8.0,
    "lexicon_lr": 0.12,
    "self_ground_lr": 0.075,
    "teaching_boost": 0.55,
    "trust_decay": 0.96,
    "grammar_mutate": 0.055,
    "known_word_max": 10,
    # Learning/action
    "curiosity": 0.20,           # chance to test a high-value signal even if poorly understood
    "memory_merge_dist": 2.2,
    "memory_forget": 0.992,
}


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def dist(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def tokenise_text(text: str) -> List[str]:
    out: List[str] = []
    for raw in text.lower().replace(",", " ").replace(".", " ").replace("?", " ").split():
        tok = "".join(ch for ch in raw if ch.isalnum() or ch in "_-')")
        tok = tok.strip("'\"")[: CFG["known_word_max"]]
        if tok:
            out.append(tok)
    return out[:8]


def direction_from_to(x: float, y: float, tx: float, ty: float) -> str:
    dx, dy = tx - x, ty - y
    if abs(dx) >= abs(dy):
        return "EAST" if dx >= 0 else "WEST"
    return "NORTH" if dy >= 0 else "SOUTH"


def concept_for_resource(kind: str) -> str:
    return {"food": "FOOD", "water": "WATER", "shelter": "SHELTER", "poison": "POISON"}.get(kind, "UNKNOWN")


# ─── WORLD ───────────────────────────────────────────────────────────────────

@dataclass
class ResourceNode:
    id: int
    kind: str              # food | water | shelter | poison
    x: float
    y: float
    strength: float
    radius: float
    regen_phase: float = 0.0

    def value_at(self, x: float, y: float, tick: int = 0) -> float:
        d = math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)
        if d > self.radius * 3:
            return 0.0
        # Gentle dynamic world: resources breathe over time.
        breath = 0.86 + 0.14 * math.sin(0.015 * tick + self.regen_phase)
        return self.strength * breath * math.exp(-(d * d) / (2 * self.radius * self.radius))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "strength": round(self.strength, 2),
            "radius": round(self.radius, 2),
        }


@dataclass
class Landmark:
    id: int
    kind: str              # stone | cave | tree | tower | river | bone
    x: float
    y: float
    token: str

    def to_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind, "x": round(self.x, 2), "y": round(self.y, 2), "token": self.token}


class World:
    def __init__(self, size: float = CFG["world_size"], resource_count: int = CFG["resource_count"], landmark_count: int = CFG["landmark_count"]):
        self.size = float(size)
        self.resources: List[ResourceNode] = []
        self.landmarks: List[Landmark] = []
        self._build(resource_count, landmark_count)

    def _build(self, resource_count: int, landmark_count: int):
        # Landmarks first; they become reference anchors.
        landmark_kinds = ["stone", "cave", "tree", "tower", "river", "bone"]
        for i in range(landmark_count):
            kind = random.choice(landmark_kinds)
            self.landmarks.append(Landmark(
                id=i + 1,
                kind=kind,
                x=random.uniform(1.0, self.size - 1.0),
                y=random.uniform(1.0, self.size - 1.0),
                token=f"lm{i+1}",
            ))

        # Ecological clustering around landmarks + some scattered nodes.
        kinds = ["food", "water", "shelter", "poison"]
        weights = [0.37, 0.28, 0.20, 0.15]
        for i in range(resource_count):
            kind = random.choices(kinds, weights=weights)[0]
            if self.landmarks and random.random() < 0.70:
                lm = random.choice(self.landmarks)
                x = clamp(random.gauss(lm.x, self.size * 0.055), 0, self.size)
                y = clamp(random.gauss(lm.y, self.size * 0.055), 0, self.size)
            else:
                x = random.uniform(0, self.size)
                y = random.uniform(0, self.size)
            if kind == "food":
                strength, radius = random.uniform(5.5, 10.5), random.uniform(1.2, 2.8)
            elif kind == "water":
                strength, radius = random.uniform(6.5, 11.5), random.uniform(1.3, 3.2)
            elif kind == "shelter":
                strength, radius = random.uniform(4.5, 8.5), random.uniform(1.1, 2.5)
            else:
                strength, radius = random.uniform(5.0, 10.0), random.uniform(1.0, 2.7)
            self.resources.append(ResourceNode(i + 1, kind, x, y, strength, radius, random.random() * math.tau))

    def sense(self, x: float, y: float, tick: int) -> dict:
        vals = {"food": 0.0, "water": 0.0, "shelter": 0.0, "poison": 0.0}
        nearest_nodes: Dict[str, Optional[ResourceNode]] = {k: None for k in vals}
        best_node_val = {k: 0.0 for k in vals}
        for r in self.resources:
            v = r.value_at(x, y, tick)
            vals[r.kind] += v
            if v > best_node_val[r.kind]:
                best_node_val[r.kind] = v
                nearest_nodes[r.kind] = r

        nearest_landmark = None
        nearest_landmark_dist = 999.0
        for lm in self.landmarks:
            d = math.sqrt((x - lm.x) ** 2 + (y - lm.y) ** 2)
            if d < nearest_landmark_dist:
                nearest_landmark = lm
                nearest_landmark_dist = d

        return {
            **vals,
            "nearest_nodes": nearest_nodes,
            "nearest_landmark": nearest_landmark,
            "nearest_landmark_dist": nearest_landmark_dist,
        }

    def nearest_landmark_to(self, x: float, y: float) -> Tuple[Optional[Landmark], float]:
        best, best_d = None, 999.0
        for lm in self.landmarks:
            d = math.sqrt((x - lm.x) ** 2 + (y - lm.y) ** 2)
            if d < best_d:
                best, best_d = lm, d
        return best, best_d

    def to_dict(self) -> dict:
        return {
            "size": self.size,
            "resources": [r.to_dict() for r in self.resources],
            "landmarks": [lm.to_dict() for lm in self.landmarks],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "World":
        w = cls(size=data.get("size", CFG["world_size"]), resource_count=0, landmark_count=0)
        w.resources = [ResourceNode(**r) for r in data.get("resources", [])]
        w.landmarks = [Landmark(**lm) for lm in data.get("landmarks", [])]
        return w


# ─── SPEECH ──────────────────────────────────────────────────────────────────

class SpeechGenome:
    def __init__(self):
        self.order = random.choice([
            "concept-direction-distance",
            "direction-concept-distance",
            "risk-concept-direction",
            "landmark-concept-direction",
            "concept-landmark-distance",
        ])
        self.max_len = random.randint(1, 4)
        self.repeat_urgency = random.random() < 0.25
        self.silence_bias = random.uniform(0.25, 0.85)
        self.danger_silence = random.random() < 0.55
        self.direct_bias = random.uniform(0.35, 0.85)
        self.vocab_size = random.randint(8, len(TOKENS))

    def mutate(self) -> "SpeechGenome":
        g = SpeechGenome()
        if random.random() > CFG["grammar_mutate"]:
            g.order = self.order
        g.max_len = max(1, min(5, self.max_len + random.choice([-1, 0, 0, 1])))
        g.repeat_urgency = self.repeat_urgency if random.random() > CFG["grammar_mutate"] else not self.repeat_urgency
        g.silence_bias = clamp(self.silence_bias + random.gauss(0, 0.045), 0.05, 0.97)
        g.danger_silence = self.danger_silence if random.random() > CFG["grammar_mutate"] else not self.danger_silence
        g.direct_bias = clamp(self.direct_bias + random.gauss(0, 0.055), 0.0, 1.0)
        g.vocab_size = max(4, min(len(TOKENS), self.vocab_size + random.choice([-1, 0, 0, 1])))
        return g

    def to_dict(self) -> dict:
        return {
            "order": self.order,
            "max_len": self.max_len,
            "repeat_urgency": self.repeat_urgency,
            "silence_bias": round(self.silence_bias, 2),
            "danger_silence": self.danger_silence,
            "direct_bias": round(self.direct_bias, 2),
            "vocab_size": self.vocab_size,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SpeechGenome":
        g = cls()
        for k, v in d.items():
            setattr(g, k, v)
        return g


class Lexicon:
    def __init__(self):
        self.table: Dict[str, Dict[str, float]] = {
            tok: {c: random.uniform(-0.025, 0.025) for c in CONCEPTS} for tok in TOKENS
        }

    def ensure(self, tok: str):
        if tok not in self.table:
            self.table[tok] = {c: 0.0 for c in CONCEPTS}

    def update(self, tok: str, concept: str, amount: float):
        if concept not in C_IDX:
            return
        self.ensure(tok)
        self.table[tok][concept] = clamp(self.table[tok].get(concept, 0.0) + amount * CFG["lexicon_lr"], -1.0, 1.0)
        if amount > 0:
            for c in CONCEPTS:
                if c != concept:
                    self.table[tok][c] = clamp(self.table[tok][c] - amount * CFG["lexicon_lr"] * 0.01, -1.0, 1.0)

    def self_ground(self, tok: str, concept: str):
        if concept in C_IDX:
            self.ensure(tok)
            self.table[tok][concept] = clamp(self.table[tok][concept] + CFG["self_ground_lr"], -1.0, 1.0)

    def teach_ground(self, tok: str, concept: str, strength: float = 0.55, corrective: bool = True):
        """Ground a human-provided sound. Corrective teaching suppresses prior wrong meanings."""
        if concept not in C_IDX:
            return
        self.ensure(tok)
        self.table[tok][concept] = clamp(self.table[tok][concept] + strength, -1.0, 1.0)
        if corrective:
            for c in CONCEPTS:
                if c != concept:
                    self.table[tok][c] = clamp(self.table[tok][c] - strength * 0.35, -1.0, 1.0)

    def strongest_token_for(self, concept: str, vocab: Iterable[str], threshold: float = 0.055) -> Optional[str]:
        best_tok, best_w = None, threshold
        for tok in vocab:
            w = self.table.get(tok, {}).get(concept, 0.0)
            if w > best_w:
                best_tok, best_w = tok, w
        return best_tok

    def interpret(self, tokens: List[str]) -> Dict[str, float]:
        vec = {c: 0.0 for c in CONCEPTS}
        for tok in tokens:
            if tok in self.table:
                for c, w in self.table[tok].items():
                    vec[c] += w
        total = sum(abs(v) for v in vec.values()) or 1.0
        return {c: v / total for c, v in vec.items()}

    def to_dict(self, threshold: float = 0.16) -> dict:
        out = {}
        for tok, weights in sorted(self.table.items()):
            best = max(weights, key=weights.get)
            if weights[best] > threshold:
                out[tok] = {"concept": best, "weight": round(weights[best], 3)}
        return out

    def full_dict(self) -> dict:
        return self.table

    @classmethod
    def from_dict(cls, data: dict) -> "Lexicon":
        lx = cls()
        lx.table = {tok: {c: float(w) for c, w in weights.items()} for tok, weights in data.items()}
        for tok in TOKENS:
            lx.ensure(tok)
        return lx


@dataclass
class MemoryItem:
    concept: str
    x: float
    y: float
    value: float
    confidence: float
    tick: int
    landmark_id: Optional[int] = None
    source: str = "sense"  # sense | heard | player

    def to_dict(self) -> dict:
        return {
            "concept": self.concept,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "value": round(self.value, 2),
            "confidence": round(self.confidence, 2),
            "tick": self.tick,
            "landmark_id": self.landmark_id,
            "source": self.source,
        }


@dataclass
class Utterance:
    tokens: List[str]
    speaker_id: int
    target_id: Optional[int]
    intended_concept: str
    position: List[float]
    value: float
    energy: float
    hydration: float
    tick: int
    landmark_id: Optional[int] = None
    is_broadcast: bool = False
    is_player: bool = False
    is_teaching: bool = False

    @property
    def text(self) -> str:
        return " ".join(self.tokens)

    def to_dict(self) -> dict:
        return {
            "tokens": self.tokens,
            "text": self.text,
            "speaker_id": self.speaker_id,
            "target_id": self.target_id,
            "intended_concept": self.intended_concept,
            "position": [round(self.position[0], 2), round(self.position[1], 2)],
            "value": round(self.value, 2),
            "energy": round(self.energy, 1),
            "hydration": round(self.hydration, 1),
            "tick": self.tick,
            "landmark_id": self.landmark_id,
            "is_broadcast": self.is_broadcast,
            "is_player": self.is_player,
            "is_teaching": self.is_teaching,
        }


@dataclass
class SilenceDecision:
    tick: int
    mote_id: int
    reason: str
    energy: float
    hydration: float
    toxicity: float
    predator_distance: float
    neighbor_count: int
    info_value: float

    def to_dict(self) -> dict:
        d = asdict(self)
        for k in ["energy", "hydration", "toxicity", "predator_distance", "info_value"]:
            d[k] = round(d[k], 2)
        return d


@dataclass
class ComprehensionEvent:
    """
    v5 audit record: did a listener actually understand/use an utterance?
    This is the difference between speech emission and communication.
    """
    utterance_tick: int
    outcome_tick: int
    speaker_id: int
    listener_id: int
    tokens: List[str]
    text: str
    speaker_intent: str
    listener_interpretation: str
    interpretation_confidence: float
    action: str
    energy_before: float
    energy_after: float
    hydration_before: float
    hydration_after: float
    trust_before: float
    trust_after: float
    outcome: str
    success: bool          # useful action: did acting help or avoid harm?
    semantic_match: bool   # stricter: did listener interpretation/outcome match speaker intent?

    def to_dict(self) -> dict:
        d = asdict(self)
        for k in ["interpretation_confidence", "energy_before", "energy_after", "hydration_before", "hydration_after", "trust_before", "trust_after"]:
            d[k] = round(d[k], 3)
        d["delta_energy"] = round(self.energy_after - self.energy_before, 3)
        d["delta_hydration"] = round(self.hydration_after - self.hydration_before, 3)
        return d


# ─── PREDATOR ────────────────────────────────────────────────────────────────

class Predator:
    _id = 0

    def __init__(self, world_size: float):
        Predator._id += 1
        self.id = Predator._id
        self.x = random.uniform(0, world_size)
        self.y = random.uniform(0, world_size)
        self.target_x = self.x
        self.target_y = self.y
        self.signals_followed = 0
        self.damage_dealt = 0.0
        self.kills = 0

    def update(self, utterances: List[Utterance], motes: List["Mote"], world_size: float, tick: int):
        best_u, best_score = None, 0.7
        for u in utterances:
            if u.is_player or u.tick < tick - 2:
                continue
            d = math.sqrt((self.x - u.position[0]) ** 2 + (self.y - u.position[1]) ** 2)
            detect = CFG["predator_broadcast_detect"] if u.is_broadcast else CFG["predator_directed_detect"]
            if d > detect:
                continue
            # Content following: high value food/water signals attract predators.
            attractive = u.value / (1.0 + d)
            if u.intended_concept in ["FOOD", "WATER", "SHELTER"]:
                attractive *= 1.25
            if attractive > best_score:
                best_score, best_u = attractive, u
        if best_u:
            self.target_x, self.target_y = best_u.position
            self.signals_followed += 1

        dx, dy = self.target_x - self.x, self.target_y - self.y
        d = math.sqrt(dx * dx + dy * dy)
        if d > 0.15:
            self.x += (dx / d) * CFG["predator_speed"]
            self.y += (dy / d) * CFG["predator_speed"]
        else:
            self.target_x = clamp(self.x + random.gauss(0, CFG["predator_wander"]), 0, world_size)
            self.target_y = clamp(self.y + random.gauss(0, CFG["predator_wander"]), 0, world_size)

        self.x = clamp(self.x, 0, world_size)
        self.y = clamp(self.y, 0, world_size)

        for m in motes:
            if not m.is_alive():
                continue
            if self.dist_to(m.x, m.y) <= CFG["predator_contact"]:
                m.energy -= CFG["predator_damage"]
                self.damage_dealt += CFG["predator_damage"]
                if m.energy <= CFG["death_threshold"]:
                    m.alive = False
                    self.kills += 1

    def dist_to(self, x: float, y: float) -> float:
        return math.sqrt((self.x - x) ** 2 + (self.y - y) ** 2)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "target_x": round(self.target_x, 2),
            "target_y": round(self.target_y, 2),
            "signals_followed": self.signals_followed,
            "kills": self.kills,
            "damage": round(self.damage_dealt, 1),
        }

    @classmethod
    def from_dict(cls, d: dict, world_size: float) -> "Predator":
        p = cls(world_size)
        p.id = d.get("id", p.id)
        p.x = d.get("x", p.x)
        p.y = d.get("y", p.y)
        p.target_x = d.get("target_x", p.x)
        p.target_y = d.get("target_y", p.y)
        p.signals_followed = d.get("signals_followed", 0)
        p.kills = d.get("kills", 0)
        p.damage_dealt = d.get("damage", 0.0)
        return p


# ─── MOTE ────────────────────────────────────────────────────────────────────

class Mote:
    _id = 0

    def __init__(self, x: float, y: float, energy: float, hydration: float, parent_id: int = -1):
        Mote._id += 1
        self.id = Mote._id
        self.parent_id = parent_id
        self.x = x
        self.y = y
        self.energy = energy
        self.hydration = hydration
        self.toxicity = 0.0
        self.age = 0
        self.alive = True

        self.sensed = {"food": 0.0, "water": 0.0, "shelter": 0.0, "poison": 0.0}
        self.nearest_predator_dist = 999.0
        self.nearest_landmark_id: Optional[int] = None
        self.nearest_landmark_dist = 999.0
        self.last_gradient: Optional[str] = None

        self.genome = SpeechGenome()
        self.lexicon = Lexicon()
        self.memories: List[MemoryItem] = []
        self.inbox: Deque[Utterance] = deque(maxlen=14)
        self.trust: Dict[int, float] = {}
        self.known_peer_state: Dict[int, Tuple[float, float]] = {}  # energy, hydration
        self.last_acted: Optional[Utterance] = None
        self.energy_before_acting = 0.0
        self.hydration_before_acting = 0.0
        self.last_listener_interpretation = "UNKNOWN"
        self.last_interpretation_confidence = 0.0
        self.last_action = "none"
        self.last_trust_before = 0.5

        self.silence_reason: Optional[str] = None
        self.times_spoke = 0
        self.times_directed = 0
        self.times_broadcast = 0
        self.times_silent_choice = 0
        self.times_silent_fear = 0
        self.times_silent_alone = 0
        self.lexicon_updates = 0
        self.memory_updates = 0
        self.comprehension_trials = 0
        self.comprehension_success = 0
        self.semantic_matches = 0
        self.utterances: Deque[Utterance] = deque(maxlen=10)
        self.silences: Deque[SilenceDecision] = deque(maxlen=10)

    def is_alive(self) -> bool:
        return self.alive and self.energy > CFG["death_threshold"] and self.hydration > -25

    def vitality(self) -> float:
        return min(self.energy, self.hydration) - self.toxicity * 2.0

    # ── Sensing/memory ───────────────────────────────────────────────────────
    def sense_world(self, world: World, predators: List[Predator], tick: int):
        s = world.sense(self.x, self.y, tick)
        self.sensed = {k: s[k] for k in ["food", "water", "shelter", "poison"]}
        lm = s["nearest_landmark"]
        self.nearest_landmark_id = lm.id if lm else None
        self.nearest_landmark_dist = s["nearest_landmark_dist"]
        self.nearest_predator_dist = min((p.dist_to(self.x, self.y) for p in predators), default=999.0)

        # Ground memories from direct sensing.
        for kind in ["food", "water", "shelter", "poison"]:
            val = self.sensed[kind]
            if val > (1.4 if kind != "poison" else 0.8):
                node = s["nearest_nodes"].get(kind)
                if node:
                    lm2, ld = world.nearest_landmark_to(node.x, node.y)
                    self.update_memory(concept_for_resource(kind), node.x, node.y, val, 0.75, tick, lm2.id if lm2 and ld < 5.0 else None, "sense")

        if self.nearest_predator_dist < 4.0:
            self.update_memory("PREDATOR", self.x, self.y, max(1.0, 5.0 - self.nearest_predator_dist), 0.65, tick, self.nearest_landmark_id, "sense")

        # Decay memory confidence.
        for mem in self.memories:
            mem.confidence *= CFG["memory_forget"]
        self.memories = [m for m in self.memories if m.confidence > 0.05]

    def update_memory(self, concept: str, x: float, y: float, value: float, confidence: float, tick: int, landmark_id: Optional[int], source: str):
        if concept not in C_IDX:
            return
        for mem in self.memories:
            if mem.concept == concept and math.sqrt((mem.x - x) ** 2 + (mem.y - y) ** 2) <= CFG["memory_merge_dist"]:
                w_old = mem.confidence
                w_new = confidence
                total = w_old + w_new + 1e-6
                mem.x = (mem.x * w_old + x * w_new) / total
                mem.y = (mem.y * w_old + y * w_new) / total
                mem.value = max(mem.value * 0.9, value)
                mem.confidence = clamp(max(mem.confidence, confidence) + 0.08, 0.0, 1.0)
                mem.tick = tick
                mem.landmark_id = landmark_id or mem.landmark_id
                mem.source = source
                self.memory_updates += 1
                return
        self.memories.append(MemoryItem(concept, x, y, value, confidence, tick, landmark_id, source))
        self.memories.sort(key=lambda m: (m.confidence * m.value), reverse=True)
        self.memories = self.memories[: CFG["memory_slots"]]
        self.memory_updates += 1

    # ── Intent/reference selection ───────────────────────────────────────────
    def derive_current_intent(self) -> str:
        if self.nearest_predator_dist < 3.0:
            return "PREDATOR"
        if self.toxicity > 35 or self.sensed["poison"] > 2.2:
            return "POISON"
        if self.hydration < 30:
            return "WATER"
        if self.energy < 32:
            return "FOOD"
        if self.sensed["food"] > 5.0:
            return "FOOD"
        if self.sensed["water"] > 5.0:
            return "WATER"
        if self.sensed["shelter"] > 4.0:
            return "SHELTER"
        if self.vitality() > 105:
            return "STRONG"
        return "SAFE"

    def best_memory_for_need(self) -> Optional[MemoryItem]:
        wanted: List[str] = []
        if self.nearest_predator_dist < 4.5:
            wanted.append("SHELTER")
            wanted.append("PREDATOR")
        if self.hydration < 65:
            wanted.append("WATER")
        if self.energy < 70:
            wanted.append("FOOD")
        wanted.extend(["FOOD", "WATER", "SHELTER", "POISON", "PREDATOR"])

        best, best_score = None, -999.0
        for mem in self.memories:
            d = math.sqrt((self.x - mem.x) ** 2 + (self.y - mem.y) ** 2)
            priority = 1.4 if mem.concept in wanted[:3] else 1.0
            if mem.concept in ["POISON", "PREDATOR"]:
                # Dangers are useful to announce even if not personally needed.
                priority *= 1.1
            score = mem.value * mem.confidence * priority / (1.0 + d * 0.08)
            if score > best_score:
                best, best_score = mem, score
        return best

    def select_target_neighbor(self, neighbors: List["Mote"], concept: str) -> Optional["Mote"]:
        if not neighbors:
            return None
        if concept == "FOOD":
            return min(neighbors, key=lambda n: n.energy)
        if concept == "WATER":
            return min(neighbors, key=lambda n: n.hydration)
        if concept in ["PREDATOR", "POISON", "SHELTER"]:
            return min(neighbors, key=lambda n: n.nearest_predator_dist if concept == "SHELTER" else n.vitality())
        return min(neighbors, key=lambda n: n.vitality())

    def make_silence(self, tick: int, reason: str, neighbors: List["Mote"], info_value: float) -> SilenceDecision:
        if reason == "predator":
            self.times_silent_fear += 1
        elif reason == "alone":
            self.times_silent_alone += 1
        else:
            self.times_silent_choice += 1
        self.silence_reason = reason
        if reason in ["no_info", "low_value"]:
            self.energy += CFG["silence_bonus"]
        sd = SilenceDecision(tick, self.id, reason, self.energy, self.hydration, self.toxicity, self.nearest_predator_dist, len(neighbors), info_value)
        self.silences.append(sd)
        return sd

    def generate_utterance(self, neighbors: List["Mote"], world: World, tick: int) -> Tuple[Optional[Utterance], Optional[SilenceDecision]]:
        self.silence_reason = None
        if self.genome.danger_silence and self.nearest_predator_dist < 1.7:
            return None, self.make_silence(tick, "predator", neighbors, 0.0)
        if self.energy < CFG["min_speech_energy"]:
            return None, self.make_silence(tick, "energy", neighbors, 0.0)
        if not neighbors:
            return None, self.make_silence(tick, "alone", neighbors, 0.0)

        mem = self.best_memory_for_need()
        current_intent = self.derive_current_intent()
        if mem and mem.confidence * mem.value > 1.25:
            concept = mem.concept
            ref_x, ref_y = mem.x, mem.y
            value = mem.value * mem.confidence
            landmark_id = mem.landmark_id
        else:
            concept = current_intent
            ref_x, ref_y = self.x, self.y
            value = max(self.sensed.get("food", 0), self.sensed.get("water", 0), self.sensed.get("shelter", 0), self.sensed.get("poison", 0), 1.0)
            landmark_id = self.nearest_landmark_id

        # Information value: worth telling if high value, danger, or neighbor need.
        neediest = self.select_target_neighbor(neighbors, concept)
        neighbor_need = 0.0
        if neediest:
            if concept == "FOOD":
                neighbor_need = max(0, 80 - neediest.energy) / 40
            elif concept == "WATER":
                neighbor_need = max(0, 80 - neediest.hydration) / 40
            elif concept in ["PREDATOR", "POISON"]:
                neighbor_need = 1.0
            elif concept == "SHELTER":
                neighbor_need = max(0, 5.0 - neediest.nearest_predator_dist) / 5.0
        info_value = value + neighbor_need * 2.0
        if info_value < self.genome.silence_bias * 2.4:
            return None, self.make_silence(tick, "low_value", neighbors, info_value)

        tokens = self.compose_tokens(concept, ref_x, ref_y, landmark_id, world)
        if not tokens:
            return None, self.make_silence(tick, "no_tokens", neighbors, info_value)

        for tok in tokens:
            # Ground each token in the primary concept and some structural concepts.
            self.lexicon.self_ground(tok, concept)
            self.lexicon_updates += 1

        directed = bool(neediest and (random.random() < self.genome.direct_bias or self.nearest_predator_dist < 4.0))
        target_id = neediest.id if directed and neediest else None
        if directed:
            self.energy -= CFG["direct_cost"]
            self.times_directed += 1
        else:
            self.energy -= CFG["speak_cost"]
            self.times_broadcast += 1
        self.times_spoke += 1

        utt = Utterance(tokens, self.id, target_id, concept, [ref_x, ref_y], value, self.energy, self.hydration, tick, landmark_id, is_broadcast=not directed)
        self.utterances.append(utt)
        return utt, None

    def answer_query(self, concept: str, world: World, tick: int) -> Tuple[Optional[Utterance], Optional[SilenceDecision]]:
        """Answer the player from memory. This is v5.5's conversation mode."""
        if concept not in C_IDX:
            concept = "UNKNOWN"
        if self.genome.danger_silence and self.nearest_predator_dist < 1.7:
            return None, self.make_silence(tick, "query_predator", [], 0.0)
        if self.energy < CFG["min_speech_energy"]:
            return None, self.make_silence(tick, "query_energy", [], 0.0)

        candidates = [m for m in self.memories if m.concept == concept]
        if not candidates and concept == "SAFE":
            candidates = [m for m in self.memories if m.concept in ["SHELTER", "PREDATOR", "POISON"]]
        if not candidates:
            return None, self.make_silence(tick, "query_no_memory", [], 0.0)

        mem = max(candidates, key=lambda m: m.value * m.confidence / (1.0 + 0.03 * math.sqrt((self.x-m.x)**2 + (self.y-m.y)**2)))
        answer_concept = mem.concept if concept != "SAFE" else ("SHELTER" if mem.concept == "SHELTER" else "SAFE")
        tokens = self.compose_tokens(answer_concept, mem.x, mem.y, mem.landmark_id, world)
        for tok in tokens:
            self.lexicon.self_ground(tok, answer_concept)
            self.lexicon_updates += 1
        self.energy -= CFG["direct_cost"]
        self.times_spoke += 1
        self.times_directed += 1
        utt = Utterance(tokens, self.id, -1, answer_concept, [mem.x, mem.y], mem.value * mem.confidence, self.energy, self.hydration, tick, mem.landmark_id, is_broadcast=False)
        self.utterances.append(utt)
        return utt, None

    def token_for(self, concept: str, vocab: List[str]) -> str:
        return self.lexicon.strongest_token_for(concept, vocab) or random.choice(vocab)

    def compose_tokens(self, concept: str, ref_x: float, ref_y: float, landmark_id: Optional[int], world: World) -> List[str]:
        vocab = TOKENS[: self.genome.vocab_size]
        concept_tok = self.token_for(concept, vocab)
        direction = direction_from_to(self.x, self.y, ref_x, ref_y)
        direction_tok = self.token_for(direction, vocab)
        distance = math.sqrt((self.x - ref_x) ** 2 + (self.y - ref_y) ** 2)
        dist_concept = "FAR" if distance > world.size * 0.18 else "NEAR"
        distance_tok = self.token_for(dist_concept, vocab)
        risk_tok = self.token_for("PREDATOR", vocab) if self.nearest_predator_dist < 5.0 or concept in ["PREDATOR", "POISON"] else None
        landmark_tok = None
        if landmark_id is not None and random.random() < 0.50:
            # Landmark token can enter as an acoustic proper-name. It can become grounded by use.
            landmark_tok = f"lm{landmark_id}"
            self.lexicon.ensure(landmark_tok)
            self.lexicon.self_ground(landmark_tok, "LANDMARK")

        order = self.genome.order
        if order == "concept-direction-distance":
            parts = [concept_tok, direction_tok, distance_tok]
        elif order == "direction-concept-distance":
            parts = [direction_tok, concept_tok, distance_tok]
        elif order == "risk-concept-direction":
            parts = ([risk_tok] if risk_tok else []) + [concept_tok, direction_tok]
        elif order == "landmark-concept-direction":
            parts = ([landmark_tok] if landmark_tok else []) + [concept_tok, direction_tok]
        elif order == "concept-landmark-distance":
            parts = [concept_tok] + ([landmark_tok] if landmark_tok else []) + [distance_tok]
        else:
            parts = [concept_tok]
        parts = [p for p in parts if p]
        deduped: List[str] = []
        for p in parts:
            if not deduped or deduped[-1] != p:
                deduped.append(p)
        parts = deduped[: self.genome.max_len]
        if self.genome.repeat_urgency and (self.energy < 30 or self.hydration < 30) and parts:
            parts = [parts[0]] + parts[: self.genome.max_len - 1]
        return parts

    # ── Listening/action/learning ────────────────────────────────────────────
    def receive(self, utt: Utterance):
        self.inbox.append(utt)
        self.trust.setdefault(utt.speaker_id, 0.5)

    def act_on_inbox(self, world: World, tick: int):
        for utt in reversed(self.inbox):
            if utt.target_id is not None and utt.target_id != self.id and not utt.is_player:
                continue
            trust = self.trust.get(utt.speaker_id, 0.5)
            concepts = self.lexicon.interpret(utt.tokens)
            # Curiosity lets meaning bootstrap: high-value content can be tested even before the token is understood.
            top_concept = max(concepts, key=concepts.get)
            top_score = concepts[top_concept]
            inferred = top_concept if top_score > 0.18 else "UNKNOWN"
            curious = random.random() < CFG["curiosity"] and utt.value > 2.0 and trust > 0.25

            move_toward = inferred in ["FOOD", "WATER", "SHELTER", "COME", "LANDMARK"] or (utt.is_player and curious)
            move_away = inferred in ["PREDATOR", "POISON", "GO"]
            if not (move_toward or move_away or curious):
                continue

            self.energy_before_acting = self.energy
            self.hydration_before_acting = self.hydration
            self.last_acted = utt
            self.last_listener_interpretation = inferred
            self.last_interpretation_confidence = float(top_score)
            self.last_trust_before = trust
            self.last_action = "away" if move_away else "toward"
            self.comprehension_trials += 1

            dx, dy = utt.position[0] - self.x, utt.position[1] - self.y
            d = math.sqrt(dx * dx + dy * dy) or 0.001
            step = CFG["mote_step_max"] * (0.55 + 0.45 * trust)
            if move_away:
                self.x = clamp(self.x - (dx / d) * step, 0, world.size)
                self.y = clamp(self.y - (dy / d) * step, 0, world.size)
            else:
                self.x = clamp(self.x + (dx / d) * step, 0, world.size)
                self.y = clamp(self.y + (dy / d) * step, 0, world.size)
                # Hearing creates a provisional map entry; outcome later strengthens/weakens token meaning.
                if utt.intended_concept in C_IDX:
                    self.update_memory(utt.intended_concept, utt.position[0], utt.position[1], utt.value, 0.35 * trust, tick, utt.landmark_id, "heard")
            break

    def update_lexicon_from_outcome(self, tick: int) -> Optional[ComprehensionEvent]:
        if self.last_acted is None:
            return None
        utt = self.last_acted
        delta_e = self.energy - self.energy_before_acting
        delta_h = self.hydration - self.hydration_before_acting
        outcome: Optional[str] = None
        if delta_e > 1.0 and self.sensed["food"] > 1.0:
            outcome = "FOOD"
        elif delta_h > 1.0 and self.sensed["water"] > 1.0:
            outcome = "WATER"
        elif self.sensed["shelter"] > 2.0 and self.nearest_predator_dist < 5.0:
            outcome = "SHELTER"
        elif self.sensed["poison"] > 1.2 or self.toxicity > 35 or self.nearest_predator_dist < 1.8 or delta_e < -8:
            outcome = "PREDATOR" if self.nearest_predator_dist < 1.8 else "POISON"

        if outcome:
            for tok in utt.tokens:
                self.lexicon.update(tok, outcome, 1.0)
                self.lexicon_updates += 1
            trust_delta = 0.08 if outcome in ["FOOD", "WATER", "SHELTER"] else -0.07
            self.trust[utt.speaker_id] = clamp(self.trust.get(utt.speaker_id, 0.5) + trust_delta, 0.0, 1.0)
        else:
            outcome = "NEUTRAL"

        trust_after = self.trust.get(utt.speaker_id, 0.5)
        success = (
            outcome == utt.intended_concept
            or (outcome in ["FOOD", "WATER", "SHELTER"] and self.last_action == "toward" and (delta_e > 0 or delta_h > 0))
            or (outcome in ["PREDATOR", "POISON"] and self.last_action == "away")
        )
        semantic_match = (self.last_listener_interpretation == utt.intended_concept and outcome == utt.intended_concept)
        if success:
            self.comprehension_success += 1
        if semantic_match:
            self.semantic_matches += 1

        ev = ComprehensionEvent(
            utterance_tick=utt.tick,
            outcome_tick=tick,
            speaker_id=utt.speaker_id,
            listener_id=self.id,
            tokens=list(utt.tokens),
            text=utt.text,
            speaker_intent=utt.intended_concept,
            listener_interpretation=self.last_listener_interpretation,
            interpretation_confidence=self.last_interpretation_confidence,
            action=self.last_action,
            energy_before=self.energy_before_acting,
            energy_after=self.energy,
            hydration_before=self.hydration_before_acting,
            hydration_after=self.hydration,
            trust_before=self.last_trust_before,
            trust_after=trust_after,
            outcome=outcome,
            success=bool(success),
            semantic_match=bool(semantic_match),
        )
        self.last_acted = None
        return ev

    def teach(self, word: str, concept: str, corrective: bool = True):
        tok = word.lower()[: CFG["known_word_max"]]
        if not tok or concept not in C_IDX:
            return
        self.lexicon.teach_ground(tok, concept, strength=CFG["teaching_boost"], corrective=corrective)
        self.lexicon_updates += 1

    # ── Movement/survival/reproduction ───────────────────────────────────────
    def explore(self, world: World, predators: List[Predator]):
        # Flee predator first.
        self.nearest_predator_dist = min((p.dist_to(self.x, self.y) for p in predators), default=999.0)
        if self.nearest_predator_dist < 1.8 and predators:
            p = min(predators, key=lambda pr: pr.dist_to(self.x, self.y))
            dx, dy = self.x - p.x, self.y - p.y
            d = math.sqrt(dx * dx + dy * dy) or 0.001
            self.x = clamp(self.x + (dx / d) * 1.15, 0, world.size)
            self.y = clamp(self.y + (dy / d) * 1.15, 0, world.size)
            return

        # If thirsty/hungry and memory exists, bias exploration toward that memory.
        wanted = "WATER" if self.hydration < 45 else "FOOD" if self.energy < 55 else None
        target = None
        if wanted:
            candidates = [m for m in self.memories if m.concept == wanted]
            if candidates:
                target = max(candidates, key=lambda m: m.value * m.confidence)
        if target and random.random() < 0.65:
            dx, dy = target.x - self.x, target.y - self.y
            d = math.sqrt(dx * dx + dy * dy) or 0.001
            step = random.uniform(CFG["mote_step_min"], CFG["mote_step_max"])
            self.x = clamp(self.x + (dx / d) * step, 0, world.size)
            self.y = clamp(self.y + (dy / d) * step, 0, world.size)
            return

        old_score = self.sensed["food"] + self.sensed["water"] + self.sensed["shelter"] - self.sensed["poison"] * 1.2
        step = random.uniform(CFG["mote_step_min"], CFG["mote_step_max"])
        dirs = [(step, 0, "EAST"), (-step, 0, "WEST"), (0, step, "NORTH"), (0, -step, "SOUTH")]
        random.shuffle(dirs)
        dx, dy, lab = dirs[0]
        nx, ny = clamp(self.x + dx, 0, world.size), clamp(self.y + dy, 0, world.size)
        s = world.sense(nx, ny, 0)
        new_score = s["food"] + s["water"] + s["shelter"] - s["poison"] * 1.2
        if new_score >= old_score * 0.65 or random.random() < 0.25:
            self.x, self.y = nx, ny
            if new_score > old_score:
                self.last_gradient = lab

    def metabolize(self, world: World, tick: int):
        s = world.sense(self.x, self.y, tick)
        food, water, shelter, poison = s["food"], s["water"], s["shelter"], s["poison"]
        shelter_mult = CFG["shelter_decay_mult"] if shelter > 2.0 else 1.0
        self.energy += min(food * CFG["food_gain"], 9.5) - CFG["base_decay"] * shelter_mult
        self.hydration += min(water * CFG["water_gain"], 10.0) - CFG["hydration_decay"]
        self.toxicity = self.toxicity * CFG["toxicity_decay"] + poison * CFG["poison_gain"]
        self.energy -= self.toxicity * CFG["toxicity_energy_damage"]
        if self.hydration < 0:
            self.energy += self.hydration * 0.18 - CFG["dehydration_damage"]
        self.energy = min(self.energy, 190.0)
        self.hydration = min(self.hydration, 150.0)
        self.age += 1
        for sid in list(self.trust):
            self.trust[sid] *= CFG["trust_decay"]
        if self.energy <= CFG["death_threshold"] or self.hydration <= -25:
            self.alive = False

    def reproduce(self, world: World) -> "Mote":
        self.energy /= 2
        self.hydration /= 2
        child = Mote(clamp(self.x + random.gauss(0, 0.7), 0, world.size), clamp(self.y + random.gauss(0, 0.7), 0, world.size), self.energy, self.hydration, self.id)
        child.toxicity = self.toxicity * 0.2
        child.genome = self.genome.mutate()
        child.lexicon = Lexicon.from_dict(self.lexicon.full_dict())
        # Noisy cultural inheritance.
        for tok in child.lexicon.table:
            for concept in CONCEPTS:
                child.lexicon.table[tok][concept] = clamp(child.lexicon.table[tok][concept] + random.gauss(0, 0.018), -1, 1)
        # Some memories pass to child.
        for mem in random.sample(self.memories, k=min(len(self.memories), CFG["memory_slots"] // 3)):
            child.memories.append(MemoryItem(mem.concept, mem.x + random.gauss(0, 0.25), mem.y + random.gauss(0, 0.25), mem.value, mem.confidence * 0.8, mem.tick, mem.landmark_id, "inherited"))
        return child

    # ── Serialization/UI ─────────────────────────────────────────────────────
    def to_save(self) -> dict:
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "x": self.x,
            "y": self.y,
            "energy": self.energy,
            "hydration": self.hydration,
            "toxicity": self.toxicity,
            "age": self.age,
            "genome": self.genome.to_dict(),
            "lexicon": self.lexicon.full_dict(),
            "memories": [asdict(m) for m in self.memories],
            "stats": {
                "spoke": self.times_spoke,
                "directed": self.times_directed,
                "broadcast": self.times_broadcast,
                "silent_choice": self.times_silent_choice,
                "silent_fear": self.times_silent_fear,
                "lexicon_updates": self.lexicon_updates,
                "memory_updates": self.memory_updates,
                "comprehension_trials": self.comprehension_trials,
                "comprehension_success": self.comprehension_success,
                "semantic_matches": self.semantic_matches,
            },
        }

    @classmethod
    def from_save(cls, d: dict) -> "Mote":
        m = cls(d["x"], d["y"], d.get("energy", 80), d.get("hydration", 80), d.get("parent_id", -1))
        m.id = d.get("id", m.id)
        m.toxicity = d.get("toxicity", 0.0)
        m.age = d.get("age", 0)
        m.genome = SpeechGenome.from_dict(d.get("genome", {}))
        m.lexicon = Lexicon.from_dict(d.get("lexicon", {}))
        m.memories = [MemoryItem(**mem) for mem in d.get("memories", [])]
        st = d.get("stats", {})
        m.times_spoke = st.get("spoke", 0)
        m.times_directed = st.get("directed", 0)
        m.times_broadcast = st.get("broadcast", 0)
        m.times_silent_choice = st.get("silent_choice", 0)
        m.times_silent_fear = st.get("silent_fear", 0)
        m.lexicon_updates = st.get("lexicon_updates", 0)
        m.memory_updates = st.get("memory_updates", 0)
        m.comprehension_trials = st.get("comprehension_trials", 0)
        m.comprehension_success = st.get("comprehension_success", 0)
        m.semantic_matches = st.get("semantic_matches", 0)
        return m

    def to_dict(self) -> dict:
        top = self.lexicon.to_dict(threshold=0.18)
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "energy": round(self.energy, 1),
            "hydration": round(self.hydration, 1),
            "toxicity": round(self.toxicity, 1),
            "vitality": round(self.vitality(), 1),
            "age": self.age,
            "sensed": {k: round(v, 2) for k, v in self.sensed.items()},
            "pred_dist": round(self.nearest_predator_dist, 2),
            "landmark_id": self.nearest_landmark_id,
            "spoke": self.times_spoke,
            "directed": self.times_directed,
            "broadcast": self.times_broadcast,
            "silent_choice": self.times_silent_choice,
            "silent_fear": self.times_silent_fear,
            "silent_alone": self.times_silent_alone,
            "lexicon_updates": self.lexicon_updates,
            "memory_updates": self.memory_updates,
            "comprehension_trials": self.comprehension_trials,
            "comprehension_success": self.comprehension_success,
            "semantic_matches": self.semantic_matches,
            "utility_rate": round(self.comprehension_success / max(1, self.comprehension_trials), 3),
            "semantic_rate": round(self.semantic_matches / max(1, self.comprehension_trials), 3),
            "genome": self.genome.to_dict(),
            "top_lexicon": top,
            "memories": [m.to_dict() for m in self.memories[:8]],
            "recent_utterances": [u.text for u in list(self.utterances)[-4:]],
            "intent": self.derive_current_intent(),
            "silence_reason": self.silence_reason,
        }


# ─── SWARM ───────────────────────────────────────────────────────────────────

class Swarm:
    def __init__(self, world_size: float = CFG["world_size"], population: int = CFG["population"]):
        self.world = World(size=world_size, resource_count=CFG["resource_count"], landmark_count=CFG["landmark_count"])
        self.motes: List[Mote] = []
        self.predators: List[Predator] = []
        self.tick = 0
        self.running = False
        self.lock = threading.RLock()
        self.pending_player_actions: List[dict] = []
        self.events: Deque[dict] = deque(maxlen=800)
        self.silence_log: Deque[dict] = deque(maxlen=800)
        self.audit_log: Deque[dict] = deque(maxlen=1200)
        self.recent_utterances: Deque[dict] = deque(maxlen=200)
        self.player = {"x": world_size / 2, "y": world_size / 2, "fitness": 0.0}
        self._bins: Dict[Tuple[int, int], List[Mote]] = {}
        self._bin_size = CFG["signal_range"]

        Mote._id = 0
        Predator._id = 0
        for _ in range(population):
            self.motes.append(Mote(random.uniform(0, world_size), random.uniform(0, world_size), CFG["initial_energy"], CFG["initial_hydration"]))
        for _ in range(CFG["predator_count"]):
            self.predators.append(Predator(world_size))

    def rebuild_bins(self):
        """Spatial hash for local communication queries."""
        self._bins = {}
        bs = self._bin_size
        for m in self.motes:
            if not m.is_alive():
                continue
            key = (int(m.x // bs), int(m.y // bs))
            self._bins.setdefault(key, []).append(m)

    def nearby_motes(self, x: float, y: float, radius: float, exclude_id: Optional[int] = None) -> List[Tuple[Mote, float]]:
        bs = self._bin_size
        if not self._bins:
            self.rebuild_bins()
        bx, by = int(x // bs), int(y // bs)
        reach = int(math.ceil(radius / bs)) + 1
        out: List[Tuple[Mote, float]] = []
        r2 = radius * radius
        for ix in range(bx - reach, bx + reach + 1):
            for iy in range(by - reach, by + reach + 1):
                for m in self._bins.get((ix, iy), []):
                    if exclude_id is not None and m.id == exclude_id:
                        continue
                    dx, dy = m.x - x, m.y - y
                    d2 = dx * dx + dy * dy
                    if d2 <= r2:
                        out.append((m, math.sqrt(d2)))
        return out

    def neighbors_of(self, mote: Mote) -> List[Mote]:
        return [m for m, _d in self.nearby_motes(mote.x, mote.y, CFG["signal_range"], exclude_id=mote.id)]

    def motes_near_player(self) -> List[Tuple[Mote, float]]:
        px, py = self.player["x"], self.player["y"]
        return sorted(self.nearby_motes(px, py, CFG["player_range"]), key=lambda x: x[1])

    def event_for_utt(self, utt: Utterance, typ: str = "utterance") -> dict:
        return {"type": typ, **utt.to_dict(), "mote_id": utt.speaker_id, "silence": False, "silence_reason": None}

    def tick_step(self) -> List[dict]:
        self.tick += 1
        tick_utts: List[Utterance] = []
        new_events: List[dict] = []

        with self.lock:
            actions = list(self.pending_player_actions)
            self.pending_player_actions = []

        self.player["fitness"] = self.player_fitness()

        # Sense.
        for m in self.motes:
            if m.is_alive():
                m.sense_world(self.world, self.predators, self.tick)
        self.rebuild_bins()

        # Player actions.
        for action in actions:
            if action.get("type") == "query":
                concept = action.get("concept") or "UNKNOWN"
                tokens = action.get("tokens", ["?"])[:8]
                new_events.append({
                    "type": "query",
                    "mote_id": None,
                    "speaker_id": -1,
                    "tokens": tokens,
                    "text": " ".join(tokens),
                    "intended_concept": concept,
                    "tick": self.tick,
                    "x": round(self.player["x"], 2),
                    "y": round(self.player["y"], 2),
                })
                answer_count = 0
                silence_count = 0
                for m, _d in self.motes_near_player()[:24]:
                    utt, sd = m.answer_query(concept, self.world, self.tick)
                    if sd:
                        silence_count += 1
                        self.silence_log.append(sd.to_dict())
                    if utt:
                        answer_count += 1
                        tick_utts.append(utt)
                        new_events.append(self.event_for_utt(utt, "answer"))
                new_events.append({"type": "query_summary", "text": f"answers={answer_count} silence={silence_count}", "tokens": [], "concept": concept, "tick": self.tick})
                continue
            if action.get("type") != "speak":
                continue
            pos = action.get("position", [self.player["x"], self.player["y"]])
            concept = action.get("concept") or "UNKNOWN"
            utt = Utterance(
                tokens=action.get("tokens", ["?"])[:8],
                speaker_id=-1,
                target_id=None,
                intended_concept=concept,
                position=[clamp(float(pos[0]), 0, self.world.size), clamp(float(pos[1]), 0, self.world.size)],
                value=float(action.get("value", action.get("fitness", self.player["fitness"]))),
                energy=999,
                hydration=999,
                tick=self.tick,
                landmark_id=action.get("landmark_id"),
                is_broadcast=True,
                is_player=True,
                is_teaching=bool(action.get("teaching", False)),
            )
            tick_utts.append(utt)
            new_events.append(self.event_for_utt(utt, "player"))
            for m, _d in self.motes_near_player():
                m.receive(utt)
                if utt.is_teaching and concept in C_IDX:
                    for tok in utt.tokens:
                        m.teach(tok, concept)
                    m.update_memory(concept, utt.position[0], utt.position[1], utt.value, 0.55, self.tick, utt.landmark_id, "player")
                    new_events.append({
                        "type": "teaching",
                        "mote_id": m.id,
                        "tokens": utt.tokens,
                        "text": utt.text,
                        "concept": concept,
                        "x": round(m.x, 2),
                        "y": round(m.y, 2),
                        "tick": self.tick,
                    })

        # Mote utterances.
        for m in list(self.motes):
            if not m.is_alive():
                continue
            neighbors = self.neighbors_of(m)
            utt, sd = m.generate_utterance(neighbors, self.world, self.tick)
            if sd:
                self.silence_log.append(sd.to_dict())
            if utt:
                tick_utts.append(utt)
                for n in neighbors:
                    if utt.target_id is None or utt.target_id == n.id:
                        n.receive(utt)
                if self.near_player(utt.position[0], utt.position[1], CFG["player_range"] * 1.25) or self.near_player(m.x, m.y, CFG["player_range"] * 1.1):
                    new_events.append(self.event_for_utt(utt, "utterance"))
            elif m.silence_reason and self.near_player(m.x, m.y, CFG["player_range"]) and random.random() < 0.35:
                new_events.append({
                    "type": "silence",
                    "mote_id": m.id,
                    "tokens": [],
                    "text": "",
                    "intent": m.derive_current_intent(),
                    "x": round(m.x, 2),
                    "y": round(m.y, 2),
                    "energy": round(m.energy, 1),
                    "hydration": round(m.hydration, 1),
                    "tick": self.tick,
                    "silence": True,
                    "silence_reason": m.silence_reason,
                })

        # Predators follow signal content.
        for p in self.predators:
            p.update(tick_utts, self.motes, self.world.size, self.tick)

        # Motes act on speech, move, survive, learn.
        for m in self.motes:
            if m.is_alive():
                m.act_on_inbox(self.world, self.tick)
        for m in self.motes:
            if m.is_alive():
                m.explore(self.world, self.predators)
        for m in self.motes:
            if m.is_alive():
                m.sense_world(self.world, self.predators, self.tick)
                m.metabolize(self.world, self.tick)
                audit = m.update_lexicon_from_outcome(self.tick)
                if audit:
                    ad = audit.to_dict()
                    self.audit_log.append(ad)
                    # Surface the important understanding events near the player.
                    if audit.success or self.near_player(m.x, m.y, CFG["player_range"]) or random.random() < 0.08:
                        new_events.append({"type": "understanding", **ad})

        # Birth/death.
        next_motes: List[Mote] = []
        births_near_player = 0
        birth_samples: List[str] = []
        for m in self.motes:
            if not m.is_alive():
                if self.near_player(m.x, m.y, CFG["player_range"] * 1.2):
                    new_events.append({"type": "death", "mote_id": m.id, "text": "", "tokens": [], "x": round(m.x, 2), "y": round(m.y, 2), "tick": self.tick})
                continue
            if m.energy >= CFG["mitosis_thresh"] and m.hydration > 45 and len(next_motes) < CFG["max_population"]:
                child = m.reproduce(self.world)
                next_motes.append(child)
                if self.near_player(child.x, child.y, CFG["player_range"] * 1.2):
                    births_near_player += 1
                    if len(birth_samples) < 5:
                        birth_samples.append(random.choice(TOKENS[:5]))
                    # Only show rare individual births; otherwise summarize to avoid chat spam.
                    if random.random() < 0.025:
                        new_events.append({"type": "birth", "mote_id": child.id, "text": birth_samples[-1], "tokens": [birth_samples[-1]], "x": round(child.x, 2), "y": round(child.y, 2), "energy": round(child.energy, 1), "tick": self.tick})
            next_motes.append(m)
        if births_near_player:
            new_events.append({"type": "birth_summary", "mote_id": None, "text": f"{births_near_player} births nearby", "tokens": birth_samples, "count": births_near_player, "tick": self.tick})
        self.motes = next_motes[: CFG["max_population"]]

        with self.lock:
            self.recent_utterances.extend([u.to_dict() for u in tick_utts])
            self.events.extend(new_events)
        return new_events

    def near_player(self, x: float, y: float, radius: float) -> bool:
        return math.sqrt((x - self.player["x"]) ** 2 + (y - self.player["y"]) ** 2) <= radius

    def player_fitness(self) -> float:
        s = self.world.sense(self.player["x"], self.player["y"], self.tick)
        # generalized local richness score
        return round(s["food"] + s["water"] + s["shelter"] - s["poison"] * 1.2, 2)

    def add_player_speech(self, tokens: List[str], concept: Optional[str], value: float, x: float, y: float, teaching: bool = False):
        lm, ld = self.world.nearest_landmark_to(x, y)
        with self.lock:
            self.pending_player_actions.append({
                "type": "speak",
                "tokens": tokens,
                "concept": concept,
                "value": value,
                "position": [x, y],
                "teaching": teaching,
                "landmark_id": lm.id if lm and ld < 5.0 else None,
            })

    def add_player_query(self, tokens: List[str], concept: str):
        with self.lock:
            self.pending_player_actions.append({"type": "query", "tokens": tokens, "concept": concept})

    def stats(self) -> dict:
        alive = [m for m in self.motes if m.is_alive()]
        spoke = sum(m.times_spoke for m in alive)
        directed = sum(m.times_directed for m in alive)
        broadcast = sum(m.times_broadcast for m in alive)
        sil_choice = sum(m.times_silent_choice for m in alive)
        sil_fear = sum(m.times_silent_fear for m in alive)
        lex = sum(m.lexicon_updates for m in alive)
        mem = sum(m.memory_updates for m in alive)
        comp_trials = sum(m.comprehension_trials for m in alive)
        comp_success = sum(m.comprehension_success for m in alive)
        semantic_matches = sum(m.semantic_matches for m in alive)
        avg_energy = sum(m.energy for m in alive) / max(1, len(alive))
        avg_hyd = sum(m.hydration for m in alive) / max(1, len(alive))
        avg_tox = sum(m.toxicity for m in alive) / max(1, len(alive))
        common = Counter()
        for m in alive:
            for tok, obj in m.lexicon.to_dict(threshold=0.22).items():
                common[(tok, obj["concept"])] += 1
        return {
            "population": len(alive),
            "spoke": spoke,
            "directed": directed,
            "broadcast": broadcast,
            "directed_ratio": round(directed / max(1, spoke), 3),
            "choice_silence": sil_choice,
            "fear_silence": sil_fear,
            "lexicon_updates": lex,
            "memory_updates": mem,
            "comprehension_trials": comp_trials,
            "comprehension_success": comp_success,
            "semantic_matches": semantic_matches,
            "utility_rate": round(comp_success / max(1, comp_trials), 3),
            "semantic_rate": round(semantic_matches / max(1, comp_trials), 3),
            "avg_energy": round(avg_energy, 1),
            "avg_hydration": round(avg_hyd, 1),
            "avg_toxicity": round(avg_tox, 1),
            "predator_follows": sum(p.signals_followed for p in self.predators),
            "predator_kills": sum(p.kills for p in self.predators),
            "common_tokens": [{"token": k[0], "concept": k[1], "count": v} for k, v in common.most_common(16)],
        }

    def snapshot(self) -> dict:
        with self.lock:
            events = list(self.events)[-120:]
            recent = list(self.recent_utterances)[-120:]
            silence = list(self.silence_log)[-120:]
            audits = list(self.audit_log)[-120:]
        return {
            "version": "v5.5",
            "tick": self.tick,
            "world": self.world.to_dict(),
            "population": len([m for m in self.motes if m.is_alive()]),
            "motes": [m.to_dict() for m in self.motes if m.is_alive()],
            "predators": [p.to_dict() for p in self.predators],
            "player": dict(self.player),
            "events": events,
            "recent_utterances": recent,
            "silence": silence,
            "audits": audits,
            "tokens": TOKENS,
            "concepts": CONCEPTS,
            "stats": self.stats(),
        }

    def save(self, path: str):
        data = {
            "version": "v5.5",
            "tick": self.tick,
            "cfg": CFG,
            "world": self.world.to_dict(),
            "motes": [m.to_save() for m in self.motes if m.is_alive()],
            "predators": [p.to_dict() for p in self.predators],
            "player": self.player,
        }
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> "Swarm":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        world = World.from_dict(data["world"])
        sw = cls(world_size=world.size, population=0)
        sw.world = world
        sw.tick = data.get("tick", 0)
        sw.player = data.get("player", {"x": world.size / 2, "y": world.size / 2, "fitness": 0})
        sw.motes = [Mote.from_save(m) for m in data.get("motes", [])]
        Mote._id = max([m.id for m in sw.motes], default=0)
        sw.predators = [Predator.from_dict(p, world.size) for p in data.get("predators", [])]
        Predator._id = max([p.id for p in sw.predators], default=0)
        return sw


# ─── GLOBAL SERVER STATE ─────────────────────────────────────────────────────

swarm: Swarm = Swarm()
swarm_thread: Optional[threading.Thread] = None


def run_loop():
    swarm.running = True
    while swarm.running:
        try:
            swarm.tick_step()
        except Exception as exc:
            print(f"[swarm-v4 error] {exc}")
        time.sleep(1.0 / CFG["ticks_per_sec"])


def start_thread():
    global swarm_thread
    swarm_thread = threading.Thread(target=run_loop, daemon=True)
    swarm_thread.start()


# ─── FLASK ROUTES ────────────────────────────────────────────────────────────

@app.route("/stream")
def stream():
    def gen():
        last = -1
        while True:
            if swarm.tick != last:
                last = swarm.tick
                yield f"data: {json.dumps(swarm.snapshot())}\n\n"
            time.sleep(0.08)
    return Response(gen(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/state")
def state():
    return jsonify(swarm.snapshot())


@app.route("/health")
def health():
    return jsonify({"ok": True, "version": "v5.5", "tick": swarm.tick, "population": len([m for m in swarm.motes if m.is_alive()])})


@app.route("/concepts")
def concepts():
    return jsonify({"concepts": CONCEPTS, "tokens": TOKENS})


@app.route("/audit")
def audit():
    return jsonify({"audits": list(swarm.audit_log)[-300:], "stats": swarm.stats()})


@app.route("/player/move", methods=["POST"])
def player_move():
    d = request.json or {}
    with swarm.lock:
        swarm.player["x"] = clamp(float(d.get("x", swarm.player["x"])), 0, swarm.world.size)
        swarm.player["y"] = clamp(float(d.get("y", swarm.player["y"])), 0, swarm.world.size)
        swarm.player["fitness"] = swarm.player_fitness()
        p = dict(swarm.player)
    return jsonify({"ok": True, "player": p})


@app.route("/player/speak", methods=["POST"])
def player_speak():
    d = request.json or {}
    raw = d.get("text", "")
    tokens = tokenise_text(raw) if raw else [str(t).lower()[: CFG["known_word_max"]] for t in d.get("tokens", ["?"]) if str(t)]
    if not tokens:
        tokens = ["?"]
    with swarm.lock:
        x = clamp(float(d.get("x", swarm.player["x"])), 0, swarm.world.size)
        y = clamp(float(d.get("y", swarm.player["y"])), 0, swarm.world.size)
        value = float(d.get("value", d.get("fitness", swarm.player["fitness"])))
    concept = d.get("concept")
    teaching = bool(d.get("teaching", False))
    swarm.add_player_speech(tokens, concept, value, x, y, teaching)
    return jsonify({"ok": True, "tokens": tokens, "concept": concept, "teaching": teaching, "x": x, "y": y, "value": value})


@app.route("/player/teach", methods=["POST"])
def player_teach():
    d = request.json or {}
    word = (d.get("word") or d.get("text") or "").strip()
    concept = d.get("concept", "FOOD")
    if concept not in C_IDX:
        return jsonify({"error": "unknown concept", "valid": CONCEPTS}), 400
    tokens = tokenise_text(word)
    if not tokens:
        return jsonify({"error": "missing word"}), 400
    warnings = []
    for tok in tokens:
        prior = HUMAN_WORD_PRIORS.get(tok)
        if prior and prior != concept:
            warnings.append(f"'{tok}' is usually grounded as {prior}, not {concept}")
    with swarm.lock:
        x = clamp(float(d.get("x", swarm.player["x"])), 0, swarm.world.size)
        y = clamp(float(d.get("y", swarm.player["y"])), 0, swarm.world.size)
        value = float(d.get("value", swarm.player["fitness"]))
    swarm.add_player_speech(tokens, concept, value, x, y, teaching=True)
    return jsonify({"ok": True, "tokens": tokens, "concept": concept, "warnings": warnings})


@app.route("/player/query", methods=["POST"])
def player_query():
    d = request.json or {}
    concept = d.get("concept")
    text = d.get("text", "")
    tokens = tokenise_text(text) if text else []
    if not concept and tokens:
        concept = HUMAN_WORD_PRIORS.get(tokens[0], "UNKNOWN")
    concept = concept or "UNKNOWN"
    if concept not in C_IDX:
        return jsonify({"error": "unknown concept", "valid": CONCEPTS}), 400
    if not tokens:
        tokens = [concept.lower()]
    swarm.add_player_query(tokens, concept)
    return jsonify({"ok": True, "tokens": tokens, "concept": concept})


@app.route("/mote/<int:mote_id>/lexicon")
def mote_lexicon(mote_id: int):
    for m in swarm.motes:
        if m.id == mote_id and m.is_alive():
            return jsonify({
                "id": m.id,
                "lexicon": m.lexicon.to_dict(threshold=0.08),
                "genome": m.genome.to_dict(),
                "memories": [mem.to_dict() for mem in m.memories],
                "utterances": [u.to_dict() for u in m.utterances],
                "trust": {str(k): round(v, 2) for k, v in m.trust.items()},
            })
    return jsonify({"error": "not found"}), 404


@app.route("/save", methods=["POST"])
def save_route():
    d = request.json or {}
    path = d.get("path", f"colonies/v4_tick_{swarm.tick}.json")
    swarm.save(path)
    return jsonify({"ok": True, "path": path})


@app.route("/reset", methods=["POST"])
def reset_route():
    global swarm
    old = swarm
    old.running = False
    time.sleep(0.15)
    d = request.json or {}
    world_size = float(d.get("world_size", CFG["world_size"]))
    pop = int(d.get("population", CFG["population"]))
    swarm = Swarm(world_size=world_size, population=pop)
    start_thread()
    return jsonify({"ok": True, "version": "v5.5"})


# ─── CLI ─────────────────────────────────────────────────────────────────────

def run_headless(args: argparse.Namespace):
    global swarm
    if args.load:
        swarm = Swarm.load(args.load)
    else:
        swarm = Swarm(world_size=args.world, population=args.population)
    t0 = time.time()
    for i in range(1, args.ticks + 1):
        swarm.tick_step()
        if args.report and (i % args.report == 0 or i == 1):
            s = swarm.stats()
            print(
                f"tick={swarm.tick:>7} pop={s['population']:>4} "
                f"E={s['avg_energy']:>5.1f} H={s['avg_hydration']:>5.1f} Tox={s['avg_toxicity']:>4.1f} "
                f"spk={s['spoke']:>6} dir={s['directed_ratio']:.2f} "
                f"sem={s.get('semantic_rate',0):.2f} util={s.get('utility_rate',0):.2f} "
                f"sil={s['choice_silence']:>6}/{s['fear_silence']:<5} lex={s['lexicon_updates']:>7} mem={s['memory_updates']:>7}"
            )
        if not swarm.motes:
            print(f"EXTINCTION at tick {swarm.tick}")
            break
    dt = time.time() - t0
    print(f"done: {swarm.tick} ticks in {dt:.2f}s ({args.ticks / max(dt, 1e-6):.1f} ticks/s)")
    if args.save:
        swarm.save(args.save)
        print(f"saved → {args.save}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="TAIS-LANG v5.5 Conversation · Query · Culture")
    p.add_argument("--headless", action="store_true", help="run training without Flask server")
    p.add_argument("--ticks", type=int, default=10000, help="headless training ticks")
    p.add_argument("--world", type=float, default=CFG["world_size"], help="world size")
    p.add_argument("--population", type=int, default=CFG["population"], help="initial population")
    p.add_argument("--save", type=str, default=None, help="save colony JSON")
    p.add_argument("--load", type=str, default=None, help="load colony JSON")
    p.add_argument("--report", type=int, default=1000, help="headless report interval")
    p.add_argument("--port", type=int, default=5123, help="server port")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.headless:
        run_headless(args)
    else:
        if args.load:
            swarm = Swarm.load(args.load)
            print(f"Loaded colony {args.load} at tick {swarm.tick}")
        else:
            swarm = Swarm(world_size=args.world, population=args.population)
        start_thread()
        print("TAIS-LANG v5.5: Conversation · Query · Culture")
        print(f"http://localhost:{args.port}")
        print(f"World: {swarm.world.size}x{swarm.world.size} | Pop: {len(swarm.motes)} | Predators: {len(swarm.predators)}")
        print("Endpoints: /stream /state /player/speak /player/teach /mote/<id>/lexicon /save /reset")
        app.run(host="0.0.0.0", port=args.port, debug=False, threaded=True)

```


# FILE: src/main.jsx

```jsx
import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

```


# FILE: src/App.jsx

```jsx
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

const SERVER = "http://localhost:5123";
const W = 640;

const C = {
  bg: "#07070c",
  surface: "#111118",
  panel: "#0f0f17",
  border: "#242438",
  muted: "#3a3a55",
  text: "#d2d2ea",
  textDim: "#66668e",
  accent: "#4a9eff",
  accentDim: "#17345f",
  food: "#28d17c",
  water: "#3fa7ff",
  shelter: "#c084fc",
  poison: "#d8f542",
  predator: "#E24B4A",
  player: "#EF9F27",
  speech: "#8a7aff",
  directed: "#4a9eff",
  silence: "#50506d",
  teaching: "#35d399",
  birth: "#1D9E75",
  death: "#ff4a4a",
};

const resourceColor = { food: C.food, water: C.water, shelter: C.shelter, poison: C.poison };

function energyColor(e = 0) {
  if (e > 130) return "#4aff9e";
  if (e > 90) return "#4a9eff";
  if (e > 55) return "#9e7aff";
  if (e > 25) return "#ff9e4a";
  return "#ff4a4a";
}

function eventStyle(ev) {
  if (ev.type === "player") return { color: C.player, prefix: "▶" };
  if (ev.type === "query") return { color: C.player, prefix: "?" };
  if (ev.type === "query_summary") return { color: C.textDim, prefix: "·" };
  if (ev.type === "teaching") return { color: C.teaching, prefix: "◆" };
  if (ev.type === "understanding") return { color: ev.semantic_match ? C.teaching : ev.success ? C.accent : C.textDim, prefix: ev.semantic_match ? "✓" : ev.success ? "↯" : "?" };
  if (ev.type === "answer") return { color: C.teaching, prefix: "↩" };
  if (ev.type === "utterance") return { color: ev.target_id ? C.directed : C.speech, prefix: ev.target_id ? "→" : "◌" };
  if (ev.type === "silence") return { color: C.silence, prefix: "∅" };
  if (ev.type === "birth") return { color: C.birth, prefix: "◉" };
  if (ev.type === "birth_summary") return { color: C.birth, prefix: "◉" };
  if (ev.type === "death") return { color: C.death, prefix: "×" };
  if (ev.type === "system") return { color: C.textDim, prefix: "·" };
  return { color: C.text, prefix: "·" };
}

function Tiny({ children, color = C.textDim }) {
  return <span style={{ fontSize: 10, color }}>{children}</span>;
}

function Stat({ label, value, color }) {
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ fontSize: 16, fontWeight: 600, color: color || C.text, fontFamily: "monospace" }}>{value}</div>
      <div style={{ fontSize: 9, color: C.textDim, textTransform: "uppercase", letterSpacing: "0.08em" }}>{label}</div>
    </div>
  );
}

function MoteTooltip({ mote }) {
  const lexItems = Object.entries(mote.top_lexicon || {}).slice(0, 8);
  const memItems = (mote.memories || []).slice(0, 5);
  const dirRatio = mote.spoke ? Math.round((mote.directed / mote.spoke) * 100) : 0;
  return (
    <div style={{ position: "absolute", pointerEvents: "none", background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6, padding: "8px 10px", fontSize: 11, color: C.text, lineHeight: 1.6, zIndex: 100, whiteSpace: "nowrap", boxShadow: "0 4px 20px rgba(0,0,0,0.65)", minWidth: 260 }}>
      <div style={{ color: C.accent, fontWeight: 700, marginBottom: 3 }}>Mote #{mote.id}</div>
      <div>energy <span style={{ color: energyColor(mote.energy) }}>{mote.energy}</span> · water <span style={{ color: C.water }}>{mote.hydration}</span> · tox <span style={{ color: C.poison }}>{mote.toxicity}</span></div>
      <div>intent <span style={{ color: C.speech }}>{mote.intent}</span> · pred {mote.pred_dist}</div>
      <div>spoke {mote.spoke} · directed <span style={{ color: C.accent }}>{dirRatio}%</span> · silent {mote.silent_choice}/{mote.silent_fear}</div>
      <div>grammar <span style={{ color: C.textDim }}>{mote.genome?.order}</span> · max {mote.genome?.max_len}</div>
      <div>lex updates <span style={{ color: C.teaching }}>{mote.lexicon_updates}</span> · memories {mote.memory_updates}</div>
      {mote.recent_utterances?.length > 0 && <div>recent <span style={{ color: C.speech }}>{mote.recent_utterances.join(" · ")}</span></div>}
      {lexItems.length > 0 && <div style={{ marginTop: 5, borderTop: `1px solid ${C.border}`, paddingTop: 4 }}>{lexItems.map(([tok, obj]) => <div key={tok}><span style={{ color: C.teaching }}>{tok}</span> ≈ {obj.concept} <span style={{ color: C.textDim }}>{obj.weight}</span></div>)}</div>}
      {memItems.length > 0 && <div style={{ marginTop: 5, borderTop: `1px solid ${C.border}`, paddingTop: 4 }}>{memItems.map((m, i) => <div key={i}><span style={{ color: resourceConceptColor(m.concept) }}>{m.concept}</span> ({m.x},{m.y}) c={m.confidence}</div>)}</div>}
    </div>
  );
}

function resourceConceptColor(c) {
  if (c === "FOOD") return C.food;
  if (c === "WATER") return C.water;
  if (c === "SHELTER") return C.shelter;
  if (c === "POISON") return C.poison;
  if (c === "PREDATOR") return C.predator;
  return C.text;
}

function WorldCanvas({ state, playerPos, hoveredMote, setHoveredMote, onGridClick, mode }) {
  const canvasRef = useRef(null);
  const size = state?.world?.size || 32;
  const scale = W / size;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !state) return;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, W, W);
    ctx.fillStyle = C.bg;
    ctx.fillRect(0, 0, W, W);

    // Subtle grid.
    const major = Math.max(4, Math.round(size / 8));
    ctx.strokeStyle = C.border;
    ctx.lineWidth = 0.5;
    for (let g = 0; g <= size; g += major) {
      ctx.beginPath(); ctx.moveTo(g * scale, 0); ctx.lineTo(g * scale, W); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0, g * scale); ctx.lineTo(W, g * scale); ctx.stroke();
    }

    // Resources.
    state.world?.resources?.forEach((r) => {
      const x = r.x * scale, y = r.y * scale, rad = r.radius * scale * 2.2;
      const col = resourceColor[r.kind] || C.text;
      const alpha = r.kind === "poison" ? 0.12 : 0.095;
      const grad = ctx.createRadialGradient(x, y, 0, x, y, rad);
      grad.addColorStop(0, `${col}${Math.round(alpha * 255).toString(16).padStart(2, "0")}`);
      grad.addColorStop(0.65, `${col}18`);
      grad.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = grad;
      ctx.beginPath(); ctx.arc(x, y, rad, 0, Math.PI * 2); ctx.fill();
    });

    // Landmarks.
    state.world?.landmarks?.forEach((lm) => {
      const x = lm.x * scale, y = lm.y * scale;
      ctx.fillStyle = C.textDim;
      ctx.strokeStyle = C.border;
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.rect(x - 4, y - 4, 8, 8); ctx.fill(); ctx.stroke();
      ctx.fillStyle = C.textDim;
      ctx.font = "8px monospace";
      ctx.textAlign = "center";
      ctx.fillText(lm.token, x, y - 7);
    });

    // Recent utterance advertised positions.
    state.recent_utterances?.slice(-50).forEach((u) => {
      if (u.is_player) return;
      const x = u.position[0] * scale, y = u.position[1] * scale;
      ctx.strokeStyle = u.is_broadcast ? "rgba(138,122,255,0.16)" : "rgba(74,158,255,0.22)";
      ctx.lineWidth = u.is_broadcast ? 1.1 : 1.7;
      ctx.beginPath(); ctx.arc(x, y, u.is_broadcast ? 15 : 8, 0, Math.PI * 2); ctx.stroke();
    });

    // Predators.
    state.predators?.forEach((p) => {
      const x = p.x * scale, y = p.y * scale, tx = p.target_x * scale, ty = p.target_y * scale;
      ctx.strokeStyle = "rgba(226,75,74,0.18)";
      ctx.setLineDash([4, 4]); ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(tx, ty); ctx.stroke(); ctx.setLineDash([]);
      ctx.strokeStyle = "rgba(226,75,74,0.13)";
      ctx.beginPath(); ctx.arc(x, y, 2.2 * scale, 0, Math.PI * 2); ctx.stroke();
      ctx.fillStyle = C.predator;
      ctx.beginPath(); ctx.moveTo(x, y - 9); ctx.lineTo(x + 8, y + 6); ctx.lineTo(x - 8, y + 6); ctx.closePath(); ctx.fill();
    });

    // Motes.
    state.motes?.forEach((m) => {
      const x = m.x * scale, y = m.y * scale;
      const r = Math.max(2.2, Math.min(6.5, 3 + m.energy / 45));
      const col = energyColor(m.energy);
      if (hoveredMote?.id === m.id) {
        ctx.strokeStyle = col; ctx.setLineDash([3, 3]); ctx.beginPath(); ctx.arc(x, y, 4.5 * scale, 0, Math.PI * 2); ctx.stroke(); ctx.setLineDash([]);
      }
      if (m.intent === "PREDATOR" || m.silent_fear > 0) {
        ctx.strokeStyle = "rgba(226,75,74,0.24)"; ctx.beginPath(); ctx.arc(x, y, r + 6, 0, Math.PI * 2); ctx.stroke();
      }
      ctx.fillStyle = `${col}35`; ctx.beginPath(); ctx.arc(x, y, r + 2, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = col; ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
    });

    // Player.
    const px = playerPos.x * scale, py = playerPos.y * scale;
    ctx.strokeStyle = "rgba(239,159,39,0.25)"; ctx.setLineDash([4, 4]); ctx.beginPath(); ctx.arc(px, py, 6 * scale, 0, Math.PI * 2); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = C.player; ctx.strokeStyle = C.bg; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(px, py, 8, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.fillStyle = C.bg; ctx.font = "bold 8px monospace"; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(mode === "teach" ? "T" : mode === "speak" ? "S" : "Y", px, py); ctx.textBaseline = "alphabetic";
  }, [state, playerPos, hoveredMote, mode, scale, size]);

  const mouseMove = useCallback((e) => {
    if (!state?.motes) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * size;
    const y = ((e.clientY - rect.top) / rect.height) * size;
    let closest = null, best = 0.75;
    state.motes.forEach((m) => {
      const d = Math.sqrt((m.x - x) ** 2 + (m.y - y) ** 2);
      if (d < best) { best = d; closest = m; }
    });
    setHoveredMote(closest);
  }, [state, size, setHoveredMote]);

  const click = useCallback((e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * size;
    const y = ((e.clientY - rect.top) / rect.height) * size;
    onGridClick(x, y);
  }, [size, onGridClick]);

  return (
    <div style={{ position: "relative" }}>
      <canvas ref={canvasRef} width={W} height={W} onMouseMove={mouseMove} onMouseLeave={() => setHoveredMote(null)} onClick={click} style={{ display: "block", cursor: "crosshair", borderRadius: 4, border: `1px solid ${C.border}` }} />
      {hoveredMote && <div style={{ position: "absolute", left: Math.min((hoveredMote.x * scale) + 12, W - 275), top: Math.max((hoveredMote.y * scale) - 95, 0) }}><MoteTooltip mote={hoveredMote} /></div>}
    </div>
  );
}

function EventRow({ ev }) {
  const st = eventStyle(ev);
  const label = ev.type === "teaching" ? `taught ${ev.text || ev.tokens?.join(" ")} ≈ ${ev.concept}`
    : ev.type === "understanding" ? `${ev.listener_id} heard "${ev.text}" as ${ev.listener_interpretation} → ${ev.action}; outcome ${ev.outcome}`
    : ev.type === "silence" ? `[${ev.silence_reason || "silence"}]`
    : ev.text || ev.tokens?.join(" ") || "";
  const concept = ev.type === "understanding" ? ev.speaker_intent : (ev.intended_concept || ev.intent || ev.concept);
  return (
    <div style={{ padding: "6px 9px", borderBottom: `1px solid ${C.border}`, display: "flex", gap: 8, alignItems: "flex-start", opacity: ev.type === "silence" ? 0.55 : 1 }}>
      <span style={{ color: st.color, flexShrink: 0 }}>{st.prefix}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <span style={{ color: C.textDim, fontSize: 10, marginRight: 6 }}>#{ev.mote_id ?? ev.speaker_id ?? "you"}</span>
        <span style={{ color: st.color, fontSize: 12 }}>{label}</span>
        {concept && <span style={{ color: resourceConceptColor(concept), fontSize: 9, marginLeft: 8 }}>({concept})</span>}
        {ev.target_id && ev.target_id !== -1 && <span style={{ color: C.directed, fontSize: 9, marginLeft: 8 }}>→#{ev.target_id}</span>}
      </div>
      {ev.energy !== undefined && <span style={{ color: energyColor(ev.energy), fontSize: 9, marginTop: 2 }}>{ev.energy}</span>}
    </div>
  );
}

export default function App() {
  const [state, setState] = useState(null);
  const [connected, setConnected] = useState(false);
  const [playerPos, setPlayerPos] = useState({ x: 16, y: 16 });
  const [events, setEvents] = useState([]);
  const [hoveredMote, setHoveredMote] = useState(null);
  const [mode, setMode] = useState("move");
  const [text, setText] = useState("food");
  const [teachWord, setTeachWord] = useState("food");
  const [concept, setConcept] = useState("FOOD");
  const [value, setValue] = useState(8.0);
  const [showBio, setShowBio] = useState(false);
  const [showAudit, setShowAudit] = useState(true);
  const lastTick = useRef(-1);
  const endRef = useRef(null);

  useEffect(() => {
    const es = new EventSource(`${SERVER}/stream`);
    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        setState(data);
        if (data.player) setPlayerPos({ x: data.player.x, y: data.player.y });
        if (data.events && data.tick !== lastTick.current) {
          lastTick.current = data.tick;
          const newer = data.events.filter((ev) => ev.tick >= data.tick - 1);
          if (newer.length) setEvents((prev) => [...prev, ...newer].slice(-220));
        }
      } catch (err) { console.warn(err); }
    };
    return () => es.close();
  }, []);

  useEffect(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), [events]);

  const worldSize = state?.world?.size || 32;
  const concepts = state?.concepts || ["FOOD", "WATER", "SHELTER", "POISON", "PREDATOR", "SAFE"];
  const stats = state?.stats || {};

  const sendMove = useCallback(async (x, y) => {
    const cx = Math.max(0, Math.min(worldSize, x));
    const cy = Math.max(0, Math.min(worldSize, y));
    setPlayerPos({ x: cx, y: cy });
    await fetch(`${SERVER}/player/move`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ x: cx, y: cy }) });
    setEvents((prev) => [...prev, { type: "player", text: `moved (${cx.toFixed(1)}, ${cy.toFixed(1)})`, tick: state?.tick ?? 0 }]);
  }, [worldSize, state]);

  const sendSpeak = useCallback(async (x = playerPos.x, y = playerPos.y, teaching = false) => {
    await fetch(`${SERVER}/player/speak`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text, concept: teaching ? concept : undefined, teaching, value, x, y }) });
    setEvents((prev) => [...prev, { type: "player", text: `${text} [value=${value.toFixed(1)}]`, intended_concept: teaching ? concept : undefined, tick: state?.tick ?? 0 }]);
  }, [text, concept, value, playerPos, state]);

  const sendTeach = useCallback(async () => {
    const res = await fetch(`${SERVER}/player/teach`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ word: teachWord, concept, value }) });
    const data = await res.json();
    const warn = data.warnings?.length ? ` ⚠ ${data.warnings.join('; ')}` : "";
    setEvents((prev) => [...prev, { type: "teaching", text: `${teachWord}${warn}`, concept, tick: state?.tick ?? 0 }]);
  }, [teachWord, concept, value, state]);

  const sendQuery = useCallback(async (qConcept = concept, qText = "") => {
    const body = { concept: qConcept, text: qText || qConcept.toLowerCase() };
    await fetch(`${SERVER}/player/query`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    setEvents((prev) => [...prev, { type: "query", text: body.text, intended_concept: qConcept, tick: state?.tick ?? 0 }]);
  }, [concept, state]);

  const onGridClick = useCallback((x, y) => {
    if (mode === "move") sendMove(x, y);
    else if (mode === "speak") sendSpeak(x, y, false);
    else sendMove(x, y);
  }, [mode, sendMove, sendSpeak]);

  const reset = async () => {
    await fetch(`${SERVER}/reset`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) });
    setEvents([{ type: "system", text: "reset", tick: 0 }]);
  };

  const save = async () => {
    const res = await fetch(`${SERVER}/save`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) });
    const d = await res.json();
    setEvents((prev) => [...prev, { type: "system", text: `saved ${d.path}`, tick: state?.tick ?? 0 }]);
  };

  const knownWords = useMemo(() => stats.common_tokens || [], [stats]);
  const dirPct = Math.round((stats.directed_ratio || 0) * 100);
  const filteredEvents = useMemo(() => events.filter(ev => {
    if (!showBio && ["birth", "birth_summary", "death"].includes(ev.type)) return false;
    if (!showAudit && ev.type === "understanding") return false;
    return true;
  }), [events, showBio, showAudit]);

  return (
    <div style={{ background: C.bg, minHeight: "100vh", color: C.text, fontFamily: "monospace", display: "flex", flexDirection: "column" }}>
      <div style={{ background: C.surface, borderBottom: `1px solid ${C.border}`, padding: "10px 16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div><span style={{ color: C.accent, fontWeight: 700 }}>TAIS-LANG v5</span><span style={{ color: C.textDim, marginLeft: 8, fontSize: 11 }}>understanding audit · syntax · culture</span></div>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <span style={{ color: connected ? C.food : C.predator, fontSize: 10 }}>{connected ? "● LIVE" : "○ OFFLINE"}</span>
          <Tiny>tick {state?.tick ?? 0} · pop {state?.population ?? 0}</Tiny>
          <button onClick={save} style={buttonStyle(false)}>save</button>
          <button onClick={reset} style={buttonStyle(false)}>reset</button>
        </div>
      </div>

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <div style={{ width: W + 30, padding: 14, display: "flex", flexDirection: "column", gap: 10 }}>
          <WorldCanvas state={state} playerPos={playerPos} hoveredMote={hoveredMote} setHoveredMote={setHoveredMote} onGridClick={onGridClick} mode={mode} />

          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 6 }}>{["move", "speak", "teach"].map((m) => <button key={m} onClick={() => setMode(m)} style={buttonStyle(mode === m)}>{m}</button>)}</div>

          <div style={panelStyle}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 7 }}>
              <Tiny color={C.player}>speak sound/word</Tiny>
              <input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && sendSpeak()} style={inputStyle} />
              <button onClick={() => sendSpeak()} style={buttonStyle(false)}>send</button>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Tiny>advertised value</Tiny>
              <input type="range" min="0" max="15" step="0.5" value={value} onChange={(e) => setValue(parseFloat(e.target.value))} style={{ flex: 1 }} />
              <span style={{ color: C.food, width: 32 }}>{value.toFixed(1)}</span>
            </div>
          </div>

          <div style={panelStyle}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Tiny color={C.teaching}>teach</Tiny>
              <input value={teachWord} onChange={(e) => setTeachWord(e.target.value)} style={{ ...inputStyle, flex: 0.8 }} />
              <select value={concept} onChange={(e) => setConcept(e.target.value)} style={selectStyle}>{concepts.map((c) => <option key={c}>{c}</option>)}</select>
              <button onClick={sendTeach} style={buttonStyle(false)}>ground</button>
            </div>
            <div style={{ marginTop: 7, color: C.textDim, fontSize: 10 }}>Ground your word in nearby motes' lexicons and maps at your current position.</div>
          </div>

          <div style={panelStyle}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 7 }}>
              <Tiny color={C.player}>ask nearby</Tiny>
              <select value={concept} onChange={(e) => setConcept(e.target.value)} style={{ ...selectStyle, flex: 1 }}>{concepts.map((c) => <option key={c}>{c}</option>)}</select>
              <button onClick={() => sendQuery(concept)} style={buttonStyle(false)}>ask</button>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(5,1fr)", gap: 5 }}>
              {["FOOD","WATER","PREDATOR","SHELTER","SAFE"].map(c => <button key={c} onClick={() => sendQuery(c)} style={buttonStyle(false)}>{c.toLowerCase()}</button>)}
            </div>
          </div>

          <div style={{ ...panelStyle, display: "grid", gridTemplateColumns: "repeat(8, 1fr)", gap: 7 }}>
            <Stat label="direct" value={`${dirPct}%`} color={C.directed} />
            <Stat label="spoke" value={stats.spoke || 0} color={C.speech} />
            <Stat label="sem" value={`${Math.round((stats.semantic_rate || 0) * 100)}%`} color={C.teaching} />
            <Stat label="util" value={`${Math.round((stats.utility_rate || 0) * 100)}%`} color={C.accent} />
            <Stat label="silent" value={stats.choice_silence || 0} color={C.silence} />
            <Stat label="fear∅" value={stats.fear_silence || 0} color={C.predator} />
            <Stat label="lex" value={stats.lexicon_updates || 0} color={C.teaching} />
            <Stat label="mem" value={stats.memory_updates || 0} color={C.food} />
          </div>

          <div style={{ ...panelStyle, display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 6, fontSize: 10 }}>
            <span style={{ color: C.food }}>● food</span><span style={{ color: C.water }}>● water</span><span style={{ color: C.shelter }}>● shelter</span><span style={{ color: C.poison }}>● poison</span>
          </div>

          <div style={panelStyle}>
            <div style={{ color: C.textDim, fontSize: 10, marginBottom: 5 }}>common grounded tokens</div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {knownWords.length === 0 && <Tiny>none yet — teach or let culture evolve</Tiny>}
              {knownWords.map((w) => <span key={`${w.token}-${w.concept}`} style={{ color: resourceConceptColor(w.concept), border: `1px solid ${C.border}`, padding: "2px 5px", borderRadius: 3, fontSize: 10 }}>{w.token}≈{w.concept}×{w.count}</span>)}
            </div>
          </div>
        </div>

        <div style={{ flex: 1, display: "flex", flexDirection: "column", borderLeft: `1px solid ${C.border}`, overflow: "hidden" }}>
          <div style={{ background: C.surface, borderBottom: `1px solid ${C.border}`, padding: "8px 12px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <Tiny>conversation stream · answers, understanding, silence</Tiny>
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <label style={{ color: C.textDim, fontSize: 10 }}><input type="checkbox" checked={showAudit} onChange={e => setShowAudit(e.target.checked)} /> audit</label>
              <label style={{ color: C.textDim, fontSize: 10 }}><input type="checkbox" checked={showBio} onChange={e => setShowBio(e.target.checked)} /> births/deaths</label>
              <Tiny color={C.player}>you ({playerPos.x.toFixed(1)}, {playerPos.y.toFixed(1)}) · local value {state?.player?.fitness?.toFixed?.(2) ?? "–"}</Tiny>
            </div>
          </div>
          <div style={{ flex: 1, overflowY: "auto" }}>
            {filteredEvents.length === 0 && <div style={{ padding: 30, textAlign: "center", color: C.textDim }}>No visible events. Move, teach, ask, or change filters.</div>}
            {filteredEvents.map((ev, i) => <EventRow key={`${ev.tick}-${ev.type}-${ev.mote_id || ev.speaker_id}-${i}`} ev={ev} />)}
            <div ref={endRef} />
          </div>
          <div style={{ borderTop: `1px solid ${C.border}`, padding: "7px 10px", background: C.surface, display: "flex", gap: 14, fontSize: 9, color: C.textDim }}>
            <span>◌ broadcast</span><span>→ directed</span><span>✓ understood</span><span>↯ useful but semantically mixed</span><span>∅ silence</span><span>◆ teaching</span><span>red triangles follow advertised content</span>
          </div>
        </div>
      </div>

      {!connected && <div style={{ color: C.predator, background: "rgba(226,75,74,0.1)", borderTop: `1px solid ${C.predator}`, padding: 8, textAlign: "center", fontSize: 11 }}>not connected · run: python3 swarm_v4.py</div>}
    </div>
  );
}

const panelStyle = { background: C.surface, border: `1px solid ${C.border}`, borderRadius: 4, padding: "8px 10px" };
const inputStyle = { flex: 1, background: C.bg, border: `1px solid ${C.border}`, borderRadius: 4, padding: "6px 8px", color: C.text, fontFamily: "monospace", outline: "none", fontSize: 12 };
const selectStyle = { background: C.bg, border: `1px solid ${C.border}`, borderRadius: 4, padding: "6px 8px", color: C.text, fontFamily: "monospace", outline: "none", fontSize: 11, maxWidth: 130 };
function buttonStyle(active) { return { background: active ? C.accentDim : "transparent", border: `1px solid ${active ? C.accent : C.muted}`, color: active ? C.accent : C.textDim, padding: "5px 9px", borderRadius: 4, cursor: "pointer", fontFamily: "monospace", fontSize: 11 }; }

```
