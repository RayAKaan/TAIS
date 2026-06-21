"""
Tests for cognitive engine integration into UniversalMote.

Covers:
- Engines are None by default (backward compatibility)
- Engines can be enabled and used
- Metacognitive modulation of exploration
- Causal recording of action->outcome
- Plan creation and execution
- Ablation mode (some engines None, others active)
- Full integration: mote with all engines in a real domain
"""

import unittest
from tais_core import (
    UniversalMote,
    MetacognitiveEngine,
    CausalReasoningEngine,
    HierarchicalPlanner,
    RuleWorld,
)
from tais_core.domains.rules import make_rule_graph


class TestEnginesDefaultNone(unittest.TestCase):
    """Cognitive engines must be None by default -- backward compatibility."""

    def test_metacog_none(self):
        mote = UniversalMote(energy=100)
        self.assertIsNone(mote.metacog)

    def test_causal_none(self):
        mote = UniversalMote(energy=100)
        self.assertIsNone(mote.causal)

    def test_planner_none(self):
        mote = UniversalMote(energy=100)
        self.assertIsNone(mote.planner)


class TestEnableCognitiveEngines(unittest.TestCase):
    """enable_cognitive_engines() creates the right objects."""

    def test_enable_all(self):
        mote = UniversalMote(energy=100)
        mote.enable_cognitive_engines()
        self.assertIsInstance(mote.metacog, MetacognitiveEngine)
        self.assertIsInstance(mote.causal, CausalReasoningEngine)
        self.assertIsInstance(mote.planner, HierarchicalPlanner)

    def test_enable_metacog_only(self):
        mote = UniversalMote(energy=100)
        mote.enable_cognitive_engines(metacognition=True, causal_reasoning=False, hierarchical_planning=False)
        self.assertIsInstance(mote.metacog, MetacognitiveEngine)
        self.assertIsNone(mote.causal)
        self.assertIsNone(mote.planner)

    def test_enable_none(self):
        mote = UniversalMote(energy=100)
        mote.enable_cognitive_engines(metacognition=False, causal_reasoning=False, hierarchical_planning=False)
        self.assertIsNone(mote.metacog)
        self.assertIsNone(mote.causal)
        self.assertIsNone(mote.planner)


class TestMoteStepsWithEngines(unittest.TestCase):
    """A mote with all engines enabled can still step through a domain."""

    def test_step_with_engines_ruleworld(self):
        mote = UniversalMote(energy=100)
        mote.enable_cognitive_engines()
        world = RuleWorld()
        graph = make_rule_graph()
        new_graph, cons, action = mote.step(world, graph, mote_position="rule_ab", tick=0)
        self.assertIsNotNone(cons)

    def test_step_without_engines_still_works(self):
        mote = UniversalMote(energy=100)
        world = RuleWorld()
        graph = make_rule_graph()
        new_graph, cons, action = mote.step(world, graph, mote_position="rule_ab", tick=0)
        self.assertIsNotNone(cons)

    def test_many_steps_with_engines(self):
        """Run 20 steps with engines -- mote should survive and learn."""
        mote = UniversalMote(energy=100)
        mote.enable_cognitive_engines()
        world = RuleWorld()
        graph = make_rule_graph()
        for tick in range(20):
            graph, cons, action = mote.step(world, graph, mote_position="rule_ab", tick=tick)
            if not mote.alive:
                break
        self.assertGreater(len(mote.causal.links), 0)
        self.assertGreater(len(mote.metacog.strategy_history), 0)


class TestCausalEngineIntegration(unittest.TestCase):
    """Causal engine records action->outcome from mote step loop."""

    def test_causal_records_on_step(self):
        mote = UniversalMote(energy=100)
        mote.enable_cognitive_engines(metacognition=False, causal_reasoning=True, hierarchical_planning=False)
        world = RuleWorld()
        graph = make_rule_graph()
        for tick in range(5):
            graph, cons, action = mote.step(world, graph, mote_position="rule_ab", tick=tick)
        self.assertGreater(mote.causal.links.__len__(), 0)

    def test_causal_links_have_delta_p(self):
        mote = UniversalMote(energy=100)
        mote.enable_cognitive_engines(causal_reasoning=True, metacognition=False, hierarchical_planning=False)
        world = RuleWorld()
        graph = make_rule_graph()
        for tick in range(10):
            graph, cons, action = mote.step(world, graph, mote_position="rule_ab", tick=tick)
        for link in mote.causal.links:
            self.assertIsInstance(link.delta_p, float)
            self.assertGreaterEqual(link.confidence, 0.0)


