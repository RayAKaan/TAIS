"""test_core.py"""
from tais_core.reality import Entity, Relation, RealityGraph, GraphPattern, Transformation, Consequence
from tais_core.memory import MoteMemory
from tais_core.speech import SpeechOrgan


def build_grid_graph():
    g = RealityGraph("grid", "danger_food")
    g.add_entity(Entity("pred", "THREAT", {"kind": "predator"}))
    g.add_entity(Entity("food", "RESOURCE", {"kind": "food"}))
    g.add_relation(Relation("pred", "NEAR", "food"))
    return g


def build_chem_graph():
    g = RealityGraph("chem", "toxic_binding")
    g.add_entity(Entity("tox", "TOXIC_GROUP", {"kind": "nitro"}))
    g.add_entity(Entity("site", "BINDING_SITE", {"kind": "pocket"}))
    g.add_relation(Relation("tox", "ADJACENT_TO", "site"))
    return g


def main():
    g1 = build_grid_graph()
    g2 = g1.snapshot()
    g2.update_entity("food", value=10)
    delta = g1.diff(g2)
    assert delta.magnitude == 1
    assert g1.distance(g2) == 0.0  # same structure; property diff not in distance

    pattern = GraphPattern(g1.entities(), g1.relations(), name="danger_near_resource", source_domain="grid")
    chem = build_chem_graph()
    analogy = chem.analogize(pattern)
    print("analogy", analogy.confidence, analogy.explanation, analogy.entity_map)
    assert analogy.confidence > 0

    mem = MoteMemory()
    tr = Transformation("avoid_pattern", "grid", "MOVE_AWAY", base_cost=1.0)
    cons = Consequence(reward=5, concept_signals={"DANGER": 1.0}, explanation={"why": "avoided threat"})
    mem.record_episode(g1, tr, cons, predicted=0.0, domain="grid", tick=1)
    transfers = mem.transfer_patterns_to(chem)
    print("transfers", [(p.name, m.confidence) for p, m in transfers])
    assert transfers

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
    assert utt is not None
    interpreted = s2.receive(utt)
    print("utterance", utt.text, "top", max(interpreted, key=interpreted.get))
    s2.record_action_outcome(utt, "MOVE_AWAY", aligned=True, outcome="GOOD")
    print("speech stats", s2.stats()["semantic_success"])


if __name__ == "__main__":
    main()
