"""Tests for Phase R3 — baseline agents and comparison."""

from __future__ import annotations

import json
import math
import os
import tempfile
import unittest

from tais_core.baselines import RandomAgent, HeuristicAgent, TabularQAgent, LLMPromptAgent
from tais_core.baselines.base import run_agent_step
from tais_core.baselines.tabular_q_agent import graph_structural_key
from tais_core.domains.gridworld import GridGraphWorld, make_grid_graph
from tais_core.domains.logic import LogicWorld, make_logic_graph_easy


class TestRandomAgent(unittest.TestCase):
    def test_reset(self):
        agent = RandomAgent(seed=42)
        agent.reset(seed=99)
        self.assertEqual(agent.name, "random")

    def test_choose_action_returns_valid_action(self):
        agent = RandomAgent(seed=42)
        world = GridGraphWorld()
        g = make_grid_graph(threat_near_resource=True)
        observation = world.observe(g, "mote")
        actions = world.valid_actions(observation, {})
        action = agent.choose_action(world, observation, actions, {}, tick=0)
        self.assertIsNotNone(action)
        self.assertIn(action, actions)

    def test_choose_action_empty_returns_none(self):
        agent = RandomAgent(seed=42)
        action = agent.choose_action(None, None, [], {}, tick=0)
        self.assertIsNone(action)

    def test_deterministic(self):
        agent = RandomAgent(seed=42)
        world = GridGraphWorld()
        g = make_grid_graph(threat_near_resource=True)
        obs = world.observe(g, "mote")
        acts = world.valid_actions(obs, {})
        a1 = agent.choose_action(world, obs, acts, {}, tick=0)
        agent.reset(seed=42)
        a2 = agent.choose_action(world, obs, acts, {}, tick=0)
        self.assertEqual(a1.name, a2.name)


class TestHeuristicAgent(unittest.TestCase):
    def test_reset(self):
        agent = HeuristicAgent(seed=42)
        agent.reset(seed=99)
        self.assertEqual(agent.name, "heuristic")

    def test_choose_action_returns_valid_action(self):
        agent = HeuristicAgent(seed=42)
        world = GridGraphWorld()
        g = make_grid_graph(threat_near_resource=True)
        observation = world.observe(g, "mote")
        actions = world.valid_actions(observation, {})
        action = agent.choose_action(world, observation, actions, {}, tick=0)
        self.assertIsNotNone(action)
        self.assertIn(action, actions)

    def test_choose_action_empty_returns_none(self):
        agent = HeuristicAgent(seed=42)
        action = agent.choose_action(None, None, [], {}, tick=0)
        self.assertIsNone(action)

    def test_prefers_transform(self):
        agent = HeuristicAgent(seed=0)
        from tais_core.reality import Transformation
        actions = [
            Transformation("a", "test", "MUTATE", base_cost=0.5),
            Transformation("b", "test", "TRANSFORM", base_cost=0.5),
        ]
        chosen = agent.choose_action(None, None, actions, {}, tick=0)
        self.assertEqual(chosen.universal_op, "TRANSFORM")


class TestTabularQAgent(unittest.TestCase):
    def test_reset(self):
        agent = TabularQAgent(seed=42)
        agent.reset(seed=99)
        self.assertEqual(agent.name, "tabular_q")
        self.assertEqual(len(agent.q_table), 0)

    def test_choose_action_returns_valid_action(self):
        agent = TabularQAgent(seed=42)
        world = GridGraphWorld()
        g = make_grid_graph(threat_near_resource=True)
        observation = world.observe(g, "mote")
        actions = world.valid_actions(observation, {})
        action = agent.choose_action(world, observation, actions, {}, tick=0)
        self.assertIsNotNone(action)
        self.assertIn(action, actions)

    def test_q_updates_after_outcome(self):
        agent = TabularQAgent(seed=42)
        world = GridGraphWorld()
        g = make_grid_graph(threat_near_resource=True)
        obs = world.observe(g, "mote")
        actions = world.valid_actions(obs, {})
        action = agent.choose_action(world, obs, actions, {}, tick=0)
        after, cons = world.act(g, action, {})
        agent.observe_outcome(world, g, action, after, cons, tick=0)
        state_key = graph_structural_key(g)
        self.assertIn((state_key, action.name), agent.q_table)

    def test_run_agent_step_via_tabular_q(self):
        agent = TabularQAgent(seed=42)
        world = GridGraphWorld()
        g = make_grid_graph(threat_near_resource=True)
        after, cons, action = run_agent_step(agent, world, g, {}, mote_position="mote", tick=0)
        self.assertIsNotNone(action)

    def test_graph_structural_key_is_string(self):
        g = make_grid_graph(threat_near_resource=True)
        key = graph_structural_key(g)
        self.assertIsInstance(key, str)
        self.assertIn("E:", key)
        self.assertIn("R:", key)


class TestLLMPromptAgent(unittest.TestCase):
    def test_disabled_by_default(self):
        agent = LLMPromptAgent()
        self.assertFalse(agent.enabled)

    def test_choose_action_raises(self):
        agent = LLMPromptAgent()
        with self.assertRaises(RuntimeError):
            agent.choose_action(None, None, [], {}, tick=0)

    def test_observe_outcome_raises(self):
        agent = LLMPromptAgent()
        with self.assertRaises(RuntimeError):
            agent.observe_outcome(None, None, None, None, None, tick=0)


class TestSmoke(unittest.TestCase):
    def test_import_runner(self):
        from experiments.phase_r import baseline_comparison
        self.assertTrue(hasattr(baseline_comparison, "run_experiment"))

    def test_2seed_smoke(self):
        from experiments.phase_r.baseline_comparison import run_experiment, CONDITIONS_ORDER
        results = run_experiment(seeds=2, pretrain_ticks=3, eval_ticks=5, verbose=False)
        self.assertEqual(len(results), 5)
        for name in CONDITIONS_ORDER:
            self.assertIn(name, results)
            self.assertEqual(len(results[name].values), 2)

    def test_output_files_created(self):
        import experiments.phase_r.baseline_comparison as bc
        results = bc.run_experiment(seeds=2, pretrain_ticks=3, eval_ticks=5, verbose=False)
        with tempfile.TemporaryDirectory() as tmp:
            base = os.path.join(tmp, "test_output")
            csv_path = base + ".csv"
            bc.write_csv(results, "RandomAgent", csv_path)
            self.assertTrue(os.path.exists(csv_path))
            with open(csv_path) as f:
                content = f.read()
            self.assertIn("TAIS_full", content)
            md_path = base + ".md"
            bc.write_md(results, 2, 3, 5, md_path)
            self.assertTrue(os.path.exists(md_path))

    def test_summary_not_nan(self):
        from experiments.phase_r.baseline_comparison import run_experiment, CONDITIONS_ORDER
        results = run_experiment(seeds=3, pretrain_ticks=3, eval_ticks=5, verbose=False)
        for name in CONDITIONS_ORDER:
            s = results[name].summary()
            for key in ["first_task_success_tick", "task_completion_rate", "reward"]:
                self.assertFalse(math.isnan(s[key]["mean"]),
                                 f"{name}/{key} mean is NaN")
