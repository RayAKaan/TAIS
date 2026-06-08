# TAIS — Thought-Assisted Intelligence System

No LLM. No pretrained language model. No codebook generation.

TAIS is a grounded learning substrate built around **domain-blind thermodynamic motes** operating over typed **RealityGraphs**. The core research claim is that the same mote architecture can transfer functional action roles across structurally different graph domains through consequence, prediction, pattern memory, and action-role priors.

---

## Repository Structure

```text
.
├── tais_core/                  Universal reality, memory, speech substrate
│   ├── reality.py              Entity, Relation, RealityGraph, WorldInterface
│   ├── memory.py               EpisodicMemory, PatternMemory, PredictionEngine
│   ├── speech.py               Lexicon, SpeechOrgan, UnderstandingAudit
│   ├── mote.py                 UniversalMote: domain-blind agent
│   └── domains/
│       ├── gridworld.py        Tiny survival/resource-threat domain
│       ├── sequences.py        Sequence prediction domain
│       ├── rules.py            Rule satisfaction / implication domain
│       ├── hazard.py           Graph navigation with hazards/resources/exits
│       └── logic.py            Propositional SAT / contradiction-avoidance domain
│
├── tests/                      Test suite, currently 59 tests
├── experiments/
│   ├── ablation_runner.py              8-condition ablation runner
│   ├── cross_domain_transfer.py        Earlier Grid → Rule transfer runner
│   ├── statistical_replication.py      200-seed paired replication
│   ├── hazard_transfer_runner.py       Grid → Hazard transfer runner
│   ├── logic_transfer_runner.py        Grid → Logic transfer runner
│   ├── predict_diagnostic.py           PredictionEngine diagnostic
│   ├── predict_calibration_sweep.py    Prediction calibration sweep
│   └── choose_action_design_sweep.py   choose_action scoring sweep
│
├── swarm_v5.py                 V5.5 ecological swarm backend / interactive demo
├── src/ + index.html           React/Vite frontend
├── docs/                       Roadmaps, experiment reports, manifest
├── archive/                    Old prototypes, e.g. swarm_v3/v4 and TAIS-LANG v2
├── results/                    Generated output files; ignored except .gitkeep
└── colonies/                   Swarm save files; ignored except .gitkeep
```

---

## Core Concept

Everything is a `RealityGraph`. Every domain implements `WorldInterface`.

The `UniversalMote` is domain-blind: it observes, predicts, acts, and learns through a uniform four-function contract:

```python
observe(graph, mote_position) -> RealityGraph
valid_actions(graph, mote_state) -> list[Transformation]
act(graph, transformation, mote_state) -> tuple[RealityGraph, Consequence]
evaluate(graph, mote_state) -> float
```

The mote does not contain chemistry-specific, math-specific, logic-specific, or GridWorld-specific code. Domains provide the graph, legal actions, and consequences. The mote provides the learning architecture.

---

## Base Architecture

The TAIS base model is:

```text
RealityGraph
+ UniversalMote
+ MoteMemory
+ SpeechOrgan
+ PredictionEngine
+ ActionRole transfer
+ Consequence feedback
```

In one loop:

```text
observe graph
→ predict action consequence
→ choose transformation
→ act in world
→ receive Consequence
→ update memory / prediction / speech / energy
→ transfer useful patterns across domains
```

---

## Current Scientific Status

Current TAIS can:

- run a domain-blind `UniversalMote` across multiple graph domains,
- represent domains as typed `RealityGraph`s,
- store graph patterns in `PatternMemory`,
- analogize patterns across domains,
- use transfer priors in action selection,
- classify actions by functional role,
- run a V5.5 ecological swarm with teaching/query/audit,
- run reproducible ablation and transfer experiments.

Current strongest result:

```text
GridWorld → LogicWorld transfer
n = 200 paired seeds
first_task_success_tick Δ ≈ -3.96
p < 0.001
d ≈ -0.568
```

Negative `first_task_success_tick` delta is good: pretrained motes solve faster.

Interpretation:

```text
Mixed GridWorld pretraining transfers functional action roles into LogicWorld.
ActionRole and PatternMemory ablations each substantially weaken the effect.
Empty pretraining does not reproduce it.
```

This is evidence for the claim that TAIS transfers **roles**, not facts.

---

## Install

Python runtime dependencies:

```bash
python -m pip install -r requirements.txt
```

For editable package mode:

```bash
python -m pip install -e .
```

Frontend dependencies:

```bash
npm install
```

On Windows/Git Bash, use `python`, not necessarily `python3`.

---

## Run Tests

```bash
PYTHONPATH=. python -m unittest discover -s tests -v
```

