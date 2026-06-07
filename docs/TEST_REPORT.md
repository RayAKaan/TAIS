# TAIS Test Report

## Date

2026-06-07

## Current status

The project now has a first **Base Validation Battery** in addition to unit tests.

This is important: we are no longer only checking whether classes compile. We are now checking early evidence for the base-model claim:

```text
same mote
same memory
same speech
same prediction loop
different domains
```

## Commands run

### Full test suite

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

Result:

```text
Ran 15 tests
OK
```

### Compile check

```bash
python3 -m py_compile tais_core/*.py tais_core/domains/*.py
```

Result: OK

## Test files

```text
tests/test_tais_core.py
tests/test_base_validation.py
```

## New modules tested

```text
tais_core/mote.py
tais_core/domains/gridworld.py
tais_core/domains/sequences.py
tais_core/domains/rules.py
```

## What is now tested

### 1. RealityGraph core

Covered:

- Entity CRUD
- Relation CRUD
- neighborhood attention window
- subgraph extraction
- graph diff
- graph distance
- pattern matching
- cross-domain analogy

### 2. Memory core

Covered:

- episodic memory
- pattern memory
- pattern transfer
- cultural memory query/capacity
- prediction engine

### 3. Speech core

Covered:

- teaching
- token interpretation
- repair update
- utterance composition
- receiving utterance
- understanding audit
- repair utterance creation

### 4. WorldInterface contract

Covered with a tiny rule world:

```python
observe()
valid_actions()
act()
evaluate()
```

### 5. UniversalMote base validation

Covered:

- same `UniversalMote` runs in three different domains
- prediction error decreases in repeated SequenceWorld
- sequence pretraining gives advantage over fresh mote
- pattern transfer exists from GridWorld into RuleWorld
- brand-new domain can be injected without mote modification

## Base Validation Battery results

### Test: same mote, three domains

Domains:

```text
GridGraphWorld
SequenceWorld
RuleWorld
```

Result: PASS

Meaning:

```text
The same UniversalMote class can act in spatial survival, sequence prediction,
and rule satisfaction without domain-specific mote code.
```

### Test: prediction error reduction

Domain:

```text
SequenceWorld
```

Result: PASS

Meaning:

```text
The prediction loop is not merely cosmetic in this tiny domain. It learns an
expected consequence per transformation and prediction error decreases.
```

Implementation note:

The `PredictionEngine` was upgraded during testing to store per-transformation expected net consequence. This was necessary because the first version only predicted from pattern valence and did not reliably reduce error.

### Test: transfer advantage

Comparison:

```text
fresh mote in SequenceWorld
vs
mote pretrained in SequenceWorld
```

Result: PASS

Meaning:

```text
Experience in a domain gives measurable advantage on the same family of tasks.
```

This is not yet cross-domain transfer; it is a sanity check that learning transfers across episodes.

### Test: pattern transfer exists

Source:

```text
GridWorld pattern memory
```

Target:

```text
RuleWorld graph
```

Result: PASS

Meaning:

```text
Stored graph patterns can analogize into a new graph/domain.
```

This proves the mechanism runs. It does not yet prove it improves task performance across different domains.

### Test: new domain injection

Domain:

```text
EmptyNovelWorld
```

Result: PASS

Meaning:

```text
A brand-new domain can be added by implementing WorldInterface only. No mote modification required.
```

## What is NOT proven yet

Important distinction:

```text
The base is now testable.
It is not yet proven as the final base model.
```

Still unproven:

1. Cross-domain transfer advantage:
   ```text
   pretrain GridWorld → learn RuleWorld faster than fresh mote
   ```

2. Pattern analogy usefulness:
   ```text
   transferred patterns improve action choice, not just map structurally
   ```

3. Repair convergence over many interactions.

4. Cultural archive improves future motes under energy cost.

5. Ablation battery:
   ```text
   no speech
   no repair
   no prediction
   no pattern memory
   no trust
   no cultural archive
   ```

6. Long-horizon planning.

7. Productive compositional language.

## Scientific interpretation

The current result is meaningful but modest:

```text
TAIS now has a working universal core and an early validation battery.
```

The strongest evidence so far:

```text
- Same UniversalMote runs across multiple domain interfaces.
- Prediction error can decrease in a repeated prediction domain.
- New domains can be injected without changing the mote.
- Graph pattern analogy works mechanically.
```

The next scientific milestone is stronger:

```text
Demonstrate cross-domain transfer advantage.
```

## Next test to build

The next test should be:

```text
GridWorld pretraining → RuleWorld improvement
```

Design:

```text
Group A: fresh motes enter RuleWorld
Group B: motes pretrained in GridWorld enter RuleWorld
Compare:
  - reward after N actions
  - invalid action rate
  - prediction error
  - time to first valid inference
```

Pass condition:

```text
Group B significantly outperforms Group A.
```

That is the first real test of the base-model claim.
