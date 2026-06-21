"""Tests for core TAIS primitives: RealityGraph, EpisodicMemory, SpeechOrgan."""

import unittest

from tais_core.memory import MoteMemory
from tais_core.reality import Entity, GraphPattern, RealityGraph, Relation, Transformation, Consequence
from tais_core.speech import SpeechOrgan


class GraphPrimitiveTests(unittest.TestCase):
    def test_build_grid_graph(self):
        g = RealityGraph("grid", "danger_food")
        g.add_entity(Entity("pred", "THREAT", {"kind": "predator"}))
        g.add_entity(Entity("food", "RESOURCE", {"kind": "food"}))
        g.add_relation(Relation("pred", "NEAR", "food"))
        self.assertEqual(len(g.entities()), 2)
        self.assertEqual(len(g.relations()), 1)

    def test_build_chem_graph(self):
        g = RealityGraph("chem", "toxic_binding")
        g.add_entity(Entity("tox", "TOXIC_GROUP", {"kind": "nitro"}))
        g.add_entity(Entity("site", "BINDING_SITE", {"kind": "pocket"}))
        g.add_relation(Relation("tox", "ADJACENT_TO", "site"))
        self.assertEqual(len(g.entities()), 2)

    def test_graph_diff_and_distance(self):
        g1 = RealityGraph("grid", "test")
        g1.add_entity(Entity("food", "RESOURCE", {"value": 5}))
        g2 = g1.snapshot()
        g2.update_entity("food", value=10)
        delta = g1.diff(g2)
        self.assertEqual(delta.magnitude, 1)
        self.assertEqual(g1.distance(g2), 0.0)

    def test_neighborhood_and_snapshot(self):
        g = RealityGraph("grid", "test")
        g.add_entity(Entity("center", "NODE", {}))
        g.add_entity(Entity("leaf", "NODE", {}))
        g.add_relation(Relation("center", "LINKS_TO", "leaf"))
        hood = g.neighborhood("center", hops=1)
        self.assertIn("center", [e.id for e in hood.entities()])
        self.assertIn("leaf", [e.id for e in hood.entities()])

    def test_pattern_matching(self):
        g = RealityGraph("grid", "test")
        g.add_entity(Entity("pred", "THREAT", {}))
        g.add_entity(Entity("food", "RESOURCE", {}))
        g.add_relation(Relation("pred", "NEAR", "food"))
        pattern = GraphPattern(
            [Entity("_t", "THREAT", {}), Entity("_r", "RESOURCE", {})],
            [Relation("_t", "NEAR", "_r")],
            name="threat_near_resource",
            source_domain="grid",
        )
        matches = g.find_pattern(pattern)
        self.assertTrue(matches)

    def test_structural_analogy(self):
        g1 = RealityGraph("grid", "test")
        g1.add_entity(Entity("pred", "THREAT", {}))
        g1.add_entity(Entity("food", "RESOURCE", {}))
        g1.add_relation(Relation("pred", "NEAR", "food"))

        g2 = RealityGraph("chem", "test")
        g2.add_entity(Entity("tox", "TOXIC_GROUP", {}))
        g2.add_entity(Entity("site", "BINDING_SITE", {}))
        g2.add_relation(Relation("tox", "ADJACENT_TO", "site"))

        pattern = GraphPattern(g1.entities(), g1.relations(), name="danger_near_resource", source_domain="grid")
        analogy = g2.analogize(pattern)
        self.assertGreater(analogy.confidence, 0)

    def test_entity_filtering_by_type(self):
        g = RealityGraph("test", "v1")
        g.add_entity(Entity("e1", "THREAT", {}))
        g.add_entity(Entity("e2", "RESOURCE", {}))
        threats = g.entities("THREAT")
        self.assertEqual(len(threats), 1)
        self.assertEqual(threats[0].id, "e1")


