#!/usr/bin/env python3
"""Phase F2 — Experiment 3: Domain-Count Scaling.

Tests whether increasing the number of pretrain domains improves
transfer to LogicWorld.
"""
from __future__ import annotations

import argparse
import sys
import time

from tais_core.experiments import Condition, ExperimentSuite, Metric


def build_suite(seeds: int = 200, eval_ticks: int = 15, pretrain_ticks: int = 20):
    return ExperimentSuite(
        name="domain_count_scaling",
        seeds=seeds,
        conditions=[
            Condition("fresh"),
            Condition("one_grid", pretrain_domains=["gridworld"]),
            Condition("two_grid_rules", pretrain_domains=["gridworld", "rules"]),
            Condition("three_grid_rules_chem", pretrain_domains=["gridworld", "rules", "chemistry_lite"]),
            Condition("four_grid_rules_chem_hazard", pretrain_domains=["gridworld", "rules", "chemistry_lite", "hazard"]),
            Condition("five_grid_rules_chem_hazard_sequences",
                      pretrain_domains=["gridworld", "rules", "chemistry_lite", "hazard", "sequences"]),
            Condition("same_domain_logic", pretrain_domains=["logic"]),
        ],
        eval_domain="logic",
        eval_ticks=eval_ticks,
        pretrain_ticks=pretrain_ticks,
        metrics=[
            Metric("first_task_success_tick", lower_is_better=True),
            Metric("task_completion_rate"),
            Metric("reward"),
            Metric("penalty", lower_is_better=True),
            Metric("invalid_actions", lower_is_better=True),
            Metric("prediction_error", lower_is_better=True),
            Metric("transfer_uses"),
            Metric("transfer_strength"),
            Metric("transfer_precision"),
            Metric("final_energy"),
        ],
    )


def main():
    parser = argparse.ArgumentParser(description="Phase F2 — Domain-Count Scaling")
    parser.add_argument("--seeds", type=int, default=200)
    parser.add_argument("--eval", type=int, default=15, dest="eval_ticks")
    parser.add_argument("--pretrain", type=int, default=20, dest="pretrain_ticks")
    parser.add_argument("--output", type=str, default=None, dest="output_dir")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    suite = build_suite(args.seeds, args.eval_ticks, args.pretrain_ticks)
    print(f"Domain-Count Scaling: {args.seeds} seeds, {args.eval_ticks} eval, {args.pretrain_ticks} pretrain",
          file=sys.stderr)
    t0 = time.time()
    results = suite.run(output_dir=args.output_dir, verbose=args.verbose)
    elapsed = time.time() - t0
    print(f"Completed in {elapsed:.1f}s", file=sys.stderr)

    for cond_name in results.records:
        if cond_name == "fresh":
            continue
        print(f"\n--- {cond_name} ---", file=sys.stderr)
        for metric in suite.metrics:
            summary = results.paired_summary(cond_name, metric.name)
            if summary is None:
                continue
            print(f"  {metric.name}: delta={summary['delta']:+.4f}, p={summary['p']:.4f}, d={summary['d']:.3f}",
                  file=sys.stderr)

    if args.output_dir:
        print(f"\nOutput: {args.output_dir}/domain_count_scaling.{{json,csv,md,tex}}", file=sys.stderr)


if __name__ == "__main__":
    main()