Expected current result:

```text
59 tests passing
```

CI runs the test suite on Python 3.10, 3.11, and 3.12.

---

## Core API Example

```python
from tais_core import UniversalMote
from tais_core.domains import RuleWorld, make_rule_graph

mote = UniversalMote(energy=100)
world = RuleWorld()
graph = make_rule_graph()

graph, consequence, action = mote.step(
    world,
    graph,
    mote_position="rule_ab",
    tick=0,
)

print(action.name if action else None)
print(consequence.net)
print(mote.metrics())
```

---

## Experiments

### Ablation runner

Strict RuleWorld metric with controls:

```bash
PYTHONPATH=. python experiments/ablation_runner.py \
  --seeds 200 --pretrain 20 --horizons 12,30,50 \
  --output results/ablation_v4.txt
```

### HazardGraphWorld transfer

```bash
PYTHONPATH=. python experiments/hazard_transfer_runner.py \
  --seeds 200 --pretrain 20 --horizons 15,30 \
  --output results/phase4_hazard.txt
```

### LogicWorld transfer

```bash
PYTHONPATH=. python experiments/logic_transfer_runner.py \
  --seeds 200 --pretrain 20 --horizons 15,30 \
  --output results/phase5_logic.txt
```

### Prediction diagnostics

```bash
PYTHONPATH=. python experiments/predict_diagnostic.py
PYTHONPATH=. python experiments/predict_calibration_sweep.py
```

### choose_action design sweep

```bash
PYTHONPATH=. python experiments/choose_action_design_sweep.py
```

---

## Interactive V5.5 Swarm

Terminal 1, backend:

```bash
python swarm_v5.py
```

Terminal 2, frontend:

```bash
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

Backend:

```text
http://localhost:5123
```

### Frontend build

```bash
npm run build
```

---

## Headless Swarm Training

```bash
python swarm_v5.py --headless --ticks 10000 --world 32 --population 80 --report 1000 --save colonies/v55_10k.json
python swarm_v5.py --load colonies/v55_10k.json
```

---

## V5.5 API Endpoints

- `GET /stream` — SSE live state
- `GET /state` — full JSON snapshot
- `GET /audit` — latest understanding audits
- `GET /health` — health check
- `POST /player/move` — `{ "x": 5, "y": 5 }`
- `POST /player/speak` — `{ "text": "water north", "concept": "WATER", "value": 10, "x": 5, "y": 8 }`
- `POST /player/teach` — `{ "word": "water", "concept": "WATER", "value": 10 }`
- `POST /player/query` — `{ "text": "food?", "concept": "FOOD" }`
- `GET /mote/<id>/lexicon` — inspect private lexicon and memories
- `POST /save` — save colony JSON
- `POST /reset` — reset world

---

## Good Teaching Curriculum for the Swarm UI

Use consistent grounding:

```text
food   → FOOD
water  → WATER
danger → PREDATOR
home   → SHELTER
safe   → SAFE
come   → COME
go     → GO
```

Avoid accidentally teaching `food → GO` or `food → SHELTER` unless intentionally creating a dialect/confusion experiment.

---

## Research Reports

Key reports live in `docs/`:

- `docs/PHASE5_LOGIC_TRANSFER_REPORT.md` — current headline result
- `docs/PHASE4_HAZARD_TRANSFER_REPORT.md` — HazardGraphWorld transfer
- `docs/PHASE1_6_RUNNER_BISECT_REPORT.md` — runner RNG fix
- `docs/PHASE1_5_PREDICTION_REPORT.md` — PredictionEngine calibration
- `docs/ABLATION_V2_REPORT.md` — strict RuleWorld metric ablation
- `docs/TAIS_FULL_DETAILED_ROADMAP.md` — full roadmap
- `docs/TAIS_BASE_MODEL_CRITERIA.md` — base model criteria

Older reports are retained as historical context and may be superseded by later phase reports.

---

## What TAIS Is Not Yet

TAIS is not currently:

- AGI,
- a chatbot,
- a real chemistry solver,
- a theorem prover at scale,
- a production AI platform.

It is a research prototype demonstrating a grounded multi-agent substrate for role-based cross-domain transfer and emergent communication.

---

## Next Recommended Work

Near-term research directions:

1. Paper draft around Grid → Rule, Grid → Hazard, Grid → Logic.
2. Phase 6 repair convergence experiment.
3. ChemistryLiteDomain only after the neutral algorithmic paper story is stable.
4. Longer-horizon planning experiments.
5. Consolidate duplicated control worlds in experiment runners.

---

## License

MIT License. See `LICENSE`.
