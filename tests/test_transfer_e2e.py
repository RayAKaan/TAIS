import unittest
import numpy as np
from tais_core.mote import UniversalMote
from tais_core.reality import RealityGraph, Entity, Relation
from tais_core.domains.registry import load_domain

class TestTransferE2E(unittest.TestCase):
    def test_grid_to_rule_transfer_flow(self):
        mote = UniversalMote()
        grid_world = load_domain("grid")

        grid_graph = RealityGraph("grid", "transfer_pretrain")
        grid_graph.add_entity(Entity("p1", "THREAT", {"danger": 1.0}))
        grid_graph.add_entity(Entity("f1", "RESOURCE", {"value": 5.0}))
        grid_graph.add_relation(Relation("p1", "NEAR", "f1"))

        for tick in range(15):
            grid_graph, consequence, action = mote.step(grid_world, grid_graph, mote_position="f1", tick=tick)

        self.assertGreater(len(mote.memory.patterns), 0, "Mote should have learned patterns in GridWorld")

        rule_world = load_domain("rules")
        rule_graph = RealityGraph("rules", "transfer_target")
        rule_graph.add_entity(Entity("a", "FACT", {"truth": True}))
        rule_graph.add_entity(Entity("b", "FACT", {"truth": False}))
        rule_graph.add_relation(Relation("a", "IMPLIES", "b"))

        rule_obs = rule_world.observe(rule_graph, "a")
        available_actions = rule_world.valid_actions(rule_obs, {})

        action = mote.choose_action(rule_obs, available_actions)

        self.assertIsNotNone(action)

    def test_structural_analogy_precision(self):
        grid = RealityGraph("grid")
        grid.add_entity(Entity("pred", "THREAT", {}))
        grid.add_entity(Entity("food", "RESOURCE", {}))
        grid.add_relation(Relation("pred", "NEAR", "food"))

        rules = RealityGraph("rules")
        rules.add_entity(Entity("premise", "FACT", {}))
        rules.add_entity(Entity("conclusion", "FACT", {}))
        rules.add_relation(Relation("premise", "IMPLIES", "conclusion"))

        from tais_core.reality import GraphPattern
        pattern = GraphPattern(grid.entities(), grid.relations(), name="threat_near_resource")

        mapping = rules.analogize(pattern)

        self.assertTrue(mapping.is_useful)
        self.assertEqual(len(mapping.entity_map), 2)

    def test_role_compatibility_matrix(self):
        from tais_core.memory import role_compatibility

        self.assertEqual(role_compatibility("APPROACH_GOOD", "APPROACH_GOOD"), 1.0)

        self.assertEqual(role_compatibility("APPROACH_GOOD", "TRANSFORM_TOWARD_GOAL"), 0.70)

        self.assertEqual(role_compatibility("AVOID_BAD", "VERIFY_UNCERTAIN"), 0.45)

        self.assertEqual(role_compatibility("APPROACH_GOOD", "AVOID_BAD"), 0.0)

if __name__ == "__main__":
    unittest.main()
