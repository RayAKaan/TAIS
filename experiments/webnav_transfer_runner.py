"""
GridWorld -> WebNav cross-domain transfer experiment.
"""

from __future__ import annotations

import json
import random
import statistics
from dataclasses import asdict, dataclass
from typing import List, Optional

from tais_core.mote import UniversalMote
from tais_core.domains.registry import load_domain
from tais_core.domains.gridworld import make_grid_graph
from tais_core.domains.webnav import make_webnav_graph


@dataclass
class TrialResult:
    seed: int
    condition: str
    total_reward: float
    invalid_actions: int
    actions_taken: int
    success: bool
    final_energy: float
    transfer_prior_uses: int
    transfer_prior_precision: float
    actions: List[str]


def pretrain_grid(mote: UniversalMote, ticks: int, seed: int):
    random.seed(seed)
    world = load_domain("grid")
    graph = make_grid_graph(threat_near_resource=True)
    for t in range(ticks):
        graph, _cons, _action = mote.step(world, graph, mote_position="mote", tick=t)
    return mote


def run_webnav_trial(mote: UniversalMote, ticks: int, seed: int, condition: str) -> TrialResult:
    random.seed(seed)
    world = load_domain("webnav")
    graph = make_webnav_graph()
    total_reward = 0.0
    actions: List[str] = []
    success = False
    for t in range(ticks):
        graph, cons, action = mote.step(world, graph, mote_position="nav", tick=t)
        total_reward += cons.net
        name = action.name if action else "NONE"
        actions.append(name)
        if cons.task_signal == "TASK_SUCCESS":
            success = True
    metrics = mote.metrics()
    return TrialResult(
        seed=seed,
        condition=condition,
        total_reward=round(total_reward, 4),
        invalid_actions=mote.invalid_actions,
        actions_taken=mote.actions_taken,
        success=success,
        final_energy=round(mote.energy, 4),
        transfer_prior_uses=metrics.get("transfer_prior_uses", 0),
        transfer_prior_precision=metrics.get("transfer_prior_precision", 0.0),
        actions=actions,
    )


def mean(xs):
    return statistics.mean(xs) if xs else 0.0


def summarize(results: List[TrialResult]) -> dict:
    return {
        "n": len(results),
        "mean_total_reward": mean([r.total_reward for r in results]),
        "success_rate": sum(1 for r in results if r.success) / len(results),
        "mean_invalid_actions": mean([r.invalid_actions for r in results]),
        "mean_transfer_prior_uses": mean([r.transfer_prior_uses for r in results]),
        "mean_transfer_prior_precision": mean([r.transfer_prior_precision for r in results]),
    }


def run_experiment(seeds=20, pretrain_ticks=20, webnav_ticks=20) -> dict:
    print(f"Running WebNav transfer experiment: {seeds} seeds...")
    fresh: List[TrialResult] = []
    pretrained: List[TrialResult] = []

    for seed in range(seeds):
        fresh_mote = UniversalMote(energy=100)
        fresh.append(run_webnav_trial(fresh_mote, webnav_ticks, seed=seed, condition="fresh"))

        pre_mote = UniversalMote(energy=100)
        pretrain_grid(pre_mote, pretrain_ticks, seed=seed + 1000)
        pretrained.append(run_webnav_trial(pre_mote, webnav_ticks, seed=seed, condition="pretrained"))

    summary = {
        "experiment": "grid_to_webnav_transfer",
        "seeds": seeds,
        "fresh": summarize(fresh),
        "pretrained": summarize(pretrained),
    }
    return summary


if __name__ == "__main__":
    result = run_experiment(seeds=30)
    print(json.dumps(result, indent=2))
