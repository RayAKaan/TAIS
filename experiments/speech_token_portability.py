#!/usr/bin/env python3
"""Phase A: Speech token portability benchmark — GridWorld {ka→DANGER} → HazardWorld.

Hypothesis: teaching a speech token "ka" to mean DANGER in GridWorld pretrain
improves the mote's ability to avoid hazards in HazardWorld, via the lexicon's
concept associations influencing memory and transfer patterns.

Null hypothesis: speech knowledge does not affect single-mote behavior.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from tais_core.domains.gridworld import GridGraphWorld, make_grid_graph
from tais_core.domains.hazard import HazardGraphWorld, make_hazard_graph_easy
HazardWorld = HazardGraphWorld
from tais_core.mote import UniversalMote


CONDITIONS = ["trained_token", "random_token", "no_token"]
DEFAULT_SEEDS = 50
PRETRAIN_TICKS = 20
EVAL_TICKS = 15


@dataclass
class ConditionResult:
    condition: str
    n: int = 0
    first_task_success_ticks: List[float] = field(default_factory=list)
    task_completed: List[int] = field(default_factory=list)
    avoid_bad_counts: List[int] = field(default_factory=list)
    total_actions: List[int] = field(default_factory=list)
    final_energies: List[float] = field(default_factory=list)
    total_rewards: List[float] = field(default_factory=list)
    invalid_action_counts: List[int] = field(default_factory=list)
    prediction_errors: List[float] = field(default_factory=list)

    def record(self, metrics: Dict[str, Any]):
        self.n += 1
        self.first_task_success_ticks.append(metrics.get("first_success_tick", EVAL_TICKS + 1))
        self.task_completed.append(1 if metrics.get("succeeded", False) else 0)
        self.avoid_bad_counts.append(metrics.get("avoid_bad_count", 0))
        self.total_actions.append(metrics.get("total_actions", 0))
        self.final_energies.append(metrics.get("final_energy", 0.0))
        self.total_rewards.append(metrics.get("total_reward", 0.0))
        self.invalid_action_counts.append(metrics.get("invalid_actions", 0))
        self.prediction_errors.append(metrics.get("mean_prediction_error", 0.0))

    def summary(self) -> Dict[str, Any]:
        def mean(vals):
            lst = list(vals)
            return sum(lst) / len(lst) if lst else 0.0
        return {
            "condition": self.condition,
            "n": self.n,
            "first_success_tick": mean(self.first_task_success_ticks),
            "completion_rate": mean(self.task_completed),
            "avoid_bad_rate": mean(a / max(1, b) for a, b in zip(self.avoid_bad_counts, self.total_actions)),
            "avoid_bad_count": mean(self.avoid_bad_counts),
            "final_energy": mean(self.final_energies),
            "total_reward": mean(self.total_rewards),
            "invalid_actions": mean(self.invalid_action_counts),
            "prediction_error": mean(self.prediction_errors),
        }


def make_mote(seed: int, condition: str) -> UniversalMote:
    rng = random.Random(seed)
    mote = UniversalMote(energy=100.0)
    mote.meta.curiosity = rng.uniform(0.1, 0.4)
    mote.meta.skepticism = rng.uniform(0.1, 0.4)
    mote.meta.risk_tolerance = rng.uniform(0.2, 0.5)
    mote.meta.teaching_bias = rng.uniform(0.1, 0.3)
    mote.meta.memory_compression = rng.uniform(0.2, 0.4)
    mote.meta.analogy_bias = rng.uniform(0.2, 0.5)

    if condition == "trained_token":
        mote.speech.teach("ka", "DANGER", strength=1.0)
    elif condition == "random_token":
        mote.speech.teach("ka", "GOOD", strength=1.0)

    return mote


def run_pretrain(mote: UniversalMote, seed: int, ticks: int) -> UniversalMote:
    rng = random.Random(seed)
    world = GridGraphWorld()
    for t in range(ticks):
        g = make_grid_graph()
        mote.step(world, g, tick=t)
    return mote


def run_eval(mote: UniversalMote, seed: int, ticks: int) -> Dict[str, Any]:
    rng = random.Random(seed)
    world = HazardWorld()
    g = make_hazard_graph_easy()

    avoid_bad_count = 0
    first_success_tick = ticks + 1
    succeeded = False

    for t in range(ticks):
        new_g, cons, action = mote.step(world, g, tick=t)
        g = new_g

        if action is not None and action.name == "avoid_hazard":
            avoid_bad_count += 1

        if cons.task_signal == "TASK_SUCCESS":
            if not succeeded:
                first_success_tick = t
            succeeded = True

    mean_pred_err = mote.memory.prediction.mean_error()
    if math.isinf(mean_pred_err):
        mean_pred_err = 0.0

    return {
        "first_success_tick": first_success_tick,
        "succeeded": succeeded,
        "avoid_bad_count": avoid_bad_count,
        "total_actions": mote.actions_taken,
        "final_energy": mote.energy,
        "total_reward": mote.total_reward,
        "invalid_actions": mote.invalid_actions,
        "mean_prediction_error": mean_pred_err,
        "transfer_prior_uses": mote.transfer_prior_uses,
        "transfer_prior_strength": mote.transfer_prior_total_strength,
    }


def run_seed(seed: int, condition: str, pretrain_ticks: int, eval_ticks: int) -> Dict[str, Any]:
    mote = make_mote(seed, condition)
    mote = run_pretrain(mote, seed, pretrain_ticks)
    metrics = run_eval(mote, seed, eval_ticks)
    metrics["condition"] = condition
    metrics["seed"] = seed
    return metrics


def run_experiment(seeds: int, pretrain_ticks: int, eval_ticks: int, verbose: bool = False) -> Dict[str, ConditionResult]:
    results = {c: ConditionResult(condition=c) for c in CONDITIONS}
    for seed in range(seeds):
        if verbose:
            print(f"  seed {seed+1}/{seeds}", file=sys.stderr)
        for condition in CONDITIONS:
            metrics = run_seed(seed, condition, pretrain_ticks, eval_ticks)
            results[condition].record(metrics)
    return results


def format_table(results: Dict[str, ConditionResult], seeds: int, pretrain_ticks: int, eval_ticks: int) -> str:
    lines = []
    lines.append("=" * 100)
    lines.append("  TAIS PHASE A - Speech Token Portability: GridWorld {ka->DANGER} -> HazardWorld")
    lines.append("=" * 100)
    lines.append(f"\n  Seeds: {seeds} | Pretrain ticks: {pretrain_ticks} | Eval ticks: {eval_ticks}\n")

    metrics = [
        ("first_success_tick", "First TASK_SUCCESS Tick"),
        ("completion_rate", "Task Completion Rate"),
        ("avoid_bad_rate", "Avoid-Bad Rate"),
        ("avoid_bad_count", "Avoid-Bad Count"),
        ("final_energy", "Final Energy"),
        ("total_reward", "Total Reward"),
        ("invalid_actions", "Invalid Actions"),
        ("prediction_error", "Prediction Error"),
    ]

    for key, label in metrics:
        lines.append(f"\n  --- {label} ---")
        lines.append(f"  {'Condition':<20} {'Value':>12}")
        lines.append(f"  {'-'*20} {'-'*12}")
        for name in CONDITIONS:
            s = results[name].summary()
            val = s[key]
            lines.append(f"  {name:<20} {val:>12.4f}")
    lines.append("\n" + "=" * 100)
    return "\n".join(lines)


def write_csv(results: Dict[str, ConditionResult], path: str):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["condition", "n", "first_success_tick", "completion_rate", "avoid_bad_rate",
                     "avoid_bad_count", "final_energy", "total_reward", "invalid_actions",
                     "prediction_error"])
        for name in CONDITIONS:
            s = results[name].summary()
            w.writerow([s["condition"], s["n"], s["first_success_tick"], s["completion_rate"],
                        s["avoid_bad_rate"], s["avoid_bad_count"], s["final_energy"],
                        s["total_reward"], s["invalid_actions"], s["prediction_error"]])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=DEFAULT_SEEDS)
    p.add_argument("--pretrain", type=int, default=PRETRAIN_TICKS)
    p.add_argument("--eval", type=int, default=EVAL_TICKS)
    p.add_argument("--output", type=str, default="results/speech_token_portability")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    print(f"\n{'=' * 60}\nTAIS Speech Token Portability: seeds={args.seeds}, "
          f"pretrain={args.pretrain}, eval={args.eval}\n{'=' * 60}\n")

    t0 = time.time()
    results = run_experiment(args.seeds, args.pretrain, args.eval, args.verbose)
    elapsed = time.time() - t0

    table = format_table(results, args.seeds, args.pretrain, args.eval)

    out_path = args.output + ".txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(table + f"\n\nElapsed: {elapsed:.2f}s\n")
    csv_path = args.output + ".csv"
    write_csv(results, csv_path)
    json_path = args.output + ".json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({name: results[name].summary() for name in CONDITIONS}, f, indent=2)

    print(f"Wrote: {out_path}\nWrote: {csv_path}\nWrote: {json_path}")


if __name__ == "__main__":
    main()
