# Mega-Fused NL Challenge Report

**Date**: 2026-06-20
**Seed**: 777
**Duration**: 500 ticks (horizon limit)

---

## Scenario

1. **4-Source Mega-Fusion Pretraining** (15 ticks each):
   - GridWorld (Safety) — position: `mote`
   - RuleWorld (Logic) — position: `rule_ab`
   - CodeSynt (Synthesis) — position: `root`
   - SciEx (Methodology) — position: `hyp1`

2. **NL Grounding**:
   - Command: *"Initiate a scientific experiment to confirm the kinetics hypothesis in a noisy lab."*
   - SLM Bridge: `LLMGroundingEngine(provider="mock")` → matched `experiment`/`science` branch
   - Output: RealityGraph with `goal→hyp1` relation + `hyp1(HYPOTHESIS)` entity

3. **Hard-Mode Environment**:
   - Base SciEx graph (7 entities)
   - Merged grounded goal (goal + hyp1 entities + relation)
   - 20 injected Noise Nodes (`noise_0`…`noise_19`) with random `entropy` properties
   - **Total**: 27 entities

---

## Results

### Pretraining Phase

| Metric | Value |
|---|---|
| Patterns learned | 3 |
| Transfer prior precision | 90.7% |

### Challenge Phase

| Metric | Value |
|---|---|
| Result | **FAILED** (horizon exceeded) |
| Final tick | 499 |
| Net reward | 2.0 |
| Task signal | no explicit success |
| Explanation | *"Action resulted in net reward of 2.0. Reason: designed experiment for hypothesis"* |

### Terminal Metrics

| Metric | Value |
|---|---|
| Transfer prior uses | 6064 |
| Transfer prior precision | **99.2%** |
| Patterns accumulated | 13 |

---

## Analysis

### What worked

- **NL grounding correctly dispatched**: The `experiment`/`science` keyword branch in `_mock_ground_goal` correctly generated a `goal→hyp1` relation, matching the SciEx domain topology.
- **Massive transfer exploitation**: 6064 transfer prior uses with 99.2% precision — the mote learned to reuse cross-domain patterns aggressively.
- **Pattern growth**: From 3 post-pretrain patterns to 13 terminal patterns indicates substantial online learning during the 500-tick challenge.

### Why it failed

- **20 noise nodes overwhelm the signal**: The SciEx base graph has only ~7 entities. With 27 total entities, of which ~74% are noise, the mote's greedy action selection cannot consistently converge on the task target (`hyp1`). The 2.0 net reward shows it made partial progress (designed experiment) but never reached `TASK_SUCCESS`.
- **Horizon too short**: While 500 ticks sounds large, each step explores a single entity. With 27 entities and noise that lacks any reward signal, the probability of consistently navigating toward `hyp1` under greedy scoring is low.

### Recommendations

1. **Add attention filtering**: A pre-processing step to down-weight or prune entities with `type == "NOISE"` before the mote's action loop.
2. **Extend horizon**: 500 → 2000 ticks for 20-noise scenarios.
3. **Progressive noise injection**: Start with 0 noise, ramp to 20 over 200 ticks so the mote can lock onto the target before distractors appear.
4. **SLM mock realism**: The mock produces perfectly correct graphs. Real SLM output would introduce errors — test with noisy translations to validate robustness.

---

## Files

- `tais_core/llm_grounding.py` — Updated `_mock_ground_goal` with 4 dispatch branches
- `mega_fused_nl_test.py` — The stress test runner
