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
        TASK: STRICT TRANSLATOR. Convert human intent into TAIS RealityGraph JSON.
        RULES: 
        1. DO NOT CONVERSE. 
        2. DO NOT REPLY TO THE USER. 
        3. If the input is a greeting or non-task, return an empty entities list.
        4. OUTPUT VALID JSON ONLY.

        DOMAIN: {domain}
        USER INPUT: "{nl_goal}"

        JSON SCHEMA:
        {{
          "entities": [{{ "id": "string", "type": "string", "properties": {{}} }}],
          "relations": [{{ "source": "string", "type": "string", "target": "string" }}]
        }}

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
        """Converts a TAIS Consequence object into a descriptive summary including graph changes."""
        if self.provider == "mock":
            return self._mock_explain_consequence(consequence_dict)

        prompt = f"""
        TASK: SUBSTRATE NARRATOR. Summarize the agent's action and the physical change to the graph.
        RULES:
        1. If entities were modified, state what property changed.
        2. If a goal was reached, announce the SUCCESS.
        3. Be technical and precise.

        OUTCOME DATA: {json.dumps(consequence_dict)}

        EXPLANATION:
        """

        try:
            response = requests.post(self.url, json={
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }, timeout=5)
            return response.json()["response"].strip()
        except:
            return self._mock_explain_consequence(consequence_dict)

    def _mock_explain_consequence(self, d: Dict[str, Any]) -> str:
        action = d.get("action", "unknown")
        net = d.get("net", 0)
        success = d.get("success", False)
        delta = d.get("delta", {})

        if success:
            modified = delta.get("modified", [])
            added = delta.get("added", [])
            parts = []
            if modified:
                for m in modified:
                    c = m.get("changes", {})
                    if c:
                        k, v = list(c.items())[0]
                        parts.append(f"modified '{m['id']}' {k} to {v}")
                    else:
                        parts.append(f"modified '{m['id']}'")
            if added:
                parts.append(f"added {', '.join(added)}")
            delta_str = "; " + "; ".join(parts) if parts else ""
            return f"The agent successfully completed the task via {action}, yielding a net reward of {net}.{delta_str}"

        descriptions = {
            "fix_operator": "modified the comparison operator from < to <=, correcting the off-by-one logic error",
            "refactor": "reorganized the AST node structure to improve code clarity and maintainability",
            "type_check": "type-checked the module structure to ensure referential integrity across the AST",
            "run_tests": "executed the unit test suite against the current implementation",
            "add_variable": "initialized a new variable declaration to satisfy the module requirements",
            "define_function": "defined a new function signature within the active scope",
        }
        desc = descriptions.get(action, f"applied {action} to the substrate graph")
        delta_str = ""
        if delta:
            modified = delta.get("modified", [])
            added = delta.get("added", [])
            parts = []
            if modified:
                for m in modified:
                    c = m.get("changes", {})
                    if c:
                        k, v = list(c.items())[0]
                        parts.append(f"modified '{m['id']}' {k} to {v}")
                    else:
                        parts.append(f"modified '{m['id']}'")
            if added:
                parts.append(f"added {', '.join(added)}")
            if parts:
                delta_str = " [delta: " + "; ".join(parts) + "]"
        return f"The agent {desc}, resulting in a net reward of {net}.{delta_str}"

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
