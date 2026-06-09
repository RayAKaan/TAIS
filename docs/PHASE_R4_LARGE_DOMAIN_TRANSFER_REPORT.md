# Phase R4 Report — Large Domain Variants Transfer

**Date:** 2026-06-09
**Branch:** `phase-r4-large-domain-variants`
**Tests:** 261 passed (238 prior + 18 large domain + 5 runner)

## Motivation

All prior TAIS experiments use small synthetic domains (LogicWorld: 3 vars, 3 clauses;
HazardWorld: 6 nodes; RuleWorld: 3-step chain). Phase R4 tests whether TAIS
role-transfer survives on larger versions of the same domain types:

- **LogicWorldLarge:** 6 variables, 12 clauses (vs 3 vars, 3 clauses)
- **HazardGraphWorldLarge:** 15 nodes, 0.2 hazard density (vs 6 nodes, 0.33 density)
- **RuleWorldChainLong:** 5-step implication chain (vs 3-step chain)

These are still small compared to real-world problems but are meaningfully harder
than the original domains, requiring the mote to scale pattern recognition and
action selection to larger graphs.

## Design

3 target domains × 5 conditions paired experiment, seeds=100, pretrain=20, eval=30:

| Condition | Pretrain domain(s) |
|---|---|
| `fresh` | None (baseline) |
| `grid_pretrain` | GridWorld (same as original cross-domain transfer) |
| `rules_pretrain` | RuleWorld (3-step) |
| `three_domain_pretrain` | GridWorld + RuleWorld + HazardWorld (small originals) |
| `same_domain_pretrain` | The large target domain itself |

### Three_domain_pretrain note

We use the small original domains (GridWorld, RuleWorld, HazardWorld) — NOT
LogicWorld small — to avoid near same-domain leakage for the logic_large target.
The three-domain condition tests whether diverse prior experience on smaller
domains transfers to larger ones, even when the source domain structures
(2D grid, 3-step chain, 6-node hazard graph) differ substantially from the
target (6-var SAT graph, 15-node hazard graph, 5-step chain).

### Domain construction

- **LogicWorldLarge:** Seeded random SAT formula with 6 boolean variables and 12
  clauses. A hidden satisfying assignment is generated deterministically from the
  seed, and each clause is guaranteed to be satisfied by this assignment. This
  guarantees the formula is satisfiable while allowing random clause generation.
  Actions: 12 actions (set each variable true/false), 64 states (all assignments).
  Graph structure: n=6 variable nodes, bipartite clause edges.

- **HazardGraphWorldLarge:** Random connected graph with n=15 nodes generated via
  a seeded spanning tree + extra random edges. Hazard density=0.2 means ~3 of 15
  nodes are hazardous (vs 2 of 6 = 0.33 in small). The mote starts at node 0 and
  must reach node 14, learning which nodes are hazardous.

- **RuleWorldChainLong:** Linear implication chain of length 5 (v0→v1→v2→v3→v4→v5).
  The mote starts with v0, must apply sequence of 5 TRANSFORM actions to reach v5.
  No alternative paths or branches (same structure as small RuleWorld, just longer).

### Implementation note

No subclass overrides were needed for the large domains. The existing `act()`
methods work on any graph of the same type:
- `LogicWorld.act()` is position-agnostic — it enumerates all variable nodes
  regardless of count
- `HazardGraphWorld.act()` works on any connected graph with START, EXIT,
  HAZARD, and SAFE entity types
- `RuleWorld.act()` handles arbitrary chain lengths via the implication
  edge-following pattern

## Results

### LogicWorldLarge (n=100, eval=30 ticks)

| Condition | Completion | First success | d (completion) | p (completion) | d (first_success) | p (first_success) |
|---|---|---|---|---|---|---|
| fresh | 0.77 | 18.26 | — | — | — | — |
| grid_pretrain | 0.49 | 19.84 | −0.686 | <0.001 | +0.139 | 0.166 |
| rules_pretrain | 0.80 | 15.73 | +0.072 | 0.476 | −0.246 | 0.014 |
| three_domain_pretrain | 0.69 | 16.14 | −0.181 | 0.072 | −0.201 | 0.045 |
| **same_domain_pretrain** | **0.92** | **8.40** | **+0.404** | **0.002** | **−0.832** | **<0.001** |

**Interpretation:** Transfer survives to logic_large. Same-domain pretraining
is the clear winner (92% completion, d=+0.404, p=0.002). Rules pretrain helps
modestly (80%, ns). Three-domain pretrain slightly hurts (-0.181, ns). GridWorld
pretrain significantly **harms** completion (49% vs 77%, d=-0.686, p<0.001) —
a clear negative transfer result on this larger domain. First_success follows
the same pattern: same-domain fastest by far (8.40 vs 18.26, d=-0.832).

### HazardGraphWorldLarge (n=100, eval=30 ticks)

| Condition | Completion | Hazard steps | d (hazard_steps) | p (hazard_steps) |
|---|---|---|---|---|
| fresh | 0.00 | 7.70 | — | — |
| grid_pretrain | 0.00 | 7.29 | −0.158 | 0.116 |
| rules_pretrain | 0.00 | 7.22 | −0.192 | 0.057 |
| three_domain_pretrain | 0.00 | 8.90 | +0.228 | 0.023 |
| **same_domain_pretrain** | **0.00** | **5.61** | **−0.620** | **<0.001** |

