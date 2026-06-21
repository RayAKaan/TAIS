"""
TAIS Bar 2: Phase 1 Validation.
Ablation study comparing Human Role-Hints vs. Autonomous Structure Discovery.
"""

import json
import random
import numpy as np
from tais_core.mote import UniversalMote
from tais_core.domains.registry import load_domain
from tais_core.domains.gridworld import make_grid_graph
from tais_core.domains.rules import make_rule_graph
from tais_core import memory

try:
    with open("discovered_role_mapping.json", "r") as f:
        DISCOVERED = json.load(f)
except Exception:
    DISCOVERED = {}


def run_experiment(mode="manual", seeds=50):
    print(f"Running Validation Mode: {mode} ({seeds} seeds)")

    orig_fn = memory.role_compatibility

    def patched_discovered(
        source_role, target_role,
        source_domain="", target_domain="",
        source_action="", target_action="",
    ):
        s_key = f"{source_domain}:{source_action}"
        t_key = f"{target_domain}:{target_action}"
        if s_key in DISCOVERED and t_key in DISCOVERED:
            return 1.0 if DISCOVERED[s_key] == DISCOVERED[t_key] else 0.0
        return 0.0

    def patched_none(source_role, target_role, **kwargs):
        return 1.0 if source_role == target_role else 0.0

    if mode == "discovered":
        memory.role_compatibility = patched_discovered
    elif mode == "none":
        memory.role_compatibility = patched_none
    else:
        memory.role_compatibility = orig_fn

    rewards = []
    precision = []

    for seed in range(seeds):
        random.seed(seed)
        mote = UniversalMote(energy=100)
        grid = load_domain("grid")
        rules = load_domain("rules")

        g = make_grid_graph()
        for t in range(20):
            mote.step(grid, g, mote_position="mote", tick=t)

        rg = make_rule_graph()
        total_r = 0
        for t in range(15):
            rg, cons, _ = mote.step(rules, rg, mote_position="rule_ab", tick=t)
            total_r += cons.net

        metrics = mote.metrics()
        rewards.append(total_r)
        precision.append(metrics.get("transfer_prior_precision", 0.0))

    memory.role_compatibility = orig_fn

    return np.mean(rewards), np.mean(precision)


if __name__ == "__main__":
    results = {}
    for mode in ["none", "manual", "discovered"]:
        r, p = run_experiment(mode=mode, seeds=100)
        results[mode] = {"reward": r, "precision": p}

    print("\n" + "=" * 40)
    print("PHASE 1: ROLE DISCOVERY VALIDATION")
    print("=" * 40)
    print(f"{'Mode':<15} | {'Reward':<10} | {'Precision':<10}")
    print("-" * 40)
    for mode, data in results.items():
        print(f"{mode:<15} | {data['reward']:<10.2f} | {data['precision']*100:<10.1f}%")
