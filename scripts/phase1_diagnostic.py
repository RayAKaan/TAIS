"""
TAIS Phase 1 Diagnostic: Role-Compatibility Ablation Tracing.

Used to produce the trace numbers cited in ``docs/PHASE1_VALIDATION_REPORT.md``.
Compares three role-compatibility modes (none/manual/discovered) on a
GridWorld -> RuleWorld 20+15 tick task, collecting per-action boost
statistics, call counts, hit rates, and action distributions.

Run:
    python scripts/phase1_diagnostic.py
"""

import json
import random
import numpy as np
from collections import defaultdict, Counter
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


def make_wrapped_role_compatibility(inner_fn, stats):
    def wrapped(source_role, target_role, **kwargs):
        stats["calls"] += 1
        result = inner_fn(source_role, target_role, **kwargs)
        if result > 0:
            stats["hits"] += 1
        stats["results"].append(result)
        return result
    return wrapped


def run_experiment(mode="manual", seeds=20):
    print(f"  {mode}: {seeds} seeds...")

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
        base_fn = patched_discovered
    elif mode == "none":
        base_fn = patched_none
    else:
        base_fn = orig_fn

    stats = {"calls": 0, "hits": 0, "results": []}
    memory.role_compatibility = make_wrapped_role_compatibility(base_fn, stats)

    all_rewards = []
    all_precisions = []
    all_uses = []
    action_counter = Counter()
    per_seed_boost_mag = []

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
            rg, cons, action = mote.step(rules, rg, mote_position="rule_ab", tick=t)
            total_r += cons.net
            if action:
                action_counter[action.name] += 1

        per_seed_boost_mag.append(abs(getattr(mote, '_last_chosen_transfer_boost', 0.0)))
        metrics = mote.metrics()
        all_rewards.append(total_r)
        all_precisions.append(metrics.get("transfer_prior_precision", 0.0))
        all_uses.append(metrics.get("transfer_prior_uses", 0))

    memory.role_compatibility = orig_fn

    return {
        "reward_mean": float(np.mean(all_rewards)),
        "reward_std": float(np.std(all_rewards)),
        "precision_mean": float(np.mean(all_precisions)),
        "precision_std": float(np.std(all_precisions)),
        "transfer_uses_mean": float(np.mean(all_uses)),
        "transfer_uses_std": float(np.std(all_uses)),
        "boost_mag_mean": float(np.mean(per_seed_boost_mag)),
        "boost_mag_nonzero_pct": float(np.mean([1 for m in per_seed_boost_mag if m > 1e-9])) * 100,
        "role_compat_calls": stats["calls"],
        "role_compat_hits": stats["hits"],
        "role_compat_mean_result": float(np.mean(stats["results"])) if stats["results"] else 0.0,
        "top_actions": action_counter.most_common(5),
    }


if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 1 DIAGNOSTIC: Role Compatibility Mode Ablation")
    print("=" * 60)

    results = {}
    for mode in ["none", "manual", "discovered"]:
        results[mode] = run_experiment(mode=mode, seeds=20)

    print("\n" + "=" * 80)
    print(f"{'Metric':<35} | {'none':<14} | {'manual':<14} | {'discovered':<14}")
    print("-" * 80)
    for key in ["reward_mean", "reward_std", "precision_mean", "transfer_uses_mean",
                "boost_mag_mean", "boost_mag_nonzero_pct", "role_compat_calls",
                "role_compat_hits", "role_compat_mean_result"]:
        vals = [f"{results[m][key]:<14.4f}" for m in ["none", "manual", "discovered"]]
        print(f"{key:<35} | {vals[0]} | {vals[1]} | {vals[2]}")

    print("\n--- Top 5 Actions (count across all seeds) ---")
    for mode in ["none", "manual", "discovered"]:
        print(f"\n  {mode}:")
        for action, count in results[mode]["top_actions"]:
            print(f"    {action}: {count}")
