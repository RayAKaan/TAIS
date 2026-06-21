#!/usr/bin/env python3
"""Phase 1.6 design sweep — pick the choose_action score formula.

After the Phase 1.6 runner fix, the corrected ablation shows `no_prediction`
beats `full` on first_apply_implication_tick by a *larger* margin than
v2/v3 reported:

    h=12: full Δ=-1.96, no_prediction Δ=-3.86  (1.9-tick gap)
    h=50: full Δ=-3.59, no_prediction Δ=-6.13  (2.5-tick gap)

Root cause is the double-counting in choose_action:
    score = predicted + historical + transfer - cost - skep * risk
where `predicted` (EWM) and `historical` (unweighted mean) are both
estimators of the same E[net]. Adding them as if independent over-weights
known-good actions and amplifies any residual calibration bias.

This sweep compares score-formula candidates on:
  - RuleWorld (easy)         — current benchmark
  - RuleWorldChain           — multi-step, exposes long-horizon credit asym.
  - RuleWorldDistractor      — many irrelevant rules, exposes selection

Candidates:
  - baseline_1_1     score = 1*pred + 1*hist + transfer - cost - skep*risk
  - drop_pred_0_1    score =          1*hist + transfer - cost - skep*risk   (= no_prediction in ablation)
  - drop_hist_1_0    score = 1*pred          + transfer - cost - skep*risk
  - blend_50_50      score = .5*pred + .5*hist + transfer - cost - skep*risk
  - blend_60_40      score = .6*pred + .4*hist + transfer - cost - skep*risk

Run:
    PYTHONPATH=. python3 experiments/choose_action_design_sweep.py
"""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass
from typing import Callable, List, Tuple

from tais_core.mote import UniversalMote
from tais_core.domains import (
    GridGraphWorld, RuleWorld, RuleWorldChain, RuleWorldDistractor,
    make_grid_graph, make_rule_graph, make_rule_graph_chain, make_rule_graph_distractor,
)


@dataclass
class Blend:
    name: str
    a_pred: float
    b_hist: float


BLENDS = [
    Blend("baseline_1_1",  1.0, 1.0),
    Blend("drop_pred_0_1", 0.0, 1.0),
    Blend("drop_hist_1_0", 1.0, 0.0),
    Blend("blend_50_50",   0.5, 0.5),
    Blend("blend_60_40",   0.6, 0.4),
]


@dataclass
class DomainSpec:
    name: str
    world_cls: type
    graph_builder: Callable
    mote_position: str


DOMAINS = [
    DomainSpec("RuleWorld",           RuleWorld,           make_rule_graph,           "rule_ab"),
    DomainSpec("RuleWorldChain",      RuleWorldChain,      make_rule_graph_chain,     "rule_ab"),
    DomainSpec("RuleWorldDistractor", RuleWorldDistractor, make_rule_graph_distractor, "rule_ab"),
]


def patched_choose_action(mote: UniversalMote, a_pred: float, b_hist: float):
    """Reversible monkeypatch of choose_action with a weighted blend."""
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


def run_trial(seed: int, blend: Blend, domain: DomainSpec, pretrain: int, eval_ticks: int, fresh: bool) -> Tuple[int, float]:
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

    rw = domain.world_cls()
    rg = domain.graph_builder()
    first_apply = eval_ticks + 1
    total = 0.0
    start = pretrain if not fresh else 0
    for i in range(eval_ticks):
        rg, cons, _ = mote.step(rw, rg, mote_position=domain.mote_position, tick=start + i)
        total += cons.net
        if cons.task_signal == "TASK_SUCCESS" and first_apply == eval_ticks + 1:
            first_apply = i + 1
        if mote.energy <= 0:
            mote.energy = 50.0
    return first_apply, total


def paired_stats(diffs: List[float]) -> Tuple[float, float, float]:
    if not diffs:
        return 0.0, 1.0, 0.0
    m = statistics.mean(diffs)
    s = statistics.stdev(diffs) if len(diffs) > 1 else 0.0
    if s < 1e-12:
        return m, (0.0 if abs(m) > 0 else 1.0), 0.0
    t = m / (s / math.sqrt(len(diffs)))
    z = abs(t)
    k = 1.0 / (1.0 + 0.2316419 * z)
    poly = k * (0.319381530 + k * (-0.356563782 + k * (1.781477937 + k * (-1.821255978 + k * 1.330274429))))
    p_one = (1.0 / math.sqrt(2 * math.pi)) * math.exp(-z * z / 2.0) * poly
    return m, max(0.0, min(1.0, 2.0 * p_one)), m / s


def main():
    SEEDS = 200
    PRETRAIN = 20
    EVAL_RULE = 12
    EVAL_CHAIN = 30      # chain needs 2 derivations, give it more time
    EVAL_DISTRACTOR = 12

    print("Phase 1.6 design sweep: which choose_action blend is best?")
    print(f"Seeds: {SEEDS} per cell. Paired (fresh vs mixed-Grid pretrained).")
    print("Metric: first_apply_implication_tick. Lower Δ = stronger transfer.")
    print()

    for domain in DOMAINS:
        eval_ticks = {"RuleWorld": EVAL_RULE, "RuleWorldChain": EVAL_CHAIN, "RuleWorldDistractor": EVAL_DISTRACTOR}[domain.name]
        print(f"════════ {domain.name} (eval={eval_ticks}) ════════")
        print(f"  {'blend':<18} {'fresh':>7} {'pre':>7} {'Δticks':>8} {'p':>9} {'d':>7}")
        print(f"  {'-'*18} {'-'*7} {'-'*7} {'-'*8} {'-'*9} {'-'*7}")
        for blend in BLENDS:
            fresh_ticks: List[float] = []
            pre_ticks: List[float] = []
            for seed in range(SEEDS):
                ft, _ = run_trial(10_000 + seed, blend, domain, PRETRAIN, eval_ticks, fresh=True)
                pt, _ = run_trial(10_000 + seed, blend, domain, PRETRAIN, eval_ticks, fresh=False)
                fresh_ticks.append(ft); pre_ticks.append(pt)
            diffs = [p - f for p, f in zip(pre_ticks, fresh_ticks)]
            m, p, d = paired_stats(diffs)
            sig = " ***" if p < 0.001 else " **" if p < 0.01 else " *" if p < 0.05 else "    "
            print(f"  {blend.name:<18} {statistics.mean(fresh_ticks):>7.3f} {statistics.mean(pre_ticks):>7.3f} "
                  f"{m:>+8.3f} {p:>9.4f}{sig} {d:>+7.3f}")
        print()


if __name__ == "__main__":
    main()
