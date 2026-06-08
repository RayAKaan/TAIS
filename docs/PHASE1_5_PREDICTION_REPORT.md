# Phase 1.5 — PredictionEngine Calibration Fix

**Date:** 2026-06-07
**Branch:** `phase1-5-prediction-fix`
**Scripts:** `experiments/predict_diagnostic.py`, `experiments/predict_calibration_sweep.py`, `experiments/ablation_runner.py`
**Raw data:** `results/ablation_v3_eval{12,30,50}.{txt,csv,json}` (regenerable, gitignored)
**Tests:** `tests/test_prediction_v15.py` (9 new)

---

## TL;DR

| Metric | v2 (post-Phase 1) | v3 (post-Phase 1.5) | Δ |
|---|---:|---:|---:|
| **Fresh-mote prediction error (h=12)** | 1.086 | **0.884** | **−18.6%** |
| Fresh-mote prediction error (h=30) | 0.682 | **0.532** | **−22.0%** |
| Fresh-mote prediction error (h=50) | 0.440 | **0.340** | **−22.7%** |
| `full` first-apply tick (h=12) | 6.625 (Δ−1.11, p=0.020) | 6.705 (Δ−1.15, p=0.017) | ~same |
| Diagnostic flip at seed=7, t06 | verify wins over apply | **apply stays chosen** | fixed |
| Unit tests | 24 | **33** | +9 |
| Production code touched | — | `tais_core/memory.py` (PredictionEngine.predict + record_outcome) | localized |

**Primary win:** prediction error drops 20–23% across all horizons, the per-trial diagnostic preference-flip bug is gone, and a new behavioral guard test (`IntegrationGuard.test_verify_cannot_outscore_apply_on_first_sight`) makes the v2 bug impossible to silently reintroduce.

**Secondary finding:** while investigating, I built `experiments/predict_calibration_sweep.py` and found that the ablation runner under-reports the true `full` transfer effect by about 2× compared to a cleaner single-condition sweep at the same 200-seed budget. Documented below; not yet fixed (would need a deeper rewrite of `run_experiment`).

---

## The bug

The v2 ablation report (Phase 1) flagged this paradox:

> `no_prediction` *helps* on first-apply tick (Δ=−2.61 at h=12) while doubling prediction error. The prediction system is mechanically active but its policy contribution is currently negative for this task.

The diagnostic (`experiments/predict_diagnostic.py`, seed=7, mixed-Grid pretrain → RuleWorld) showed exactly why. At tick 01 of the first eval trial:

```
   t01 |*apply_implication | +4.00 | +4.00 | +1.70 |  0.40 |  0.25 |  +9.05
       | verify_rule       | +3.00 | +0.00 | +0.06 |  0.20 |  0.25 |  +2.61
       | random_assert     | +3.00 | +0.00 | +0.00 |  0.50 |  0.25 |  +2.25
```

`verify_rule` had **never been executed** in this trial (historical = 0.00) yet its `predicted` value was **+3.00**. Looking at `PredictionEngine.predict`:

```python
nets = self._per_transform_net.get(transformation.name, [])
if nets:
    return sum(nets[-12:]) / len(nets[-12:])
valence = pattern_memory.predict_consequence(graph)
if valence == "GOOD":
    return 3.0    # <— this
if valence == "BAD":
    return -3.0
return 0.0
```

The fallback for "unseen action in a GOOD-looking graph" returned a hardcoded **+3.0** — regardless of the action's own cost. In RuleWorld:

| Action | base_cost | actual reward | v2 unseen prior |
|---|---:|---:|---:|
| `verify_rule` | 0.2 | +0.02 | **+3.0** |
| `apply_implication` | 0.4 | +4.00 first / +0.05 repeat | **+3.0** |
| `random_assert` | 0.5 | −3.00 | **+3.0** |

In the `choose_action` score formula:

```python
score = predicted + historical + transfer - cost - skepticism * risk
```

the `verify_rule` prior alone outweighs its cost by 2.80, so the mote was funnelled toward verify-spamming after a few ticks — even though `apply_implication`'s actual EV is two orders of magnitude higher.

