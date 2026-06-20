"""
Fused multi-source transfer experiment: Grid+Rules+Code+SciEx -> NegoSim.
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
from tais_core.domains.rules import make_rule_graph
from tais_core.domains.codesynt import make_codesynt_graph
from tais_core.domains.sciex import make_sciex_graph
from tais_core.domains.negosim import make_negosim_graph


@dataclass
class TrialResult:
    seed: int
    condition: str
    total_reward: float
    success: bool
    transfer_prior_uses: int
    transfer_prior_precision: float


def pretrain_mega_fused(mote: UniversalMote, ticks_per_domain: int, seed: int):
    random.seed(seed)

    # 1. Grid (Navigation/Safety)
    grid_world = load_domain("grid")
    grid_graph = make_grid_graph(threat_near_resource=True)
    for t in range(ticks_per_domain):
        grid_graph, _, _ = mote.step(grid_world, grid_graph, mote_position="mote", tick=t)

    # 2. Rules (Logic/Inference)
    rules_world = load_domain("rules")
    rules_graph = make_rule_graph()
    for t in range(ticks_per_domain):
        rules_graph, _, _ = mote.step(rules_world, rules_graph, mote_position="rule_ab", tick=t)

    # 3. CodeSynt (Synthesis/Structure)
    code_world = load_domain("codesynt")
    code_graph = make_codesynt_graph()
    for t in range(ticks_per_domain):
        code_graph, _, _ = mote.step(code_world, code_graph, mote_position="root", tick=t)

    # 4. SciEx (Experimental Design)
    sciex_world = load_domain("sciex")
    sciex_graph = make_sciex_graph()
    for t in range(ticks_per_domain):
        sciex_graph, _, _ = mote.step(sciex_world, sciex_graph, mote_position="hyp1", tick=t)

    return mote


def run_negosim_trial(mote: UniversalMote, ticks: int, seed: int, condition: str) -> TrialResult:
    random.seed(seed)
    world = load_domain("negosim")
    graph = make_negosim_graph(num_agents=2)
    total_reward = 0.0
    success = False

    for t in range(ticks):
        graph, cons, action = mote.step(world, graph, mote_position="agent_0", tick=t, extra_state={"mote_id_str": "agent_0"})
        total_reward += cons.net
        if cons.task_signal == "TASK_SUCCESS":
            success = True

    metrics = mote.metrics()
    return TrialResult(
        seed=seed,
        condition=condition,
        total_reward=round(total_reward, 4),
        success=success,
        transfer_prior_uses=metrics.get("transfer_prior_uses", 0),
        transfer_prior_precision=metrics.get("transfer_prior_precision", 0.0),
    )


def mean(xs):
    return statistics.mean(xs) if xs else 0.0


def summarize(results: List[TrialResult]) -> dict:
    return {
        "n": len(results),
        "mean_total_reward": mean([r.total_reward for r in results]),
        "success_rate": sum(1 for r in results if r.success) / len(results),
        "mean_transfer_prior_uses": mean([r.transfer_prior_uses for r in results]),
        "mean_transfer_prior_precision": mean([r.transfer_prior_precision for r in results]),
    }


def run_experiment(seeds=20, pretrain_ticks=15, nego_ticks=25) -> dict:
    print(f"Running Mega-Fused NegoSim transfer experiment: {seeds} seeds...")
    fresh: List[TrialResult] = []
    pretrained: List[TrialResult] = []

    for seed in range(seeds):
        fresh_mote = UniversalMote(energy=100)
        fresh.append(run_negosim_trial(fresh_mote, nego_ticks, seed=seed, condition="fresh"))

        pre_mote = UniversalMote(energy=100)
        pretrain_mega_fused(pre_mote, pretrain_ticks, seed=seed + 4000)
        pretrained.append(run_negosim_trial(pre_mote, nego_ticks, seed=seed, condition="mega_fused_pretrained"))

    summary = {
        "experiment": "mega_fused_to_negosim_transfer",
        "seeds": seeds,
        "fresh": summarize(fresh),
        "mega_fused_pretrained": summarize(pretrained),
    }
    return summary


if __name__ == "__main__":
    result = run_experiment(seeds=30)
    print(json.dumps(result, indent=2))
