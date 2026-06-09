# Phase R3 — Baseline Agents Comparison Report

**Date:** 2026-06-09  
**Seeds:** 200 | **Pretrain ticks:** 20 (GridWorld) | **Eval ticks:** 15 (LogicWorld)  
**Branch:** `phase-r3-baseline-agents`  
**Runner:** `experiments/phase_r/baseline_comparison.py`

## Design

Paired-experiment design (same seed across all 5 conditions):

| Condition | Description |
|---|---|
| **TAIS_full** | UniversalMote with all mechanisms (PatternMemory, ActionRole, transfer) |
| **TAIS_no_pattern_transfer** | UniversalMote with `transfer_action_priors` zeroed (blocks all prior transfer) |
| **RandomAgent** | Uniform random action selection (statistical baseline) |
| **HeuristicAgent** | Op-weight heuristic — prefers TRANSFORM > MUTATE > other ops |
| **TabularQAgent** | Q-learning (α=0.1, γ=0.9, ε=0.1) using `graph_structural_key()` state representation |

All agents see the same GridWorld pretrain (20 ticks, alternating threat_near_resource) and LogicWorld eval (easy variant).

## Results

### Raw Means

| Metric | TAIS_full | TAIS_no_pat_transfer | RandomAgent | HeuristicAgent | TabularQAgent |
|---|---|---|---|---|---|
| First TASK_SUCCESS tick | 8.600 | 10.665 | 11.000 | **2.000** | **3.455** |
| Task Completion Rate | 0.620 | 0.555 | 0.490 | **1.000** | **0.935** |
| Contradictions (TASK_FAILURE) | 1.000 | 1.050 | 3.390 | **0.000** | **0.675** |
| Total Reward | 3.264 | 2.813 | 2.601 | **5.150** | **4.769** |
| Invalid Actions | 1.605 | 1.665 | 6.100 | **0.000** | **0.975** |
| Final Energy | 142.695 | 141.954 | 123.927 | 126.650 | **159.934** |
| Transfer Precision | 0.845 | 0.000 | 0.000 | 0.000 | 0.000 |

### Comparison vs RandomAgent (paired)

| Metric | TAIS_full | TAIS_no_pat_transfer | HeuristicAgent | TabularQAgent |
|---|---|---|---|---|
| **First Success (d)** | **−0.285** *** | −0.044 ns | **−1.597** *** | **−1.128** *** |
| **Completion Rate (d)** | **+0.189** ** | +0.094 ns | **+1.018** *** | **+0.801** *** |
| **Contradictions (d)** | **−1.143** *** | **−1.083** *** | **−1.921** *** | **−1.459** *** |
| **Reward (d)** | **+0.229** ** | +0.072 ns | **+1.245** *** | **+0.942** *** |
| **Invalid (d)** | **−1.782** *** | **−1.738** *** | **−2.931** *** | **−2.289** *** |
| **Energy (d)** | **+1.130** *** | **+1.084** *** | **+0.210** ** | **+2.489** *** |

* p<0.05  ** p<0.01  *** p<0.001  (ns = not significant)

## Key Findings

### 1. Simple baselines dominate TAIS on LogicWorld

**HeuristicAgent achieves 100% task completion and 0 contradictions on every seed** — perfect performance on the eval domain. TabularQAgent follows at 93.5% completion. TAIS_full reaches only 62%.

The reason is straightforward: LogicWorld is a simple domain where the optimal policy is to apply TRANSFORM operations on relevant entities. The HeuristicAgent's op-weight heuristic (TRANSFORM > MUTATE > other) solves this domain directly, and TabularQAgent learns the same policy within 3-4 eval ticks.

**Impact on paper:** The paper must acknowledge that TAIS does not outperform simple, domain-appropriate baselines on the Grid→Logic transfer task. TAIS's value lies in transfer across diverse domains (3+ domain threshold from Phase F2), not in peak performance on any single domain.

### 2. TAIS_full does show significant transfer vs RandomAgent

Despite being outperformed by heuristic and RL baselines, TAIS_full beats RandomAgent on:
- First success tick: d=−0.285, p<0.001
- Task completion rate: d=+0.189, p=0.008
- Contradictions: d=−1.143, p<0.001
- Reward: d=+0.229, p=0.001

The effect sizes are moderate-to-small for speed/completion but large for contradiction avoidance (d=−1.143) and energy management (d=+1.130).

### 3. Pattern transfer contributes modestly to overall TAIS performance

TAIS_no_pattern_transfer (zeroed prior transfer) shows:
- No significant difference from RandomAgent on completion (d=+0.094 ns) or reward (d=+0.072 ns)
- Weak trend toward faster first success (d=−0.044 ns)
- Significant improvement on contradictions (d=−1.083, p<0.001), invalid actions (d=−1.738, p<0.001), and energy (d=+1.084, p<0.001)

The non-transfer components of TAIS (prediction, pattern matching, etc.) still provide significant benefit for avoiding contradictions and managing energy. However, transfer itself is the primary mechanism for task completion improvement.

### 4. TabularQAgent learns rapidly

Q-learning on the `graph_structural_key()` state representation achieves 93.5% completion by tick 3.5 on average, demonstrating that the LogicWorld state space is simple enough for tabular RL to converge within a single eval episode.

### 5. HeuristicAgent's perfect score reveals domain simplicity

The fact that a hardcoded op-weight heuristic solves LogicWorld with 100% success, 0 invalid actions, and 0 contradictions means that LogicWorld (easy variant) is not a challenging transfer target. A more complex eval domain would be needed to distinguish agent capabilities.

## Impact on TAIS Claims

| Claim | Prior stance | R3 impact |
|---|---|---|
| TAIS transfers roles across typed graph domains | Supported | Still supported (TAIS beats RandomAgent), but trivial baselines also succeed |
| PatternMemory + ActionRole are load-bearing | Supported | Still supported (no_pattern_transfer weakens performance), but effect is modest on this domain |
| Grid→Logic transfer speedup is meaningful | d=−0.238 (F2) | d=−0.285 (R3 baseline; consistent with F2) |

**The paper should note that simple op-preference heuristics and tabular Q-learning outperform TAIS on GridWorld→LogicWorld transfer.** TAIS's comparative advantage is expected to appear in multi-domain transfer settings or when domain structure requires pattern generalization beyond simple op-weight heuristics.

## Artifacts

- `results/phase_r/baseline_comparison/baseline_comparison.txt` — full ASCII table
- `results/phase_r/baseline_comparison/baseline_comparison.csv` — comparison data
- `results/phase_r/baseline_comparison/baseline_comparison.json` — summary JSON
- `results/phase_r/baseline_comparison/baseline_comparison.md` — summary markdown
- `experiments/phase_r/baseline_comparison.py` — runner
- `tais_core/baselines/` — baseline agent implementations
- `tests/test_baselines.py` — 20 tests

## Limitations

- **LogicWorld easy variant only.** More complex eval domains (hard LogicWorld, RuleWorld, HazardWorld) may show different ordering.
- **TabularQAgent uses a hand-crafted state key.** A learned representation (e.g., neural network) might generalize differently.
- **HeuristicAgent uses a domain-general op preference.** This specific heuristic (TRANSFORM > MUTATE) happens to match LogicWorld's structure but may fail in other domains.
- **No cross-validation.** Single pretrain domain (GridWorld), single eval domain (LogicWorld easy).
- **Pretrain ticks limited to 20.** Longer pretrain might improve TAIS convergence.