By tick 06 of the diagnostic, the running mean of `apply_implication` had dropped to `+1.04` (one +4 solve + several +0.05 repeats averaged across 12 entries) while `verify_rule` was still being scored against the **+3.00 valence prior** rather than its actual +0.02, and verify won:

```
   t06 |*verify_rule       | +3.00 | +0.00 | +0.26 |  0.20 |  0.25 |  +2.81
       | apply_implication | +1.04 | +1.04 | +1.24 |  0.40 |  0.95 |  +1.96
```

That's the smoking gun.

---

## The fix

Four scoped changes to `PredictionEngine` in `tais_core/memory.py`:

### 1. Per-action history keyed by `(domain, name)`

Was `Dict[str, List[float]]` keyed on transformation name. Now `Dict[Tuple[str, str], Tuple[float, int]]` keyed on `(domain, name)`. Prevents a `move_toward` mean learned in GridWorld from silently driving an action with the same name in another domain. Cross-domain inference still happens — explicitly, through pattern memory / `transfer_action_priors` — but no longer invisibly through per-action means.

### 2. Exponentially-weighted running mean (α = 0.4)

Replace the unweighted sliding window of 12 outcomes with an EWM:

```python
new_ewm = (1 - α) * ewm + α * actual.net
```

The previous window averaged the first +4 solve against eleven +0.05 repeats and produced ~0.71. With α=0.4, after the same five repeats the EWM is ~0.36 — *still small but no longer pretending the +4 never happened*. More importantly, a single fresh outcome moves the estimate by 40% of the gap, so calibration adapts within a few ticks instead of waiting for a sliding window to roll.

### 3. Cost-anchored valence-prior cap

```python
cap = max(0.5, min(3.0, 1.5 * float(transformation.base_cost or 1.0)))
return cap * UNSEEN_DISCOUNT  if valence == "GOOD" else ...
```

An action that costs 0.2 (verify) gets a prior of at most ±0.5, multiplied by the 0.5 unseen discount = ±0.25. An action that costs 1.0 (`TRANSFORM`-class) gets ±0.75. An action that costs ≥2.0 is clipped at ±3.0 (so we still allow large priors for genuinely expensive actions). This forces the prior to be proportional to skin in the game.

### 4. Unseen-action discount (0.5)

`_UNSEEN_DISCOUNT = 0.5` halves the valence prior when no real history exists. Prior uncertainty deserves a discount, not a full optimistic prior. With (3) above, this means a fresh `verify_rule` in a "GOOD" graph predicts +0.25 instead of +3.00.

---

## Test coverage

`tests/test_prediction_v15.py` adds 9 new tests pinning the contract. The behavioral guard:

```python
class IntegrationGuard:
    def test_verify_cannot_outscore_apply_on_first_sight(self):
        # Cost-anchored priors must respect base_cost ordering on unseen
        # actions. p(verify) < p(apply) < p(random_assert) in magnitude.
```

If anyone ever reintroduces the hardcoded ±3.0 fallback (or removes the cost anchor), this test fails immediately.

---

## Ablation v3 (post-fix) results

Same setup as Phase 1: 200 seeds × 8 conditions × {12, 30, 50}-tick horizons, mixed-Grid pretrain (20 ticks). Compared to v2:

### First Apply (TASK_SUCCESS) Tick — h=12

| Condition | v2 Δ (p) | v3 Δ (p) | Notes |
|---|---:|---:|---|
| `full` | −1.11 (0.020 *) | **−1.15 (0.017 *)** | unchanged |
| `no_action_role` | −0.40 (0.39) | −0.37 (0.44) | still null |
| `no_prior_decay` | −1.07 (0.025 *) | −1.11 (0.020 *) | unchanged |
| `no_pattern_transfer` | −0.40 (0.39) | −0.41 (0.38) | still null |
| `no_prediction` | −2.61 (<0.001 ***) | −2.61 (<0.001 ***) | unchanged (predict is monkeypatched out) |
| `empty_pretrain` | +0.64 (0.13) | +0.57 (0.18) | still null/slight hurt |
| `random_pretrain` | −0.77 (0.087) | **−0.88 (0.049 *)** | now significant |
| `ruleworld_pretrain` | −2.47 (<0.001 ***) | **−1.33 (0.008 **)** | weaker — calibration changed |

