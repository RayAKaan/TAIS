import math
import unittest

from tais_core.reality import (
    Entity,
    Relation,
    RealityGraph,
    GraphPattern,
    Transformation,
    Constraint,
    Consequence,
    WorldInterface,
)
from tais_core.memory import MoteMemory, CulturalMemory
from tais_core.speech import SpeechOrgan, Lexicon, Utterance


class TinyRuleWorld(WorldInterface):
    """Minimal domain lens used to test the universal four-function contract."""

    domain_name = "tiny_rules"

    def observe(self, graph, mote_position):
        # The attention mechanism: observe only the focused entity's neighborhood.
        return graph.neighborhood(mote_position, hops=1)

    def valid_actions(self, graph, mote_state):
        return [
            Transformation("apply_rule", self.domain_name, "TRANSFORM", base_cost=1.0),
            Transformation("verify", self.domain_name, "VERIFY", base_cost=0.5),
        ]

    def act(self, graph, transformation, mote_state):
        before = graph.snapshot()
        after = graph.snapshot()
        if transformation.name == "apply_rule":
            # if fact_a IMPLIES fact_b, add inferred fact_b_known
            if after.get_relation("fact_a", "IMPLIES", "fact_b"):
                after.add_entity(Entity("fact_b_known", "FACT", {"truth": True}))
                after.add_relation(Relation("fact_b", "SUPPORTS", "fact_b_known"))
                cons = Consequence(
                    reward=4.0,
                    valid=True,
                    concept_signals={"GOOD": 1.0, "TRUST": 0.5},
                    explanation={"why": "valid implication applied"},
                    graph_delta=before.diff(after),
                )
                return after, cons
        return graph, Consequence(penalty=2.0, valid=False, concept_signals={"BAD": 1.0}, explanation={"why": "invalid action"})

    def evaluate(self, graph, mote_state):
        return 10.0 if graph.get_entity("fact_b_known") else 0.0

    def concepts(self):
        return ["GOOD", "BAD", "TRUST"]


class RealityGraphTests(unittest.TestCase):
    def make_grid_graph(self):
        g = RealityGraph("grid", "danger_food")
        g.add_entity(Entity("pred", "THREAT", {"kind": "predator", "danger": 1.0}))
        g.add_entity(Entity("food", "RESOURCE", {"kind": "food", "value": 8.0}))
        g.add_relation(Relation("pred", "NEAR", "food"))
        return g

    def make_chem_graph(self):
        g = RealityGraph("chem", "toxic_binding")
        g.add_entity(Entity("tox", "TOXIC_GROUP", {"kind": "nitro", "danger": 1.0}))
        g.add_entity(Entity("site", "BINDING_SITE", {"kind": "pocket", "value": 8.0}))
        g.add_relation(Relation("tox", "ADJACENT_TO", "site"))
        return g

    def test_crud_neighborhood_and_diff(self):
        g = self.make_grid_graph()
        self.assertEqual(len(g.entities()), 2)
        self.assertEqual(len(g.relations()), 1)
        self.assertIsNotNone(g.get_relation("pred", "NEAR", "food"))

        n = g.neighborhood("pred", hops=1)
        self.assertEqual(len(n.entities()), 2)
        self.assertEqual(len(n.relations()), 1)

        g2 = g.snapshot()
        g2.update_entity("food", value=10.0)
        delta = g.diff(g2)
        self.assertEqual(delta.magnitude, 1)
        self.assertEqual(len(delta.entities_modified), 1)

        g3 = g.snapshot()
        g3.add_entity(Entity("water", "RESOURCE", {"kind": "water"}))
        g3.add_relation(Relation("food", "NEXT_TO", "water"))
        delta2 = g.diff(g3)
        self.assertEqual(len(delta2.entities_added), 1)
        self.assertEqual(len(delta2.relations_added), 1)

    def test_pattern_matching(self):
        g = self.make_grid_graph()
        pattern = GraphPattern(
            entities=[Entity("a", "THREAT", {}), Entity("b", "RESOURCE", {})],
            relations=[Relation("a", "NEAR", "b")],
        )
        matches = g.find_pattern(pattern)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["a"], "pred")
        self.assertEqual(matches[0]["b"], "food")

    def test_distance_and_analogy(self):
        grid = self.make_grid_graph()
        chem = self.make_chem_graph()
        self.assertGreater(grid.distance(chem), 0.0)

        pattern = GraphPattern(grid.entities(), grid.relations(), name="danger_near_resource", source_domain="grid")
        mapping = chem.analogize(pattern)
        self.assertTrue(mapping.is_useful)
        self.assertIn("pred", mapping.entity_map)
        self.assertIn("food", mapping.entity_map)

    def test_constraint(self):
        def no_more_than_two_entities(before, after, transformation):
            return 1.0 if len(after.entities()) > 2 else 0.0

        g = self.make_grid_graph()
        g2 = g.snapshot().add_entity(Entity("extra", "THING", {}))
        c = Constraint("max_two", "test", no_more_than_two_entities, hard=True)
        self.assertEqual(c.check(g, g, Transformation("noop", "test", "TEST")), 0.0)
        self.assertGreater(c.check(g, g2, Transformation("add", "test", "TRANSFORM")), 0.0)


