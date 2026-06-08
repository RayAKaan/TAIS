# TAIS Experiment Guide

## Overview

The experiment framework lives under `tais_core/experiments/` and provides reusable
infrastructure for running paired-seed transfer-learning experiments, computing
statistical summaries, and generating reports.

## Core Concepts

- **Condition** — a named experimental treatment (e.g. "fresh", "grid_only",
  "grid_metacog") with optional `pretrain_domains` and `engines`.
- **Metric** — a named measurement with a `lower_is_better` flag.
- **TrialRecord** — a single trial's metrics for one seed + condition.
- **ExperimentResults** — container for all trial records; computes paired
  summaries, exports to JSON/CSV.
- **ExperimentReport** — generates Markdown and LaTeX tables from results.
- **ExperimentSuite** — orchestrates the full lifecycle: pretrain → evaluate →
  record for every (seed, condition) pair.

## Quick Start

```python
from tais_core.experiments import Condition, ExperimentSuite, Metric

suite = ExperimentSuite(
    name="my_experiment",
    seeds=30,
    conditions=[
        Condition("fresh"),
        Condition("grid_only", pretrain_domains=["gridworld"]),
    ],
    eval_domain="logic",
    eval_ticks=15,
    pretrain_ticks=10,
    metrics=[
        Metric("first_task_success_tick", lower_is_better=True),
        Metric("task_completion_rate"),
    ],
)

results = suite.run(output_dir="output/")
```

This writes `output/my_experiment.json`, `.csv`, `.md`, `.tex`.

## Condition Configurations

| Condition           | `pretrain_domains` | `engines`                              |
|---------------------|--------------------|----------------------------------------|
| fresh               | `[]`               | `{}`                                   |
| grid_only           | `["gridworld"]`    | `{}`                                   |
| grid_metacog        | `["gridworld"]`    | `{"metacognition": true}`             |
| grid_causal         | `["gridworld"]`    | `{"causal_reasoning": true}`           |
| grid_planning       | `["gridworld"]`    | `{"hierarchical_planning": true}`      |

## Provenance

Every run records git SHA/branch, UTC timestamp, Python version, platform, and
dependency versions (numpy, scipy, matplotlib, yaml). Access via:

```python
from tais_core.experiments.provenance import capture_provenance
prov = capture_provenance("my_experiment", {"seeds": 30})
```

## Statistics

All paired analyses compare each non-baseline condition against the baseline
("fresh") using identical seed pairs:

- **Delta** = condition_mean - baseline_mean (negative = improvement for
  `lower_is_better` metrics)
- **Cohen's d** (paired) — standardized mean difference
- **Paired t-test** (normal approximation) — p-value
- **95% CI** on delta
- **Transfer precision** — correct / (correct + incorrect) on cross-domain
  transfer lookups

## Outputs

| Format | File extension | Description                        |
|--------|---------------|------------------------------------|
| JSON   | `.json`       | Full results dict, provenance      |
| CSV    | `.csv`        | Per-trial rows for external tools  |
| Markdown| `.md`        | Human-readable summary tables      |
| LaTeX  | `.tex`        | Publication-ready table            |

## CLI Runner

```bash
python experiments/phase_c_logic_transfer_suite.py \
    --seeds 200 --eval 15 --pretrain 20 --output results/
```

## Adding a New Domain

1. Create a YAML spec under `tais_core/domains/` (see `gridworld.yaml`).
2. The framework loads it automatically via `load_domain()`.
3. Reference it by name in `pretrain_domains` or `eval_domain`.
