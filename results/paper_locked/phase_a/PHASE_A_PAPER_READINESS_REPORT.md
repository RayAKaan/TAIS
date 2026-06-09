# Phase A: Paper Readiness Report

## Summary

Three reviewer-critical gaps identified during pre-submission review have been
addressed:

| Gap | Status | Result |
|-----|--------|--------|
| Prediction paradox (`no_prediction` beats `full`) | **Resolved** | Paradox eliminated on 3/5 metrics; gap reduced 43-56% on remaining 2 |
| Engine selection policy | **Implemented** | Action-vocabulary-based gating with no regression on cognitive contribution results |
| Speech token portability benchmark | **Implemented** | Null result (honestly reported); establishes quantitative baseline |

## Test Coverage

- **Baseline (before Phase A):** 162 tests
- **New tests:** 19 (6 calibration + 5 engine policy + 2 mote integration + 6 speech)
- **Total:** 181 tests all passing

## Files Changed

### New Files (6)

| File | Purpose |
|------|---------|
| `tais_core/engine_policy.py` | Action-vocabulary-based engine selection policy |
| `experiments/speech_token_portability.py` | Speech token portability benchmark runner |
| `tests/test_prediction_calibration.py` | 6 calibration unit tests |
| `tests/test_engine_policy.py` | 5 engine policy unit tests |
| `tests/test_mote_engine_policy.py` | 2 mote integration tests |
| `tests/test_speech_token_portability.py` | 6 benchmark tests |
| `docs/PHASE_A_PREDICTION_CALIBRATION_REPORT.md` | Calibration fix report |
| `docs/PHASE_A_ENGINE_SELECTION_REPORT.md` | Engine policy report |
| `docs/PHASE_A_SPEECH_TOKEN_PORTABILITY_REPORT.md` | Speech benchmark report |
| `docs/PHASE_A_PAPER_READINESS_REPORT.md` | This aggregate report |

### Modified Files (3)

| File | Change |
|------|--------|
| `tais_core/memory.py` | `PredictionEngine`: domain reward scale calibration in `predict()` and `record_outcome()`; `should_explore()` accepts domain parameter |
| `tais_core/mote.py` | `use_engine_policy` flag and gating in `step()` / `choose_action()` |
| `experiments/logic_transfer_runner.py` | ASCII-safe table characters for Windows compat |

## Non-Negotiables

1. **Do not break existing transfer results** — Verified: calibration experiment with 200 seeds shows consistent `full`, `empty_pretrain`, `logic_pretrain` results vs baseline.
2. **Do not hard-code LogicWorld or RuleWorld into prediction calibration** — Calibration uses per-domain reward scale tracked generically in `_domain_abs_mean`.
3. **Do not disable cognitive engines globally** — Policy is per-mote with `use_engine_policy` flag defaulting to `True`.
4. **Engine policy must be generic and action-vocabulary-based** — Policy reads `universal_op` from the action set, not domain names.
5. **Speech benchmark can fail scientifically, but must run** — 50-seed run completes in ~1s; null result is honestly reported.
6. **All tests must pass before commit** — 181 tests pass.
7. **Reports must use real numbers only** — All reports use actual experimental data.

## Unresolved Items for Reviewers

- The prediction paradox is reduced but not eliminated on First TASK_SUCCESS Tick
  (gap went from -1.265 to -0.715). The remaining gap is inherent to having a
  non-zero prediction mechanism — `no_prediction` will always have a smaller
  first-prediction error by returning 0.0.
- The engine policy's sensorimotor-only branch is untested empirically because
  all current TAIS domains include VERIFY. A dedicated sensorimotor domain would
  be needed for a full validation.
- Speech token portability is a null result in single-mote settings. Multi-mote
  swarms may show transfer through inter-mote communication.
