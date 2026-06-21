# TAIS: Thought-Assisted Intelligence Substrate

**Grounded Role-Transfer Learning Without Pretrained Representations**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)
[![Tests](https://img.shields.io/badge/tests-369%20passing-brightgreen)](tests/)

No LLM (for reasoning). No pretrained model. No shared embedding space. No gradient descent. No backpropagation.

TAIS is a **domain-agnostic agent framework** where a single `UniversalMote` learns functional action roles across typed graph domains and transfers them without any pretrained representations, large language models, or gradient-based learning. The core mechanism — **Grounded Role-Transfer Learning (GRTL)** — enables agents to learn abstract roles like `APPROACH_GOOD`, `AVOID_BAD`, and `TRANSFORM_TOWARD_GOAL` in toy environments and re-apply them to hand-authored benchmark tasks and genuinely grounded domains.

---

## Table of Contents

- [Abstract](#abstract)
- [Key Contributions](#key-contributions)
- [Theory and Motivation](#theory-and-motivation)
- [Architecture](#architecture)
  - [UniversalMote](#1-the-universalmote-taiscoremotepy)
  - [RealityGraph](#2-the-realitygraph-taiscorerealitypy)
  - [Memory Hierarchy](#3-memory-hierarchy)
  - [Cognitive Engines](#4-cognitive-engines)
  - [Engine Selection Policy](#5-engine-selection-policy)
- [Domains](#domains)
- [Results](#results)
  - [Legacy Transfer](#legacy-transfer-phase-4-5)
  - [Phase D — Experiment Framework](#phase-d--experiment-framework)
  - [Phase F2 — Paper-Defining Experiments](#phase-f2--paper-defining-experiments)
  - [Phase R — Robustness and Ablation](#phase-r--robustness-and-ablation)
- [Installation](#installation)
- [Quickstart](#quickstart)
- [Reproducing Experiments](#reproducing-experiments)
- [Project Structure](#project-structure)
- [Documentation](#documentation)
- [Citation](#citation)
- [License](#license)

---

## Abstract

Grounded Role-Transfer Learning (GRTL) addresses a fundamental challenge in artificial intelligence: how can an agent learn behavioral priors that transfer across radically different domains without relying on pretrained embeddings, large language models, or gradient-based optimization?

TAIS models every domain — from 2D grid navigation to code synthesis to multi-agent negotiation — as a **typed, labeled graph** (`RealityGraph`). A single architecture (`UniversalMote`) performs the same observe–analogize–predict–act–learn cycle in every domain. Action roles (e.g., `APPROACH_GOOD`, `AVOID_BAD`) are discovered through structural analogy and transferred via a hand-coded compatibility matrix or a learned compatibility function.

We demonstrate that:
- A single mote pretrained on GridWorld, RuleWorld, CodeSynt, and SciEx achieves a **+97% reward gain** and **73.4% transfer precision** in multi-agent negotiation (NegoSim) — surpassing all baselines including Tabular Q-Learning (measured via the fused-transfer runner at 30 seeds).
- Navigation survival patterns transfer from 2D grids to autonomous web navigation (WebNav) with **84.2% precision**.
- Role semantics learned in one domain (e.g., `APPROACH_GOOD` in GridWorld) are robustly reusable in domains with completely different entity types, relation structures, and action vocabularies.
- All cognitive engines (metacognition, causal reasoning, planning) operate domain-agnostically on the same substrate.

---

## Key Contributions

1. **Universal Graph Substrate.** A single `RealityGraph` representation (entities + typed relations + transformations + constraints) that subsumes navigation, logic, code ASTs, scientific experiments, negotiation, and web browsing.

2. **Grounded Role-Transfer Learning (GRTL).** Action roles discovered through structural subgraph analogy, transferred via compatibility analysis — no embeddings, no gradients, no pretrained models.

3. **Fused Multi-Source Transfer.** Multiple source domains contribute distinct functional priors that stack synergistically: GridWorld teaches spatial approach/avoid, RuleWorld teaches transformation-to-goal, CodeSynt teaches dependency ordering, SciEx teaches experimental control.

4. **Domain-Agnostic Cognitive Engines.** Metacognition (prediction-error-driven exploration), causal reasoning (Delta-P with counterfactuals), and hierarchical planning (backward chaining on causal links) all operate on the same universal substrate.

5. **Multiple Domain Tiers.** Transfer from toy domains (GridWorld, RuleWorld) to hand-authored benchmark tasks (WebNav, CodeSynt, SciEx, NegoSim) and genuinely grounded domains (PythonAST, CodeRepair) without any domain-specific tuning.

6. **AttentionDB Memory.** Multi-head attention (semantic, temporal, structural) for retrieval-augmented episodic recall, backed by a Rust vector engine with gRPC and REST interfaces.

---

## Theory and Motivation

### Structural Analogy Without Embeddings

TAIS does not learn continuous vector representations. Instead, transfer is mediated by **structural analogy** — subgraph isomorphism between a learned pattern and a novel observation. When a mote encounters an entity tagged with `TARGET`, it maps the subgraph around that entity onto the stored pattern for `APPROACH_GOOD` from GridWorld. The action role is transferred, not the raw action.

### Delta-P Causal Reasoning

Causal relationships are modeled using **Delta-P** (probability of outcome given action minus probability of outcome given no action). Each `(action, outcome)` pair is tracked independently:

$$ \Delta P = P(O \mid A) - P(O \mid \neg A) $$

A link is considered causal when $|\Delta P| > 0.15$ and confidence $> 0.15$. Counterfactuals are computed by comparing $P(O \mid A)$ against $P(O \mid \neg A)$.

### Prediction-Error-Driven Metacognition

The metacognitive engine tracks prediction error per action role. When prediction accuracy drops below a threshold, exploration is increased; when accuracy rises, exploration is reduced. This provides a simple but effective mechanism for balancing exploitation and exploration without parameter sweeps.

### Role Compatibility

Transfer uses a **role compatibility matrix** — a hand-coded $R \times R$ table where $R_{ij}$ quantifies how well role $i$ (source) maps to role $j$ (target). Values range from 0 (incompatible) to 10 (identical). The learned compatibility variant (Phase R6) replaces this table with an exponentially-weighted moving average learned from experience.

---

## Architecture

### 1. The UniversalMote (`tais_core/mote.py`)

The "beating heart" of TAIS. It executes a domain-blind cycle every tick:

| Phase | Operation | Description |
|-------|-----------|-------------|
| Observe | `world.observe(graph, position)` | Retrieve k-hop neighborhood from RealityGraph |
| Predict | `memory.predict_action(action, observation)` | Estimate consequence of candidate actions |
| Act | `action = choose_action(...)` | Select and execute a Transformation |
| Learn | `memory.record_episode(...)` | Store (state, action, role, consequence) in episodic + pattern memory |
| Cog. Update | See §4 | Metacognition, causal reasoning, planning |

### 2. The RealityGraph (`tais_core/reality.py`)

A universal typed graph substrate with:

```
Entity          — a node: anything that exists (id, etype, properties)
Relation        — a typed directed edge (source, rtype, target, properties)
Transformation  — a candidate action (name, domain, universal_op, base_cost, role_hint)
Constraint      — a rule the world enforces
Consequence     — what the world returns after an action (reward, penalty, graph_delta)
```

Key operations: `diff()` (what changed), `distance()` (structural difference), `analogize()` (cross-domain pattern mapping), `neighborhood()` (k-hop subgraph extraction).

### 3. Memory Hierarchy

| Component | File | Function |
|-----------|------|----------|
| EpisodicMemory | `tais_core/memory.py` | Sequential experience log with prediction records |
| PatternMemory | `tais_core/memory.py` | Structural subgraphs with consequence signatures |
| SymbolicMemory | `tais_core/memory.py` | Discrete symbol-concept mappings |
| CulturalMemory | `tais_core/memory.py` | Shared cross-mote knowledge archive |
| PredictionEngine | `tais_core/memory.py` | Cost-anchored valence prediction with error tracking |
| AttentionDB | `tais_core/memory_attentiondb.py` | Multi-head attention (Semantic, Temporal, Structural) for retrieval-augmented recall |
| AttentionDB Client | `tais_core/attentiondb_client.py` | gRPC + REST client for the Rust AttentionDB vector engine |

### 4. Cognitive Engines

All three cognitive engines operate **domain-agnostically** — they see only action names, outcome concepts, and prediction errors, never raw graph structure.

| Engine | File | Mechanism | Key Parameters |
|--------|------|-----------|----------------|
| **MetacognitiveEngine** | `tais_core/metacognition.py` | Prediction-error-driven exploration modulation. Tracks accuracy per action role; increases exploration when accuracy drops below 0.3, decreases when above 0.7. | `learning_rate=0.1`, `exploration_base=0.5` |
| **CausalReasoningEngine** | `tais_core/causal.py` | Per-`(action, outcome)` Delta-P tracking. Computes $P(O\|A)$, $P(O\|\neg A)$, $\Delta P$, confidence. Supports counterfactual queries: "what would happen without this action?" | `window_size=5`, `min_confidence=0.15` |
| **HierarchicalPlanner** | `tais_core/planning.py` | Single-step backward chaining from causal links. Picks the action with highest $\Delta P$ for the target outcome. Plan library with reuse, rollback, and success-rate tracking. | `planning_cost=2.0` |

Engines are enabled via `UniversalMote.enable_cognitive_engines()`:

```python
mote.enable_cognitive_engines(
    metacognition=True,
    causal_reasoning=True,
    hierarchical_planning=True,
)
```

An **Engine Selection Policy** (`tais_core/engine_policy.py`) can gate which engines activate based on the action vocabulary (sensorimotor, symbolic, or mixed).

### 5. Engine Selection Policy

The policy classifies action vocabularies into regimes:

| Regime | Criteria | Enabled Engines |
|--------|----------|-----------------|
| Sensorimotor | Only MOVE/APPROACH/AVOID actions | None |
| Mixed | Sensorimotor + symbolic actions | Metacognition only |
| Symbolic | At least one TRANSFORM/VERIFY/ASSERT action | All three |

This prevents cognitive overhead in purely reactive domains while enabling full reasoning in symbolic domains.

---

## Domains

| Category | Domain | File | Description |
|----------|--------|------|-------------|
| Core | GridWorld | `tais_core/domains/gridworld.py` | 2D spatial navigation, resource collection, threat avoidance |
| Core | SequenceWorld | `tais_core/domains/sequences.py` | Temporal pattern prediction and completion |
| Core | RuleWorld | `tais_core/domains/rules.py` | Modus ponens inference with TARGET-fact variants (Easy, Chain, Distractor, ChainLong) |
| Core | HazardWorld | `tais_core/domains/hazard.py` | Threat avoidance with distractor exits (easy, large variants) |
| Core | LogicWorld | `tais_core/domains/logic.py` | Propositional constraint satisfaction (easy, chain, large, unsat variants) |
| Hand-Authored* | WebNav | `tais_core/domains/webnav.py` | Autonomous web navigation, form filling, modal dismissal |
| Hand-Authored* | CodeSynt | `tais_core/domains/codesynt.py` | AST-based code synthesis, operator repair, dependency ordering |
| Hand-Authored* | SciEx | `tais_core/domains/sciex.py` | Scientific hypothesis testing, experiment design, data analysis |
| Hand-Authored* | NegoSim | `tais_core/domains/negosim.py` | Multi-agent negotiation with complementary goals and resource trading |
| Grounded† | PythonAST | `tais_core/domains/python_ast.py` | Real Python AST analysis (parse real source into RealityGraph) |
| Grounded† | CodeRepair | `tais_core/domains/code_repair.py` | Relational code repair (AST diff over real Python source) |
| Research | MathWorld | `tais_core/domains/math_world.py` | Arithmetic expression evaluation and manipulation |
| Research | AST Diff | `tais_core/domains/ast_diff.py` | Abstract syntax tree structural differencing |
| Research | BugInference | `tais_core/domains/bug_inference.py` | Code defect localization and repair planning |

\* *Hand-authored synthetic graph environments designed to mimic real-world tasks.*
† *Genuinely grounded: parses real Python source code into RealityGraphs.*

Domains can be loaded by name or by YAML spec path:

```python
from tais_core.dsl.codegen import load_domain

grid = load_domain("gridworld")
custom = load_domain("path/to/my_domain.yaml")
```

All domain specifications live in `tais_core/dsl/specs/`. See the [Domain Guide](docs/domain-guide.md) for the YAML DSL reference.

---

## Results

### Legacy Transfer (Phase 4–5)

| Experiment | Source → Target | Reward Δ | Transfer Precision |
|-----------|----------------|----------|-------------------|
| Grid → Hazard | GridWorld → HazardWorld | — | 83% |
| Grid → Logic | GridWorld → LogicWorld | — | 79% |

*Runners:* `tais_core/experiments/runners/hazard_transfer_runner.py`, `tais_core/experiments/runners/logic_transfer_runner.py`

### Phase D — Experiment Framework

Phase D uses the unified experiment framework (`tais_core/experiments/suite.py`) with paired-seed methodology, Cohens-d effect sizes, and systematic ablation.

#### Composition (multi-source transfer)

| Composition | Target | Reward Δ | Cohen's d |
|------------|--------|----------|-----------|
| Grid → NegoSim | NegoSim | +134% | — |
| Grid+Rules → NegoSim | NegoSim | +143% | — |
| Grid+Rules+Code → NegoSim | NegoSim | +157% | — |
| Grid+Rules+Code+SciEx → NegoSim | NegoSim | **+160%** | **2.41** |

*Runner:* `tais_core/experiments/runners/phase_d/composition.py`
*Report:* `docs/PHASE_D_KILLER_EXPERIMENTS_REPORT.md`

#### Curriculum (ordering of source domains)

| Curriculum | Target | Reward Δ |
|-----------|--------|----------|
| Grid → SciEx → Rules → Code → NegoSim | NegoSim | **+168%** |
| Code → SciEx → Rules → Grid → NegoSim | NegoSim | +147% |
| Random order | NegoSim | +132–155% |

*Runner:* `tais_core/experiments/runners/phase_d/curriculum.py`

#### Scaling Laws

| Metric | Finding |
|--------|---------|
| Domain count scaling | Each additional source domain adds +7–10% reward (diminishing returns after 4) |
| Horizon scaling | Transfer advantage increases with evaluation horizon; 50-tick horizon shows +73% Δ vs 10-tick |
| Cognitive contribution | Metacognition alone: +12%; Causal alone: +8%; Planner alone: +5%; All three: +24% |

*Runners:* `tais_core/experiments/runners/phase_d/scaling_law.py`, `tais_core/experiments/runners/phase_d/cognitive_contribution.py`

### Phase F2 — Paper-Defining Experiments

#### Role-Balanced Curriculum

| Condition | Precision | Reward |
|-----------|-----------|--------|
| Random baseline | 23.5% | -12.6 |
| GRTL (hand-coded roles) | **90.1%** | **+47.2** |
| GRTL + learned compatibility | 88.3% | +44.8 |

*Runner:* `tais_core/experiments/runners/phase_f2/role_balanced_curriculum.py`

#### Domain-Count Scaling (20 seeds, NegoSim)

| Sources | Precision | Reward | vs Fresh |
|---------|-----------|--------|---------|
| Fresh (no pretrain) | 28.2% | +5.2 | — |
| 1 source | 60.4% | +18.3 | +252% |
| 2 sources | 74.8% | +28.6 | +450% |
| 3 sources | 82.1% | +36.9 | +610% |
| 4 sources | **90.1%** | **+47.2** | **+808%** |

*Runner:* `tais_core/experiments/runners/phase_f2/domain_count_scaling.py`

#### Grid-to-Logic 1000-Seed Replication

| Condition | Precision (mean ± SD) | Reward (mean ± SD) |
|-----------|----------------------|-------------------|
| Fresh | 51.4% ± 3.2% | +2.1 ± 1.8 |
| Grid-pretrained | **92.7% ± 1.8%** | **+14.8 ± 2.1** |
| Cohen's d | — | **6.81** |

*Runner:* `tais_core/experiments/runners/phase_f2/grid_logic_1000_replication.py`

#### Repair Convergence

| Condition | % Converged (50 ticks) | Mean ticks to converge |
|-----------|----------------------|----------------------|
| Fresh | 34.2% | 42.3 |
| Grid-pretrained | 78.6% | 21.4 |
| GRTL full | **89.1%** | **14.7** |

*Runner:* `tais_core/experiments/runners/phase_f2/repair_convergence.py`

### Phase R — Robustness and Ablation

| Experiment | Key Finding | Report |
|-----------|-------------|--------|
| **R2: Role Ontology Robustness** | Shuffling role names reduces precision by <5%; hand-coded semantics not necessary | [`docs/PHASE_R2_ROLE_ONTOLOGY_ROBUSTNESS_REPORT.md`](docs/PHASE_R2_ROLE_ONTOLOGY_ROBUSTNESS_REPORT.md) |
| **R3: Baseline Comparison** | TAIS (GRTL) outperforms RandomAgent (×4.2), HeuristicAgent (×2.1), TabularQ (×1.7) | [`docs/PHASE_R3_BASELINE_COMPARISON_REPORT.md`](docs/PHASE_R3_BASELINE_COMPARISON_REPORT.md) |
| **R4: Large Domain Transfer** | Transfer holds at scale: logic_large, hazard_large, rules_chain_long | [`docs/PHASE_R4_LARGE_DOMAIN_TRANSFER_REPORT.md`](docs/PHASE_R4_LARGE_DOMAIN_TRANSFER_REPORT.md) |
| **R5: Prediction Gating** | Engine policy gates reduce cognitive overhead without degrading transfer | [`docs/PHASE_R5_PREDICTION_GATING_REPORT.md`](docs/PHASE_R5_PREDICTION_GATING_REPORT.md) |
| **R6: Learned Role Compatibility** | EWM learned compatibility matches hand-coded within 2% | [`docs/PHASE_R6_LEARNED_ROLE_COMPATIBILITY_REPORT.md`](docs/PHASE_R6_LEARNED_ROLE_COMPATIBILITY_REPORT.md) |

---

## Installation

### Requirements

- Python 3.10–3.14
- pip

### From source

```bash
git clone https://github.com/RayAKaan/TAIS.git
cd TAIS
pip install -e .
```

### With dev dependencies (for running tests)

```bash
pip install -e .[dev]
```

### Dependencies

| Dependency | Version | Purpose |
|-----------|---------|---------|
| numpy | ≥1.24 | Numerical operations |
| scipy | ≥1.10 | Statistical tests |
| matplotlib | ≥3.7 | Visualization, figures |
| tqdm | ≥4.65 | Progress bars |
| PyYAML | ≥6.0 | DSL spec parsing |
| requests | ≥2.28 | AttentionDB REST client, LLM grounding |
| grpcio | ≥1.48 | AttentionDB gRPC client |
| fastapi | ≥0.104 | API server |
| uvicorn | ≥0.24 | ASGI server |
| websockets | ≥12.0 | WebSocket event streaming |
| pydantic | ≥2.0 | API request/response models |
| pytest | ≥7.4 (dev) | Test runner |

---

## Quickstart

### Minimal example

```python
from tais_core.mote import UniversalMote
from tais_core.domains.gridworld import GridGraphWorld, make_grid_graph

# Create a mote and a world
mote = UniversalMote(energy=100)
world = GridGraphWorld()
graph = make_grid_graph()

# Enable cognitive engines
mote.enable_cognitive_engines()

# Run 10 ticks
for tick in range(10):
    graph, cons, action = mote.step(world, graph, mote_position="mote", tick=tick)
    if action:
        print(f"tick={tick} action={action.name} reward={cons.net:.2f}")
    if not mote.alive:
        break
```

### Starting the API server

```bash
uvicorn tais_api:app --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000/v6/` for the web UI or use the REST endpoints.

### Loading a domain from the DSL

```python
from tais_core.dsl.codegen import load_domain

# By builtin name
grid = load_domain("gridworld")

# By YAML spec path
custom = load_domain("tais_core/dsl/specs/webnav.yaml")

# Disable caching for fresh instances
fresh = load_domain("gridworld", use_cache=False)
```

---

## Reproducing Experiments

All experiment runners are in `tais_core/experiments/runners/`. Each runner supports command-line arguments for seed count, output directory, and domain selection.

### Fused multi-source transfer (Paper Figure 4)

```bash
python -m tais_core.experiments.runners.phase_d.composition
```

### Role-balanced curriculum (Paper Figure 5)

```bash
python -m tais_core.experiments.runners.phase_f2.role_balanced_curriculum
```

### Domain-count scaling (Paper Figure 6)

```bash
python -m tais_core.experiments.runners.phase_f2.domain_count_scaling
```

### Grid-to-logic 1000-seed replication (Paper Figure 7)

```bash
python -m tais_core.experiments.runners.phase_f2.grid_logic_1000_replication
```

### Baseline comparison

```bash
python -m tais_core.experiments.runners.phase_r.baseline_comparison
```

### Role ontology robustness

```bash
python -m tais_core.experiments.runners.phase_r.role_ontology_robustness
```

### All experiments (full paper reproduction)

```bash
# See REPRODUCIBILITY.md for per-experiment commands
# or run with default parameters:
python -m tais_core.experiments.suite
```

### Running tests

```bash
# All tests
python -m pytest tests/

# Core engine tests
python -m pytest tests/core/

# Domain-specific tests
python -m pytest tests/domains/

# Experiment framework tests
python -m pytest tests/experiments/

# Transfer tests
python -m pytest tests/transfer/

# Prediction engine tests
python -m pytest tests/prediction/
```

**Current test count: 369 passing** across all suites.

---

## Project Structure

```
tais/                         # Repository root
├── tais_core/                # Core framework
│   ├── reality.py            # Entity, Relation, RealityGraph, WorldInterface
│   ├── mote.py               # UniversalMote agent
│   ├── memory.py             # EpisodicMemory, PatternMemory, PredictionEngine
│   ├── memory_attentiondb.py # AttentionDB-backed memory
│   ├── causal.py             # CausalReasoningEngine (Delta-P)
│   ├── planning.py           # HierarchicalPlanner
│   ├── metacognition.py      # MetacognitiveEngine
│   ├── speech.py             # SpeechOrgan, Lexicon, SpeechGenome
│   ├── role_learning.py      # Learned role compatibility (Phase R6)
│   ├── engine_policy.py      # Engine selection policy
│   ├── llm_grounding.py      # NL → RealityGraph translation
│   ├── event_bus.py          # WebSocket event broadcasting
│   ├── attentiondb_client.py # gRPC/REST client for AttentionDB
│   ├── attentiondb_pb2.py    # Protobuf message definitions
│   ├── attentiondb_pb2_grpc.py # gRPC service stubs
│   ├── __init__.py           # Public API exports
│   ├── domains/              # Domain implementations
│   │   ├── gridworld.py      # GridGraphWorld + make_grid_graph
│   │   ├── rules.py          # RuleWorld variants
│   │   ├── hazard.py         # HazardGraphWorld variants
│   │   ├── logic.py          # LogicWorld variants
│   │   ├── sequences.py      # SequenceWorld
│   │   ├── webnav.py         # WebNav (autonomous web navigation)
│   │   ├── codesynt.py       # CodeSynt (AST-based code synthesis)
│   │   ├── sciex.py          # SciEx (scientific experimentation)
│   │   ├── negosim.py        # NegoSim (multi-agent negotiation)
│   │   ├── python_ast.py     # PythonAST (real AST parsing)
│   │   ├── code_repair.py    # CodeRepair (AST-diff repair)
│   │   ├── math_world.py     # MathWorld (arithmetic expressions)
│   │   ├── ast_diff.py       # AST structural differencing
│   │   ├── bug_inference.py  # Code defect localization
│   │   ├── registry.py       # Name-to-domain mapping (re-export shim)
│   │   └── __init__.py       # Domain package exports
│   ├── dsl/                  # Domain Specification Language
│   │   ├── codegen.py        # load_domain, BuiltinDSLWorld, DeclarativeDSLWorld
│   │   ├── parser.py         # YAML spec parser
│   │   ├── validator.py      # Spec schema validation
│   │   ├── __init__.py       # DSL package exports
│   │   └── specs/            # YAML domain specifications
│   ├── experiments/          # Experiment framework
│   │   ├── suite.py          # ExperimentSuite, Condition, Metric
│   │   ├── results.py        # TrialRecord, ExperimentResults, reports
│   │   └── runners/          # Experiment runner scripts
│   │       ├── phase_d/      # Composition, curriculum, scaling
│   │       ├── phase_f2/     # Paper-defining experiments
│   │       ├── phase_r/      # Robustness and ablation
│   │       ├── phase_e/      # Visualization
│   │       └── ...           # Legacy and research runners
│   └── viz/                  # Visualization utilities
│       └── trajectory.py     # Mote trajectory recording and HTML export
├── tais_api.py               # FastAPI server with WebSocket streaming
├── frontend/                 # Web UI (Vite + React)
├── scripts/                  # Utility scripts
├── tests/                    # Test suites
│   ├── core/                 # Core engine tests
│   ├── domains/              # Domain-specific tests
│   ├── experiments/          # Experiment framework tests
│   ├── prediction/           # Prediction engine tests
│   └── transfer/             # Transfer learning tests
├── docs/                     # Research documentation
│   ├── TAIS_GRTL_RESEARCH_REPORT.md  # Full 5-phase empirical investigation
│   ├── domain-guide.md       # DSL specification guide
│   ├── experiment-guide.md   # Experiment framework user guide
│   ├── visualization-guide.md # Trajectory and plotting guide
│   ├── CODEBASE_MANIFEST.md  # Full codebase layout reference
│   ├── PHASE_*.md            # Phase-by-phase experiment reports
│   └── PAPER_SUBMISSION_CHECKLIST.md
├── results/                  # Experiment output artifacts
│   └── paper_locked/         # Curated paper results
├── REPRODUCIBILITY.md        # Full experiment reproduction guide
├── pyproject.toml            # Build and dependency configuration
└── README.md                 # This file
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [GRTL Research Report](docs/TAIS_GRTL_RESEARCH_REPORT.md) | Full 5-phase empirical investigation of Grounded Role-Transfer Learning |
| [Reproducibility Guide](REPRODUCIBILITY.md) | Step-by-step instructions to reproduce all experiments |
| [Domain Guide](docs/domain-guide.md) | YAML DSL reference: builtin-backed and declarative worlds |
| [Experiment Guide](docs/experiment-guide.md) | Experiment framework: Condition, Metric, Suite, Results |
| [Codebase Manifest](docs/CODEBASE_MANIFEST.md) | Complete file-by-file codebase layout |
| [Handover Report](docs/HANDOVER_REPORT.md) | Roadmap completion and future work summary |

### Phase Reports

| Phase | Report | Content |
|-------|--------|---------|
| 0–2 | [`PHASE0_PHASE2_PHASE1_CHANGELOG.md`](docs/PHASE0_PHASE2_PHASE1_CHANGELOG.md) | Early development, prediction, speech |
| 1 | [`PHASE1_VALIDATION_REPORT.md`](docs/PHASE1_VALIDATION_REPORT.md) | Role-compatibility ablation analysis (harness limitation finding) |
| A | [`docs/PHASE_A_*`](docs/PHASE_A_PAPER_READINESS_REPORT.md) | Prediction calibration, engine policy, speech portability |
| B | [`PHASE_B_DOMAIN_DSL_REPORT.md`](docs/PHASE_B_DOMAIN_DSL_REPORT.md) | Domain DSL implementation |
| C | [`PHASE_C_EXPERIMENT_FRAMEWORK_REPORT.md`](docs/PHASE_C_EXPERIMENT_FRAMEWORK_REPORT.md) | Experiment framework design |
| D | [`PHASE_D_KILLER_EXPERIMENTS_REPORT.md`](docs/PHASE_D_KILLER_EXPERIMENTS_REPORT.md) | Composition, curriculum, scaling, cognitive contribution |
| E | [`PHASE_E_VISUALIZATION_REPORT.md`](docs/PHASE_E_VISUALIZATION_REPORT.md) | Trajectory visualization, radar charts, scaling curves |
| F2 | [`PHASE_F2_PAPER_DEFINING_EXPERIMENTS_REPORT.md`](docs/PHASE_F2_PAPER_DEFINING_EXPERIMENTS_REPORT.md) | Role-balanced curriculum, domain-count scaling, 1000-seed replication |
| R2 | [`PHASE_R2_ROLE_ONTOLOGY_ROBUSTNESS_REPORT.md`](docs/PHASE_R2_ROLE_ONTOLOGY_ROBUSTNESS_REPORT.md) | Role ontology robustness |
| R3 | [`PHASE_R3_BASELINE_COMPARISON_REPORT.md`](docs/PHASE_R3_BASELINE_COMPARISON_REPORT.md) | TAIS vs Random/Heuristic/TabularQ |
| R4 | [`PHASE_R4_LARGE_DOMAIN_TRANSFER_REPORT.md`](docs/PHASE_R4_LARGE_DOMAIN_TRANSFER_REPORT.md) | Large-domain variants |
| R5 | [`PHASE_R5_PREDICTION_GATING_REPORT.md`](docs/PHASE_R5_PREDICTION_GATING_REPORT.md) | Engine selection policy |
| R6 | [`PHASE_R6_LEARNED_ROLE_COMPATIBILITY_REPORT.md`](docs/PHASE_R6_LEARNED_ROLE_COMPATIBILITY_REPORT.md) | Learned role compatibility |
| 7–8 | [`PHASE7_8_LOAD_BEARING_ARCHITECTURE_REPORT.md`](docs/PHASE7_8_LOAD_BEARING_ARCHITECTURE_REPORT.md) | CulturalMemory, Active Planning |

---

## Citation

If you use TAIS in your research, please cite:

```bibtex
@software{tais2026,
  author = {RayAKaan and TAIS Contributors},
  title = {TAIS: Thought-Assisted Intelligence Substrate — Grounded Role-Transfer Learning Without Pretrained Representations},
  year = {2026},
  url = {https://github.com/RayAKaan/TAIS},
  doi = {10.5281/zenodo.XXXXXXX},
}
```

---

## License

MIT. See [LICENSE](LICENSE).

---

*TAIS is a research framework for grounded role-transfer learning. It is not a production system. Results are reported on controlled benchmarks and may not generalize to all domains.*
