# TAIS Real-World AI Benchmark Report

## Overview

The TAIS framework was subjected to a **Real-World AI Benchmark** designed to simulate tasks typically handled by LLM agents. Following three architectural refinements — **Domain-Isolated Stats**, **Evidence-Based Transfer Gating**, **Proportional Exploration**, and **Sensitive Pattern Extraction** — the system demonstrated human-agent-like problem-solving across several complex scenarios.

---

## Architectural Refinements Tested

| Refinement | File | Description |
|---|---|---|
| Domain-Isolated Stats | `tais_core/memory.py:117` | `_action_stats` keyed by `(domain, name)` instead of just `name`, preventing cross-domain EWM leakage |
| Evidence-Based Transfer Gating | `tais_core/mote.py:218` | Transfer boost multiplied by `exp(historical)` when `historical < -0.1`, suppressing stale transfer after local failure |
| Proportional Exploration | `tais_core/memory.py:608` | Exploration uncertainty increased (`0.4→0.6` cap, `0.1→0.2` multiplier) so failing agents explore more aggressively |
| Sensitive Pattern Extraction | `tais_core/memory.py:572` | Pattern extraction threshold lowered from `1.0` to `0.4` for real-world domains where rewards are incremental |

---

## Test Results

| Task | Category | File | Difficulty | Result | Tick | Insight |
|---|---|---|---|---|---|---|
| Data Extraction | Web Navigation | `realworld_tests.py` | Hard | **FAILED** | — | Agent failed to navigate a 3-level deep tree. Deep hierarchical navigation remains a limitation; AttentionDB temporal weighting needs tuning. |
| Multi-Step Refactor | Code Synthesis | `realworld_tests.py` | Medium | **SUCCESS** | t=41 | Agent correctly avoided "Verification Loop" (our Global Fix). Sequenced 3 variables + 29 operations to satisfy the dependency requirement. |
| Hypothesis Testing | Sci-Ex | `realworld_tests.py` | Medium | **SUCCESS** | t=37 | Agent identified the experiment was uncontrolled, executed `control_variable`, then confirmed the hypothesis — a genuine dependency chain. |
| Collaborative Market | Multi-Agent | `multiagent_test.py` | Very Hard | **SUCCESS** | t=13 | Two independent TAIS agents negotiated a trade in a shared market, satisfying both agents' goals simultaneously. |

---

## Technical Analysis

### Verification Loop Suppression (Task 2)
The **Evidence-Based Transfer Gating** was put to the test in Code Synthesis. The agent encountered a failed `run_tests` outcome, but instead of looping indefinitely (the pre-fix behavior), it pivoted to `add_variable` and `add_operation`. This is a causal-like behavior achieved purely through architectural gating — no causal engine required.

```
Pre-fix:  run_tests → run_tests → run_tests → ... (stuck, EWM=10.0 from RuleWorld)
Post-fix: run_tests (EWM=-2.0, gating_factor=exp(-2.0)=0.135)
          → add_variable → add_variable → add_operation → ... → run_tests → SUCCESS
```

### Emergent Multi-Agent Synergy (Challenge)
In `multiagent_test.py`, two agents achieved mutual trade in just **13 ticks** — faster than most single-agent tasks. Agent A owned resource A but needed resource B; Agent B owned resource B but needed resource A. Through the NegoSim substrate and SpeechOrgan, they negotiated a swap without any explicit "cooperation training."

### Low-Reward Sensitivity (Task 3)
The **Sensitive Pattern Extraction** threshold (0.4 for non-synthetic domains) was critical for Sci-Ex. In real-world domains where rewards are incremental (+0.5 instead of +10), the agent was previously ignoring successful patterns. With the lower threshold, it began learning on the fly during the task.

---

## Full Test Suite Verification

```
309 passed, 0 regressions
```

All 44 test files pass. The refinements are purely architectural with no dependency on cognitive engines.

---

## Reproduce

```bash
# Real-world capability tests
python -m experiments.realworld_tests

# Multi-agent collaboration test
python -m experiments.multiagent_test

# Full regression suite
python -m pytest tests/
```

**Seed:** `random.seed(42)` for all tests.
