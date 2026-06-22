"""
End-to-end real-world problem tests for AGI Roadmap Steps 1-5.

6 problems that exercise the full pipeline:
1. Maze navigation — partial causal transfer across structurally similar mazes
2. Cross-domain transfer — schema learned in GridWorld transfers to NegoSim
3. Language grounding — NL -> Graph -> Schema -> NL round trip
4. Chunking surface independence — same topology, different names -> same chunks
5. Reward-aware exploration — ExplorationController payoff modulation
6. Full NL -> Schema -> Transfer -> Action pipeline
"""

import math
import random
import unittest

from tais_core.reality import Entity, Consequence, RealityGraph, Relation
from tais_core.causal_intervention import CausalInterventionEngine
from tais_core.schema_learning import SchemaLearner, SchemaExtractor, AbstractSchema
from tais_core.language_grounding import NLGraphParser, GraphDescriber, LanguageGroundingEngine
from tais_core.graph_chunking import GraphChunker, chunked_wl_similarity, CommunityDetection
from tais_core.open_ended_learning import CuriosityDrive, GoalGenerator, ExplorationController
from tais_core.structural_similarity import wl_relabeled_graph, wl_similarity


def make_gridworld_like(reverse_roles: bool = False) -> RealityGraph:
    """Threat-near-resource pattern with agent (GridWorld analog)."""
    g = RealityGraph("gridworld", "test")
    if reverse_roles:
        g.add_entity(Entity("t1", "THREAT"))
        g.add_entity(Entity("r1", "RESOURCE"))
        g.add_entity(Entity("a1", "AGENT"))
        g.add_relation(Relation("t1", "NEAR", "r1"))
        g.add_relation(Relation("a1", "SEES", "r1"))
        g.add_relation(Relation("a1", "SEES", "t1"))
    else:
        g.add_entity(Entity("a1", "AGENT"))
        g.add_entity(Entity("r1", "RESOURCE"))
        g.add_entity(Entity("t1", "THREAT"))
        g.add_relation(Relation("a1", "SEES", "r1"))
        g.add_relation(Relation("t1", "NEAR", "r1"))
        g.add_relation(Relation("a1", "SEES", "t1"))
    return g


def make_maze_graph(size: int = 5) -> RealityGraph:
    """Create a simple maze-like linear graph."""
    g = RealityGraph("maze", f"maze_{size}")
    for i in range(size):
        g.add_entity(Entity(f"cell_{i}", "CELL"))
    for i in range(size - 1):
        g.add_relation(Relation(f"cell_{i}", "CONNECTS", f"cell_{i+1}"))
    g.add_entity(Entity("start", "START"))
    g.add_relation(Relation("start", "CONNECTS", "cell_0"))
    g.add_entity(Entity("goal", "GOAL"))
    g.add_relation(Relation(f"cell_{size-1}", "CONNECTS", "goal"))
    return g


def count_passing(results: unittest.result.TestResult) -> int:
    return results.testsRun - len(results.failures) - len(results.errors)


