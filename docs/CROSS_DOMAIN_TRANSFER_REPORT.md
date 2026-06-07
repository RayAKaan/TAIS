# Cross-Domain Transfer Report

## Question

Does GridWorld pretraining improve RuleWorld learning compared with fresh motes?

This is the first Category 3-style scientific test. It is allowed to fail.

## Experiment

File:

```text
experiments_cross_domain_transfer.py
```

Command:

```bash
PYTHONPATH=. python3 experiments_cross_domain_transfer.py
```

Design:

```text
50 seeds
Group A: fresh UniversalMote enters RuleWorld
Group B: UniversalMote pretrained in GridWorld for 20 ticks, then enters RuleWorld
RuleWorld evaluation length: 12 ticks
```

Metrics:

```text
mean total RuleWorld reward
mean invalid actions
mean first tick applying implication
number of trials that never applied implication
mean final energy
mean prediction error
```

## Results

```json
{
  "fresh": {
    "mean_total_reward": 23.39,
    "mean_invalid_actions": 1.48,
    "mean_first_apply_tick": 4.857,
    "never_applied": 8,
    "mean_final_energy": 119.582,
    "mean_prediction_error": 0.58472
  },
  "grid_pretrained": {
    "mean_total_reward": 22.85,
    "mean_invalid_actions": 1.10,
    "mean_first_apply_tick": 5.371,
    "never_applied": 15,
    "mean_final_energy": 159.958,
    "mean_prediction_error": 0.48316
  },
  "delta_pretrained_minus_fresh": {
    "mean_total_reward": -0.54,
    "mean_invalid_actions": -0.38,
    "mean_first_apply_tick": 0.514,
    "mean_final_energy": 40.376,
    "mean_prediction_error": -0.10156
  }
}
```

## Interpretation

Result:

```text
FAIL / INCONCLUSIVE for cross-domain transfer reward advantage.
```

GridWorld-pretrained motes did **not** earn higher RuleWorld reward than fresh motes.

They did show some secondary improvements:

```text
lower invalid actions
lower prediction error
higher final energy
```

But they also:

```text
applied the key RuleWorld implication later
failed to apply it in more trials
earned slightly lower RuleWorld reward
```

## What this means

This is a useful failure.

It means:

```text
The substrate can represent cross-domain analogies.
Pattern transfer mechanically exists.
But transferred patterns are not yet being used strongly enough to improve behavior in a new domain.
```

The current architecture passes Category 1 and Category 2 tests, but the first Category 3 transfer-performance test is not yet passed.

## Likely reason

The UniversalMote action selector currently uses:

```text
per-action prediction history
pattern valence lookup
historical action value
cost/risk
```

But it does not yet convert analogical pattern mappings into specific action preferences in the new domain.

In other words:

```text
It can see that a pattern may transfer.
It does not yet know what to do with that transfer.
```

## Next architectural fix to test

Add an analogy-guided action prior:

```text
if current graph analogizes to stored GOOD pattern:
    boost transformations whose universal_op matches the successful source action

if current graph analogizes to stored BAD/DANGER pattern:
    boost VERIFY / MOVE_AWAY / TEST actions
    penalize risky TRANSFORM / MUTATE actions
```

This must be implemented generically, not as GridWorld→RuleWorld special code.

Then rerun the same experiment.

## Why this is valuable

This failure is exactly what the test battery is supposed to reveal.

The claim was:

```text
Pattern transfer should improve new-domain learning.
```

The result says:

```text
Not yet.
```

So the next work is not more domains. The next work is making pattern transfer operational in action selection.
