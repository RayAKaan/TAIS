"""
TAIS Phase 1: Automatic Structure Discovery.
Task: Collect structural action signatures from GridWorld and RuleWorld 
without using hand-tagged roles.
"""

import json
import random
import numpy as np
from tais_core.mote import UniversalMote
from tais_core.domains.registry import load_domain
from tais_core.reality import Entity, Relation, RealityGraph


def get_structural_signature(consequence, action):
    """
    Extracts a domain-agnostic feature vector from an action consequence.
    Features are purely structural and numerical.
    """
    sig = {
        "net": consequence.net,
        "valid": 1.0 if consequence.valid else 0.0,
        "ent_added": 0,
        "ent_removed": 0,
        "ent_mod": 0,
        "rel_added": 0,
        "rel_removed": 0,
        "rel_mod": 0,
        "magnitude": 0,
    }

    if consequence.graph_delta:
        d = consequence.graph_delta
        sig["ent_added"] = len(d.entities_added)
        sig["ent_removed"] = len(d.entities_removed)
        sig["ent_mod"] = len(d.entities_modified)
        sig["rel_added"] = len(d.relations_added)
        sig["rel_removed"] = len(d.relations_removed)
        sig["rel_mod"] = len(d.relations_modified)
        sig["magnitude"] = d.magnitude

    return list(sig.values())


def collect_signatures(domain_name, seeds=20, ticks=50):
    print(f"Collecting signatures from {domain_name}...")
    world = load_domain(domain_name)
    all_data = []

    for seed in range(seeds):
        random.seed(seed)
        mote = UniversalMote()
        graph = world.initial_graph()
        pos = "mote" if domain_name == "grid" else "rule_ab"

        for t in range(ticks):
            mote_state = mote.state()
            obs = world.observe(graph, pos)
            actions = world.valid_actions(obs, mote_state)
            if not actions:
                break

            action = random.choice(actions)
            new_graph, cons = world.act(graph, action, mote_state)

            signature = get_structural_signature(cons, action)

            all_data.append({
                "domain": domain_name,
                "action": action.name,
                "role_hint": action.role_hint,
                "signature": signature,
            })

            graph = new_graph

    return all_data


if __name__ == "__main__":
    grid_sigs = collect_signatures("grid", seeds=30)
    rule_sigs = collect_signatures("rules", seeds=30)

    combined = grid_sigs + rule_sigs
    with open("structural_signatures.json", "w") as f:
        json.dump(combined, f, indent=2)
    print(f"Collected {len(combined)} total signatures. Saved to structural_signatures.json")
