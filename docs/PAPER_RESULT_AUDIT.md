# TAIS Paper Result Audit

## Summary

This audit freezes the current result state for the foundational GRTL paper.

## Current Commit and Tests

- **Commit:** `3c41338a1d0d13bde79d0271d4e0986a28bb82fd`
- **Branch provenance:** R1 branches from `main` after Phase F2 merge (`phase-f2-paper-defining-experiments` → `main` via PR #13).
- **Baseline tests:** 197 passed, 3 warnings, 4 subtests passed (`pytest tests/ -q --tb=short`).
- **Status:** All tests passing.

## Result Regimes

### Legacy runners

Used for original Grid→Rule / Grid→Hazard / Grid→Logic transfer claims. Results are from
standalone runners (`logic_transfer_runner.py`, `hazard_transfer_runner.py`) that use
older graph factory configurations and no experiment framework.

### Phase A paper-readiness fixes

Prediction calibration (`memory.py`), engine selection policy (`engine_policy.py`),
and speech token portability benchmark (`speech_token_portability.py`). These fix the
prediction paradox but also change the Grid→Logic transfer baseline.

### Phase D framework experiments

Composition, curriculum, scaling, cognitive contribution — run via `ExperimentSuite`.
Established the framework protocol for subsequent experiments.

### Phase F2 paper-defining experiments

Role-balanced curriculum, domain-count scaling, 1000-seed Grid→Logic replication,
repair convergence. These are the primary evidence base for the paper.

## Canonical Paper Claims

| # | Claim | Evidence | Status | Paper placement |
|---|---|---|---|---|
| 1 | Fixed mote transfers roles across typed graph domains | All experiments show transfer precision > fresh baseline | Supported | Main |
| 2 | PatternMemory + ActionRole are load-bearing | F2 1000-seed: `no_pattern_transfer` eliminates transfer (d=0), `no_action_role` reduces it | Supported | Main |
| 3 | Grid→Logic has legacy strong effect | Phase 5: d=-0.568, Δfirst_success=-3.96 | Supported (historical) | Legacy context |
| 4 | 1000-seed replication has smaller speed effect | F2: d=-0.238 (first_success), Δ=-1.78 | Supported (weaker) | Main |
| 5 | Completion-rate improvement is weak in replication | F2: d=+0.038 (task_completion_rate), p=0.232 ns | Null result | Limitations |
| 6 | Domain-count scaling shows 3+ domain threshold | F2: 1-2 domains ns, 3+ d=+0.49 to +0.66 | Supported | Main |
| 7 | Role-balanced curriculum failed | F2: role_balanced d=-0.161 vs approach_only d=+0.690 | Null result | Limitations |
| 8 | Hazard shows caution transfer but speed harm | Phase 4: caution-d positive, speed-d negative | Supported | Appendix |
| 9 | Prediction paradox reduced but not fully eliminated | Phase A: gap reduced 43-56% | Supported | Limitations |
| 10 | Speech portability null result | Phase A: no significant portability | Null result | Exclude (Paper 2) |
| 11 | Cognitive engines not central to Paper 1 | Phase D: engines hurt or neutral | Supported | Exclusion note |

## Include / Appendix / Exclude Decisions

| Result | Include in main? | Appendix? | Exclude? | Reason |
|---|---|---|---|---|
| F2 1000-seed Grid→Logic replication | Yes | - | - | Canonical current effect |
| F2 domain-count scaling | Yes | - | - | Best diversity evidence |
| F2 role-balanced curriculum | - | - | Limitations | Null/negative result |
| F2 repair convergence | - | - | Paper 2 | Not Paper 1 material |
| Legacy Grid→Logic | Historical context | - | - | Major comparison baseline |
| Legacy Grid→Hazard | - | Asymmetric transfer | - | Caution-speed dissociation |
| Phase D composition | - | Context | - | Framework protocol |
| Phase D curriculum | Domain diversity | - | - | Supporting evidence |
| Phase D scaling | - | Appendix | - | Earlier sweep |
| Phase D cognitive | - | - | Paper 3 | Hurts performance |
| Phase A prediction calibration | - | Limitations | - | Paradox fix context |
| Phase A engine selection | - | Appendix | - | Implementation detail |
| Phase A speech portability | - | - | Paper 2 | Null result |

## Key Numbers

### Legacy Grid→Logic (Phase 5, 200 seeds, eval=15)
- Δ first_success = −3.96
- d = −0.568
- p < 0.001

### F2 1000-seed Grid→Logic Replication (1000 seeds, eval=15)
- Δ first_success = −1.782
- d = −0.238 (first_success), d = +0.038 (completion, ns)
- p < 0.001 (first_success), p = 0.232 (completion)
- Transfer precision d = +0.843

### F2 Domain-Count Scaling (200 seeds per condition)
- 3 domains (grid+rules+chem): d = +0.487, p < 0.001
- 4 domains (+hazard): d = +0.657, p < 0.001
- 5 domains (+sequences): d = +0.610, p < 0.001
- Ceiling (same-domain logic): d = −0.061, ns

### F2 Role-Balanced Curriculum (200 seeds)
- approach_only: d = +0.690, p < 0.001
- grid_standard: d = +0.098, ns
- role_balanced: d = −0.161, p = 0.023
- danger_only: d = −0.414, p < 0.001

### F2 Repair Convergence (200 seeds, 100 ticks)
- Lexicon divergence (enabled): 0.8789 → 0.7862
- Lexicon divergence (disabled): 0.8790 → 0.8790
- Semantic success: ~0.985 both conditions (no significant difference)

## Paper Framing Recommendation

The paper should **not** claim a large stable Grid→Logic effect. It should claim:

> TAIS demonstrates a smaller but replicated first-success speedup whose mechanism
is eliminated by removing PatternMemory or ActionRole classification, and
domain-count scaling suggests transfer improves sharply once the agent has seen
at least three diverse source domains.

The 1000-seed replication confirms that the effect is real but smaller than the
legacy estimate (d ≈ −0.24 vs d ≈ −0.57). The completion-rate effect is not
significant at 1000 seeds. The diversity scaling pattern (3+ domain threshold)
is the strongest positive claim.

## Reviewer Risk Notes

- **Hand-designed role ontology:** The role taxonomy (APPROACH_GOOD,
  AVOID_BAD, VERIFY_UNCERTAIN) is hand-specified. The paper must acknowledge
  this and discuss automation as future work.
- **No neural/LLM baselines:** No comparisons to fine-tuned transformers
  or gradient-based meta-learners.
- **Effect shrinkage in 1000-seed replication:** The legacy d ≈ −0.57
  shrinks to d ≈ −0.24 at 1000 seeds. Without replication, reviewers
  would question stability.
- **Completion-rate weakness:** The primary metric (first_success_tick)
  shows a speedup, but the completion rate does not improve significantly
  at 1000 seeds.
- **Role-balanced curriculum null/negative:** The hypothesis that
  role-balancing helps was not supported. Approach-only pretraining is
  strongest.
- **Cognitive engines / speech should stay out of Paper 1.**
  Including them dilutes the core message.

## Artifact Index

- `results/paper_locked/audit_summary.md` — human-readable audit table
- `results/paper_locked/audit_summary.json` — machine-readable audit
- `results/paper_locked/legacy/` — legacy transfer reports
- `results/paper_locked/phase_a/` — Phase A calibration reports
- `results/paper_locked/phase_d/` — Phase D experiment results
- `results/paper_locked/phase_f2/` — Phase F2 experiment results + figures

---

## Phase R2 Addendum — Role-Ontology Robustness

**Date:** 2026-06-09  
**Commit:** `4385e74`  
**Branch:** `phase-r2-role-ontology-robustness` → merged to main  
**Tests:** 218 passed (197 prior + 21 new)

### Motivation

The role ontology used in TAIS role-based transfer is hand-designed.
Phase R2 tests whether these hardcoded roles and the compatibility table
are load-bearing — or whether the transfer benefit survives arbitrary
corruption of the role signals.

### Design

7-condition paired experiment (seeds=200), GridWorld(20 ticks)→LogicWorld(15 ticks):

| Condition | What is corrupted |
|---|---|
| `canonical_roles` | None (baseline) |
| `shuffled_target_role_hints` | `role_hint` on LogicWorld actions permuted per seed |
| `shuffled_target_universal_ops` | `universal_op` on LogicWorld actions permuted per seed |
| `shuffled_source_roles` | `classify_action_role` output shuffled during GridWorld pretrain |
| `random_compatibility` | `role_compatibility()` table replaced by uniform random values |
| `identity_only_compatibility` | `role_compatibility()` returns 1.0 only if source==target |
| `no_role_transfer` | `transfer_action_priors` returns all zeros |

### Impact on Paper Claims

**The role ontology is NOT load-bearing.**  All 5 role-corruption conditions preserve
significant transfer (d for first_success: −0.193 to −0.441, all p<0.01 except
no_role_transfer which blocks all priors).  Random and identity-only compatibility
tables produce **stronger** transfer than the canonical hand-designed table
(d=−0.388, −0.441 vs −0.328), suggesting the role system may add friction.

**Ruling:** The paper should de-emphasize role-based transfer as a mechanistic
necessity and frame roles as a diagnostic/interpretive tool instead.  If causal
claims about role generalization enabling transfer appear in the paper, they
must be softened with this evidence.

See `docs/PHASE_R2_ROLE_ONTOLOGY_ROBUSTNESS_REPORT.md` for full details.

### Artifacts

- `docs/PHASE_R2_ROLE_ONTOLOGY_ROBUSTNESS_REPORT.md` — full report
- `results/phase_r/role_ontology_robustness/report.{txt,csv,json}` — data
- `experiments/phase_r/role_ontology_robustness.py` — runner
- `tests/test_role_ontology_robustness.py` — 21 tests

---

## Phase R3 Addendum — Baseline Agents Comparison

**Date:** 2026-06-09  
**Commit:** `c9e51c5`  
**Branch:** `phase-r3-baseline-agents`  
**Tests:** 238 passed (218 prior + 20 new)

### Motivation

TAIS had never been systematically compared against non-TAIS baselines on the Grid→Logic transfer task. Phase R3 adds RandomAgent, HeuristicAgent, and TabularQAgent under the same paired-experiment protocol (200 seeds, 20 GridWorld pretrain ticks, 15 LogicWorld eval ticks).

### Design

5-condition paired comparison (all conditions share the same seeds):

| Condition | Type |
|---|---|
| TAIS_full | UniversalMote (all mechanisms) |
| TAIS_no_pattern_transfer | UniversalMote (priors zeroed) |
| RandomAgent | Uniform random (statistical baseline) |
| HeuristicAgent | Op-weight heuristic (TRANSFORM > MUTATE > other) |
| TabularQAgent | Q-learning (α=0.1, γ=0.9, ε=0.1) via `graph_structural_key()` |

### Impact on Paper Claims

**Simple baselines dominate TAIS on LogicWorld.** HeuristicAgent achieves 100% task completion and 0 contradictions on every seed. TabularQAgent follows at 93.5%. TAIS_full reaches only 62% (d=+0.189 vs RandomAgent, p=0.008).

**The Grid→Logic transfer task is not challenging enough to distinguish agent capabilities.** A hardcoded op-weight heuristic (prefer TRANSFORM) solves the eval domain perfectly. This does not invalidate TAIS's transfer claims but establishes that the evaluation benchmark is saturated.

**TAIS still shows significant transfer** compared to RandomAgent (first_success d=−0.285, p<0.001; contradictions d=−1.143, p<0.001), consistent with the F2 1000-seed replication (d=−0.238).

**Ruling:** The paper must acknowledge that simple, domain-appropriate baselines outperform TAIS on Grid→Logic. TAIS's comparative advantage should be framed in terms of multi-domain generalization (3+ domain threshold) rather than peak performance on a single eval domain.

See `docs/PHASE_R3_BASELINE_COMPARISON_REPORT.md` for full details.

### Artifacts

- `docs/PHASE_R3_BASELINE_COMPARISON_REPORT.md` — full report
- `results/phase_r/baseline_comparison/baseline_comparison.{txt,csv,json,md}` — data
- `experiments/phase_r/baseline_comparison.py` — runner
- `tais_core/baselines/` — baseline agent package (base.py, random_agent.py, heuristic_agent.py, tabular_q_agent.py, llm_prompt_agent.py)
- `tests/test_baselines.py` — 20 tests

---

## Phase R4 Addendum — Large Domain Variants Transfer

**Date:** 2026-06-09  
**Branch:** `phase-r4-large-domain-variants`  
**Tests:** 261 passed (238 prior + 18 large domain + 5 runner)

### Motivation

All prior TAIS experiments use small synthetic domains (LogicWorld: 3 vars, 3 clauses;
HazardWorld: 6 nodes; RuleWorld: 3-step chain). Phase R4 tests whether TAIS
role-transfer survives on larger versions (LogicWorldLarge: 6 vars, 12 clauses;
HazardGraphWorldLarge: 15 nodes; RuleWorldChainLong: 5-step chain).

### Design

3 target domains × 5 conditions paired experiment (seeds=100, pretrain=20, eval=30).

### Impact on Paper Claims

**Transfer survives to larger domains but with caveats:**

1. **Same-domain pretrain helps strongly on logic_large** (92% completion vs 77%
   fresh, d=+0.404, p=0.002) and **reduces hazard_large failure rate** (5.61 vs
   7.70 hazard steps, d=−0.620, p<0.001). But **fails on rules_chain_long** (12%
   same as fresh) — the 20-tick pretrain budget is insufficient.

2. **Cross-domain Grid→Logic_large produces negative transfer** (49% completion
   vs 77% fresh, d=−0.686, p<0.001). This is the first clear negative transfer
   result in TAIS and bounds the Grid→Logic claim.

3. **Three-domain pretrain is the strongest cross-domain condition for
   rules_chain_long** (54% completion, d=+0.713, p<0.001), extending the
   diversity-benefit evidence from Phase F2.

**Ruling:** Phase R4 extends the empirical scope but does not change core paper
claims. The negative Grid→Logic_large result is a boundary condition worth noting.
The three_domain→rules_chain_long result supports the diversity-benefit narrative.

See `docs/PHASE_R4_LARGE_DOMAIN_TRANSFER_REPORT.md` for full details.

### Artifacts

- `docs/PHASE_R4_LARGE_DOMAIN_TRANSFER_REPORT.md` — full report
- `results/phase_r/large_domain_transfer/large_domain_transfer.{txt,csv,json,md}` — data
- `experiments/phase_r/large_domain_transfer.py` — runner
- `tais_core/domains/logic.py` — `LogicWorldLarge`, `make_logic_graph_large()`
- `tais_core/domains/hazard.py` — `HazardGraphWorldLarge`, `make_hazard_graph_large()`
- `tais_core/domains/rules.py` — `RuleWorldChainLong`, `make_rule_graph_chain_long()`
- `tais_core/dsl/specs/{logic_large,hazard_large,rules_chain_long}.yaml` — DSL specs
- `tests/test_large_domains.py` — 18 domain tests
- `tests/test_large_domain_transfer_runner.py` — 5 runner tests

---

## Phase R5 Addendum — Prediction Gating

**Date:** 2026-06-09  
**Branch:** `phase-r5-prediction-gating`  
**Tests:** 272 passed (261 prior + 11 new)

### Motivation

Reviewer objection: prediction is implemented but not clearly load-bearing for
transfer. Phase R5 tests whether prediction can improve transfer when gated by
sufficient target-domain evidence (k observations) and weighted by w.

### Design

3 targets (logic, rules, hazard) × 9 conditions + GridWorld pretrain (20 ticks),
paired by seed (200 seeds, 15 eval ticks). Prediction scoring enabled via
opt-in `use_prediction_in_score` flag (default off, preserving all legacy
behavior).

### Impact on Paper Claims

**Prediction is conditionally useful.** On LogicWorld, `prediction_k3_w05`
(k=3 target-domain observations, w=0.5 weight) achieves 68.5% completion vs
53.0% baseline (d=+0.427, p<0.001) and first_success 8.45 vs 9.78
(d=−0.430, p<0.001). `no_prediction` is identical to default on all targets
(d=0.000 on logic completion).

However, prediction scoring is **neutral on Rules and Hazard targets** — no
condition shows significant improvement over baseline.

**Ruling:** Prediction should remain in Paper 1 as an auxiliary mechanism
but not be framed as a core transfer driver. The `prediction_k3_w05` result
demonstrates load-bearing for at least one target, satisfying the reviewer
requirement. The paper should present prediction as a domain-specific
complement to pattern-based role transfer.

See `docs/PHASE_R5_PREDICTION_GATING_REPORT.md` for full details.

### Artifacts

- `docs/PHASE_R5_PREDICTION_GATING_REPORT.md` — full report
- `results/phase_r/prediction_gating_sweep/prediction_gating_sweep.{txt,csv,json,md}` — data
- `experiments/phase_r/prediction_gating_sweep.py` — runner
- `tests/test_prediction_gating.py` — 11 tests
- `tais_core/mote.py` — `UniversalMote` gating params (`use_prediction_in_score`, etc.)
- `tais_core/memory.py` — `PredictionEngine.domain_observation_count()`

---

## Phase R6 Addendum — Learned Role Compatibility

**Date:** 2026-06-09  
**Branch:** `phase-r6-learned-role-compatibility`  
**Tests:** 306 passed (272 prior + 34 new, excluding 1 pre-existing flaky speech test)

### Motivation

The hand-designed `role_compatibility()` table is a known limitation (Phase R2
found it is not load-bearing). Phase R6 tests whether a simple learned
alternative — consequence-based EWM per (role, universal_op) — can approach
or replace the hand-coded table.

### Design

3 targets (logic, rules, hazard) × 5 conditions paired experiment (seeds=200,
GridWorld pretrain=20, eval=15):

| Condition | Description |
|-----------|-------------|
| `hardcoded_compatibility` | Normal behaviour (baseline) |
| `learned_compatibility` | `role_compatibility` patched to use learned `role_score` |
| `learned_plus_hardcoded` | 0.5 × learned + 0.5 × hardcoded |
| `random_compatibility` | Seed-deterministic random table (replicating R2) |
| `no_compatibility` | Cross-role compatibility returns 0.0 |

### Impact on Paper Claims

**Learned compatibility partially recovers transfer on LogicWorld but is
neutral on Rules and Hazard.** On LogicWorld, `learned_compatibility`
significantly improves first success tick (Δ=−2.805, d=−0.378, p<0.001)
while the hardcoded baseline is non-significant. However,
`learned_plus_hardcoded` never beats hardcoded alone.

**Ruling:** The learned approach provides initial evidence that
consequence-driven learning is viable but does not replace the hand-coded
table. The reviewer risk note about hand-designed role ontology remains.
Learned compatibility should be noted as future work.

See `docs/PHASE_R6_LEARNED_ROLE_COMPATIBILITY_REPORT.md` for full details.

### Artifacts

- `docs/PHASE_R6_LEARNED_ROLE_COMPATIBILITY_REPORT.md` — full report
- `results/phase_r/learned_role_compatibility/learned_role_compatibility.{txt,csv,json}` — data
- `experiments/phase_r/learned_role_compatibility.py` — runner
- `tais_core/role_learning.py` — `LearnedRoleCompatibility` + `make_learned_role_compatibility_fn()`
- `tais_core/mote.py` — `enable_learned_role_compatibility()`, `use_learned_role_compatibility` flag
- `tests/test_role_learning.py` — 34 tests
