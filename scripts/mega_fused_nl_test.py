"""
TAIS Mega-Fused NL Stress Test.
4-Source Pretraining + Natural Language Goal Grounding.
"""

import random
import time
import json
from tais_core.mote import UniversalMote
from tais_core.domains.registry import load_domain
from tais_core.llm_grounding import LLMGroundingEngine
from tais_core.reality import Entity, Relation, RealityGraph


def pretrain_mega_fused(mote):
    print("[1/3] Executing 4-Source Mega-Fusion Pretraining...")
    domains = ["grid", "rules", "codesynt", "sciex"]
    pos_map = {"grid": "mote", "rules": "rule_ab",
               "codesynt": "root", "sciex": "hyp1"}
    for d in domains:
        world = load_domain(d)
        g = world.initial_graph()
        for t in range(15):
            g, _, _ = mote.step(world, g, mote_position=pos_map[d], tick=t)
    print(f"      Status: Patterns Learned={len(mote.memory.patterns)} "
          f"| Precision={mote.metrics()['transfer_prior_precision']*100:.1f}%")


def run_nl_discovery_challenge():
    print("\n=== TAIS MEGA-FUSED NL CHALLENGE ===")

    mote = UniversalMote(energy=1000)
    mote.enable_cognitive_engines(hierarchical_planning=True, causal_reasoning=True)
    pretrain_mega_fused(mote)

    translator = LLMGroundingEngine(provider="mock")
    human_command = "Initiate a scientific experiment to confirm the kinetics hypothesis in a noisy lab."
    print(f"\n[Human] -> {human_command}")

    print("[SLM] Grounding command into RealityGraph...")
    grounded_goal_graph = translator.ground_goal(human_command, domain="sciex")

    world = load_domain("sciex")
    graph = world.initial_graph()
    existing_ids = {e.id for e in graph.entities()}
    for e in grounded_goal_graph.entities():
        if e.id not in existing_ids:
            graph.add_entity(e)
            existing_ids.add(e.id)
    for r in grounded_goal_graph.relations():
        graph.add_relation(r)

    for i in range(20):
        graph.add_entity(Entity(f"noise_{i}", "NOISE",
                                {"entropy": random.random()}))

    print(f"[Substrate] lab_v1 initialized with "
          f"{len(list(graph.entities()))} entities (Goal Grounded).")

    success = False
    start_time = time.time()
    for t in range(500):
        graph, cons, action = mote.step(world, graph,
                                        mote_position="hyp1", tick=t)
        if cons.task_signal == "TASK_SUCCESS":
            print(f"\n>>> CHALLENGE SOLVED at t={t}!")
            success = True
            final_cons = cons
            break

    if not success:
        print(f"\n>>> Challenge FAILED (Horizon Exceeded, t={t}).")
        final_cons = cons

    print("\n[SLM] Narrating outcome...")
    explanation = translator.explain_consequence({
        "net": final_cons.net,
        "explanation": final_cons.explanation,
        "success": success,
    })
    print(f"[Agent] -> {explanation}")

    metrics = mote.metrics()
    print("\n=== Research Metrics ===")
    print(f"Fused Transfer Uses: {metrics['transfer_prior_uses']}")
    print(f"Final Precision: {metrics['transfer_prior_precision']*100:.1f}%")
    print(f"Patterns Accumulated: {len(mote.memory.patterns)}")


if __name__ == "__main__":
    random.seed(777)
    run_nl_discovery_challenge()
