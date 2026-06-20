"""Multi-Agent Negotiation domain implementation for TAIS."""

from __future__ import annotations
import random
from typing import Any, Dict, List, Tuple, Optional

from ..reality import Consequence, Entity, Relation, RealityGraph, Transformation, WorldInterface


def make_negosim_graph(num_agents: int = 2) -> RealityGraph:
    """Creates a simulated Negotiation environment graph."""
    g = RealityGraph("negosim", "market_v1")

    for i in range(num_agents):
        agent_id = f"agent_{i}"
        g.add_entity(Entity(agent_id, "AGENT", {"id": i, "energy": 100.0}))

        # Resources
        res_id = f"res_{i}"
        g.add_entity(Entity(res_id, "RESOURCE", {"type": "A" if i == 0 else "B", "quantity": 10}))
        g.add_relation(Relation(agent_id, "OWNS", res_id))

        # Goals
        goal_id = f"goal_{i}"
        g.add_entity(Entity(goal_id, "GOAL", {"needs": "B" if i == 0 else "A", "satisfied": False}))
        g.add_relation(Relation(agent_id, "PURSUES", goal_id))

    return g


class NegoSimWorld(WorldInterface):
    """
    Simulated Multi-Agent Negotiation domain.

    Structural Transfer mappings:
    - GridWorld: RESOURCE -> NegoSim: TRADE_OFFER (APPROACH_GOOD)
    - GridWorld: THREAT -> NegoSim: UNFAIR_OFFER (AVOID_BAD)
    - CodeSynt/SciEx: COMPOSE -> NegoSim: MAKE_PROPOSAL (TRANSFORM_TOWARD_GOAL)
    - Speech/Social: REPAIR -> NegoSim: NEGOTIATE (REPAIR_MISMATCH)
    """
    domain_name = "negosim"

    def observe(self, graph: RealityGraph, mote_position: Any) -> RealityGraph:
        agent_id = mote_position if isinstance(mote_position, str) else "agent_0"
        return graph.neighborhood(agent_id, hops=2)

    def valid_actions(self, graph: RealityGraph, mote_state: Dict) -> List[Transformation]:
        return [
            Transformation("make_offer", self.domain_name, "ASK", base_cost=0.4, role_hint="TRANSFORM_TOWARD_GOAL"),
            Transformation("accept_offer", self.domain_name, "ANSWER", base_cost=0.2, role_hint="APPROACH_GOOD"),
            Transformation("reject_offer", self.domain_name, "MOVE_AWAY", base_cost=0.2, role_hint="AVOID_BAD"),
            Transformation("evaluate_proposal", self.domain_name, "VERIFY", base_cost=0.3, role_hint="VERIFY_UNCERTAIN"),
            Transformation("renegotiate", self.domain_name, "MUTATE", base_cost=0.5, role_hint="REPAIR_MISMATCH"),
        ]

    def act(self, graph: RealityGraph, transformation: Transformation, mote_state: Dict) -> Tuple[RealityGraph, Consequence]:
        after = graph.snapshot()
        agent_id = mote_state.get("mote_id_str", "agent_0")

        other_agent_id = "agent_1" if agent_id == "agent_0" else "agent_0"
        others_props = [e for e in graph.entities("PROPOSAL") if e.get("from") == other_agent_id]
        if not others_props and random.random() < 0.3:
            prop_id = f"prop_{other_agent_id}_sim"
            after.add_entity(Entity(prop_id, "PROPOSAL", {"from": other_agent_id, "status": "pending"}))
            after.add_relation(Relation(other_agent_id, "OFFERS", prop_id))

        if transformation.name == "make_offer":
            prop_id = f"prop_{agent_id}_{random.randint(100, 999)}"
            after.add_entity(Entity(prop_id, "PROPOSAL", {"from": agent_id, "status": "pending"}))
            after.add_relation(Relation(agent_id, "OFFERS", prop_id))
            return after, Consequence(
                reward=1.0,
                concept_signals={"PROGRESS": 0.5, "TRUST": 0.2},
                explanation={"why": "made a trade proposal"}
            )

        if transformation.name == "accept_offer":
            proposals = [e for e in graph.entities("PROPOSAL") if e.get("from") != agent_id]
            if proposals:
                prop = proposals[0]
                after.update_entity(prop.id, status="accepted")

                agent_goal = [e for e in graph.entities("GOAL") if any(r.source == agent_id and r.target == e.id for r in graph.relations())][0]
                after.update_entity(agent_goal.id, satisfied=True)

                return after, Consequence(
                    reward=10.0,
                    concept_signals={"SUCCESS": 1.0, "GOOD": 1.0},
                    task_signal="TASK_SUCCESS",
                    explanation={"why": "trade offer accepted, goal satisfied"}
                )
            return graph, Consequence(penalty=0.5, explanation={"why": "no offers to accept"})

        if transformation.name == "reject_offer":
            proposals = [e for e in graph.entities("PROPOSAL") if e.get("from") != agent_id]
            if proposals:
                prop = proposals[0]
                after.remove_entity(prop.id)
                return after, Consequence(
                    reward=2.0,
                    concept_signals={"SAFE": 0.5},
                    explanation={"why": "rejected offer"}
                )
            return graph, Consequence(penalty=0.2, explanation={"why": "nothing to reject"})

        if transformation.name == "evaluate_proposal":
            return graph, Consequence(reward=0.5, concept_signals={"TRUST": 0.4}, explanation={"why": "evaluated offer fairness"})

        if transformation.name == "renegotiate":
            return graph, Consequence(reward=0.3, explanation={"why": "adjusting terms"})

        return graph, Consequence(penalty=1.0, valid=False)

    def evaluate(self, graph: RealityGraph, mote_state: Dict) -> float:
        agent_id = mote_state.get("mote_id_str", "agent_0")
        goals = [e for e in graph.entities("GOAL") if any(r.source == agent_id and r.target == e.id for r in graph.relations())]
        if goals and goals[0].get("satisfied"):
            return 10.0
        return 0.0

    def concepts(self) -> List[str]:
        return ["GOOD", "BAD", "TRUST", "SAFE", "SUCCESS", "PROGRESS"]
