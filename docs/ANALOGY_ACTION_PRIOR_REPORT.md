# Analogy-Guided Action Prior Report

## Question

The first cross-domain transfer test showed that pattern transfer existed but did not improve RuleWorld reward.

Hypothesis from analysis:

```text
Pattern transfer in memory is not sufficient.
Transferred patterns must influence action selection.
```

## Implemented fix

### 1. Enriched GraphPattern

Added action provenance to `GraphPattern`:

```python
successful_action_op
successful_action_name
successful_action_cost
failed_action_ops
failed_action_names
mean_outcome_net
```

This means a remembered pattern now stores not only:

```text
this structure was GOOD/BAD
```

but also:

```text
this universal action type produced that outcome
```

### 2. Changed pattern confidence semantics

Previously, confidence effectively meant “how often this pattern was good.”

That was wrong because reliable BAD patterns are also important.

Now confidence means:

```text
how reliably this pattern predicts its consequence signature
```

So a consistently BAD/DANGER pattern can be high-confidence.

### 3. Added PatternMemory.action_priors()

New bridge:

```python
PatternMemory.action_priors(target_graph, available_actions)
```

It:

```text
1. transfers stored patterns into the current graph by analogy
2. looks at source successful/failed universal action ops
3. returns action boosts/penalties for current available actions
```

Generic behavior:

```text
GOOD pattern + same successful universal_op → boost action
BAD pattern + same failed universal_op → penalize action
BAD pattern → modestly boost VERIFY / TEST / MOVE_AWAY
BAD pattern → modestly penalize MUTATE / COMPOSE
```

No domain-specific GridWorld→RuleWorld code was added.

### 4. Integrated into UniversalMote action selection

Action score now includes:

```text
prediction
+ historical action value
+ analogy_bias * transfer_prior
- cost
- skepticism * risk
```

Also added metrics:

```text
transfer_prior_uses
transfer_prior_total_strength
```

## Validation after fix

Full tests:

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

Result:

```text
Ran 15 tests
OK
```

## Cross-domain transfer experiment after fix

Command:

```bash
PYTHONPATH=. python3 experiments_cross_domain_transfer.py
```

Design:

```text
50 seeds
GridWorld pretraining: 20 ticks
RuleWorld evaluation: 12 ticks
```

Results:

```json
{
  "fresh": {
    "mean_total_reward": 22.62,
    "mean_invalid_actions": 1.64,
    "mean_first_apply_tick": 4.61,
    "never_applied": 9,
    "mean_final_energy": 118.768,
    "mean_prediction_error": 0.59306,
    "mean_transfer_prior_uses": 9.2,
    "mean_transfer_prior_strength": 18.38884
  },
  "grid_pretrained": {
    "mean_total_reward": 22.85,
    "mean_invalid_actions": 1.10,
    "mean_first_apply_tick": 5.371,
    "never_applied": 15,
    "mean_final_energy": 159.958,
    "mean_prediction_error": 0.49068,
    "mean_transfer_prior_uses": 29.28,
    "mean_transfer_prior_strength": 49.81576
  }
}
```

Delta, pretrained minus fresh:

```text
reward:                 +0.23
invalid actions:         -0.54
first apply tick:        +0.76  (worse/slower)
final energy:           +41.19
prediction error:        -0.102
transfer prior uses:    +20.08
transfer prior strength:+31.43
```

Interpretation:

```text
MIXED.
```

The fix made transfer priors actively used and produced a tiny reward improvement at 12 ticks.

But it did not solve the deeper problem:

```text
pretrained motes still apply the key RuleWorld action later
more pretrained motes still never apply implication
longer evaluations still do not show clear reward advantage
```

## Longer evaluation check

Ran additional informal checks with 30 and 50 RuleWorld ticks.

### 30 ticks

```text
fresh reward:       74.62
pretrained reward:  71.76
```

### 50 ticks

```text
fresh reward:       135.77
pretrained reward:  132.46
```

So the 12-tick reward improvement does not persist.

## Scientific interpretation

The analogy-action-prior bridge works mechanically:

```text
transfer prior uses increased from 9.2 to 29.28
transfer prior strength increased from 18.39 to 49.82
invalid actions decreased
prediction error decreased
energy improved
```

But cross-domain reward advantage is still not robust.

This means:

```text
The representation-to-action bridge exists now,
but GridWorld→RuleWorld is still mostly transferring caution/verification,
not task-relevant implication application.
```

## Diagnosis

The likely issue is action-space mismatch.

GridWorld successful action ops:

```text
MOVE_AWAY
VERIFY
MOVE_TOWARD
```

RuleWorld reward-critical action op:

```text
TRANSFORM
```

The transferred priors mostly encourage caution and verification, which reduces invalid actions but delays the rewarding implication action.

This is not a failure of graph representation.
It is a failure of action analogy.

## Next fix

Need a generic **action-role analogy** layer, not just universal-op matching.

Examples:

```text
MOVE_TOWARD resource in GridWorld
≈ APPLY_RULE toward target fact in RuleWorld
≈ ADD_FRAGMENT toward binding target in ChemistryLite
```

This cannot be hardcoded by domain pair.
It should be inferred from consequence role:

```text
approach-reward-source
avoid-harm-source
verify-before-risk
transform-toward-goal
```

So the next abstraction may be:

```python
ActionRole
```

with roles like:

```text
APPROACH_GOOD
AVOID_BAD
VERIFY_UNCERTAIN
TRANSFORM_TOWARD_GOAL
REPAIR_MISMATCH
ASK_UNCERTAIN
```

Then transfer should match by action role, not raw universal op.

## Current conclusion

The fix improved mechanism and secondary metrics but did not yet establish robust Category 3 transfer reward advantage.

Status:

```text
Pattern transfer: works
Action prior bridge: works mechanically
Invalid action reduction: works
Prediction/energy benefit: works
Robust cross-domain reward advantage: not yet
```

Next decisive experiment:

```text
Add action-role abstraction.
Rerun GridWorld→RuleWorld and SequenceWorld→RuleWorld.
```
