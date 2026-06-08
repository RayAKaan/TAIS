#!/usr/bin/env python3
"""
TAIS V6 Command Line Interface.

Headless swarm training, experiment orchestration, and analysis.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from tais_swarm_v6.experiments.runner import BatchRunner, AblationConfig
from tais_swarm_v6.experiments.analysis import ExperimentAnalyzer
from tais_swarm_v6.engine.config import SwarmConfig


def cmd_swarm(args):
    config = SwarmConfig.from_file(args.config) if args.config else SwarmConfig()
    runner = BatchRunner(config, output_dir=args.output)

    ablation = AblationConfig(
        metacognition=not args.no_metacognition,
        causal_reasoning=not args.no_causal,
        hierarchical_planning=not args.no_planning,
        grammar_discovery=not args.no_grammar,
        trust_networks=not args.no_trust,
    )

    result = runner.run_single(
        seed=args.seed,
        ticks=args.ticks,
        ablation=ablation,
        label=args.label,
    )

    fname = f"{args.label}_seed{args.seed}.json"
    runner.save_results([result], fname)
    print(f"\nDone: {result.ticks} ticks in {result.wall_time_seconds:.1f}s")
    print(f"Population: {result.final_population} | "
          f"PredAcc: {result.avg_prediction_accuracy:.3f} | "
          f"Plans: {result.total_plans_completed}")


def cmd_ablate(args):
    config = SwarmConfig.from_file(args.config) if args.config else SwarmConfig()
    runner = BatchRunner(config, output_dir=args.output)
    analyzer = ExperimentAnalyzer(results_dir=args.output)

    seeds = list(range(args.seed_start, args.seed_start + args.seeds))
    print(f"Ablation suite: {len(seeds)} seeds x conditions...")

    results = runner.run_ablation_suite(seeds=seeds, ticks=args.ticks)
    fname = f"ablation_{args.seeds}seeds_{args.ticks}ticks.json"
    runner.save_results(results, fname)

    print("\nAnalyzing...")
    result_dicts = [asdict(r) for r in results]
    comparisons = analyzer.compare_conditions(result_dicts, metric="avg_prediction_accuracy")
    analyzer.plot_metric_over_time(result_dicts, metric="avg_prediction_accuracy")
    analyzer.plot_final_comparison(result_dicts)
    analyzer.generate_report(result_dicts, comparisons)

    print(f"\nAll outputs in {args.output}/")


def cmd_analyze(args):
    analyzer = ExperimentAnalyzer(results_dir=args.output)
    results = analyzer.load_results(args.input)

    comparisons = analyzer.compare_conditions(results, metric=args.metric)
    analyzer.plot_metric_over_time(results, metric=args.metric)
    analyzer.plot_final_comparison(results, metrics=[args.metric])
    analyzer.generate_report(results, comparisons)

    print(json.dumps(comparisons, indent=2))


def cmd_serve(args):
    from tais_swarm_v6.api.server import SwarmServer
    from tais_swarm_v6.engine.core import SwarmV6

    print(f"Starting TAIS V6 API on {args.host}:{args.port}")
    swarm = SwarmV6()
    swarm.init_population(20)
    server = SwarmServer(swarm, host=args.host, port=args.port)
    server.start()


def main():
    parser = argparse.ArgumentParser(
        prog="tais-v6",
        description="TAIS V6 - No LLM. Grounded substrate. Raw inspection.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_swarm = sub.add_parser("swarm", help="Run single headless swarm")
    p_swarm.add_argument("--ticks", type=int, default=5000)
    p_swarm.add_argument("--seed", type=int, default=42)
    p_swarm.add_argument("--config", type=str, default=None)
    p_swarm.add_argument("--output", type=str, default="results")
    p_swarm.add_argument("--label", type=str, default="experiment")
    p_swarm.add_argument("--no-metacognition", action="store_true")
    p_swarm.add_argument("--no-causal", action="store_true")
    p_swarm.add_argument("--no-planning", action="store_true")
    p_swarm.add_argument("--no-grammar", action="store_true")
    p_swarm.add_argument("--no-trust", action="store_true")
    p_swarm.set_defaults(func=cmd_swarm)

    p_ablate = sub.add_parser("ablate", help="Run full ablation study")
    p_ablate.add_argument("--seeds", type=int, default=10)
    p_ablate.add_argument("--seed-start", type=int, default=0)
    p_ablate.add_argument("--ticks", type=int, default=2000)
    p_ablate.add_argument("--config", type=str, default=None)
    p_ablate.add_argument("--output", type=str, default="results")
    p_ablate.set_defaults(func=cmd_ablate)

    p_analyze = sub.add_parser("analyze", help="Analyze existing JSON results")
    p_analyze.add_argument("input", type=str, help="Results JSON file")
    p_analyze.add_argument("--metric", type=str, default="avg_prediction_accuracy")
    p_analyze.add_argument("--output", type=str, default="results")
    p_analyze.set_defaults(func=cmd_analyze)

    p_serve = sub.add_parser("serve", help="Start API/WebSocket server")
    p_serve.add_argument("--host", type=str, default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8612)
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
