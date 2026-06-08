from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Set

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from .common import as_float, filter_metric, save_figure


def plot_radar_chart(
    series: Mapping[str, Mapping[str, float]],
    metric_order: Sequence[str],
    title: str = "Ablation Radar Chart",
    output: str | Path | None = None,
):
    num_vars = len(metric_order)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    for label, values in series.items():
        vals = [values.get(m, 0.0) for m in metric_order]
        vals += vals[:1]
        ax.fill(angles, vals, alpha=0.08)
        ax.plot(angles, vals, linewidth=1.5, label=label)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(metric_order, fontsize=7)
    ax.set_ylim(0, 1)
    ax.set_title(title, fontsize=10, pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1), fontsize=7)
    fig.tight_layout()
    if output:
        return save_figure(fig, output)
    return fig


def normalize_summary_for_radar(
    rows: list[dict[str, str]],
    conditions: Sequence[str],
    metrics: Sequence[str],
    lower_is_better: Set[str] | None = None,
) -> dict[str, dict[str, float]]:
    if lower_is_better is None:
        lower_is_better = set()

    result: dict[str, dict[str, float]] = {}
    for cond in conditions:
        result[cond] = {}
        for m in metrics:
            r = _find_row(rows, cond, m)
            if r is not None:
                val = as_float(r, "condition_value", 0.0)
            else:
                val = 0.0
            result[cond][m] = val

    for m in metrics:
        vals = [result[c][m] for c in conditions]
        mn, mx = min(vals), max(vals)
        if mx == mn:
            for c in conditions:
                result[c][m] = 0.5
        else:
            for c in conditions:
                raw = (result[c][m] - mn) / (mx - mn)
                if m in lower_is_better:
                    raw = 1.0 - raw
                result[c][m] = raw
    return result


def _find_row(rows: list[dict[str, str]], condition: str, metric: str) -> dict[str, str] | None:
    for r in rows:
        if r.get("condition", "").strip() == condition and r.get("metric", "").strip() == metric:
            return r
    return None
