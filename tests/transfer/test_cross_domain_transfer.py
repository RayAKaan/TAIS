import unittest

from tais_core.reality import Entity, Relation, RealityGraph, GraphPattern, Transformation, Consequence
from tais_core.memory import PatternMemory
from tais_core import UniversalMote
from tais_core.domains.gridworld import GridGraphWorld, make_grid_graph
from tais_core.domains.rules import RuleWorld
from tais_core.domains import make_rule_graph


class TestCrossDomainTransfer_unit(unittest.TestCase):
    """Unit-level tests for the transfer mechanism itself."""

    def test_role_compatibility_boosts_matching_role(self):
        pattern = GraphPattern(
            entities=[Entity("e1", "AGENT"), Entity("e2", "RESOURCE")],
            relations=[Relation("e1", "SEES", "e2")],
            successful_action_role="APPROACH_GOOD",
            consequence_signature="GOOD",
            confidence=1.0,
            mean_outcome_net=4.0,
        )
        pm = PatternMemory(capacity=32)
        pm.store(pattern, Consequence(reward=4.0, valid=True, concept_signals={}))

        target_actions = [
            Transformation("assert_literal", "logic", "TRANSFORM", role_hint="APPROACH_GOOD"),
            Transformation("check_consistency", "logic", "VERIFY", role_hint="VERIFY_UNCERTAIN"),
        ]
        target_graph = RealityGraph("logic", "test")
        target_graph.add_entity(Entity("x1", "VARIABLE"))
        target_graph.add_entity(Entity("C1", "CLAUSE"))
        target_graph.add_relation(Relation("x1", "OCCURS_IN", "C1"))

        boosts, used = pm.action_priors(target_graph, target_actions)

        self.assertGreater(boosts["assert_literal"], boosts["check_consistency"])
        self.assertGreater(boosts["assert_literal"], 0.0)
        self.assertEqual(used, 1)

    def test_role_compatibility_zero_for_mismatched_role(self):
        pattern = GraphPattern(
            entities=[Entity("e1", "AGENT"), Entity("e2", "THREAT")],
            relations=[Relation("e1", "SEES", "e2")],
            successful_action_role="AVOID_BAD",
            consequence_signature="GOOD",
            confidence=1.0,
            mean_outcome_net=4.0,
        )
        pm = PatternMemory(capacity=32)
        pm.store(pattern, Consequence(reward=4.0, valid=True, concept_signals={}))

        target_actions = [
            Transformation("assert_literal", "logic", "TRANSFORM", role_hint="APPROACH_GOOD"),
        ]
        target_graph = RealityGraph("logic", "test")
        target_graph.add_entity(Entity("x1", "VARIABLE"))

        boosts, used = pm.action_priors(target_graph, target_actions)
        self.assertEqual(boosts["assert_literal"], 0.0)

    def test_negative_transfer_penalizes_mismatch(self):
        pattern = GraphPattern(
            entities=[Entity("e1", "AGENT"), Entity("e2", "RESOURCE")],
            relations=[Relation("e1", "SEES", "e2")],
            consequence_signature="BAD",
            confidence=1.0,
            mean_outcome_net=-3.0,
            failed_action_roles=["APPROACH_GOOD"],
            failed_action_ops=["TRANSFORM"],
        )
        pm = PatternMemory(capacity=32)
        pm.store(pattern, Consequence(reward=0.0, penalty=3.0, valid=False, concept_signals={}))

        target_actions = [
            Transformation("assert_literal", "logic", "TRANSFORM", role_hint="APPROACH_GOOD"),
            Transformation("check_consistency", "logic", "VERIFY", role_hint="VERIFY_UNCERTAIN"),
        ]
        target_graph = RealityGraph("logic", "test")
        target_graph.add_entity(Entity("x1", "VARIABLE"))
        target_graph.add_entity(Entity("C1", "CLAUSE"))
        target_graph.add_relation(Relation("x1", "OCCURS_IN", "C1"))

        boosts, used = pm.action_priors(target_graph, target_actions)

        self.assertLess(boosts["assert_literal"], 0.0)
        # SAFETY BIAS: VERIFY_UNCERTAIN gets a positive boost even in BAD patterns
        self.assertGreater(boosts["check_consistency"], boosts["assert_literal"])


class TestCrossDomainTransfer_integration(unittest.TestCase):
    """End-to-end: a mote pretrained on GridWorld shows transfer to RuleWorld."""

    def test_grid_pretrained_mote_uses_transfer_in_ruleworld(self):
        world = GridGraphWorld()
        graph = make_grid_graph(threat_near_resource=True)
        mote = UniversalMote(energy=100)

        # Pretrain in GridWorld
        for t in range(24):
            graph, cons, action = mote.step(world, graph, mote_position="mote", tick=t)

        self.assertGreater(mote.transfer_prior_uses, 0,
                           "mote should have built transferable patterns")

        # Now run in RuleWorld
        ruleworld = RuleWorld()
        rulegraph = make_rule_graph()

        before = mote.memory.patterns.best_patterns(3)
        self.assertGreater(len(before), 0, "should have stored patterns after pretrain")

        for t in range(100, 108):
            rulegraph, cons, action = mote.step(ruleworld, rulegraph, mote_position=None, tick=t)

        # The mote should have attempted pattern-based transfer
        self.assertGreater(
            mote.transfer_prior_uses,
            0,
            "cross-domain transfer should fire when switching domains",
        )

    def test_pretrain_has_more_transfer_than_fresh(self):
        """A GridWorld-pretrained mote uses more cross-domain transfer than a fresh one."""
        ruleworld = RuleWorld()

        # Fresh mote baseline
        fresh = UniversalMote(energy=100)
        for t in range(8):
            rg = make_rule_graph()
            rg, cons, action = fresh.step(ruleworld, rg, mote_position=None, tick=t)

        # Pretrained mote
        grid_world = GridGraphWorld()
        pretrained = UniversalMote(energy=100)
        g = make_grid_graph(threat_near_resource=True)
        for t in range(24):
            g, cons, action = pretrained.step(grid_world, g, mote_position="mote", tick=t)
        pretrained_uses_before = pretrained.transfer_prior_uses
        self.assertGreater(pretrained_uses_before, 0, "pretrained should have used transfer in GridWorld itself")

        for t in range(8):
            rulegraph2 = make_rule_graph()
            rulegraph2, cons, action = pretrained.step(ruleworld, rulegraph2, mote_position=None, tick=t)

        self.assertGreater(
            pretrained.transfer_prior_uses,
            pretrained_uses_before,
            "pretrained mote should fire additional cross-domain transfer in RuleWorld",
        )
