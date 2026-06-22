#!/usr/bin/env python3
"""Phase F2 — Experiment 5: Structural Transfer v2 at scale.

200-seed experiment proving that mote.enable_structural_transfer() produces
genuine topology-based transfer on ProceduralDomainFactory pairs.

Conditions:
  fresh             — no pretrain, no structural transfer
  v2_structural     — pretrain on source WITH enable_structural_transfer()
  legacy_role_hint  — pretrain on source WITHOUT v2 (old role_hint path)
  v2_high_overlap   — v2 with source/target overlap=0.9
  v2_low_overlap    — v2 with source/target overlap=0.3
  v2_zero_overlap   — v2 with overlap=0.0 (control: no shared structure)

Expected results:
  v2_structural  > fresh        (transfer helps)
  v2_structural  > legacy       (v2 outperforms old role_hint path)
  v2_high_overlap > v2_low_overlap  (transfer scales with overlap)
  v2_zero_overlap ≈ fresh        (no structure = no transfer)
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

from tais_core.domains.procedural import ProceduralDomainFactory, ProceduralWorld
from tais_core.mote import UniversalMote
from tais_core.reality import RealityGraph, Transformation


# ─── STATS ───────────────────────────────────────────────────────────────────

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

def paired_ttest(condition: List[float], baseline: List[float]) -> Tuple[float, float]:
    diffs = [c - b for c, b in zip(condition, baseline)]
    if len(diffs) < 2:
        return 0.0, 1.0
    s = std(diffs)
    m = mean(diffs)
    if s < 1e-12:
        return (0.0, 1.0) if abs(m) < 1e-12 else (float("inf"), 0.0)
    t = m / (s / math.sqrt(len(diffs)))
    p = 2.0 * (1.0 - norm_cdf(abs(t)))
    return t, max(0.0, min(1.0, p))

def ci95_delta(condition: List[float], baseline: List[float]) -> Tuple[float, float]:
    diffs = [c - b for c, b in zip(condition, baseline)]
    if len(diffs) < 2:
        return 0.0, 0.0
    m = mean(diffs)
    s = std(diffs)
    tcrit = 1.96 if len(diffs) >= 120 else 1.96 + 2.0 / max(1, len(diffs) - 1)
    margin = tcrit * s / math.sqrt(len(diffs))
    return m - margin, m + margin


# ─── TRIAL METRICS ───────────────────────────────────────────────────────────

@dataclass
class TrialMetrics:
    reward: float
    penalty: float
    task_completion_rate: float
    first_success_tick: float
    invalid_actions: int
    final_energy: float
    prediction_error: float
    transfer_uses: int
    transfer_strength: float
    transfer_precision: float
    policy_sequences: int = 0
    discovered_roles: int = 0
    structural_recall: float = 0.0


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
        if not fresh_vals or not pre_vals:
            return {"fresh": 0, "pretrained": 0, "delta": 0, "ci_low": 0, "ci_high": 0, "p": 1, "d": 0}
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
            "reward": self.summarize_metric("reward"),
            "penalty": self.summarize_metric("penalty"),
            "task_completion_rate": self.summarize_metric("task_completion_rate"),
            "first_success_tick": self.summarize_metric("first_success_tick"),
            "invalid_actions": self.summarize_metric("invalid_actions"),
            "final_energy": self.summarize_metric("final_energy"),
            "prediction_error": self.summarize_metric("prediction_error"),
            "transfer_uses": self.summarize_metric("transfer_uses"),
            "transfer_strength": self.summarize_metric("transfer_strength"),
            "transfer_precision": self.summarize_metric("transfer_precision"),
            "policy_sequences": self.summarize_metric("policy_sequences"),
            "discovered_roles": self.summarize_metric("discovered_roles"),
            "structural_recall": self.summarize_metric("structural_recall"),
        }


# ─── PRETRAIN / EVAL ────────────────────────────────────────────────────────

def pretrain_on_source(
    mote: UniversalMote,
    source_world: ProceduralWorld,
    source_graph: RealityGraph,
    ticks: int,
):
    """Step the mote through a procedural source world."""
    g = source_graph
    for t in range(ticks):
        if mote.energy <= 0:
            mote.energy = 50.0
        g, cons, action = mote.step(source_world, g, mote_position="mote", tick=t)
        # Regenerate source graph occasionally to provide variety
        if t > 0 and t % 10 == 0:
            g = source_graph.snapshot()


def evaluate_on_target(
    mote: UniversalMote,
    target_world: ProceduralWorld,
    target_graph: RealityGraph,
    ticks: int,
) -> TrialMetrics:
    """Evaluate mote performance on a procedural target world."""
    g = target_graph

    reward0 = mote.total_reward
    penalty0 = mote.total_penalty
    invalid0 = mote.invalid_actions
    tu0 = mote.transfer_prior_uses
    ts0 = mote.transfer_prior_total_strength
    tc0 = mote.transfer_prior_correct
    ti0 = mote.transfer_prior_incorrect

    first_success: Optional[float] = None
    pred_errors: List[float] = []

    for i in range(ticks):
        if mote.energy <= 0:
            mote.energy = 50.0
        g, cons, action = mote.step(target_world, g, mote_position="mote", tick=1000 + i)
        pe = abs(mote.last_prediction - cons.net)
        pred_errors.append(pe)
        if cons.task_signal == "TASK_SUCCESS" and first_success is None:
            first_success = float(i + 1)

    correct = mote.transfer_prior_correct - tc0
    incorrect = mote.transfer_prior_incorrect - ti0

    # Structural transfer v2 telemetry
    policy_sequences = 0
    discovered_roles = 0
    if mote._use_structural_transfer and mote.compositional_policy is not None:
        policy_sequences = len(mote.compositional_policy._sequences)
    if mote._use_structural_transfer and mote.role_discovery is not None:
        discovered_roles = len(mote.role_discovery._roles)

    m = mote.metrics()
    structural_recall = m.get("structural_recall", 0.0)

    return TrialMetrics(
        reward=mote.total_reward - reward0,
        penalty=mote.total_penalty - penalty0,
        task_completion_rate=1.0 if first_success is not None else 0.0,
        first_success_tick=first_success if first_success is not None else float(ticks + 1),
        invalid_actions=mote.invalid_actions - invalid0,
        final_energy=mote.energy,
        prediction_error=mean(pred_errors) if pred_errors else 0.0,
        transfer_uses=mote.transfer_prior_uses - tu0,
        transfer_strength=mote.transfer_prior_total_strength - ts0,
        transfer_precision=correct / max(1, correct + incorrect),
        policy_sequences=policy_sequences,
        discovered_roles=discovered_roles,
        structural_recall=structural_recall,
    )


# ─── CONDITIONS ─────────────────────────────────────────────────────────────

CONDITIONS = [
    "fresh",
    "v2_structural",
    "legacy_role_hint",
    "v2_high_overlap",
    "v2_low_overlap",
    "v2_zero_overlap",
]


def run_trial(
    seed: int,
    condition: str,
    pretrain_ticks: int,
    eval_ticks: int,
    overlap: float = 0.7,
    complexity: int = 50,
    depth: int = 3,
    surface_distance: float = 0.9,
) -> Tuple[TrialMetrics, TrialMetrics]:
    """Run a single trial for a given condition.

    Returns (fresh_metrics, condition_metrics) for paired comparison.
    """
    # Generate domain pair — same pair for both fresh and condition
    source_world, target_world = ProceduralDomainFactory.generate_pair(
        overlap=overlap,
        complexity=complexity,
        depth=depth,
        surface_distance=surface_distance,
        seed=seed,
    )
    source_graph = source_world.target_graph
    target_graph = target_world.target_graph

    # ── Fresh mote (no pretrain, no structural transfer) ──
    random.seed(seed + 100_000)
    fresh_mote = UniversalMote(energy=100.0)
    fresh_metrics = evaluate_on_target(fresh_mote, target_world, target_graph, eval_ticks)

    # ── Condition mote ──
    random.seed(seed + 100_000)
    cond_mote = UniversalMote(energy=100.0)

    if condition == "fresh":
        # No pretrain at all
        pass
    elif condition == "v2_structural":
        cond_mote.enable_structural_transfer()
        pretrain_on_source(cond_mote, source_world, source_graph, pretrain_ticks)
    elif condition == "legacy_role_hint":
        # No enable_structural_transfer — legacy path
        pretrain_on_source(cond_mote, source_world, source_graph, pretrain_ticks)
    elif condition == "v2_high_overlap":
        # Generate a high-overlap pair
        src_h, tgt_h = ProceduralDomainFactory.generate_pair(
            overlap=0.9, complexity=complexity, depth=depth,
            surface_distance=surface_distance, seed=seed + 1000,
        )
        cond_mote.enable_structural_transfer()
        pretrain_on_source(cond_mote, src_h, src_h.target_graph, pretrain_ticks)
        # Evaluate on the high-overlap target
        target_world = tgt_h
        target_graph = tgt_h.target_graph
    elif condition == "v2_low_overlap":
        src_l, tgt_l = ProceduralDomainFactory.generate_pair(
            overlap=0.3, complexity=complexity, depth=depth,
            surface_distance=surface_distance, seed=seed + 2000,
        )
        cond_mote.enable_structural_transfer()
        pretrain_on_source(cond_mote, src_l, src_l.target_graph, pretrain_ticks)
        target_world = tgt_l
        target_graph = tgt_l.target_graph
    elif condition == "v2_zero_overlap":
        src_z, tgt_z = ProceduralDomainFactory.generate_pair(
            overlap=0.0, complexity=complexity, depth=depth,
            surface_distance=surface_distance, seed=seed + 3000,
        )
        cond_mote.enable_structural_transfer()
        pretrain_on_source(cond_mote, src_z, src_z.target_graph, pretrain_ticks)
        target_world = tgt_z
        target_graph = tgt_z.target_graph

    cond_metrics = evaluate_on_target(cond_mote, target_world, target_graph, eval_ticks)
    return fresh_metrics, cond_metrics


def run_experiment(
    seeds: int,
    pretrain_ticks: int,
    eval_ticks: int,
    overlap: float = 0.7,
    complexity: int = 50,
    depth: int = 3,
    surface_distance: float = 0.9,
    verbose: bool = False,
) -> Dict[str, ExperimentResult]:
    results = {name: ExperimentResult(name) for name in CONDITIONS}
    t0 = time.time()
    for seed in range(seeds):
        if verbose and (seed + 1) % 25 == 0:
            print(f"  seed {seed + 1}/{seeds} ({time.time() - t0:.1f}s)")
        for name in CONDITIONS:
            fresh_m, cond_m = run_trial(
                seed, name, pretrain_ticks, eval_ticks,
                overlap=overlap, complexity=complexity, depth=depth,
                surface_distance=surface_distance,
            )
            results[name].add(fresh_m, cond_m)
    return results


# ─── OUTPUT ─────────────────────────────────────────────────────────────────

METRICS = [
    ("reward", "Total Reward"),
    ("penalty", "Penalty"),
    ("task_completion_rate", "Task Completion"),
    ("first_success_tick", "First Success Tick"),
    ("invalid_actions", "Invalid Actions"),
    ("final_energy", "Final Energy"),
    ("prediction_error", "Prediction Error"),
    ("transfer_uses", "Transfer Uses"),
    ("transfer_strength", "Transfer Strength"),
    ("transfer_precision", "Transfer Precision"),
    ("policy_sequences", "Policy Sequences"),
    ("discovered_roles", "Discovered Roles"),
    ("structural_recall", "Structural Recall"),
]

ORDER = CONDITIONS


def format_table(
    results, seeds: int, pretrain_ticks: int, eval_ticks: int,
    overlap: float, complexity: int, depth: int, surface_distance: float,
) -> str:
    lines = []
    lines.append("=" * 130)
    lines.append("  PHASE F2 — Experiment 5: Structural Transfer v2 at Scale")
    lines.append("  ProceduralDomainFactory: controlled-overlap cross-domain transfer")
    lines.append("=" * 130)
    lines.append(
        f"\n  Seeds: {seeds} | Pretrain: {pretrain_ticks} ticks | Eval: {eval_ticks} ticks"
        f"\n  Overlap: {overlap} | Complexity: {complexity} | Depth: {depth} | Surface distance: {surface_distance}\n"
    )

    for key, label in METRICS:
        lines.append(f"\n  --- {label} ---")
        lines.append(
            f"  {'Condition':<22} {'Fresh':>10} {'Cond':>11} {'Delta':>10} {'95% CI':>20} {'p':>10} {'d':>8}"
        )
        lines.append(f"  {'-'*22} {'-'*10} {'-'*11} {'-'*10} {'-'*20} {'-'*10} {'-'*8}")
        for name in ORDER:
            s = results[name].summary().get(key, {})
            if not s:
                continue
            sig = (
                " ***" if s.get("p", 1) < 0.001
                else " **" if s.get("p", 1) < 0.01
                else " *" if s.get("p", 1) < 0.05
                else ""
            )
            ci = f"[{s.get('ci_low', 0):.3f}, {s.get('ci_high', 0):.3f}]"
            lines.append(
                f"  {name:<22} {s.get('fresh', 0):>10.3f} {s.get('pretrained', 0):>11.3f} "
                f"{s.get('delta', 0):>+10.4f} {ci:>20} {s.get('p', 1):>10.6f}{sig:<4} {s.get('d', 0):>8.3f}"
            )

    lines.append("\n" + "=" * 130)
    lines.append("  * p<0.05   ** p<0.01   *** p<0.001")
    lines.append("=" * 130)
    return "\n".join(lines)


def write_csv(results: Dict, path: str):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["condition", "metric", "fresh", "condition", "delta", "ci_low", "ci_high", "p", "d"])
        for name, result in results.items():
            summary = result.summary()
            for key, _ in METRICS:
                s = summary.get(key, {})
                if s:
                    w.writerow([
                        name, key, s.get("fresh", 0), s.get("pretrained", 0),
                        s.get("delta", 0), s.get("ci_low", 0), s.get("ci_high", 0),
                        s.get("p", 1), s.get("d", 0),
                    ])


def main():
    p = argparse.ArgumentParser(description="Phase F2 — Structural Transfer v2 at Scale")
    p.add_argument("--seeds", type=int, default=200)
    p.add_argument("--pretrain", type=int, default=30)
    p.add_argument("--eval", type=int, default=20)
    p.add_argument("--overlap", type=float, default=0.7)
    p.add_argument("--complexity", type=int, default=50)
    p.add_argument("--depth", type=int, default=3)
    p.add_argument("--surface-distance", type=float, default=0.9)
    p.add_argument("--output", type=str, default="results/phase_f2/structural_transfer_v2.txt")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    print(
        f"Structural Transfer v2: seeds={args.seeds}, pretrain={args.pretrain}, "
        f"eval={args.eval}, overlap={args.overlap}"
    )
    t0 = time.time()
    results = run_experiment(
        args.seeds, args.pretrain, args.eval,
        overlap=args.overlap, complexity=args.complexity, depth=args.depth,
        surface_distance=args.surface_distance, verbose=args.verbose,
    )
    elapsed = time.time() - t0
    table = format_table(
        results, args.seeds, args.pretrain, args.eval,
        args.overlap, args.complexity, args.depth, args.surface_distance,
    )
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
    print(f"\nWrote: {out}\nWrote: {csv_path}\nWrote: {json_path}")


if __name__ == "__main__":
    main()
