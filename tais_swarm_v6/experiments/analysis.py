"""
TAIS V6 Experiment Analysis.

Statistical comparison (t-tests, Cohen's d), time-series plots, and
automated report writing.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from scipy import stats
import matplotlib.pyplot as plt


class ExperimentAnalyzer:
    def __init__(self, results_dir: str = "results"):
        self.results_dir = Path(results_dir)
        self.figures_dir = self.results_dir / "figures"
        self.figures_dir.mkdir(parents=True, exist_ok=True)

    def load_results(self, filename: str) -> List[Dict[str, Any]]:
        path = self.results_dir / filename
        with open(path) as f:
            return json.load(f)

    def compare_conditions(
        self,
        results: List[Dict[str, Any]],
        metric: str = "avg_prediction_accuracy",
        baseline: str = "full",
    ) -> Dict[str, Dict[str, float]]:
        conditions: Dict[str, List[float]] = {}
        for r in results:
            conditions.setdefault(r["ablation"], []).append(r[metric])

        if baseline not in conditions:
            raise ValueError(f"Baseline '{baseline}' not found in conditions: {list(conditions.keys())}")

        baseline_vals = np.array(conditions[baseline])
        comparisons: Dict[str, Dict[str, float]] = {}

        for cond, vals in conditions.items():
            if cond == baseline:
                continue
            vals = np.array(vals)
            t_stat, p_val = stats.ttest_ind(baseline_vals, vals)
            pooled_std = np.sqrt(
                ((baseline_vals.std(ddof=1) ** 2) + (vals.std(ddof=1) ** 2)) / 2
            )
            cohens_d = (baseline_vals.mean() - vals.mean()) / pooled_std if pooled_std > 0 else 0.0
            comparisons[cond] = {
                "mean_diff": float(baseline_vals.mean() - vals.mean()),
                "t_statistic": float(t_stat),
                "p_value": float(p_val),
                "cohens_d": float(cohens_d),
                "baseline_mean": float(baseline_vals.mean()),
                "condition_mean": float(vals.mean()),
                "n": len(baseline_vals),
            }
        return comparisons

    def plot_metric_over_time(
        self,
        results: List[Dict[str, Any]],
        metric: str = "avg_prediction_accuracy",
        conditions: Optional[List[str]] = None,
        filename: str = "metric_over_time.png",
    ):
        tick_key = metric
        record_key = metric.replace("avg_", "", 1) if metric.startswith("avg_") else metric

        plt.figure(figsize=(10, 6))
        if conditions is None:
            conditions = sorted({r["ablation"] for r in results})

        for cond in conditions:
            runs = [r for r in results if r["ablation"] == cond]
            if not runs:
                continue
            max_ticks = max(len(r["tick_records"]) for r in runs)
            trajectories = []
            for r in runs:
                traj = [t.get(record_key, t.get("avg_energy", 0)) for t in r["tick_records"]]
                traj += [traj[-1] if traj else 0] * (max_ticks - len(traj))
                trajectories.append(traj)

            mean_traj = np.mean(trajectories, axis=0)
            std_traj = np.std(trajectories, axis=0)
            x = np.arange(len(mean_traj))

            plt.plot(x, mean_traj, label=cond)
            plt.fill_between(x, mean_traj - std_traj, mean_traj + std_traj, alpha=0.2)

        plt.xlabel("Tick")
        plt.ylabel(metric.replace("_", " ").title())
        plt.title(f"{metric.replace('_', ' ').title()} Over Time")
        plt.legend()
        plt.tight_layout()
        path = self.figures_dir / filename
        plt.savefig(path, dpi=150)
        plt.close()
        print(f"Saved figure: {path}")

    def plot_final_comparison(
        self,
        results: List[Dict[str, Any]],
        metrics: Optional[List[str]] = None,
        filename: str = "final_comparison.png",
    ):
        if metrics is None:
            metrics = [
                "avg_prediction_accuracy",
                "total_plans_completed",
                "avg_causal_links",
                "avg_lexicon_size",
            ]

        conditions = sorted({r["ablation"] for r in results})
        data: Dict[str, List[float]] = {m: [] for m in metrics}
        errors: Dict[str, List[float]] = {m: [] for m in metrics}

        for cond in conditions:
            runs = [r for r in results if r["ablation"] == cond]
            for m in metrics:
                vals = [r[m] for r in runs]
                data[m].append(np.mean(vals))
                errors[m].append(np.std(vals))

        x = np.arange(len(conditions))
        width = 0.15
        fig, ax = plt.subplots(figsize=(12, 6))

        for i, m in enumerate(metrics):
            offset = (i - len(metrics) / 2) * width
            ax.bar(
                x + offset,
                data[m],
                width,
                yerr=errors[m],
                label=m.replace("_", " ").title(),
                capsize=3,
            )

        ax.set_ylabel("Value")
        ax.set_title("Ablation Study: Final Metrics by Condition")
        ax.set_xticks(x)
        ax.set_xticklabels(conditions, rotation=15, ha="right")
        ax.legend()
        plt.tight_layout()
        path = self.figures_dir / filename
        plt.savefig(path, dpi=150)
        plt.close()
        print(f"Saved figure: {path}")

    def generate_report(
        self,
        results: List[Dict[str, Any]],
        comparisons: Dict[str, Dict[str, float]],
        filename: str = "analysis_report.md",
    ):
        conditions = sorted({r["ablation"] for r in results})
        lines = [
            "# TAIS V6 Ablation Analysis Report",
            "",
            f"**Total runs:** {len(results)}",
            f"**Conditions:** {', '.join(conditions)}",
            "",
            "## Statistical Comparisons vs. Full Substrate",
            "",
            "| Condition | Mean Diff | t-stat | p-value | Cohen's d |",
            "|-----------|-----------|--------|---------|-----------|",
        ]
        for cond, comp in comparisons.items():
            lines.append(
                f"| {cond} | {comp['mean_diff']:.4f} | {comp['t_statistic']:.3f} "
                f"| {comp['p_value']:.4f} | {comp['cohens_d']:.3f} |"
            )

        lines.extend([
            "",
            "## Interpretation",
            "",
            "- **|d| > 0.2**: Small effect.",
            "- **|d| > 0.5**: Medium effect. The module likely contributes meaningfully.",
            "- **|d| > 0.8**: Large effect. The module is critical.",
            "- **p < 0.05**: Statistically significant difference.",
            "",
            "## Recommendations",
            "",
        ])

        critical = [
            c for c, comp in comparisons.items()
            if abs(comp["cohens_d"]) > 0.5 and comp["p_value"] < 0.05
        ]
        if critical:
            lines.append(
                f"Modules with strong evidence of contribution: **{', '.join(critical)}**."
            )
        else:
            lines.append(
                "No single module dominated; substrate performance may be robustly distributed "
                "or synergistic effects are required."
            )

        lines.extend(["", "---", "*Generated by TAIS V6 ExperimentAnalyzer*"])
        path = self.results_dir / filename
        with open(path, "w") as f:
            f.write("\n".join(lines))
        print(f"Saved report: {path}")
