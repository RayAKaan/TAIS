from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from .common import filter_metric, as_float, save_figure


def plot_transfer_heatmap(
    matrix: Sequence[Sequence[float]],
    row_labels: Sequence[str],
    col_labels: Sequence[str],
    title: str = "Transfer Effect Size Heatmap",
    output: str | Path | None = None,
    cmap: str = "coolwarm",
):
    data = np.array(matrix, dtype=float)
    fig, ax = plt.subplots(figsize=(max(3, len(col_labels) * 1.5), max(2, len(row_labels) * 0.6)))
    im = ax.imshow(data, aspect="auto", cmap=cmap, vmin=-1, vmax=1)
    fig.colorbar(im, ax=ax, label="Cohen's d")
    ax.set_xticks(range(len(col_labels)))
    ax.set_xticklabels(col_labels, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(row_labels)))
    ax.set_yticklabels(row_labels, fontsize=8)
    for i in range(len(row_labels)):
        for j in range(len(col_labels)):
            val = data[i, j]
            color = "white" if abs(val) > 0.5 else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=7, color=color)
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    if output:
        return save_figure(fig, output)
    return fig


def heatmap_from_summary_rows(
    rows: List[Dict[str, str]],
    condition_order: Sequence[str],
    metric: str = "first_task_success_tick",
    value_key: str = "d",
) -> tuple[list[list[float]], list[str], list[str]]:
    metric_rows = filter_metric(rows, metric)
    label_map: dict[str, str] = {}
    val_map: dict[str, float] = {}
    for r in metric_rows:
        cond = r.get("condition_value") or r.get("condition", "")
        label_map[cond] = cond
        val_map[cond] = as_float(r, value_key)
    matrix = [[val_map.get(c, 0.0) for _ in [metric]] for c in condition_order]
    return matrix, list(condition_order), [metric]
