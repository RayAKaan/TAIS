"""
TAIS Universal Substrate Benchmark (USB) - Level: Production Rigor.
Task: Relational Code Repair (RCR).
Problem: Detect and fix a logic error in a Binary Search implementation
         using real Python AST parsing and Multi-Head Attention.
"""

import ast
import random
import time
import numpy as np
from typing import Dict, List, Tuple, Any
from tais_core.mote import UniversalMote
from tais_core.reality import Entity, Relation, RealityGraph, Transformation, Consequence, WorldInterface
from tais_core.domains.registry import load_domain
from tais_core.domains.code_repair import CodeRepairWorld

BUGGY_SEARCH = """
def binary_search(arr, x):
    low = 0
    high = len(arr) - 1
    while low < high: # BUG: Should be <=
        mid = (high + low) // 2
        if arr[mid] < x: low = mid + 1
        elif arr[mid] > x: high = mid - 1
        else: return mid
    return -1
"""

CORRECT_SEARCH = BUGGY_SEARCH.replace("low < high", "low <= high")

def run_production_benchmark(seeds=50):
    print(f"=== TAIS PRODUCTION BENCHMARK: RELATIONAL CODE REPAIR ===")
    print(f"Target: Fix off-by-one bug in Binary Search AST")
    print(f"Scale: {seeds} independent trials\n")

    results = {"tais_transfer": [], "fresh_mote": []}

    for seed in range(seeds):
        # 1. TAIS with Multi-Source Pretraining
        random.seed(seed)
        mote_p = UniversalMote(energy=500)
        grid = load_domain("grid")
        rules = load_domain("rules")
        for t in range(15): mote_p.step(grid, grid.initial_graph(), mote_position="mote", tick=t)
        for t in range(15): mote_p.step(rules, rules.initial_graph(), mote_position="rule_ab", tick=t)

        world = CodeRepairWorld(BUGGY_SEARCH, CORRECT_SEARCH)
        g = world.initial_graph()
        reward_p = 0
        success_p = False
        for t in range(30):
            g, cons, _ = mote_p.step(world, g, mote_position="root", tick=t)
            reward_p += cons.net
            if cons.task_signal == "TASK_SUCCESS":
                success_p = True; break
        results["tais_transfer"].append({"reward": reward_p, "success": success_p, "tick": t})

        # 2. Fresh Mote (Control)
        random.seed(seed)
        mote_f = UniversalMote(energy=500)
        g = world.initial_graph()
        reward_f = 0
        success_f = False
        for t in range(30):
            g, cons, _ = mote_f.step(world, g, mote_position="root", tick=t)
            reward_f += cons.net
            if cons.task_signal == "TASK_SUCCESS":
                success_f = True; break
        results["fresh_mote"].append({"reward": reward_f, "success": success_f, "tick": t})

    def stats(key):
        data = results[key]
        rew = [r["reward"] for r in data]
        suc = sum(1 for r in data if r["success"])
        ticks = [r["tick"] for r in data if r["success"]]
        return np.mean(rew), (suc/seeds)*100, np.mean(ticks) if ticks else 0

    m_tais, s_tais, t_tais = stats("tais_transfer")
    m_fresh, s_fresh, t_fresh = stats("fresh_mote")

    print(f"{'Condition':<20} | {'Avg Reward':<12} | {'Success %':<10} | {'Avg Tick':<10}")
    print("-" * 65)
    print(f"{'TAIS (Pretrained)':<20} | {m_tais:<12.2f} | {s_tais:<10.1f} | {t_tais:<10.1f}")
    print(f"{'Fresh Mote':<20} | {m_fresh:<12.2f} | {s_fresh:<10.1f} | {t_fresh:<10.1f}")

if __name__ == "__main__":
    run_production_benchmark()
