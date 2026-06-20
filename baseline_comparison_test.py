"""
TAIS Phase 3: Strong Baseline Comparison.
Comparing TAIS (Grounded Transfer) vs. Tabular Q-Learning on PythonASTWorld.
"""

import random
import numpy as np
from tais_core.mote import UniversalMote
from tais_core.domains.python_ast import PythonASTWorld
from tais_core.baselines.tabular_q_agent import TabularQAgent
from tais_core.domains.registry import load_domain


def run_baseline_comparison(seeds=30, ticks=50):
    print(f"Running Baseline Comparison: TAIS vs Tabular Q-Learning "
          f"({seeds} seeds, {ticks} ticks)")

    results = {"tais": [], "q_learning": []}

    for seed in range(seeds):
        random.seed(seed)
        mote_tais = UniversalMote(energy=500)
        rules = load_domain("rules")
        rg = rules.initial_graph()
        for t in range(20):
            mote_tais.step(rules, rg, mote_position="rule_ab", tick=t)

        target_world = PythonASTWorld(source_code="z = 100")
        g = target_world.initial_graph()
        r_tais = 0
        for t in range(ticks):
            g, cons, _ = mote_tais.step(target_world, g,
                                         mote_position="root", tick=t)
            r_tais += cons.net
        results["tais"].append(r_tais)

        random.seed(seed)
        q_agent = TabularQAgent(seed=seed)
        g = target_world.initial_graph()
        r_q = 0
        for t in range(ticks):
            obs = target_world.observe(g, "root")
            actions = target_world.valid_actions(obs, {})
            action = q_agent.choose_action(target_world, obs, actions, {}, t)
            next_g, cons = target_world.act(g, action, {})
            q_agent.observe_outcome(target_world, obs, action,
                                    target_world.observe(next_g, "root"),
                                    cons, t)
            r_q += cons.net
            g = next_g
        results["q_learning"].append(r_q)

    avg_tais = np.mean(results["tais"])
    avg_q = np.mean(results["q_learning"])

    print(f"  TAIS Avg Reward:            {avg_tais:.2f}")
    print(f"  Q-Learning Avg Reward:      {avg_q:.2f}")
    delta = ((avg_tais - avg_q) / abs(avg_q if avg_q != 0 else 1)) * 100
    print(f"  TAIS vs Q-Learning Delta:   {delta:.1f}%")


if __name__ == "__main__":
    run_baseline_comparison()
