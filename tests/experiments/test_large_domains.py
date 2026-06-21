"""Tests for Phase R4 — large domain variants.

Covers LogicWorldLarge, HazardWorldLarge, and RuleWorldChainLong.
All existing small domains remain untouched.
"""

from __future__ import annotations

import random
import unittest

from tais_core.domains import (
    LogicWorldLarge,
    HazardGraphWorldLarge,
    RuleWorldChainLong,
    make_logic_graph_large,
    make_hazard_graph_large,
    make_rule_graph_chain_long,
    load_domain,
)
from tais_core.mote import UniversalMote
from tais_core.reality import Transformation


# ─── LogicWorldLarge Tests ───────────────────────────────────────────────────

class LogicWorldLargeTests(unittest.TestCase):
    def test_factory_returns_graph_with_correct_size(self):
        g = make_logic_graph_large(seed=0, n_vars=6, n_clauses=12)
        vars = g.entities("VARIABLE")
        clauses = g.entities("CLAUSE")
        self.assertEqual(len(vars), 6)
        self.assertEqual(len(clauses), 12)
        tgt = g.get_entity("TARGET")
        self.assertIsNotNone(tgt)
        self.assertEqual(tgt.get("derive_id"), "formula_large")

    def test_deterministic(self):
        g1 = make_logic_graph_large(seed=42, n_vars=6, n_clauses=12)
        g2 = make_logic_graph_large(seed=42, n_vars=6, n_clauses=12)
        self.assertEqual(
            sorted(e.id for e in g1.entities("VARIABLE")),
            sorted(e.id for e in g2.entities("VARIABLE")),
        )

    def test_world_valid_actions_returns_actions(self):
        world = LogicWorldLarge()
        g = make_logic_graph_large(seed=0)
        actions = world.valid_actions(g, {})
        self.assertEqual(len(actions), 4)
        names = {a.name for a in actions}
        self.assertIn("assert_literal", names)
        self.assertIn("check_consistency", names)
        self.assertIn("retract_literal", names)
        self.assertIn("random_assert", names)

    def test_mote_can_step_without_crashing(self):
        random.seed(42)
        world = LogicWorldLarge()
        mote = UniversalMote(energy=100.0)
        g = make_logic_graph_large(seed=0)
        for t in range(5):
            g, cons, _ = mote.step(world, g, mote_position="ASSIGN", tick=t)
            if mote.energy <= 0:
                mote.energy = 50.0
        self.assertGreater(mote.actions_taken, 0)

    def test_load_domain_works(self):
        domain = load_domain("logic_large")
        g = domain.initial_graph()
        self.assertIsNotNone(g)
        self.assertEqual(len(g.entities("VARIABLE")), 6)
        self.assertEqual(len(g.entities("CLAUSE")), 12)


# ─── HazardWorldLarge Tests ──────────────────────────────────────────────────

