#!/usr/bin/env python3
"""
Phase A headline experiment: Does adding cognitive engines improve transfer?

Conditions (paired fresh-vs-condition, default 200 seeds x 15-tick horizon):
  1. fresh_control        - no pretrain, no engines vs no pretrain, no engines
  2. full_baseline        - Grid pretrain, no engines; should reproduce Phase 5 full
  3. full_with_metacog    - Grid pretrain, metacog only
  4. full_with_causal     - Grid pretrain, causal only
  5. full_with_planning   - Grid pretrain, planning only
  6. full_with_all        - Grid pretrain, all engines
  7. engines_no_pretrain  - no pretrain, all engines; control

This runner intentionally reuses Phase 5 LogicWorld helpers so domain factory
signatures stay correct: make_grid_graph(threat_near_resource=...) and
make_logic_graph_easy().
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import time
from dataclasses import dataclass
from typing import Dict, Optional

from tais_core import UniversalMote
from tais_core.experiments.runners.logic_transfer_runner import (
    ExperimentResult,
    evaluate_logicworld,
    run_grid_pretrain,
    METRICS,
)


@dataclass(frozen=True)
class CognitiveCondition:
    pretrain_grid: bool
    engines: Optional[dict]


ENGINE_CONDITIONS: Dict[str, CognitiveCondition] = {
    "fresh_control": CognitiveCondition(pretrain_grid=False, engines=None),
    "full_baseline": CognitiveCondition(pretrain_grid=True, engines=None),
    "full_with_metacog": CognitiveCondition(
        pretrain_grid=True,
        engines={"metacognition": True, "causal_reasoning": False, "hierarchical_planning": False},
    ),
    "full_with_causal": CognitiveCondition(
        pretrain_grid=True,
        engines={"metacognition": False, "causal_reasoning": True, "hierarchical_planning": False},
    ),
    "full_with_planning": CognitiveCondition(
        pretrain_grid=True,
        engines={"metacognition": False, "causal_reasoning": False, "hierarchical_planning": True},
    ),
    "full_with_all": CognitiveCondition(
        pretrain_grid=True,
        engines={"metacognition": True, "causal_reasoning": True, "hierarchical_planning": True},
    ),
    "engines_no_pretrain": CognitiveCondition(
        pretrain_grid=False,
        engines={"metacognition": True, "causal_reasoning": True, "hierarchical_planning": True},
    ),
}


def make_mote(engines: Optional[dict]) -> UniversalMote:
    mote = UniversalMote(energy=100.0)
    if engines:
        mote.enable_cognitive_engines(**engines)
    return mote


def run_condition_trial(seed: int, condition: CognitiveCondition, pretrain_ticks: int, eval_ticks: int):
    random.seed(seed)
    mote = make_mote(condition.engines)
    if condition.pretrain_grid:
        run_grid_pretrain(mote, pretrain_ticks, mixed=True)
    return evaluate_logicworld(
        mote,
        eval_ticks,
        start_tick=pretrain_ticks if condition.pretrain_grid else 0,
    )


def run_fresh_trial(seed: int, pretrain_ticks: int, eval_ticks: int):
    random.seed(seed)
    mote = UniversalMote(energy=100.0)
    return evaluate_logicworld(mote, eval_ticks, start_tick=0)


def run_experiment(seeds: int = 200, horizon: int = 15, pretrain_ticks: int = 20, verbose: bool = False):
    results = {name: ExperimentResult(name) for name in ENGINE_CONDITIONS}
    t0 = time.time()
    for seed in range(seeds):
        if verbose and (seed + 1) % 25 == 0:
            print(f"  seed {seed + 1}/{seeds} ({time.time() - t0:.1f}s)")
        paired_seed = 10_000 + seed
        fresh = run_fresh_trial(paired_seed, pretrain_ticks, horizon)
        for name, condition in ENGINE_CONDITIONS.items():
            if name == "fresh_control":
                comparison = run_fresh_trial(paired_seed, pretrain_ticks, horizon)
            else:
                comparison = run_condition_trial(paired_seed, condition, pretrain_ticks, horizon)
            results[name].add(fresh, comparison)
    return results


def format_table(results, seeds: int, pretrain_ticks: int, eval_ticks: int) -> str:
    lines = []
    lines.append("=" * 122)
    lines.append("  TAIS PHASE A -- Cognitive Engine Grid->Logic Transfer")
    lines.append("=" * 122)
    lines.append(f"\n  Seeds: {seeds} | Grid pretrain ticks: {pretrain_ticks} | Logic eval ticks: {eval_ticks}\n")
    for key, label in METRICS:
        lines.append(f"\n  --- {label} ---")
        lines.append(f"  {'Condition':<22} {'Fresh':>10} {'Condition':>11} {'Delta':>10} {'95% CI':>20} {'p':>10} {'d':>8}")
        lines.append(f"  {'-'*22} {'-'*10} {'-'*11} {'-'*10} {'-'*20} {'-'*10} {'-'*8}")
        for name in ENGINE_CONDITIONS:
            s = results[name].summary()[key]
            sig = " ***" if s["p"] < 0.001 else " **" if s["p"] < 0.01 else " *" if s["p"] < 0.05 else ""
            ci = f"[{s['ci_low']:.3f}, {s['ci_high']:.3f}]"
            lines.append(
                f"  {name:<22} {s['fresh']:>10.3f} {s['pretrained']:>11.3f} "
                f"{s['delta']:>+10.4f} {ci:>20} {s['p']:>10.6f}{sig:<4} {s['d']:>8.3f}"
            )
    lines.append("\n" + "=" * 122)
    lines.append("  Delta = condition - fresh. For first_task_success_tick, negative is better.")
    lines.append("  * p<0.05   ** p<0.01   *** p<0.001")
    lines.append("=" * 122)
    return "\n".join(lines)


def write_csv(results, path: str):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["condition", "metric", "fresh", "condition_value", "delta", "ci_low", "ci_high", "p", "d"])
        for name, result in results.items():
            summary = result.summary()
            for key, _label in METRICS:
                s = summary[key]
                w.writerow([name, key, s["fresh"], s["pretrained"], s["delta"], s["ci_low"], s["ci_high"], s["p"], s["d"]])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=200)
    parser.add_argument("--horizon", type=int, default=15)
    parser.add_argument("--pretrain", type=int, default=20)
    parser.add_argument("--output", type=str, default="results/cognitive_transfer.txt")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    start = time.time()
    results = run_experiment(args.seeds, args.horizon, args.pretrain, verbose=args.verbose)
    elapsed = time.time() - start
    table = format_table(results, args.seeds, args.pretrain, args.horizon)
    print(table)
    print(f"\nWall time: {elapsed:.1f}s")

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(table + f"\n\nWall time: {elapsed:.1f}s\n")
    csv_path = args.output.rsplit(".", 1)[0] + ".csv"
    json_path = args.output.rsplit(".", 1)[0] + ".json"
    write_csv(results, csv_path)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({name: res.summary() for name, res in results.items()}, f, indent=2)
    print(f"Wrote: {args.output}\nWrote: {csv_path}\nWrote: {json_path}")


if __name__ == "__main__":
    main()
