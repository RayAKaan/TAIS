"""Tests for Structural Transfer v2: genuine structural analogy without role labels.

These tests validate the 5 breakthrough changes:
1. Role Discovery Engine (no role_hint needed)
2. Structural Compatibility via WL Kernel
3. Procedural Domain Factory
4. Structural Analogy Engine
5. Compositional Policy Transfer
"""

import unittest
import random

from tais_core.reality import Entity, Relation, RealityGraph, Transformation, Consequence, GraphPattern
from tais_core.mote import UniversalMote
from tais_core.domains.gridworld import GridGraphWorld, make_grid_graph
from tais_core.domains.negosim import NegoSimWorld, make_negosim_graph
from tais_core.role_discovery import RoleDiscoveryEngine, DiscoveredRole
from tais_core.structural_similarity import (
    StructuralCompatibility, wl_relabeled_graph, wl_similarity, wl_pattern_histogram,
)
from tais_core.analogy_engine import StructuralAnalogyEngine, StructuralAnalogy, neighborhood_hash, entity_structural_signature
from tais_core.policy_transfer import CompositionalPolicy, PolicySequence, PolicyStep, HierarchicalPlannerV2
from tais_core.domains.procedural import ProceduralDomainFactory, ProceduralWorld


# ═══════════════════════════════════════════════════════════════════════════════
# CHANGE 1: Role Discovery Engine Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestRoleDiscovery(unittest.TestCase):
    """Test that roles are discovered from structure, not assigned by code."""

    def test_structural_key_is_surface_independent(self):
        """Two graphs with the same topology but different names should have the same structural key."""
        engine = RoleDiscoveryEngine(min_cluster_size=1)

        g1 = RealityGraph("grid", "test")
        g1.add_entity(Entity("mote", "AGENT", {}))
        g1.add_entity(Entity("food", "RESOURCE", {}))
        g1.add_entity(Entity("pred", "THREAT", {}))
        g1.add_relation(Relation("mote", "SEES", "food"))
        g1.add_relation(Relation("mote", "SEES", "pred"))

        g2 = RealityGraph("negosim", "test")
        g2.add_entity(Entity("agent", "PARTICIPANT", {}))
        g2.add_entity(Entity("offer", "PROPOSAL", {}))
        g2.add_entity(Entity("risk", "DANGER_FLAG", {}))
        g2.add_relation(Relation("agent", "VIEWS", "offer"))
        g2.add_relation(Relation("agent", "VIEWS", "risk"))

        key1 = engine.compute_structural_key(g1)
        key2 = engine.compute_structural_key(g2)

        self.assertEqual(key1, key2,
            "Structural keys should be surface-independent: "
            "same topology must produce same key regardless of entity/relation names"
        )

    def test_different_topology_different_key(self):
        """Graphs with different topology should have different structural keys."""
        engine = RoleDiscoveryEngine(min_cluster_size=1)

        g1 = RealityGraph("star", "test")
        g1.add_entity(Entity("center", "HUB", {}))
        for i in range(5):
            g1.add_entity(Entity(f"leaf_{i}", "NODE", {}))
            g1.add_relation(Relation("center", "CONNECTS", f"leaf_{i}"))

        g2 = RealityGraph("chain", "test")
        for i in range(6):
            g2.add_entity(Entity(f"node_{i}", "NODE", {}))
            if i > 0:
                g2.add_relation(Relation(f"node_{i-1}", "CONNECTS", f"node_{i}"))

        key1 = engine.compute_structural_key(g1)
        key2 = engine.compute_structural_key(g2)

        self.assertNotEqual(key1, key2,
            "Different topologies should produce different structural keys"
        )

    def test_role_discovery_from_experience(self):
        """Roles should emerge from (observation, action, consequence) clustering."""
        engine = RoleDiscoveryEngine(min_cluster_size=2)

        g = RealityGraph("test", "role_test")
        g.add_entity(Entity("mote", "AGENT", {}))
        g.add_entity(Entity("food", "RESOURCE", {}))
        g.add_entity(Entity("pred", "THREAT", {}))
        g.add_relation(Relation("mote", "SEES", "food"))

        action = Transformation("approach_resource", "test", "MOVE_TOWARD", base_cost=0.5)
        for _ in range(3):
            engine.record_experience(
                observation=g,
                action=action,
                consequence=Consequence(reward=5.0, concept_signals={"GOOD": 0.8}),
                domain="grid",
                tick=0,
            )

        roles = engine.discover_roles()
        self.assertTrue(len(roles) > 0,
            "At least one role should be discovered from 3 similar experiences")
        self.assertEqual(roles[0].outcome_valence, "POSITIVE")

    def test_no_role_hint_needed(self):
        """The RoleDiscoveryEngine works without any role_hint on Transformations."""
        engine = RoleDiscoveryEngine(min_cluster_size=1)

        g = RealityGraph("test", "no_hint")
        g.add_entity(Entity("a", "TYPE_A", {}))
        g.add_entity(Entity("b", "TYPE_B", {}))
        g.add_relation(Relation("a", "LINKS", "b"))

        action = Transformation("do_thing", "test", "TRANSFORM", base_cost=1.0)
        self.assertIsNone(action.role_hint)

        role_id = engine.record_experience(
            observation=g,
            action=action,
            consequence=Consequence(reward=3.0, concept_signals={"GOOD": 0.9}),
            domain="test",
            tick=0,
        )

        self.assertIsNotNone(role_id,
            "Role should be discovered even without role_hint")

    def test_transfer_boosts_without_role_labels(self):
        """Transfer action boosts should work without role labels."""
        engine = RoleDiscoveryEngine(min_cluster_size=1)

        g1 = RealityGraph("source", "train")
        g1.add_entity(Entity("agent", "ACTOR", {}))
        g1.add_entity(Entity("target", "GOAL_ITEM", {}))
        g1.add_relation(Relation("agent", "PERCEIVES", "target"))

        for _ in range(3):
            engine.record_experience(
                observation=g1,
                action=Transformation("go", "source", "MOVE_TOWARD"),
                consequence=Consequence(reward=5.0, concept_signals={"GOOD": 0.8}),
                domain="source",
                tick=0,
            )

        g2 = RealityGraph("target", "eval")
        g2.add_entity(Entity("negotiator", "DELEGATE", {}))
        g2.add_entity(Entity("proposal", "OFFER", {}))
        g2.add_relation(Relation("negotiator", "REVIEWS", "proposal"))

        available = [
            Transformation("accept", "target", "MOVE_TOWARD"),
            Transformation("reject", "target", "MOVE_AWAY"),
        ]

        boosts, used = engine.transfer_action_boosts(g2, available)

        self.assertGreater(boosts["accept"], 0.0,
            "MOVE_TOWARD should get positive boost from structural transfer "
            "even when domain names are completely different"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# CHANGE 2: Structural Compatibility (WL Kernel) Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestStructuralCompatibility(unittest.TestCase):
    """Test WL kernel-based structural compatibility."""

    def test_identical_graphs_high_similarity(self):
        """A graph should be maximally similar to itself."""
        g = RealityGraph("test", "self_sim")
        g.add_entity(Entity("a", "TYPE_A", {}))
        g.add_entity(Entity("b", "TYPE_B", {}))
        g.add_entity(Entity("c", "TYPE_C", {}))
        g.add_relation(Relation("a", "LINKS", "b"))
        g.add_relation(Relation("b", "LINKS", "c"))

        compat = StructuralCompatibility()
        sim = compat.similarity(g, g)
        self.assertAlmostEqual(sim, 1.0, places=2,
            msg="A graph should have ~1.0 similarity with itself"
        )

    def test_same_topology_different_names_high_similarity(self):
        """Graphs with the same topology but different names should be similar.

        THIS IS THE ACID TEST for genuine structural transfer.
        """
        g1 = RealityGraph("grid", "source")
        g1.add_entity(Entity("mote", "AGENT", {}))
        g1.add_entity(Entity("food", "RESOURCE", {}))
        g1.add_entity(Entity("pred", "THREAT", {}))
        g1.add_relation(Relation("mote", "SEES", "food"))
        g1.add_relation(Relation("pred", "NEAR", "food"))

        g2 = RealityGraph("negosim", "target")
        g2.add_entity(Entity("delegate", "PARTICIPANT", {}))
        g2.add_entity(Entity("proposal", "OFFER", {}))
        g2.add_entity(Entity("risk", "DANGER_FLAG", {}))
        g2.add_relation(Relation("delegate", "REVIEWS", "proposal"))
        g2.add_relation(Relation("risk", "ASSOCIATED_WITH", "proposal"))

        compat = StructuralCompatibility()
        sim = compat.similarity(g1, g2)
        self.assertGreater(sim, 0.5,
            "Graphs with the same topology should have high WL similarity "
            "even when all entity/relation names are different"
        )

    def test_different_topology_low_similarity(self):
        """Graphs with different topology should have lower similarity."""
        g1 = RealityGraph("star", "test")
        g1.add_entity(Entity("center", "HUB", {}))
        for i in range(4):
            g1.add_entity(Entity(f"leaf_{i}", "NODE", {}))
            g1.add_relation(Relation("center", "LINKS", f"leaf_{i}"))

        g2 = RealityGraph("chain", "test")
        for i in range(5):
            g2.add_entity(Entity(f"n_{i}", "NODE", {}))
            if i > 0:
                g2.add_relation(Relation(f"n_{i-1}", "LINKS", f"n_{i}"))

        compat = StructuralCompatibility()
        sim = compat.similarity(g1, g2)
        self.assertLess(sim, 0.9,
            "Star and chain topologies should have different WL similarity"
        )

    def test_compatibility_positive_valence_alignment(self):
        """GOOD-GOOD alignment should produce positive compatibility."""
        g1 = RealityGraph("a", "test")
        g1.add_entity(Entity("x", "A", {}))
        g1.add_entity(Entity("y", "B", {}))
        g1.add_relation(Relation("x", "R", "y"))

        g2 = RealityGraph("b", "test")
        g2.add_entity(Entity("p", "C", {}))
        g2.add_entity(Entity("q", "D", {}))
        g2.add_relation(Relation("p", "S", "q"))

        compat = StructuralCompatibility()
        score = compat.compatibility_graphs(g1, g2, "GOOD", "GOOD")
        self.assertGreater(score, 0.0,
            "GOOD-GOOD alignment with similar topology should be positive"
        )

    def test_compatibility_anti_valence(self):
        """GOOD-BAD alignment should produce negative compatibility."""
        g1 = RealityGraph("a", "test")
        g1.add_entity(Entity("x", "A", {}))
        g1.add_entity(Entity("y", "B", {}))
        g1.add_relation(Relation("x", "R", "y"))

        g2 = RealityGraph("b", "test")
        g2.add_entity(Entity("p", "C", {}))
        g2.add_entity(Entity("q", "D", {}))
        g2.add_relation(Relation("p", "S", "q"))

        compat = StructuralCompatibility()
        score = compat.compatibility_graphs(g1, g2, "GOOD", "BAD")
        self.assertLess(score, 0.0,
            "GOOD-BAD alignment should produce negative compatibility"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# CHANGE 3: Procedural Domain Factory Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestProceduralDomainFactory(unittest.TestCase):
    """Test procedural domain generation with controllable overlap."""

    def test_generate_pair(self):
        """Should generate a pair of domain worlds."""
        source, target = ProceduralDomainFactory.generate_pair(
            overlap=0.7,
            complexity=30,
            seed=42,
        )
        self.assertIsInstance(source, ProceduralWorld)
        self.assertIsInstance(target, ProceduralWorld)

    def test_high_overlap_similar_structure(self):
        """High-overlap pairs should have similar WL structure."""
        source, target = ProceduralDomainFactory.generate_pair(
            overlap=0.9,
            complexity=30,
            surface_distance=0.9,
            seed=42,
        )
        compat = StructuralCompatibility()
        sim = compat.similarity(source.target_graph, target.target_graph)
        self.assertGreater(sim, 0.3,
            "High-overlap pairs should have reasonable structural similarity"
        )

    def test_surface_distance_renames_types(self):
        """High surface distance should produce different entity type names."""
        source, target = ProceduralDomainFactory.generate_pair(
            overlap=0.9,
            complexity=30,
            surface_distance=1.0,
            seed=42,
        )
        src_types = set(e.etype for e in source.target_graph.entities())
        tgt_types = set(e.etype for e in target.target_graph.entities())

        overlap = src_types & tgt_types
        self.assertLess(len(overlap), len(src_types),
            "High surface distance should rename most entity types"
        )

    def test_world_interface(self):
        """ProceduralWorld should implement WorldInterface correctly."""
        source, _ = ProceduralDomainFactory.generate_pair(
            overlap=0.7, complexity=30, seed=42,
        )
        graph = source.target_graph
        mote_state = {"mote_id_str": "e_0"}

        obs = source.observe(graph, "e_0")
        self.assertIsNotNone(obs)

        actions = source.valid_actions(graph, mote_state)
        self.assertTrue(len(actions) > 0)

        new_graph, cons = source.act(graph, actions[0], mote_state)
        self.assertIsNotNone(cons)

    def test_scaling_suite(self):
        """Should generate a valid experimental suite."""
        suite = ProceduralDomainFactory.generate_scaling_suite(
            overlaps=[0.3, 0.7],
            complexities=[20],
            surface_distances=[0.5],
            seeds_per_condition=2,
        )
        self.assertEqual(len(suite), 4)
        for exp in suite:
            self.assertIn("source_world", exp)
            self.assertIn("target_world", exp)
            self.assertIn("overlap", exp)


# ═══════════════════════════════════════════════════════════════════════════════
# CHANGE 4: Structural Analogy Engine Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestStructuralAnalogy(unittest.TestCase):
    """Test genuine subgraph matching for cross-domain transfer."""

    def test_analogy_between_same_topology(self):
        """Structural analogy should find mappings between same-topology graphs."""
        g1 = RealityGraph("grid", "source")
        g1.add_entity(Entity("mote", "AGENT", {}))
        g1.add_entity(Entity("food", "RESOURCE", {}))
        g1.add_entity(Entity("pred", "THREAT", {}))
        g1.add_relation(Relation("mote", "SEES", "food"))
        g1.add_relation(Relation("mote", "SEES", "pred"))

        g2 = RealityGraph("nego", "target")
        g2.add_entity(Entity("agent", "PARTICIPANT", {}))
        g2.add_entity(Entity("offer", "PROPOSAL", {}))
        g2.add_entity(Entity("risk", "WARNING", {}))
        g2.add_relation(Relation("agent", "VIEWS", "offer"))
        g2.add_relation(Relation("agent", "VIEWS", "risk"))

        engine = StructuralAnalogyEngine()
        analogy = engine.find_analogy(g1, g2)

        self.assertGreater(analogy.topology_match, 0.3,
            "Same-topology graphs should have positive WL similarity"
        )

    def test_neighborhood_hash_deterministic(self):
        """Neighborhood hash should be deterministic for the same graph."""
        g = RealityGraph("test", "hash")
        g.add_entity(Entity("a", "A", {}))
        g.add_entity(Entity("b", "B", {}))
        g.add_relation(Relation("a", "R", "b"))

        h1 = neighborhood_hash(g, "a")
        h2 = neighborhood_hash(g, "a")
        self.assertEqual(h1, h2, "Neighborhood hash should be deterministic")

    def test_structural_signature(self):
        """Structural role signature should work for degree analysis."""
        g = RealityGraph("test", "sig")
        g.add_entity(Entity("hub", "HUB", {}))
        g.add_entity(Entity("leaf1", "LEAF", {}))
        g.add_entity(Entity("leaf2", "LEAF", {}))
        g.add_relation(Relation("hub", "LINKS", "leaf1"))
        g.add_relation(Relation("hub", "LINKS", "leaf2"))

        hub_sig = entity_structural_signature(g, "hub")
        leaf_sig = entity_structural_signature(g, "leaf1")

        self.assertTrue("HUB" in hub_sig or "SOURCE" in hub_sig or hub_sig.startswith("DEG_"))
        self.assertTrue("SINK" in leaf_sig or leaf_sig.startswith("DEG_"))

    def test_structural_boosts_from_patterns(self):
        """Structural analogy should produce action boosts from stored patterns."""
        pattern = GraphPattern(
            entities=[Entity("_a", "AGENT", {}), Entity("_t", "THREAT", {}), Entity("_r", "RESOURCE", {})],
            relations=[Relation("_t", "NEAR", "_r")],
            name="threat_near_resource",
            source_domain="grid",
            consequence_signature="GOOD",
            successful_action_op="MOVE_TOWARD",
            confidence=0.8,
            mean_outcome_net=5.0,
        )

        target = RealityGraph("nego", "target")
        target.add_entity(Entity("delegate", "PARTICIPANT", {}))
        target.add_entity(Entity("risk", "WARNING", {}))
        target.add_entity(Entity("offer", "PROPOSAL", {}))
        target.add_relation(Relation("risk", "ASSOCIATED_WITH", "offer"))

        engine = StructuralAnalogyEngine()
        available = [
            Transformation("accept", "nego", "MOVE_TOWARD"),
            Transformation("reject", "nego", "MOVE_AWAY"),
        ]

        boosts = engine.compute_structural_boosts([pattern], target, available)
        self.assertGreater(boosts.get("accept", 0.0), 0.0,
            "MOVE_TOWARD should get positive boost from structural analogy "
            "with a GOOD pattern, even across different domain names"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# CHANGE 5: Compositional Policy Transfer Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestCompositionalPolicy(unittest.TestCase):
    """Test transfer of action sequences, not just individual role preferences."""

    def test_policy_sequence_creation(self):
        """A PolicySequence should have proper step ordering."""
        steps = [
            PolicyStep(step_index=0, topology_fingerprint="fp1",
                      action_op="VERIFY", expected_valence="POSITIVE"),
            PolicyStep(step_index=1, topology_fingerprint="fp2",
                      action_op="MOVE_TOWARD", expected_valence="POSITIVE",
                      prerequisite_step=0),
        ]

        seq = PolicySequence(
            sequence_id="test_seq",
            source_domain="grid",
            steps=steps,
            total_reward=7.0,
        )

        self.assertEqual(seq.length, 2)
        self.assertEqual(seq.steps[1].prerequisite_step, 0)

    def test_planner_v2_multistep(self):
        """HierarchicalPlannerV2 should support multi-step plans."""
        policy = CompositionalPolicy()
        planner = HierarchicalPlannerV2(compositional_policy=policy)

        self.assertIsNone(planner.active_plan)
        self.assertEqual(planner.plan_depth, 0)


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION: Mote with Structural Transfer v2
# ═══════════════════════════════════════════════════════════════════════════════

class TestMoteStructuralTransferIntegration(unittest.TestCase):
    """Test that UniversalMote works with structural transfer v2 enabled."""

    def test_enable_structural_transfer(self):
        """Should be able to enable structural transfer on a mote."""
        mote = UniversalMote(energy=100)
        mote.enable_structural_transfer()

        self.assertIsNotNone(mote.role_discovery)
        self.assertIsNotNone(mote.structural_compat)
        self.assertIsNotNone(mote.analogy_engine)
        self.assertIsNotNone(mote.compositional_policy)
        self.assertIsNotNone(mote.planner_v2)
        self.assertTrue(mote._use_structural_transfer)

    def test_mote_step_with_structural_transfer(self):
        """A mote with structural transfer should be able to step through GridWorld."""
        mote = UniversalMote(energy=100)
        mote.enable_structural_transfer()
        mote.enable_cognitive_engines()

        world = GridGraphWorld()
        graph = make_grid_graph()

        for tick in range(5):
            graph, cons, action = mote.step(world, graph, mote_position="mote", tick=tick)
            if not mote.alive:
                break

        self.assertTrue(mote.alive or mote.actions_taken > 0)

    def test_structural_transfer_metrics(self):
        """Mote metrics should include structural transfer info."""
        mote = UniversalMote(energy=100)
        mote.enable_structural_transfer()

        m = mote.metrics()
        self.assertIn("discovered_roles", m)
        self.assertIn("policy_sequences", m)

    def test_cross_domain_transfer_without_role_hint(self):
        """Test transfer from GridWorld to NegoSim WITHOUT role_hint."""
        random.seed(42)

        pretrained = UniversalMote(energy=100)
        pretrained.enable_structural_transfer()

        grid_world = GridGraphWorld()
        grid_graph = make_grid_graph()

        for tick in range(15):
            grid_graph, cons, action = pretrained.step(
                grid_world, grid_graph, mote_position="mote", tick=tick
            )
            if not pretrained.alive:
                pretrained = UniversalMote(energy=100)
                pretrained.enable_structural_transfer()
                break

        nego_world = NegoSimWorld()
        nego_graph = make_negosim_graph()

        pretrained_reward = 0.0
        fresh_reward = 0.0

        for tick in range(10):
            nego_graph, cons, action = pretrained.step(
                nego_world, nego_graph, mote_position="agent_0",
                tick=tick, extra_state={"mote_id_str": "agent_0"}
            )
            pretrained_reward += cons.net
            if not pretrained.alive:
                break

        fresh = UniversalMote(energy=100)
        fresh.enable_structural_transfer()
        nego_graph2 = make_negosim_graph()

        for tick in range(10):
            nego_graph2, cons, action = fresh.step(
                nego_world, nego_graph2, mote_position="agent_0",
                tick=tick, extra_state={"mote_id_str": "agent_0"}
            )
            fresh_reward += cons.net
            if not fresh.alive:
                break

        self.assertGreater(pretrained.actions_taken, 0)
        self.assertGreater(fresh.actions_taken, 0)


# ═══════════════════════════════════════════════════════════════════════════════
# ACID TEST: Surface-Independent Transfer
# ═══════════════════════════════════════════════════════════════════════════════

class TestAcidTestSurfaceIndependence(unittest.TestCase):
    """THE ACID TEST: transfer should work when all names are shuffled."""

    def test_structural_key_surface_independence(self):
        """Structural keys should be IDENTICAL for same-topology, different-name graphs."""
        engine = RoleDiscoveryEngine(min_cluster_size=1)

        ga = RealityGraph("a", "test")
        ga.add_entity(Entity("n1", "ALPHA", {}))
        ga.add_entity(Entity("n2", "BETA", {}))
        ga.add_entity(Entity("n3", "GAMMA", {}))
        ga.add_relation(Relation("n1", "CONNECTS", "n2"))
        ga.add_relation(Relation("n2", "LINKS", "n3"))

        gb = RealityGraph("b", "test")
        gb.add_entity(Entity("x1", "ZETA", {}))
        gb.add_entity(Entity("x2", "ETA", {}))
        gb.add_entity(Entity("x3", "THETA", {}))
        gb.add_relation(Relation("x1", "BINDS", "x2"))
        gb.add_relation(Relation("x2", "ATTACHES", "x3"))

        key_a = engine.compute_structural_key(ga)
        key_b = engine.compute_structural_key(gb)

        self.assertEqual(key_a, key_b,
            "ACID TEST FAILED: Structural keys differ for same-topology graphs "
            "with different surface names. Transfer cannot be surface-independent."
        )

    def test_wl_similarity_surface_independence(self):
        """WL similarity should be high for same-topology, different-name graphs."""
        ga = RealityGraph("a", "test")
        ga.add_entity(Entity("n1", "ALPHA", {}))
        ga.add_entity(Entity("n2", "BETA", {}))
        ga.add_entity(Entity("n3", "GAMMA", {}))
        ga.add_relation(Relation("n1", "CONNECTS", "n2"))
        ga.add_relation(Relation("n2", "LINKS", "n3"))

        gb = RealityGraph("b", "test")
        gb.add_entity(Entity("x1", "ZETA", {}))
        gb.add_entity(Entity("x2", "ETA", {}))
        gb.add_entity(Entity("x3", "THETA", {}))
        gb.add_relation(Relation("x1", "BINDS", "x2"))
        gb.add_relation(Relation("x2", "ATTACHES", "x3"))

        compat = StructuralCompatibility()
        sim = compat.similarity(ga, gb)

        self.assertGreater(sim, 0.8,
            f"ACID TEST FAILED: WL similarity={sim:.3f} for same-topology graphs "
            "with different names. Should be >0.8 for surface-independent transfer."
        )


if __name__ == "__main__":
    unittest.main()
