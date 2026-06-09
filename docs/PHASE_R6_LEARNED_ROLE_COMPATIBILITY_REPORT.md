# Phase R6 Report — Learned Role Compatibility Prototype

## Summary

Consequence-based learned role/op compatibility **partially recovers transfer**
on LogicWorld (Grid→Logic) but is **neutral on Rules and Hazard targets**.

On LogicWorld, the `learned_compatibility` condition significantly improves
first success tick (Δ=−2.805, d=−0.378, p<0.001) and total reward (+0.479,
d=0.159, p=0.025), while the hardcoded baseline is non-significant
(Δ=−0.815, d=−0.107, ns). This is a positive finding: simple EWM learning
from consequence statistics can produce usable compatibility scores.

However, `learned_plus_hardcoded` is consistently between learned and
hardcoded — never significantly better than either. The hand-coded table
remains competitive and is sometimes stronger.

**Key takeaway:** Learned role compatibility is partial evidence that
consequence statistics can recover useful compatibility, but the
hand-designed compatibility table remains at least as strong overall.
Averaging them does not improve over hardcoded alone.

## Design

| # | Condition | role_compatibility source |
|---|-----------|--------------------------|
| 1 | `hardcoded_compatibility` | Normal (hand-coded table, unchanged) |
| 2 | `learned_compatibility` | Learned `role_score(target_role)` from GridWorld pretrain |
| 3 | `learned_plus_hardcoded` | 0.5 × learned + 0.5 × hardcoded |
| 4 | `random_compatibility` | Seed-deterministic uniform random values |
| 5 | `no_compatibility` | Always 0.0 (cross-role) |

**Protocol:** GridWorld (20 mixed pretrain ticks) → target domain (15 eval ticks).
Paired by seed (200 seeds). Target domains: LogicWorld, RuleWorld, HazardWorld.

**Learning mechanism:**
- `LearnedRoleCompatibility` updates per `(role, universal_op)` key using
  bounded-normalized EWM (target = max(-1, min(1, outcome_net / 4.0)), alpha=0.3).
- When queried as `role_compatibility(source_role, target_role)`, returns
  `learned.role_score(target_role)` (average of all entries for that role)
  for cross-role pairs, and 1.0 for identical roles.
- Table populated during GridWorld pretrain (mean size: 3.46, mean score: 0.35).

## Results

### LogicWorld

| Metric | hardcoded | learned | learned+hardcoded | random | none |
|--------|-----------|---------|-------------------|--------|------|
| **First success Δ** | −0.815 | **−2.805** **** | −1.190 * | −2.030 *** | −1.720 ** |
| **Completion Δ** | −0.065 | +0.085 | −0.025 | +0.045 | +0.020 |
| **Reward Δ** | −0.187 | **+0.479** * | −0.021 | +0.255 | +0.173 |

`learned_compatibility` is the only condition with **positive** completion
rate (+0.085, ns trend) and the only one with **significant reward improvement**
(p=0.025). All conditions improve first success tick, but learned is strongest.

### RuleWorld

| Metric | hardcoded | learned | learned+hardcoded | random | none |
|--------|-----------|---------|-------------------|--------|------|
| **First success Δ** | −0.795 | +0.650 | +0.650 | −0.210 | +0.635 |
| **Completion Δ** | −0.005 | −0.065 | −0.065 | −0.040 | −0.060 |

No condition produces significant transfer on Rules. Learned compatibility
is essentially neutral and similar to no_compatibility for this target.

### HazardWorld

| Metric | hardcoded | learned | learned+hardcoded | random | none |
|--------|-----------|---------|-------------------|--------|------|
| **First success Δ** | +1.335 ** | +1.440 ** | +1.045 * | +2.010 *** | +1.895 *** |
| **Completion Δ** | −0.175 *** | −0.195 *** | −0.170 *** | −0.215 *** | −0.215 *** |
| **Contradictions Δ** | −0.365 *** | **−0.435** *** | −0.400 *** | −0.380 *** | −0.390 *** |

GridWorld → Hazard shows **negative transfer** on completion: all conditions
reduce task completion rate. Learned compatibility slightly reduces contradictions
more than hardcoded (−0.435 vs −0.365) but at a similar cost to completion.

## Interpretation

### Learned compatibility is partial evidence

Learned compatibility alone **significantly improves LogicWorld** transfer
(Δfirst_success=−2.805, d=−0.378). This exceeds the hardcoded baseline
(d=−0.107, ns). The learned table encodes meaningful cross-role information
from only 20 GridWorld ticks (mean table size ~3.5, mean score ~0.35).

However, on Rules and Hazard, learned compatibility is neutral or slightly
worse than hardcoded. The hand-designed compatibility table remains stronger
for these targets.

### learned_plus_hardcoded does not improve over hardcoded alone

Averaging learned and hardcoded (0.5 + 0.5) produces results that are
consistently intermediate — never significantly better than hardcoded alone on
any target. This is **not** the finding that would justify adding learned
compatibility as a refinement.

### Grid→Hazard negative transfer is robust

All conditions, including hardcoded, show negative transfer to HazardWorld.
This is consistent with Phase F2 (caution-speed dissociation) and Phase R4
(Grid→HazardLarge negative transfer). Learned compatibility does not mitigate
this.

### Limitations

1. **Role-only aggregation:** The patched function uses `learned.role_score()`
   which averages over all ops for a given role. This discards the op-specific
   information that the learning mechanism collects.
2. **Short pretrain budget:** 20 GridWorld ticks yields only ~3.5 table entries.
   More pretrain data might improve learned scores.
3. **No op-aware compatibility query:** The `role_compatibility` function
   signature only accepts role strings. A signature that also accepts the
   action's universal_op would let the learned table use its full (role, op) key.
4. **Prototype only:** This does not yet learn role labels themselves — only
   pairwise compatibility scores.

## Ruling

Learned compatibility from consequence statistics **can** recover useful
transfer information, as shown on LogicWorld. But the hand-designed
compatibility table is not replaceable by this simple prototype across all
targets. Learned compatibility should be noted as future work / auxiliary
mechanism rather than a core claim.

The paper reviewer risk note about "hand-designed role ontology" remains:
this prototype does not solve the automation problem, but it provides
initial evidence that consequence-driven learning is a viable direction.

## Artifacts

- `results/phase_r/learned_role_compatibility/learned_role_compatibility.{txt,csv,json}` — data
- `experiments/phase_r/learned_role_compatibility.py` — runner
- `tais_core/role_learning.py` — `LearnedRoleCompatibility` class + `make_learned_role_compatibility_fn()`
- `tais_core/mote.py` — `enable_learned_role_compatibility()`, `use_learned_role_compatibility` flag
- `tests/test_role_learning.py` — 34 tests (27 unit + 7 runner)
