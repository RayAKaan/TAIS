# Paper-Locked Result Artifacts

This directory contains curated artifacts used to support the foundational TAIS paper draft:

**Grounded Role-Transfer Learning Without Pretrained Representations**

These files are copies of existing reports/results from the repo. They are not new experiments.

## Why this exists

TAIS contains several result regimes:
- legacy transfer runners
- Phase A paper-readiness fixes
- Phase D experiment framework
- Phase F2 paper-defining experiments

These regimes are not always directly comparable. This directory freezes the artifacts used for the paper and records provenance.

## Directory structure

- `legacy/` — pre-framework transfer reports
- `phase_a/` — prediction calibration, engine policy, speech benchmark
- `phase_d/` — framework composition/curriculum/scaling/cognitive contribution
- `phase_f2/` — role-balanced curriculum, domain-count scaling, 1000-seed replication, repair convergence
- `audit_summary.json` — machine-readable audit
- `audit_summary.md` — human-readable audit table

## Policy

Do not edit files here manually. Regenerate by running:

```bash
PYTHONPATH=. python scripts/audit_paper_results.py \
  --output results/paper_locked/audit_summary.json \
  --markdown results/paper_locked/audit_summary.md
```

Then copy curated artifacts from their original locations.

## Comparability warning

Legacy runner results and Phase D/F2 framework results may differ because:
- experiment framework changed
- prediction calibration changed
- domain initialization changed
- metrics and graph factories may differ

The paper must not mix these numbers without provenance.
