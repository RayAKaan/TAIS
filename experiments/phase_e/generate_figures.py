from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tais_core import load_domain, UniversalMote
from tais_core.viz import (
    heatmap_from_summary_rows,
    normalize_summary_for_radar,
    plot_radar_chart,
    plot_scaling_from_csv,
    plot_transfer_heatmap,
    record_mote_trajectory,
    save_trajectory_html,
    save_trajectory_json,
    plot_lexicon_convergence,
)
from tais_core.viz.common import load_summary_csv


def glob_csv(root: str) -> list[Path]:
    return list(Path(root).rglob("*.csv"))


def find_csv(root: str, name: str) -> Path | None:
    for p in glob_csv(root):
        if p.name == name:
            return p
    return None


def generate_composition_figures(phase_d_root: str, output_dir: str):
    csv_path = find_csv(phase_d_root, "composition.csv")
    if csv_path is None:
        print("SKIP composition: composition.csv not found")
        return
    rows = load_summary_csv(csv_path)
    condition_order = [
        "fresh",
        "grid_only",
        "rules_only",
        "grid_plus_rules",
        "rules_plus_grid",
        "logic_same_domain",
    ]
    for metric in ["first_task_success_tick", "task_completion_rate"]:
        matrix, row_labels, col_labels = heatmap_from_summary_rows(
            rows, condition_order, metric=metric, value_key="d"
        )
        out = Path(output_dir) / f"composition_{metric}_heatmap.png"
        plot_transfer_heatmap(
            matrix, row_labels, col_labels,
            title=f"Composition — {metric} (Cohen's d)",
            output=str(out), cmap="coolwarm",
        )
        print(f"  wrote {out}")


def generate_cognitive_radar(phase_d_root: str, output_dir: str):
    csv_path = find_csv(phase_d_root, "cognitive_contribution.csv")
    if csv_path is None:
        print("SKIP cognitive_contribution: CSV not found")
        return
    rows = load_summary_csv(csv_path)
    conditions = [
        "grid_baseline",
        "grid_metacog",
        "grid_causal",
        "grid_planning",
        "grid_all_engines",
        "all_engines_no_pretrain",
    ]
    metrics = [
        "first_task_success_tick",
        "task_completion_rate",
        "reward",
        "invalid_actions",
        "prediction_error",
        "transfer_precision",
    ]
    lower_is_better = {"first_task_success_tick", "invalid_actions", "prediction_error"}
    series = normalize_summary_for_radar(rows, conditions, metrics, lower_is_better)
    out = Path(output_dir) / "cognitive_contribution_radar.png"
    plot_radar_chart(
        series, metrics,
        title="Cognitive Engine Contribution (normalized)",
        output=str(out),
    )
    print(f"  wrote {out}")


def generate_scaling_figures(phase_d_root: str, output_dir: str):
    csv_path = find_csv(phase_d_root, "scaling_summary.csv")
    if csv_path is None:
        print("SKIP scaling: scaling_summary.csv not found")
        return
    sweeps = [
        ("domain_count", "pretrain_domain_count"),
        ("horizon_sweep", "pretrain_ticks"),
    ]
    for sweep, x_key in sweeps:
        suffix = sweep.replace("_sweep", "")
        out = Path(output_dir) / f"scaling_{suffix}_d.png"
        plot_scaling_from_csv(
            csv_path, sweep=sweep, x_key=x_key,
            metric="first_task_success_tick", y_key="d",
            output=str(out),
        )
        print(f"  wrote {out}")


def generate_trajectory_example(output_dir: str):
    try:
        world = load_domain("chemistry_lite")
    except Exception as e:
        print(f"SKIP trajectory: cannot load chemistry_lite ({e})")
        return
    graph = world.initial_graph()
    mote = UniversalMote(energy=100)
    records = record_mote_trajectory(world, graph, mote, mote_position="atom_c", ticks=10)
    json_path = Path(output_dir) / "chemistry_lite_trajectory.json"
    save_trajectory_json(records, str(json_path))
    print(f"  wrote {json_path} ({len(records)} ticks)")
    html_path = Path(output_dir) / "chemistry_lite_trajectory.html"
    save_trajectory_html(records, str(html_path), title="Chemistry Lite Mote Trajectory")
    print(f"  wrote {html_path}")


def generate_lexicon_demo(output_dir: str):
    ticks = list(range(21))
    convergence = [0.0, 0.05, 0.12, 0.18, 0.25, 0.30, 0.35, 0.40,
                   0.44, 0.48, 0.52, 0.55, 0.58, 0.60, 0.62, 0.64,
                   0.65, 0.66, 0.67, 0.67, 0.68]
    out = Path(output_dir) / "lexicon_convergence_demo.png"
    plot_lexicon_convergence(
        ticks, convergence,
        title="Lexicon Convergence Demo",
        output=str(out),
    )
    print(f"  wrote {out}")


def main():
    parser = argparse.ArgumentParser(description="Generate Phase E figures")
    parser.add_argument("--phase-d", default="results/phase_d",
                        help="Path to Phase D results directory")
    parser.add_argument("--output", default="results/phase_e/figures",
                        help="Output directory for figures")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    phase_d_root = args.phase_d

    print("Generating Phase E figures...")
    print(f"  Phase D root: {phase_d_root}")
    print(f"  Output dir:   {output_dir}")
    print()

    print("[1/5] Composition heatmaps")
    generate_composition_figures(phase_d_root, str(output_dir))

    print("[2/5] Cognitive contribution radar")
    generate_cognitive_radar(phase_d_root, str(output_dir))

    print("[3/5] Scaling law curves")
    generate_scaling_figures(phase_d_root, str(output_dir))

    print("[4/5] Trajectory example")
    generate_trajectory_example(str(output_dir))

    print("[5/5] Lexicon convergence demo")
    generate_lexicon_demo(str(output_dir))

    print()
    print("Done.")


if __name__ == "__main__":
    main()