class EpisodicMemoryTests(unittest.TestCase):
    def test_record_and_transfer(self):
        g1 = RealityGraph("grid", "test")
        g1.add_entity(Entity("pred", "THREAT", {}))
        g1.add_entity(Entity("food", "RESOURCE", {}))
        g1.add_relation(Relation("pred", "NEAR", "food"))

        g2 = RealityGraph("chem", "test")
        g2.add_entity(Entity("tox", "TOXIC_GROUP", {}))
        g2.add_entity(Entity("site", "BINDING_SITE", {}))
        g2.add_relation(Relation("tox", "ADJACENT_TO", "site"))

        mem = MoteMemory()
        tr = Transformation("avoid_pattern", "grid", "MOVE_AWAY", base_cost=1.0)
        cons = Consequence(reward=5.0, concept_signals={"DANGER": 1.0})
        mem.record_episode(g1, g1, tr, cons, predicted=0.0, domain="grid", tick=1)

        self.assertEqual(len(mem.episodic), 1)
        self.assertGreater(mem.episodic.action_value("avoid_pattern", domain="grid"), 0.0)

        transfers = mem.transfer_patterns_to(g2)
        self.assertTrue(transfers)
        self.assertTrue(transfers[0][1].is_useful)

    def test_prediction_error_trend(self):
        mem = MoteMemory()
        g = RealityGraph("test", "v1")
        g.add_entity(Entity("e1", "THING", {}))
        for i in range(8):
            tr = Transformation(f"act_{i}", "test", "TEST", base_cost=0.5)
            cons = Consequence(reward=1.0 if i < 4 else 2.0)
            predicted = 1.0 if i < 4 else 3.0
            mem.record_episode(g, g, tr, cons, predicted=predicted, domain="test", tick=i)
        trend = mem.episodic.prediction_error_trend()
        self.assertIsInstance(trend, float)

    def test_recent_concept_signals(self):
        mem = MoteMemory()
        g = RealityGraph("test", "v1")
        g.add_entity(Entity("e1", "THING", {}))
        for i in range(5):
            tr = Transformation(f"act_{i}", "test", "TEST", base_cost=0.5)
            cons = Consequence(reward=1.0, concept_signals={"SIG": 0.5 + i * 0.1})
            mem.record_episode(g, g, tr, cons, predicted=0.0, domain="test", tick=i)
        signals = mem.episodic.recent_concept_signals(3)
        self.assertIn("SIG", signals)

    def test_summary_contains_keys(self):
        mem = MoteMemory()
        s = mem.summary()
        self.assertIn("episodes", s)
        self.assertIn("patterns", s)
        self.assertIn("best_actions", s)
        self.assertIn("worst_actions", s)


class SpeechOrganTests(unittest.TestCase):
    def test_teach_and_interpret(self):
        s1 = SpeechOrgan(1)
        s2 = SpeechOrgan(2)
        s1.teach("ka", "DANGER", strength=0.8)
        utt = s1.compose(
            intent="DANGER",
            neighbors=[2],
            mote_state={"energy": 50, "fitness": 5, "nearest_threat": 3, "position": [0, 0], "neediest_neighbor_id": 2},
            domain="grid",
            tick=1,
            info_delta=5,
        )
        self.assertIsNotNone(utt)
        interpreted = s2.receive(utt)
        self.assertIn("DANGER", interpreted)

    def test_repair_utterance_records(self):
        s1 = SpeechOrgan(1)
        s2 = SpeechOrgan(2)
        s1.teach("lum", "GOOD", strength=0.8)
        utt = s1.compose(
            intent="GOOD",
            neighbors=[2],
            mote_state={"energy": 50, "fitness": 5, "nearest_threat": 3, "position": [0, 0], "neediest_neighbor_id": 2},
            domain="grid",
            tick=1,
            info_delta=5,
        )
        self.assertIsNotNone(utt)
        s2.record_action_outcome(utt, "MOVE_TOWARD", aligned=True, outcome="GOOD")
        stats = s2.stats()
        self.assertGreater(stats["semantic_success"], 0)

    def test_compose_receive_audit_cycle(self):
        s1 = SpeechOrgan(1)
        s2 = SpeechOrgan(2)
        s1.teach("tak", "AVOID", strength=0.9)
        utt = s1.compose(
            intent="AVOID",
            neighbors=[2],
            mote_state={"energy": 50, "fitness": 5, "nearest_threat": 3, "position": [0, 0], "neediest_neighbor_id": 2},
            domain="grid",
            tick=1,
            info_delta=5,
        )
        self.assertIsNotNone(utt)
        interpreted = s2.receive(utt)
        s2.record_action_outcome(utt, "MOVE_AWAY", aligned=True, outcome="GOOD")
        stats = s2.stats()
        self.assertIn("semantic_success", stats)
