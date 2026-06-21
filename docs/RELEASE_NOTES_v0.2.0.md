# TAIS v0.2.0 — GRTL Paper Research Release

This release freezes the code, experiments, and curated artifacts for the foundational TAIS paper draft:

**Grounded Role-Transfer Learning Without Pretrained Representations**

**Status:** Research release / paper draft artifacts. Not peer-reviewed.

## Highlights

- Domain-agnostic `UniversalMote`
- Typed `RealityGraph`
- `PatternMemory` + `ActionRole` transfer
- Domain DSL via YAML/JSON
- Unified experiment framework
- Visualization toolkit (heatmaps, radar charts, scaling plots, trajectory viewer)
- Paper-strengthening experiments R1–R7
- Baseline agents (Random, Heuristic, TabularQ)
- Larger synthetic domain variants
- Prediction gating sweep
- Learned role compatibility prototype
- Paper figures and submission checklist

## Key scientific status

TAIS supports the following careful claim:

> Consequence-grounded functional role transfer can produce measurable early-transfer effects across typed graph domains, and those effects depend mechanistically on `PatternMemory` and `ActionRole` classification.

## Important limitations

- Role ontology is still partly hand-designed.
- Learned compatibility is prototype-level.
- Domains are synthetic graph environments.
- Completion-rate improvements are weaker than speed effects.
- Speech portability is currently a null result.
- Cognitive engines are not central to Paper 1.

## Reproducibility

See:

- `REPRODUCIBILITY.md`
- `docs/PAPER_RESULT_AUDIT.md`
- `results/paper_locked/`
- `docs/PAPER_SUBMISSION_CHECKLIST.md`

## Tests

305 passing, 1 deselected (flaky speech test), 4 subtests.