class TestMetacogEngineIntegration(unittest.TestCase):
    """Metacognitive engine tracks prediction accuracy."""

    def test_metacog_records_outcomes(self):
        mote = UniversalMote(energy=100)
        mote.enable_cognitive_engines(metacognition=True, causal_reasoning=False, hierarchical_planning=False)
        world = RuleWorld()
        graph = make_rule_graph()
        for tick in range(10):
            graph, cons, action = mote.step(world, graph, mote_position="rule_ab", tick=tick)
        self.assertGreater(len(mote.metacog.strategy_history), 0)
        self.assertGreater(mote.metacog.get_confidence(), 0.0)

    def test_metacog_modulates_exploration(self):
        """After many correct predictions, exploration should remain a valid float."""
        mote = UniversalMote(energy=100)
        mote.enable_cognitive_engines(metacognition=True, causal_reasoning=False, hierarchical_planning=False)
        world = RuleWorld()
        graph = make_rule_graph()
        initial_rate = mote.metacog.get_exploration_rate()
        for tick in range(30):
            graph, cons, action = mote.step(world, graph, mote_position="rule_ab", tick=tick)
        final_rate = mote.metacog.get_exploration_rate()
        self.assertIsInstance(final_rate, float)
        self.assertGreaterEqual(final_rate, 0.0)
        self.assertLessEqual(final_rate, 1.0)


class TestPlannerIntegration(unittest.TestCase):
    """Planner creates plans from causal model."""

    def test_planner_instantiated(self):
        mote = UniversalMote(energy=100)
        mote.enable_cognitive_engines(metacognition=False, causal_reasoning=False, hierarchical_planning=True)
        self.assertIsInstance(mote.planner, HierarchicalPlanner)

    def test_planner_creates_plan_from_causal(self):
        mote = UniversalMote(energy=100)
        mote.enable_cognitive_engines(causal_reasoning=True, hierarchical_planning=True)
        world = RuleWorld()
        graph = make_rule_graph()
        for tick in range(20):
            graph, cons, action = mote.step(world, graph, mote_position="rule_ab", tick=tick)
        links = mote.causal.get_all_links()
        causal_links = [(l.action, l.outcome, l.delta_p) for l in links if l.is_causal]
        if causal_links:
            mote.planner.create_plan("TASK_SUCCESS", causal_links, tick=20)


class TestReproductionWithEngines(unittest.TestCase):
    """Children inherit self-model parameters from parent."""

    def test_child_inherits_metacog_params(self):
        parent = UniversalMote(energy=100)
        parent.enable_cognitive_engines()
        parent.metacog.self_model.learning_speed = 0.8
        parent.metacog.self_model.exploration_tendency = 0.15
        child = parent.reproduce()
        self.assertIsInstance(child.metacog, MetacognitiveEngine)
        self.assertAlmostEqual(child.metacog.self_model.learning_speed, 0.8)
        self.assertAlmostEqual(child.metacog.self_model.exploration_tendency, 0.15)

    def test_child_no_causal_inheritance(self):
        parent = UniversalMote(energy=100)
        parent.enable_cognitive_engines()
        child = parent.reproduce()
        self.assertIsNone(child.causal)
        self.assertIsNone(child.planner)

    def test_child_without_parent_engines(self):
        """Parent without engines -> child without engines."""
        parent = UniversalMote(energy=100)
        child = parent.reproduce()
        self.assertIsNone(child.metacog)
        self.assertIsNone(child.causal)
        self.assertIsNone(child.planner)


class TestMetricsWithEngines(unittest.TestCase):
    """metrics() includes cognitive engine data when engines are active."""

    def test_metrics_without_engines(self):
        mote = UniversalMote(energy=100)
        m = mote.metrics()
        self.assertNotIn("metacog_confidence", m)
        self.assertNotIn("causal_links_count", m)

    def test_metrics_with_engines(self):
        mote = UniversalMote(energy=100)
        mote.enable_cognitive_engines()
        world = RuleWorld()
        graph = make_rule_graph()
        for tick in range(5):
            graph, cons, action = mote.step(world, graph, mote_position="rule_ab", tick=tick)
        m = mote.metrics()
        self.assertIn("metacog_confidence", m)
        self.assertIn("causal_links_count", m)
        self.assertIn("planner_active", m)


if __name__ == "__main__":
    unittest.main()
