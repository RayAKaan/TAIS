#!/usr/bin/env python3
"""Phase R5 — Prediction Gating Sweep Experiment.

Tests whether prediction can improve transfer when gated by sufficient
target-domain evidence.

Research question:
    Can prediction improve transfer when activated only after
    k current-domain observations, weighted by w?

Targets:
    logic     — LogicWorld (3 vars, 3 clauses, eval=15 ticks)
    rules     — RuleWorld (3-step chain, eval=15 ticks)
    hazard    — HazardGraphWorld (6 nodes, eval=15 ticks)

Source: GridWorld pretrain (20 ticks)

Conditions:
    no_prediction              — predict_action zeroed via monkeypatch
    prediction_disabled_current — default behavior (baseline)
    prediction_k0_w025         — k=0, w=0.25
    prediction_k3_w025         — k=3, w=0.25
    prediction_k5_w025         — k=5, w=0.25
    prediction_k10_w025        — k=10, w=0.25
    prediction_k3_w05          — k=3, w=0.5
    prediction_k5_w05          — k=5, w=0.5
    prediction_k10_w05         — k=10, w=0.5

Default TAIS behavior is unchanged. R5 tests optional prediction scoring.

Run:
    python experiments/phase_r/prediction_gating_sweep.py --seeds 200 --pretrain 20 --eval 15
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
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tais_core.domains.gridworld import GridGraphWorld, make_grid_graph
from tais_core.domains.hazard import HazardGraphWorld, make_hazard_graph_easy
from tais_core.domains.logic import LogicWorld, make_logic_graph_easy
from tais_core.domains.rules import RuleWorld, make_rule_graph_easy
from tais_core.mote import UniversalMote
from tais_core.reality import Consequence, RealityGraph, Transformation, WorldInterface


# ─── STATS ────────────────────────────────────────────────────────────────────

def mean(xs: List[float]) -> float:
    return sum(xs) / max(1, len(xs))

def std(xs: List[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))

def cohens_d_paired(pre, baseline):
    diffs = [p - b for p, b in zip(pre, baseline)]
    s = std(diffs)
    return 0.0 if s < 1e-12 else mean(diffs) / s

def norm_cdf(x):
    if x < 0:
        return 1.0 - norm_cdf(-x)
    k = 1.0 / (1.0 + 0.2316419 * x)
    poly = k * (0.319381530 + k * (-0.356563782 + k * (1.781477937 + k * (-1.821255978 + k * 1.330274429))))
    return 1.0 - (1.0 / math.sqrt(2 * math.pi)) * math.exp(-x * x / 2.0) * poly

def paired_ttest(pre, baseline):
    diffs = [p - b for p, b in zip(pre, baseline)]
    if len(diffs) < 2:
        return 0.0, 1.0
    s = std(diffs)
    m = mean(diffs)
    if s < 1e-12:
        return (0.0, 1.0) if abs(m) < 1e-12 else (float("inf"), 0.0)
    t = m / (s / math.sqrt(len(diffs)))
    p = 2.0 * (1.0 - norm_cdf(abs(t)))
    return t, max(0.0, min(1.0, p))

def ci95_delta(pre, baseline):
    diffs = [p - b for p, b in zip(pre, baseline)]
    if len(diffs) < 2:
        return 0.0, 0.0
    m = mean(diffs)
    s = std(diffs)
    tcrit = 1.96 if len(diffs) >= 120 else 1.96 + 2.0 / max(1, len(diffs) - 1)
    margin = tcrit * s / math.sqrt(len(diffs))
    return m - margin, m + margin


# ─── METRICS ──────────────────────────────────────────────────────────────────

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


# ─── TARGET REGISTRY ──────────────────────────────────────────────────────────

@dataclass
class TargetSpec:
    name: str
    world_class: type
    graph_factory: Any
    position: str
    eval_ticks: int
    track_hazard: bool = False


TARGETS: Dict[str, TargetSpec] = {
    "logic": TargetSpec(
        name="logic",
        world_class=LogicWorld,
        graph_factory=lambda seed: make_logic_graph_easy(),
        position="ASSIGN",
        eval_ticks=15,
    ),
    "rules": TargetSpec(
        name="rules",
        world_class=RuleWorld,
        graph_factory=lambda _: make_rule_graph_easy(),
        position="fact_a",
        eval_ticks=15,
    ),
    "hazard": TargetSpec(
        name="hazard",
        world_class=HazardGraphWorld,
        graph_factory=lambda _: make_hazard_graph_easy(),
        position="agent",
        eval_ticks=15,
        track_hazard=True,
    ),
}


# ─── APPLY CONDITION ──────────────────────────────────────────────────────────

def _apply_prediction_condition(mote: UniversalMote, condition: str):
    """Configure mote for the given prediction condition.

    Mutates mote in place. Returns nothing.
    """
    if condition == "no_prediction":
        mote.memory.predict_action = lambda action, graph: 0.0
    elif condition == "prediction_disabled_current":
        pass  # default: use_prediction_in_score=False
    elif condition.startswith("prediction_k") and "_w" in condition:
        # Parse k and w from condition name, e.g. prediction_k3_w025
        # kNN_wWWW where NN = digits, WWW = digits (interpreted as decimal)
        parts = condition.replace("prediction_", "").split("_")
        k_part = parts[0]  # e.g. "k3"
        w_part = parts[1]  # e.g. "w025"
        k = int(k_part[1:])
        w_str = w_part[1:]
        if len(w_str) == 3:
            w = int(w_str) / 100.0
        elif len(w_str) == 2:
            w = int(w_str) / 10.0
        else:
            w = float(w_str)
        mote.use_prediction_in_score = True
        mote.prediction_min_domain_observations = k
        mote.prediction_score_weight = w
    else:
        raise ValueError(f"Unknown condition: {condition}")


# ─── PRETRAIN HELPERS ─────────────────────────────────────────────────────────

def _run_grid_pretrain(mote: UniversalMote, ticks: int, seed: int) -> None:
    world = GridGraphWorld()
    random.seed(seed)
    for t in range(ticks):
        g = make_grid_graph(threat_near_resource=(t % 2 == 0))
        g, _, _ = mote.step(world, g, mote_position="mote", tick=t)
        if mote.energy <= 0:
            mote.energy = 50.0


# ─── TRIAL RUNNER ─────────────────────────────────────────────────────────────

def _check_task_success(cons: Consequence) -> bool:
    return cons.task_signal == "TASK_SUCCESS"


def run_trial(seed: int, target: str, condition: str,
              pretrain_ticks: int, eval_ticks: int) -> TrialMetrics:
    spec = TARGETS[target]
    random.seed(seed)
    mote = UniversalMote(energy=100.0)

    # Apply prediction condition BEFORE pretrain so gating takes effect
    _apply_prediction_condition(mote, condition)

    # GridWorld pretrain
    _run_grid_pretrain(mote, pretrain_ticks, seed)

    # Eval on target
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


# ─── EXPERIMENT ───────────────────────────────────────────────────────────────

CONDITIONS = [
    "no_prediction",
    "prediction_disabled_current",
    "prediction_k0_w025",
    "prediction_k3_w025",
    "prediction_k5_w025",
    "prediction_k10_w025",
    "prediction_k3_w05",
    "prediction_k5_w05",
    "prediction_k10_w05",
]

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


# ─── OUTPUT ───────────────────────────────────────────────────────────────────

def format_raw_table(results, seeds, pretrain_ticks, eval_ticks):
    lines = []
    lines.append("=" * 120)
    lines.append("  TAIS PHASE R5 — PREDICTION GATING SWEEP")
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
    baseline_cond = "prediction_disabled_current"
    for target in TARGETS:
        lines.append(f"\n  {'=' * 100}")
        lines.append(f"  Target: {target} — Comparison vs {baseline_cond}")
        lines.append(f"  {'=' * 100}")
        for key, label in METRICS:
            lines.append(f"\n    {label}:")
            lines.append(f"    {'Condition':<30} {'Cond Mean':>10} {'Base Mean':>10} {'Delta':>10} {'95% CI':>22} {'p':>10} {'d':>8}")
            lines.append(f"    {'-' * 30} {'-' * 10} {'-' * 10} {'-' * 10} {'-' * 22} {'-' * 10} {'-' * 8}")
            baseline = results[target][baseline_cond].values
            for cond in CONDITIONS:
                if cond == baseline_cond:
                    continue
                c = compare_vs_baseline(results[target][cond].values, baseline, key)
                sig = " ***" if c["p"] < 0.001 else " **" if c["p"] < 0.01 else " *" if c["p"] < 0.05 else ""
                ci = f"[{c['ci_low']:.3f}, {c['ci_high']:.3f}]"
                lines.append(
                    f"    {cond:<30} {c['condition_mean']:>10.3f} {c['baseline_mean']:>10.3f} {c['delta']:>+10.4f} {ci:>22} {c['p']:>10.6f}{sig:<4} {c['d']:>8.3f}"
                )
    return "\n".join(lines)


def write_csv(results, path):
    baseline_cond = "prediction_disabled_current"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["target", "condition", "metric", "condition_mean", "baseline",
                     "delta", "ci_low", "ci_high", "p", "d"])
        for target in TARGETS:
            baseline = results[target][baseline_cond].values
            for cond in CONDITIONS:
                if cond == baseline_cond:
                    continue
                for key, _label in METRICS:
                    c = compare_vs_baseline(results[target][cond].values, baseline, key)
                    w.writerow([target, cond, key, c["condition_mean"], baseline_cond,
                                c["delta"], c["ci_low"], c["ci_high"], c["p"], c["d"]])


def write_json(results, path):
    out = {}
    for target in TARGETS:
        out[target] = {}
        for cond in CONDITIONS:
            out[target][cond] = results[target][cond].summary()
    out["_meta"] = {
        "phase": "R5",
        "description": "Prediction gating sweep experiment",
        "conditions": CONDITIONS,
        "targets": list(TARGETS.keys()),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)


def write_md(results, seeds, pretrain_ticks, eval_ticks, path):
    header = f"# Phase R5 — Prediction Gating Sweep Results\n\n**Seeds:** {seeds} | **Pretrain ticks:** {pretrain_ticks} | **Eval ticks:** {eval_ticks}\n"
    raw = format_raw_table(results, seeds, pretrain_ticks, eval_ticks)
    comp = format_comparison_table(results, seeds, pretrain_ticks, eval_ticks)
    with open(path, "w", encoding="utf-8") as f:
        f.write(header + "\n```\n" + raw + "\n```\n\n```\n" + comp + "\n```\n")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Phase R5 — prediction gating sweep")
    p.add_argument("--seeds", type=int, default=200)
    p.add_argument("--pretrain", type=int, default=20)
    p.add_argument("--eval", type=int, default=15)
    p.add_argument("--output", type=str, default="results/phase_r/prediction_gating_sweep/prediction_gating_sweep")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    out_base = args.output
    seeds = args.seeds
    pretrain = args.pretrain
    eval_ticks = args.eval

    print(f"\n{'=' * 60}\nTAIS Phase R5: seeds={seeds}, "
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
    main()
