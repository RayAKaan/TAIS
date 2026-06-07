# TAIS Full Detailed Roadmap

## Mission

Build TAIS into a validated, universal, grounded learning substrate where domain-blind thermodynamic motes can learn, communicate, repair misunderstanding, predict consequences, preserve patterns, and transfer functional roles across typed reality domains.

The goal is not to build a chatbot first. The goal is to build a base ecology of intelligence:

```text
consequence before language
prediction before action
repair before shared meaning
role transfer before domain expertise
```

## Current status

TAIS currently has:

```text
- V5.5 ecological swarm with grounded speech, query mode, teaching, silence, audit
- Universal core: RealityGraph, MoteMemory, SpeechOrgan, UniversalMote
- Tiny validation domains: GridGraphWorld, SequenceWorld, RuleWorld
- Passing unit/base tests
- Cross-domain transfer experiments
- Statistical replication scripts
- Clean ablation runner scaffold
```

But TAIS has not yet fully proven the base model claim.

The next stage is to prove which components are load-bearing and then extend into ChemistryLite and additional domains.

---

# Roadmap Overview

```text
Phase 0 — Stabilize the codebase
Phase 1 — Clean ablation suite
Phase 2 — Fix RuleWorld metrics and evaluation design
Phase 3 — Prove or falsify ActionRole transfer
Phase 4 — Add closer transfer domain: HazardGraphWorld
Phase 5 — Add ChemistryLiteDomain
Phase 6 — Repair convergence experiments
Phase 7 — Cultural memory under cost
Phase 8 — Long-horizon planning
Phase 9 — Multi-domain curriculum
Phase 10 — Paper-grade benchmarks and baselines
Phase 11 — Scaling and GPU/vectorization
Phase 12 — Research paper packaging
```

---

# Phase 0 — Stabilize the Codebase

## Goal

Make the current codebase coherent, reproducible, and easy to test.

## Why

Right now there are several generations of TAIS code:

```text
swarm_v3.py
swarm_v4.py
swarm_v5.py
tais_core/
experiments_*.py
```

The research base should be separated from experimental prototypes.

## Tasks

### 0.1 Clean package structure

Target:

```text
tais_core/
  reality.py
  memory.py
  speech.py
  mote.py
  domains/
    gridworld.py
    sequences.py
    rules.py
    hazard.py
    chemistry_lite.py
  experiments/
    ablation_runner.py
    transfer_runner.py
    repair_runner.py
    cultural_memory_runner.py
  analysis/
    stats.py
    plotting.py
  tests/
```

Current scripts can remain at root for now, but paper-grade work should move into a clean package.

### 0.2 Add versioned experiment outputs

Every run should save:

```text
config
commit/hash or timestamp
random seeds
condition names
raw per-seed rows
summary statistics
plots later
```

Output format:

```text
runs/YYYYMMDD_HHMM_experiment_name/
  config.json
  raw.csv
  summary.json
  summary.md
```

### 0.3 Freeze current baseline tests

Maintain:

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

Acceptance:

```text
All tests pass before every experiment.
```

---

# Phase 1 — Clean Ablation Suite

## Goal

Determine which core components are load-bearing.

## Why

A system with many components can appear to work for the wrong reason. Ablations tell us whether ActionRole, pattern memory, prediction, and prior decay actually matter.

## Conditions

Run:

```text
full
no_action_role
no_prior_decay
no_pattern_transfer
no_prediction
empty_pretrain
random_pretrain
ruleworld_pretrain
```

## Core experiment

```text
Source: mixed GridGraphWorld
Target: RuleWorld
Seeds: 200 minimum, 1000 preferred for final paper
Pretraining: 20 ticks
Evaluation: 12, 30, 50, 100 ticks
```

## Metrics

```text
eval-only reward
time to first apply_implication
invalid actions
final energy
prediction error
transfer prior uses
transfer prior strength
transfer prior precision
semantic/speech metrics if used
```

## Critical metric fix

Use strict task metric:

```text
first_apply_implication_tick
```

Not:

```text
first positive consequence
```

Because verify_rule can produce positive reward and obscure the real task.

## Acceptance criteria

A component is load-bearing if removing it causes predictable degradation:

