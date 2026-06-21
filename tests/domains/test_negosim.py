"""Tests for the NegoSim (Multi-Agent Negotiation) domain."""

import unittest

from tais_core.domains.negosim import NegoSimWorld, make_negosim_graph
from tais_core.mote import UniversalMote
from tais_core.reality import Transformation


ADD_VAR = Transformation("add_variable", "codesynt", "TRANSFORM", base_cost=0.3)
ADD_OP = Transformation("add_operation", "codesynt", "COMPOSE", base_cost=0.5)


class NegoSimWorldTests(unittest.TestCase):
    def setUp(self):
        self.world = NegoSimWorld()
        self.graph = make_negosim_graph(num_agents=2)

    def test_initial_graph_has_two_agents(self):
        agents = self.graph.entities("AGENT")
        self.assertEqual(len(agents), 2)

    def test_each_agent_owns_a_resource(self):
        for i in range(2):
            res = self.graph.neighbors_out(f"agent_{i}", "OWNS")
            self.assertEqual(len(res), 1)

    def test_each_agent_has_a_goal(self):
        for i in range(2):
            goals = self.graph.neighbors_out(f"agent_{i}", "PURSUES")
            self.assertEqual(len(goals), 1)

    def test_goals_are_complementary(self):
        g0 = [e for e in self.graph.entities("GOAL") if any(
            r.source == "agent_0" and r.target == e.id for r in self.graph.relations())][0]
        g1 = [e for e in self.graph.entities("GOAL") if any(
            r.source == "agent_1" and r.target == e.id for r in self.graph.relations())][0]
        self.assertEqual(g0.get("needs"), "B")
        self.assertEqual(g1.get("needs"), "A")

    def test_make_offer_creates_proposal(self):
        after, cons = self.world.act(self.graph, Transformation("make_offer", "negosim", "ASK", base_cost=0.4),
                                     {"mote_id_str": "agent_0"})
        props = after.entities("PROPOSAL")
        self.assertGreater(len(props), 0)
        self.assertGreater(cons.net, 0)

    def test_accept_offer_satisfies_goal(self):
        g = self.graph
        g, _ = self.world.act(g, Transformation("make_offer", "negosim", "ASK", base_cost=0.4),
                              {"mote_id_str": "agent_1"})
        _, cons = self.world.act(g, Transformation("accept_offer", "negosim", "ANSWER", base_cost=0.2),
                                 {"mote_id_str": "agent_0"})
        self.assertEqual(cons.task_signal, "TASK_SUCCESS")

    def test_accept_without_offer_fails(self):
        _, cons = self.world.act(self.graph, Transformation("accept_offer", "negosim", "ANSWER", base_cost=0.2),
                                 {"mote_id_str": "agent_0"})
        self.assertLess(cons.net, 0)

    def test_reject_offer_removes_proposal(self):
        g = self.graph
        g, _ = self.world.act(g, Transformation("make_offer", "negosim", "ASK", base_cost=0.4),
                              {"mote_id_str": "agent_1"})
        after, cons = self.world.act(g, Transformation("reject_offer", "negosim", "MOVE_AWAY", base_cost=0.2),
                                     {"mote_id_str": "agent_0"})
        props = after.entities("PROPOSAL")
        self.assertEqual(len(props), 0)
        self.assertGreater(cons.net, 0)

    def test_reject_without_offer_fails(self):
        _, cons = self.world.act(self.graph, Transformation("reject_offer", "negosim", "MOVE_AWAY", base_cost=0.2),
                                 {"mote_id_str": "agent_0"})
        self.assertLess(cons.net, 0)

    def test_evaluate_proposal_produces_reward(self):
        _, cons = self.world.act(self.graph, Transformation("evaluate_proposal", "negosim", "VERIFY", base_cost=0.3),
                                 {"mote_id_str": "agent_0"})
        self.assertGreater(cons.reward, 0)

    def test_renegotiate_produces_reward(self):
        _, cons = self.world.act(self.graph, Transformation("renegotiate", "negosim", "MUTATE", base_cost=0.5),
                                 {"mote_id_str": "agent_0"})
        self.assertGreater(cons.reward, 0)

    def test_mote_can_step_without_crashing(self):
        mote = UniversalMote(energy=100)
        for t in range(5):
            g, cons, action = mote.step(self.world, self.graph, mote_position="agent_0", tick=t,
                                        extra_state={"mote_id_str": "agent_0"})
            self.assertIsNotNone(g)
            self.assertIsNotNone(cons)