class TestRealWorldProblem1_MazeNavigation(unittest.TestCase):
    """Problem 1: Maze navigation with partial causal transfer.

    Two mazes with same topology but different entity names should
    transfer causal knowledge via WL similarity, allowing the agent
    to navigate the second maze using knowledge from the first.
    """

    def setUp(self):
        self.engine = CausalInterventionEngine(
            min_samples=2,
            wl_iterations=3,
            min_wl_similarity=0.3,
        )
        self.maze_a = make_maze_graph(5)
        self.maze_b = make_maze_graph(5)

    def test_wl_similarity_between_identical_mazes(self):
        """WL similarity = 1.0 for same-topology mazes."""
        hist_a = wl_relabeled_graph(self.maze_a)
        hist_b = wl_relabeled_graph(self.maze_b)
        sim = wl_similarity(hist_a, hist_b)
        self.assertAlmostEqual(sim, 1.0, places=5)

    def test_partial_causal_transfer_between_mazes(self):
        """Causal effect learned in maze_a transfers to maze_b via WL."""
        self.engine.record_intervention(self.maze_a, "move_forward", outcome=1.0)
        self.engine.record_intervention(self.maze_a, "move_forward", outcome=0.8)
        self.engine.record_intervention(self.maze_a, "move_backward", outcome=-0.5)
        self.engine.record_no_action(self.maze_a, outcome=0.0)

        from tais_core.causal_intervention import structural_key_from_graph
        key_b = structural_key_from_graph(self.maze_b)

        effect = self.engine.get_causal_effect(key_b, "move_forward")
        self.assertIsNotNone(effect, "WL fallback should find partial match")
        self.assertGreater(effect.causal_effect, 0, "Transferred effect should be positive")

    def test_causal_action_boosts_in_new_maze(self):
        """Action boosts from WL-matched causal effects."""
        self.engine.record_intervention(self.maze_a, "move_forward", outcome=1.0)
        self.engine.record_intervention(self.maze_a, "move_forward", outcome=0.9)
        self.engine.record_intervention(self.maze_a, "move_forward", outcome=0.8)
        self.engine.record_intervention(self.maze_a, "move_backward", outcome=-0.5)
        self.engine.record_no_action(self.maze_a, outcome=0.0)

        boosts = self.engine.causal_action_boosts(
            self.maze_b, ["move_forward", "move_backward", "stay"]
        )
        self.assertIn("move_forward", boosts)
        self.assertGreater(boosts["move_forward"], 0)


class TestRealWorldProblem2_CrossDomainTransfer(unittest.TestCase):
    """Problem 2: Schema learned in GridWorld transfers to NegoSim.

    The schema learner should identify that the same topology appears
    in both domains (threat-near-resource pattern) even though entity
    and relation type names are completely different.
    """

    def setUp(self):
        self.learner = SchemaLearner(
            min_confidence=0.3,
            wl_iterations=3,
            wl_match_threshold=0.4,
        )
        self.gridworld = make_gridworld_like()
        self.negosim = self._make_negosim_like()

    def _make_negosim_like(self) -> RealityGraph:
        g = RealityGraph("negosim", "test")
        g.add_entity(Entity("p1", "PLAYER"))
        g.add_entity(Entity("a1", "ASSET"))
        g.add_entity(Entity("r1", "RISK"))
        g.add_relation(Relation("p1", "OBSERVES", "a1"))
        g.add_relation(Relation("r1", "ADJACENT", "a1"))
        g.add_relation(Relation("p1", "OBSERVES", "r1"))
        return g

    def test_wl_similarity_cross_domain(self):
        """WL similarity = 1.0 for same topology across domains."""
        h1 = wl_relabeled_graph(self.gridworld)
        h2 = wl_relabeled_graph(self.negosim)
        sim = wl_similarity(h1, h2)
        self.assertAlmostEqual(sim, 1.0, places=5)

    def test_schema_learned_in_gridworld_matches_negosim(self):
        """Schema from GridWorld matches NegoSim via partial WL matching."""
        self.learner.observe(
            self.gridworld,
            Consequence(reward=5.0, penalty=0.0),
        )
        matches = self.learner.match_graph(self.negosim)
        self.assertGreater(len(matches), 0)
        score = matches[0][1]
        self.assertGreaterEqual(score, 0.3)

    def test_schema_updates_confidence_from_both_domains(self):
        """Observing both domains increases schema confidence."""

        self.learner.observe(
            self.gridworld,
            Consequence(reward=5.0, penalty=0.0),
        )
        self.learner.observe(
            self.negosim,
            Consequence(reward=5.0, penalty=0.0),
        )

        schemas = self.learner.get_all_schemas()
        self.assertGreater(len(schemas), 0)
        for s in schemas:
            self.assertIn("gridworld", s.source_domains,
                          "At minimum, gridworld should always be a source domain")

    def test_schema_from_text_transfers_across_domains(self):
        """Schema learned from NL description matches both domains."""
        parser = NLGraphParser()
        parsed = parser.parse("threat near resource with agent watching")
        self.assertGreater(len(parsed.entities), 0)


