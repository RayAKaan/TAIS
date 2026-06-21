"""Tests for the CodeSynt (AST Synthesis) domain."""

import unittest

from tais_core.domains.codesynt import CustomCodeWorld
from tais_core.mote import UniversalMote
from tais_core.reality import Transformation


class CodeSyntWorldTests(unittest.TestCase):
    def setUp(self):
        self.world = CustomCodeWorld("def solve(): return False")
        self.graph = self.world.initial_graph()

    def test_initial_graph_has_requirement_and_goal(self):
        goal = self.graph.get_entity("goal")
        self.assertIsNotNone(goal)
        self.assertEqual(goal.get("status"), "unresolved")

    def test_fix_operator_creates_logic_fix_entity(self):
        tr = Transformation("fix_operator", "codesynt", "TRANSFORM", base_cost=0.5)
        after, cons = self.world.act(self.graph, tr, {})
        fixes = [e for e in after.entities() if e.id == "patch"]
        self.assertEqual(len(fixes), 1)
        self.assertGreater(cons.net, 0)
        self.assertEqual(cons.task_signal, "TASK_PROGRESS")

    def test_run_validation_fails_without_fix(self):
        tr = Transformation("run_validation", "codesynt", "VERIFY", base_cost=0.3)
        _, cons = self.world.act(self.graph, tr, {})
        self.assertEqual(cons.task_signal, None)
        self.assertLess(cons.net, 0)

    def test_run_validation_succeeds_after_fix(self):
        g = self.graph
        g, _ = self.world.act(g, Transformation("fix_operator", "codesynt", "TRANSFORM", base_cost=0.5), {})
        _, cons = self.world.act(g, Transformation("run_validation", "codesynt", "VERIFY", base_cost=0.3), {})
        self.assertEqual(cons.task_signal, "TASK_SUCCESS")

    def test_refactor_produces_small_penalty(self):
        tr = Transformation("refactor", "codesynt", "MUTATE", base_cost=0.2)
        _, cons = self.world.act(self.graph, tr, {})
        self.assertTrue(cons.valid)

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
        self.assertIn("fix_operator", seen_actions)
        self.assertIn("run_validation", seen_actions)
