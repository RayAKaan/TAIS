"""Tests for the SciEx (Scientific Experiment Design) domain."""

import unittest

from tais_core.domains.sciex import SciExWorld, make_sciex_graph
from tais_core.mote import UniversalMote
from tais_core.reality import Transformation


class SciExWorldTests(unittest.TestCase):
    def setUp(self):
        self.world = SciExWorld()
        self.graph = make_sciex_graph()

    def test_initial_graph_has_theory_and_hypothesis(self):
        theory = self.graph.get_entity("theory1")
        hyp = self.graph.get_entity("hyp1")
        self.assertIsNotNone(theory)
        self.assertIsNotNone(hyp)
        self.assertFalse(hyp.get("tested"))

    def test_formulate_experiment_creates_experiment(self):
        tr = Transformation("formulate_experiment", "sciex", "COMPOSE", base_cost=0.5)
        after, cons = self.world.act(self.graph, tr, {})
        exps = after.entities("EXPERIMENT")
        self.assertEqual(len(exps), 1)
        self.assertGreater(cons.net, 0)

    def test_control_variable_without_experiment_fails(self):
        tr = Transformation("control_variable", "sciex", "TRANSFORM", base_cost=0.4)
        _, cons = self.world.act(self.graph, tr, {})
        self.assertLess(cons.net, 0)

    def test_control_variable_with_experiment_succeeds(self):
        g = self.graph
        g, _ = self.world.act(g, Transformation("formulate_experiment", "sciex", "COMPOSE", base_cost=0.5), {})
        _, cons = self.world.act(g, Transformation("control_variable", "sciex", "TRANSFORM", base_cost=0.4), {})
        self.assertGreater(cons.net, 0)

    def test_run_experiment_without_control_fails(self):
        g = self.graph
        g, _ = self.world.act(g, Transformation("formulate_experiment", "sciex", "COMPOSE", base_cost=0.5), {})
        _, cons = self.world.act(g, Transformation("run_experiment", "sciex", "TEST", base_cost=0.6), {})
        self.assertLess(cons.net, 0)

    def test_run_experiment_with_control_succeeds(self):
        g = self.graph
        g, _ = self.world.act(g, Transformation("formulate_experiment", "sciex", "COMPOSE", base_cost=0.5), {})
        g, _ = self.world.act(g, Transformation("control_variable", "sciex", "TRANSFORM", base_cost=0.4), {})
        _, cons = self.world.act(g, Transformation("run_experiment", "sciex", "TEST", base_cost=0.6), {})
        self.assertGreater(cons.net, 0)
        self.assertIsNotNone(self.graph.get_entity("hyp1"))

    def test_analyze_data_without_results_fails(self):
        tr = Transformation("analyze_data", "sciex", "VERIFY", base_cost=0.3)
        _, cons = self.world.act(self.graph, tr, {})
        self.assertLess(cons.net, 0)

    def test_analyze_data_succeeds(self):
        g = self.graph
        g, _ = self.world.act(g, Transformation("formulate_experiment", "sciex", "COMPOSE", base_cost=0.5), {})
        g, _ = self.world.act(g, Transformation("control_variable", "sciex", "TRANSFORM", base_cost=0.4), {})
        g, _ = self.world.act(g, Transformation("run_experiment", "sciex", "TEST", base_cost=0.6), {})
        _, cons = self.world.act(g, Transformation("analyze_data", "sciex", "VERIFY", base_cost=0.3), {})
        self.assertEqual(cons.task_signal, "TASK_SUCCESS")

    def test_revise_hypothesis_produces_small_reward(self):
        tr = Transformation("revise_hypothesis", "sciex", "MUTATE", base_cost=0.4)
        _, cons = self.world.act(self.graph, tr, {})
        self.assertGreater(cons.reward, 0)

    def test_mote_can_step_without_crashing(self):
        mote = UniversalMote(energy=100)
        for t in range(5):
            g, cons, action = mote.step(self.world, self.graph, mote_position="hyp1", tick=t)
            self.assertIsNotNone(g)
            self.assertIsNotNone(cons)

    def test_mote_solves_with_dependency_ordering(self):
        mote = UniversalMote(energy=500)
        g = self.graph
        seen_actions = set()
        for t in range(50):
            g, cons, action = mote.step(self.world, g, mote_position="hyp1", tick=t)
            if cons.task_signal == "TASK_SUCCESS":
                return
            if action:
                seen_actions.add(action.name)
        self.assertIn("formulate_experiment", seen_actions)