```text
no_action_role → weaker/fewer early transfer benefits
no_pattern_transfer → transfer prior uses collapse and transfer advantage drops
no_prediction → prediction error worsens
no_prior_decay → longer-run negative transfer or over-persistence increases
```

## Deliverables

```text
experiments_ablation_runner.py
ablation_results.csv
ablation_results.json
ablation_report.md
```

---

# Phase 2 — Fix RuleWorld Evaluation

## Goal

Make RuleWorld a sharper test of rule-based task solving.

## Current issue

`verify_rule` can give reward. This makes the task too easy and allows agents to score without applying implication.

## Changes

### 2.1 Reward structure

Suggested:

```text
apply_implication: +4.0 reward
verify_rule: +0.1 or +0.2 reward
random_assert: -3.0 penalty
invalid action: clear penalty
```

### 2.2 Add explicit target

Graph should include:

```text
TARGET_FACT
```

Then `evaluate()` measures:

```text
is target derived?
```

### 2.3 Add harder RuleWorld variants

```text
RuleWorldEasy: one implication
RuleWorldChain: A -> B -> C
RuleWorldException: A -> B unless X
RuleWorldDistractor: many irrelevant rules
```

## Acceptance

Full system should solve easy version reliably.
Harder versions should separate conditions more clearly.

---

# Phase 3 — Prove/Falsify ActionRole Transfer

## Goal

Show ActionRole is the mechanism behind early cross-domain transfer, or discover that it is not.

## Experiments

### 3.1 Mixed GridWorld → RuleWorld

Run:

```text
full vs no_action_role
```

### 3.2 Danger-only GridWorld → RuleWorld

Expected:

```text
transfers caution, not goal pursuit
```

### 3.3 Approach-only GridWorld → RuleWorld

Expected:

```text
faster apply_implication, perhaps more invalid actions
```

### 3.4 Role-balanced curriculum

Expose:

```text
APPROACH_GOOD
AVOID_BAD
VERIFY_UNCERTAIN
EXPLORE_UNCERTAIN
```

Expected:

```text
best early transfer profile
```

## Acceptance

Paper-worthy result:

```text
Role-balanced source curriculum produces statistically significant early target-domain improvement.
No ActionRole ablation weakens the effect.
```

---

# Phase 4 — Add HazardGraphWorld

## Goal

Test closer domain transfer before jumping into chemistry or logic.

## Why

GridWorld → RuleWorld is a large jump:

```text
spatial survival → symbolic inference
```

HazardGraphWorld is a closer intermediate:

```text
graph navigation with rewarding and dangerous nodes
```

## Domain design

Entities:

```text
AGENT
NODE
RESOURCE_NODE
HAZARD_NODE
EXIT_NODE
```

Relations:

```text
CONNECTED_TO
NEAR
BLOCKED_BY
LEADS_TO
```

Actions:

```text
move_to_neighbor
verify_node
avoid_hazard
approach_resource
```

Consequences:

```text
resource reached → reward
hazard reached → penalty
exit reached → reward
invalid edge → penalty
```

## Transfer tests

```text
GridWorld → HazardGraphWorld
HazardGraphWorld → RuleWorld
GridWorld → HazardGraphWorld → RuleWorld
```

## Acceptance

Expected stronger transfer than GridWorld → RuleWorld.

If close-domain transfer fails, the analogy/action-role mechanism is still too weak.

---

# Phase 5 — ChemistryLiteDomain

## Goal

Move from toy symbolic domains toward a scientific design domain.

## Why

ChemistryLite is the first domain that makes TAIS relevant to real scientific search, without overclaiming real drug discovery.

## Domain representation

Entities:

```text
MOLECULE
ATOM
BOND
FRAGMENT
TOXIC_GROUP
BINDING_SITE
POLAR_GROUP
HYDROPHOBIC_GROUP
SIZE_LIMIT
```

Relations:

```text
BONDED_TO
PART_OF
ADJACENT_TO
BINDS_TO
CLASHES_WITH
HAS_GROUP
NEAR_SITE
VIOLATES
SATISFIES
```

Actions:

```text
add_fragment
remove_fragment
replace_fragment
verify_valence
check_toxicity
improve_binding
reduce_size
```

Constraints:

