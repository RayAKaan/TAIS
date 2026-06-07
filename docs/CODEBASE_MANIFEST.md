# TAIS Current Codebase Manifest

This archive contains the current working TAIS research codebase from this workspace.

## Core universal substrate

- `tais_core/reality.py` — Entity, Relation, RealityGraph, Transformation, Constraint, Consequence, GraphDelta, analogy, WorldInterface.
- `tais_core/memory.py` — EpisodicMemory, PatternMemory, SymbolicMemory, CulturalMemory, PredictionEngine, MoteMemory, ActionRole helpers currently integrated here.
- `tais_core/speech.py` — Lexicon, SpeechGenome, Utterance, RepairSignal, UnderstandingAudit, SpeechOrgan.
- `tais_core/mote.py` — UniversalMote and MetaGenes.
- `tais_core/domains/gridworld.py` — GridGraphWorld.
- `tais_core/domains/sequences.py` — SequenceWorld.
- `tais_core/domains/rules.py` — RuleWorld.

## Swarm systems

- `swarm_v5.py` — V5.5 ecological swarm/server/UI backend with query mode, audit, action role transfer.
- `swarm_v4.py` — V4 world/memory/reference version.
- `swarm_v3.py` — V3 living speech version.
- `swarm_server.py` — older codebook conversational server.
- `tais_lang_v2_predator.py` — predator/silence/deception simulation.

## Experiments

- `experiments_cross_domain_transfer.py` — 50-seed/variable transfer experiment runner.
- `experiments_statistical_replication.py` — 200-seed paired replication of mixed GridWorld → RuleWorld.

## Tests

- `tests/test_tais_core.py` — core unit tests.
- `tests/test_base_validation.py` — base validation tests.

## Frontend

- `src/App.jsx` — current React UI.
- `src/main.jsx`
- `index.html`
- `package.json`
- `package-lock.json`

## Reports / docs

- `README.md`
- `TAIS_UNIVERSAL_ROADMAP.md`
- `TAIS_BASE_MODEL_CRITERIA.md`
- `TEST_REPORT.md`
- `CROSS_DOMAIN_TRANSFER_REPORT.md`
- `ANALOGY_ACTION_PRIOR_REPORT.md`

## Outputs

- `cross_domain_transfer_results.json`
- `statistical_replication_results.json`
- `colonies/*.json` smoke-test colonies

## Run tests

```bash
python3 -m pip install -r requirements.txt
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

## Run V5.5 interactive backend

```bash
python3 swarm_v5.py
```

Then frontend:

```bash
npm install
npm run dev
```

## Run replication

```bash
PYTHONPATH=. python3 experiments_statistical_replication.py
```
