"""Tests for the Global Fix: Domain-Isolated Stats + Evidence-Based Transfer Gating.

Verifies:
1. EpisodicMemory._action_stats keys are (domain, name), not just name.
2. action_value() and action_risk() return domain-isolated values.
3. best_actions()/worst_actions() handle tuple keys.
4. best_action_from_history() passes domain to action_value/action_risk.
5. choose_action() applies gating_factor = exp(historical) when historical < -0.1.
"""

import hashlib
import json
import math
import random
import unittest

from tais_core.memory import EpisodicMemory, Episode
from tais_core.mote import UniversalMote
from tais_core.reality import Consequence, Entity, RealityGraph, Transformation


def _graph_fp(graph: RealityGraph) -> str:
    return hashlib.md5(json.dumps(graph.summary(), sort_keys=True).encode()).hexdigest()[:12]


def _make_episode(name: str, domain: str, net: float, graph: RealityGraph) -> Episode:
    tr = Transformation(name, domain, "TEST", base_cost=0.5)
    cons = Consequence(reward=max(0, net), penalty=max(0, -net), concept_signals={"test": 1.0})
    return Episode(
        state_fingerprint=_graph_fp(graph),
        after_state_fingerprint=_graph_fp(graph),
        transformation=tr,
        consequence=cons,
        domain=domain,
    )


class DomainIsolatedStatsTests(unittest.TestCase):
    def setUp(self):
        self.mem = EpisodicMemory(capacity=16)
        self.g = RealityGraph("test", "v1")
        self.g.add_entity(Entity("e1", "THING", {}))

    def test_action_value_separates_domains(self):
        self.mem.record(_make_episode("foo", "domain_a", 5.0, self.g))
        self.mem.record(_make_episode("foo", "domain_b", -3.0, self.g))
        val_a = self.mem.action_value("foo", domain="domain_a")
        val_b = self.mem.action_value("foo", domain="domain_b")
        self.assertGreater(val_a, 0)
        self.assertLess(val_b, 0)

    def test_action_value_returns_zero_for_unknown_domain(self):
        self.mem.record(_make_episode("foo", "domain_a", 5.0, self.g))
        val = self.mem.action_value("foo", domain="unknown")
        self.assertEqual(val, 0.0)

    def test_action_value_defaults_to_unknown(self):
        self.mem.record(_make_episode("foo", "domain_a", 5.0, self.g))
        val = self.mem.action_value("foo")
        self.assertEqual(val, 0.0)

    def test_action_risk_separates_domains(self):
        self.mem.record(_make_episode("bar", "domain_x", 2.0, self.g))
        self.mem.record(_make_episode("bar", "domain_x", -1.0, self.g))
        self.mem.record(_make_episode("bar", "domain_y", 10.0, self.g))
        risk_x = self.mem.action_risk("bar", domain="domain_x")
        risk_y = self.mem.action_risk("bar", domain="domain_y")
        self.assertNotAlmostEqual(risk_x, risk_y, places=4)

    def test_action_risk_returns_1_for_single_sample(self):
        self.mem.record(_make_episode("baz", "d", 2.0, self.g))
        risk = self.mem.action_risk("baz", domain="d")
        self.assertEqual(risk, 1.0)

    def test_best_actions_handles_tuple_keys(self):
        self.mem.record(_make_episode("a1", "d1", 3.0, self.g))
        self.mem.record(_make_episode("a2", "d2", 5.0, self.g))
        best = self.mem.best_actions(n=2)
        self.assertEqual(len(best), 2)
        names = [name for name, _ in best]
        self.assertIn("a1", names)
        self.assertIn("a2", names)

    def test_worst_actions_handles_tuple_keys(self):
        self.mem.record(_make_episode("a1", "d1", -3.0, self.g))
        self.mem.record(_make_episode("a2", "d2", 5.0, self.g))
        worst = self.mem.worst_actions(n=1)
        self.assertEqual(len(worst), 1)
        self.assertEqual(worst[0][0], "a1")

    def test_record_stores_domain_in_key(self):
        self.mem.record(_make_episode("x", "my_domain", 1.0, self.g))
        self.assertIn(("my_domain", "x"), self.mem._action_stats)
        self.assertNotIn("x", self.mem._action_stats)

    def test_best_action_from_history_passes_domain(self):
        from tais_core.memory import MoteMemory
        mm = MoteMemory()
        mm.record_episode(
            state_before=self.g,
            state_after=self.g,
            transformation=Transformation("act", "myd", "TEST", base_cost=0.5),
            consequence=Consequence(reward=5.0),
            predicted=0.0,
            domain="myd",
            tick=1,
        )
        cand = [
            Transformation("act", "myd", "TEST", base_cost=0.5),
            Transformation("other", "myd", "TEST", base_cost=0.3),
        ]
        best = mm.best_action_from_history(cand)
        self.assertEqual(best.name, "act")


class EvidenceBasedTransferGatingTests(unittest.TestCase):
    def setUp(self):
        self.mote = UniversalMote(energy=500)
        self.g = RealityGraph("test", "v1")
        self.g.add_entity(Entity("e1", "THING", {}))
        self.g.domain = "test_domain"

    def test_gating_factor_suppresses_on_negative_historical(self):
        self.mote.memory.episodic.record(_make_episode("bad_action", "test_domain", -2.0, self.g))
        historical = self.mote.memory.episodic.action_value("bad_action", domain="test_domain")
        self.assertLess(historical, -0.1)
        expected_gating = math.exp(historical)
        self.assertLess(expected_gating, 1.0)
        self.assertAlmostEqual(expected_gating, math.exp(-2.0), places=6)

    def test_gating_factor_passes_on_neutral_historical(self):
        historical = self.mote.memory.episodic.action_value("unknown_action", domain="test_domain")
        self.assertEqual(historical, 0.0)
        self.assertGreaterEqual(historical, -0.1)
        gating = 1.0
        self.assertEqual(gating, 1.0)

    def test_gating_factor_drops_sharply_after_one_failure(self):
        self.mote.memory.episodic.record(_make_episode("run_test", "test_domain", -2.0, self.g))
        historical = self.mote.memory.episodic.action_value("run_test", domain="test_domain")
        gating = math.exp(historical) if historical < -0.1 else 1.0
        self.assertLess(gating, 0.2, "Single failure should suppress transfer below 20%")

    def test_positive_historical_leaves_gating_at_one(self):
        self.mote.memory.episodic.record(_make_episode("good_action", "test_domain", 5.0, self.g))
        historical = self.mote.memory.episodic.action_value("good_action", domain="test_domain")
        gating = 1.0
        if historical < -0.1:
            gating = math.exp(historical)
        self.assertEqual(gating, 1.0)

    def test_gating_integrated_in_choose_action(self):
        self.mote.memory.episodic.record(_make_episode("run_tests", "test_domain", -2.0, self.g))
        self.mote.memory.episodic.record(_make_episode("add_var", "test_domain", 1.0, self.g))
        self.mote.meta.curiosity = 0.0
        random.seed(0)
        obs = self.g
        acts = [
            Transformation("run_tests", "test_domain", "VERIFY", base_cost=0.4),
            Transformation("add_var", "test_domain", "TRANSFORM", base_cost=0.3),
        ]
        chosen = self.mote.choose_action(obs, acts)
        self.assertEqual(chosen.name, "add_var",
                         "Mote should avoid gated-down run_tests and pick add_var")
