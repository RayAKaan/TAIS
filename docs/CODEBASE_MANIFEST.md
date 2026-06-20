# TAIS Codebase Manifest

This file mirrors the actual on-disk layout of the repository.
Updated 2026-06-20 to reflect Phase F2/R2–R8/7–8 state.

## Core framework (`tais_core/`)

### Substrate
- `reality.py` — Entity, Relation, RealityGraph, Transformation, Constraint, Consequence, WorldInterface.
- `mote.py` — `UniversalMote`: domain-agnostic agent with observe/analogize/predict/act/learn cycle, Phase 7 CulturalMemory, Phase 8 Active Planning.
- `memory.py` — `EpisodicMemory`, `PatternMemory`, `SymbolicMemory`, `CulturalMemory`, `PredictionEngine`, `MoteMemory`.
- `memory_attentiondb.py` — AttentionDB-backed episodic memory (drop-in replacement for `MoteMemory`).
- `attentiondb_client.py` — Thin REST client for the Rust AttentionDB vector engine.
- `speech.py` — Lexicon, SpeechGenome, Utterance, RepairSignal, SpeechOrgan.
- `role_learning.py` — Learned role compatibility prototype (Phase R6, experimental alternative to hand-coded table).
- `planning.py` — Hierarchical planner with backward chaining, plan library, rollback.
- `metacognition.py` — Metacognitive engine: prediction tracking, exploration modulation.
- `causal.py` — Causal reasoning engine: Delta-P with temporal windowing and counterfactuals.
- `llm_grounding.py` — NL-to-RealityGraph translation layer (keyword-matching stub).
- `engine_policy.py` — Engine selection policy based on action vocabulary.

### Domains (`tais_core/domains/`)
- `gridworld.py` — GridGraphWorld (spatial survival, the original validation domain).
- `sequences.py` — SequenceWorld (prediction / pattern completion).
- `rules.py` — RuleWorld with Phase 2 TARGET-fact variants (Easy, Chain, Distractor).
- `hazard.py` — HazardGraphWorld (intermediate-distance transfer, Phase 4).
- `logic.py` — LogicWorld (propositional constraint satisfaction, Phase 5).
- `negosim.py` — Multi-agent negotiation and resource trading.
- `codesynt.py` — AST-based code synthesis and refactoring.
- `sciex.py` — Scientific experiment design and hypothesis testing.
- `webnav.py` — Autonomous web navigation and form filling.
- `registry.py` — `load_domain(name)` registry mapping names to built-in specs.

### DSL (`tais_core/dsl/`)
- `parser.py` — `load_spec()`: loads YAML/JSON domain specs.
- `validator.py` — `validate_spec()`: validates spec structure.
- `codegen.py` — `load_domain_from_spec()`: generates domain worlds from specs.

### Baselines (`tais_core/baselines/`)
- `random_agent.py` — `RandomAgent`: picks uniformly among valid actions.
- `heuristic_agent.py` — `HeuristicAgent`: hand-coded preferences by op type.
- `tabular_q_agent.py` — `TabularQAgent`: Q-learning with graph-structural state keys.
- `llm_prompt_agent.py` — `LLMPromptAgent`: stub, disabled by default.

### Experiment framework (`tais_core/experiments/`)
- `suite.py` — `ExperimentSuite`: runs paired trials across conditions, seeds, horizons.
- `results.py` — `ExperimentResults` / `TrialRecord`: structured output types.
- `report.py` — `ExperimentReport`: pretty-print, paired t-test, Cohen's d.
- `metrics.py` — `Metric` dataclass and `summarize_paired()`.
- `condition.py` — `Condition`: name + pretrain domains + engine flags.
- `provenance.py` — `capture_provenance()`: git hash, timestamp, platform.

