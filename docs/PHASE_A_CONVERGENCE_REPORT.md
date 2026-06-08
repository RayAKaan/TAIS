# Phase A Convergence Report

**Goal:** Merge V6 cognitive engines (metacognition, causal reasoning, hierarchical planning) into `tais_core/UniversalMote` as optional None-safe components, then evaluate Grid→Logic transfer.

**Branch:** `phase-a-convergence`

**Date:** 2026-06-09

---

## Files Created/Modified

| File | Change |
|---|---|
| `tais_core/metacognition.py` | New — `MetacognitiveEngine`, `SelfModel`, `PredictionTracker` |
| `tais_core/causal.py` | New — `CausalReasoningEngine`, `CausalLink`, `Counterfactual` |
| `tais_core/planning.py` | New — `HierarchicalPlanner`, `Plan`, `PlanStep` |
| `tais_core/__init__.py` | Added 9 new exports for all engine classes |
| `tais_core/mote.py` | 7 modifications: engine slots (default `None`), `enable_cognitive_engines()`, `choose_action()` metacognitive modulation, `step()` engine hooks, `reproduce()` metacog-only inheritance, `metrics()` cognitive dict |
| `tests/test_cognitive_engines.py` | New — 20 tests (None defaults, enable/disable, step integration, reproduction, metrics) |
| `experiments/cognitive_transfer_runner.py` | New — 7-condition experiment reusing `logic_transfer_runner` helpers |

## Design Decisions

1. **Engines default to `None`** — existing 74 tests pass unchanged. Only motes that call `enable_cognitive_engines()` get engine behavior.
2. **Metacognition modulates exploration** in `choose_action()`: low prediction accuracy → force explore (ignore highest score), high accuracy → suppress explore. This is the only change to action selection.
3. **Causal and Planning are passive recorders** — they record data in `step()` but do not alter action selection. Any transfer benefit would need Phase B wiring.
4. **Causal/planner NOT inherited** by children — causal beliefs are domain-specific. Metacognitive self-model params *are* inherited.
5. **`record_outcome()` corrected** to increment `self_model.prediction_count` and append to `strategy_history` — without this, metacognitive competence never updates since `select_strategy()` is not called in the mote loop.

## Test Suite

- **Before: 74 tests passing** (all existing)
- **After: 94 tests passing** (74 old + 20 new cognitive engine tests)
- No regressions.

## Experiment: Grid → Logic Transfer (200 seeds, 15 eval ticks)

### Conditions

| Condition | Engines | Pretrain |
|---|---|---|
| `fresh_control` | (none — fresh mote) | (none) |
| `full_baseline` | None | Grid, 20 ticks |
| `full_with_metacog` | Metacognition | Grid, 20 ticks |
| `full_with_causal` | Causal | Grid, 20 ticks |
| `full_with_planning` | Planning | Grid, 20 ticks |
| `full_with_all` | All 3 | Grid, 20 ticks |
| `engines_no_pretrain` | All 3 | (none) |

### First TASK_SUCCESS Tick (lower is better)

| Condition | Fresh | Condition | Δ | 95% CI | p | d |
|---|---|---|---|---|---|---|
| full_baseline | 11.750 | 9.425 | -2.325 | [-3.315, -1.335] | 0.000004 *** | -0.325 |
| full_with_metacog | 11.750 | 9.510 | -2.240 | [-3.285, -1.195] | 0.000026 *** | -0.297 |
| full_with_causal | 11.750 | 9.425 | -2.325 | [-3.315, -1.335] | 0.000004 *** | -0.325 |
| full_with_planning | 11.750 | 9.425 | -2.325 | [-3.315, -1.335] | 0.000004 *** | -0.325 |
| full_with_all | 11.750 | 9.510 | -2.240 | [-3.285, -1.195] | 0.000026 *** | -0.297 |
| engines_no_pretrain | 11.750 | 13.315 | +1.565 | [0.838, 2.292] | 0.000024 *** | +0.298 |

### Transfer Precision (higher is better)

| Condition | Fresh | Condition | Δ | 95% CI | p | d |
|---|---|---|---|---|---|---|
| full_baseline | 0.425 | 0.811 | +0.386 | [0.325, 0.447] | <0.001 *** | 0.877 |
| full_with_metacog | 0.425 | 0.859 | +0.434 | [0.373, 0.495] | <0.001 *** | 0.987 |
| full_with_all | 0.425 | 0.859 | +0.434 | [0.373, 0.495] | <0.001 *** | 0.987 |
| engines_no_pretrain | 0.425 | 0.254 | -0.171 | [-0.239, -0.103] | <0.001 *** | -0.349 |

### Key Metrics Summary

| Metric | Baseline | +Metacog | +Causal | +Planning | +All | NoPretrain |
|---|---|---|---|---|---|---|
| First success Δ | -2.325 | -2.240 | -2.325 | -2.325 | -2.240 | +1.565 |
| Completion Δ | +0.075 | +0.060 | +0.075 | +0.075 | +0.060 | -0.215 *** |
| Contradictions Δ | +0.260 * | -0.075 | +0.260 * | +0.260 * | -0.075 | -0.570 *** |
| Reward Δ | +0.474 * | +0.380 | +0.474 * | +0.474 * | +0.380 | -0.971 *** |
| Invalid Δ | +0.205 | -0.325 * | +0.205 | +0.205 | -0.325 * | -0.860 *** |
| Precision Δ | +0.386 *** | +0.434 *** | +0.386 *** | +0.386 *** | +0.434 *** | -0.171 *** |

* p<0.05  ** p<0.01  *** p<0.001

## Interpretation

1. **Metacognition shows a modest positive signal**: fewer contradictions (0.985 vs 1.320), fewer invalid actions (1.520 vs 2.050, p=0.013), and higher transfer precision (0.859 vs 0.811). However, first-task success tick and task completion rate are not significantly improved over baseline.

2. **Causal and Planning have zero measurable effect**: every metric is numerically identical to `full_baseline`. This is expected — they are passive recorders with no action selection influence. They are ready for Phase B wiring.

3. **Engines without pretrain significantly harms**: the metacognitive exploration modulation interferes when the mote has no prior domain knowledge. The mote explores erratically instead of learning from scratch. This is a known limitation: confidence calibration is meaningless without experience.

4. **No cognitive engine harms transfer** when combined with pretrain. The None-safe design is validated — existing behavior is fully preserved.

## Verdict

**Phase A convergence is successful.** All cognitive engines are integrated, tested, and experimentally evaluated. Metacognition provides a small but measurable improvement in transfer precision and action quality. Causal and planning are structurally integrated and ready for active wiring in Phase B.

No performance regression. All 94 tests pass. Experiment results are reproducible (200 seeds).
