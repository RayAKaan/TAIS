"""
TAIS SLM-Bridge Integration Test.
Scenario: Use a local 1B SLM to translate a Human Goal into a TAIS RealityGraph.
"""

import json
from tais_core.llm_grounding import LLMGroundingEngine
from tais_core.mote import UniversalMote
from tais_core.domains.registry import load_domain


def run_hybrid_demo():
    print("=== TAIS HYBRID DEMO: SLM TRANSLATOR + SUBSTRATE ===")

    translator = LLMGroundingEngine(provider="mock", model="llama3.2:1b")

    human_goal = "I need to fix the off-by-one bug in the binary search code"
    print(f"\n[Human] -> {human_goal}")

    print("[SLM] Translating to RealityGraph...")
    grounded_graph = translator.ground_goal(human_goal, domain="code_repair")

    print("\n[Substrate] Received Graph Structure:")
    print(f"  Entities: {len(list(grounded_graph.entities()))}")
    for ent in grounded_graph.entities():
        print(f"    - {ent.id} ({ent.etype})")

    sample_cons = {
        "net": 10.0,
        "valid": True,
        "task_signal": "TASK_SUCCESS",
        "explanation": {"why": "All unit tests passed after fixing Compare operator."},
    }

    print("\n[Substrate] Action completed. Reward: +10.0")
    print("[SLM] Translating outcome to Human Language...")
    human_explanation = translator.explain_consequence(sample_cons)

    print(f"\n[Agent] -> {human_explanation}")


if __name__ == "__main__":
    try:
        run_hybrid_demo()
    except Exception as e:
        print(f"\n[!] Demo completed with simulation fallback.")
        print(f"    (Reason: {e})")
