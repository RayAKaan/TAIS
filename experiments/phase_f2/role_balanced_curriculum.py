#!/usr/bin/env python3
"""Phase F2 — Experiment 1: Role-Balanced Curriculum.

Tests whether balanced exposure to both approach and danger roles
during GridWorld pretrain improves transfer to LogicWorld.
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
from typing import Dict, List, Optional, Tuple

from tais_core.domains import GridGraphWorld, LogicWorld, make_grid_graph, make_logic_graph_easy
from tais_core.mote import UniversalMote
from tais_core.reality import Transformation


# ─── STAT HELPERS ─────────────────────────────────────────────────────────────

def mean(xs: List[float]) -> float:
    return sum(xs) / max(1, len(xs))


def std(xs: List[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def cohens_d_paired(pre: List[float], fresh: List[float]) -> float:
    diffs = [p - f for p, f in zip(pre, fresh)]
    s = std(diffs)
    return 0.0 if s < 1e-12 else mean(diffs) / s


def norm_cdf(x: float) -> float:
    if x < 0:
        return 1.0 - norm_cdf(-x)
    k = 1.0 / (1.0 + 0.2316419 * x)
    poly = k * (0.319381530 + k * (-0.356563782 + k * (1.781477937 + k * (-1.821255978 + k * 1.330274429))))
    return 1.0 - (1.0 / math.sqrt(2 * math.pi)) * math.exp(-x * x / 2.0) * poly


def paired_ttest(pre: List[float], fresh: List[float]) -> Tuple[float, float]:
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


# ─── MONKEYPATCH HELPERS ──────────────────────────────────────────────────────

def filter_actions_by_op(original_valid_actions, allowed_ops: set):
    """Return a wrapped valid_actions that only returns actions with allowed ops."""
    def wrapped(self, graph, mote_state):
        actions = original_valid_actions(self, graph, mote_state)
        return [a for a in actions if a.universal_op in allowed_ops]
    return wrapped


def patch_gridworld_for_role(role: str):
    """Return a GridGraphWorld with valid_actions filtered by role.

    Role options:
        'full': all actions (no patch)
        'approach': only MOVE_TOWARD and VERIFY
        'danger': only MOVE_AWAY and VERIFY
    """
    if role == "full":
        return GridGraphWorld()

    original = GridGraphWorld.valid_actions
    if role == "approach":
        allowed = {"MOVE_TOWARD", "VERIFY", "OBSERVE"}
    elif role == "danger":
        allowed = {"MOVE_AWAY", "VERIFY", "OBSERVE"}
    else:
        raise ValueError(f"Unknown role: {role}")

    PatchedWorld = type("PatchedGridWorld", (GridGraphWorld,), {
        "valid_actions": filter_actions_by_op(original, allowed),
    })
    return PatchedWorld()


# ─── TRIAL METRICS ────────────────────────────────────────────────────────────

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
    fresh: List[TrialMetrics] = field(default_factory=list)
    pretrained: List[TrialMetrics] = field(default_factory=list)

    def add(self, fresh_metrics: TrialMetrics, pre_metrics: TrialMetrics):
        self.fresh.append(fresh_metrics)
        self.pretrained.append(pre_metrics)

    def metric_lists(self, attr: str) -> Tuple[List[float], List[float]]:
        return (
            [float(getattr(x, attr)) for x in self.fresh],
            [float(getattr(x, attr)) for x in self.pretrained],
        )

    def summarize_metric(self, attr: str) -> Dict[str, float]:
        fresh_vals, pre_vals = self.metric_lists(attr)
        lo, hi = ci95_delta(pre_vals, fresh_vals)
        _t, p = paired_ttest(pre_vals, fresh_vals)
        return {
            "fresh": round(mean(fresh_vals), 6),
            "pretrained": round(mean(pre_vals), 6),
            "delta": round(mean(pre_vals) - mean(fresh_vals), 6),
            "ci_low": round(lo, 6),
            "ci_high": round(hi, 6),
            "p": round(p, 6),
            "d": round(cohens_d_paired(pre_vals, fresh_vals), 6),
        }

    def summary(self) -> Dict:
        return {
            "condition": self.condition,
            "n": len(self.fresh),
            "first_task_success_tick": self.summarize_metric("first_task_success_tick"),
            "task_completion_rate": self.summarize_metric("task_completion_rate"),
            "reward": self.summarize_metric("reward"),
            "penalty": self.summarize_metric("penalty"),
            "invalid_actions": self.summarize_metric("invalid_actions"),
            "final_energy": self.summarize_metric("final_energy"),
            "prediction_error": self.summarize_metric("prediction_error"),
            "transfer_uses": self.summarize_metric("transfer_uses"),
            "transfer_strength": self.summarize_metric("transfer_strength"),
            "transfer_precision": self.summarize_metric("transfer_precision"),
        }


def ci95_delta(pre: List[float], fresh: List[float]) -> Tuple[float, float]:
    diffs = [p - f for p, f in zip(pre, fresh)]
    if len(diffs) < 2:
        return 0.0, 0.0
    m = mean(diffs)
    s = std(diffs)
    tcrit = 1.96 if len(diffs) >= 120 else 1.96 + 2.0 / max(1, len(diffs) - 1)
    margin = tcrit * s / math.sqrt(len(diffs))
    return m - margin, m + margin


# ─── PRETRAIN / EVAL HELPERS ──────────────────────────────────────────────────

def run_grid_pretrain(mote: UniversalMote, ticks: int, role: str = "full", mixed: bool = True):
    """Pretrain on GridWorld with optional role-filtered actions."""
    world = patch_gridworld_for_role(role)
    for t in range(ticks):
        if mixed:
            g = make_grid_graph(threat_near_resource=(t % 2 == 0))
        else:
            g = make_grid_graph(threat_near_resource=True)
        g, _, _ = mote.step(world, g, mote_position="mote", tick=t)
        if mote.energy <= 0:
            mote.energy = 50.0


def run_role_balanced_pretrain(mote: UniversalMote, ticks: int):
    """Alternate between approach-only and danger-only worlds each tick."""
    for t in range(ticks):
        role = "approach" if t % 2 == 0 else "danger"
        world = patch_gridworld_for_role(role)
        g = make_grid_graph(threat_near_resource=True)
        g, _, _ = mote.step(world, g, mote_position="mote", tick=t)
        if mote.energy <= 0:
            mote.energy = 50.0


def run_logic_pretrain(mote: UniversalMote, ticks: int, start_tick: int = 0):
    world = LogicWorld()
    g = make_logic_graph_easy()
    for t in range(ticks):
        g, _, _ = mote.step(world, g, mote_position="ASSIGN", tick=start_tick + t)
        if mote.energy <= 0:
            mote.energy = 50.0
        a = g.get_entity("ASSIGN")
        if a and a.get("solved"):
            g = make_logic_graph_easy()


def evaluate_logicworld(mote: UniversalMote, ticks: int, start_tick: int) -> TrialMetrics:
    world = LogicWorld()
    g = make_logic_graph_easy()
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

    for i in range(ticks):
        g, cons, _ = mote.step(world, g, mote_position="ASSIGN", tick=start_tick + i)
        pred_errors.append(abs(mote.last_prediction - cons.net))
        if cons.task_signal == "TASK_SUCCESS" and first_success is None:
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
        first_task_success_tick=(first_success if first_success is not None else float(ticks + 1)),
        task_completion_rate=(1.0 if first_success is not None else 0.0),
        contradictions=contradictions,
        invalid_actions=mote.invalid_actions - invalid0,
        final_energy=mote.energy,
        prediction_error=mean(pred_errors),
        transfer_uses=mote.transfer_prior_uses - tu0,
        transfer_strength=mote.transfer_prior_total_strength - ts0,
        transfer_precision=correct / max(1, correct + incorrect),
    )


# ─── TRIAL RUNNER ─────────────────────────────────────────────────────────────

CONDITIONS: Dict[str, str | None] = {
    "fresh": None,
    "grid_standard": "full",
    "danger_only": "danger",
    "approach_only": "approach",
    "role_balanced": "balanced",
    "logic_same_domain": "logic",
}


def run_trial(seed: int, condition: str, pretrain_ticks: int, eval_ticks: int) -> TrialMetrics:
    random.seed(seed)
    mote = UniversalMote(energy=100.0)
    role = CONDITIONS[condition]

    if role is None:
        pass
    elif role == "logic":
        run_logic_pretrain(mote, pretrain_ticks, start_tick=0)
    elif role == "balanced":
        run_role_balanced_pretrain(mote, pretrain_ticks)
    else:
        run_grid_pretrain(mote, pretrain_ticks, role=role, mixed=True)

    return evaluate_logicworld(mote, eval_ticks, start_tick=pretrain_ticks if role else 0)


def run_experiment(seeds: int, pretrain_ticks: int, eval_ticks: int, verbose: bool = False):
    results = {name: ExperimentResult(name) for name in CONDITIONS}
    t0 = time.time()
    for seed in range(seeds):
        if verbose and (seed + 1) % 25 == 0:
            print(f"  seed {seed + 1}/{seeds} ({time.time() - t0:.1f}s)")
        baseline = run_trial(10_000 + seed, "fresh", pretrain_ticks, eval_ticks)
        for name in CONDITIONS:
            cond = run_trial(10_000 + seed, name, pretrain_ticks, eval_ticks)
            results[name].add(baseline, cond)
    return results


# ─── OUTPUT ───────────────────────────────────────────────────────────────────

METRICS = [
    ("first_task_success_tick", "First TASK_SUCCESS Tick"),
    ("task_completion_rate", "Task Completion Rate"),
    ("reward", "Total Reward"),
    ("penalty", "Penalty"),
    ("invalid_actions", "Invalid Actions"),
    ("final_energy", "Final Energy"),
    ("prediction_error", "Prediction Error"),
    ("transfer_uses", "Transfer Uses"),
    ("transfer_strength", "Transfer Strength"),
    ("transfer_precision", "Transfer Precision"),
]


def format_table(results, seeds: int, pretrain_ticks: int, eval_ticks: int) -> str:
    order = list(CONDITIONS)
    lines = []
    lines.append("=" * 122)
    lines.append("  PHASE F2 — Experiment 1: Role-Balanced Curriculum")
    lines.append("  GridWorld (role-filtered) -> LogicWorld")
    lines.append("=" * 122)
    lines.append(f"\n  Seeds: {seeds} | Pretrain ticks: {pretrain_ticks} | Eval ticks: {eval_ticks}\n")

    for key, label in METRICS:
        lines.append(f"\n  --- {label} ---")
        lines.append(f"  {'Condition':<22} {'Fresh':>10} {'Pretrained':>11} {'Delta':>10} {'95% CI':>20} {'p':>10} {'d':>8}")
        lines.append(f"  {'-'*22} {'-'*10} {'-'*11} {'-'*10} {'-'*20} {'-'*10} {'-'*8}")
        for name in order:
            s = results[name].summary().get(key, {})
            sig = " ***" if s.get("p", 1) < 0.001 else " **" if s.get("p", 1) < 0.01 else " *" if s.get("p", 1) < 0.05 else ""
            ci = f"[{s.get('ci_low', 0):.3f}, {s.get('ci_high', 0):.3f}]"
            lines.append(
                f"  {name:<22} {s.get('fresh', 0):>10.3f} {s.get('pretrained', 0):>11.3f} "
                f"{s.get('delta', 0):>+10.4f} {ci:>20} {s.get('p', 1):>10.6f}{sig:<4} {s.get('d', 0):>8.3f}"
            )

    lines.append("\n" + "=" * 122)
    lines.append("  * p<0.05   ** p<0.01   *** p<0.001")
    lines.append("=" * 122)
    return "\n".join(lines)


def write_csv(results: Dict, path: str):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["condition", "metric", "fresh", "pretrained", "delta", "ci_low", "ci_high", "p", "d"])
        for name, result in results.items():
            summary = result.summary()
            for key, _ in METRICS:
                s = summary.get(key, {})
                w.writerow([name, key, s.get("fresh", 0), s.get("pretrained", 0), s.get("delta", 0),
                           s.get("ci_low", 0), s.get("ci_high", 0), s.get("p", 1), s.get("d", 0)])


def main():
    p = argparse.ArgumentParser(description="Phase F2 — Role-Balanced Curriculum")
    p.add_argument("--seeds", type=int, default=200)
    p.add_argument("--pretrain", type=int, default=20)
    p.add_argument("--eval", type=int, default=15)
    p.add_argument("--output", type=str, default="results/phase_f2/role_balanced_curriculum.txt")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    print(f"Role-Balanced Curriculum: seeds={args.seeds}, pretrain={args.pretrain}, eval={args.eval}")
    t0 = time.time()
    results = run_experiment(args.seeds, args.pretrain, args.eval, args.verbose)
    elapsed = time.time() - t0
    table = format_table(results, args.seeds, args.pretrain, args.eval)
    try:
        print(table)
    except UnicodeEncodeError:
        sys.stderr.buffer.write(table.encode("utf-8") + b"\n")

    out = args.output
    with open(out, "w", encoding="utf-8") as f:
        f.write(table + f"\n\nElapsed: {elapsed:.2f}s\n")
    csv_path = out.rsplit(".", 1)[0] + ".csv"
    write_csv(results, csv_path)
    json_path = out.rsplit(".", 1)[0] + ".json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({name: res.summary() for name, res in results.items()}, f, indent=2)
    print(f"Wrote: {out}\nWrote: {csv_path}\nWrote: {json_path}")


if __name__ == "__main__":
    main()
