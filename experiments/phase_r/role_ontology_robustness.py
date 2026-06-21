#!/usr/bin/env python3
"""Phase R2 — role-ontology robustness experiment.

Tests whether the hand-designed role ontology is load-bearing for
GridWorld → LogicWorld transfer.  All 7 conditions use the same
paired design (fresh mote + pretrained mote, same seed) as F2.

Conditions:
    canonical_roles           — normal behaviour (baseline)
    shuffled_target_role_hints — permute role_hint on LogicWorld actions
    shuffled_target_universal_ops — permute universal_op on LogicWorld actions
    shuffled_source_roles      — permute roles emitted by classify_action_role during pretrain
    random_compatibility       — replace role_compatibility table with seed-deterministic random values
    identity_only_compatibility — role_compatibility returns 1.0 only if source==target else 0.0
    no_role_transfer           — transfer_action_priors returns all zeros

Run:
    python experiments/phase_r/role_ontology_robustness.py --seeds 200 --pretrain 20 --eval 15

Output: results/phase_r/role_ontology_robustness/
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

from tais_core.domains import GridGraphWorld, LogicWorld, make_grid_graph, make_logic_graph_easy
from tais_core.mote import UniversalMote
from tais_core.reality import Consequence, RealityGraph, Transformation, WorldInterface

# Module-level functions we monkeypatch
import tais_core.memory as memory_module


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


# ─── METRICS (same as logic_transfer_runner) ─────────────────────────────────

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
        }


# ─── ROLE SHUFFLE HELPERS ────────────────────────────────────────────────────

ALL_ROLES = [
    "APPROACH_GOOD", "AVOID_BAD", "VERIFY_UNCERTAIN", "TRANSFORM_TOWARD_GOAL",
    "EXPLORE_UNCERTAIN", "REPAIR_MISMATCH", "MAINTAIN_STABLE", "FAILED", "UNCLASSIFIED",
]


def _shuffle_role_mapping(seed: int, offset: int = 0) -> Dict[str, str]:
    """Deterministic permutation of ALL_ROLES."""
    rng = random.Random(seed + offset)
    shuffled = list(ALL_ROLES)
    rng.shuffle(shuffled)
    return {src: tgt for src, tgt in zip(ALL_ROLES, shuffled)}


def _shuffle_list(values: List, seed: int, offset: int = 0) -> List:
    """Deterministic permutation of a list."""
    rng = random.Random(seed + offset)
    shuffled = list(values)
    rng.shuffle(shuffled)
    return shuffled


def _make_shuffled_transform(t: Transformation, new_role_hint: Optional[str] = None,
                              new_universal_op: Optional[str] = None) -> Transformation:
    """Create a new Transformation with overridden role_hint and/or universal_op."""
    return Transformation(
        name=t.name,
        domain=t.domain,
        universal_op=new_universal_op if new_universal_op is not None else t.universal_op,
        base_cost=t.base_cost,
        role_hint=new_role_hint if new_role_hint is not None else t.role_hint,
    )


# ─── MONKEYPATCH APPLICATION ─────────────────────────────────────────────────

@dataclass
class Patches:
    """Tracks applied monkeypatches for restoration."""
    restore_fns: List[Callable] = field(default_factory=list)

    def add(self, fn: Callable):
        self.restore_fns.append(fn)

    def restore_all(self):
        for fn in self.restore_fns:
            fn()
        self.restore_fns.clear()


def apply_condition_patches(mote: UniversalMote, condition: str, seed: int,
                            is_pretrain: bool, patches: Patches):
    """Apply monkeypatches for a given condition.

    Must be called *before* pretrain.  Some patches are temporary and
    should be removed before eval (e.g. shuffled_source_roles).
    """
    if condition == "canonical_roles":
        return

    if condition == "shuffled_target_role_hints":
        _patch_logicworld_role_hints(patches, seed)

    elif condition == "shuffled_target_universal_ops":
        _patch_logicworld_universal_ops(patches, seed)

    elif condition == "shuffled_source_roles":
        if is_pretrain:
            _patch_shuffled_source_roles(mote, patches, seed)

    elif condition == "random_compatibility":
        _patch_random_compatibility(patches, seed)

    elif condition == "identity_only_compatibility":
        _patch_identity_compatibility(patches)

    elif condition == "no_role_transfer":
        _patch_no_role_transfer(mote, patches)


def _patch_logicworld_role_hints(patches: Patches, seed: int):
    """Permute role_hint values on LogicWorld actions."""
    orig_valid = LogicWorld.valid_actions

    def patched_valid(self, graph, mote_state):
        actions = orig_valid(self, graph, mote_state)
        hints = [a.role_hint for a in actions]
        shuffled = _shuffle_list(hints, seed, offset=999_001)
        return [_make_shuffled_transform(a, new_role_hint=shuffled[i]) for i, a in enumerate(actions)]

    LogicWorld.valid_actions = patched_valid
    patches.add(lambda: setattr(LogicWorld, "valid_actions", orig_valid))


def _patch_logicworld_universal_ops(patches: Patches, seed: int):
    """Permute universal_op values on LogicWorld actions."""
    orig_valid = LogicWorld.valid_actions

    def patched_valid(self, graph, mote_state):
        actions = orig_valid(self, graph, mote_state)
        ops = [a.universal_op for a in actions]
        shuffled = _shuffle_list(ops, seed, offset=999_002)
        return [_make_shuffled_transform(a, new_universal_op=shuffled[i]) for i, a in enumerate(actions)]

    LogicWorld.valid_actions = patched_valid
    patches.add(lambda: setattr(LogicWorld, "valid_actions", orig_valid))


def _patch_shuffled_source_roles(mote: UniversalMote, patches: Patches, seed: int):
    """During pretrain, permute roles emitted by classify_action_role."""
    role_map = _shuffle_role_mapping(seed, offset=999_003)
    orig_classify = mote.classify_action_role

    def patched_classify(action, world, graph_before, graph_after, consequence, mote_state, predicted):
        orig_role = orig_classify(action, world, graph_before, graph_after,
                                  consequence, mote_state, predicted)
        return role_map.get(orig_role, orig_role)

    mote.classify_action_role = patched_classify
    patches.add(lambda: setattr(mote, "classify_action_role", orig_classify))


def _patch_random_compatibility(patches: Patches, seed: int):
    """Replace role_compatibility with seed-deterministic random values."""
    rng = random.Random(seed + 999_004)
    compat_table: Dict[Tuple[str, str], float] = {}
    for src in ALL_ROLES:
        for tgt in ALL_ROLES:
            compat_table[(src, tgt)] = rng.uniform(0.0, 1.0) if src != tgt else 1.0

    def random_compat(source_role: str, target_role: str, **kwargs) -> float:
        if not source_role or not target_role:
            return 0.0
        if source_role == target_role:
            return 1.0
        return compat_table.get((source_role, target_role), 0.0)

    orig_fn = memory_module.role_compatibility
    memory_module.role_compatibility = random_compat
    patches.add(lambda: setattr(memory_module, "role_compatibility", orig_fn))


def _patch_identity_compatibility(patches: Patches):
    """role_compatibility returns 1.0 only if source==target."""
    def identity_compat(source_role: str, target_role: str, **kwargs) -> float:
        if not source_role or not target_role:
            return 0.0
        return 1.0 if source_role == target_role else 0.0

    orig_fn = memory_module.role_compatibility
    memory_module.role_compatibility = identity_compat
    patches.add(lambda: setattr(memory_module, "role_compatibility", orig_fn))


def _patch_no_role_transfer(mote: UniversalMote, patches: Patches):
    """Zero out transfer_action_priors."""
    orig_transfer = mote.memory.transfer_action_priors

    def no_transfer(*args, **kwargs):
        return ({}, 0)

    mote.memory.transfer_action_priors = no_transfer
    patches.add(lambda: setattr(mote.memory, "transfer_action_priors", orig_transfer))


# ─── PRETRAIN / EVAL HELPERS ─────────────────────────────────────────────────

def run_grid_pretrain(mote, ticks, mixed=True):
    world = GridGraphWorld()
    g = make_grid_graph(threat_near_resource=True)
    for t in range(ticks):
        if mixed:
            g = make_grid_graph(threat_near_resource=(t % 2 == 0))
        g, _, _ = mote.step(world, g, mote_position="mote", tick=t)
        if mote.energy <= 0:
            mote.energy = 50.0


def evaluate_logicworld(mote, ticks, start_tick):
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


# ─── TRIAL ───────────────────────────────────────────────────────────────────

def run_trial(seed: int, condition: str, pretrain_domain: Optional[str],
              pretrain_ticks: int, eval_ticks: int) -> TrialMetrics:
    random.seed(seed)
    mote = UniversalMote(energy=100.0)
    patches = Patches()

    # Apply patches for this trial.
    # shuffled_source_roles only applied during pretrain; removed before eval.
    # All other conditions persist through both phases.
    has_pretrain = pretrain_domain is not None
    apply_condition_patches(mote, condition, seed, is_pretrain=has_pretrain, patches=patches)

    if pretrain_domain == "grid":
        run_grid_pretrain(mote, pretrain_ticks, mixed=True)

    # Remove pretrain-only patches (shuffled_source_roles) before eval.
    patches.restore_all()

    # Re-apply patches that should persist through eval (not shuffled_source_roles).
    if condition != "shuffled_source_roles":
        apply_condition_patches(mote, condition, seed, is_pretrain=False, patches=patches)

    metrics = evaluate_logicworld(mote, eval_ticks, start_tick=pretrain_ticks if pretrain_domain else 0)
    patches.restore_all()
    return metrics


# ─── CONDITIONS ──────────────────────────────────────────────────────────────

CONDITIONS = [
    "canonical_roles",
    "shuffled_target_role_hints",
    "shuffled_target_universal_ops",
    "shuffled_source_roles",
    "random_compatibility",
    "identity_only_compatibility",
    "no_role_transfer",
]


def run_experiment(seeds: int, pretrain_ticks: int, eval_ticks: int,
                   condition_filter: Optional[List[str]] = None, verbose: bool = False):
    conditions = [c for c in CONDITIONS if condition_filter is None or c in condition_filter]
    results = {name: ExperimentResult(name) for name in conditions}
    t0 = time.time()
    for seed in range(seeds):
        if verbose and (seed + 1) % 25 == 0:
            print(f"  seed {seed + 1}/{seeds} ({time.time() - t0:.1f}s)")
        for name in conditions:
            fresh = run_trial(10_000 + seed, name, None, pretrain_ticks, eval_ticks)
            pre = run_trial(10_000 + seed, name, "grid", pretrain_ticks, eval_ticks)
            results[name].add(fresh, pre)
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


def format_table(results: Dict[str, ExperimentResult], seeds: int,
                 pretrain_ticks: int, eval_ticks: int) -> str:
    order = CONDITIONS
    lines = []
    lines.append("=" * 122)
    lines.append("  TAIS PHASE R2 — ROLE ONTOLOGY ROBUSTNESS")
    lines.append("=" * 122)
    lines.append(f"\n  Seeds: {seeds} | Pretrain ticks: {pretrain_ticks} | Eval ticks: {eval_ticks}\n")
    for key, label in METRICS:
        lines.append(f"\n  --- {label} ---")
        lines.append(f"  {'Condition':<33} {'Fresh':>10} {'Pretrained':>11} {'Delta':>10} {'95% CI':>20} {'p':>10} {'d':>8}")
        lines.append(f"  {'-'*33} {'-'*10} {'-'*11} {'-'*10} {'-'*20} {'-'*10} {'-'*8}")
        for name in order:
            s = results[name].summary()[key]
            sig = " ***" if s["p"] < 0.001 else " **" if s["p"] < 0.01 else " *" if s["p"] < 0.05 else ""
            ci = f"[{s['ci_low']:.3f}, {s['ci_high']:.3f}]"
            lines.append(
                f"  {name:<33} {s['fresh']:>10.3f} {s['pretrained']:>11.3f} {s['delta']:>+10.4f} {ci:>20} {s['p']:>10.6f}{sig:<4} {s['d']:>8.3f}"
            )
    lines.append("\n" + "=" * 122)
    lines.append("  * p<0.05   ** p<0.01   *** p<0.001")
    lines.append("=" * 122)
    return "\n".join(lines)


def write_csv(results: Dict[str, ExperimentResult], path: str):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["condition", "metric", "fresh", "pretrained", "delta", "ci_low", "ci_high", "p", "d"])
        for name, result in results.items():
            summary = result.summary()
            for key, _label in METRICS:
                s = summary[key]
                w.writerow([name, key, s["fresh"], s["pretrained"], s["delta"], s["ci_low"], s["ci_high"], s["p"], s["d"]])


def main():
    p = argparse.ArgumentParser(description="Phase R2 — role ontology robustness")
    p.add_argument("--seeds", type=int, default=200)
    p.add_argument("--pretrain", type=int, default=20)
    p.add_argument("--eval", type=int, default=15)
    p.add_argument("--condition", type=str, default=None,
                   help="Run only this condition (comma-separated)")
    p.add_argument("--output", type=str, default="results/phase_r/role_ontology_robustness/report.txt")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    condition_filter = args.condition.split(",") if args.condition else None

    print(f"\n{'=' * 60}\nTAIS Phase R2: seeds={args.seeds}, "
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

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(table + f"\n\nElapsed: {elapsed:.2f}s\n")
    csv_path = args.output.rsplit(".", 1)[0] + ".csv"
    write_csv(results, csv_path)
    json_path = args.output.rsplit(".", 1)[0] + ".json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({name: res.summary() for name, res in results.items()}, f, indent=2)
    print(f"Wrote: {args.output}\nWrote: {csv_path}\nWrote: {json_path}")


if __name__ == "__main__":
    main()
