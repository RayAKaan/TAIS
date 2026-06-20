# TAIS: Thought-Assisted Intelligence Substrate

**Grounded Role-Transfer Learning without pretrained representations.**

No LLM (for reasoning). No pretrained model. No shared embedding space. No gradient descent.

TAIS is a domain-agnostic agent framework where a single `UniversalMote` learns functional action roles across typed graph domains and transfers them without pretrained representations, LLMs, or gradient descent.

The core mechanism, **Grounded Role-Transfer Learning (GRTL)**, enables agents to learn abstract roles like `APPROACH_GOOD`, `AVOID_BAD`, and `TRANSFORM_TOWARD_GOAL` in toy environments and apply them with high precision to complex, real-world-aligned tasks.

---

## Key Research Breakthroughs

- **Fused Multi-Source Transfer:** Proven that functional roles stack synergistically. A single mote pretrained on GridWorld + RuleWorld + CodeSynt + SciEx achieved a **+160% reward gain** and **90.1% precision** in multi-agent negotiation (NegoSim).
- **Real-World Grounding:** Successfully transferred navigation survival patterns from 2D grids to autonomous web navigation (WebNav) with **84.2% precision**.
- **Universal Substrate:** Every domain — from chemistry and logic to code synthesis — is represented as a `RealityGraph`, allowing for pure structural analogy via subgraph mapping.

---

## Architecture

### 1. The UniversalMote (`tais_core/mote.py`)

The "beating heart" of TAIS. It executes a domain-blind cycle:

- **Observe:** Retrieve a k-hop neighborhood from the RealityGraph.
- **Analogize:** Map learned patterns from other domains onto the current view.
- **Predict:** Estimate consequences using cost-anchored valence fallbacks.
- **Act:** Execute a `Transformation` based on transfer-aware biases.
- **Learn:** Record (state, action, role, consequence) in episodic and pattern memory.

### 2. RealityGraph (`tais_core/reality.py`)

A universal typed graph substrate composed of:

- **Entities:** Typed nodes with arbitrary properties.
- **Relations:** Typed directed edges.
- **Transformations:** Universal operations (MOVE, TRANSFORM, VERIFY, etc.).
- **Constraints:** Domain-enforced rules.

### 3. Memory Hierarchy

- **EpisodicMemory:** Sequential experience log.
- **PatternMemory:** Structural subgraphs with consequence signatures.
- **AttentionDB (New):** Multi-head attention (Semantic, Temporal, Structural) for retrieval-augmented recall.
- **CulturalMemory:** Shared archive for cross-mote knowledge transfer.

### 4. Cognitive Engines (optional)

- **MetacognitiveEngine:** Prediction tracking, self-model, exploration modulation.
- **CausalReasoningEngine:** Delta-P causal discovery, counterfactuals.
- **HierarchicalPlanner:** Backward-chaining plan library.
- **LLMGroundingEngine:** NL → RealityGraph goal translation.

---

## Domains

| Category | Domain | Description |
|----------|--------|-------------|
| Core | GridWorld | 2D navigation and survival |
| Core | RuleWorld | Modus ponens and logical inference |
| Core | HazardWorld | Threat avoidance and safety verification |
| Core | LogicWorld | Assignment and variable derivation |
| Real-World | WebNav | Autonomous web navigation and form filling |
| Real-World | CodeSynt | AST-based code synthesis and refactoring |
| Real-World | SciEx | Scientific experiment design and hypothesis testing |
| Real-World | NegoSim | Multi-agent negotiation and resource trading |

---

## Benchmarks

| Experiment | Source → Target | Reward Δ | Transfer Precision |
|-----------|----------------|----------|-------------------|
| Single Transfer | Grid → WebNav | +32% | 84.2% |
| Single Transfer | Rules → CodeSynt | +19% | 93.6% |
| 3-Source Fused | Grid+Rules+Code → SciEx | +73% | 92.1% |
| 4-Source Fused | Mega-Fusion → NegoSim | **+160%** | **90.1%** |

---

## Getting Started

### Installation

```bash
git clone https://github.com/RayAKaan/TAIS.git
cd TAIS
pip install -e .[dev]
```

### Running Tests

```bash
make pytest
```

Current: **309 tests passing**.

### Reproduce Fused Transfer

```bash
# 4-source fusion experiment (Grid+Rules+Code+SciEx -> NegoSim)
PYTHONPATH=. python experiments/negosim_fused_transfer_runner.py
```

### Generate Paper Figures

```bash
make figures
```

---

## Advanced Modules

- **LLM Grounding Engine** (`tais_core/llm_grounding.py`): Converts natural language goals into RealityGraph entities.
- **AttentionDB Memory** (`tais_core/memory_attentiondb.py`): Multi-head attention for structurally-aware episodic retrieval.
- **Swarm V6** (`tais_swarm_v6/`): Persistent multi-agent ecosystem with spatial thermodynamics and emergent communication.

---

## Research Artifacts

- [GRTL Research Report](TAIS_GRTL_RESEARCH_REPORT.md) — full 5-phase empirical investigation
- [Reproducibility Guide](REPRODUCIBILITY.md) — reproduce all experiments
- [Handover Report](HANDOVER_REPORT.md) — roadmap completion summary

---

## Citation

If you use TAIS in your research, please cite:

```bibtex
@software{tais2026,
  author = {RayAKaan and TAIS Contributors},
  title = {TAIS: Thought-Assisted Intelligence Substrate},
  year = {2026},
  url = {https://github.com/RayAKaan/TAIS}
}
```

## License

MIT.
