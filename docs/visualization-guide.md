# TAIS Visualization Guide

## Purpose

The visualization layer converts experiment artifacts and mote trajectories into publication-ready figures.

## Modules

### `transfer_heatmap`

Effect-size heatmaps. Use `plot_transfer_heatmap()` with a matrix of Cohen's d values, or `heatmap_from_summary_rows()` to read directly from Phase D CSV summaries.

```python
from tais_core.viz import heatmap_from_summary_rows, plot_transfer_heatmap

rows = load_summary_csv("results/phase_d/composition/composition.csv")
matrix, rows, cols = heatmap_from_summary_rows(rows, ["grid_only", "rules_only"], "first_task_success_tick")
plot_transfer_heatmap(matrix, rows, cols, output="heatmap.png")
```

### `ablation_radar`

Multi-metric condition comparison using polar radar charts. `normalize_summary_for_radar()` converts CSV summaries to [0,1]-normalized series.

```python
from tais_core.viz import normalize_summary_for_radar, plot_radar_chart

rows = load_summary_csv("results/phase_d/cognitive_contribution/cognitive_contribution.csv")
series = normalize_summary_for_radar(rows, ["grid_baseline", "grid_metacog"], ["reward", "prediction_error"],
                                     lower_is_better={"prediction_error"})
plot_radar_chart(series, ["reward", "prediction_error"], output="radar.png")
```

### `scaling`

Scaling law curves. `plot_scaling_from_csv()` reads the Phase D `scaling_summary.csv` directly.

```python
from tais_core.viz import plot_scaling_from_csv

plot_scaling_from_csv("results/phase_d/scaling_law/scaling_summary.csv", sweep="domain_count",
                      x_key="pretrain_domain_count", output="scaling.png")
```

### `trajectory`

Mote step-by-step trajectory export and standalone HTML viewer. `record_mote_trajectory()` runs a mote for N ticks and records per-tick state. `save_trajectory_html()` produces a self-contained viewer with no external dependencies.

```python
from tais_core import load_domain, UniversalMote
from tais_core.viz import record_mote_trajectory, save_trajectory_html

world = load_domain("chemistry_lite")
graph = world.initial_graph()
mote = UniversalMote(energy=100)
records = record_mote_trajectory(world, graph, mote, mote_position="atom_c", ticks=10)
save_trajectory_html(records, "trajectory.html")
```

### `lexicon`

Lexicon convergence utilities. `compute_pairwise_lexicon_agreement()` measures agreement across multiple lexicons. `plot_lexicon_convergence()` plots convergence score over time. Currently generic/demo until swarm artifacts are standardized.

## Generate Phase E figures

```bash
PYTHONPATH=. python experiments/phase_e/generate_figures.py \
  --phase-d results/phase_d \
  --output results/phase_e/figures
```

## Current limitations

- Plotly/D3 interactive graph rendering is deferred.
- Phase E uses Matplotlib static figures and simple standalone HTML.
- Lexicon plot helper is generic until full swarm artifacts are standardized.
- Heatmap currently reflects available Phase D summaries; full all-pairs benchmark heatmap is later TAIS-Bench work.
