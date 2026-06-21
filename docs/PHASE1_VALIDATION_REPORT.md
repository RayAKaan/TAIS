# Phase 1 Validation: Role-Compatibility Ablation Analysis

## Summary

The `scripts/phase1_validation.py` ablation compares three role-compatibility modes
(none/manual/discovered) on a GridWorld → RuleWorld 20+15 tick transfer task and reports
**identical reward** (−1.30) across all three at 100 seeds, with precision varying only
marginally (90.8–91.1%).

**Verdict: harness limitation, not a null result.** The GridWorld→RuleWorld setup is too
simple — `verify_rule` dominates the action-selection score regardless of which
role-compatibility function is installed. The finding does NOT generalise to domains
where multiple actions compete on similar scores.

---

## Traced Root Cause

Instrumented runs (`scripts/phase1_diagnostic.py`, 20 seeds) show:

| Metric                      | none    | manual  | discovered |
|-----------------------------|---------|---------|------------|
| `role_compat_calls`         | 3012    | 3012    | 3012       |
| `role_compat_hits`          | 980     | 1512    | 1512       |
| `role_compat_mean_result`   | 0.3254  | 0.5020  | 0.5020     |
| `transfer_uses_mean`        | 29.3    | 29.3    | 29.3       |
| `boost_mag_mean`            | 0.3087  | 0.3418  | 0.3418     |
| Action distribution         | ident.  | ident.  | ident.     |

The function is called 3012 times identically across modes (deterministic random seeds).
It returns different values (980 vs 1512 hits), producing slightly different mean
boost magnitudes (0.3087 vs 0.3418). But **the action with the highest composite score
is always `verify_rule`**, so behaviour — and therefore reward — never changes.

### Per-action boost breakdown (10 seeds)

| Action              | none mean | manual mean | discovered mean | Calls |
|---------------------|-----------|-------------|-----------------|-------|
| verify_rule         | 0.7838    | 0.9601      | 0.9601          | 206   |
| apply_implication   | 0.3883    | 0.3883      | 0.3883          | 206   |
| random_assert       | −0.3721   | −0.3721     | −0.3721         | 206   |
| verify_safety (GW)  | —         | 1.5957      | 1.5957          | 284   |
| avoid_threat (GW)   | —         | 1.5957      | 1.5957          | 284   |
| approach_resource   | 0.0       | 0.0         | 0.0             | 284   |

GridWorld-only actions (verify_safety, avoid_threat, approach_resource) get high
boosts in manual/discovered but are *not present* in the RuleWorld action vocabulary,
so they never compete. The RuleWorld actions are:

- `verify_rule`      — role `VERIFY_UNCERTAIN`        → boosted in every mode
- `apply_implication`— role `TRANSFORM_TOWARD_GOAL`    → rarely boosted (rare pattern match)
- `random_assert`    — role `EXPLORE_UNCERTAIN`        → negatively boosted

`verify_rule` wins because it maps exactly to `VERIFY_UNCERTAIN`, the role of
GridWorld's `verify_safety` pattern. In 'none' mode, identity matching gives
source==target → 1.0. In manual mode, the caution-family cross-bonus adds extra
boost. **Both are sufficient to make `verify_rule` dominate.**

---

## Why `verify_rule` always dominates

The `choose_action` score (mote.py:264):

```
score = historical + transfer + retrieval_boosts + continuity_boost − cost − risk
```

- `verify_rule` base cost ≈ 0.2; `apply_implication` base cost ≈ higher (more complex)
- `historical` for both starts at 0.0 in a new domain and accumulates slowly
- `transfer` for `verify_rule` is always the highest among available RuleWorld actions
- After the first few successful `verify_rule` uses, `historical` becomes positive,
  creating a self-reinforcing cycle

The 15-tick eval horizon is too short for the transfer decay (`transfer_decay_rate =
0.08`) to weaken `verify_rule`'s lead, or for `apply_implication` to build competing
local evidence.

---

## Implications

**The null result is specific to this test harness, not a general finding.**

| Claim | Status |
|-------|--------|
| Role compatibility does not affect reward in general | **False** — this setup is not sensitive enough |
| Role compatibility *is* called on the hot path | **Confirmed** — 3012 calls per 35 ticks |
| Role compatibility *does* produce different boost values | **Confirmed** — 0.3087 vs 0.3418 mean boost |
| The difference is too small to change action selection here | **Confirmed** — verify_rule always dominates |

A sensitive test needs:
1. A target domain where ≥2 actions have **similar scores** and different roles
2. A **longer eval horizon** (≥50 ticks) so transfer decay differentiates actions
3. A domain where the **marginal action choice matters** (asymmetric payoffs)

This is exactly what the Phase D NegoSim experiments provide — 50+ eval ticks,
multiple competing roles, and large asymmetric payoffs. Those show clear, significant
differences across compatibility regimes (the Phase R6 learned-compatibility results,
with Cohen's d > 2 for fused transfer).

---

## Recommendation

1. **Retire** `scripts/phase1_validation.py` as a validation tool (it cannot detect
   role-compatibility effects).
2. **Replace** it with a GridWorld→LogicWorld or GridWorld→NegoSim evaluation that
   has multiple competitive actions (the `grid_logic_1000_replication.py` runner is a
   natural candidate).
3. **Document** this finding so no one interprets the identical reward as evidence
   against the role-compatibility mechanism.

---

*Written following Phase 1 diagnostic runs at 20 seeds (deep boost tracing) and
confirmation at 100 seeds (full ablation).*
