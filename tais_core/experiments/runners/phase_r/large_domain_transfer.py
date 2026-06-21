#!/usr/bin/env python3
"""Phase R4 — Large Domain Variants Transfer Experiment.

Tests whether TAIS role-transfer survives larger synthetic graph domains.

Targets:
    logic_large       — 6 vars, 12 clauses (vs 3 vars, 3 clauses in easy)
    hazard_large      — 15 nodes, 20% hazard density (vs 5 nodes in easy)
    rules_chain_long  — chain of length 5 (vs length 2 in chain)

Conditions per target (paired by seed):
    fresh                  — no pretrain
    grid_pretrain          — GridWorld pretrain only
    rules_pretrain         — RuleWorld easy pretrain only
    three_domain_pretrain  — GridWorld + RuleWorld + HazardWorld
    same_domain_pretrain   — target domain itself

Run:
    python experiments/phase_r/large_domain_transfer.py --seeds 100 --pretrain 20 --eval 30
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from tais_core.domains.gridworld import GridGraphWorld, make_grid_graph
from tais_core.domains.logic import LogicWorldLarge, make_logic_graph_large, LogicWorld
from tais_core.domains.hazard import HazardGraphWorldLarge, make_hazard_graph_large, HazardGraphWorld
from tais_core.domains.rules import RuleWorld, RuleWorldChainLong, make_rule_graph_chain_long, make_rule_graph_easy
from tais_core.mote import UniversalMote
from tais_core.reality import Consequence, RealityGraph, Transformation, WorldInterface


# ─── STATS (identical to R3 runner) ──────────────────────────────────────────

def mean(xs: List[float]) -> float:
    return sum(xs) / max(1, len(xs))

def std(xs: List[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))

def cohens_d_paired(pre, fresh):
    diffs = [p - f for p, f in zip(pre, fresh)]
    s = std(diffs)
    return 0.0 if s < 1e-12 else mean(diffs) / s

def norm_cdf(x):
    if x < 0:
        return 1.0 - norm_cdf(-x)
    k = 1.0 / (1.0 + 0.2316419 * x)
    poly = k * (0.319381530 + k * (-0.356563782 + k * (1.781477937 + k * (-1.821255978 + k * 1.330274429))))
    return 1.0 - (1.0 / math.sqrt(2 * math.pi)) * math.exp(-x * x / 2.0) * poly

def paired_ttest(pre, fresh):
    diffs = [p - f for p, f in zip(pre, fresh)]
    if len(diffs) < 2:
        return 0.0, 1.0
    s = std(diffs)
    m = mean(diffs)
    if s < 1e-12:
        return (0.0, 1.0) if abs(m) < 1e-12 else (float("inf"), 0.0)
    t = m / (s / math.sqrt(len(diffs)))
    p = 2.0 * (1.0 - norm_cdf(abs(t)))
    return t, max(0.0, min(1.0, p))

def ci95_delta(pre, fresh):
    diffs = [p - f for p, f in zip(pre, fresh)]
    if len(diffs) < 2:
        return 0.0, 0.0
    m = mean(diffs)
    s = std(diffs)
    tcrit = 1.96 if len(diffs) >= 120 else 1.96 + 2.0 / max(1, len(diffs) - 1)
    margin = tcrit * s / math.sqrt(len(diffs))
    return m - margin, m + margin


# ─── METRICS ─────────────────────────────────────────────────────────────────

@dataclass
class TrialMetrics:
    reward: float
    penalty: float
    first_task_success_tick: float
    task_completion_rate: float
    contradictions: int
    invalid_actions: int
    final_energy: float
    prediction_error: float
    transfer_uses: int
    transfer_strength: float
    transfer_precision: float
    hazard_steps: int = 0


@dataclass
class ExperimentResult:
    condition: str
    values: List[TrialMetrics] = field(default_factory=list)

    def add(self, m: TrialMetrics):
        self.values.append(m)

    def metric_list(self, attr):
        return [float(getattr(x, attr)) for x in self.values]

    def summarize_metric(self, attr):
        vals = self.metric_list(attr)
        return {
            "mean": round(mean(vals), 6),
            "std": round(std(vals), 6),
            "n": len(vals),
        }

    def summary(self):
        return {
            "condition": self.condition,
            "n": len(self.values),
            "first_task_success_tick": self.summarize_metric("first_task_success_tick"),
            "task_completion_rate": self.summarize_metric("task_completion_rate"),
            "contradictions": self.summarize_metric("contradictions"),
            "reward": self.summarize_metric("reward"),
            "invalid_actions": self.summarize_metric("invalid_actions"),
            "final_energy": self.summarize_metric("final_energy"),
            "prediction_error": self.summarize_metric("prediction_error"),
            "transfer_uses": self.summarize_metric("transfer_uses"),
            "transfer_strength": self.summarize_metric("transfer_strength"),
            "transfer_precision": self.summarize_metric("transfer_precision"),
            "hazard_steps": self.summarize_metric("hazard_steps"),
        }


def compare_vs_baseline(condition_vals: List[TrialMetrics],
                        baseline_vals: List[TrialMetrics],
                        attr: str) -> Dict[str, float]:
    c = [float(getattr(x, attr)) for x in condition_vals]
    b = [float(getattr(x, attr)) for x in baseline_vals]
    lo, hi = ci95_delta(c, b)
    _t, p = paired_ttest(c, b)
    return {
        "condition_mean": round(mean(c), 6),
        "baseline_mean": round(mean(b), 6),
        "delta": round(mean(c) - mean(b), 6),
        "ci_low": round(lo, 6),
        "ci_high": round(hi, 6),
        "p": round(p, 6),
        "d": round(cohens_d_paired(c, b), 6),
    }


# ─── TARGET REGISTRY ─────────────────────────────────────────────────────────

@dataclass
class TargetSpec:
    name: str
    world_class: type
    graph_factory: Any
    position: str
    eval_ticks: int
    track_hazard: bool = False


TARGETS: Dict[str, TargetSpec] = {
    "logic_large": TargetSpec(
        name="logic_large",
        world_class=LogicWorldLarge,
        graph_factory=lambda seed: make_logic_graph_large(seed=seed, n_vars=6, n_clauses=12),
        position="ASSIGN",
        eval_ticks=30,
    ),
    "hazard_large": TargetSpec(
        name="hazard_large",
        world_class=HazardGraphWorldLarge,
        graph_factory=lambda seed: make_hazard_graph_large(seed=seed, n_nodes=15, hazard_density=0.2),
        position="agent",
        eval_ticks=30,
        track_hazard=True,
    ),
    "rules_chain_long": TargetSpec(
        name="rules_chain_long",
        world_class=RuleWorldChainLong,
        graph_factory=lambda seed: make_rule_graph_chain_long(length=5),
        position="fact_0",
        eval_ticks=30,
    ),
}


# ─── PRETRAIN HELPERS ────────────────────────────────────────────────────────

def _run_grid_pretrain(mote: UniversalMote, ticks: int, seed: int) -> None:
    world = GridGraphWorld()
    random.seed(seed)
    for t in range(ticks):
        g = make_grid_graph(threat_near_resource=(t % 2 == 0))
        g, _, _ = mote.step(world, g, mote_position="mote", tick=t)
        if mote.energy <= 0:
            mote.energy = 50.0


def _run_rules_pretrain(mote: UniversalMote, ticks: int, seed: int) -> None:
    world = RuleWorld()
    random.seed(seed)
    g = make_rule_graph_easy()
    for t in range(ticks):
        g, _, _ = mote.step(world, g, mote_position="fact_a", tick=t)
        if mote.energy <= 0:
            mote.energy = 50.0


def _run_hazard_pretrain(mote: UniversalMote, ticks: int, seed: int) -> None:
    from tais_core.domains import HazardGraphWorld, make_hazard_graph_easy
    world = HazardGraphWorld()
    random.seed(seed)
    g = make_hazard_graph_easy()
    for t in range(ticks):
        g, _, _ = mote.step(world, g, mote_position="agent", tick=t)
        if mote.energy <= 0:
            mote.energy = 50.0


def _run_same_domain_pretrain(mote: UniversalMote, target: str, ticks: int, seed: int) -> None:
    spec = TARGETS[target]
    world = spec.world_class()
    random.seed(seed)
    g = spec.graph_factory(seed)
    for t in range(ticks):
        g, _, _ = mote.step(world, g, mote_position=spec.position, tick=t)
        if mote.energy <= 0:
            mote.energy = 50.0


# ─── TRIAL RUNNER ────────────────────────────────────────────────────────────

def _check_task_success(cons: Consequence) -> bool:
    return cons.task_signal == "TASK_SUCCESS"


def run_trial(seed: int, target: str, condition: str,
              pretrain_ticks: int, eval_ticks: int) -> TrialMetrics:
    spec = TARGETS[target]
    random.seed(seed)
    mote = UniversalMote(energy=100.0)

    if condition == "grid_pretrain":
        _run_grid_pretrain(mote, pretrain_ticks, seed)
    elif condition == "rules_pretrain":
        _run_rules_pretrain(mote, pretrain_ticks, seed)
    elif condition == "three_domain_pretrain":
        third = max(1, pretrain_ticks // 3)
        _run_grid_pretrain(mote, third, seed)
        _run_rules_pretrain(mote, third, seed + 1000)
        _run_hazard_pretrain(mote, pretrain_ticks - 2 * third, seed + 2000)
    elif condition == "same_domain_pretrain":
        _run_same_domain_pretrain(mote, target, pretrain_ticks, seed)
    elif condition == "fresh":
        pass
    else:
        raise ValueError(f"Unknown condition: {condition}")

    world_eval = spec.world_class()
    g_eval = spec.graph_factory(seed)
    reward0 = mote.total_reward
    penalty0 = mote.total_penalty
    invalid0 = mote.invalid_actions
    tu0 = mote.transfer_prior_uses
    ts0 = mote.transfer_prior_total_strength
    tc0 = mote.transfer_prior_correct
    ti0 = mote.transfer_prior_incorrect

    first_success: Optional[float] = None
    contradictions = 0
    pred_errors: List[float] = []
    hazard_steps = 0

    for i in range(eval_ticks):
        g_eval, cons, _ = mote.step(world_eval, g_eval, mote_position=spec.position,
                                     tick=pretrain_ticks + i)
        pred_errors.append(abs(mote.last_prediction - cons.net))
        if _check_task_success(cons) and first_success is None:
            first_success = float(i + 1)
        if cons.task_signal == "TASK_FAILURE" and cons.penalty >= 1.0:
            contradictions += 1
        if spec.track_hazard and cons.task_signal == "TASK_FAILURE":
            hazard_steps += 1
        if mote.energy <= 0:
            mote.energy = 50.0

    correct = mote.transfer_prior_correct - tc0
    incorrect = mote.transfer_prior_incorrect - ti0
    return TrialMetrics(
        reward=mote.total_reward - reward0,
        penalty=mote.total_penalty - penalty0,
        first_task_success_tick=(first_success if first_success is not None else float(eval_ticks + 1)),
        task_completion_rate=(1.0 if first_success is not None else 0.0),
        contradictions=contradictions,
        invalid_actions=mote.invalid_actions - invalid0,
        final_energy=mote.energy,
        prediction_error=mean(pred_errors) if pred_errors else 0.0,
        transfer_uses=mote.transfer_prior_uses - tu0,
        transfer_strength=mote.transfer_prior_total_strength - ts0,
        transfer_precision=correct / max(1, correct + incorrect),
        hazard_steps=hazard_steps,
    )


# ─── EXPERIMENT ──────────────────────────────────────────────────────────────

CONDITIONS = ["fresh", "grid_pretrain", "rules_pretrain", "three_domain_pretrain", "same_domain_pretrain"]

METRICS = [
    ("first_task_success_tick", "First TASK_SUCCESS Tick"),
    ("task_completion_rate", "Task Completion Rate"),
    ("contradictions", "Contradictions (TASK_FAILURE count)"),
    ("reward", "Total Reward"),
    ("invalid_actions", "Invalid Actions"),
    ("final_energy", "Final Energy"),
    ("prediction_error", "Prediction Error"),
    ("transfer_uses", "Transfer Uses"),
    ("transfer_strength", "Transfer Strength"),
    ("transfer_precision", "Transfer Precision"),
    ("hazard_steps", "Hazard Steps"),
]


def run_experiment(seeds: int, pretrain_ticks: int, eval_ticks: int,
                   verbose: bool = False):
    results: Dict[str, Dict[str, ExperimentResult]] = {}
    t0 = time.time()
    for target in TARGETS:
        results[target] = {}
        for cond in CONDITIONS:
            results[target][cond] = ExperimentResult(f"{target}/{cond}")
    for seed in range(seeds):
        if verbose and (seed + 1) % 25 == 0:
            elapsed = time.time() - t0
            print(f"  seed {seed + 1}/{seeds} ({elapsed:.1f}s)")
        for target in TARGETS:
            for cond in CONDITIONS:
                m = run_trial(seed, target, cond, pretrain_ticks, eval_ticks)
                results[target][cond].add(m)
    return results


# ─── OUTPUT ──────────────────────────────────────────────────────────────────

def format_raw_table(results, seeds, pretrain_ticks, eval_ticks):
    lines = []
    lines.append("=" * 120)
    lines.append("  TAIS PHASE R4 — LARGE DOMAIN TRANSFER")
    lines.append("=" * 120)
    lines.append(f"\n  Seeds: {seeds} | Pretrain ticks: {pretrain_ticks} | Eval ticks: {eval_ticks}\n")
    for target in TARGETS:
        lines.append(f"\n  {'=' * 100}")
        lines.append(f"  Target: {target}")
        lines.append(f"  {'=' * 100}")
        for key, label in METRICS:
            lines.append(f"\n    {label} (raw means):")
            lines.append(f"    {'Condition':<30} {'Mean':>12} {'Std':>12}  {'n':>6}")
            lines.append(f"    {'-' * 30} {'-' * 12} {'-' * 12}  {'-' * 6}")
            for cond in CONDITIONS:
                s = results[target][cond].summary()[key]
                lines.append(f"    {cond:<30} {s['mean']:>12.4f} {s['std']:>12.4f}  {s['n']:>6}")
    return "\n".join(lines)


def format_comparison_table(results, seeds, pretrain_ticks, eval_ticks):
    lines = []
    for target in TARGETS:
        lines.append(f"\n  {'=' * 100}")
        lines.append(f"  Target: {target} — Comparison vs fresh")
        lines.append(f"  {'=' * 100}")
        for key, label in METRICS:
            lines.append(f"\n    {label}:")
            lines.append(f"    {'Condition':<30} {'Cond Mean':>10} {'Fresh Mean':>10} {'Delta':>10} {'95% CI':>22} {'p':>10} {'d':>8}")
            lines.append(f"    {'-' * 30} {'-' * 10} {'-' * 10} {'-' * 10} {'-' * 22} {'-' * 10} {'-' * 8}")
            fresh = results[target]["fresh"].values
            for cond in CONDITIONS:
                if cond == "fresh":
                    continue
                c = compare_vs_baseline(results[target][cond].values, fresh, key)
                sig = " ***" if c["p"] < 0.001 else " **" if c["p"] < 0.01 else " *" if c["p"] < 0.05 else ""
                ci = f"[{c['ci_low']:.3f}, {c['ci_high']:.3f}]"
                lines.append(
                    f"    {cond:<30} {c['condition_mean']:>10.3f} {c['baseline_mean']:>10.3f} {c['delta']:>+10.4f} {ci:>22} {c['p']:>10.6f}{sig:<4} {c['d']:>8.3f}"
                )
    return "\n".join(lines)


def write_csv(results, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["target", "condition", "metric", "condition_mean", "baseline",
                     "delta", "ci_low", "ci_high", "p", "d"])
        for target in TARGETS:
            fresh = results[target]["fresh"].values
            for cond in CONDITIONS:
                if cond == "fresh":
                    continue
                for key, _label in METRICS:
                    c = compare_vs_baseline(results[target][cond].values, fresh, key)
                    w.writerow([target, cond, key, c["condition_mean"], "fresh",
                                c["delta"], c["ci_low"], c["ci_high"], c["p"], c["d"]])


def write_json(results, path):
    out = {}
    for target in TARGETS:
        out[target] = {}
        for cond in CONDITIONS:
            out[target][cond] = results[target][cond].summary()
    # Add metadata
    out["_meta"] = {
        "phase": "R4",
        "description": "Large domain variants transfer experiment",
        "conditions": CONDITIONS,
        "targets": list(TARGETS.keys()),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)


def write_md(results, seeds, pretrain_ticks, eval_ticks, path):
    header = f"# Phase R4 — Large Domain Transfer Results\n\n**Seeds:** {seeds} | **Pretrain ticks:** {pretrain_ticks} | **Eval ticks:** {eval_ticks}\n"
    raw = format_raw_table(results, seeds, pretrain_ticks, eval_ticks)
    comp = format_comparison_table(results, seeds, pretrain_ticks, eval_ticks)
    with open(path, "w", encoding="utf-8") as f:
        f.write(header + "\n```\n" + raw + "\n```\n\n```\n" + comp + "\n```\n")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Phase R4 — large domain transfer")
    p.add_argument("--seeds", type=int, default=100)
    p.add_argument("--pretrain", type=int, default=20)
    p.add_argument("--eval", type=int, default=30)
    p.add_argument("--output", type=str, default="results/phase_r/large_domain_transfer/large_domain_transfer")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    out_base = args.output
    seeds = args.seeds
    pretrain = args.pretrain
    eval_ticks = args.eval

    print(f"\n{'=' * 60}\nTAIS Phase R4: seeds={seeds}, "
          f"pretrain={pretrain}, eval={eval_ticks}\n{'=' * 60}\n")
    t0 = time.time()
    results = run_experiment(seeds, pretrain, eval_ticks, verbose=args.verbose)
    elapsed = time.time() - t0

    table = format_raw_table(results, seeds, pretrain, eval_ticks)
    comp = format_comparison_table(results, seeds, pretrain, eval_ticks)
    try:
        print(table)
        print(comp)
    except UnicodeEncodeError:
        sys.stderr.buffer.write((table + comp).encode("utf-8") + b"\n")
    print(f"\nElapsed: {elapsed:.2f}s")

    out_dir = Path(out_base).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    txt_path = out_base + ".txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(table + comp + f"\n\nElapsed: {elapsed:.2f}s\n")

    csv_path = out_base + ".csv"
    write_csv(results, csv_path)

    json_path = out_base + ".json"
    write_json(results, json_path)

    md_path = out_base + ".md"
    write_md(results, seeds, pretrain, eval_ticks, md_path)

    print(f"Wrote: {txt_path}\nWrote: {csv_path}\nWrote: {json_path}\nWrote: {md_path}")


if __name__ == "__main__":
    from pathlib import Path
    main()
