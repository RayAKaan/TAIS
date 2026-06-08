from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from .common import as_float, load_summary_csv, save_figure


def plot_scaling_curve(
    x: Sequence[float],
    y: Sequence[float],
    xlabel: str,
    ylabel: str,
    title: str,
    output: str | Path | None = None,
):
    fig, ax = plt.subplots(figsize=(5, 3.5))
    ax.plot(list(x), list(y), marker="o", linestyle="-", linewidth=1.5, markersize=5)
    ax.axhline(0, color="gray", linestyle="--", linewidth=0.7)
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_title(title, fontsize=10)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    if output:
        return save_figure(fig, output)
    return fig


def plot_scaling_from_csv(
    csv_path: str | Path,
    sweep: str,
    x_key: str,
    metric: str = "first_task_success_tick",
    y_key: str = "d",
    output: str | Path | None = None,
):
    rows = load_summary_csv(csv_path)
    sweep_rows = [r for r in rows if r.get("sweep", "").strip() == sweep]
    metric_rows = [r for r in sweep_rows if r.get("metric", "").strip() == metric]

    points: list[tuple[float, float]] = []
    for r in metric_rows:
        xv = as_float(r, x_key)
        yv = as_float(r, y_key)
        points.append((xv, yv))

    points.sort(key=lambda p: p[0])
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    xlabel = x_key.replace("_", " ").title()
    ylabel = f"Cohen's d ({metric})"
    title = f"Scaling: {sweep.replace('_', ' ').title()} — {metric}"
    return plot_scaling_curve(xs, ys, xlabel, ylabel, title, output=output)
