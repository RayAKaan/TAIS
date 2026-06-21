#!/usr/bin/env python3
"""Phase 1.5 diagnostic — instrument the PredictionEngine in RuleWorld.

The Phase 1 ablation found that removing prediction *helps* on
first_apply_implication_tick (delta = -2.61 ticks at h=12) while doubling
prediction error. That points at a calibration bug, not a missing feature.

This script logs, per tick, what each action's choose_action score actually
is, broken down into (predicted, historical, transfer, cost, risk). It runs
one trial each of fresh / full / no_prediction and prints a table.

Run:
    PYTHONPATH=. python3 experiments/predict_diagnostic.py
"""

from __future__ import annotations

import random
from typing import Dict, List

from tais_core.mote import UniversalMote
from tais_core.domains import RuleWorld, make_rule_graph
from tais_core.domains.gridworld import GridGraphWorld, make_grid_graph


def _scores_for(mote: UniversalMote, observation, actions) -> List[Dict[str, float]]:
    """Recompute the same components choose_action uses, without random tie-break."""
    transfer_boosts, _ = mote.memory.transfer_action_priors(observation, actions)
    local_exp = mote.domain_action_counts.get(observation.domain, 0)
    transfer_decay_rate = 0.08
    effective_analogy_weight = mote.meta.analogy_bias / (1.0 + transfer_decay_rate * local_exp)
    out = []
    for a in actions:
        predicted = mote.memory.predict_action(a, observation)
        historical = mote.memory.episodic.action_value(a.name)
        risk = mote.memory.episodic.action_risk(a.name)
        cost = a.compute_cost(observation, mote.state())
        transfer = effective_analogy_weight * transfer_boosts.get(a.name, 0.0)
        score = predicted + historical + transfer - cost - mote.meta.skepticism * risk
        out.append({
            "name": a.name,
            "predicted": predicted,
            "historical": historical,
            "transfer": transfer,
            "cost": cost,
            "risk_penalty": mote.meta.skepticism * risk,
            "score": score,
        })
    return out


def run_one(label: str, mote: UniversalMote, ticks: int = 12, pretrain: int = 20):
    random.seed(7)
    # Mixed-grid pretraining matching the ablation runner's "full" condition.
    gworld = GridGraphWorld()
    g = make_grid_graph(threat_near_resource=True)
    for t in range(pretrain):
        g = make_grid_graph(threat_near_resource=(t % 2 == 0))
        g, _, _ = mote.step(gworld, g, mote_position="mote", tick=t)
        if mote.energy <= 0:
            mote.energy = 50.0

    print(f"\n══════════════════ {label} ══════════════════")
    rworld = RuleWorld()
    rg = make_rule_graph()
    print(f"  tick | action            |  pred |  hist | trans |  cost |  risk |  score")
    print(f"  -----+-------------------+-------+-------+-------+-------+-------+--------")
    for i in range(ticks):
        obs = rworld.observe(rg, "rule_ab")
        actions = rworld.valid_actions(obs, mote.state())
        scores = _scores_for(mote, obs, actions)
        scores.sort(key=lambda s: -s["score"])
        chosen = scores[0]["name"]
        for j, s in enumerate(scores):
            marker = "*" if s["name"] == chosen else " "
            tag = f"t{i:02d}" if j == 0 else "   "
            print(f"   {tag} |{marker}{s['name']:<17} | {s['predicted']:+5.2f} | {s['historical']:+5.2f} | "
                  f"{s['transfer']:+5.2f} | {s['cost']:5.2f} | {s['risk_penalty']:5.2f} | {s['score']:+6.2f}")
        rg, cons, _ = mote.step(rworld, rg, mote_position="rule_ab", tick=pretrain + i)
        signal = cons.task_signal or "-"
        print(f"        | -> result        | net={cons.net:+5.2f} signal={signal}")
        if mote.energy <= 0:
            mote.energy = 50.0


def main():
    print("Phase 1.5 diagnostic: what does the PredictionEngine actually score per action?")
    print("Setup: mixed-Grid pretrain (20 ticks) -> RuleWorld eval (12 ticks). seed=7.")
    print("Same conditions as ablation v2 'full', single seed.")
    print()

    # full
    full_mote = UniversalMote(energy=100.0)
    run_one("FULL (prediction enabled)", full_mote)

    # no_prediction: monkeypatch predict_action to 0
    nop_mote = UniversalMote(energy=100.0)
    nop_mote.memory.predict_action = lambda a, g: 0.0
    run_one("NO_PREDICTION (predict_action -> 0)", nop_mote)

    # fresh-full (no pretrain)
    fresh_mote = UniversalMote(energy=100.0)
    print("\n══════════════════ FRESH (no pretrain, prediction enabled) ══════════════════")
    rworld = RuleWorld()
    rg = make_rule_graph()
    print(f"  tick | action            |  pred |  hist | trans |  cost |  risk |  score")
    print(f"  -----+-------------------+-------+-------+-------+-------+-------+--------")
    for i in range(12):
        obs = rworld.observe(rg, "rule_ab")
        actions = rworld.valid_actions(obs, fresh_mote.state())
        scores = _scores_for(fresh_mote, obs, actions)
        scores.sort(key=lambda s: -s["score"])
        chosen = scores[0]["name"]
        for j, s in enumerate(scores):
            marker = "*" if s["name"] == chosen else " "
            tag = f"t{i:02d}" if j == 0 else "   "
            print(f"   {tag} |{marker}{s['name']:<17} | {s['predicted']:+5.2f} | {s['historical']:+5.2f} | "
                  f"{s['transfer']:+5.2f} | {s['cost']:5.2f} | {s['risk_penalty']:5.2f} | {s['score']:+6.2f}")
        rg, cons, _ = fresh_mote.step(rworld, rg, mote_position="rule_ab", tick=i)
        signal = cons.task_signal or "-"
        print(f"        | -> result        | net={cons.net:+5.2f} signal={signal}")


if __name__ == "__main__":
    main()
