# TAIS Base Model Criteria

## The central question

How do we know the TAIS core is the base model, not just another prototype?

We cannot prove once and forever that no upgrade will ever be useful. But we can know when the **conceptual base** is stable enough that new capabilities should be built as domains, curricula, tools, or memory extensions — not by changing the mote itself.

The base becomes real when:

```text
same mote
same memory
same speech
same action loop
same consequence loop
many worlds
measurable transfer
```

## What counts as the base

The base is not a UI, not a GridWorld, not chemistry, not a particular token set.

The base is the invariant substrate:

```text
Thermodynamic Core
+ Epistemic State
+ Universal Action Interface
+ Speech/Repair/Trust
+ Pattern Memory
+ Prediction Loop
+ Consequence Feedback
```

In code terms:

```text
RealityGraph
MoteMemory
SpeechOrgan
Transformation
Constraint
Consequence
WorldInterface
```

Everything else is an application if it can be added without changing those concepts.

## The Base Model Invariants

### Invariant 1 — Domain Blindness

A mote must not contain chemistry-specific, math-specific, physics-specific, or law-specific logic.

Pass condition:

```text
The same Mote class runs in GridWorld, RuleWorld, SequenceWorld, and ChemistryLite.
```

Fail condition:

```text
We need ChemistryMote, MathMote, PhysicsMote, etc.
```

### Invariant 2 — Four-function world interface

Every domain must be expressible as:

```python
observe(graph, mote_state) -> subgraph
valid_actions(graph, mote_state) -> list[Transformation]
act(graph, transformation, mote_state) -> (graph, Consequence)
evaluate(graph, mote_state) -> float
```

Pass condition:

```text
New domains are added by implementing the interface, not by changing the mote.
```

Fail condition:

```text
A domain requires a new learning loop inside the mote.
```

### Invariant 3 — Consequence is the only teacher

The world teaches through:

```text
reward
penalty
validity
concept signals
explanation
prediction error
graph delta
```

Pass condition:

```text
Motes improve using Consequence objects across domains.
```

Fail condition:

```text
A domain requires hidden labels or direct hand-coded mote updates.
```

### Invariant 4 — Pattern transfer

A useful pattern from one domain must be representable and testable in another domain.

Example:

```text
GridWorld: THREAT near RESOURCE
Chemistry: TOXIC_GROUP near BINDING_SITE
Law: EXCEPTION near OBLIGATION
Math: INVALID_OPERATION near TARGET_EXPRESSION
```

Pass condition:

```text
PatternMemory.transfer_to(new_graph) gives useful analogies.
```

Fail condition:

```text
Patterns are trapped inside their original domain.
```

### Invariant 5 — Prediction loop

Motes must predict before acting.

Pass condition:

```text
Prediction error decreases over repeated exposure.
```

Fail condition:

```text
Motes only react after reward and form superstitious associations.
```

### Invariant 6 — Speech is portable

A token learned through consequence in one domain should be testable in another.

Example:

```text
ka means danger in GridWorld.
ka becomes useful for toxicity in ChemistryLite.
```

Pass condition:

```text
Cross-domain token priors improve early performance or communication.
```

Fail condition:

```text
Language resets completely in every domain and no meaning transfers.
```

### Invariant 7 — Repair exists

Miscommunication must be correctable.

Pass condition:

```text
Repeated repair increases semantic success rate.
```

Fail condition:

```text
Semantic drift cannot be corrected except by external intervention.
```

### Invariant 8 — Culture is optional but compatible

The base must work with no archive, heritable memory, or cultural memory.

Pass condition:

```text
A: individual-only learning works.
B: heritable priors improve learning.
C: cultural archive improves learning further.
```

Fail condition:

```text
The base depends on a global archive to function at all.
```

## The Breakthrough Test Battery

The base can be considered stable when it passes this battery.

### Test 1 — Same Mote, Three Domains

Train one universal mote lineage across:

```text
GridWorld → SequenceWorld → RuleWorld
```

No mote code changes.

Measure:

```text
performance per domain
prediction error
semantic rate
pattern transfer count
```

### Test 2 — Transfer Advantage

Compare:

```text
fresh motes in domain B
vs
motes pretrained in domain A then moved to domain B
```

Pass if pretrained motes need fewer actions/ticks to reach the same performance.

### Test 3 — Token Migration

Teach or evolve a token in one domain.

Example:

```text
ka → DANGER in GridWorld
```

Move descendants to ChemistryLite.

Pass if:

```text
ka becomes associated with toxic/invalid/harmful patterns faster than random tokens.
```

### Test 4 — Pattern Analogy Usefulness

Store patterns in one domain and transfer them into another.

Pass if transferred patterns cause measurable improvement over random action selection.

### Test 5 — Repair Convergence

Force semantic mismatch between two colonies.

Pass if repair signals reduce misunderstanding and increase semantic success.

### Test 6 — Prediction Error Reduction

In each domain, prediction error must decrease with experience.

This is the anti-superstition test.

### Test 7 — New Domain Injection

Add a domain the mote has never seen.

Pass if the domain can be added by implementing only:

```text
observe
valid_actions
act
evaluate
```

No mote edits.

### Test 8 — Ablation

Remove one base organ at a time:

```text
no speech
no repair
no pattern memory
no prediction
no cultural memory
no trust
```

Pass if each removal causes a predictable performance drop.

If removing an organ does nothing, that organ is not part of the true base.

## When to freeze the base API

Freeze the base API when:

```text
1. Three domains run with the same mote.
2. Cross-domain transfer is measurable.
3. Repair improves semantic alignment.
4. Prediction error decreases.
5. New domains require no mote modifications.
6. Ablations show each core organ matters.
```

At that point, freeze these abstractions:

```text
Entity
Relation
RealityGraph
GraphPattern
Transformation
Constraint
Consequence
MoteMemory
SpeechOrgan
WorldInterface
```

After freeze, improvements should be:

```text
domain modules
curricula
optimizations
tools
visualization
benchmarks
archive policies
```

not changes to the core identity of the mote.

## What can still change after freeze

Even after the base is validated, implementation can improve:

```text
speed
GPU vectorization
storage
better analogy search
better graph indexing
larger memory capacity
more efficient speech delivery
```

These are engineering upgrades, not conceptual upgrades.

The base breakthrough is conceptual stability, not perfect implementation.

## Definition of the Breakthrough

TAIS becomes a base model when:

```text
An energy-budgeted, epistemic, speech-capable mote can enter any typed RealityGraph,
observe a local subgraph, choose universal transformations, predict consequences,
learn from validity/reward/error, communicate patterns to other motes, repair
misunderstanding, preserve useful patterns, and transfer strategies across domains
without changing its internal architecture.
```

If that holds, then chemistry, math, physics, law, language, quantum circuits,
research, and everything else are no longer separate AI systems.

They are environments inside the same learning ecology.
