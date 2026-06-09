# Phase R2 — Role-Ontology Robustness

**Question:** Is the hand-designed role ontology load-bearing for TAIS
cross-domain transfer?

**Design:** 7-condition paired experiment (200 seeds, fresh + GridWorld-pretrained,
same seed) evaluated on LogicWorld (h=15).  All corruption applied via runner-local
monkeypatches — no core code or domain files modified.

## Conditions

| Condition | Description |
|---|---|
| `canonical_roles` | Normal behaviour (baseline) |
| `shuffled_target_role_hints` | Permute `role_hint` values among LogicWorld actions |
| `shuffled_target_universal_ops` | Permute `universal_op` values among LogicWorld actions |
| `shuffled_source_roles` | Permute roles emitted by `classify_action_role` during GridWorld pretrain only |
| `random_compatibility` | Replace `role_compatibility()` table with seed-deterministic uniform random values |
| `identity_only_compatibility` | `role_compatibility()` returns 1.0 only if source == target, else 0.0 |
| `no_role_transfer` | Zero-out `transfer_action_priors` (identical to F2's `no_pattern_transfer` at the action-prior level) |

## Results

### Table 1 — Primary Metrics

| Condition | first_success delta | completion delta | d(first_success) | d(completion) |
|---|---|---|---|---|
| canonical_roles | −2.34 *** | +0.060 | −0.328 | +0.098 |
| shuffled_target_role_hints | −1.70 ** | +0.070 | −0.230 | +0.108 |
| shuffled_target_universal_ops | −2.40 *** | +0.065 | −0.341 | +0.106 |
| shuffled_source_roles | −1.48 ** | +0.035 | −0.193 | +0.052 |
| random_compatibility | −2.87 *** | +0.110 * | −0.388 | +0.170 |
| identity_only_compatibility | −3.15 *** | +0.130 ** | −0.441 | +0.212 |
| no_role_transfer | −0.33 | +0.015 | −0.045 | +0.021 |

*** p<0.001, ** p<0.01, * p<0.05

### Table 2 — Transfer Mechanism Metrics

| Condition | transfer_uses delta | transfer_precision delta | transfer_strength delta |
|---|---|---|---|
| canonical_roles | +22.2 *** | +0.415 *** | +22.8 *** |
| shuffled_target_role_hints | +21.7 *** | +0.394 *** | +27.5 *** |
| shuffled_target_universal_ops | +22.3 *** | +0.417 *** | +31.1 *** |
| shuffled_source_roles | +21.9 *** | +0.406 *** | +20.0 *** |
| random_compatibility | +22.6 *** | +0.401 *** | +67.5 *** |
| identity_only_compatibility | +22.6 *** | +0.406 *** | +20.2 *** |
| no_role_transfer | +0.0 | +0.000 | +0.0 |

### Table 3 — Robustness Comparison

Each corruption condition compared to the canonical baseline on first_success d.

| Condition | d(first_success) | Diff from canonical | Interpretation |
|---|---|---|---|
| canonical_roles | −0.328 | — | Baseline |
| shuffled_target_role_hints | −0.230 | +0.098 (weaker) | Transfer survives; mild attenuation |
| shuffled_target_universal_ops | −0.341 | −0.013 (similar) | No effect vs baseline |
| shuffled_source_roles | −0.193 | +0.135 (weaker) | Transfer survives; modest attenuation |
| random_compatibility | −0.388 | −0.060 (stronger) | Random compat **improves** transfer |
| identity_only_compatibility | −0.441 | −0.113 (stronger) | Identity-only **improves** transfer |
| no_role_transfer | −0.045 | +0.283 (null) | No transfer without priors |

### Table 4 — Fresh vs Pretrained Completion Rates

| Condition | Fresh completion | Pretrained completion | Delta |
|---|---|---|---|
| canonical_roles | 0.500 | 0.560 | +0.060 |
| shuffled_target_role_hints | 0.500 | 0.570 | +0.070 |
| shuffled_target_universal_ops | 0.500 | 0.565 | +0.065 |
| shuffled_source_roles | 0.500 | 0.535 | +0.035 |
| random_compatibility | 0.500 | 0.610 | +0.110 * |
| identity_only_compatibility | 0.500 | 0.630 | +0.130 ** |
| no_role_transfer | 0.500 | 0.515 | +0.015 |

## Interpretation

### Key Findings

1. **The role ontology is not load-bearing.** Every role-corruption condition
   (shuffled target role_hints, shuffled target universal_ops, shuffled source
   roles, random compatibility, identity-only compatibility) preserves
   statistically significant transfer.  Only `no_role_transfer` — which blocks
   all prior transfer, not just role-mediated — kills the effect.

2. **Random and identity-only compatibility improve transfer.** Both conditions
   produce **stronger** first_success effect sizes than the canonical (hand-designed)
   compatibility table (d=−0.388 and d=−0.441 vs d=−0.328).  This suggests the
   hand-designed role ontology may introduce friction that partially counteracts
   transfer benefit from pattern matching alone.

3. **The load-bearing element is pattern transfer, not roles.** Since all role
   corruptions leave pattern matching intact, and only the complete removal of
   `transfer_action_priors` eliminates transfer, the primary mechanism is
   structural analogy — not the role system.

4. **Role-hint corruption on the target side is well-tolerated** (d=−0.230,
   still significant).  The classifier's early return on `action.role_hint`
   (mote.py:142) makes target role classification trivial, but even when these
   hints are shuffled, the role compatibility pathway contributes enough to
   maintain transfer.

5. **Random compatibility vastly inflates transfer_strength** (Δ=+67.5 vs
   canonical +22.8) because uniform random values in [0,1] often exceed the
   canonical table's moderate cross-role weights (0.70, 0.45, 0.35).  Despite
   this noise, transfer precision remains comparable (0.401 vs 0.415),
   indicating that the pattern matching is doing the real work.

### Impact on Paper Claims

| Claim | Status |
|---|---|
| Role ontology enables transfer | **Not supported.** Transfer survives all role corruptions. The ontology is not load-bearing. |
| Role-compatibility table is load-bearing | **Not supported.** Random and identity-only tables produce equivalent or stronger transfer. The hand-designed table is not needed. |
| Shuffled target roles disrupt transfer | **Not supported.** Target role-hint corruption only mildly attenuates transfer (d=−0.230 vs −0.328); significance survives. |
| Pattern transfer (structural analogy) is the primary mechanism | **Supported.** Only `no_role_transfer` (which blocks all prior transfer) eliminates the effect. |
| Role ontology may introduce friction | **Suggested.** Identity-only and random compatibility outperform the canonical table, hinting that cross-role generalization may add noise rather than signal. |

### Implications for Paper

- The box labeled "role-based transfer" in the architecture diagram can be
  de-emphasized.  The role system adds complexity but does not appear to carry
  the transfer signal.
- The paper should frame roles as a *diagnostic* tool for interpreting what the
  agent is doing, rather than a *mechanistic* necessity for transfer.
- If the paper makes causal claims about role generalization enabling transfer,
  these claims should be softened or qualified with the R2 robustness evidence.
- The finding that identity-only compatibility (purely structural analogy)
  produces the strongest transfer is notable and may refocus the contribution
  narrative.

## Artifacts

- `results/phase_r/role_ontology_robustness/report.txt` — full terminal output
- `results/phase_r/role_ontology_robustness/report.csv` — machine-readable
- `results/phase_r/role_ontology_robustness/report.json` — per-condition summary dicts
- `experiments/phase_r/role_ontology_robustness.py` — runner (all 7 conditions)
- `tests/test_role_ontology_robustness.py` — 21 tests
