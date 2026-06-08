#!/usr/bin/env python3
"""Phase 4 transfer runner — GridGraphWorld → HazardGraphWorld.

The second transfer pair the roadmap calls for. Mirrors the design of
experiments/ablation_runner.py (post Phase 1.6 RNG fix):

  - paired (fresh vs mixed-Grid pretrained) per seed
  - 8 conditions (full, 4 ablations, 3 pretrain controls)
  - same statistics (paired t, 95% CI, Cohen's d)
  - --horizons CLI flag for horizon sweeps
  - strict task_signal metric: first_task_success_tick (=
    first_apply_implication_tick equivalent on Hazard, just for the
    Exit-reached event)

Conditions:

    full                - mixed Grid -> Hazard, all mechanisms active
    no_action_role      - role classification -> UNCLASSIFIED
    no_prior_decay      - hide domain_action_counts during choose_action
    no_pattern_transfer - transfer_action_priors -> zero
    no_prediction       - predict_action zeroed; affects should_explore() gating only, not action scoring
    empty_pretrain      - 20 ticks EmptyNovelWorld -> Hazard
    random_pretrain     - 20 ticks RandomWorld -> Hazard
    hazard_pretrain     - 20 ticks Hazard -> Hazard (same-domain upper bound)

Run:
    PYTHONPATH=. python3 experiments/hazard_transfer_runner.py --seeds 200 --horizons 15,30

Output: results/hazard_transfer_eval{N}.{txt,csv,json}
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

from tais_core.domains import (
    GridGraphWorld, HazardGraphWorld, make_grid_graph, make_hazard_graph_easy,
)
from tais_core.mote import UniversalMote
from tais_core.reality import Consequence, Entity, RealityGraph, Transformation, WorldInterface


# ─── CONTROL DOMAINS (same as ablation_runner) ──────────────────────────────

class EmptyNovelWorld(WorldInterface):
    domain_name = "novel_empty"

    def observe(self, graph, mote_position):
        return graph

    def valid_actions(self, graph, mote_state):
        return [Transformation("verify_empty", self.domain_name, "VERIFY", base_cost=0.1)]

    def act(self, graph, transformation, mote_state):
        return graph, Consequence(reward=1.0, valid=True, concept_signals={"GOOD": 1.0})

    def evaluate(self, graph, mote_state):
        return 1.0


class RandomWorld(WorldInterface):
    domain_name = "random_noise"

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)

    def observe(self, graph, mote_position):
        return graph

    def valid_actions(self, graph, mote_state):
        return [
            Transformation("noise_verify", self.domain_name, "VERIFY", base_cost=0.5),
            Transformation("noise_test",   self.domain_name, "TEST",   base_cost=0.5),
            Transformation("noise_mutate", self.domain_name, "MUTATE", base_cost=0.5),
        ]

    def act(self, graph, transformation, mote_state):
        raw = self.rng.uniform(-1.0, 2.0)
        valid = self.rng.random() > 0.20
        return graph, Consequence(
            reward=max(0.0, raw),
            penalty=max(0.0, -raw) + (0.5 if not valid else 0.0),
            valid=valid,
            concept_signals={"GOOD": max(0.0, raw), "BAD": max(0.0, -raw)},
        )

    def evaluate(self, graph, mote_state):
        return 0.0


def make_control_graph(domain: str = "control") -> RealityGraph:
    g = RealityGraph(domain, "control")
    g.add_entity(Entity("void", "VOID", {}))
    return g


# ─── STATS (same conventions as ablation_runner) ────────────────────────────

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
    s = std(diffs); m = mean(diffs)
    if s < 1e-12:
        return (0.0, 1.0) if abs(m) < 1e-12 else (float("inf"), 0.0)
    t = m / (s / math.sqrt(len(diffs)))
    p = 2.0 * (1.0 - norm_cdf(abs(t)))
    return t, max(0.0, min(1.0, p))


def ci95_delta(pre: List[float], fresh: List[float]) -> Tuple[float, float]:
    diffs = [p - f for p, f in zip(pre, fresh)]
    if len(diffs) < 2:
        return 0.0, 0.0
    m = mean(diffs); s = std(diffs)
    tcrit = 1.96 if len(diffs) >= 120 else 1.96 + 2.0 / max(1, len(diffs) - 1)
    margin = tcrit * s / math.sqrt(len(diffs))
    return m - margin, m + margin


# ─── ABLATIONS (same as ablation_runner) ────────────────────────────────────

@dataclass(frozen=True)
class AblationControls:
    use_action_role: bool = True
    use_prior_decay: bool = True
    use_pattern_transfer: bool = True
    use_prediction: bool = True

    @classmethod
    def full(cls) -> "AblationControls":              return cls()
    @classmethod
    def no_action_role(cls) -> "AblationControls":     return cls(use_action_role=False)
    @classmethod
    def no_prior_decay(cls) -> "AblationControls":     return cls(use_prior_decay=False)
    @classmethod
    def no_pattern_transfer(cls) -> "AblationControls":return cls(use_pattern_transfer=False)
    @classmethod
    def no_prediction(cls) -> "AblationControls":      return cls(use_prediction=False)


def apply_ablation(mote: UniversalMote, controls: AblationControls):
    if not hasattr(mote, "_ab_orig"):
        mote._ab_orig = {
            "transfer_action_priors": mote.memory.transfer_action_priors,
            "predict_action":         mote.memory.predict_action,
            "classify_action_role":   mote.classify_action_role,
            "choose_action":          mote.choose_action,
        }
    mote.memory.transfer_action_priors = (
        mote._ab_orig["transfer_action_priors"] if controls.use_pattern_transfer
        else (lambda graph, actions: ({a.name: 0.0 for a in actions}, 0))
    )
    mote.memory.predict_action = (
        mote._ab_orig["predict_action"] if controls.use_prediction
        else (lambda action, graph: 0.0)
    )
    mote.classify_action_role = (
        mote._ab_orig["classify_action_role"] if controls.use_action_role
        else (lambda *args, **kwargs: "UNCLASSIFIED")
    )
    if controls.use_prior_decay:
        mote.choose_action = mote._ab_orig["choose_action"]
    else:
        orig_choose = mote._ab_orig["choose_action"]
        def no_decay_choose(observation, actions, _m=mote, _orig=orig_choose):
            saved = dict(_m.domain_action_counts)
            _m.domain_action_counts = {}
            result = _orig(observation, actions)
            _m.domain_action_counts = saved
            return result
        mote.choose_action = no_decay_choose


def restore_ablation(mote: UniversalMote):
    if hasattr(mote, "_ab_orig"):
        for k, v in mote._ab_orig.items():
            if k == "transfer_action_priors":
                mote.memory.transfer_action_priors = v
            elif k == "predict_action":
                mote.memory.predict_action = v
            elif k == "classify_action_role":
                mote.classify_action_role = v
            elif k == "choose_action":
                mote.choose_action = v


# ─── TRIAL ──────────────────────────────────────────────────────────────────

@dataclass
class TrialMetrics:
    reward: float
    penalty: float
    first_task_success_tick: float
    task_completion_rate: float
    hazard_steps: int                 # how many times the mote stepped into a HAZARD_NODE
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
        self.fresh.append(fresh); self.pretrained.append(pretrained)

    def metric_lists(self, attr: str) -> Tuple[List[float], List[float]]:
        return ([float(getattr(x, attr)) for x in self.fresh],
                [float(getattr(x, attr)) for x in self.pretrained])

    def summarize_metric(self, attr: str) -> Dict[str, float]:
        fresh, pre = self.metric_lists(attr)
        lo, hi = ci95_delta(pre, fresh)
        _t, p = paired_ttest(pre, fresh)
        return {
            "fresh":      round(mean(fresh), 6),
            "pretrained": round(mean(pre), 6),
            "delta":      round(mean(pre) - mean(fresh), 6),
            "ci_low":     round(lo, 6),
            "ci_high":    round(hi, 6),
            "p":          round(p, 6),
            "d":          round(cohens_d_paired(pre, fresh), 6),
        }

    def summary(self) -> Dict[str, Any]:
        return {
            "condition":               self.condition,
            "n":                       len(self.fresh),
            "first_task_success_tick": self.summarize_metric("first_task_success_tick"),
            "task_completion_rate":    self.summarize_metric("task_completion_rate"),
            "hazard_steps":            self.summarize_metric("hazard_steps"),
            "reward":                  self.summarize_metric("reward"),
            "invalid_actions":         self.summarize_metric("invalid_actions"),
            "final_energy":            self.summarize_metric("final_energy"),
            "prediction_error":        self.summarize_metric("prediction_error"),
            "transfer_uses":           self.summarize_metric("transfer_uses"),
            "transfer_strength":       self.summarize_metric("transfer_strength"),
            "transfer_precision":      self.summarize_metric("transfer_precision"),
        }


# ─── PRETRAIN / EVAL HELPERS ────────────────────────────────────────────────
# Same Phase 1.6 RNG discipline as ablation_runner: NO inner random.seed() in
# the pretrain helpers; the outer run_trial() seeds once.

def run_grid_pretrain(mote: UniversalMote, ticks: int, mixed: bool = True):
    world = GridGraphWorld()
    g = make_grid_graph(threat_near_resource=True)
    for t in range(ticks):
        if mixed:
            g = make_grid_graph(threat_near_resource=(t % 2 == 0))
        g, _, _ = mote.step(world, g, mote_position="mote", tick=t)
        if mote.energy <= 0:
            mote.energy = 50.0


def run_empty_pretrain(mote: UniversalMote, ticks: int):
    world = EmptyNovelWorld()
    g = make_control_graph("novel_empty")
    for t in range(ticks):
        g, _, _ = mote.step(world, g, mote_position=None, tick=t)
        if mote.energy <= 0:
            mote.energy = 50.0


def run_random_pretrain(mote: UniversalMote, ticks: int, seed: int):
    # RandomWorld owns its own RNG (seeded once at construction); does NOT touch
    # the global RNG. Phase 1.6 discipline.
    world = RandomWorld(seed=seed)
    g = make_control_graph("random_noise")
    for t in range(ticks):
        g, _, _ = mote.step(world, g, mote_position=None, tick=t)
        if mote.energy <= 0:
            mote.energy = 50.0


def run_hazard_pretrain(mote: UniversalMote, ticks: int, start_tick: int = 0):
    world = HazardGraphWorld()
    g = make_hazard_graph_easy()
    for t in range(ticks):
        g, _, _ = mote.step(world, g, mote_position="agent", tick=start_tick + t)
        if mote.energy <= 0:
            mote.energy = 50.0
        # If we accidentally solved during pretrain, reset the graph for
        # subsequent ticks so the mote keeps facing the same task.
        # (Without this the rest of pretrain becomes a no-op.)
        if g.get_entity("agent") and g.get_entity("agent").get("reached_target"):
            g = make_hazard_graph_easy()


def evaluate_hazardworld(mote: UniversalMote, ticks: int, start_tick: int) -> TrialMetrics:
    world = HazardGraphWorld()
    g = make_hazard_graph_easy()
    reward0       = mote.total_reward
    penalty0      = mote.total_penalty
    invalid0      = mote.invalid_actions
    tu0           = mote.transfer_prior_uses
    ts0           = mote.transfer_prior_total_strength
    tc0           = mote.transfer_prior_correct
    ti0           = mote.transfer_prior_incorrect

    first_success: Optional[float] = None
    hazard_steps = 0
    pred_errors: List[float] = []
    for i in range(ticks):
        g, cons, _action = mote.step(world, g, mote_position="agent", tick=start_tick + i)
        pred_errors.append(abs(mote.last_prediction - cons.net))
        if cons.task_signal == "TASK_SUCCESS" and first_success is None:
            first_success = float(i + 1)
        if cons.task_signal == "TASK_FAILURE" and cons.penalty >= 1.0:
            # ignore "no neighbors" invalid moves; only count real hazards
            hazard_steps += 1
        if mote.energy <= 0:
            mote.energy = 50.0

    correct = mote.transfer_prior_correct - tc0
    incorrect = mote.transfer_prior_incorrect - ti0
    return TrialMetrics(
        reward=mote.total_reward - reward0,
        penalty=mote.total_penalty - penalty0,
        first_task_success_tick=(first_success if first_success is not None else float(ticks + 1)),
        task_completion_rate=(1.0 if first_success is not None else 0.0),
        hazard_steps=hazard_steps,
        invalid_actions=mote.invalid_actions - invalid0,
        final_energy=mote.energy,
        prediction_error=mean(pred_errors),
        transfer_uses=mote.transfer_prior_uses - tu0,
        transfer_strength=mote.transfer_prior_total_strength - ts0,
        transfer_precision=correct / max(1, correct + incorrect),
    )


def run_trial(seed: int, controls: AblationControls, pretrain_domain: Optional[str],
              pretrain_ticks: int, eval_ticks: int) -> TrialMetrics:
    random.seed(seed)
    mote = UniversalMote(energy=100.0)
    apply_ablation(mote, controls)

    if pretrain_domain == "grid":
        run_grid_pretrain(mote, pretrain_ticks, mixed=True)
    elif pretrain_domain == "empty":
        run_empty_pretrain(mote, pretrain_ticks)
    elif pretrain_domain == "random":
        run_random_pretrain(mote, pretrain_ticks, seed=seed)
    elif pretrain_domain == "hazard":
        run_hazard_pretrain(mote, pretrain_ticks, start_tick=0)
    elif pretrain_domain is None:
        pass
    else:
        raise ValueError(f"Unknown pretrain_domain: {pretrain_domain}")

    metrics = evaluate_hazardworld(mote, eval_ticks, start_tick=pretrain_ticks if pretrain_domain else 0)
    restore_ablation(mote)
    return metrics


CONDITIONS: Dict[str, Tuple[AblationControls, Optional[str]]] = {
    "full":                (AblationControls.full(),                "grid"),
    "no_action_role":      (AblationControls.no_action_role(),      "grid"),
    "no_prior_decay":      (AblationControls.no_prior_decay(),      "grid"),
    "no_pattern_transfer": (AblationControls.no_pattern_transfer(), "grid"),
    "no_prediction":       (AblationControls.no_prediction(),       "grid"),
    "empty_pretrain":      (AblationControls.full(),                "empty"),
    "random_pretrain":     (AblationControls.full(),                "random"),
    "hazard_pretrain":     (AblationControls.full(),                "hazard"),
}


def run_experiment(seeds: int, pretrain_ticks: int, eval_ticks: int, verbose: bool = False) -> Dict[str, ExperimentResult]:
    results = {name: ExperimentResult(name) for name in CONDITIONS}
    t0 = time.time()
    for seed in range(seeds):
        if verbose and (seed + 1) % 25 == 0:
            print(f"  seed {seed + 1}/{seeds} ({time.time() - t0:.1f}s)")
        for name, (controls, pretrain_domain) in CONDITIONS.items():
            fresh = run_trial(seed=10_000 + seed, controls=controls,
                              pretrain_domain=None, pretrain_ticks=pretrain_ticks, eval_ticks=eval_ticks)
            pre = run_trial(seed=10_000 + seed, controls=controls,
                            pretrain_domain=pretrain_domain, pretrain_ticks=pretrain_ticks, eval_ticks=eval_ticks)
            results[name].add(fresh, pre)
    return results


# ─── OUTPUT ─────────────────────────────────────────────────────────────────

METRICS = [
    ("first_task_success_tick", "First TASK_SUCCESS Tick"),
    ("task_completion_rate",    "Task Completion Rate"),
    ("hazard_steps",            "Hazard Steps"),
    ("reward",                  "Total Reward"),
    ("invalid_actions",         "Invalid Actions"),
    ("final_energy",            "Final Energy"),
    ("prediction_error",        "Prediction Error"),
    ("transfer_uses",           "Transfer Uses"),
    ("transfer_strength",       "Transfer Strength"),
    ("transfer_precision",      "Transfer Precision"),
]


def format_table(results: Dict[str, ExperimentResult], seeds: int, pretrain_ticks: int, eval_ticks: int) -> str:
    order = list(CONDITIONS)
    lines = []
    lines.append("=" * 122)
    lines.append("  TAIS PHASE 4 TRANSFER — mixed GridWorld/controls/Hazard → HazardGraphWorld")
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


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=200)
    p.add_argument("--pretrain", type=int, default=20)
    p.add_argument("--eval", type=int, default=15,
                   help="Default eval=15: HazardWorld solves slower than RuleWorld (mean ~6 ticks for fresh) "
                        "so 15 leaves headroom but is short enough that the ceiling doesn't dominate.")
    p.add_argument("--horizons", type=str, default=None,
                   help="Comma-separated list of eval horizons, e.g. '15,30'.")
    p.add_argument("--output", type=str, default="results/hazard_transfer.txt")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    horizons = [int(args.eval)] if not args.horizons else [int(h) for h in args.horizons.split(",")]
    for eval_ticks in horizons:
        print(f"\n{'=' * 60}\nTAIS Hazard transfer: seeds={args.seeds}, "
              f"pretrain={args.pretrain}, eval={eval_ticks}\n{'=' * 60}\n")
        t0 = time.time()
        results = run_experiment(args.seeds, args.pretrain, eval_ticks, args.verbose)
        elapsed = time.time() - t0
        if args.horizons:
            base, _, ext = args.output.rpartition(".")
            out = f"{base}_eval{eval_ticks}.{ext}" if ext else f"{args.output}_eval{eval_ticks}"
        else:
            out = args.output
        table = format_table(results, args.seeds, args.pretrain, eval_ticks)
        print(table)
        print(f"\nElapsed: {elapsed:.2f}s")
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