### Visualization (`tais_core/viz/`)
- `ablation_radar.py` — Radar charts for ablation comparisons.
- `transfer_heatmap.py` — Transfer heatmaps from summary rows.
- `trajectory.py` — Mote trajectory recording (HTML/JSON export).
- `scaling.py` — Scaling-curve plots (domain count / horizon vs transfer delta).
- `lexicon.py` — Pairwise lexicon agreement matrices.
- `common.py` — Shared CSV/JSON helpers, repo-root finder.

## Swarm V6 (`tais_swarm_v6/`)
- `engine/config.py` — Typed `SwarmConfig`, `WorldConfig`, presets.
- `engine/spatial.py` — Quadtree + spatial hash for unified range queries.
- `engine/thermodynamics.py` — Real thermodynamic engine (energy is a hard constraint).
- `engine/ecosystem.py` — Cellular automata ecosystem (diffusion, seasons, carrying capacity).
- `engine/events.py` — Typed event bus with subscriber pattern.
- `engine/persistence.py` — SQLite persistence (WAL mode, time-series logging).
- `engine/world.py` — WorldV6 state container with landmarks.
- `engine/core.py` — Core tick loop integrating world, motes, event bus, persistence.
- `agents/mote_v6.py` — MoteV6: integrates all V6 cognitive systems.
- `agents/memory_v6.py` — Temporal memory (episodic narrative, Bayesian decay).
- `agents/trust_v6.py` — Vector trust and reputation (gossip protocol).
- `agents/speech_v6.py` — Enhanced speech (grammar innovation, creole formation).
- `agents/metacognition.py`, `agents/causal.py`, `agents/planning.py` — Engines.
- `api/server.py` — FastAPI + WebSocket server.
- `experiments/runner.py`, `experiments/analysis.py` — Batch runner and analysis.
- `frontend/` — React UI (SwarmCanvas, AnalysisOverlay, TeachingPanel, MoteInspector, useTAISStream hook).

## Experiments (`experiments/`)

| Module | Description |
|--------|-------------|
| `ablation_runner.py` | Ablation against `first_apply_implication_tick` |
| `cross_domain_transfer.py` | GridWorld → RuleWorld transfer (original) |
| `statistical_replication.py` | 200-seed paired replication |
| `choose_action_design_sweep.py` | Phase 1.6: score-formula sweep |
| `predict_calibration_sweep.py` | Phase 1.5: blend-weight sweep |
| `predict_diagnostic.py` | Phase 1.5: PredictionEngine diagnostics |
| `hazard_transfer_runner.py` | Phase 4: Grid → Hazard |
| `logic_transfer_runner.py` | Phase 5: Grid → Logic |
| `codesynt_transfer_runner.py` | Rule → CodeSynt transfer |
| `webnav_transfer_runner.py` | Grid → WebNav transfer |
| `negosim_fused_transfer_runner.py` | Grid+Rules+Code+SciEx → NegoSim |
| `sciex_fused_transfer_runner.py` | Grid+Rules+Code → SciEx |
| `cognitive_transfer_runner.py` | Phase A: engine-addition impact |
| `speech_token_portability.py` | Phase A: ka→DANGER benchmark |
| `research_stress_test.py` | Phase 6: multi-source stress tests |
| `stress_test.py` | Easy-to-extremely-hard stress suite |
| `realworld_tests.py` | Real-world capability tests |
| `multiagent_test.py` | Multi-agent collaboration tests |
| `phase_c_logic_transfer_suite.py` | Phase C: logic-suite CLI runner |
| `phase_r/baseline_comparison.py` | Phase R3: TAIS vs baselines |
| `phase_r/large_domain_transfer.py` | Phase R4: larger synthetic domains |
| `phase_r/role_ontology_robustness.py` | Phase R2: ontology ablation |
| `phase_r/prediction_gating_sweep.py` | Phase R5: prediction-gated transfer |
| `phase_r/learned_role_compatibility.py` | Phase R6: learned vs hand-coded |
| `phase_f2/role_balanced_curriculum.py` | F2 Exp 1: balanced role exposure |
| `phase_f2/repair_convergence.py` | F2 Exp 2: speech-repair alignment |
| `phase_f2/domain_count_scaling.py` | F2 Exp 3: domain-count scaling |
| `phase_f2/grid_logic_1000_replication.py` | F2 Exp 4: 1000-seed replication |
| `phase_f2/generate_paper_figures.py` | F2 paper figure generation |
| `phase_d/` | Killer-experiment suite (cognitive_contribution, composition, curriculum, reverse_transfer, scaling_law, run_all) |
| `phase_e/generate_figures.py` | Phase D/E paper figure generation |

