# Phase E Visualization Report

## Summary

Implemented reusable visualization layer under `tais_core.viz`.

## Files Added

- `tais_core/viz/__init__.py`
- `tais_core/viz/common.py`
- `tais_core/viz/transfer_heatmap.py`
- `tais_core/viz/ablation_radar.py`
- `tais_core/viz/scaling.py`
- `tais_core/viz/trajectory.py`
- `tais_core/viz/lexicon.py`
- `experiments/phase_e/__init__.py`
- `experiments/phase_e/generate_figures.py`
- `tests/test_viz.py`
- `docs/visualization-guide.md`

## Figures Generated

```
chemistry_lite_trajectory.html
chemistry_lite_trajectory.json
cognitive_contribution_radar.png
composition_first_task_success_tick_heatmap.png
composition_task_completion_rate_heatmap.png
lexicon_convergence_demo.png
scaling_domain_count_d.png
scaling_horizon_d.png
```

## Test Results

```
Ran 162 tests in 4.893s
OK
```

(147 baseline + 15 new viz tests)

## Design Notes

- Matplotlib Agg backend for headless CI.
- Standalone HTML trajectory viewer with no external dependencies (inline CSS/JS, embedded JSON).
- Figure generation skips missing Phase D artifacts gracefully.
- Radar chart supports lower-is-better metric normalization.
- Scaling law plotter reads `scaling_summary.csv` directly, filtering by sweep and metric.
- Heatmap generator works with any Phase D summary CSV via `heatmap_from_summary_rows()`.

## Limitations

- Interactive D3/Plotly viewer deferred.
- Lexicon convergence currently generic/demo unless swarm artifacts are supplied.
- Heatmap currently reflects available Phase D summaries; full all-pairs benchmark heatmap is later TAIS-Bench work.

## Phase E Checkpoint Status

- [x] Visualization package exists
- [x] Transfer heatmap works
- [x] Radar chart works
- [x] Scaling plots work
- [x] Trajectory JSON export works
- [x] Trajectory HTML viewer works
- [x] Lexicon convergence helper works
- [x] Figure generation script works
- [x] Tests pass
- [x] Visualization guide exists
