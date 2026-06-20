"""
TAIS Real-World Capability Test: System vs. Real-World AI Tasks.
Tests whether TAIS can solve structured problems analogous to LLM/Agent use cases.
1. Multi-Step Data Extraction (Web)
2. Dependency-Aware Refactoring (Code)
3. Reproducibility Verification (Science)
"""

import random
from tais_core.mote import UniversalMote
from tais_core.domains.registry import load_domain
from tais_core.reality import Entity, Relation, RealityGraph

def setup_realworld_mote():
    mote = UniversalMote(energy=500)
    for d in ["grid", "rules", "codesynt"]:
        world = load_domain(d)
        g = world.initial_graph()
        pos = "mote" if d == "grid" else ("rule_ab" if d == "rules" else "root")
        for t in range(10):
            mote.step(world, g, mote_position=pos, tick=t)
    return mote

def test_data_extraction_agent():
    print("\n[Task 1] Web Agent: Deep Data Extraction")
    print("Scenario: Navigate multi-page structure to find a specific hidden value.")
    mote = setup_realworld_mote()
    world = load_domain("webnav")

    g = world.initial_graph()
    g.add_entity(Entity("page3", "PAGE", {"title": "Deep Data"}))
    g.add_entity(Entity("link_to_deep", "ELEMENT", {"role": "link", "text": "Next"}))
    g.add_relation(Relation("page2", "CONTAINS", "link_to_deep"))
    g.add_relation(Relation("link_to_deep", "LINKS_TO", "page3"))

    success = False
    for t in range(100):
        g, cons, action = mote.step(world, g, mote_position="nav", tick=t)
        if cons.task_signal == "TASK_SUCCESS":
            success = True
            print(f"  Result: SUCCESS (t={t}) - Agent successfully navigated deep tree.")
            break
    if not success:
        print("  Result: FAILED - Agent lost in navigation.")

def test_coding_refactor_agent():
    print("\n[Task 2] Coding Agent: Multi-Step Refactor")
    print("Scenario: Must add variables AND operations before running tests will pass.")
    mote = setup_realworld_mote()
    world = load_domain("codesynt")
    g = world.initial_graph()

    success = False
    actions_taken = []
    for t in range(100):
        g, cons, action = mote.step(world, g, mote_position="root", tick=t)
        if action:
            actions_taken.append(action.name)
        if cons.task_signal == "TASK_SUCCESS":
            success = True
            print(f"  Result: SUCCESS (t={t}) - Agent sequenced {actions_taken.count('add_variable')} vars and {actions_taken.count('add_operation')} ops.")
            break
    if not success:
        print(f"  Result: FAILED - Actions: {set(actions_taken)}")

def test_scientific_verification_agent():
    print("\n[Task 3] Science Agent: Reproducibility Check")
    print("Scenario: Identify if an experiment is 'uncontrolled' and fix it before running.")
    mote = setup_realworld_mote()
    world = load_domain("sciex")
    g = world.initial_graph()

    success = False
    for t in range(100):
        g, cons, action = mote.step(world, g, mote_position="hyp1", tick=t)
        if cons.task_signal == "TASK_SUCCESS":
            success = True
            print(f"  Result: SUCCESS (t={t}) - Scientific hypothesis confirmed.")
            break
    if not success:
        print("  Result: FAILED - Horizon exceeded.")

if __name__ == "__main__":
    random.seed(42)
    print("=== TAIS REAL-WORLD CAPABILITY TEST ===")
    test_data_extraction_agent()
    test_coding_refactor_agent()
    test_scientific_verification_agent()
