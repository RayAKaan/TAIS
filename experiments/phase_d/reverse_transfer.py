#!/usr/bin/env python3
"""Phase D — Reverse Transfer Experiment.

Question: After transferring Grid→Logic, does the mote improve when
evaluated back on Grid?

GridWorld has no TASK_SUCCESS signal, so this runner uses an explicit
local heuristic: cons.net > 0 and ("RESOURCE" in cons.concept_signals
or "SAFE" in cons.concept_signals).
"""
import argparse
import random
import sys
import time
from pathlib import Path
from typing import Dict, List

from tais_core import UniversalMote, load_domain
from tais_core.experiments import Metric, TrialRecord, ExperimentResults, ExperimentReport, capture_provenance
from tais_core.experiments.metrics import mean

# GridWorld success heuristic (GridWorld has no TASK_SUCCESS)
def grid_success(cons) -> bool:
    return cons.net > 0 and ("RESOURCE" in cons.concept_signals or "SAFE" in cons.concept_signals)


def build_conditions():
    return [
        ("fresh_grid_eval", [], 0),
        ("grid_pretrained_grid_eval", ["gridworld"], 20),
        ("grid_logic_grid_eval", ["gridworld"], 20),
        ("logic_grid_eval", ["logic"], 20),
    ]


METRICS = [
    Metric("first_task_success_tick", lower_is_better=True),
    Metric("task_completion_rate"),
    Metric("reward"),
    Metric("penalty", lower_is_better=True),
    Metric("invalid_actions", lower_is_better=True),
    Metric("prediction_error", lower_is_better=True),
    Metric("final_energy"),
]


def run_trial(condition_name: str, pretrain_domains: List[str], pretrain_ticks: int, seed: int) -> Dict[str, float]:
    rng = random.Random(seed)

    mote = UniversalMote(energy=100.0)
    position = "mote"

    # Pretrain
    for domain_name in pretrain_domains:
        world = load_domain(domain_name)
        graph = world.initial_graph()
        for t in range(pretrain_ticks):
            if mote.energy <= 0:
                mote.energy = 50.0
            graph, cons, action = mote.step(world, graph, mote_position=position, tick=t)

    # Logic segment (only for grid_logic_grid_eval)
    if condition_name == "grid_logic_grid_eval":
        logic_world = load_domain("logic")
        logic_graph = logic_world.initial_graph()
        for t in range(15):
            if mote.energy <= 0:
                mote.energy = 50.0
            logic_graph, cons, action = mote.step(logic_world, logic_graph, mote_position="ASSIGN", tick=t)

    # Evaluate on GridWorld
    reward0 = mote.total_reward
    penalty0 = mote.total_penalty
    invalid0 = mote.invalid_actions
    tu0 = mote.transfer_prior_uses
    correct0 = mote.transfer_prior_correct
    incorrect0 = mote.transfer_prior_incorrect

    grid_world = load_domain("gridworld")
    grid_graph = grid_world.initial_graph()
    first_success = None
    pred_errors = []

    for t in range(15):
        grid_graph, cons, action = mote.step(grid_world, grid_graph, mote_position=position, tick=t)
        pe = abs(mote.last_prediction - cons.net)
        pred_errors.append(pe)
        if first_success is None and grid_success(cons):
            first_success = t

    correct_after = mote.transfer_prior_correct - correct0
    incorrect_after = mote.transfer_prior_incorrect - incorrect0

    return {
        "first_task_success_tick": float(first_success if first_success is not None else 16),
        "task_completion_rate": 1.0 if first_success is not None else 0.0,
        "reward": mote.total_reward - reward0,
        "penalty": mote.total_penalty - penalty0,
        "invalid_actions": mote.invalid_actions - invalid0,
        "final_energy": mote.energy,
        "prediction_error": mean(pred_errors) if pred_errors else 0.0,
        "transfer_uses": mote.transfer_prior_uses - tu0,
        "transfer_precision": correct_after / max(1, correct_after + incorrect_after),
    }


def main():
    parser = argparse.ArgumentParser(description="Phase D — Reverse Transfer Experiment")
    parser.add_argument("--seeds", type=int, default=200)
    parser.add_argument("--output", type=str, default=None, dest="output_dir")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    params = {"seeds": args.seeds, "eval_domain": "gridworld", "eval_ticks": 15}
    provenance = capture_provenance("reverse_transfer", params)
    results = ExperimentResults(name="reverse_transfer", baseline_condition="fresh_grid_eval", metrics=METRICS, provenance=provenance)

    conds = build_conditions()
    print(f"Reverse Transfer Experiment: {args.seeds} seeds, 4 conditions", file=sys.stderr)
    t0 = time.time()

    for seed_idx in range(args.seeds):
        trial_seed = 20_000 + seed_idx
        random.seed(trial_seed)

        for cond_name, domains, pt in conds:
            metrics = run_trial(cond_name, domains, pt, trial_seed)
            record = TrialRecord(seed=seed_idx, condition=cond_name, metrics=metrics)
            results.add_record(record)

        if args.verbose:
            print(f"  seed {seed_idx+1}/{args.seeds} ({time.time()-t0:.1f}s)", file=sys.stderr)

    elapsed = time.time() - t0
    print(f"Completed in {elapsed:.1f}s", file=sys.stderr)

    if args.output_dir:
        odir = Path(args.output_dir)
        odir.mkdir(parents=True, exist_ok=True)
        results.save_json(odir / "reverse_transfer.json")
        results.save_csv(odir / "reverse_transfer.csv")
        report = ExperimentReport(results)
        report.save_markdown(odir / "reverse_transfer.md")
        report.save_latex(odir / "reverse_transfer.tex")

    for cond_name in results.records:
        if cond_name == "fresh_grid_eval":
            continue
        print(f"\n--- {cond_name} ---", file=sys.stderr)
        for metric in METRICS:
            summary = results.paired_summary(cond_name, metric.name)
            if summary is None:
                continue
            print(f"  {metric.name}: delta={summary['delta']:+.4f}, p={summary['p']:.4f}, d={summary['d']:.3f}",
                  file=sys.stderr)

    if args.output_dir:
        print(f"\nOutput: {args.output_dir}/reverse_transfer.{{json,csv,md,tex}}", file=sys.stderr)


if __name__ == "__main__":
    main()