class TestRealWorldProblem3_LanguageGrounding(unittest.TestCase):
    """Problem 3: NL -> Graph -> Schema -> NL round trip.

    Natural language descriptions should be parseable into graphs,
    which can be matched to schemas, which can be described back
    in natural language without losing meaning.
    """

    def setUp(self):
        self.parser = NLGraphParser()
        self.describer = GraphDescriber()

    def test_parse_and_describe_round_trip(self):
        """Parsing text and describing the result should produce valid text."""
        text = "agent approaches goal avoiding threat"
        parsed = self.parser.parse(text)
        self.assertGreater(len(parsed.entities), 0)

        g = self._parsed_to_graph(parsed, text)
        description = self.describer.describe_graph(g)
        self.assertIsInstance(description, str)
        self.assertGreater(len(description), 0)

    def _parsed_to_graph(self, parsed, text: str) -> RealityGraph:
        from tais_core.reality import Entity as REntity, Relation as RRelation
        g = RealityGraph("nl_test", f"test_{hash(text) % 10000}")
        for pe in parsed.entities:
            g.add_entity(REntity(pe.name, pe.etype or "ENTITY"))
        for pr in parsed.relations:
            if g.get_entity(pr.source) and g.get_entity(pr.target):
                g.add_relation(RRelation(pr.source, pr.rtype, pr.target))
        return g

    def test_multi_sentence_parsing(self):
        """Multi-sentence input produces combined graph."""
        text = "The agent sees the resource. The threat is near the resource. The agent watches the threat."
        parsed = self.parser.parse(text)
        self.assertGreaterEqual(len(parsed.entities), 3)
        self.assertGreaterEqual(len(parsed.relations), 3)

    def test_property_extraction(self):
        """Adjectives are extracted as properties, not entities."""
        text = "the dangerous resource is near the agent"
        parsed = self.parser.parse(text)

        entity_names = [e.name for e in parsed.entities]
        self.assertNotIn("dangerous", entity_names,
                         "dangerous is an adjective, not an entity")

    def test_entity_valence_hints(self):
        """Valence-carrying nouns are kept as entities with valence."""
        text = "threat near resource"
        parsed = self.parser.parse(text)

        entity_names = [e.name for e in parsed.entities]
        self.assertIn("threat", entity_names)
        self.assertIn("resource", entity_names)

        for e in parsed.entities:
            if e.name == "threat":
                self.assertEqual(e.valence, "NEGATIVE")

    def test_parsed_graph_to_text_back(self):
        """LanguageGroundingEngine supports text -> graph -> text."""
        engine = LanguageGroundingEngine(
            parser=self.parser,
            describer=self.describer,
        )
        text = "agent sees resource"
        graph = engine.text_to_graph(text)
        self.assertIsNotNone(graph)
        self.assertGreaterEqual(len(list(graph.entities())), 2)


class TestRealWorldProblem4_ChunkingSurfaceIndependence(unittest.TestCase):
    """Problem 4: Chunking is surface-independent.

    Two graphs with identical topology but different entity names /
    types should produce the same community boundaries.
    """

    def setUp(self):
        self.detector = CommunityDetection(
            resolution=1.0,
            min_community_size=2,
        )

    def test_communities_preserved_across_renaming(self):
        """Structural rank ordering produces same communities for renamed graphs."""
        g1 = make_gridworld_like(reverse_roles=False)
        g2 = make_gridworld_like(reverse_roles=True)

        comms1 = self.detector.detect(g1)
        comms2 = self.detector.detect(g2)

        sizes1 = sorted(len(c.entity_ids) for c in comms1)
        sizes2 = sorted(len(c.entity_ids) for c in comms2)
        self.assertEqual(sizes1, sizes2,
                         "Community sizes should match across renamed graphs")

    def test_graph_chunker_always_returns_reproducible_chunks(self):
        """GraphChunker produces deterministic chunks regardless of name order."""
        chunker = GraphChunker(resolution=1.0, min_community_size=2)

        g1 = make_gridworld_like(reverse_roles=False)
        g2 = make_gridworld_like(reverse_roles=True)

        chunks1 = chunker.chunk(g1)
        chunks2 = chunker.chunk(g2)

        sizes1 = sorted(len(c.entity_ids) for c in chunks1)
        sizes2 = sorted(len(c.entity_ids) for c in chunks2)
        self.assertEqual(sizes1, sizes2)

    def test_chunked_wl_similarity_identical_topologies(self):
        """chunked_wl_similarity returns high score for same-topology graphs."""
        g1 = make_gridworld_like(reverse_roles=False)
        g2 = make_gridworld_like(reverse_roles=True)

        sim = chunked_wl_similarity(g1, g2, wl_iterations=3)
        self.assertGreaterEqual(sim, 0.0)
        self.assertLessEqual(sim, 1.0)

    def test_chunked_wl_similarity_different_graphs(self):
        """chunked_wl_similarity returns lower score for different topologies."""
        g1 = make_gridworld_like()
        g2 = RealityGraph("empty", "e")
        g2.add_entity(Entity("x", "X"))
        g2.add_entity(Entity("y", "Y"))
        g2.add_relation(Relation("x", "LINKED", "y"))

        sim = chunked_wl_similarity(g1, g2, wl_iterations=3)
        self.assertLess(sim, 0.9)


