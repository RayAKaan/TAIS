# TAIS Reproducibility Guide

This guide describes how to reproduce the research artifacts for:

**Grounded Role-Transfer Learning Without Pretrained Representations**

## Repository snapshot

- Release: `v0.2.0-grtl-paper`
- Release commit: the commit tagged `v0.2.0-grtl-paper`
- Python: 3.10–3.12 supported
- License: MIT

## Install

```bash
git clone https://github.com/RayAKaan/TAIS.git
cd TAIS
python -m pip install -r requirements.txt
python -m pip install -e .
```

## Run tests

```bash
make test
```

Expected test count: **305 passing** (1 flaky speech test deselected; 4 subtests).

## Result regimes

### Legacy transfer results (Phase 4–5)

These are the earliest experiments establishing basic grid-to-logic and grid-to-hazard transfer. Results are reported as legacy context in the paper.

- Runner: `experiments/logic_transfer_runner.py`, `experiments/hazard_transfer_runner.py`
- Artifacts: `results/paper_locked/legacy/`

### Phase A — Paper-readiness fixes

Prediction calibration, engine selection, speech token portability. Not central to Paper 1.

- Artifacts: `results/paper_locked/phase_a/`

### Phase D — Experiment framework

Systematic composition, curriculum, scaling-law, and cognitive-contribution experiments using the unified framework.

- Runners: `experiments/phase_d/composition.py`, `experiments/phase_d/curriculum.py`, `experiments/phase_d/scaling_law.py`, `experiments/phase_d/cognitive_contribution.py`
- Artifacts: `results/paper_locked/phase_d/`

### Phase F2 — Paper-defining experiments

Role-balanced curriculum, domain-count scaling, grid-to-logic 1000-seed replication, repair convergence.

- Runners: `experiments/phase_f2/*.py`
- Artifacts: `results/paper_locked/phase_f2/`

### Phase R2 — Role-ontology robustness

Tests whether hand-designed role semantics are necessary for transfer.

- Runner: `experiments/phase_r/role_ontology_robustness.py`
- Command: see below

### Phase R3 — Baseline comparison

TAIS vs RandomAgent, HeuristicAgent, TabularQAgent.

- Runner: `experiments/phase_r/baseline_comparison.py`
- Command: see below

### Phase R4 — Larger-domain variants

Transfer to logic_large, hazard_large, rules_chain_long.

- Runner: `experiments/phase_r/large_domain_transfer.py`
- Command: see below

### Phase R5 — Prediction gating

Sweep over gating hyperparameters.

- Runner: `experiments/phase_r/prediction_gating_sweep.py`
- Command: see below

### Phase R6 — Learned role compatibility

Learned vs hardcoded compatibility matrix.

- Runner: `experiments/phase_r/learned_role_compatibility.py`
- Command: see below

## Canonical paper artifacts

- Paper result audit: `results/paper_locked/audit_summary.md` and `results/paper_locked/audit_summary.json`
- Submission checklist: `docs/PAPER_SUBMISSION_CHECKLIST.md`
- Paper figures: `paper/figures/`
- Figure generation script: `scripts/generate_paper_figures.py`
- References: `paper/references.bib`

## Regenerate paper figures

```bash
PYTHONPATH=. python scripts/generate_paper_figures.py
```

All figures are generated from committed CSV/JSON result artifacts.

## Run core experiments

### 1000-seed Grid→Logic replication

```bash
PYTHONPATH=. python experiments/phase_f2/grid_logic_1000_replication.py \
  --seeds 1000 --pretrain 20 --eval 15 \
  --output results/phase_f2/grid_logic_1000_replication
```

### Domain-count scaling

```bash
PYTHONPATH=. python experiments/phase_f2/domain_count_scaling.py \
  --seeds 200 --pretrain 20 --eval 15 \
  --output results/phase_f2/domain_count_scaling
```

### Role ontology robustness

```bash
PYTHONPATH=. python experiments/phase_r/role_ontology_robustness.py \
  --seeds 200 --pretrain 20 --eval 15 \
  --output results/phase_r/role_ontology_robustness
```

### Baseline comparison

```bash
PYTHONPATH=. python experiments/phase_r/baseline_comparison.py \
  --seeds 200 --pretrain 20 --eval 15 \
  --output results/phase_r/baseline_comparison
```

### Larger domain transfer

```bash
PYTHONPATH=. python experiments/phase_r/large_domain_transfer.py \
  --seeds 100 --pretrain 20 --eval 30 \
  --output results/phase_r/large_domain_transfer
```

### Prediction gating

```bash
PYTHONPATH=. python experiments/phase_r/prediction_gating_sweep.py \
  --seeds 200 --pretrain 20 --eval 15 \
  --output results/phase_r/prediction_gating_sweep
```

### Learned role compatibility

```bash
PYTHONPATH=. python experiments/phase_r/learned_role_compatibility.py \
  --seeds 200 --pretrain 20 --eval 15 \
  --output results/phase_r/learned_role_compatibility
```

## Paper source policy

LaTeX source drafts are maintained locally and are not required for reproduction of the code artifacts. Tracked paper assets include generated figures, references, result artifacts, and the submission checklist. PDF compilation requires a local LaTeX installation.

## Important caveats

- Legacy and framework results are not directly comparable due to different evaluation protocols.
- Some results are negative or null (e.g., role-balanced curriculum, cognitive engines, hazard_large transfer). These must be reported as such.
- `paper/*.tex` is intentionally not tracked in the repository.
- All paper numbers should trace to `results/paper_locked/audit_summary.md` and the individual phase artifacts.
