# TAIS Codebase Manifest

This file mirrors the actual on-disk layout of the repository.
Updated for Phase 0/2/1 (stabilize + RuleWorld metric fix + ablation v2).

## Core universal substrate

- `tais_core/reality.py` — Entity, Relation, RealityGraph, Transformation, Constraint, Consequence, GraphDelta, AnalogyMapping, WorldInterface.
- `tais_core/memory.py` — EpisodicMemory, PatternMemory, SymbolicMemory, CulturalMemory, PredictionEngine, MoteMemory, ActionRole helpers.
- `tais_core/speech.py` — Lexicon, SpeechGenome, Utterance, RepairSignal, UnderstandingAudit, SpeechOrgan.
- `tais_core/mote.py` — UniversalMote and MetaGenes.

## Domains (`tais_core/domains/`)

- `gridworld.py` — GridGraphWorld (spatial survival).
- `sequences.py` — SequenceWorld (prediction).
- `rules.py` — RuleWorld (modus-ponens-style rule application). Phase 2 variants: `RuleWorldEasy`, `RuleWorldChain`, `RuleWorldDistractor`.

## Swarm system

- `swarm_v5.py` — V5.5 ecological swarm/server/UI backend with query mode, audit, action role transfer.

## Experiments (`experiments/`)

- `ablation_runner.py` — N-condition ablation against the strict `first_apply_implication_tick` metric.
- `cross_domain_transfer.py` — 50-seed/variable transfer experiment runner.
- `statistical_replication.py` — 200-seed paired replication of mixed GridWorld → RuleWorld.

## Tests (`tests/`)

- `test_tais_core.py` — core unit tests for reality/memory/speech.
- `test_base_validation.py` — universal-mote-runs-N-domains battery.
- `test_core.py` — quick smoke script (not a unittest case).

## Frontend

- `src/App.jsx`, `src/main.jsx`, `index.html`
- `package.json`, `package-lock.json`

## Reports / docs (`docs/`)

- `TAIS_UNIVERSAL_ROADMAP.md`
- `TAIS_FULL_DETAILED_ROADMAP.md`
- `TAIS_BASE_MODEL_CRITERIA.md`
- `TEST_REPORT.md`
- `CROSS_DOMAIN_TRANSFER_REPORT.md`
- `ANALOGY_ACTION_PRIOR_REPORT.md`
- `ACTION_ROLE_TRANSFER_REPORT.md`
- `ABLATION_V2_REPORT.md` (Phase 1 rerun on the fixed metric)
- `PHASE0_PHASE2_PHASE1_CHANGELOG.md`

## Generated artefacts (not committed)

- `colonies/*.json` — swarm save files. Regenerate with `swarm_v5.py --headless --save`.
- `results/*.{csv,json,txt}` — experiment outputs. Regenerate with the scripts above.
- `runs/<timestamp>_*/` — per-run output folders (Phase 0.2 convention).

## Reproducing the test suite

```bash
python3 -m pip install -r requirements.txt
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

Expected: 15 tests passing (16+ after Phase 2 adds RuleWorld target-fact tests).

## Reproducing the ablation (Phase 1 v2)

```bash
mkdir -p results
PYTHONPATH=. python3 experiments/ablation_runner.py \
    --seeds 200 --pretrain 20 --eval 12 \
    --output results/ablation_v2_eval12.txt

# Horizon sweep:
for E in 12 30 50; do
  PYTHONPATH=. python3 experiments/ablation_runner.py \
      --seeds 200 --pretrain 20 --eval $E \
      --output results/ablation_v2_eval${E}.txt
done
```