```text
max valence
max atom count
no toxic group adjacent to binding site
binding contact required
size/polarity constraints
```

Consequence examples:

```text
valid fragment addition → reward
invalid valence → penalty
toxic group near binding site → penalty + DANGER concept
binding contact improved → reward + RESOURCE/GOOD concept
size too large → penalty
```

## Transfer experiments

```text
GridWorld mixed → ChemistryLite
HazardGraphWorld → ChemistryLite
RuleWorld → ChemistryLite
```

## Baselines

```text
fresh
empty pretrain
random pretrain
same-domain ChemistryLite pretrain
```

## Metrics

```text
valid molecule rate
toxicity violations
binding score proxy
first valid improvement tick
final chemistry score
energy efficiency
prediction error
transfer prior precision
```

## Acceptance

Minimum paper signal:

```text
Grid/Hazard pretraining reduces toxic/invalid actions or improves early valid-binding score vs fresh/random controls.
```

Strong signal:

```text
ActionRole ablation removes ChemistryLite transfer benefit.
```

---

# Phase 6 — Repair Convergence

## Goal

Prove repair is load-bearing for shared meaning.

## Why

The speech system mechanically supports repair, but convergence has not been proven.

## Experiment design

Create two colonies:

```text
Colony A: ka ≈ DANGER
Colony B: ka ≈ RESOURCE
```

Let them interact in a shared world.

Conditions:

```text
repair enabled
repair disabled
```

Metrics:

```text
semantic success rate
misaction rate
trust recovery
time to convergence
lexicon divergence over time
repair count
```

## Acceptance

Repair enabled should show:

```text
semantic success rises faster
lexicon divergence decreases
misactions decrease
trust stabilizes
```

If repair does nothing, it is not load-bearing yet.

---

# Phase 7 — Cultural Memory Under Cost

## Goal

Test whether a cultural archive improves learning without violating thermodynamic grounding.

## Why

If archive queries are free, cultural memory becomes a cheat. It must cost energy or opportunity.

## Experiment

Conditions:

```text
no archive
archive free
archive costly
archive costly + limited query budget
```

Metrics:

```text
learning speed
energy economy
query frequency
archive precision
performance per query cost
```

## Acceptance

Useful cultural memory should:

```text
improve learning under moderate query cost
be worse or wasteful under high query cost
show strategic query behavior
```

---

# Phase 8 — Long-Horizon Planning

## Goal

Extend TAIS from short-horizon action selection to multi-step problem solving.

## Current limitation

Current mote loop is mostly:

```text
observe → choose one action → consequence
```

Hard domains need:

```text
subgoals
plans
chains
backtracking
```

## Additions

### 8.1 Goal representation

Use graph/evaluation target:

```text
goal = state with higher evaluate()
```

### 8.2 Plan fragments

Store:

```text
pattern → action sequence → consequence
```

### 8.3 Subgoal memory

```text
current state
subgoal state
expected action chain
confidence
```

### 8.4 Planning actions

Universal actions:

```text
PLAN
SIMULATE
BACKTRACK
COMMIT
ABANDON
```

## Test domains

```text
RuleWorldChain
SequenceWorld multi-step
ChemistryLite multi-fragment build
```

## Acceptance

Motes should solve tasks requiring >1 correct transformation where greedy one-step action fails.

---

# Phase 9 — Multi-Domain Curriculum

## Goal

Test whether motes learn better after diverse domain exposure.

## Curriculum types

```text
narrow: one role/domain only
mixed role: approach + avoid + verify + explore
multi-domain: Grid + Sequence + Rule + Hazard
self-selected: mote chooses domains/tasks
```

## Metrics

```text
new-domain learning speed
transfer precision
role diversity
prediction error slope
invalid action rate
energy efficiency
```

## Hypothesis

```text
Role-diverse curricula outperform deep narrow curricula for new-domain adaptation.
```

## Acceptance

Multi-role/multi-domain curriculum should generalize better than single-role pretraining.

---

# Phase 10 — Paper-Grade Benchmarks

## Goal

Produce a defensible research paper.

## Required experiments

### Experiment A — Base interface

Same mote across:

```text
GridGraphWorld
HazardGraphWorld
SequenceWorld
RuleWorld
ChemistryLite
```

