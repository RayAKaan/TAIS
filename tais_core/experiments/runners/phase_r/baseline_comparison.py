#!/usr/bin/env python3
"""Phase R3 — Baseline Agents and Comparison.

Compares TAIS against RandomAgent, HeuristicAgent, TabularQAgent on
GridWorld pretrain (20 ticks) → LogicWorld eval (15 ticks).

Conditions (all paired by seed):
    TAIS_full                — UniversalMote with all mechanisms
    TAIS_no_pattern_transfer — UniversalMote with transfer_action_priors zeroed
    RandomAgent              — deterministic random choice
    HeuristicAgent           — op-weight heuristic
    TabularQAgent            — Q-learning on structural state key

Run:
    python experiments/phase_r/baseline_comparison.py --seeds 200 --pretrain 20 --eval 15
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
from tais_core.domains.logic import LogicWorld, make_logic_graph_easy
from tais_core.mote import UniversalMote
from tais_core.reality import Consequence, RealityGraph, Transformation, WorldInterface

from tais_core.baselines import RandomAgent, HeuristicAgent, TabularQAgent
from tais_core.baselines.base import run_agent_step


# ─── STATS (identical to logic_transfer_runner) ──────────────────────────────

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


# ─── EVAL HELPERS — LogicWorld ──────────────────────────────────────────────

_LOGIC_SOLVE_TICKS = 30


def _make_logic_world():
    return LogicWorld()


def _make_logic_graph():
    return make_logic_graph_easy()


def _check_logic_success(cons: Consequence) -> bool:
    return cons.task_signal == "TASK_SUCCESS"


# ─── TAIS TRIAL ──────────────────────────────────────────────────────────────

def run_tais_trial(seed: int, no_pattern_transfer: bool,
                   pretrain_ticks: int, eval_ticks: int) -> TrialMetrics:
    random.seed(seed)
    mote = UniversalMote(energy=100.0)

    if no_pattern_transfer:
        mote.memory.transfer_action_priors = lambda graph, actions: ({a.name: 0.0 for a in actions}, 0)

    world = GridGraphWorld()
    g = make_grid_graph(threat_near_resource=True)
    for t in range(pretrain_ticks):
        g = make_grid_graph(threat_near_resource=(t % 2 == 0))
        g, _, _ = mote.step(world, g, mote_position="mote", tick=t)
        if mote.energy <= 0:
            mote.energy = 50.0

    world_eval = LogicWorld()
    g_eval = make_logic_graph_easy()
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
    for i in range(eval_ticks):
        g_eval, cons, _ = mote.step(world_eval, g_eval, mote_position="ASSIGN",
                                    tick=pretrain_ticks + i)
        pred_errors.append(abs(mote.last_prediction - cons.net))
        if _check_logic_success(cons) and first_success is None:
            first_success = float(i + 1)
        if cons.task_signal == "TASK_FAILURE" and cons.penalty >= 1.0:
            contradictions += 1
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
    )


# ─── BASELINE AGENT TRIAL ────────────────────────────────────────────────────

@dataclass
class _BaselineCounters:
    total_reward: float = 0.0
    total_penalty: float = 0.0
    invalid_actions: int = 0
    energy: float = 100.0


def run_baseline_trial(agent_class, seed: int,
                       pretrain_ticks: int, eval_ticks: int) -> TrialMetrics:
    agent = agent_class(seed=seed)
    ctr = _BaselineCounters()

    world = GridGraphWorld()
    g = make_grid_graph(threat_near_resource=True)
    mote_state: Dict[str, Any] = {}
    for t in range(pretrain_ticks):
        g = make_grid_graph(threat_near_resource=(t % 2 == 0))
        after, cons, action = run_agent_step(agent, world, g, mote_state,
                                              mote_position="mote", tick=t)
        g = after
        ctr.total_reward += cons.reward
        ctr.total_penalty += cons.penalty
        if not cons.valid:
            ctr.invalid_actions += 1
        cost = action.compute_cost(world.observe(g, "mote"), mote_state) if action else 0.0
        ctr.energy += cons.net - cost
        if ctr.energy <= 0:
            ctr.energy = 50.0

    world_eval = LogicWorld()
    g_eval = make_logic_graph_easy()
    reward0 = ctr.total_reward
    penalty0 = ctr.total_penalty
    invalid0 = ctr.invalid_actions
    energy0 = ctr.energy

    first_success: Optional[float] = None
    contradictions = 0
    for i in range(eval_ticks):
        after, cons, action = run_agent_step(agent, world_eval, g_eval, mote_state,
                                              mote_position="ASSIGN", tick=pretrain_ticks + i)
        g_eval = after
        ctr.total_reward += cons.reward
        ctr.total_penalty += cons.penalty
        if not cons.valid:
            ctr.invalid_actions += 1
        cost = action.compute_cost(world_eval.observe(g_eval, "ASSIGN"), mote_state) if action else 0.0
        ctr.energy += cons.net - cost
        if _check_logic_success(cons) and first_success is None:
            first_success = float(i + 1)
        if cons.task_signal == "TASK_FAILURE" and cons.penalty >= 1.0:
            contradictions += 1
        if ctr.energy <= 0:
            ctr.energy = 50.0

    return TrialMetrics(
        reward=ctr.total_reward - reward0,
        penalty=ctr.total_penalty - penalty0,
        first_task_success_tick=(first_success if first_success is not None else float(eval_ticks + 1)),
        task_completion_rate=(1.0 if first_success is not None else 0.0),
        contradictions=contradictions,
        invalid_actions=ctr.invalid_actions - invalid0,
        final_energy=ctr.energy,
        prediction_error=0.0,
        transfer_uses=0,
        transfer_strength=0.0,
        transfer_precision=0.0,
    )


# ─── CONDITIONS ──────────────────────────────────────────────────────────────

CONDITIONS_ORDER = [
    "TAIS_full",
    "TAIS_no_pattern_transfer",
    "RandomAgent",
    "HeuristicAgent",
    "TabularQAgent",
]


def run_condition(seed: int, condition: str,
                  pretrain_ticks: int, eval_ticks: int) -> TrialMetrics:
    if condition == "TAIS_full":
        return run_tais_trial(seed, no_pattern_transfer=False,
                              pretrain_ticks=pretrain_ticks, eval_ticks=eval_ticks)
    elif condition == "TAIS_no_pattern_transfer":
        return run_tais_trial(seed, no_pattern_transfer=True,
                              pretrain_ticks=pretrain_ticks, eval_ticks=eval_ticks)
    elif condition == "RandomAgent":
        return run_baseline_trial(RandomAgent, seed, pretrain_ticks, eval_ticks)
    elif condition == "HeuristicAgent":
        return run_baseline_trial(HeuristicAgent, seed, pretrain_ticks, eval_ticks)
    elif condition == "TabularQAgent":
        return run_baseline_trial(TabularQAgent, seed, pretrain_ticks, eval_ticks)
    else:
        raise ValueError(f"Unknown condition: {condition}")


def run_experiment(seeds: int, pretrain_ticks: int, eval_ticks: int,
                   verbose: bool = False):
    results = {name: ExperimentResult(name) for name in CONDITIONS_ORDER}
    t0 = time.time()
    for seed in range(seeds):
        if verbose and (seed + 1) % 25 == 0:
            print(f"  seed {seed + 1}/{seeds} ({time.time() - t0:.1f}s)")
        for name in CONDITIONS_ORDER:
            m = run_condition(seed, name, pretrain_ticks, eval_ticks)
            results[name].add(m)
    return results


# ─── OUTPUT ──────────────────────────────────────────────────────────────────

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
]


def format_raw_table(results, seeds, pretrain_ticks, eval_ticks):
    lines = []
    lines.append("=" * 100)
    lines.append("  TAIS PHASE R3 — BASELINE COMPARISON")
    lines.append("=" * 100)
    lines.append(f"\n  Seeds: {seeds} | Pretrain ticks: {pretrain_ticks} | Eval ticks: {eval_ticks}\n")
    for key, label in METRICS:
        lines.append(f"\n  --- {label} (raw means) ---")
        lines.append(f"  {'Condition':<30} {'Mean':>12} {'Std':>12}  {'n':>6}")
        lines.append(f"  {'-'*30} {'-'*12} {'-'*12}  {'-'*6}")
        for name in CONDITIONS_ORDER:
            s = results[name].summary()[key]
            lines.append(f"  {name:<30} {s['mean']:>12.4f} {s['std']:>12.4f}  {s['n']:>6}")
    return "\n".join(lines)


def format_comparison_table(results, baseline_name, seeds, pretrain_ticks, eval_ticks):
    baseline = results[baseline_name]
    order = [n for n in CONDITIONS_ORDER if n != baseline_name]
    lines = []
    lines.append(f"\n  --- Comparison vs {baseline_name} ---")
    for key, label in METRICS:
        lines.append(f"\n  {label}:")
        lines.append(f"  {'Condition':<30} {'Cond Mean':>10} {'Base Mean':>10} {'Delta':>10} {'95% CI':>20} {'p':>10} {'d':>8}")
        lines.append(f"  {'-'*30} {'-'*10} {'-'*10} {'-'*10} {'-'*20} {'-'*10} {'-'*8}")
        for name in order:
            c = compare_vs_baseline(results[name].values, baseline.values, key)
            sig = " ***" if c["p"] < 0.001 else " **" if c["p"] < 0.01 else " *" if c["p"] < 0.05 else ""
            ci = f"[{c['ci_low']:.3f}, {c['ci_high']:.3f}]"
            lines.append(
                f"  {name:<30} {c['condition_mean']:>10.3f} {c['baseline_mean']:>10.3f} {c['delta']:>+10.4f} {ci:>20} {c['p']:>10.6f}{sig:<4} {c['d']:>8.3f}"
            )
    return "\n".join(lines)


def format_full_table(results, seeds, pretrain_ticks, eval_ticks):
    raw = format_raw_table(results, seeds, pretrain_ticks, eval_ticks)
    comp = format_comparison_table(results, "RandomAgent", seeds, pretrain_ticks, eval_ticks)
    footer = "\n\n" + "=" * 100
    footer += "\n  * p<0.05   ** p<0.01   *** p<0.001"
    footer += "\n  RandomAgent is the statistical baseline for comparisons."
    footer += "\n" + "=" * 100
    return raw + comp + footer


def write_csv(results, baseline_name, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["condition", "metric", "condition_mean", "baseline_mean",
                     "delta", "ci_low", "ci_high", "p", "d"])
        for name in CONDITIONS_ORDER:
            if name == baseline_name:
                continue
            for key, _label in METRICS:
                c = compare_vs_baseline(results[name].values, results[baseline_name].values, key)
                w.writerow([name, key, c["condition_mean"], c["baseline_mean"],
                            c["delta"], c["ci_low"], c["ci_high"], c["p"], c["d"]])


def write_md(results, seeds, pretrain_ticks, eval_ticks, path):
    raw = format_raw_table(results, seeds, pretrain_ticks, eval_ticks)
    comp = format_comparison_table(results, "RandomAgent", seeds, pretrain_ticks, eval_ticks)
    md = f"""# Phase R3 — Baseline Comparison Results

