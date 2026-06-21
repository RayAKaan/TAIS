#!/usr/bin/env python3
"""Phase C logic-transfer experiment suite runner.

Usage:
    python experiments/phase_c_logic_transfer_suite.py --seeds 200 --eval 15 --pretrain 20 --verbose
    python experiments/phase_c_logic_transfer_suite.py --seeds 5 --eval 10 --pretrain 5 --output results/
"""
import argparse
import sys
import time

from tais_core.experiments import Condition, ExperimentSuite, Metric


def build_suite(seeds, eval_ticks, pretrain_ticks):
    return ExperimentSuite(
        name="phase_c_logic_transfer",
        seeds=seeds,
        conditions=[
            Condition("fresh"),
            Condition("grid_only", pretrain_domains=["gridworld"]),
            Condition("grid_metacog", pretrain_domains=["gridworld"], engines={"metacognition": True}),
            Condition("grid_causal", pretrain_domains=["gridworld"], engines={"causal_reasoning": True}),
            Condition("grid_planning", pretrain_domains=["gridworld"], engines={"hierarchical_planning": True}),
        ],
        eval_domain="logic",
        eval_ticks=eval_ticks,
        pretrain_ticks=pretrain_ticks,
        metrics=[
            Metric("first_task_success_tick", lower_is_better=True, description="Tick when TASK_SUCCESS first emitted"),
            Metric("task_completion_rate", description="Fraction of trials with TASK_SUCCESS"),
            Metric("reward", description="Total reward accumulated"),
            Metric("penalty", lower_is_better=True, description="Total penalty accumulated"),
            Metric("invalid_actions", lower_is_better=True, description="Number of invalid actions"),
            Metric("final_energy", description="Energy at end of evaluation"),
            Metric("prediction_error", lower_is_better=True, description="Mean prediction error"),
            Metric("transfer_uses", description="Number of cross-domain transfer uses"),
            Metric("transfer_strength", description="Total cross-domain transfer strength"),
            Metric("transfer_precision", description="Cross-domain transfer precision"),
            Metric("alive", description="Fraction of trials where mote survived"),
            Metric("actions_taken", description="Total actions taken"),
        ],
    )


def main():
    parser = argparse.ArgumentParser(description="Phase C logic-transfer experiment suite")
    parser.add_argument("--seeds", type=int, default=200, help="Number of seeds")
    parser.add_argument("--eval", type=int, default=15, dest="eval_ticks", help="Evaluation ticks")
    parser.add_argument("--pretrain", type=int, default=20, dest="pretrain_ticks", help="Pretrain ticks per domain")
    parser.add_argument("--output", type=str, default=None, dest="output_dir", help="Output directory")
    parser.add_argument("--verbose", action="store_true", help="Print per-tick progress")
    args = parser.parse_args()

    suite = build_suite(args.seeds, args.eval_ticks, args.pretrain_ticks)
    print(f"Running Phase C logic-transfer suite: {args.seeds} seeds, {args.eval_ticks} eval ticks, "
          f"{args.pretrain_ticks} pretrain ticks", file=sys.stderr)
    t0 = time.time()

    results = suite.run(output_dir=args.output_dir, verbose=args.verbose)

    elapsed = time.time() - t0
    print(f"\nCompleted in {elapsed:.1f}s", file=sys.stderr)
    print(f"Conditions: {len(results.records)}", file=sys.stderr)
    print(f"Total trials: {sum(len(v) for v in results.records.values())}", file=sys.stderr)

    for condition_name in results.records:
        print(f"\n--- {condition_name} ---", file=sys.stderr)
        for metric in suite.metrics:
            summary = results.paired_summary(condition_name, metric.name)
            if summary is None:
                continue
            print(f"  {metric.name}: baseline={summary['baseline']:.4f}, "
                  f"condition={summary['condition']:.4f}, "
                  f"delta={summary['delta']:+.4f}, "
                  f"p={summary['p']:.4f}, d={summary['d']:.3f}", file=sys.stderr)

    if args.output_dir:
        import os
        base = os.path.join(args.output_dir, suite.name)
        print(f"\nOutput written to {base}.*", file=sys.stderr)

    results.summary()


if __name__ == "__main__":
    main()
