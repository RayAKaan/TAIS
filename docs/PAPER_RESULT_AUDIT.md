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
**Commit:** TBD  
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
