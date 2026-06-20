import requests
import json
from typing import Any, Dict, List, Optional
from .reality import Entity, RealityGraph, Relation


class LLMGroundingEngine:
    """
    Perception/Translation layer that converts Natural Language to RealityGraphs
    using a local SLM (e.g., Llama-3.2-1B via Ollama).
    """

    def __init__(self, provider: str = "ollama", model: str = "llama3.2:1b"):
        self.provider = provider
        self.model = model
        self.url = "http://localhost:11434/api/generate"

    def ground_goal(self, nl_goal: str, domain: str = "webnav") -> RealityGraph:
        """Converts a natural language goal into a RealityGraph using the SLM."""
        if self.provider == "mock":
            return self._mock_ground_goal(nl_goal, domain)

        prompt = f"""
        TASK: Convert the user's natural language goal into a structured TAIS RealityGraph.
        DOMAIN: {domain}
        USER GOAL: "{nl_goal}"

        FORMAT: Output valid JSON only.
        JSON SCHEMA:
        {{
          "entities": [{{"id": "string", "type": "string", "properties": {{}} }}],
          "relations": [{{"source": "string", "type": "string", "target": "string"}}]
        }}

        EXAMPLES:
        "Find the submit button" -> {{"entities": [{{"id": "goal", "type": "GOAL", "properties": {{"target": "btn"}}}}], "relations": []}}

        JSON OUTPUT:
        """

        try:
            response = requests.post(self.url, json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            }, timeout=10)

            data = response.json()
            graph_data = json.loads(data["response"])

            g = RealityGraph(domain, "grounded_from_nl")
            for ent in graph_data.get("entities", []):
                g.add_entity(Entity(ent["id"], ent["type"], ent.get("properties", {})))
            for rel in graph_data.get("relations", []):
                g.add_relation(Relation(rel["source"], rel["type"], rel["target"]))

            return g
        except Exception as e:
            print(f">> LLMGrounding: SLM failed ({e}). Falling back to mock.")
            return self._mock_ground_goal(nl_goal, domain)

    def explain_consequence(self, consequence_dict: Dict[str, Any]) -> str:
        """Converts a TAIS Consequence object into human-readable Natural Language."""
        if self.provider == "mock":
            net = consequence_dict.get("net", 0)
            why = consequence_dict.get("explanation", {}).get("why",
                  consequence_dict.get("why", "Unknown"))
            success = consequence_dict.get("success", False)
            if success:
                return f"I successfully completed the task: {why}"
            return f"Action resulted in net reward of {net}. Reason: {why}"

        prompt = f"""
        TASK: You are a narrator for an AI agent. Explain the following outcome in one simple, natural sentence.
        OUTCOME DATA: {json.dumps(consequence_dict)}

        EXPLANATION:
        """

        try:
            response = requests.post(self.url, json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            }, timeout=5)
            return response.json()["response"].strip()
        except Exception:
            return f"Action resulted in net reward of {consequence_dict.get('net', 0)}."

    def _mock_ground_goal(self, nl_goal: str, domain: str) -> RealityGraph:
        g = RealityGraph(domain, "grounded_goal")
        g.add_entity(Entity("nav", "NAVIGATION", {"depth": 0}))

        nl_lower = nl_goal.lower()

        if "deep" in nl_lower:
            g.add_entity(Entity("goal", "GOAL", {"target_id": "secret_btn", "satisfied": False}))
            g.add_entity(Entity("secret_btn", "ELEMENT", {"role": "submit"}))
            g.add_relation(Relation("goal", "TARGETS", "secret_btn"))

        elif "fix" in nl_lower or "bug" in nl_lower:
            g.add_entity(Entity("goal", "GOAL", {"target_id": "test_suite", "status": "failing"}))
            g.add_entity(Entity("test_suite", "REQUIREMENT", {"target": "BinarySearch"}))
            g.add_relation(Relation("goal", "TARGETS", "test_suite"))

        elif "experiment" in nl_lower or "science" in nl_lower:
            g.add_entity(Entity("goal", "GOAL", {"target_id": "hyp1", "satisfied": False}))
            g.add_entity(Entity("hyp1", "HYPOTHESIS", {"confirmed": False}))
            g.add_relation(Relation("goal", "TARGETS", "hyp1"))

        elif "market" in nl_lower or "trade" in nl_lower:
            g.add_entity(Entity("goal", "GOAL", {"target_id": "agent_0", "satisfied": False}))
            g.add_relation(Relation("goal", "TARGETS", "agent_0"))

        return g
