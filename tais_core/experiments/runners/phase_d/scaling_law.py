#!/usr/bin/env python3
"""Phase D — Scaling Law Experiment.

Sweep A: domain count  {fresh, one, two, three, same_domain}
Sweep B: pretrain horizon  {0, 5, 10, 20, 50, 100}
"""
import argparse
import csv
import sys
import time
from pathlib import Path

from tais_core.experiments import Condition, ExperimentSuite, Metric


def build_suite_domain_count(seeds=200, eval_ticks=15, pretrain_ticks=20):
    return ExperimentSuite(
        name="domain_count",
        seeds=seeds,
        conditions=[
            Condition("fresh"),
            Condition("one_domain", pretrain_domains=["gridworld"]),
            Condition("two_domains", pretrain_domains=["gridworld", "rules"]),
            Condition("three_domains", pretrain_domains=["gridworld", "rules", "chemistry_lite"]),
            Condition("same_domain", pretrain_domains=["logic"]),
        ],
        eval_domain="logic",
        eval_ticks=eval_ticks,
        pretrain_ticks=pretrain_ticks,
        metrics=[
            Metric("first_task_success_tick", lower_is_better=True),
            Metric("task_completion_rate"),
            Metric("reward"),
            Metric("invalid_actions", lower_is_better=True),
            Metric("prediction_error", lower_is_better=True),
            Metric("transfer_uses"),
            Metric("transfer_precision"),
        ],
    )


def build_suite_horizon(seeds=200, eval_ticks=15):
    horizons = [5, 10, 20, 50, 100]
    conditions = [Condition("fresh")]
    for h in horizons:
        conditions.append(
            Condition(f"grid_h{h}", pretrain_domains=["gridworld"], pretrain_ticks=h)
        )
    return ExperimentSuite(
        name="horizon_sweep",
        seeds=seeds,
        conditions=conditions,
        eval_domain="logic",
        eval_ticks=eval_ticks,
        pretrain_ticks=20,  # fallback only
        metrics=[
            Metric("first_task_success_tick", lower_is_better=True),
            Metric("task_completion_rate"),
            Metric("reward"),
            Metric("invalid_actions", lower_is_better=True),
            Metric("prediction_error", lower_is_better=True),
            Metric("transfer_uses"),
            Metric("transfer_precision"),
        ],
    )


def write_scaling_summary(domain_results, horizon_results, path: Path):
    rows = []
    for sweep_name, results, suite in [
        ("domain_count", domain_results, build_suite_domain_count()),
        ("horizon_sweep", horizon_results, build_suite_horizon()),
    ]:
        for cond_name in results.records:
            if cond_name == results.baseline_condition:
                continue
            cond_obj = next(c for c in suite.conditions if c.name == cond_name)
            n_domains = len(cond_obj.pretrain_domains)
            pt = cond_obj.pretrain_ticks if cond_obj.pretrain_ticks > 0 else suite.pretrain_ticks
            for metric in suite.metrics:
                summary = results.paired_summary(cond_name, metric.name)
                if summary is None:
                    continue
                rows.append({
                    "sweep": sweep_name,
                    "condition": cond_name,
                    "pretrain_domain_count": n_domains,
                    "pretrain_ticks": pt,
                    "metric": metric.name,
                    "delta": summary["delta"],
                    "d": summary["d"],
                    "p": summary["p"],
                })
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "sweep", "condition", "pretrain_domain_count", "pretrain_ticks",
            "metric", "delta", "d", "p",
        ])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Scaling summary written to {path}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Phase D — Scaling Law Experiment")
    parser.add_argument("--seeds", type=int, default=200)
    parser.add_argument("--eval", type=int, default=15, dest="eval_ticks")
    parser.add_argument("--pretrain", type=int, default=20, dest="pretrain_ticks")
    parser.add_argument("--output", type=str, default=None, dest="output_dir")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    base = Path(args.output_dir) if args.output_dir else Path.cwd()

    print("Sweep A — domain count", file=sys.stderr)
    suite_dc = build_suite_domain_count(args.seeds, args.eval_ticks, args.pretrain_ticks)
    t0 = time.time()
    dc_results = suite_dc.run(
        output_dir=str(base / "domain_count") if args.output_dir else None,
        verbose=args.verbose,
    )
    print(f"  completed in {time.time() - t0:.1f}s", file=sys.stderr)

    print("Sweep B — pretrain horizon", file=sys.stderr)
    suite_hz = build_suite_horizon(args.seeds, args.eval_ticks)
    t0 = time.time()
    hz_results = suite_hz.run(
        output_dir=str(base / "horizon_sweep") if args.output_dir else None,
        verbose=args.verbose,
    )
    print(f"  completed in {time.time() - t0:.1f}s", file=sys.stderr)

    write_scaling_summary(dc_results, hz_results, base / "scaling_summary.csv")

    print(f"\nOutput: {args.output_dir}/", file=sys.stderr)


if __name__ == "__main__":
    main()
