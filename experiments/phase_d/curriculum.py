#!/usr/bin/env python3
"""Phase D — Curriculum Order Experiment.

Question: Does the order of pretraining domains affect Logic transfer?
"""
import argparse
import sys
import time

from tais_core.experiments import Condition, ExperimentSuite, Metric


def build_suite(seeds=200, eval_ticks=15, pretrain_ticks=20):
    return ExperimentSuite(
        name="curriculum",
        seeds=seeds,
        conditions=[
            Condition("fresh"),
            Condition("grid_rules_chem", pretrain_domains=["gridworld", "rules", "chemistry_lite"]),
            Condition("chem_rules_grid", pretrain_domains=["chemistry_lite", "rules", "gridworld"]),
            Condition("rules_grid_chem", pretrain_domains=["rules", "gridworld", "chemistry_lite"]),
            Condition("grid_chem_rules", pretrain_domains=["gridworld", "chemistry_lite", "rules"]),
            Condition("logic_same_domain", pretrain_domains=["logic"]),
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
            Metric("transfer_strength"),
            Metric("transfer_precision"),
        ],
    )


def main():
    parser = argparse.ArgumentParser(description="Phase D — Curriculum Order Experiment")
    parser.add_argument("--seeds", type=int, default=200)
    parser.add_argument("--eval", type=int, default=15, dest="eval_ticks")
    parser.add_argument("--pretrain", type=int, default=20, dest="pretrain_ticks")
    parser.add_argument("--output", type=str, default=None, dest="output_dir")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    suite = build_suite(args.seeds, args.eval_ticks, args.pretrain_ticks)
    print(f"Curriculum Experiment: {args.seeds} seeds, {args.eval_ticks} eval, {args.pretrain_ticks} pretrain",
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
        print(f"\nOutput: {args.output_dir}/curriculum.{{json,csv,md,tex}}", file=sys.stderr)


if __name__ == "__main__":
    main()