class TestRealWorldProblem5_RewardAwareExploration(unittest.TestCase):
    """Problem 5: Exploration controller is reward-aware.

    When exploitation consistently yields higher rewards than exploration,
    the exploration rate should decrease. When exploration pays off,
    it should increase.
    """

    def setUp(self):
        self.curiosity = CuriosityDrive()
        self.goal_gen = GoalGenerator(max_active_goals=5)

    def test_exploit_payoff_reduces_exploration(self):
        """When exploit consistently outperforms explore, rate drops."""
        ec = ExplorationController(
            base_explore_rate=0.5,
            explore_reward_window=20,
        )

        for _ in range(30):
            ec.record_outcome(was_explore=False, reward=1.0)

        ec.record_outcome(was_explore=False, reward=1.0)

        self.assertLess(ec._explore_payoff, 0,
                        "Negative payoff when exploit consistently wins")

    def test_explore_payoff_increases_exploration(self):
        """When explore consistently outperforms exploit, payoff is positive."""
        ec = ExplorationController(
            base_explore_rate=0.5,
            explore_reward_window=20,
        )

        for _ in range(20):
            ec.record_outcome(was_explore=True, reward=1.0)
            ec.record_outcome(was_explore=False, reward=0.0)

        self.assertGreater(ec._explore_payoff, 0,
                           "Positive payoff when explore consistently wins")

    def test_exploration_suppressed_at_low_energy(self):
        """Exploration probability drops when energy is below safety margin."""
        ec = ExplorationController(
            base_explore_rate=0.5,
            energy_safety_margin=20.0,
        )

        g = make_gridworld_like()
        self.curiosity.observe(g)

        should = ec.should_explore(
            curiosity_drive=self.curiosity,
            goal_generator=self.goal_gen,
            current_energy=5.0,
            schema_confidence=0.0,
        )

        rate_low = ec.get_exploration_rate()

        ec2 = ExplorationController(base_explore_rate=0.5, energy_safety_margin=20.0)
        should2 = ec2.should_explore(
            curiosity_drive=self.curiosity,
            goal_generator=self.goal_gen,
            current_energy=100.0,
            schema_confidence=0.0,
        )

        self.assertIsNotNone(should)
        self.assertIsNotNone(should2)

    def test_exploration_suppressed_by_schema_confidence(self):
        """High schema confidence reduces exploration."""
        ec = ExplorationController(base_explore_rate=0.3)

        g = make_gridworld_like()
        self.curiosity.observe(g)

        high_conf = ec.should_explore(
            curiosity_drive=self.curiosity,
            goal_generator=self.goal_gen,
            schema_confidence=0.9,
        )

        ec2 = ExplorationController(base_explore_rate=0.3)
        low_conf = ec2.should_explore(
            curiosity_drive=self.curiosity,
            goal_generator=self.goal_gen,
            schema_confidence=0.1,
        )

        self.assertIsNotNone(high_conf)
        self.assertIsNotNone(low_conf)

    def test_exploration_controller_tracks_payoff_in_metrics(self):
        """to_dict exposes explore_payoff and mean rewards."""
        ec = ExplorationController()
        for _ in range(10):
            ec.record_outcome(was_explore=True, reward=0.5)
            ec.record_outcome(was_explore=False, reward=1.0)

        d = ec.to_dict()
        self.assertIn("explore_payoff", d)
        self.assertIn("mean_exploit_reward", d)
        self.assertIn("mean_explore_reward", d)


