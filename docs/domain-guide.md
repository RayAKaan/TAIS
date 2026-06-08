# TAIS Domain Specification Language

## What the DSL does

The DSL lets researchers define or wrap graph domains using YAML or JSON.
Instead of writing a Python class with `observe`, `valid_actions`, `act`, and
`evaluate` methods, you write a `.yaml` spec and `load_domain()` returns a
`WorldInterface`-compatible object.

## Two modes

### Builtin-backed mode

Use this for existing Python domains. The YAML spec points to existing
`WorldInterface` subclasses and graph factories, so behavior is preserved
identically.

```yaml
backend:
  world_class: tais_core.domains.gridworld.GridGraphWorld
  graph_factory: tais_core.domains.gridworld.make_grid_graph
  graph_factory_kwargs:
    threat_near_resource: true
```

Builtin-backed specs are the safe path for porting existing domains:
GridWorld, RuleWorld, LogicWorld, and HazardWorld can all be wrapped without
changing a single line of Python domain code.

### Declarative mode

Use this for simple new domains that can be expressed using entities,
relations, actions, consequences, and effects. No Python domain class needed.

## Minimal declarative example

```yaml
name: ChemistryLite
domain_name: chemistry_lite
version: 1.0

entities:
  ATOM:
    attributes: [element, valence, charge]
  MOLECULE:
    attributes: [formula, stability]

relations:
  BONDED_TO:
    src: ATOM
    tgt: ATOM
    symmetric: true
  PART_OF:
    src: ATOM
    tgt: MOLECULE

action_roles:
  APPROACH_GOOD: form_bond
  AVOID_BAD: break_unstable

graph:
  id: chemistry_lite_initial
  entities:
    - id: atom_c
      type: ATOM
      properties:
        element: C
        valence: 4
        charge: 0
    - id: atom_o
      type: ATOM
      properties:
        element: O
        valence: 2
        charge: 0

actions:
  - name: form_bond
    universal_op: TRANSFORM
    base_cost: 0.4
    role_hint: APPROACH_GOOD
    reward: 4.0
    task_signal: TASK_SUCCESS
    concept_signals:
      GOOD: 1.0
    effects:
      add_entities:
        - id: stable_molecule
          type: MOLECULE
          properties:
            formula: CO
            stability: stable

evaluation:
  success_entity: stable_molecule
  success_score: 10.0
  default_score: 0.0
```

## Loading a domain

```python
from tais_core import load_domain
from tais_core import UniversalMote

# By builtin name
world = load_domain("gridworld")
graph = world.initial_graph()

# Or by file path
world = load_domain("path/to/my_domain.yaml")

# Use with UniversalMote
mote = UniversalMote()
graph, cons, action = mote.step(world, graph, mote_position="atom_c", tick=0)
```

## Domain spec schema

| Field | Required | Type | Description |
|---|---|---|---|
| `name` | yes | str | Human-readable name |
| `version` | yes | str | Semver version string |
| `domain_name` | no | str | Internal domain name (default: `name` lowercase) |
| `description` | no | str | Free-text description |
| `backend` | one-of | dict | Points to existing Python classes |
| `entities` | one-of | dict | Entity type definitions |
| `relations` | one-of | dict | Relation type definitions |
| `actions` | one-of | list | Action definitions |
| `graph` | one-of | dict | Initial graph state |
| `action_roles` | no | dict | Maps role names to action names |
| `world_defaults` | no | dict | Default energy, horizon, step cost |
| `evaluation` | no | dict | Evaluation criteria |

### Backend fields

| Field | Required | Type | Description |
|---|---|---|---|
| `world_class` | yes | str | Dotted Python class path |
| `graph_factory` | yes | str | Dotted Python factory function path |
| `graph_factory_kwargs` | no | dict | Keyword arguments for factory |

### Action fields

| Field | Required | Type | Description |
|---|---|---|---|
| `name` | yes | str | Action name |
| `universal_op` | yes | str | Must be in `Transformation.VALID_OPS` |
| `base_cost` | no | float | Default 1.0 |
| `role_hint` | no | str | Role name matching `action_roles` |
| `reward` | no | float | Reward when action succeeds |
| `penalty` | no | float | Penalty when action fails |
| `valid` | no | bool | Whether action is valid |
| `task_signal` | no | str | `TASK_SUCCESS`, `TASK_PROGRESS`, etc. |
| `concept_signals` | no | dict | Concept → strength mapping |
| `effects` | no | dict | Graph modifications (see below) |

### Effect fields

| Field | Type | Description |
|---|---|---|
| `add_entities` | list | Entities to add to the graph |
| `add_relations` | list | Relations to add to the graph |
| `set_properties` | list | Entity properties to update |

## Built-in domain names

| Name | Type | Description |
|---|---|---|
| `gridworld` / `grid` | Builtin-backed | GridGraphWorld with hazards and resources |
| `rules` / `ruleworld` | Builtin-backed | RuleWorld with implications |
| `logic` / `logicworld` | Builtin-backed | LogicWorld (SAT) |
| `chemistry_lite` | Declarative | Toy chemistry domain |

## Current limitations

- Declarative DSL supports simple unconditional actions only.
- Complex domains like LogicWorld should be builtin-backed for now.
- Conditional effects and formal graph type constraints are Phase C/D work.
