"""
Cross-domain transfer experiment for TAIS core.

Question:
    Does GridWorld pretraining improve RuleWorld learning vs fresh motes?

This is intentionally an experiment, not a unit test. It is allowed to fail.
A failure means the architecture has not yet demonstrated cross-domain transfer
performance, even if the graph analogy mechanism exists.

Run:
    PYTHONPATH=. python3 experiments_cross_domain_transfer.py
"""

from __future__ import annotations

import json
import random
import statistics
from dataclasses import asdict, dataclass
from typing import List, Optional

from tais_core.mote import UniversalMote
from tais_core.domains import GridGraphWorld, RuleWorld, make_grid_graph, make_rule_graph


@dataclass
class TrialResult:
    seed: int
    condition: str
    total_reward: float
    invalid_actions: int
    actions_taken: int
    first_apply_tick: Optional[int]
    final_energy: float
    mean_prediction_error: Optional[float]
    transfer_prior_uses: int
    transfer_prior_total_strength: float
    transfer_prior_correct: int
    transfer_prior_incorrect: int
    transfer_prior_precision: float
    actions: List[str]


def pretrain_grid(mote: UniversalMote, ticks: int, seed: int, mixed: bool = False):
    random.seed(seed)
    world = GridGraphWorld()
    graph = make_grid_graph(threat_near_resource=True)
    for t in range(ticks):
        # Mixed curriculum exposes both AVOID_BAD and APPROACH_GOOD roles.
        if mixed:
            graph = make_grid_graph(threat_near_resource=(t % 2 == 0))
        graph, _cons, _action = mote.step(world, graph, mote_position="mote", tick=t)
    return mote


def run_rule_trial(mote: UniversalMote, ticks: int, seed: int, condition: str) -> TrialResult:
    random.seed(seed)
    world = RuleWorld()
    graph = make_rule_graph()
    total_reward = 0.0
    actions: List[str] = []
    first_apply_tick = None
    for t in range(ticks):
        graph, cons, action = mote.step(world, graph, mote_position="rule_ab", tick=t)
        total_reward += cons.net
        name = action.name if action else "NONE"
        actions.append(name)
        if name == "apply_implication" and first_apply_tick is None:
            first_apply_tick = t
    metrics = mote.metrics()
    return TrialResult(
        seed=seed,
        condition=condition,
        total_reward=round(total_reward, 4),
        invalid_actions=mote.invalid_actions,
        actions_taken=mote.actions_taken,
        first_apply_tick=first_apply_tick,
        final_energy=round(mote.energy, 4),
        mean_prediction_error=metrics["mean_prediction_error"],
        transfer_prior_uses=metrics.get("transfer_prior_uses", 0),
        transfer_prior_total_strength=metrics.get("transfer_prior_total_strength", 0.0),
        transfer_prior_correct=metrics.get("transfer_prior_correct", 0),
        transfer_prior_incorrect=metrics.get("transfer_prior_incorrect", 0),
        transfer_prior_precision=metrics.get("transfer_prior_precision", 0.0),
        actions=actions,
    )


def mean(xs):
    return statistics.mean(xs) if xs else None


def summarize(results: List[TrialResult]) -> dict:
    return {
        "n": len(results),
        "mean_total_reward": mean([r.total_reward for r in results]),
        "mean_invalid_actions": mean([r.invalid_actions for r in results]),
        "mean_first_apply_tick": mean([r.first_apply_tick for r in results if r.first_apply_tick is not None]),
        "never_applied": sum(1 for r in results if r.first_apply_tick is None),
        "mean_final_energy": mean([r.final_energy for r in results]),
        "mean_prediction_error": mean([r.mean_prediction_error for r in results if r.mean_prediction_error is not None]),
        "mean_transfer_prior_uses": mean([r.transfer_prior_uses for r in results]),
        "mean_transfer_prior_strength": mean([r.transfer_prior_total_strength for r in results]),
        "mean_transfer_prior_correct": mean([r.transfer_prior_correct for r in results]),
        "mean_transfer_prior_incorrect": mean([r.transfer_prior_incorrect for r in results]),
        "mean_transfer_prior_precision": mean([r.transfer_prior_precision for r in results]),
    }


def run_experiment(seeds=50, pretrain_ticks=20, rule_ticks=12, mixed_pretraining: bool = False) -> dict:
    fresh: List[TrialResult] = []
    pretrained: List[TrialResult] = []

    for seed in range(seeds):
        fresh_mote = UniversalMote(energy=100)
        fresh.append(run_rule_trial(fresh_mote, rule_ticks, seed=10_000 + seed, condition="fresh"))

        pre_mote = UniversalMote(energy=100)
        pretrain_grid(pre_mote, pretrain_ticks, seed=20_000 + seed, mixed=mixed_pretraining)
        condition = "grid_mixed_pretrained" if mixed_pretraining else "grid_pretrained"
        pretrained.append(run_rule_trial(pre_mote, rule_ticks, seed=10_000 + seed, condition=condition))

    summary = {
        "experiment": "grid_pretraining_to_ruleworld",
        "seeds": seeds,
        "pretrain_ticks": pretrain_ticks,
        "rule_ticks": rule_ticks,
        "mixed_pretraining": mixed_pretraining,
        "fresh": summarize(fresh),
        "grid_pretrained": summarize(pretrained),
        "deltas_pretrained_minus_fresh": {},
        "interpretation": "",
        "trials": [asdict(r) for r in fresh + pretrained],
    }
    for key in ["mean_total_reward", "mean_final_energy"]:
        summary["deltas_pretrained_minus_fresh"][key] = summary["grid_pretrained"][key] - summary["fresh"][key]
    for key in ["mean_invalid_actions", "mean_first_apply_tick", "mean_prediction_error", "mean_transfer_prior_uses", "mean_transfer_prior_strength", "mean_transfer_prior_correct", "mean_transfer_prior_incorrect", "mean_transfer_prior_precision"]:
        a = summary["grid_pretrained"][key]
        b = summary["fresh"][key]
        summary["deltas_pretrained_minus_fresh"][key] = None if a is None or b is None else a - b

    reward_delta = summary["deltas_pretrained_minus_fresh"]["mean_total_reward"]
    first_apply_delta = summary["deltas_pretrained_minus_fresh"]["mean_first_apply_tick"]
    invalid_delta = summary["deltas_pretrained_minus_fresh"]["mean_invalid_actions"]

    if reward_delta > 0 and (first_apply_delta is None or first_apply_delta < 0) and invalid_delta <= 0:
        interp = "PASS: grid pretraining improved RuleWorld reward and did not increase invalid actions."
    elif reward_delta > 0:
        interp = "MIXED: grid pretraining improved reward but other metrics are not clearly better."
    else:
        interp = "FAIL/INCONCLUSIVE: grid pretraining did not improve RuleWorld reward."
    summary["interpretation"] = interp
    return summary


if __name__ == "__main__":
    result = run_experiment(seeds=50, pretrain_ticks=20, rule_ticks=12)
    print(json.dumps({k: v for k, v in result.items() if k != "trials"}, indent=2))
    with open("cross_domain_transfer_results.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print("saved → cross_domain_transfer_results.json")
