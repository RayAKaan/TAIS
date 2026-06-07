# Phase 0 + Phase 2 + Phase 1 — Changelog

Branch: `phase0-2-1-stabilize-metric-ablation`
Three commits, in order:

1. `Phase 0: stabilize repo`
2. `Phase 2: harden RuleWorld evaluation (fix metric leak)`
3. `Phase 1: rerun ablations on the strict metric (v2 ablation suite)`

---

## What changed

### Phase 0 — Stabilize

- **Fixed broken import** in `experiments/statistical_replication.py` (was importing the old flat layout `experiments_cross_domain_transfer`; the README's headline replication command was crashing).
- **Added `experiments/__init__.py`** so the directory is a real package.
- **Added MIT `LICENSE`** (the repo had no license).
- **Added `.github/workflows/tests.yml`** — runs the unit suite on Python 3.10/3.11/3.12, import-checks experiments, and runs a 5-seed smoke ablation, on every push/PR.
- **Added `pyproject.toml`** so `pip install -e .` works and packaging metadata is in one place.
- **Pinned frontend deps** (`package.json`: was `"latest"` for vite/react/react-dom/@vitejs/plugin-react; now stable ranges).
- **Upper-bounded backend deps** (`requirements.txt`).
- **`.gitignore`d generated artefacts** (`colonies/*.json`, `results/*.{csv,json,txt}`, `runs/`). Dropped ~31 MB of tracked, regenerable JSON.
- **Removed `archive/CODE_DUMP.md`** (5,516 lines of dead text; preserved in git history) and `archive/tais_lang_v2_results.json` (460 KB).
- **Synced `docs/CODEBASE_MANIFEST.md`** with the actual experiments/ layout.

### Phase 2 — Fix RuleWorld metric leak

- **Added `Consequence.task_signal: Optional[str]`** (in `tais_core/reality.py`) — a domain-agnostic `TASK_SUCCESS | TASK_PROGRESS | TASK_FAILURE | None` tag so runners can compute `first_apply_implication_tick` without per-domain action-name special-casing.
- **Rewrote `tais_core/domains/rules.py`**:
  - Added explicit `TARGET` entity to the graph; `evaluate()` reads its `derive_id`.
  - Sharpened rewards:
    - `apply_implication` first solve: **+4.0** (unchanged)
    - `apply_implication` repeat: **+0.05** (was 4.0 every time — exploit loop)
    - `apply_implication` chain step: **+0.20**
    - `verify_rule`: **+0.02** (was **+1.5** — the metric leak)
    - `verify_rule` (no rule found): **−1.0** (was −2.0)
    - `random_assert`: **−3.0** (unchanged)
  - `act()` emits `task_signal` on every return.
  - `_try_derive()` generalised so chained worlds work.
  - New variants exported: `RuleWorldEasy`, `RuleWorldChain` (A→B→C), `RuleWorldDistractor` (1 satisfied + 4 noise rules).
- **Added `tests/test_ruleworld_v2.py`** — 9 tests pinning the new contract. The critical one:
  ```
  test_verify_reward_cannot_mimic_solution
      assert 100 verify actions sum to less reward than one true solve
  ```
  This is the regression guard. In v1, 3 verifies already exceeded one solve.

### Phase 1 — Rerun ablations on the strict metric

- **`experiments/ablation_runner.py`**:
  - Headline metric is now `first_apply_implication_tick` (uses `task_signal == "TASK_SUCCESS"`); legacy "any positive consequence" metric retained as `first_positive_tick_legacy` for sanity comparison only.
  - Added `task_completion_rate` (1.0 if `TASK_SUCCESS` ever fired, else 0.0).
  - Added `--horizons 12,30,50` CLI flag for the full ablation × horizon sweep.
  - Per-horizon output files (`results/ablation_v2_eval{N}.{txt,csv,json}`).
- **Ran 200 seeds × 8 conditions × 3 horizons** (~55 s total on one CPU).
- **Wrote `docs/ABLATION_V2_REPORT.md`** — full statistical analysis (read this).

---

## Test status

| | Before | After |
|---|---|---|
| Unit tests | 15 | **24** (9 new from Phase 2) |
| Run time | 0.03 s | 0.04 s |
| CI | none | GitHub Actions on 3.10/3.11/3.12 |
| `import experiments.statistical_replication` | **crash** | works |
| `experiments/ablation_runner.py --seeds 200` | works (leaky metric) | works (strict metric) |

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
# Ran 24 tests in 0.036s — OK
```

---

## The science delta

The v1 ablation table showed `no_pattern_transfer` *identical* to `full`, which read as "pattern transfer doesn't matter." That was an artefact of `verify_rule` paying +1.5 reward — motes could accumulate the headline metric without ever solving the task.

Under the strict v2 metric:

| Condition | First-apply tick (h=12) | p |
|---|---:|---:|
| fresh | 7.74 | — |
| `full` | **6.63** | **0.020** |
| `no_pattern_transfer` | 7.34 | 0.39 (ns) |
| `no_action_role` | 7.34 | 0.39 (ns) |
| `ruleworld_pretrain` (ceiling) | 5.27 | <0.001 |
| `empty_pretrain` (control) | 8.37 | 0.13 |
| `random_pretrain` (control) | 6.97 | 0.087 |

**The transfer effect is real, modest (d=−0.16), and dies when pattern-transfer or action-role classification is ablated.** The empty/random controls don't reproduce it. That's the load-bearing signal the v1 metric was hiding.

See `docs/ABLATION_V2_REPORT.md` for the full table, horizon sweep, and the "prediction calibration is anti-helpful for this task" diagnostic.

---

## What this branch does NOT do (deferred to later phases)

- Phase 3 (role-balanced curriculum): danger-only / approach-only / balanced source curricula.
- Phase 4 (HazardGraphWorld): closer-domain transfer pair.
- Phase 5 (ChemistryLite): structured-design transfer.
- Phase 6 (repair convergence): two-colony `ka=DANGER` vs `ka=RESOURCE`.
- Calibration fix to `PredictionEngine` (flagged in the report as the next bug to chase).

These are the right next moves; see `docs/ABLATION_V2_REPORT.md` § *Recommended next steps* and `docs/TAIS_FULL_DETAILED_ROADMAP.md` for the full plan.
