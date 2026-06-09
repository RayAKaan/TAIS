# Paper Result Audit

- **Generated at:** 2026-06-09T15:54:17.068036+00:00
- **Commit:** 8541acada2603dbe0a627ea99084c3ae0b937055

## Summary Table

| ID | Phase | Runner | Artifact | Exists | Paper Status | Notes | Key Metrics |
|----|-------|--------|----------|--------|-------------|-------|-------------|
| legacy_grid_logic | Phase 5 legacy | experiments/logic_transfer_runner.py | docs/PHASE5_LOGIC_TRANSFER_REPORT.md | Yes | include_legacy_context | Strong legacy Grid->Logic result; not directly comparable to F2. | - |
| legacy_grid_hazard | Phase 4 legacy | experiments/hazard_transfer_runner.py | docs/PHASE4_HAZARD_TRANSFER_REPORT.md | Yes | include_as_asymmetric_transfer | Caution transfer positive; task-speed negative. | - |
| phase_a_prediction_calibration | Phase A paper readiness | experiments/logic_transfer_runner.py | docs/PHASE_A_PREDICTION_CALIBRATION_REPORT.md | Yes | include_limitations | Prediction paradox reduced but not fully eliminated. | - |
| phase_a_engine_selection | Phase A paper readiness | experiments/phase_d/cognitive_contribution.py | docs/PHASE_A_ENGINE_SELECTION_REPORT.md | Yes | appendix_or_exclude_paper1 | Engine policy implemented; not central to Paper 1. | - |
| phase_a_speech_token | Phase A paper readiness | experiments/speech_token_portability.py | docs/PHASE_A_SPEECH_TOKEN_PORTABILITY_REPORT.md | Yes | exclude_paper1 | Null speech result; Paper 2 material. | - |
| phase_d_composition | Phase D | experiments/phase_d/composition.py | results/phase_d/composition/composition.csv | Yes | appendix_or_context | Framework protocol; do not mix with legacy table. | - |
| phase_d_curriculum | Phase D | experiments/phase_d/curriculum.py | results/phase_d/curriculum/curriculum.csv | Yes | include_as_domain_diversity | Strong 3-domain curriculum results. | - |
| phase_d_scaling | Phase D | experiments/phase_d/scaling_law.py | results/phase_d/scaling_law/scaling_summary.csv | Yes | appendix | Earlier scaling sweep. | - |
| phase_d_cognitive | Phase D | experiments/phase_d/cognitive_contribution.py | results/phase_d/cognitive_contribution/cognitive_contribution.csv | Yes | exclude_paper1_or_limitations | Cognitive engines hurt; Paper 3 material. | - |
| phase_f2_role_balanced | Phase F2 | experiments/phase_f2/role_balanced_curriculum.py | results/phase_f2/role_balanced_curriculum.csv | Yes | include_negative_result | Role-balanced hypothesis failed; approach-only strongest. | grid_standard.first_task_success_tick: d=-0.328283; grid_standard.task_completion_rate: d=0.097552; grid_standard.transfer_uses: d=3.787306; grid_standard.transfer_precision: d=0.930636; approach_only.first_task_success_tick: d=-1.234236 |
| phase_f2_domain_count | Phase F2 | experiments/phase_f2/domain_count_scaling.py | results/phase_f2/domain_count_scaling.csv | Yes | include_main | Best current diversity evidence. | three_grid_rules_chem.first_task_success_tick: d=-0.811404; three_grid_rules_chem.task_completion_rate: d=0.487296; three_grid_rules_chem.transfer_uses: d=2.650656; three_grid_rules_chem.transfer_precision: d=0.898494; four_grid_rules_chem_hazard.first_task_success_tick: d=-1.063064 |
| phase_f2_repair | Phase F2 | experiments/phase_f2/repair_convergence.py | results/phase_f2/repair_convergence.json | Yes | exclude_paper1 | Paper 2 material; modest divergence reduction. | - |
| phase_f2_grid_logic_1000 | Phase F2 | experiments/phase_f2/grid_logic_1000_replication.py | results/phase_f2/grid_logic_1000_replication.csv | Yes | include_main | Canonical current Grid->Logic replication. | full.first_task_success_tick: d=-0.238491; full.task_completion_rate: d=0.037826; full.transfer_uses: d=3.318805; full.transfer_precision: d=0.842508; no_action_role.first_task_success_tick: d=0.028222 |
| phase_r3_baseline_comparison | Phase R3 | experiments/phase_r/baseline_comparison.py | results/phase_r/baseline_comparison/baseline_comparison.csv | Yes | include_as_limitation | HeuristicAgent and TabularQAgent outperform TAIS on Grid->Logic evaluation. | - |
| phase_r4_large_domain_transfer | Phase R4 | experiments/phase_r/large_domain_transfer.py | results/phase_r/large_domain_transfer/large_domain_transfer.json | Yes | appendix_or_future_work | Transfer survives to larger domains but Grid->Logic_large shows negative transfer. | - |
| phase_r5_prediction_gating | Phase R5 | experiments/phase_r/prediction_gating_sweep.py | results/phase_r/prediction_gating_sweep/prediction_gating_sweep.csv | Yes | include_appendix_or_limitations | Prediction is conditionally useful on logic (d=+0.427) but neutral on rules/hazard. | no_prediction.first_task_success_tick: d=0.007937; no_prediction.task_completion_rate: d=0.0; no_prediction.transfer_uses: d=0.113284; no_prediction.transfer_precision: d=0.111782; no_prediction.hazard_steps: d=0.0 |
| phase_r6_learned_role_compatibility | Phase R6 | experiments/phase_r/learned_role_compatibility.py | results/phase_r/learned_role_compatibility/learned_role_compatibility.csv | Yes | future_work_or_limitations | Learned compatibility partially recovers transfer on logic (d=-0.378) but neutral on rules/hazard. Hand-coded table still competitive. | - |
