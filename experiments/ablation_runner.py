#!/usr/bin/env python3
"""
experiments_ablation_runner.py
==============================

Ablation experiments for the ACTUAL current TAIS API.

Targets:
    UniversalMote(energy=100)
    mote.step(world, graph, mote_position, tick) -> (graph, consequence, action)
    tais_core.domains.{GridGraphWorld, RuleWorld, make_grid_graph, make_rule_graph}

No core files are modified. Ablations use reversible monkeypatching.

Conditions:
    full                — all mechanisms active
    no_action_role      — role classification returns UNCLASSIFIED, leaving op fallback only
    no_prior_decay      — local domain counts hidden during choose_action, so transfer priors do not decay
    no_pattern_transfer — transfer_action_priors returns zero boosts
    no_prediction       — predict_action returns 0.0

Controls:
    empty_pretrain      — 20 ticks in EmptyNovelWorld before RuleWorld
    random_pretrain     — 20 ticks in RandomWorld before RuleWorld
    ruleworld_pretrain  — 20 ticks in RuleWorld before RuleWorld, upper bound

Run:
    PYTHONPATH=. python3 experiments_ablation_runner.py --seeds 200 --verbose
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from tais_core.mote import UniversalMote
from tais_core.domains import GridGraphWorld, RuleWorld, make_grid_graph, make_rule_graph
from tais_core.reality import Consequence, Entity, RealityGraph, Transformation, WorldInterface


# ─── CONTROL DOMAINS ────────────────────────────────────────────────────────

class EmptyNovelWorld(WorldInterface):
    """A deliberately empty control domain: one safe, uninformative action."""

    domain_name = "novel_empty"

    def observe(self, graph: RealityGraph, mote_position: Any) -> RealityGraph:
        return graph

    def valid_actions(self, graph: RealityGraph, mote_state: Dict[str, Any]) -> List[Transformation]:
        return [Transformation("verify_empty", self.domain_name, "VERIFY", base_cost=0.1)]

    def act(self, graph: RealityGraph, transformation: Transformation, mote_state: Dict[str, Any]) -> Tuple[RealityGraph, Consequence]:
        return graph, Consequence(
            reward=1.0,
            valid=True,
            concept_signals={"GOOD": 1.0},
            explanation={"why": "empty verified"},
        )

    def evaluate(self, graph: RealityGraph, mote_state: Dict[str, Any]) -> float:
        return 1.0


class RandomWorld(WorldInterface):
    """Noisy control domain: random rewards, little learnable structure."""

    domain_name = "random_noise"

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)

    def observe(self, graph: RealityGraph, mote_position: Any) -> RealityGraph:
        return graph

    def valid_actions(self, graph: RealityGraph, mote_state: Dict[str, Any]) -> List[Transformation]:
        return [
            Transformation("noise_verify", self.domain_name, "VERIFY", base_cost=0.5),
            Transformation("noise_test", self.domain_name, "TEST", base_cost=0.5),
            Transformation("noise_mutate", self.domain_name, "MUTATE", base_cost=0.5),
        ]

    def act(self, graph: RealityGraph, transformation: Transformation, mote_state: Dict[str, Any]) -> Tuple[RealityGraph, Consequence]:
        raw = self.rng.uniform(-1.0, 2.0)
        valid = self.rng.random() > 0.20
        return graph, Consequence(
            reward=max(0.0, raw),
            penalty=max(0.0, -raw) + (0.5 if not valid else 0.0),
            valid=valid,
            concept_signals={"GOOD": max(0.0, raw), "BAD": max(0.0, -raw)},
            explanation={"why": "random control"},
        )

    def evaluate(self, graph: RealityGraph, mote_state: Dict[str, Any]) -> float:
        return 0.0


def make_control_graph(domain: str = "control") -> RealityGraph:
    g = RealityGraph(domain, "control")
    g.add_entity(Entity("void", "VOID", {}))
    return g


# ─── STATISTICS ──────────────────────────────────────────────────────────────

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
    # Normal approximation is good enough for n>=~30. This runner is not a stats package.
    p = 2.0 * (1.0 - norm_cdf(abs(t)))
    return t, max(0.0, min(1.0, p))


def ci95_delta(pre: List[float], fresh: List[float]) -> Tuple[float, float]:
    diffs = [p - f for p, f in zip(pre, fresh)]
    if len(diffs) < 2:
        return 0.0, 0.0
    m = mean(diffs)
    s = std(diffs)
    tcrit = 1.96 if len(diffs) >= 120 else 1.96 + 2.0 / max(1, len(diffs) - 1)
    margin = tcrit * s / math.sqrt(len(diffs))
    return m - margin, m + margin


# ─── ABLATIONS ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AblationControls:
    use_action_role: bool = True
    use_prior_decay: bool = True
    use_pattern_transfer: bool = True
    use_prediction: bool = True

    @classmethod
    def full(cls) -> "AblationControls":
        return cls()

    @classmethod
    def no_action_role(cls) -> "AblationControls":
        return cls(use_action_role=False)

    @classmethod
    def no_prior_decay(cls) -> "AblationControls":
        return cls(use_prior_decay=False)

    @classmethod
    def no_pattern_transfer(cls) -> "AblationControls":
        return cls(use_pattern_transfer=False)

    @classmethod
    def no_prediction(cls) -> "AblationControls":
        return cls(use_prediction=False)


def apply_ablation(mote: UniversalMote, controls: AblationControls):
    """Apply ablations by reversible monkeypatching."""
    if not hasattr(mote, "_ab_orig"):
        mote._ab_orig = {
            "transfer_action_priors": mote.memory.transfer_action_priors,
            "predict_action": mote.memory.predict_action,
            "classify_action_role": mote.classify_action_role,
            "choose_action": mote.choose_action,
        }

    if controls.use_pattern_transfer:
        mote.memory.transfer_action_priors = mote._ab_orig["transfer_action_priors"]
    else:
        mote.memory.transfer_action_priors = lambda graph, actions: ({a.name: 0.0 for a in actions}, 0)

    if controls.use_prediction:
        mote.memory.predict_action = mote._ab_orig["predict_action"]
    else:
        mote.memory.predict_action = lambda action, graph: 0.0

    if controls.use_action_role:
        mote.classify_action_role = mote._ab_orig["classify_action_role"]
    else:
        mote.classify_action_role = lambda *args, **kwargs: "UNCLASSIFIED"

    if controls.use_prior_decay:
        mote.choose_action = mote._ab_orig["choose_action"]
    else:
        orig_choose = mote._ab_orig["choose_action"]  # bound method

        def no_decay_choose(observation, actions, _m=mote, _orig=orig_choose):
            saved = dict(_m.domain_action_counts)
            _m.domain_action_counts = {}
            result = _orig(observation, actions)
            _m.domain_action_counts = saved
            return result

        mote.choose_action = no_decay_choose


def restore_ablation(mote: UniversalMote):
    if hasattr(mote, "_ab_orig"):
        mote.memory.transfer_action_priors = mote._ab_orig["transfer_action_priors"]
        mote.memory.predict_action = mote._ab_orig["predict_action"]
        mote.classify_action_role = mote._ab_orig["classify_action_role"]
        mote.choose_action = mote._ab_orig["choose_action"]


# ─── RUNNERS ─────────────────────────────────────────────────────────────────

@dataclass
class TrialMetrics:
    reward: float
    penalty: float
    # Phase 2 strict task metric: first tick on which the world emitted
    # cons.task_signal == "TASK_SUCCESS". Encoded as eval_ticks+1 when the
    # target was never derived in the trial (worst possible value, larger
    # than any in-trial tick so means/CIs behave correctly).
    first_apply_implication_tick: float
    task_completion_rate: float           # 1.0 if TASK_SUCCESS ever fired, else 0.0
    # Kept for backward-compatibility with v1 result files; this is the old
    # "any positive consequence" metric and should NOT be used as headline.
    first_positive_tick_legacy: float
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

    def add(self, fresh: TrialMetrics, pretrained: TrialMetrics):
        self.fresh.append(fresh)
        self.pretrained.append(pretrained)

    def metric_lists(self, attr: str) -> Tuple[List[float], List[float]]:
        return [float(getattr(x, attr)) for x in self.fresh], [float(getattr(x, attr)) for x in self.pretrained]

    def summarize_metric(self, attr: str) -> Dict[str, float]:
        fresh, pre = self.metric_lists(attr)
        lo, hi = ci95_delta(pre, fresh)
        _t, p = paired_ttest(pre, fresh)
        return {
            "fresh": round(mean(fresh), 6),
            "pretrained": round(mean(pre), 6),
            "delta": round(mean(pre) - mean(fresh), 6),
            "ci_low": round(lo, 6),
            "ci_high": round(hi, 6),
            "p": round(p, 6),
            "d": round(cohens_d_paired(pre, fresh), 6),
        }

    def summary(self) -> Dict[str, Dict[str, float]]:
        return {
            "condition": self.condition,
            "n": len(self.fresh),
            "reward": self.summarize_metric("reward"),
            "first_apply_implication_tick": self.summarize_metric("first_apply_implication_tick"),
            "task_completion_rate": self.summarize_metric("task_completion_rate"),
            "first_positive_tick_legacy": self.summarize_metric("first_positive_tick_legacy"),
            "invalid_actions": self.summarize_metric("invalid_actions"),
            "final_energy": self.summarize_metric("final_energy"),
            "prediction_error": self.summarize_metric("prediction_error"),
            "transfer_uses": self.summarize_metric("transfer_uses"),
            "transfer_strength": self.summarize_metric("transfer_strength"),
            "transfer_precision": self.summarize_metric("transfer_precision"),
        }


def run_grid_pretrain(mote: UniversalMote, ticks: int, seed: int, mixed: bool = True):
    random.seed(seed)
    world = GridGraphWorld()
    graph = make_grid_graph(threat_near_resource=True)
    for t in range(ticks):
        if mixed:
            graph = make_grid_graph(threat_near_resource=(t % 2 == 0))
        graph, _cons, _action = mote.step(world, graph, mote_position="mote", tick=t)
        if mote.energy <= 0:
            mote.energy = 50.0


def run_empty_pretrain(mote: UniversalMote, ticks: int):
    world = EmptyNovelWorld()
    graph = make_control_graph("novel_empty")
    for t in range(ticks):
        graph, _cons, _action = mote.step(world, graph, mote_position=None, tick=t)
        if mote.energy <= 0:
            mote.energy = 50.0


def run_random_pretrain(mote: UniversalMote, ticks: int, seed: int):
    world = RandomWorld(seed=seed)
    graph = make_control_graph("random_noise")
    for t in range(ticks):
        graph, _cons, _action = mote.step(world, graph, mote_position=None, tick=t)
        if mote.energy <= 0:
            mote.energy = 50.0


def run_rule_pretrain(mote: UniversalMote, ticks: int, start_tick: int = 0):
    world = RuleWorld()
    graph = make_rule_graph()
    for t in range(ticks):
        graph, _cons, _action = mote.step(world, graph, mote_position="rule_ab", tick=start_tick + t)
        if mote.energy <= 0:
            mote.energy = 50.0


def evaluate_ruleworld(mote: UniversalMote, ticks: int, start_tick: int) -> TrialMetrics:
    world = RuleWorld()
    graph = make_rule_graph()
    reward0 = mote.total_reward
    penalty0 = mote.total_penalty
    invalid0 = mote.invalid_actions
    transfer_uses0 = mote.transfer_prior_uses
    transfer_strength0 = mote.transfer_prior_total_strength
    correct0 = mote.transfer_prior_correct
    incorrect0 = mote.transfer_prior_incorrect

    first_task_success_tick: Optional[float] = None  # Phase 2 strict metric
    first_positive_tick: Optional[float] = None      # legacy / sanity
    pred_errors: List[float] = []
    for i in range(ticks):
        graph, cons, action = mote.step(world, graph, mote_position="rule_ab", tick=start_tick + i)
        pred_errors.append(abs(mote.last_prediction - cons.net))
        if first_task_success_tick is None and cons.task_signal == "TASK_SUCCESS":
            first_task_success_tick = float(i + 1)
        if first_positive_tick is None and cons.net > 0:
            first_positive_tick = float(i + 1)
        if mote.energy <= 0:
            mote.energy = 50.0

    correct = mote.transfer_prior_correct - correct0
    incorrect = mote.transfer_prior_incorrect - incorrect0
    return TrialMetrics(
        reward=mote.total_reward - reward0,
        penalty=mote.total_penalty - penalty0,
        first_apply_implication_tick=(
            first_task_success_tick if first_task_success_tick is not None else float(ticks + 1)
        ),
        task_completion_rate=1.0 if first_task_success_tick is not None else 0.0,
        first_positive_tick_legacy=(
            first_positive_tick if first_positive_tick is not None else float(ticks + 1)
        ),
        invalid_actions=mote.invalid_actions - invalid0,
        final_energy=mote.energy,
        prediction_error=mean(pred_errors),
        transfer_uses=mote.transfer_prior_uses - transfer_uses0,
        transfer_strength=mote.transfer_prior_total_strength - transfer_strength0,
        transfer_precision=correct / max(1, correct + incorrect),
    )


def run_trial(seed: int, controls: AblationControls, pretrain_domain: Optional[str], pretrain_ticks: int, eval_ticks: int) -> TrialMetrics:
    random.seed(seed)
    mote = UniversalMote(energy=100.0)
    apply_ablation(mote, controls)

    if pretrain_domain == "grid":
        run_grid_pretrain(mote, pretrain_ticks, seed=seed, mixed=True)
    elif pretrain_domain == "empty":
        run_empty_pretrain(mote, pretrain_ticks)
    elif pretrain_domain == "random":
        run_random_pretrain(mote, pretrain_ticks, seed=seed)
    elif pretrain_domain == "rules":
        run_rule_pretrain(mote, pretrain_ticks, start_tick=0)
    elif pretrain_domain is None:
        pass
    else:
        raise ValueError(f"Unknown pretrain_domain: {pretrain_domain}")

    metrics = evaluate_ruleworld(mote, eval_ticks, start_tick=pretrain_ticks if pretrain_domain else 0)
    restore_ablation(mote)
    return metrics


CONDITIONS: Dict[str, Tuple[AblationControls, Optional[str]]] = {
    "full": (AblationControls.full(), "grid"),
    "no_action_role": (AblationControls.no_action_role(), "grid"),
    "no_prior_decay": (AblationControls.no_prior_decay(), "grid"),
    "no_pattern_transfer": (AblationControls.no_pattern_transfer(), "grid"),
    "no_prediction": (AblationControls.no_prediction(), "grid"),
    "empty_pretrain": (AblationControls.full(), "empty"),
    "random_pretrain": (AblationControls.full(), "random"),
    "ruleworld_pretrain": (AblationControls.full(), "rules"),
}


def run_experiment(seeds: int = 200, pretrain_ticks: int = 20, eval_ticks: int = 12, verbose: bool = False) -> Dict[str, ExperimentResult]:
    results = {name: ExperimentResult(name) for name in CONDITIONS}
    t0 = time.time()
    for seed in range(seeds):
        if verbose and (seed + 1) % 25 == 0:
            print(f"  seed {seed + 1}/{seeds} ({time.time() - t0:.1f}s)")
        for name, (controls, pretrain_domain) in CONDITIONS.items():
            # Fresh uses same controls but no pretraining.
            fresh = run_trial(seed=10_000 + seed, controls=controls, pretrain_domain=None, pretrain_ticks=pretrain_ticks, eval_ticks=eval_ticks)
            pre = run_trial(seed=10_000 + seed, controls=controls, pretrain_domain=pretrain_domain, pretrain_ticks=pretrain_ticks, eval_ticks=eval_ticks)
            results[name].add(fresh, pre)
    return results


# ─── OUTPUT ─────────────────────────────────────────────────────────────────

METRICS = [
    # Phase 2 strict task metric is the headline.
    ("first_apply_implication_tick", "First Apply (TASK_SUCCESS) Tick"),
    ("task_completion_rate", "Task Completion Rate"),
    ("reward", "Total Reward"),
    ("invalid_actions", "Invalid Actions"),
    ("final_energy", "Final Energy"),
    ("prediction_error", "Prediction Error"),
    ("transfer_uses", "Transfer Uses"),
    ("transfer_strength", "Transfer Strength"),
    ("transfer_precision", "Transfer Precision"),
    # Kept last for sanity-comparison against v1 reports only.
    ("first_positive_tick_legacy", "First +Reward Tick (legacy v1)"),
]


def format_table(results: Dict[str, ExperimentResult], seeds: int, pretrain_ticks: int, eval_ticks: int) -> str:
    order = list(CONDITIONS)
    lines = []
    lines.append("=" * 122)
    lines.append("  TAIS ABLATION EXPERIMENT — mixed GridWorld/controls → RuleWorld")
    lines.append("=" * 122)
    lines.append(f"\n  Seeds: {seeds} | Pretrain ticks: {pretrain_ticks} | Eval ticks: {eval_ticks}\n")
    for key, label in METRICS:
        lines.append(f"\n  ─── {label} ───")
        lines.append(f"  {'Condition':<22} {'Fresh':>10} {'Pretrained':>11} {'Delta':>10} {'95% CI':>20} {'p':>10} {'d':>8}")
        lines.append(f"  {'─'*22} {'─'*10} {'─'*11} {'─'*10} {'─'*20} {'─'*10} {'─'*8}")
        for name in order:
            s = results[name].summary()[key]
            sig = " ***" if s["p"] < 0.001 else " **" if s["p"] < 0.01 else " *" if s["p"] < 0.05 else ""
            ci = f"[{s['ci_low']:.3f}, {s['ci_high']:.3f}]"
            lines.append(
                f"  {name:<22} {s['fresh']:>10.3f} {s['pretrained']:>11.3f} {s['delta']:>+10.4f} {ci:>20} {s['p']:>10.6f}{sig:<4} {s['d']:>8.3f}"
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


def _write_outputs(results, args, eval_ticks, output_path, elapsed):
    table = format_table(results, args.seeds, args.pretrain, eval_ticks)
    print(table)
    print(f"\nElapsed (eval={eval_ticks}): {elapsed:.2f}s")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(table + f"\n\nElapsed: {elapsed:.2f}s\n")
    csv_path = output_path.rsplit(".", 1)[0] + ".csv"
    write_csv(results, csv_path)
    json_path = output_path.rsplit(".", 1)[0] + ".json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({name: res.summary() for name, res in results.items()}, f, indent=2)
    print(f"Wrote: {output_path}")
    print(f"Wrote: {csv_path}")
    print(f"Wrote: {json_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=200)
    parser.add_argument("--pretrain", type=int, default=20)
    parser.add_argument("--eval", type=int, default=12,
                        help="Single eval horizon. Ignored if --horizons is given.")
    parser.add_argument("--horizons", type=str, default=None,
                        help="Comma-separated list of eval horizons, e.g. '12,30,50'. "
                             "Runs the full ablation suite once per horizon.")
    parser.add_argument("--output", type=str, default="results/ablation_v2.txt",
                        help="Output path. When --horizons is used, the eval value is "
                             "appended before the extension: ablation_v2_eval12.txt etc.")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    horizons = [int(args.eval)] if not args.horizons else [int(h) for h in args.horizons.split(",")]

    for eval_ticks in horizons:
        print(f"\n{'=' * 60}\nTAIS ablation v2: seeds={args.seeds}, "
              f"pretrain={args.pretrain}, eval={eval_ticks}\n{'=' * 60}\n")
        t0 = time.time()
        results = run_experiment(args.seeds, args.pretrain, eval_ticks, args.verbose)
        elapsed = time.time() - t0

        if args.horizons:
            base, _, ext = args.output.rpartition(".")
            out = f"{base}_eval{eval_ticks}.{ext}" if ext else f"{args.output}_eval{eval_ticks}"
        else:
            out = args.output
        _write_outputs(results, args, eval_ticks, out, elapsed)


if __name__ == "__main__":
    main()
