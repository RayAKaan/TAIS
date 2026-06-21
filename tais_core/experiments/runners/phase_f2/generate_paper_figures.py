#!/usr/bin/env python3
"""Phase F2 — Generate paper figures from experiment results.

Usage:
    PYTHONPATH=. python experiments/phase_f2/generate_paper_figures.py [--results-dir DIR] [--output-dir DIR]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from tais_core.viz.common import save_figure
from tais_core.viz.lexicon import plot_lexicon_convergence


def load_json(path: Path) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fig1_role_balanced(data: Dict[str, Any], output_dir: Path) -> Path:
    """Bar chart of Cohen's d for each curriculum condition."""
    conditions = ["grid_standard", "danger_only", "approach_only", "role_balanced", "logic_same_domain"]
    labels = ["Grid\nStandard", "Danger\nOnly", "Approach\nOnly", "Role\nBalanced", "Logic\nSame Domain"]

    ds = []
    for cond in conditions:
        summary = data.get(cond, {})
        m = summary.get("task_completion_rate", {})
        ds.append(m.get("d", 0))

    fig, ax = plt.subplots(figsize=(5, 3.5))
    colors = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3"]
    bars = ax.bar(range(len(conditions)), ds, color=colors, width=0.6)
    ax.axhline(0, color="gray", linestyle="--", linewidth=0.7)
    ax.set_xticks(range(len(conditions)))
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("Cohen's d (task completion rate)", fontsize=9)
    ax.set_title("Experiment 1: Role-Balanced Curriculum", fontsize=10)
    for bar, d in zip(bars, ds):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.02 * (1 if d >= 0 else -1),
                f"{d:.3f}", ha="center", va="bottom" if d >= 0 else "top", fontsize=7)
    fig.tight_layout()
    return save_figure(fig, output_dir / "fig1_role_balanced.png", dpi=200)


def fig2_repair_convergence(data: Dict[str, Any], output_dir: Path) -> Path:
    """Line plot of lexicon divergence over time for repair enabled vs disabled."""
    enabled = data.get("repair_enabled", {})
    disabled = data.get("repair_disabled", {})

    ticks_e = enabled.get("tick", [])
    div_e = enabled.get("lexicon_divergence", [])
    ticks_d = disabled.get("tick", [])
    div_d = disabled.get("lexicon_divergence", [])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 3))

    # Lexicon divergence
    ax1.plot(ticks_e, div_e, label="Repair Enabled", color="#C44E52", linewidth=1.2)
    ax1.plot(ticks_d, div_d, label="Repair Disabled", color="#4C72B0", linewidth=1.2, linestyle="--")
    ax1.set_xlabel("Tick", fontsize=9)
    ax1.set_ylabel("Lexicon Divergence", fontsize=9)
    ax1.set_title("Lexicon Divergence Over Time", fontsize=10)
    ax1.legend(fontsize=7)
    ax1.grid(True, alpha=0.3)

    # Semantic success rate
    ss_e = enabled.get("semantic_success_rate", [])
    ss_d = disabled.get("semantic_success_rate", [])
    ax2.plot(ticks_e, ss_e, label="Repair Enabled", color="#C44E52", linewidth=1.2)
    ax2.plot(ticks_d, ss_d, label="Repair Disabled", color="#4C72B0", linewidth=1.2, linestyle="--")
    ax2.set_xlabel("Tick", fontsize=9)
    ax2.set_ylabel("Semantic Success Rate", fontsize=9)
    ax2.set_title("Semantic Success Over Time", fontsize=10)
    ax2.legend(fontsize=7)
    ax2.grid(True, alpha=0.3)

    fig.tight_layout()
    return save_figure(fig, output_dir / "fig2_repair_convergence.png", dpi=200)


def fig3_domain_count_scaling(data: Dict[str, Any], output_dir: Path) -> Path:
    """Line plot of Cohen's d vs number of pretrain domains."""
    condition_map = {
        0: "fresh",
        1: "one_grid",
        2: "two_grid_rules",
        3: "three_grid_rules_chem",
        4: "four_grid_rules_chem_hazard",
        5: "five_grid_rules_chem_hazard_sequences",
    }
    x = []
    y = []
    for n_domains, cond_name in condition_map.items():
        summary = data.get(cond_name, {})
        m = summary.get("task_completion_rate", {})
        if cond_name == "fresh":
            continue
        x.append(n_domains)
        y.append(m.get("d", 0))

    fig, ax = plt.subplots(figsize=(5, 3.5))
    ax.plot(x, y, marker="o", linestyle="-", linewidth=1.5, markersize=6, color="#4C72B0")
    # Add same-domain ceiling
    logic_d = data.get("same_domain_logic", {}).get("task_completion_rate", {}).get("d", 0)
    ax.axhline(logic_d, color="#DD8452", linestyle="--", linewidth=0.8, label=f"Same-domain ceiling (d={logic_d:.3f})")
    ax.axhline(0, color="gray", linestyle=":", linewidth=0.5)
    ax.set_xlabel("Number of Pretrain Domains", fontsize=9)
    ax.set_ylabel("Cohen's d (task completion rate)", fontsize=9)
    ax.set_title("Experiment 3: Domain-Count Scaling", fontsize=10)
    ax.set_xticks(x)
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return save_figure(fig, output_dir / "fig3_domain_count_scaling.png", dpi=200)


