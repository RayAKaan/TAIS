"""
TAIS V6 Cognitive Integration Tests.

Validate that metacognition, causal reasoning, and planning
are wired into the mote lifecycle and export correctly.
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from tais_swarm_v6.agents.mote_v6 import MoteV6
from tais_swarm_v6.agents.metacognition import MetacognitiveEngine
from tais_swarm_v6.agents.causal import CausalReasoningEngine
from tais_swarm_v6.agents.planning import HierarchicalPlanner, Plan, PlanStep
from tais_swarm_v6.engine.config import SwarmConfig


def _make_config() -> SwarmConfig:
    return SwarmConfig()


class TestMoteV6CognitiveEngines(unittest.TestCase):
    def setUp(self):
        self.config = _make_config()
        self.mote = MoteV6(x=5, y=5, config=self.config)

    def test_engines_instantiated(self):
        self.assertIsInstance(self.mote.metacog, MetacognitiveEngine)
        self.assertIsInstance(self.mote.causal, CausalReasoningEngine)
        self.assertIsInstance(self.mote.planner, HierarchicalPlanner)

    def test_metacognition_prediction_cycle(self):
        self.mote.metacog.record_prediction(tick=0, cue="food_north", expected="energy_up", confidence=0.8)
        self.mote.metacog.resolve_prediction(expected="energy_up", actual="energy_up")
        acc = self.mote.metacog.get_accuracy()
        self.assertGreater(acc, 0.0)

    def test_causal_action_outcome_tracking(self):
        self.mote.causal.record_action(tick=0, action="move_north", outcome_concept="energy_increase", positive_outcome=True)
        self.mote.causal.record_outcome(tick=1, outcome="energy_increase", delta=10, context={})
        strength = self.mote.causal.get_causal_strength("move_north", "energy_increase")
        self.assertGreaterEqual(strength, 0.0)

    def test_planner_generates_plan(self):
        goal = {"type": "increase_energy", "target": 120}
        plan = self.mote.planner.plan_for_goal(goal, self.mote.causal)
        if plan is not None:
            self.assertIsInstance(plan, Plan)
            self.assertGreater(len(plan.steps), 0)
            self.assertIsInstance(plan.steps[0], PlanStep)

    def test_to_dict_exports_raw_cognitive_state(self):
        state = self.mote.to_dict()
        self.assertIn("metacognition", state)
        self.assertIn("causal", state)
        self.assertIn("planner", state)
        self.assertIn("predictions", state["metacognition"])
        self.assertIn("active_plan", state["planner"])

    def test_exploration_rate_responds_to_accuracy(self):
        for i in range(20):
            self.mote.metacog.record_prediction(tick=i, cue="x", expected="y", confidence=0.5)
            self.mote.metacog.resolve_prediction(expected="y", actual="z")
        rate_low = self.mote.metacog.get_exploration_rate()

        self.mote.metacog = MetacognitiveEngine()
        for i in range(20):
            self.mote.metacog.record_prediction(tick=i, cue="x", expected="y", confidence=0.9)
            self.mote.metacog.resolve_prediction(expected="y", actual="y")
        rate_high = self.mote.metacog.get_exploration_rate()

        self.assertNotEqual(rate_low, rate_high)

    def test_causal_counterfactual(self):
        for i in range(5):
            self.mote.causal.record_action(tick=i * 2, action="eat", outcome_concept="energy_up", positive_outcome=True)
        self.mote.causal.record_action(tick=10, action="eat", outcome_concept="energy_up", positive_outcome=True)
        cf = self.mote.causal.counterfactual("eat", "energy_up")
        self.assertIsNotNone(cf)
        self.assertIn("would_occur", cf)
        self.assertIn("strength", cf)


class TestSwarmV6TickPhaseOrdering(unittest.TestCase):
    def test_plan_before_utterance(self):
        from tais_swarm_v6.engine.core import SwarmV6
        from tais_swarm_v6.engine.config import CONFIG_PRESETS

        config = CONFIG_PRESETS["standard"]
        swarm = SwarmV6(config=config, seed=1)
        swarm.init_population(4)

        mote = swarm.motes[0]
        plan = Plan(
            steps=[PlanStep(action="move_north", target_concept="energy", expected_outcome="closer")],
            goal="test",
            expected_utility=0.5,
            tick_created=0,
        )
        mote.planner.start_plan(plan)

        plan_queried = [False]
        original_next_step = mote.planner.next_step

        def tracking_next_step():
            plan_queried[0] = True
            return original_next_step()

        mote.planner.next_step = tracking_next_step
        swarm.step()
        self.assertTrue(plan_queried[0],
                        "Planner.next_step() should be called during tick (Phase 2, before utterances)")


class TestBatchRunnerSmoke(unittest.TestCase):
    def test_runner_creates_experiment_result(self):
        from tais_swarm_v6.experiments.runner import BatchRunner, AblationConfig, ExperimentResult
        from tais_swarm_v6.engine.config import SwarmConfig

        config = SwarmConfig()
        runner = BatchRunner(config, output_dir="results")
        result = runner.run_single(seed=0, ticks=10, ablation=AblationConfig(), label="smoke")
        self.assertIsInstance(result, ExperimentResult)
        self.assertEqual(result.seed, 0)
        self.assertGreaterEqual(result.ticks, 1)
        self.assertIn("avg_energy", result.tick_records[0])


class TestAnalysisSmoke(unittest.TestCase):
    def test_analyzer_loads_and_compares(self):
        from tais_swarm_v6.experiments.analysis import ExperimentAnalyzer
        results = [
            {"ablation": "full", "avg_prediction_accuracy": 0.6, "avg_causal_links": 2.0,
             "avg_lexicon_size": 3.0, "total_plans_completed": 5, "total_plans_created": 10,
             "total_plans_failed": 2, "grammar_rules": 4, "births": 10, "deaths": 5,
             "predator_kills": 0, "final_population": 15, "avg_energy": 50.0,
             "wall_time_seconds": 1.0, "ticks": 100, "seed": 0, "tick_records": []},
            {"ablation": "no_metacognition", "avg_prediction_accuracy": 0.4,
             "avg_causal_links": 1.0, "avg_lexicon_size": 2.0, "total_plans_completed": 2,
             "total_plans_created": 5, "total_plans_failed": 1, "grammar_rules": 3,
             "births": 5, "deaths": 8, "predator_kills": 0, "final_population": 8,
             "avg_energy": 40.0, "wall_time_seconds": 1.0, "ticks": 100, "seed": 1,
             "tick_records": []},
        ]
        analyzer = ExperimentAnalyzer(results_dir="results")
        comparisons = analyzer.compare_conditions(results, metric="avg_prediction_accuracy")
        self.assertIn("no_metacognition", comparisons)
        self.assertIn("cohens_d", comparisons["no_metacognition"])
        self.assertIn("p_value", comparisons["no_metacognition"])


if __name__ == "__main__":
    unittest.main()
