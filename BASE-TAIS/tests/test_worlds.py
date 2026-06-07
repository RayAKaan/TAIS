"""test_worlds.py — validate the three tiny worlds."""
from tais_core.reality import Entity, Relation, RealityGraph, Transformation
from tais_core.worlds import GridGraphWorld, SequencePredictionWorld, RuleSatisfactionWorld


def test_gridworld_basic():
    w = GridGraphWorld(5, 5)
    g = w.graph
    assert g.get_entity("agent") is not None
    assert len(g.entities("CELL")) == 25
    assert len(g.relations("RIGHT")) == 40  # 20 forward + 20 reverse (undirected)
    assert len(g.relations("ABOVE")) == 40  # 20 forward + 20 reverse (undirected)
    assert g.get_entity("food_0") is not None
    assert g.get_entity("threat_0") is not None


def test_gridworld_actions():
    w = GridGraphWorld(5, 5)
    g = w.graph
    actions = w.valid_actions(g, {})
    assert len(actions) >= 2
    for a in actions:
        assert a.universal_op == "MOVE_TOWARD"


def test_gridworld_act_move():
    w = GridGraphWorld(3, 3)
    g = w.graph
    for a in w.valid_actions(g, {}):
        if a.effects.get("dx") == 0 and a.effects.get("dy") == 1:
            g2, cons = w.act(g, a, {})
            agent = g2.get_entity("agent")
            assert agent.properties["x"] == 0
            assert agent.properties["y"] == 1
            return
    assert False, "No upward move found"


def test_gridworld_observe_reveals_nearby():
    w = GridGraphWorld(8, 8)
    g = w.graph
    obs = w.observe(g, None)
    assert "agent" in obs
    assert "cell_0_0" in obs
    assert "cell_2_0" in obs or "cell_0_2" in obs


def test_sequenceworld_basic():
    w = SequencePredictionWorld(["X", "Y", "Z"])
    g = w.graph
    assert g.get_entity("elt_0") is not None
    assert g.get_entity("elt_1") is not None
    assert g.get_entity("elt_2") is not None
    assert g.get_entity("marker") is not None
    assert g.get_relation("elt_0", "NEXT", "elt_1") is not None


def test_sequenceworld_predict_correct():
    w = SequencePredictionWorld(["A", "B", "C"], seed=42)
    g = w.graph
    actions = w.valid_actions(g, {})
    predict_a = [a for a in actions if a.effects.get("prediction") == "A"][0]
    g2, cons = w.act(g, predict_a, {})
    assert cons.reward > 0
    assert "CORRECT" in cons.concept_signals


def test_sequenceworld_predict_wrong():
    w = SequencePredictionWorld(["A", "B", "C"], seed=42)
    g = w.graph
    predict_z = Transformation("predict_Z", "sequence", "PREDICT", base_cost=0.5, effects={"prediction": "Z"})
    g2, cons = w.act(g, predict_z, {})
    assert cons.penalty > 0
    assert "WRONG" in cons.concept_signals


def test_sequenceworld_marker_advances():
    w = SequencePredictionWorld(["A", "B", "C"], seed=42)
    g = w.graph
    actions = w.valid_actions(g, {})
    for _ in range(5):
        g, _ = w.act(g, actions[0], {})
    marker_rels = g.relations("AT")
    assert len(marker_rels) == 1
    target = g.get_entity(marker_rels[0].target)
    assert target is not None


def test_ruleworld_basic():
    w = RuleSatisfactionWorld(seed=0)
    g = w.graph
    assert g.get_entity("r1") is not None
    assert g.get_entity("r2") is not None
    assert g.get_entity("r3") is not None


def test_ruleworld_propose():
    w = RuleSatisfactionWorld(seed=0)
    g = w.graph
    actions = w.valid_actions(g, {})
    propose_r1_true = [a for a in actions if a.effects.get("rule") == "r1" and a.effects.get("satisfies") is True][0]
    g2, cons = w.act(g, propose_r1_true, {})
    assert cons.valid
    assert len(g2.relations("SATISFIES")) == 1
    assert "COMPLIANCE" in cons.concept_signals


def test_ruleworld_propose_violation():
    w = RuleSatisfactionWorld(seed=0)
    g = w.graph
    propose_r1_false = Transformation("propose_r1_false", "rules", "TEST", base_cost=0.5, effects={"rule": "r1", "satisfies": False})
    g2, cons = w.act(g, propose_r1_false, {})
    assert len(g2.relations("VIOLATES")) == 1


def test_ruleworld_evaluate():
    w = RuleSatisfactionWorld(seed=0)
    g = w.graph
    # propose all rules satisfied
    for rid in ["r1", "r2", "r3"]:
        t = Transformation(f"propose_{rid}", "rules", "TEST", base_cost=0.5, effects={"rule": rid, "satisfies": True})
        g, _ = w.act(g, t, {})
    score = w.evaluate(g, {})
    assert score == 1.0


def main():
    test_gridworld_basic()
    print("✓ test_gridworld_basic")
    test_gridworld_actions()
    print("✓ test_gridworld_actions")
    test_gridworld_act_move()
    print("✓ test_gridworld_act_move")
    test_gridworld_observe_reveals_nearby()
    print("✓ test_gridworld_observe_reveals_nearby")
    test_sequenceworld_basic()
    print("✓ test_sequenceworld_basic")
    test_sequenceworld_predict_correct()
    print("✓ test_sequenceworld_predict_correct")
    test_sequenceworld_predict_wrong()
    print("✓ test_sequenceworld_predict_wrong")
    test_sequenceworld_marker_advances()
    print("✓ test_sequenceworld_marker_advances")
    test_ruleworld_basic()
    print("✓ test_ruleworld_basic")
    test_ruleworld_propose()
    print("✓ test_ruleworld_propose")
    test_ruleworld_propose_violation()
    print("✓ test_ruleworld_propose_violation")
    test_ruleworld_evaluate()
    print("✓ test_ruleworld_evaluate")
    print("\n✅ All world tests passed")


if __name__ == "__main__":
    main()
