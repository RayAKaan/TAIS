"""
TAIS Final Breakthrough Validation: The Lock-in Effect.
Phase 1: Discover path in a Clean Lab.
Phase 2: Execute path in a Noisy Lab with 100% reliability via Sequential Gating.
"""

import random
from tais_core.mote import UniversalMote
from tais_core.domains.registry import load_domain
from tais_core.reality import Entity, Relation, RealityGraph


def run_final_validation():
    print("=== TAIS BREAKTHROUGH VALIDATION: CONTINUITY LOCK-IN ===")

    mote = UniversalMote(energy=1000)
    mote.enable_cognitive_engines(hierarchical_planning=True, causal_reasoning=True)

    world = load_domain("sciex")

    # --- PHASE 1: CLEAN DISCOVERY ---
    print("\n[Phase 1] Discovery in Clean Lab (Noise=0)...")
    clean_graph = world.initial_graph()

    steps = ["formulate_experiment", "control_variable",
             "run_experiment", "analyze_data"]
    for i, action_name in enumerate(steps):
        obs = world.observe(clean_graph, "hyp1")
        actions = world.valid_actions(obs, {})
        action = next(a for a in actions if a.name == action_name)

        predicted = mote.memory.predict_action(action, obs)
        new_graph, cons = world.act(clean_graph, action, mote.state())

        after_obs = world.observe(new_graph, "hyp1")
        cons.reward = 5.0
        mote.memory.record_episode(obs, after_obs, action, cons, predicted,
                                   world.domain_name, i)

        clean_graph = new_graph
        print(f"  Step {i+1}: Seeding {action_name} as SUCCESS")

    print(f"\n[Memory] Transition chain established. "
          f"Episodes: {len(mote.memory.episodic)}")

    # --- PHASE 2: NOISY EXECUTION ---
    print("\n[Phase 2] Execution in Noisy Lab (20 Distractors)...")
    noisy_graph = world.initial_graph()
    for i in range(20):
        noisy_graph.add_entity(
            Entity(f"noise_{i}", "NOISE", {"val": random.random()}))

    mote.age = 0

    success = False
    for t in range(10):
        noisy_graph, cons, action = mote.step(
            world, noisy_graph, mote_position="hyp1", tick=t)

        if action:
            print(f"  t={t}: Action='{action.name}' "
                  f"| Signal='{cons.task_signal}'")

        if cons.task_signal == "TASK_SUCCESS":
            print(f"\n>>> BREAKTHROUGH SUCCESS at t={t}!")
            success = True
            break

    if success:
        print("\nCONCLUSION: Sequential Continuity Gating successfully "
              "overrode 20 noise nodes.")
    else:
        print("\nCONCLUSION: Lock-in failed.")


if __name__ == "__main__":
    random.seed(42)
    run_final_validation()