No mote code changes.

### Experiment B — Cross-domain transfer

At least three domain pairs:

```text
Grid → Hazard
Grid → Rule
Grid/Hazard → ChemistryLite
Sequence → Rule
```

### Experiment C — Ablations

```text
full
no ActionRole
no PatternMemory
no Prediction
no PriorDecay
no Repair
```

### Experiment D — Repair convergence

```text
repair enabled vs disabled
```

### Experiment E — Cultural memory

```text
archive costly vs no archive
```

## Statistical standards

```text
200 seeds exploratory
1000 seeds final where feasible
95% confidence intervals
p-values
effect sizes
learning curves
raw data released
```

## Baselines

```text
fresh mote
empty pretraining
random pretraining
same-domain pretraining
random policy
history-only policy
prediction-only policy
```

---

# Phase 11 — Scaling and Optimization

## Goal

Make larger experiments practical.

## Tasks

### 11.1 Headless batch runner

```text
parallel seeds
multiprocessing
structured result folders
resume failed runs
```

### 11.2 Vectorization

Move from object loops to arrays where possible:

```text
mote energy arrays
trust matrices
lexicon tensors
pattern indices
```

### 11.3 GPU later

Your GTX 1650 can help once state is tensorized, but current code is Python-object bound.

### 11.4 Profiling

Measure:

```text
graph analogy cost
pattern matching cost
speech audit cost
world stepping cost
```

Optimize the bottleneck that actually dominates.

---

# Phase 12 — Research Paper Packaging

## Target claim

A careful claim:

```text
TAIS demonstrates that thermodynamic, speech-capable motes operating over typed
RealityGraphs can transfer functional action roles across domains under controlled
curricula, with statistically significant early learning improvements and measurable
semantic repair dynamics.
```

Avoid overclaiming:

```text
not AGI
not real drug discovery
not human-like language
not theorem proving at scale
```

## Possible title

```text
Consequence Before Language: Thermodynamic Agent Swarms for Grounded Communication and Cross-Domain Role Transfer
```

or:

```text
RealityGraphs and ActionRoles: A Grounded Multi-Agent Substrate for Cross-Domain Transfer
```

## Paper contributions

```text
1. RealityGraph universal substrate
2. UniversalMote thermodynamic architecture
3. Emergent speech + repair + audit
4. ActionRole mechanism for cross-domain transfer
5. Controlled transfer and ablation experiments
```

## Paper figures

```text
architecture diagram
RealityGraph examples across domains
ActionRole transfer diagram
learning curves
ablation table
repair convergence plot
ChemistryLite transfer plot
```

## Paper artifacts

```text
code
tests
experiment configs
raw CSVs
result notebooks
reproduction instructions
```

---

# Immediate Next 10 Tasks

1. Fix/confirm ablation runner metrics:
   ```text
   first_apply_implication_tick, eval-only reward, strict invalid action count
   ```

2. Rerun ablation suite with:
   ```text
   full, no_action_role, no_prior_decay, no_pattern_transfer, no_prediction,
   empty, random, ruleworld controls
   ```

3. Run horizons:
   ```text
   12, 30, 50, 100 ticks
   ```

4. Build HazardGraphWorld.

5. Run Grid → Hazard transfer.

6. Build ChemistryLiteDomain.

7. Run Grid/Hazard → ChemistryLite transfer.

8. Build repair convergence experiment.

9. Build cultural memory cost experiment.

10. Write first draft of paper methods section using only validated claims.

---

# Success Criteria for Breakthrough-Level TAIS

TAIS reaches research breakthrough level when it satisfies:

```text
1. Same mote runs 5+ domains without architecture changes.
2. Cross-domain transfer improves early learning in 2+ domain pairs.
3. Empty/random controls do not explain the effect.
4. ActionRole and PatternMemory ablations reduce the effect.
5. Prediction ablation worsens prediction/calibration.
6. Repair ablation worsens semantic convergence.
7. ChemistryLite shows transfer into structured design.
8. Results replicate with statistical significance.
```

At that point, TAIS has a defensible claim:

```text
not AGI,
but a new grounded multi-agent substrate for role-based transfer and emergent communication.
```
