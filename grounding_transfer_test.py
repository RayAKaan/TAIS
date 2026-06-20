"""
TAIS Phase 2 Validation: Grounding Transfer.
Transfer from abstract RuleWorld to real Python AST.
"""

import json
import random
import numpy as np
from tais_core.mote import UniversalMote
from tais_core.domains.registry import load_domain
from tais_core.domains.rules import make_rule_graph
from tais_core.domains.python_ast import PythonASTWorld


def run_grounding_transfer(seeds=30):
    print(f"Running RuleWorld -> PythonAST Transfer: {seeds} seeds")

    results = {"fresh": [], "pretrained": []}

    for seed in range(seeds):
        random.seed(seed)
        mote_f = UniversalMote(energy=100)
        world = PythonASTWorld(source_code="y = 42")
        g = world.initial_graph()
        reward_f = 0
        for t in range(15):
            g, cons, _ = mote_f.step(world, g, mote_position="root", tick=t)
            reward_f += cons.net
        results["fresh"].append(reward_f)

        random.seed(seed)
        mote_p = UniversalMote(energy=100)
        rules = load_domain("rules")
        rg = make_rule_graph()
        for t in range(20):
            mote_p.step(rules, rg, mote_position="rule_ab", tick=t)

        world = PythonASTWorld(source_code="y = 42")
        g = world.initial_graph()
        reward_p = 0
        for t in range(15):
            g, cons, _ = mote_p.step(world, g, mote_position="root", tick=t)
            reward_p += cons.net
        results["pretrained"].append(reward_p)

    avg_f = np.mean(results["fresh"])
    avg_p = np.mean(results["pretrained"])
    print(f"  Fresh Avg Reward:       {avg_f:.2f}")
    print(f"  Pretrained Avg Reward:  {avg_p:.2f}")
    delta = ((avg_p - avg_f) / abs(avg_f if avg_f != 0 else 1)) * 100
    print(f"  Transfer Delta:         {delta:.1f}%")


if __name__ == "__main__":
    run_grounding_transfer()
