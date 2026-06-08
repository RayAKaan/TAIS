# TAIS — Thought-Assisted Intelligence System

No LLM. No pretrained language model. No codebook generation.

## Repository Structure

```
.
├── tais_core/              Universal reality, memory, speech substrate
│   ├── reality.py          Entity, Relation, RealityGraph, WorldInterface
│   ├── memory.py           EpisodicMemory, PatternMemory, PredictionEngine
│   ├── speech.py           Lexicon, SpeechOrgan, UnderstandingAudit
│   ├── mote.py             UniversalMote (domain-blind agent)
│   └── domains/
│       ├── gridworld.py    Tiny survival domain
│       ├── sequences.py    Sequence prediction domain
│       └── rules.py        Rule satisfaction domain
<<<<<<< HEAD
├── tests/                  Test suite (33 tests)
=======
├── tests/                  Test suite (24 tests)
>>>>>>> Phase 0 followup: drop tracked artefacts, README test count
├── experiments/
│   ├── ablation_runner.py         Ablation experiments (v2 strict metric)
│   ├── cross_domain_transfer.py   Cross-domain transfer experiment
│   └── statistical_replication.py 200-seed statistical replication
├── swarm_v5.py             V5.5 ecological swarm backend
├── src/ + index.html       React/Vite frontend
├── docs/                   Roadmaps, reports, manifest
├── archive/                Old prototypes (swarm_v3, v4, etc.)
├── results/                Generated output files
└── colonies/               Swarm save files
```

## Core Concept

Everything is a `RealityGraph`. Every domain implements `WorldInterface`.
The `UniversalMote` is domain-blind — it observes, predicts, acts, and learns
through a uniform 4-function contract:

```python
observe(graph, mote_position)
valid_actions(graph, mote_state)
act(graph, transformation, mote_state)
evaluate(graph, mote_state)
```

## Run Tests

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

<<<<<<< HEAD
Expected: **33 tests passing**
=======
Expected: **24 tests passing**
>>>>>>> Phase 0 followup: drop tracked artefacts, README test count

## Experiments

```bash
# Ablation v2 — 8 conditions × strict task_signal metric × horizon sweep.
# See docs/ABLATION_V2_REPORT.md for the analysis of the headline result.
PYTHONPATH=. python3 experiments/ablation_runner.py \
    --seeds 200 --pretrain 20 --horizons 12,30,50 \
    --output results/ablation_v2.txt

# Cross-domain transfer (GridWorld → RuleWorld)
PYTHONPATH=. python3 experiments/cross_domain_transfer.py

# Statistical replication (200-seed paired test)
PYTHONPATH=. python3 experiments/statistical_replication.py
```

## Interactive Swarm

Terminal 1 (backend):

```bash
python3 -m pip install -r requirements.txt
python3 swarm_v5.py
```

Terminal 2 (frontend):

```bash
npm install
npm run dev
```

Open: `http://localhost:5173`

## Headless Training

```bash
python3 swarm_v5.py --headless --ticks 10000 --world 32 --population 80 --report 1000 --save colonies/v55_10k.json
python3 swarm_v5.py --load colonies/v55_10k.json
```

## API Endpoints

- `GET /stream` — SSE live state
- `GET /state` — full JSON snapshot
- `GET /audit` — latest understanding audits
- `GET /health` — health check
- `POST /player/move` — `{ "x": 5, "y": 5 }`
- `POST /player/speak` — `{ "text": "water north", "concept": "WATER", ... }`
- `POST /player/teach` — `{ "word": "water", "concept": "WATER" }`
- `POST /player/query` — `{ "text": "food?", "concept": "FOOD" }`
- `GET /mote/<id>/lexicon` — inspect private lexicon and memories