class MemoryTests(unittest.TestCase):
    def make_pattern_graphs(self):
        grid = RealityGraph("grid")
        grid.add_entity(Entity("pred", "THREAT", {}))
        grid.add_entity(Entity("food", "RESOURCE", {}))
        grid.add_relation(Relation("pred", "NEAR", "food"))

        chem = RealityGraph("chem")
        chem.add_entity(Entity("tox", "TOXIC_GROUP", {}))
        chem.add_entity(Entity("site", "BINDING_SITE", {}))
        chem.add_relation(Relation("tox", "ADJACENT_TO", "site"))
        return grid, chem

    def test_episode_prediction_and_pattern_transfer(self):
        grid, chem = self.make_pattern_graphs()
        memory = MoteMemory()
        tr = Transformation("avoid", "grid", "MOVE_AWAY", base_cost=1.0)
        cons = Consequence(reward=5.0, concept_signals={"DANGER": 1.0}, explanation={"why": "avoided threat"})

        memory.record_episode(grid, tr, cons, predicted=0.0, domain="grid", tick=1)
        self.assertEqual(len(memory.episodic), 1)
        self.assertGreater(memory.episodic.action_value("avoid"), 0.0)
        self.assertEqual(len(memory.patterns), 1)

        transfers = memory.transfer_patterns_to(chem)
        self.assertTrue(transfers)
        self.assertTrue(transfers[0][1].is_useful)

    def test_cultural_memory(self):
        archive = CulturalMemory(capacity_per_domain=2)
        archive.write("chem", {"concept": "GOOD", "token": "lum"}, fitness=6.0)
        archive.write("chem", {"concept": "BAD", "token": "ka"}, fitness=7.0)
        archive.write("chem", {"concept": "GOOD", "token": "mi"}, fitness=8.0)
        self.assertEqual(len(archive.query("chem")), 2)
        self.assertEqual(archive.query("chem")[0]["token"], "mi")
        self.assertEqual(len(archive.query("chem", concept="GOOD")), 1)


class SpeechTests(unittest.TestCase):
    def test_lexicon_teaching_interpretation_and_repair(self):
        lx = Lexicon()
        lx.teach("ka", "DANGER", strength=0.8)
        self.assertEqual(lx.top_concept("ka"), "DANGER")
        interp = lx.interpret(["ka"])
        self.assertEqual(max(interp, key=interp.get), "DANGER")

        # Repair pushes token toward intended concept.
        lx.teach("lum", "GOOD", strength=0.5)
        before = lx.weight("lum", "BAD")
        lx.apply_repair(["lum"], "BAD", lr=0.5)
        self.assertGreater(lx.weight("lum", "BAD"), before)

    def test_speech_compose_receive_audit(self):
        speaker = SpeechOrgan(1)
        listener = SpeechOrgan(2)
        speaker.teach("ka", "DANGER", strength=0.8)
        listener.teach("ka", "DANGER", strength=0.8)

        utt = speaker.compose(
            intent="DANGER",
            neighbors=[2],
            mote_state={
                "energy": 50,
                "fitness": 5,
                "nearest_threat": 3.0,
                "position": [1.0, 2.0],
                "neediest_neighbor_id": 2,
            },
            domain="grid",
            tick=1,
            info_delta=5.0,
        )
        self.assertIsNotNone(utt)
        concepts = listener.receive(utt)
        self.assertEqual(max(concepts, key=concepts.get), "DANGER")
        listener.record_action_outcome(utt, "MOVE_AWAY", aligned=True, outcome="GOOD")
        self.assertGreaterEqual(listener.audit.semantic_success_rate(), 0.5)

    def test_repair_utterance(self):
        speaker = SpeechOrgan(1)
        speaker.teach("no", "DENY", strength=0.8)
        speaker.teach("ka", "DANGER", strength=0.8)
        original = Utterance(["ka"], 1, 2, "DANGER", [0, 0], 1.0, 50.0, domain="grid", tick=1)
        repair = speaker.fire_repair(original, listener_id=2, tick=2)
        self.assertIsNotNone(repair)
        self.assertTrue(repair.is_repair)
        self.assertEqual(repair.target_id, 2)


class WorldInterfaceTests(unittest.TestCase):
    def test_tiny_rule_world_four_function_contract(self):
        g = RealityGraph("tiny_rules")
        g.add_entity(Entity("fact_a", "FACT", {"truth": True}))
        g.add_entity(Entity("fact_b", "FACT", {"truth": True}))
        g.add_relation(Relation("fact_a", "IMPLIES", "fact_b"))
        world = TinyRuleWorld()

        obs = world.observe(g, "fact_a")
        self.assertEqual(len(obs.entities()), 2)
        actions = world.valid_actions(obs, {})
        self.assertEqual({a.universal_op for a in actions}, {"TRANSFORM", "VERIFY"})
        after, cons = world.act(g, actions[0], {})
        self.assertTrue(cons.valid)
        self.assertGreater(cons.net, 0)
        self.assertIsNotNone(after.get_entity("fact_b_known"))
        self.assertGreater(world.evaluate(after, {}), world.evaluate(g, {}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
