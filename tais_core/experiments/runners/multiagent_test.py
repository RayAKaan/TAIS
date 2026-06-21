"""
Verification of Multi-Agent Collaboration.
Challenge: Two agents must communicate and trade to achieve mutual goals.
"""

import random
from tais_core.mote import UniversalMote
from tais_core.domains.registry import load_domain
from tais_core.domains.negosim import make_negosim_graph

def run_multi_agent_market():
    print("\n[Challenge] Multi-Agent Collaborative Market")
    world = load_domain("negosim")
    graph = make_negosim_graph(num_agents=2)

    agent_a = UniversalMote(energy=200)
    agent_b = UniversalMote(energy=200)

    for t in range(50):
        graph, cons_a, _ = agent_a.step(world, graph, mote_position="agent_0", tick=t, extra_state={"mote_id_str": "agent_0"})
        graph, cons_b, _ = agent_b.step(world, graph, mote_position="agent_1", tick=t, extra_state={"mote_id_str": "agent_1"})

        goals = [e for e in graph.entities("GOAL") if e.get("satisfied")]
        if len(goals) >= 2:
            print(f"  Result: SUCCESS (t={t}) - Both agents achieved mutual trade.")
            return True

    print("  Result: FAILED - Market stagnation.")
    return False

if __name__ == "__main__":
    random.seed(42)
    run_multi_agent_market()
