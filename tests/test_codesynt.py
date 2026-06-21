"""Tests for the CodeSynt (AST Synthesis) domain."""

import unittest

from tais_core.domains.codesynt import CodeSyntWorld, make_codesynt_graph
from tais_core.mote import UniversalMote
from tais_core.reality import Transformation


class CodeSyntWorldTests(unittest.TestCase):
    def setUp(self):
        self.world = CodeSyntWorld()
        self.graph = make_codesynt_graph()

    def test_initial_graph_has_requirement_and_goal(self):
        req = self.graph.get_entity("req1")
        goal = self.graph.get_entity("goal")
        self.assertIsNotNone(req)
        self.assertIsNotNone(goal)
        self.assertFalse(req.get("satisfied"))

    def test_add_variable_creates_variable_entity(self):
        tr = Transformation("add_variable", "codesynt", "TRANSFORM", base_cost=0.3)
        after, cons = self.world.act(self.graph, tr, {})
        vars = [e for e in after.entities("VARIABLE")]
        self.assertEqual(len(vars), 1)
        self.assertGreater(cons.net, 0)

    def test_add_operation_creates_operation_entity(self):
        tr = Transformation("add_operation", "codesynt", "COMPOSE", base_cost=0.5)
        after, cons = self.world.act(self.graph, tr, {})
        ops = [e for e in after.entities("OPERATION")]
        self.assertEqual(len(ops), 1)
        self.assertGreater(cons.net, 0)

    def test_run_tests_fails_without_prerequisites(self):
        tr = Transformation("run_tests", "codesynt", "VERIFY", base_cost=0.4)
        _, cons = self.world.act(self.graph, tr, {})
        self.assertEqual(cons.task_signal, None)
        self.assertLess(cons.net, 0)

    def test_run_tests_succeeds_with_var_and_op(self):
        g = self.graph
        g, _ = self.world.act(g, Transformation("add_variable", "codesynt", "TRANSFORM", base_cost=0.3), {})
        g, _ = self.world.act(g, Transformation("add_operation", "codesynt", "COMPOSE", base_cost=0.5), {})
        _, cons = self.world.act(g, Transformation("run_tests", "codesynt", "VERIFY", base_cost=0.4), {})
        self.assertEqual(cons.task_signal, "TASK_SUCCESS")

    def test_refactor_produces_small_reward(self):
        tr = Transformation("refactor", "codesynt", "MUTATE", base_cost=0.6)
        _, cons = self.world.act(self.graph, tr, {})
        self.assertGreater(cons.reward, 0)

    def test_type_check_produces_small_reward(self):
        tr = Transformation("type_check", "codesynt", "TEST", base_cost=0.2)
        _, cons = self.world.act(self.graph, tr, {})
        self.assertGreater(cons.reward, 0)

    def test_mote_can_step_without_crashing(self):
        mote = UniversalMote(energy=100)
        for t in range(5):
            g, cons, action = mote.step(self.world, self.graph, mote_position="root", tick=t)
            self.assertIsNotNone(g)
            self.assertIsNotNone(cons)

    def test_mote_solves_with_dependency_ordering(self):
        mote = UniversalMote(energy=500)
        g = self.graph
        seen_actions = set()
        for t in range(50):
            g, cons, action = mote.step(self.world, g, mote_position="root", tick=t)
            if cons.task_signal == "TASK_SUCCESS":
                return
            if action:
                seen_actions.add(action.name)
        self.assertIn("add_variable", seen_actions)
        self.assertIn("add_operation", seen_actions)