## Tests (`tests/`)
**381 test functions** across 32 files. Run with `pytest tests/` or `python -m unittest discover -s tests`.

Key test files:
- `test_core.py` — RealityGraph, mote stepping, memory, planning primitives.
- `test_base_validation.py` — Mote runs N domains battery.
- `test_transfer_e2e.py` — End-to-end Grid → Rule transfer.
- `test_cross_domain_transfer.py` — Graph analogy / pattern matching.
- `test_cognitive_engines.py` — Metacog/causal/planning integration.
- `test_v6_integration.py` — V6 cognitive integration.
- `test_dsl.py` — DSL parser/validator/codegen.
- `test_experiment_framework.py` — Suite, results, report.
- `test_runner_rng_isolation.py` — RNG isolation verification.
- `test_baselines.py` — Random/Heuristic/TabularQ/LLM agents.
- `test_global_fix.py` — Domain-isolated stats + gating.
- Domain tests: `test_hazardworld.py`, `test_logicworld.py`, `test_negosim.py`, `test_codesynt.py`, `test_sciex.py`, `test_webnav.py`, `test_ruleworld_v2.py`, `test_large_domains.py`.
- Experiment-runner tests: `test_phase_f2_runners.py`, `test_phase_d_runners.py`, `test_large_domain_transfer_runner.py`, `test_prediction_gating.py`, `test_prediction_calibration.py`, `test_role_ontology_robustness.py`.

## Paper (`paper/`)
- `grtl_foundational_paper.tex` — LaTeX source for the TAIS GRTL paper.
- `references.bib` — Bibliography.
- `figures/` — Rendered PNG figures (baseline, scaling, ontology, curriculum, repair, domains, replication).

## Scripts (`scripts/`)
- `generate_paper_figures.py` — Generate all paper figures from result artifacts.
- `audit_paper_results.py` — Scan repo, verify every claimed result has backing artifact.
- `cleanup_tracked_artifacts.sh` — Remove accidentally-tracked generated artifacts.

## Reports (`docs/`)
41 markdown files covering Phase 0–F2, R2–R8, A–E, and architecture upgrades.
- `PHASE7_8_LOAD_BEARING_ARCHITECTURE_REPORT.md` — Latest: Phase 7 (CulturalMemory) and Phase 8 (Active Planning).

## Generated artifacts (not committed)
- `results/*.{csv,json,txt}` — Experiment outputs. Regenerate with experiment scripts.
- `colonies/*.json` — Swarm save files (swarm_v5 legacy).
- `runs/<timestamp>_*/` — Per-run output (Phase 0.2 convention).
- `tais_v6_simulation.db` — SQLite persistence database (V6).

## Reproducing the test suite
```bash
pip install -e .[dev]
make pytest        # or: pytest tests/
```
Expected: **381 tests passing**.

## Reproducing the ablation (Phase 1 v2)
```bash
mkdir -p results
PYTHONPATH=. python experiments/ablation_runner.py \
    --seeds 200 --pretrain 20 --eval 12 \
    --output results/ablation_v2_eval12.txt

# Horizon sweep:
for E in 12 30 50; do
  PYTHONPATH=. python experiments/ablation_runner.py \
      --seeds 200 --pretrain 20 --eval $E \
      --output results/ablation_v2_eval${E}.txt
done
```
