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
        if "deep" in nl_goal.lower():
            g.add_entity(Entity("goal", "GOAL", {"target_id": "secret_btn", "satisfied": False}))
            g.add_entity(Entity("secret_btn", "ELEMENT", {"role": "submit"}))
            g.add_relation(Relation("goal", "TARGETS", "secret_btn"))
        return g