class HazardWorldLargeTests(unittest.TestCase):
    def test_factory_returns_graph_with_start_exit(self):
        g = make_hazard_graph_large(seed=0, n_nodes=15, hazard_density=0.2)
        self.assertIsNotNone(g.get_entity("S"))
        self.assertIsNotNone(g.get_entity("E"))
        self.assertIsNotNone(g.get_entity("agent"))
        self.assertGreater(len(g.entities("HAZARD_NODE")), 0)
        self.assertGreater(len(g.entities("RESOURCE_NODE")), 0)

    def test_deterministic(self):
        g1 = make_hazard_graph_large(seed=42, n_nodes=15)
        g2 = make_hazard_graph_large(seed=42, n_nodes=15)
        s1 = g1.get_entity("S")
        s2 = g2.get_entity("S")
        self.assertIsNotNone(s1)
        self.assertIsNotNone(s2)
        # Both should have NEAR_HAZARD edges if hazards present
        self.assertEqual(
            len(list(g1.relations("NEAR_HAZARD"))),
            len(list(g2.relations("NEAR_HAZARD"))),
        )

    def test_world_actions_work(self):
        world = HazardGraphWorldLarge()
        g = make_hazard_graph_large(seed=0)
        actions = world.valid_actions(g, {})
        self.assertEqual(len(actions), 4)
        names = {a.name for a in actions}
        self.assertIn("move_to_neighbor", names)
        self.assertIn("approach_resource", names)
        self.assertIn("avoid_hazard", names)
        self.assertIn("verify_node", names)

    def test_mote_can_step_without_crashing(self):
        random.seed(42)
        world = HazardGraphWorldLarge()
        mote = UniversalMote(energy=100.0)
        g = make_hazard_graph_large(seed=0)
        for t in range(5):
            g, cons, _ = mote.step(world, g, mote_position="agent", tick=t)
            if mote.energy <= 0:
                mote.energy = 50.0
        self.assertGreater(mote.actions_taken, 0)

    def test_load_domain_works(self):
        domain = load_domain("hazard_large")
        g = domain.initial_graph()
        self.assertIsNotNone(g)
        self.assertIsNotNone(g.get_entity("S"))
        self.assertIsNotNone(g.get_entity("E"))

    def test_agent_starts_at_S(self):
        g = make_hazard_graph_large(seed=0)
        for rel, ent in g.neighbors_out("agent", "AT"):
            self.assertEqual(ent.id, "S")
            return
        self.fail("agent not connected via AT relation")

    def test_target_points_to_exit(self):
        g = make_hazard_graph_large(seed=0)
        tgt = g.get_entity("TARGET")
        self.assertIsNotNone(tgt)
        self.assertEqual(tgt.get("derive_id"), "E")


# ─── RuleWorldChainLong Tests ────────────────────────────────────────────────

class RuleWorldChainLongTests(unittest.TestCase):
    def test_factory_returns_chain_of_correct_length(self):
        g = make_rule_graph_chain_long(length=5)
        target = g.get_entity("TARGET")
        self.assertIsNotNone(target)
        self.assertEqual(target.get("derive_id"), "fact_5_known")
        # Chain has length+1 facts and length rules
        self.assertEqual(len(g.entities("FACT")), 6)
        self.assertEqual(len(g.entities("RULE")), 5)

    def test_deterministic(self):
        g1 = make_rule_graph_chain_long(length=5)
        g2 = make_rule_graph_chain_long(length=5)
        self.assertEqual(len(g1.entities("FACT")), len(g2.entities("FACT")))

    def test_chain_requires_length_steps_to_succeed(self):
        """For a chain of length L, exactly L applies are needed
        (each step derives the next intermediate fact; the L-th is the target)."""
        world = RuleWorldChainLong()
        g = make_rule_graph_chain_long(length=5)
        apply = Transformation("apply_implication", "rules", "TRANSFORM", base_cost=0.4)
        steps = 0
        for _ in range(10):
            g, cons = world.act(g, apply, {})
            steps += 1
            if cons.task_signal == "TASK_SUCCESS":
                break
        self.assertEqual(steps, 5)

    def test_chain_requires_progress_before_success(self):
        world = RuleWorldChainLong()
        g = make_rule_graph_chain_long(length=5)
        apply = Transformation("apply_implication", "rules", "TRANSFORM", base_cost=0.4)
        signals = []
        for _ in range(10):
            g, cons = world.act(g, apply, {})
            signals.append(cons.task_signal)
            if cons.task_signal == "TASK_SUCCESS":
                break
        self.assertIn("TASK_PROGRESS", signals)
        self.assertIn("TASK_SUCCESS", signals)

    def test_mote_can_step_without_crashing(self):
        random.seed(42)
        world = RuleWorldChainLong()
        mote = UniversalMote(energy=100.0)
        g = make_rule_graph_chain_long(length=5)
        for t in range(10):
            g, cons, _ = mote.step(world, g, mote_position="fact_0", tick=t)
            if mote.energy <= 0:
                mote.energy = 50.0
        self.assertGreater(mote.actions_taken, 0)

    def test_load_domain_works(self):
        domain = load_domain("rules_chain_long")
        g = domain.initial_graph()
        self.assertIsNotNone(g)
        target = g.get_entity("TARGET")
        self.assertIsNotNone(target)
        self.assertEqual(target.get("derive_id"), "fact_5_known")


if __name__ == "__main__":
    unittest.main()
