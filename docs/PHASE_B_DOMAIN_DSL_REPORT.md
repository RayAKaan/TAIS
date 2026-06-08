# Phase B Domain DSL Report

## Summary

Implemented the TAIS Domain Specification Language with builtin-backed and
declarative loading modes. Domains can now be loaded from YAML/JSON specs
while preserving all existing behavior and tests.

## Files Added

- `tais_core/dsl/__init__.py` — DSL package exports
- `tais_core/dsl/parser.py` — YAML/JSON spec loader
- `tais_core/dsl/validator.py` — spec validation with `DomainSpecError`
- `tais_core/dsl/codegen.py` — `BuiltinDSLWorld` and `DeclarativeDSLWorld`
- `tais_core/dsl/specs/gridworld.yaml` — builtin-backed GridWorld spec
- `tais_core/dsl/specs/rules.yaml` — builtin-backed RuleWorld spec
- `tais_core/dsl/specs/logic.yaml` — builtin-backed LogicWorld spec
- `tais_core/dsl/specs/chemistry_lite.yaml` — declarative chemistry domain
- `tais_core/domains/registry.py` — `load_domain()` registry
- `tests/test_dsl.py` — 20 DSL tests
- `docs/domain-guide.md` — DSL documentation

## Files Modified

- `requirements.txt` — added `PyYAML>=6.0,<7.0`
- `pyproject.toml` — added `PyYAML>=6.0,<7.0` dependency
- `tais_core/domains/__init__.py` — added `load_domain` export
- `tais_core/__init__.py` — added `load_domain` to imports and `__all__`

## Design

### Builtin-backed specs

Existing domains are wrapped via YAML while preserving their original Python
implementation. The YAML spec points to the existing `WorldInterface` subclass
and graph factory via dotted Python paths. `BuiltinDSLWorld` delegates all
`observe`, `valid_actions`, `act`, `evaluate` calls to the wrapped instance.

### Declarative specs

Simple new graph domains can be created directly from YAML without writing a
Python domain class. `DeclarativeDSLWorld` builds a `RealityGraph` from the
spec's `graph` section, creates `Transformation` objects from the `actions`
list, and applies declarative `effects` (add entities, add relations, set
properties) on `act()`.

## Test Results

```
Ran 114 tests in 2.200s
OK
```

- **94 existing tests** (from Phase A and earlier) — all pass, no regressions
- **20 new DSL tests** — all pass
  - 4 parser tests (load YAML, load JSON, invalid suffix, nonexistent file)
  - 5 validator tests (valid backend, valid declarative, missing name,
    invalid op, nonexistent action role)
  - 4 builtin loader tests (gridworld step, rules step, logic step, by-path)
  - 4 declarative loader tests (chemistry load, valid actions, form_bond
    effect, unknown action)
  - 2 public API tests (callable, unknown name error)
  - 1 cross-domain smoke test (all 4 domains step)

## Manual Smoke Test

```
gridworld BuiltinDSLWorld verify_safety 2.0
rules BuiltinDSLWorld verify_rule 0.02
logic BuiltinDSLWorld check_consistency 0.02
chemistry_lite DeclarativeDSLWorld check_valence 0.5
```

All four domains load, produce valid initial graphs, and step successfully
with `UniversalMote`.

## Known Limitations

- Declarative actions are unconditional (no preconditions).
- Complex dynamics (e.g., LogicWorld's SAT-solving) still require
  builtin-backed specs.
- Formal graph type checking is not yet implemented.
- No conditional effects or branching.

## Phase B Checkpoint Status

- [x] DSL package exists
- [x] YAML/JSON parser exists
- [x] Validator exists
- [x] Builtin-backed loader exists
- [x] Declarative generic loader exists
- [x] GridWorld YAML spec exists
- [x] RuleWorld YAML spec exists
- [x] LogicWorld YAML spec exists
- [x] ChemistryLite YAML spec exists
- [x] `load_domain("gridworld")` works
- [x] `load_domain("rules")` works
- [x] `load_domain("logic")` works
- [x] `load_domain("chemistry_lite")` works
- [x] DSL tests pass
- [x] All existing tests pass
- [x] Domain guide exists
