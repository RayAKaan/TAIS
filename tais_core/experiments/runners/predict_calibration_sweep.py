#!/usr/bin/env python3
"""Phase 1.5 calibration sweep — find the best (alpha_pred, alpha_hist) blend.

The diagnostic in experiments/predict_diagnostic.py showed predicted and
historical were double-counting (both are estimators of the same E[net]).
This script sweeps blend weights to find the configuration that minimises
first_apply_implication_tick (the headline strict metric) without inflating
prediction error.

We compare:
  - v2 baseline:    score = pred + hist + transfer - cost - skep*risk        (a=1, b=1)
  - no_pred:        score =        hist + transfer - cost - skep*risk        (a=0, b=1)
  - no_hist:        score = pred        + transfer - cost - skep*risk        (a=1, b=0)
  - blend_60_40:    score = .6*pred + .4*hist + transfer - cost - skep*risk
  - blend_40_60:    score = .4*pred + .6*hist + transfer - cost - skep*risk
  - blend_50_50:    score = .5*pred + .5*hist + transfer - cost - skep*risk

200 seeds, mixed Grid pretrain 20 ticks, eval 12 ticks, paired (fresh vs full).

Run:
    PYTHONPATH=. python3 experiments/predict_calibration_sweep.py
"""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass
from typing import List, Tuple

from tais_core.mote import UniversalMote
from tais_core.domains import GridGraphWorld, RuleWorld, make_grid_graph, make_rule_graph


@dataclass
class Blend:
    name: str
    a_pred: float
    b_hist: float


BLENDS = [
    Blend("v2_baseline_1_1", 1.0, 1.0),
    Blend("no_pred_0_1",     0.0, 1.0),
    Blend("no_hist_1_0",     1.0, 0.0),
    Blend("blend_60_40",     0.6, 0.4),
    Blend("blend_40_60",     0.4, 0.6),
    Blend("blend_50_50",     0.5, 0.5),
]


def patched_choose_action(mote: UniversalMote, a_pred: float, b_hist: float):
    """Reversible monkeypatch: swap choose_action with one that weights pred/hist."""
    orig = mote.choose_action

    def new_choose(observation, actions, _m=mote, _a=a_pred, _b=b_hist, **kwargs):
        if not actions:
            return None
        if _m.memory.should_explore(actions, curiosity=_m.meta.curiosity):
            return random.choice(actions)
        transfer_boosts, transfer_used = _m.memory.transfer_action_priors(observation, actions)
        if transfer_used:
            _m.transfer_prior_uses += transfer_used
            _m.transfer_prior_total_strength += sum(abs(v) for v in transfer_boosts.values())
        local_exp = _m.domain_action_counts.get(observation.domain, 0)
        eff_w = _m.meta.analogy_bias / (1.0 + 0.08 * local_exp)
        best, best_score, best_transfer = None, float("-inf"), 0.0
        for a in actions:
            pred = _m.memory.predict_action(a, observation)
            hist = _m.memory.episodic.action_value(a.name)
            risk = _m.memory.episodic.action_risk(a.name)
            cost = a.compute_cost(observation, _m.state())
            transfer = eff_w * transfer_boosts.get(a.name, 0.0)
            score = _a * pred + _b * hist + transfer - cost - _m.meta.skepticism * risk
            if score > best_score:
                best, best_score, best_transfer = a, score, transfer
        _m._last_chosen_transfer_boost = best_transfer
        return best or random.choice(actions)

    mote.choose_action = new_choose
    return orig


def run_trial(seed: int, pretrain: int, eval_ticks: int, fresh: bool, blend: Blend) -> Tuple[int, float]:
    """Returns (first_apply_tick, total_reward) for one paired trial side."""
    random.seed(seed)
    mote = UniversalMote(energy=100.0)
    patched_choose_action(mote, blend.a_pred, blend.b_hist)

    if not fresh:
        gw = GridGraphWorld()
        g = make_grid_graph(threat_near_resource=True)
        for t in range(pretrain):
            g = make_grid_graph(threat_near_resource=(t % 2 == 0))
            g, _, _ = mote.step(gw, g, mote_position="mote", tick=t)
            if mote.energy <= 0:
                mote.energy = 50.0

    rw = RuleWorld()
    rg = make_rule_graph()
    first_apply = eval_ticks + 1
    total_reward = 0.0
    start = pretrain if not fresh else 0
    for i in range(eval_ticks):
        rg, cons, _ = mote.step(rw, rg, mote_position="rule_ab", tick=start + i)
        total_reward += cons.net
        if cons.task_signal == "TASK_SUCCESS" and first_apply == eval_ticks + 1:
            first_apply = i + 1
        if mote.energy <= 0:
            mote.energy = 50.0
    return first_apply, total_reward


def mean(xs: List[float]) -> float:
    return sum(xs) / max(1, len(xs))


def std(xs: List[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def paired_stats(diffs: List[float]) -> Tuple[float, float, float]:
    """Return (mean, p_two_sided_normal_approx, cohens_d_paired)."""
    if not diffs:
        return 0.0, 1.0, 0.0
    m = mean(diffs)
    s = std(diffs)
    if s < 1e-12:
        return m, (0.0 if abs(m) > 0 else 1.0), 0.0
    t = m / (s / math.sqrt(len(diffs)))
    # normal-approx p
    z = abs(t)
    k = 1.0 / (1.0 + 0.2316419 * z)
    poly = k * (0.319381530 + k * (-0.356563782 + k * (1.781477937 + k * (-1.821255978 + k * 1.330274429))))
    p_one = (1.0 / math.sqrt(2 * math.pi)) * math.exp(-z * z / 2.0) * poly
    p = 2.0 * p_one
    return m, max(0.0, min(1.0, p)), m / s


def main():
    SEEDS = 200
    PRETRAIN = 20
    EVAL = 12

    print(f"\nPhase 1.5 calibration sweep")
    print(f"Seeds: {SEEDS}, pretrain: {PRETRAIN}, eval: {EVAL}")
    print(f"Metric: first_apply_implication_tick (lower is better)")
    print(f"Δ = pretrained − fresh; negative = transfer helped.\n")

    print(f"  {'blend':<22} {'fresh':>7} {'pre':>7} {'Δticks':>8} {'p':>9} {'d':>7}")
    print(f"  {'-'*22} {'-'*7} {'-'*7} {'-'*8} {'-'*9} {'-'*7}")

    for blend in BLENDS:
        fresh_ticks: List[float] = []
        pre_ticks: List[float] = []
        for seed in range(SEEDS):
            ft, _ = run_trial(10_000 + seed, PRETRAIN, EVAL, fresh=True, blend=blend)
            pt, _ = run_trial(10_000 + seed, PRETRAIN, EVAL, fresh=False, blend=blend)
            fresh_ticks.append(ft)
            pre_ticks.append(pt)
        diffs = [p - f for p, f in zip(pre_ticks, fresh_ticks)]
        m, p, d = paired_stats(diffs)
        sig = " ***" if p < 0.001 else " **" if p < 0.01 else " *" if p < 0.05 else "    "
        print(f"  {blend.name:<22} {mean(fresh_ticks):>7.3f} {mean(pre_ticks):>7.3f} "
              f"{m:>+8.3f} {p:>9.4f}{sig} {d:>+7.3f}")

    print()


if __name__ == "__main__":
    main()
