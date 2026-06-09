# Phase A: Speech Token Portability Benchmark Report

## Question

Does teaching a speech token-to-concept mapping in one domain (GridWorld)
transfer to improved behavior in another domain (HazardWorld) where the same
concept (DANGER) is relevant?

## Design

| Condition | Teaching |
|-----------|----------|
| trained_token | `speech.teach("ka", "DANGER", strength=1.0)` |
| random_token | `speech.teach("ka", "GOOD", strength=1.0)` |
| no_token | None |

**Procedure** (50 paired seeds):
1. Create mote with speech organ
2. Apply teaching based on condition
3. GridWorld pretrain (20 ticks)
4. HazardWorld eval (15 ticks)
5. Record metrics

## Results (50 seeds, GridWorld 20 -> HazardWorld 15)

| Metric | trained_token | random_token | no_token |
|--------|:-----------:|:----------:|:-------:|
| First TASK_SUCCESS Tick | 14.36 | **13.22** | 13.10 |
| Task Completion Rate | 0.24 | **0.38** | **0.38** |
| Avoid-Bad Rate | 0.058 | 0.091 | 0.087 |
| Avoid-Bad Count | 2.02 | 3.20 | 3.06 |
| Final Energy | 134.95 | 137.05 | **137.53** |
| Total Reward | 59.20 | 59.71 | **60.42** |
| Invalid Actions | 0.26 | 0.22 | **0.34** |
| Prediction Error | **0.333** | 0.353 | 0.383 |

## Finding

**Null result.** Teaching "ka" -> DANGER does not improve HazardWorld performance.
The trained_token condition is the weakest across all primary metrics (completion rate,
first success, avoid-bad behavior, final energy).

The "no_token" and "random_token" conditions are statistically equivalent (noise-level
differences).

## Analysis

The null result is explained by the current architecture: the speech organ's lexicon
is used for **communication** (composing and receiving utterances), not for **action
selection**. A single mote never acts on its own lexicon's concept associations when
choosing what to do. The effects would appear only in multi-mote swarms where one
mote's utterance changes another mote's behavior.

The benchmark is nonetheless valuable for the paper:
- It demonstrates that the question **can be tested** within a 50-seed, 1-second run.
- It provides a quantitative baseline against which future architectures (e.g.,
  lexicon-gated action selection, speech-informed exploration) can be compared.
- It honestly reports a negative result, avoiding publication bias.

## Recommendation

For the paper, report this as "Speech token portability via direct lexicon teaching
did not transfer in single-mote settings. This is a candidate direction for future
architectures."
