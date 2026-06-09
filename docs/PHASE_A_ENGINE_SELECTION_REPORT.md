# Phase A: Engine Selection Policy Report

## Problem

Cognitive engines (metacognition, causal reasoning, hierarchical planning) are activated
per-condition in experiments via `enable_cognitive_engines()`. There is no runtime policy
for deciding *when* each engine should be active based on the current action vocabulary.

For the paper, reviewers may ask: "Do cognitive engines help in sensorimotor domains
(GridWorld) where there are no symbolic operators to reason about?" The current
all-or-nothing approach cannot answer this.

## Fix

New module `tais_core/engine_policy.py` implements a generic, action-vocabulary-based
policy with three cases:

| Action vocabulary | Metacognition | Causal | Planning |
|-------------------|:-:|:-:|:-:|
| Sensorimotor only (MOVE_TOWARD, MOVE_AWAY) | off | off | off |
| Any symbolic op (VERIFY, TRANSFORM, etc.) | on | on | on |
| Mixed or unknown | on | off | off |

### Integration in `UniversalMote`

- `use_engine_policy: bool = True` flag in `__init__()` (can be disabled per-mote)
- Policy evaluated at each `step()` after actions are retrieved
- Engine update blocks gated: `if engine is not None and (policy is None or policy.use_xxx)`
- Metacognitive exploration modulation in `choose_action()` similarly gated

### Files Changed

| File | Change |
|------|--------|
| `tais_core/engine_policy.py` | **New** — `EnginePolicyDecision`, `decide_engine_usage()` |
| `tais_core/mote.py` | Added `use_engine_policy`, `_engine_policy`, gating in `step()` and `choose_action()` |

## Validation

- All 7 engine policy tests pass (5 unit + 2 integration)
- Existing cognitive ablation runner (`cognitive_contribution.py`) continues to work
  (policy is evaluated but all current domains have symbolic ops, so engines stay on)
- A mote in GridWorld with policy enabled and engines instantiated steps without error
  (policy detects symbolic ops and keeps engines active)
- A mote in RuleWorld with policy enabled correctly has `_engine_policy.use_metacognition == True`

## No Regression

The cognitive contribution experiment (200 seeds) was re-run with the policy active.
Results are consistent with the Phase D baseline because all TAIS domains include
at least one symbolic operator (VERIFY), so the policy never suppresses engines.

## Limitations

- Current TAIS domains all include VERIFY, so the policy never exercises the
  sensorimotor-only branch in practice. A dedicated sensorimotor-only domain
  would be needed to empirically measure the benefit of disabling engines.
- The symbolic/sensorimotor classification is heuristic; future work could learn
  the policy from experience.
