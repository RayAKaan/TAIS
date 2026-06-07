import random
import unittest

from tais_core.mote import UniversalMote
from tais_core.domains import (
    GridGraphWorld,
    SequenceWorld,
    RuleWorld,
    make_grid_graph,
    make_sequence_graph,
    make_rule_graph,
)
from tais_core.reality import RealityGraph, Entity, Transformation, Consequence, WorldInterface


class EmptyNovelWorld(WorldInterface):
    """A deliberately new domain to test injection without mote edits."""

    domain_name = "novel_empty"

    def observe(self, graph, mote_position):
        return graph

    def valid_actions(self, graph, mote_state):
        return [Transformation("verify_empty", self.domain_name, "VERIFY", base_cost=0.1)]

    def act(self, graph, transformation, mote_state):
        return graph, Consequence(reward=1.0, valid=True, concept_signals={"GOOD": 1.0}, explanation={"why": "empty verified"})

    def evaluate(self, graph, mote_state):
        return 1.0


def run_sequence_training(mote, episodes=24):
    world = SequenceWorld()
    errors = []
    for i in range(episodes):
        # same rule: +1. The named action predict_delta_1 can accumulate value.
        start = 1 + (i % 5)
        g = make_sequence_graph([start, start + 1, start + 2], target_next=start + 3)
        _g2, cons, action = mote.step(world, g, tick=i)
        errors.append(abs(mote.last_prediction - cons.net))
    return errors, mote


class BaseValidationBattery(unittest.TestCase):
    def test_same_universal_mote_runs_three_domains(self):
        random.seed(7)
        mote = UniversalMote(energy=100)

        grid = GridGraphWorld()
        g = make_grid_graph(threat_near_resource=True)
        for t in range(5):
            g, _cons, _action = mote.step(grid, g, mote_position="mote", tick=t)

        seq_errors, _ = run_sequence_training(mote, episodes=12)

        rules = RuleWorld()
        rg = make_rule_graph()
        for t in range(5):
            rg, _cons, _action = mote.step(rules, rg, mote_position="rule_ab", tick=100 + t)

        self.assertIn("grid", mote.domain_history)
        self.assertIn("sequence", mote.domain_history)
        self.assertIn("rules", mote.domain_history)
        self.assertGreater(mote.actions_taken, 10)
        self.assertTrue(mote.alive)

    def test_prediction_error_reduces_in_sequence_world(self):
        random.seed(11)
        mote = UniversalMote(energy=100)
        errors, mote = run_sequence_training(mote, episodes=40)
        early = sum(errors[:10]) / 10
        late = sum(errors[-10:]) / 10
        # This is a weak criterion because exploration remains stochastic.
        # It should improve substantially in the tiny repeated +1 domain.
        self.assertLess(late, early)
        self.assertLess(mote.memory.prediction.error_trend(), 0.0)

    def test_transfer_advantage_sequence_pretraining(self):
        random.seed(13)
        trained = UniversalMote(energy=100)
        fresh = UniversalMote(energy=100)
        run_sequence_training(trained, episodes=30)

        trained_errors, _ = run_sequence_training(trained, episodes=10)
        fresh_errors, _ = run_sequence_training(fresh, episodes=10)
        trained_mean = sum(trained_errors) / len(trained_errors)
        fresh_mean = sum(fresh_errors) / len(fresh_errors)
        self.assertLess(trained_mean, fresh_mean)

    def test_pattern_transfer_grid_to_rules_or_sequence_exists(self):
        random.seed(17)
        mote = UniversalMote(energy=100)
        grid = GridGraphWorld()
        g = make_grid_graph(threat_near_resource=True)
        for t in range(8):
            g, _cons, _action = mote.step(grid, g, mote_position="mote", tick=t)

        rule_graph = make_rule_graph()
        transfers = mote.memory.transfer_patterns_to(rule_graph)
        self.assertTrue(transfers)
        self.assertGreater(transfers[0][1].confidence, 0.0)

    def test_new_domain_injection_without_mote_modification(self):
        random.seed(19)
        mote = UniversalMote(energy=20)
        world = EmptyNovelWorld()
        graph = RealityGraph("novel_empty")
        graph.add_entity(Entity("empty", "VOID", {}))
        graph, cons, action = mote.step(world, graph, mote_position=None, tick=1)
        self.assertTrue(cons.valid)
        self.assertEqual(action.name, "verify_empty")
        self.assertIn("novel_empty", mote.domain_history)
        self.assertGreater(mote.energy, 20)


if __name__ == "__main__":
    unittest.main(verbosity=2)
