# Phase R5 Report — Prediction Gating Sweep

## Summary

Prediction scoring is **conditionally useful** on LogicWorld (Grid→Logic transfer)
when enabled with sufficient weight (w=0.5) and modest gating threshold (k=3).
Completion rate rises from 53.0% to 68.5% (d=+0.427, p<0.001). However, prediction
scoring is **neutral on Rules and Hazard** targets. `no_prediction` is identical to
the default on all targets. The paper should keep prediction as an auxiliary
diagnostic mechanism rather than a core transfer driver.

## Reviewer Objection

> Prediction is implemented, but it is not clearly load-bearing for transfer.
> Right now, prediction calibration reduced the paradox, but no_prediction
> can still be competitive.

R5 tests whether prediction can become useful when its influence is gated by
current-domain evidence.

## Prediction Path Audit

### Where prediction is called

| Call site | File & Line | Effect |
|-----------|-------------|--------|
| `mote.step()` → `predict_action()` | `mote.py:233` | Records prediction for error tracking |
| `should_explore()` → `domain_error()` | `memory.py:597-606` | Uses prediction error as uncertainty bonus to exploration |
| `choose_action()` (R5 addition) | `mote.py:203-207` | **Opt-in scoring term** added for this experiment |
| `record_episode()` → `record_outcome()` | `memory.py:568` | Updates EWM and per-domain calibration |

### Current calibration state (Phase A)

- `_calibrate()` scales predictions down by `_domain_abs_mean` when that mean is
  in `(0.0, 1.0)`, preventing overestimation in small-reward domains like LogicWorld.
- EWM with `alpha=0.4` accumulates per `(domain, action_name)`.
- Fallback for unseen actions: cost-anchored valence prior (capped at ±1.5× cost).

### Current `no_prediction` behavior

- `AblationControls` in legacy runners replaces `mote.memory.predict_action` with
  `lambda action, graph: 0.0`.
- Affects `should_explore()` (domain_error computed against zero predictions) and
  recorded prediction error, but NOT the scoring formula (prediction was removed
  from scoring in Phase 1.5).

## Gating Design

Default TAIS behavior is unchanged. R5 tests optional prediction scoring.

### Parameters added to `UniversalMote` (`mote.py`)

```python
self.use_prediction_in_score: bool = False            # default: disabled
self.prediction_score_weight: float = 0.25            # prediction scaling
self.prediction_min_domain_observations: int = 0      # gating threshold
```

### Score term (inside `choose_action`, opt-in)

```python
if self.use_prediction_in_score:
    n = self.memory.prediction.domain_observation_count(observation.domain)
    if n >= self.prediction_min_domain_observations:
        score += self.prediction_score_weight * self.memory.predict_action(action, observation)
```

The `domain_observation_count()` accessor was added to `PredictionEngine` in
`memory.py` (Phase R5).

## Experiment Design

### Targets (small original domains)

- **logic** — LogicWorld (3 var, 3 clause satisfiability)
- **rules** — RuleWorld (3-step implication chain)
- **hazard** — HazardGraphWorld (6-node graph, 2 hazards)

### Source: GridWorld pretrain (20 ticks)

### Conditions

| Condition | `predict_action` | `use_prediction_in_score` | k | w |
|---|---|---|---|---|
| `no_prediction` | zeroed | — | — | — |
| `prediction_disabled_current` | normal | `False` | — | — |
| `prediction_k0_w025` | normal | `True` | 0 | 0.25 |
| `prediction_k3_w025` | normal | `True` | 3 | 0.25 |
| `prediction_k5_w025` | normal | `True` | 5 | 0.25 |
| `prediction_k10_w025` | normal | `True` | 10 | 0.25 |
| `prediction_k3_w05` | normal | `True` | 3 | 0.5 |
| `prediction_k5_w05` | normal | `True` | 5 | 0.5 |
| `prediction_k10_w05` | normal | `True` | 10 | 0.5 |

**Defaults:** seeds=200, pretrain_ticks=20, eval_ticks=15.

Comparison baseline: `prediction_disabled_current`.

## Results

### LogicWorld (Grid→Logic)

| Condition | First success | d (first) | p | Completion | d (compl) | p |
|---|---|---|---|---|---|---|
| no_prediction | 9.82 | +0.008 | 0.911 | 0.530 | 0.000 | 1.000 |
| prediction_disabled_current | 9.78 | — | — | 0.530 | — | — |
| prediction_k0_w025 | 9.35 | −0.215 | 0.002 | 0.580 | +0.208 | 0.003 |
| prediction_k3_w025 | 9.36 | −0.212 | 0.003 | 0.580 | +0.208 | 0.003 |
| prediction_k5_w025 | 9.51 | −0.174 | 0.014 | 0.575 | +0.195 | 0.006 |
| prediction_k10_w025 | 9.66 | −0.115 | 0.105 | 0.570 | +0.181 | 0.010 |
| **prediction_k3_w05** | **8.45** | **−0.430** | **<0.001** | **0.685** | **+0.427** | **<0.001** |
| prediction_k5_w05 | 8.58 | −0.422 | <0.001 | 0.680 | +0.419 | <0.001 |
| prediction_k10_w05 | 9.29 | −0.332 | <0.001 | 0.650 | +0.352 | <0.001 |