**Seeds:** {seeds} | **Pretrain ticks:** {pretrain_ticks} | **Eval ticks:** {eval_ticks}

## Raw Means

```
{raw}
```

## Comparison vs RandomAgent

```
{comp}
```
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Phase R3 — baseline comparison")
    p.add_argument("--seeds", type=int, default=200)
    p.add_argument("--pretrain", type=int, default=20)
    p.add_argument("--eval", type=int, default=15)
    p.add_argument("--output", type=str, default="results/phase_r/baseline_comparison/baseline_comparison")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    out_base = args.output
    seeds = args.seeds
    pretrain = args.pretrain
    eval_ticks = args.eval

    print(f"\n{'=' * 60}\nTAIS Phase R3: seeds={seeds}, "
          f"pretrain={pretrain}, eval={eval_ticks}\n{'=' * 60}\n")
    t0 = time.time()
    results = run_experiment(seeds, pretrain, eval_ticks, verbose=args.verbose)
    elapsed = time.time() - t0

    table = format_full_table(results, seeds, pretrain, eval_ticks)
    try:
        print(table)
    except UnicodeEncodeError:
        sys.stderr.buffer.write(table.encode("utf-8") + b"\n")
    try:
        print(f"\nElapsed: {elapsed:.2f}s")
    except UnicodeEncodeError:
        pass

    txt_path = out_base + ".txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(table + f"\n\nElapsed: {elapsed:.2f}s\n")

    csv_path = out_base + ".csv"
    write_csv(results, "RandomAgent", csv_path)

    json_path = out_base + ".json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({name: res.summary() for name, res in results.items()}, f, indent=2)

    md_path = out_base + ".md"
    write_md(results, seeds, pretrain, eval_ticks, md_path)

    print(f"Wrote: {txt_path}\nWrote: {csv_path}\nWrote: {json_path}\nWrote: {md_path}")


if __name__ == "__main__":
    main()