def fig4_grid_logic_replication(data: Dict[str, Any], output_dir: Path) -> Path:
    """Bar chart of Cohen's d for each ablation in the replication."""
    conditions = ["full", "no_action_role", "no_prior_decay", "no_pattern_transfer",
                  "no_prediction", "empty_pretrain", "random_pretrain", "logic_pretrain"]
    labels = ["Full", "No Action\nRole", "No Prior\nDecay", "No Pattern\nTransfer",
              "No Predict.", "Empty\nPretrain", "Random\nPretrain", "Logic\nPretrain"]

    ds = []
    delta_vals = []
    for cond in conditions:
        summary = data.get(cond, {})
        m = summary.get("task_completion_rate", {})
        ds.append(m.get("d", 0))
        delta_vals.append(m.get("delta", 0))

    fig, ax = plt.subplots(figsize=(6, 3.5))
    colors = ["#4C72B0"] + ["#DD8452"] * 4 + ["#55A868"] * 2 + ["#8172B3"]
    bars = ax.bar(range(len(conditions)), ds, color=colors, width=0.6)
    ax.axhline(0, color="gray", linestyle="--", linewidth=0.7)
    ax.set_xticks(range(len(conditions)))
    ax.set_xticklabels(labels, fontsize=7, rotation=20)
    ax.set_ylabel("Cohen's d (task completion rate)", fontsize=9)
    ax.set_title("Experiment 4: Grid->Logic 1000-Seed Replication", fontsize=10)
    for bar, d in zip(bars, ds):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.02 * (1 if d >= 0 else -1),
                f"{d:.3f}", ha="center", va="bottom" if d >= 0 else "top", fontsize=6)
    fig.tight_layout()
    return save_figure(fig, output_dir / "fig4_grid_logic_replication.png", dpi=200)


def main():
    p = argparse.ArgumentParser(description="Generate Phase F2 paper figures")
    p.add_argument("--results-dir", type=str, default="results/phase_f2",
                   help="Directory with experiment JSON results")
    p.add_argument("--output-dir", type=str, default="results/phase_f2/figures",
                   help="Output directory for figures")
    args = p.parse_args()

    results_dir = Path(args.results_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating Phase F2 figures...", file=sys.stderr)

    # Figure 1: Role-Balanced Curriculum
    rb_path = results_dir / "role_balanced_curriculum.json"
    if rb_path.exists():
        rb_data = load_json(rb_path)
        p1 = fig1_role_balanced(rb_data, output_dir)
        print(f"  Figure 1: {p1}", file=sys.stderr)
    else:
        print(f"  Skipping Figure 1: {rb_path} not found", file=sys.stderr)

    # Figure 2: Repair Convergence
    rc_path = results_dir / "repair_convergence.json"
    if rc_path.exists():
        rc_data = load_json(rc_path)
        p2 = fig2_repair_convergence(rc_data, output_dir)
        print(f"  Figure 2: {p2}", file=sys.stderr)
    else:
        print(f"  Skipping Figure 2: {rc_path} not found", file=sys.stderr)

    # Figure 3: Domain-Count Scaling
    dc_path = results_dir / "domain_count_scaling.json"
    if dc_path.exists():
        dc_data = load_json(dc_path)
        p3 = fig3_domain_count_scaling(dc_data, output_dir)
        print(f"  Figure 3: {p3}", file=sys.stderr)
    else:
        print(f"  Skipping Figure 3: {dc_path} not found", file=sys.stderr)

    # Figure 4: Grid->Logic Replication
    gl_path = results_dir / "grid_logic_1000_replication.json"
    if gl_path.exists():
        gl_data = load_json(gl_path)
        p4 = fig4_grid_logic_replication(gl_data, output_dir)
        print(f"  Figure 4: {p4}", file=sys.stderr)
    else:
        print(f"  Skipping Figure 4: {gl_path} not found", file=sys.stderr)

    print("Done.", file=sys.stderr)


if __name__ == "__main__":
    main()