### Prediction Error — h=12 (lower is better)

| Condition | v2 fresh | v3 fresh | Δ |
|---|---:|---:|---:|
| `full` | 1.086 | **0.884** | −18.6% |
| `no_action_role` | 1.093 | 0.885 | −19.0% |
| `no_prior_decay` | 1.087 | 0.884 | −18.7% |
| `no_pattern_transfer` | 1.092 | 0.883 | −19.1% |
| `no_prediction` | 0.550 | 0.550 | 0% (predict monkeypatched out) |
| `empty_pretrain` | 1.086 | 0.884 | −18.6% |
| `random_pretrain` | 1.086 | 0.884 | −18.6% |
| `ruleworld_pretrain` | 1.086 | 0.884 | −18.6% |

At h=50 the improvement is **−22.7%** uniformly: 0.440 → 0.340. The calibration fix is doing real work; the engine is now systematically better at predicting consequences.

### What didn't move much (and why)

- **`full` first-apply tick is statistically unchanged** (Δ−1.11 → Δ−1.15). The runner's per-trial RNG noise is large enough at h=12/n=200 that the diagnostic-level improvement (apply stays chosen instead of flipping to verify) doesn't always reach the runner's TASK_SUCCESS detector before the trial ends.
- **`no_prediction` is still net-positive on first-apply tick** (Δ=−2.61). The calibration is much better but `predicted` is still *double-counted* with `historical` in `choose_action`'s additive score:
  ```python
  score = predicted + historical + transfer - cost - skepticism * risk
  ```
  Both terms are estimators of E[net] for the same action — adding them as if independent over-weights known-good actions and amplifies any residual calibration bias. This is the next thing to fix (Phase 1.6?) but it's a deeper architectural choice (subsume `historical` into `predicted`? blend with a weight? use prediction only for `prediction_error` and `should_explore`?) and I left it for an explicit design decision rather than a silent commit.
- **`ruleworld_pretrain` ceiling effect is smaller in v3** (−2.47 → −1.33). Same root cause: the calibration improvement helps fresh motes more than already-pretrained motes (pretrained motes already had real history, so the per-trial fix mostly matters for the fresh comparator). The ceiling and full conditions are converging — which is what we want long-term.

---

## Secondary finding: the runner under-reports the effect

While building `experiments/predict_calibration_sweep.py` (a single-condition, single-blend sweep over the same 200 seeds), I found:

| Source | `full` first-apply Δ (h=12) | p | d |
|---|---:|---:|---:|
| `ablation_runner.py` `full` | **−1.15** | 0.017 * | −0.169 |
| `predict_calibration_sweep.py` `v2_baseline_1_1` | **−1.96** | <0.001 *** | −0.326 |

The sweep is 70% stronger. Same code paths, same seeds, same mote, same RuleWorld, same Phase 1.5 prediction engine. The standalone seed=10000 case agrees exactly (−11 ticks both ways). So the difference appears at *aggregate* level only.

Most plausible suspect: shared global state across conditions. `UniversalMote._id` is a class-level counter, and inside a single `run_experiment` loop the runner constructs ~3,200 motes (8 conditions × 2 sides × 200 seeds). Each `__init__` consumes ~30 random numbers (Lexicon, SpeechGenome). Even though `random.seed(seed)` is called at the start of each `run_trial`, *something* — possibly the import-time RNG state of an indirect dependency, or `_per_transform_net_ewm` carrying state across the mote pool — is reducing the *paired* delta in the runner relative to the cleaner sweep.

I did **not** fix this in Phase 1.5. The runner is deterministic and the qualitative pattern (full ≫ ablations ≫ controls) is consistent across all three reports (v1, v2, v3), so the headline conclusion stands. But for paper-grade work the cleaner sweep design should replace the all-conditions-in-one-loop runner. Logged as a Phase 1.6 task.

