# TAIS — Thought-Assisted Intelligence System

**Grounded Role-Transfer Learning without pretrained representations.**

No LLM. No pretrained model. No shared embedding space. No gradient descent.

TAIS is a research platform for studying domain-agnostic agents that learn and transfer functional action roles across typed graph domains.

---

## Research release

Current research release: **v0.2.0-grtl-paper**

This release freezes the code and artifacts for the foundational GRTL paper draft. See `REPRODUCIBILITY.md` for reproduction instructions.

---

## One-line pitch

TAIS is a grounded AI system where the same mote can learn, transfer, communicate, reason, run controlled experiments, load new domains from YAML, and generate publication-ready figures — without pretrained representations.

---

## Current capabilities

- Domain-agnostic `UniversalMote`
- Typed `RealityGraph`
- Pattern memory and consequence prediction
- Action-role transfer
- Optional cognitive engines:
  - metacognition
  - causal reasoning
  - hierarchical planning
- Domain DSL via YAML/JSON
- Unified experiment framework
- Killer experiment runners:
  - composition
  - scaling law
  - reverse transfer
  - curriculum
  - cognitive contribution
- Visualization toolkit:
  - heatmaps
  - radar charts
  - scaling plots
  - trajectory HTML viewer
  - lexicon convergence plots
- V6 swarm prototype with emergent communication / ecology

---

## Scientific framing

### Grounded Role-Transfer Learning (GRTL)

GRTL is the thesis that domain-agnostic agents can transfer functional action roles such as `APPROACH_GOOD`, `AVOID_BAD`, `VERIFY_UNCERTAIN`, and `REPAIR_MISMATCH` across structurally distinct typed graph domains through consequence prediction, pattern memory, and energy-budgeted survival — without pretrained language models, shared embedding spaces, or fine-tuning.

---

## Install

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
```

## Run tests

```bash
PYTHONPATH=. python -m unittest discover -s tests -v
```

Current: **162 tests passing**.

## Quickstart: load a YAML domain

```python
from tais_core import UniversalMote, load_domain

world = load_domain("chemistry_lite")
graph = world.initial_graph()

mote = UniversalMote(energy=100)
graph, consequence, action = mote.step(
    world,
    graph,
    mote_position="atom_c",
    tick=0,
)

print(action.name if action else None)
print(consequence.net)
print(mote.metrics())
```

## Quickstart: run an experiment suite

```bash
PYTHONPATH=. python experiments/phase_c_logic_transfer_suite.py \
  --seeds 20 --eval 15 --pretrain 20 \
  --output results/readme_demo
```

## Generate figures

```bash
PYTHONPATH=. python experiments/phase_e/generate_figures.py \
  --phase-d results/phase_d \
  --output results/phase_e/figures
```

## Repository map

```text
tais_core/
  reality.py
  memory.py
  mote.py
  metacognition.py
  causal.py
  planning.py
  domains/
  dsl/
  experiments/
  viz/

tais_swarm_v6/
experiments/
tests/
docs/
results/
archive/
examples/
```

## Key commands

```bash
make test
make smoke
make figures
```

## Research artifacts

- [`docs/PHASE_A_CONVERGENCE_REPORT.md`](docs/PHASE_A_CONVERGENCE_REPORT.md)
- [`docs/PHASE_B_DOMAIN_DSL_REPORT.md`](docs/PHASE_B_DOMAIN_DSL_REPORT.md)
- [`docs/PHASE_C_EXPERIMENT_FRAMEWORK_REPORT.md`](docs/PHASE_C_EXPERIMENT_FRAMEWORK_REPORT.md)
- [`docs/PHASE_D_KILLER_EXPERIMENTS_REPORT.md`](docs/PHASE_D_KILLER_EXPERIMENTS_REPORT.md)
- [`docs/PHASE_E_VISUALIZATION_REPORT.md`](docs/PHASE_E_VISUALIZATION_REPORT.md)

## Status

TAIS is an active research prototype. APIs may change before v1.0.

## Citation

See [`CITATION.cff`](CITATION.cff).

## License

MIT.