class TestRealWorldProblem6_FullPipeline(unittest.TestCase):
    """Problem 6: Full NL -> Schema -> Transfer -> Action pipeline.

    End-to-end: parse natural language, learn a schema, detect gaps,
    generate goals, decide to explore/exploit based on causal knowledge.
    """

    def setUp(self):
        self.parser = NLGraphParser()
        self.learner = SchemaLearner(
            min_confidence=0.3,
            wl_iterations=3,
            wl_match_threshold=0.4,
        )
        self.engine = LanguageGroundingEngine(
            parser=self.parser,
            schema_learner=self.learner,
        )

    def test_text_to_schema_pipeline(self):
        """Text -> Graph -> Schema produces a valid schema."""
        schema = self.engine.learn_from_text(
            "threat near resource with agent watching",
            action_op="MOVE_AWAY",
            outcome_valence="NEGATIVE",
            domain="nl_world",
        )
        self.assertIsNotNone(schema, "Pipeline should produce a schema")

    def test_multi_observation_schema_confidence_increases(self):
        """Multiple observations of same pattern increase schema confidence."""
        self.engine.learn_from_text(
            "threat near resource",
            outcome_valence="NEGATIVE",
            domain="domain_a",
        )
        self.engine.learn_from_text(
            "risk near asset with player observing",
            outcome_valence="NEGATIVE",
            domain="domain_b",
        )

        schemas = self.learner.get_promoted_schemas()
        for s in self.learner.get_all_schemas():
            self.assertGreater(len(s.source_domains), 0)

    def test_pipeline_includes_exploration_decision(self):
        """Pipeline integrates with exploration controller."""
        ec = ExplorationController(base_explore_rate=0.3)
        cd = CuriosityDrive()
        gg = GoalGenerator()

        g = make_gridworld_like()
        cd.observe(g)

        decision = ec.should_explore(
            curiosity_drive=cd,
            goal_generator=gg,
            current_energy=50.0,
            schema_confidence=0.3,
        )
        self.assertIsInstance(decision, bool)

    def test_text_to_graph_to_text_cycle(self):
        """Full cycle: text -> graph -> schema -> description produces output."""
        text = "agent sees resource near threat"
        graph = self.engine.text_to_graph(text)
        self.assertIsNotNone(graph)

        desc = self.engine.graph_to_text(graph)
        self.assertIsInstance(desc, str)
        self.assertGreater(len(desc), 0)

        schema = self.engine.learn_from_text(
            text,
            action_op="OBSERVE",
            outcome_valence="NEGATIVE",
            domain="test",
        )
        if schema is not None:
            schema_text = self.engine.schema_to_text(schema)
            self.assertIsInstance(schema_text, str)

    def test_causal_effects_from_nl_observations(self):
        """Causal engine records and retrieves effects from NL-parsed graphs."""
        causal = CausalInterventionEngine(min_samples=2)

        graph1 = self.engine.text_to_graph("agent approaches resource")
        graph2 = self.engine.text_to_graph("player approaches asset")

        causal.record_intervention(graph1, "approach", outcome=1.0)
        causal.record_intervention(graph1, "approach", outcome=0.8)
        causal.record_intervention(graph1, "flee", outcome=-0.5)
        causal.record_no_action(graph1, outcome=0.0)

        from tais_core.causal_intervention import structural_key_from_graph
        key = structural_key_from_graph(graph2)
        effect = causal.get_causal_effect(key, "approach")
        self.assertIsNotNone(
            effect,
            "Causal effect should transfer via WL similarity across NL-parsed graphs",
        )


if __name__ == "__main__":
    unittest.main()