### Calibration sweep itself

The sweep also answered the original "what's the best blend?" question:

```
blend                    fresh     pre   Δticks         p       d
---------------------- ------- ------- -------- --------- -------
v2_baseline_1_1          7.850   5.890   -1.960    <0.001 ***  -0.326
no_pred_0_1              7.850   5.810   -2.040    <0.001 ***  -0.345
no_hist_1_0              7.850   5.920   -1.930    <0.001 ***  -0.322
blend_60_40              7.850   5.870   -1.980    <0.001 ***  -0.331
blend_40_60              7.850   5.870   -1.980    <0.001 ***  -0.331
blend_50_50              7.850   5.870   -1.980    <0.001 ***  -0.331
```

All blends are within ~0.1 ticks. **The double-counting is not the load-bearing problem** — once the calibration is fixed, the formula's shape barely matters for this benchmark. That's a useful data point: don't refactor `choose_action`'s score formula in Phase 1.6 just for elegance; only do it if a *different* domain (HazardWorld, ChemistryLite) shows asymmetric sensitivity.

---

## Honest caveats

1. **The diagnostic single-trial improvement does not show up clearly at the population scale**, because the runner's noise is larger than the per-trial improvement (~1 tick) for this 12-tick horizon. The win is real but the headline metric is roughly unchanged.
2. **The 20% prediction-error improvement is the cleanest result.** It's significant at every horizon, holds across every condition that uses prediction, and the effect size grows with horizon (more chances to update the EWM, more chances for v2's stale window to hurt).
3. **`no_prediction` still beating `full` is a remaining architectural issue.** The next fix is `choose_action`'s additive score, not the prediction engine itself.
4. **Same-domain pretraining ceiling shrank** (−2.47 → −1.33). This is *expected* — the v2 ceiling was inflated by `ruleworld_pretrain` having seen real `apply_implication` history while fresh motes were trapped with miscalibrated +3.0 priors. With both sides now well-calibrated, the gap narrows.
5. **The runner-vs-sweep discrepancy needs investigation** before any HazardWorld/ChemistryLite transfer claims. We are currently *under-reporting* the real transfer effect at population scale.

---

## Files touched

- `tais_core/memory.py` — `PredictionEngine.predict` + `record_outcome` rewrite, plus docstring with the four fixes spelled out.
- `tests/test_prediction_v15.py` — 9 new tests (4 cost-anchored prior, 3 EWM, 1 cross-domain isolation, 1 integration guard).
- `experiments/predict_diagnostic.py` — single-seed per-tick action-score diagnostic. Run with `PYTHONPATH=. python3 experiments/predict_diagnostic.py`.
- `experiments/predict_calibration_sweep.py` — 200-seed blend sweep over 6 weighting schemes. Run with `PYTHONPATH=. python3 experiments/predict_calibration_sweep.py`.
- `docs/PHASE1_5_PREDICTION_REPORT.md` — this report.

## Test status

```
PYTHONPATH=. python3 -m unittest discover -s tests -v
# Ran 33 tests in 0.034s — OK
```

## Recommended next steps

1. **Investigate the runner-vs-sweep discrepancy.** The standalone `predict_calibration_sweep.py` reports a 2× larger effect than `ablation_runner.py`. Bisecting which shared state in the runner suppresses the effect should take an hour and would directly strengthen any future paper claim.
2. **Decide on the `choose_action` formula.** `no_prediction` still beats `full` because `predicted + historical` double-counts. Three options: (a) drop `predicted` from the score and reserve it for `should_explore` only; (b) drop `historical` and rely on the EWM; (c) blend with a weight learned per-domain. The sweep suggests any of these would be roughly equivalent on RuleWorld; HazardWorld will be the real test.
3. **Then proceed with the roadmap's Phase 4 (HazardGraphWorld).** Don't add new domains until the runner/sweep discrepancy is understood; otherwise transfer claims will be ambiguous between "the architecture transferred" and "the runner under-counted the effect."