**Interpretation:** HazardGraphWorldLarge is very hard — no agent reaches the
exit within 30 ticks under any condition (0% completion). The primary metric is
hazard_steps (number of TASK_FAILURE events). Same-domain pretraining
significantly reduces hazard steps (5.61 vs 7.70, d=-0.620, p<0.001),
demonstrating that avoidance learning transfers. Three-domain pretrain
unexpectedly increases hazard steps (8.90, d=+0.228, p=0.023). Grid and rules
pretrain show modest non-significant reductions.

### RuleWorldChainLong (n=100, eval=30 ticks)

| Condition | Completion | First success | d (completion) | p (completion) | d (first_success) | p (first_success) |
|---|---|---|---|---|---|---|
| fresh | 0.12 | 30.08 | — | — | — | — |
| grid_pretrain | 0.29 | 24.98 | +0.331 | 0.001 | −0.499 | <0.001 |
| rules_pretrain | 0.22 | 28.55 | +0.185 | 0.065 | −0.141 | 0.160 |
| three_domain_pretrain | 0.54 | 22.53 | +0.713 | <0.001 | −0.744 | <0.001 |
| same_domain_pretrain | 0.12 | 29.56 | 0.000 | 1.000 | −0.051 | 0.610 |

**Interpretation:** RuleWorldChainLong is the hardest of the three targets for
fresh training (12% completion). Three-domain pretraining produces the strongest
benefit (54% completion, d=+0.713, p<0.001), followed by grid pretrain (29%,
d=+0.331, p=0.001). Same-domain pretraining shows **no improvement at all**
(12%, d=0.000), because the chain is too long for the mote to learn in 20
pretrain ticks — the mote never reaches the end of the chain during pretraining
and therefore acquires no useful patterns. This is an important null result:
same-domain pretrain is not automatically beneficial when the domain is too
hard for the available pretrain budget.

### Transfer precision summary

| Target | fresh | grid_pretrain | rules_pretrain | three_domain_pretrain | same_domain_pretrain |
|---|---|---|---|---|---|
| logic_large | 0.656 | 0.874 | 0.816 | 0.878 | 0.832 |
| hazard_large | 0.000 | 0.762 | 0.399 | 0.704 | 0.000 |
| rules_chain_long | 0.843 | 0.917 | 0.500 | 0.878 | 0.872 |

Same-domain pretrain has zero transfer_precision on hazard_large because the
mote uses no transfer during eval — it has already internalized the domain
structure during pretrain. On logic_large and rules_chain_long, same-domain
pretrain shows moderate-to-high precision, indicating the mote still uses
transfer as a fallback strategy despite having seen the domain before.

## Impact on Paper Claims

**Transfer survives to larger domains but with important caveats:**

1. **Same-domain pretrain helps on two of three targets.** LogicWorldLarge
   reaches 92% completion (d=+0.404); HazardGraphWorldLarge reduces hazard
   steps by 27% (d=−0.620). But RuleWorldChainLong shows no benefit from
   same-domain pretrain — the pretrain budget (20 ticks) is insufficient.

2. **Cross-domain transfer is weaker on large domains.** Grid→Logic_large
   actually **harms** completion (49% vs 77%, d=−0.686). This is the first clear
   negative transfer result in TAIS and suggests that the small-domain Grid→Logic
   effect does not generalize to larger formula sizes.

3. **Three-domain pretrain is the strongest cross-domain condition for
   rules_chain_long** (54% completion, d=+0.713), confirming the diversity
   benefit seen in Phase F2 and Phase D. But it harms hazard_large (more
   hazard steps).

4. **The Grid→Logic negative transfer is a new finding.** All prior TAIS
   experiments found positive or neutral Grid→Logic transfer. On the larger
   domain, GridWorld pretraining produces a robust negative effect on
   completion rate. Possible explanation: GridWorld rewards the mote for
   exploring and moving through space, but LogicWorldLarge requires focused
   variable-toggling — the GridWorld-learned exploration bias is detrimental.

5. **Zero completion on hazard_large** (even with same-domain pretrain)
   establishes that 30 eval ticks is insufficient for the 15-node hazard
   graph. This is a ceiling effect, not a failure of transfer. A longer eval
   horizon or the small hazard domain (where completion is possible) would
   show different results.

**Ruling:** Phase R4 extends the empirical scope of TAIS but does not change
the core paper claims. The negative Grid→Logic_large result should be noted
as a boundary condition. The three_domain→rules_chain_long result adds to the
diversity-benefit evidence. See `docs/PAPER_RESULT_AUDIT.md` (Phase R4
Addendum) for audit status.

## Artifacts

- `docs/PHASE_R4_LARGE_DOMAIN_TRANSFER_REPORT.md` — this document
- `results/phase_r/large_domain_transfer/large_domain_transfer.{json,csv,md,txt}` — 100-seed results
- `experiments/phase_r/large_domain_transfer.py` — runner
- `tais_core/domains/logic.py` — `LogicWorldLarge`, `make_logic_graph_large()`
- `tais_core/domains/hazard.py` — `HazardGraphWorldLarge`, `make_hazard_graph_large()`
- `tais_core/domains/rules.py` — `RuleWorldChainLong`, `make_rule_graph_chain_long()`
- `tais_core/domains/registry.py` — `logic_large`, `hazard_large`, `rules_chain_long` entries
- `tais_core/dsl/specs/{logic_large,hazard_large,rules_chain_long}.yaml` — DSL specs
- `tests/test_large_domains.py` — 18 domain tests
- `tests/test_large_domain_transfer_runner.py` — 5 runner tests