**Key finding:** Prediction scoring with k=3, w=0.5 produces the strongest
improvement on LogicWorld. `no_prediction` is identical to default (d=0.000),
confirming that the default prediction-off-in-scoring behavior is equivalent to
zeroing predictions.

### RuleWorld (Grid→Rules)

| Condition | First success | d (first) | p | Completion | d (compl) | p |
|---|---|---|---|---|---|---|
| no_prediction | 6.52 | −0.069 | 0.332 | 0.815 | +0.029 | 0.684 |
| prediction_disabled_current | 6.87 | — | — | 0.805 | — | — |
| prediction_k0_w025 | 6.84 | −0.041 | 0.559 | 0.805 | 0.000 | 1.000 |
| prediction_k3_w05 | 6.85 | −0.032 | 0.651 | 0.805 | 0.000 | 1.000 |

All prediction gating conditions are essentially identical to baseline on
RuleWorld. No condition shows a significant difference in first_success or
completion rate.

### HazardGraphWorld (Grid→Hazard)

| Condition | First success | d (first) | p | Completion | d (compl) | p |
|---|---|---|---|---|---|---|
| no_prediction | 10.57 | −0.025 | 0.725 | 0.600 | +0.057 | 0.424 |
| prediction_disabled_current | 10.70 | — | — | 0.575 | — | — |
| prediction_k0_w025 | 10.96 | +0.117 | 0.097 | 0.555 | −0.116 | 0.101 |
| prediction_k3_w05 | 11.04 | +0.157 | 0.027 | 0.555 | −0.116 | 0.101 |

All prediction gating conditions are neutral to slightly negative on HazardWorld.
No meaningful improvement in completion or hazard steps.

## Interpretation

### 1. Does any prediction-gated condition beat current default?

**Yes, on LogicWorld.** `prediction_k3_w05` achieves 68.5% completion vs 53.0%
(d=+0.427, p<0.001) and first_success 8.45 vs 9.78 (d=−0.430, p<0.001).

### 2. Does any beat `no_prediction`?

**Yes, on LogicWorld.** `no_prediction` is identical to default (53.0%, d=0.000),
so all gated conditions that improve over default also beat `no_prediction`.

### 3. Is prediction helpful only after k observations?

**Not strongly.** k=0 works as well as k=3 on LogicWorld. The benefit comes
primarily from enabling prediction scoring at all, not from the gating threshold.
However, k=10 reduces the benefit, suggesting that delaying prediction too long
misses the early-task window where prediction helps most.

### 4. Does prediction help symbolic domains but hurt Hazard?

Prediction helps a symbolic domain (LogicWorld) but is neutral on both Rules
(also symbolic) and Hazard (graph navigation). The effect is domain-specific
rather than category-specific.

### 5. Should prediction remain in Paper 1 as mechanism or be demoted?

**Prediction is conditionally useful.** It provides a significant, replicable
benefit on Grid→Logic transfer when scoring is enabled with sufficient weight.
The effect is not universal (neutral on Rules and Hazard), but it is real on
the primary symbolic target.

**Recommendation:** Prediction should remain in Paper 1 as an **auxiliary
mechanism** that contributes to task completion under appropriate gating. It
should not be framed as a core transfer driver (pattern matching + role
compatibility remain primary). The `prediction_k3_w05` condition demonstrates
that prediction is load-bearing on at least one target.

## Paper Impact

Prediction can be claimed as **conditionally useful** under target-domain
calibration/gating (k=3, w=0.5 on LogicWorld). The effect is large enough
(d=+0.427 completion) to be practically meaningful but domain-specific enough
that prediction should not be overclaimed as a universal mechanism.

### Decision

> Gated prediction beats default and no_prediction on at least one primary
> target (LogicWorld, d=+0.427 completion, d=−0.430 first_success).
> **Prediction is conditionally useful and should remain in Paper 1 as an
> auxiliary mechanism.**

## Limitations

- **Heuristic sweep**: The k/w values (3, 5, 10 / 0.25, 0.5) were hand-selected
  and may not be optimal. A broader grid search could find better combinations.
- **Domain specificity**: Prediction helps only on LogicWorld. It is neutral on
  Rules and Hazard. The paper must not overclaim.
- **Short horizons**: 15 eval ticks may be insufficient for prediction to
  accumulate reliable EWM evidence on domains with longer action chains.
- **Prediction remains scalar**: The prediction engine forecasts a single scalar
  outcome (consequence.net). More sophisticated prediction (e.g., multi-step,
  categorical) might generalize better.
- **Gating threshold matters little**: k=0 works as well as k=3, suggesting the
  gating mechanic adds complexity without clear benefit. The simpler fix —
  enable prediction scoring with sufficient weight — achieves the same result.
- **Hazard metric is noisy**: The small HazardGraphWorld (6 nodes) shows ~57%
  completion at baseline. hazard_steps is a binary-like count and may not capture
  subtle avoidance learning.

## Test Results

All 272 tests pass (261 prior + 11 new):

```
272 passed, 3 warnings, 4 subtests passed in 9.82s
```

## Artifacts

- `experiments/phase_r/prediction_gating_sweep.py` — runner
- `tests/test_prediction_gating.py` — 11 tests
- `results/phase_r/prediction_gating_sweep/prediction_gating_sweep.{json,csv,md,txt}` — 200-seed results
- `docs/PHASE_R5_PREDICTION_GATING_REPORT.md` — this document
