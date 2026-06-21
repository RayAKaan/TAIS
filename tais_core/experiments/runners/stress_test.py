"""
TAIS Stress Test Suite: From Easy to Extremely Hard.
Tests the limits of Grounded Role-Transfer Learning (GRTL) across increasing complexity.
"""

import random
import time
import json
from tais_core.mote import UniversalMote
from tais_core.reality import RealityGraph, Entity, Relation
from tais_core.domains.registry import load_domain
from tais_core.domains.gridworld import make_grid_graph
from tais_core.domains.rules import make_rule_graph
from tais_core.domains.codesynt import make_custom_code_graph
from tais_core.domains.sciex import make_sciex_graph
from tais_core.domains.negosim import make_negosim_graph


def pretrain_universal(mote, ticks=15):
    """Pretrains on all core domains to build a library of functional roles."""
    domains = ["grid", "rules", "codesynt"]
    for d_name in domains:
        world = load_domain(d_name)
        g = world.initial_graph() if hasattr(world, 'initial_graph') else None
        if not g:
            if d_name == "grid": g = make_grid_graph()
            elif d_name == "rules": g = make_rule_graph()
            elif d_name == "codesynt": g = make_custom_code_graph()

        pos = "mote" if d_name == "grid" else ("rule_ab" if d_name == "rules" else "root")
        for t in range(ticks):
            g, _, _ = mote.step(world, g, mote_position=pos, tick=t)


def run_stress_test():
    mote = UniversalMote(energy=500)
    pretrain_universal(mote)

    levels = [
        {"name": "EASY: Standard Web Navigation", "domain": "webnav", "ticks": 10, "pos": "nav"},
        {"name": "MEDIUM: AST Synthesis", "domain": "codesynt", "ticks": 20, "pos": "root"},
        {"name": "HARD: Scientific Design", "domain": "sciex", "ticks": 30, "pos": "hyp1"},
        {"name": "VERY HARD: Multi-Agent Negotiation", "domain": "negosim", "ticks": 40, "pos": "agent_0", "state": {"mote_id_str": "agent_0"}},
        {"name": "SUPER HARD: Noisy SciEx (Distractors)", "domain": "sciex", "ticks": 50, "pos": "hyp1", "noise": True},
        {"name": "EXTREMELY HARD: High-Pressure Market", "domain": "negosim", "ticks": 60, "pos": "agent_0", "state": {"mote_id_str": "agent_0"}, "pressure": True},
    ]

    print("=== TAIS EXTREME STRESS TEST ===\n")
    results = []

    for lvl in levels:
        print(f">>> Level: {lvl['name']}")
        world = load_domain(lvl['domain'])
        graph = world.initial_graph() if hasattr(world, 'initial_graph') else None

        if lvl.get("noise"):
            for i in range(20):
                graph.add_entity(Entity(f"noise_{i}", "DISTRACTOR", {"val": random.random()}))

        if lvl.get("pressure"):
            mote.energy = 50

        success = False
        start_time = time.time()
        solved_at = None

        for t in range(lvl['ticks']):
            graph, cons, action = mote.step(world, graph, mote_position=lvl['pos'], tick=t, extra_state=lvl.get("state"))
            if cons.task_signal == "TASK_SUCCESS":
                elapsed = time.time() - start_time
                solved_at = t
                print(f"  [SUCCESS] Solved at t={t} (Time: {elapsed:.3f}s)")
                success = True
                break

        if not success:
            print(f"  [FAILED] Goal not reached within {lvl['ticks']} ticks.")

        metrics = mote.metrics()
        precision = metrics.get("transfer_prior_precision", 0.0)
        print(f"  [Status] Energy: {metrics['energy']:.1f} | Patterns: {len(mote.memory.patterns)} | Precision: {precision*100:.1f}%")
        print()

        results.append({
            "level": lvl['name'],
            "success": success,
            "solved_at_tick": solved_at,
            "precision": round(precision, 4),
            "energy": metrics['energy'],
        })

        if not mote.alive:
            print("!!! MOTE DIED. Stress test terminated.\n")
            break

    print("=== Final Stress Test Report ===")
    final = mote.metrics()
    print(f"Domains Traversed: {len(final['domains'])}")
    print(f"Total Patterns Learned: {len(mote.memory.patterns)}")
    print(f"Final Survival Status: {'ALIVE' if mote.alive else 'DEAD'}")
    print(f"\nSummary Table:\n")
    print(f"{'Level':<45} {'Result':<12} {'Tick':<8} {'Precision':<10}")
    print("-"*75)
    for r in results:
        res = "SUCCESS" if r['success'] else "FAILED"
        tick = str(r['solved_at_tick']) if r['solved_at_tick'] is not None else "-"
        prec = f"{r['precision']*100:.1f}%"
        print(f"{r['level']:<45} {res:<12} {tick:<8} {prec:<10}")

    return results


if __name__ == "__main__":
    random.seed(99)
    run_stress_test()
