#!/usr/bin/env python3
"""Phase R6 — Learned Role Compatibility Prototype.

Tests whether learned role/op compatibility from consequence statistics
can replace or augment the hand-coded role_compatibility table.

Design
------
Source domain: GridWorld for all conditions.
Targets: LogicWorld, RuleWorld, HazardWorld (one per trial, paired by seed).

Conditions per target:
    hardcoded_compatibility       — normal behaviour (baseline)
    learned_compatibility          — replace role_compatibility with learned scores
    learned_plus_hardcoded         — average learned + hardcoded (0.5 + 0.5)
    random_compatibility           — seed-deterministic random table
    no_compatibility               — role_compatibility returns 0.0

Run:
    python experiments/phase_r/learned_role_compatibility.py --seeds 200 --pretrain 20 --eval 15
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
from typing import Any, Callable, Dict, List, Optional, Tuple

from tais_core.domains.gridworld import GridGraphWorld, make_grid_graph
from tais_core.domains.logic import LogicWorld, make_logic_graph_easy
from tais_core.domains.rules import RuleWorld, make_rule_graph_easy
from tais_core.domains.hazard import HazardGraphWorld, make_hazard_graph_easy
from tais_core.mote import UniversalMote
from tais_core.reality import Consequence, RealityGraph, Transformation, WorldInterface
from tais_core.role_learning import (
    LearnedRoleCompatibility,
    make_learned_role_compatibility_fn,
)

# Module-level function we monkeypatch
import tais_core.memory as memory_module


# ─── STATS (identical to all Phase R runners) ─────────────────────────────────

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
    learned_table_size: int = 0
    learned_total_observations: int = 0
    learned_mean_score: float = 0.0


@dataclass
class ExperimentResult:
    condition: str
    fresh: List[TrialMetrics] = field(default_factory=list)
    pretrained: List[TrialMetrics] = field(default_factory=list)

    def add(self, fresh_metrics, pretrained_metrics):
        self.fresh.append(fresh_metrics)
        self.pretrained.append(pretrained_metrics)

    def metric_lists(self, attr):
        return (
            [float(getattr(x, attr)) for x in self.fresh],
            [float(getattr(x, attr)) for x in self.pretrained],
        )

    def summarize_metric(self, attr):
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

    def summary(self):
        return {
            "condition": self.condition,
            "n": len(self.fresh),
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
            "learned_table_size": self.summarize_metric("learned_table_size"),
            "learned_total_observations": self.summarize_metric("learned_total_observations"),
            "learned_mean_score": self.summarize_metric("learned_mean_score"),
        }


# ─── PATCHES (same pattern as R2) ─────────────────────────────────────────────

@dataclass
class Patches:
    restore_fns: List[Callable] = field(default_factory=list)

    def add(self, fn: Callable):
        self.restore_fns.append(fn)

    def restore_all(self):
        for fn in self.restore_fns:
            fn()
        self.restore_fns.clear()


def _patch_role_compatibility(
    patches: Patches,
    learned: Optional[LearnedRoleCompatibility],
    mode: str,
    seed: int,
):
    orig_fn = memory_module.role_compatibility
    if mode == "hardcoded_compatibility":
        return

    patched = make_learned_role_compatibility_fn(
        learned=learned or LearnedRoleCompatibility(),
        mode={
            "learned_compatibility": "learned",
            "learned_plus_hardcoded": "learned_plus_hardcoded",
            "random_compatibility": "random",
            "no_compatibility": "zero",
        }.get(mode, "zero"),
        hardcoded_fn=orig_fn,
        seed=seed,
    )
    memory_module.role_compatibility = patched
    patches.add(lambda: setattr(memory_module, "role_compatibility", orig_fn))


# ─── TARGET REGISTRY ──────────────────────────────────────────────────────────

@dataclass
class TargetSpec:
    name: str
    world_class: type
    graph_factory: Any
    position: str


TARGETS: Dict[str, TargetSpec] = {
    "logic": TargetSpec(
        name="logic",
        world_class=LogicWorld,
        graph_factory=lambda: make_logic_graph_easy(),
        position="ASSIGN",
    ),
    "rules": TargetSpec(
        name="rules",
        world_class=RuleWorld,
        graph_factory=lambda: make_rule_graph_easy(),
        position="fact_a",
    ),
    "hazard": TargetSpec(
        name="hazard",
        world_class=HazardGraphWorld,
        graph_factory=lambda: make_hazard_graph_easy(),
        position="agent",
    ),
}

CONDITIONS = [
    "hardcoded_compatibility",
    "learned_compatibility",
    "learned_plus_hardcoded",
    "random_compatibility",
    "no_compatibility",
]

ALL_ROLES = [
    "APPROACH_GOOD", "AVOID_BAD", "VERIFY_UNCERTAIN", "TRANSFORM_TOWARD_GOAL",
    "EXPLORE_UNCERTAIN", "REPAIR_MISMATCH", "MAINTAIN_STABLE", "FAILED", "UNCLASSIFIED",
]


# ─── PRETRAIN / EVAL HELPERS ──────────────────────────────────────────────────

def run_grid_pretrain(mote, ticks, seed):
    random.seed(seed)
    world = GridGraphWorld()
    g = make_grid_graph(threat_near_resource=True)
    for t in range(ticks):
        g = make_grid_graph(threat_near_resource=(t % 2 == 0))
        g, _, _ = mote.step(world, g, mote_position="mote", tick=t)
        if mote.energy <= 0:
            mote.energy = 50.0


def evaluate_target(mote, target_spec: TargetSpec, ticks, start_tick):
    world = target_spec.world_class()
    g = target_spec.graph_factory()
    reward0 = mote.total_reward
    penalty0 = mote.total_penalty
    invalid0 = mote.invalid_actions
    tu0 = mote.transfer_prior_uses
    ts0 = mote.transfer_prior_total_strength
    tc0 = mote.transfer_prior_correct
    ti0 = mote.transfer_prior_incorrect

    lr_table_size = 0
    lr_total_obs = 0
    lr_mean_score = 0.0
    if mote.learned_role_compatibility is not None:
        lr_table_size = mote.learned_role_compatibility.table_size()
        lr_total_obs = mote.learned_role_compatibility.total_observations()
        lr_mean_score = mote.learned_role_compatibility.mean_learned_score()

    first_success: Optional[float] = None
    contradictions = 0
    pred_errors: List[float] = []
    for i in range(ticks):
        g, cons, _ = mote.step(world, g, mote_position=target_spec.position,
                                tick=start_tick + i)
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
        prediction_error=mean(pred_errors) if pred_errors else 0.0,
        transfer_uses=mote.transfer_prior_uses - tu0,
        transfer_strength=mote.transfer_prior_total_strength - ts0,
        transfer_precision=correct / max(1, correct + incorrect),
        learned_table_size=lr_table_size,
        learned_total_observations=lr_total_obs,
        learned_mean_score=lr_mean_score,
    )


# ─── TRIAL ────────────────────────────────────────────────────────────────────

def run_trial(seed: int, target: str, condition: str,
              pretrain_ticks: int, eval_ticks: int) -> TrialMetrics:
    spec = TARGETS[target]
    random.seed(seed)
    mote = UniversalMote(energy=100.0)
    patches = Patches()

    # Enable learned compatibility for conditions that need it.
    if condition in ("learned_compatibility", "learned_plus_hardcoded"):
        mote.enable_learned_role_compatibility(alpha=0.3)

    # Apply patches after mote creation (patches reference learned table).
    _patch_role_compatibility(patches, mote.learned_role_compatibility, condition, seed)

    # GridWorld pretrain.
    run_grid_pretrain(mote, pretrain_ticks, seed)

    # Remove pretrain-only patches (none in R6 — all conditions persist).
    # Re-apply patches for eval (no distinction needed for R6).
    patches.restore_all()
    _patch_role_compatibility(patches, mote.learned_role_compatibility, condition, seed)

    metrics = evaluate_target(mote, spec, eval_ticks,
                              start_tick=pretrain_ticks if pretrain_ticks > 0 else 0)
    patches.restore_all()
    return metrics


def run_paired_trial(seed: int, target: str, condition: str,
                     pretrain_ticks: int, eval_ticks: int) -> Tuple[TrialMetrics, TrialMetrics]:
    fresh = run_trial(10_000 + seed, target, condition, 0, eval_ticks)
    pre = run_trial(10_000 + seed, target, condition, pretrain_ticks, eval_ticks)
    return fresh, pre


# ─── EXPERIMENT ───────────────────────────────────────────────────────────────

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
    ("learned_table_size", "Learned Table Size"),
    ("learned_total_observations", "Learned Total Observations"),
    ("learned_mean_score", "Learned Mean Score"),
]


def run_experiment(seeds: int, pretrain_ticks: int, eval_ticks: int,
                   condition_filter: Optional[List[str]] = None, verbose: bool = False):
    conditions = [c for c in CONDITIONS if condition_filter is None or c in condition_filter]
    results: Dict[str, Dict[str, ExperimentResult]] = {}
    for target in TARGETS:
        results[target] = {}
        for cond in conditions:
            results[target][cond] = ExperimentResult(f"{target}/{cond}")

    t0 = time.time()
    for seed in range(seeds):
        if verbose and (seed + 1) % 25 == 0:
            print(f"  seed {seed + 1}/{seeds} ({time.time() - t0:.1f}s)")
        for target in TARGETS:
            for cond in conditions:
                fresh, pre = run_paired_trial(seed, target, cond, pretrain_ticks, eval_ticks)
                results[target][cond].add(fresh, pre)
    return results


# ─── OUTPUT ───────────────────────────────────────────────────────────────────

def format_table(results: Dict[str, Dict[str, ExperimentResult]],
                 seeds: int, pretrain_ticks: int, eval_ticks: int) -> str:
    lines = []
    lines.append("=" * 126)
    lines.append("  TAIS PHASE R6 — LEARNED ROLE COMPATIBILITY")
    lines.append("=" * 126)
    lines.append(f"\n  Seeds: {seeds} | Pretrain ticks: {pretrain_ticks} | Eval ticks: {eval_ticks}\n")

    for target in TARGETS:
        lines.append(f"\n  >>> TARGET: {target.upper()} <<<")
        for key, label in METRICS:
            lines.append(f"\n    --- {label} ---")
            lines.append(f"    {'Condition':<33} {'Fresh':>10} {'Pretrained':>11} {'Delta':>10} {'95% CI':>20} {'p':>10} {'d':>8}")
            lines.append(f"    {'-'*33} {'-'*10} {'-'*11} {'-'*10} {'-'*20} {'-'*10} {'-'*8}")
            for cond in CONDITIONS:
                if cond not in results[target]:
                    continue
                s = results[target][cond].summary()[key]
                sig = " ***" if s["p"] < 0.001 else " **" if s["p"] < 0.01 else " *" if s["p"] < 0.05 else ""
                ci = f"[{s['ci_low']:.3f}, {s['ci_high']:.3f}]"
                lines.append(
                    f"    {cond:<33} {s['fresh']:>10.3f} {s['pretrained']:>11.3f} {s['delta']:>+10.4f} {ci:>20} {s['p']:>10.6f}{sig:<4} {s['d']:>8.3f}"
                )
    lines.append("\n" + "=" * 126)
    lines.append("  * p<0.05   ** p<0.01   *** p<0.001")
    lines.append("=" * 126)
    return "\n".join(lines)


def write_csv(results: Dict[str, Dict[str, ExperimentResult]], path: str):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["target", "condition", "metric", "fresh", "pretrained", "delta", "ci_low", "ci_high", "p", "d"])
        for target in TARGETS:
            for cond in CONDITIONS:
                if cond not in results[target]:
                    continue
                summary = results[target][cond].summary()
                for key, _label in METRICS:
                    if key not in summary:
                        continue
                    s = summary[key]
                    w.writerow([target, cond, key, s["fresh"], s["pretrained"], s["delta"],
                                s["ci_low"], s["ci_high"], s["p"], s["d"]])


def main():
    p = argparse.ArgumentParser(description="Phase R6 — learned role compatibility")
    p.add_argument("--seeds", type=int, default=200)
    p.add_argument("--pretrain", type=int, default=20)
    p.add_argument("--eval", type=int, default=15)
    p.add_argument("--condition", type=str, default=None,
                   help="Run only this condition (comma-separated)")
    p.add_argument("--output", type=str, default="results/phase_r/learned_role_compatibility/learned_role_compatibility.txt")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    condition_filter = args.condition.split(",") if args.condition else None

    print(f"\n{'=' * 60}\nTAIS Phase R6: seeds={args.seeds}, "
          f"pretrain={args.pretrain}, eval={args.eval}\n{'=' * 60}\n")
    t0 = time.time()
    results = run_experiment(args.seeds, args.pretrain, args.eval,
                             condition_filter=condition_filter, verbose=args.verbose)
    elapsed = time.time() - t0

    table = format_table(results, args.seeds, args.pretrain, args.eval)
    try:
        print(table)
    except UnicodeEncodeError:
        sys.stderr.buffer.write(table.encode("utf-8") + b"\n")
    try:
        print(f"\nElapsed: {elapsed:.2f}s")
    except UnicodeEncodeError:
        pass

    output_dir = args.output.rsplit("/", 1)[0] if "/" in args.output else args.output.rsplit("\\", 1)[0]
    import os as _os
    _os.makedirs(output_dir, exist_ok=True)

    base = args.output.rsplit(".", 1)[0]
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(table + f"\n\nElapsed: {elapsed:.2f}s\n")
    csv_path = base + ".csv"
    write_csv(results, csv_path)
    json_path = base + ".json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            t: {c: results[t][c].summary() for c in results[t]}
            for t in TARGETS
        }, f, indent=2)
    print(f"Wrote: {args.output}\nWrote: {csv_path}\nWrote: {json_path}")


if __name__ == "__main__":
    main()
