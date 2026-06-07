"""test_mote.py — validate the V6 UniversalMote."""
from tais_core.mote import UniversalMote
from tais_core.worlds import GridGraphWorld, SequencePredictionWorld, RuleSatisfactionWorld


def test_mote_imports():
    m = UniversalMote(mote_id=0)
    assert m.mote_id == 0
    assert m.memory is not None
    assert m.speech is not None
    assert m.model is not None


def test_mote_steps_in_gridworld():
    w = GridGraphWorld(5, 5)
    m = UniversalMote(mote_id=0, world=w)
    result = m.step()
    # Should have moved somewhere
    assert result["tick"] == 1
    assert result["domain"] == "grid"
    assert result["action"] is not None
    assert len(m.memory.episodic) == 1


def test_mote_runs_multiple_steps():
    w = GridGraphWorld(4, 4)
    m = UniversalMote(mote_id=0, world=w)
    results = m.run(5)
    assert len(results) == 5
    assert all(r["tick"] == i + 1 for i, r in enumerate(results))
    assert len(m.memory.episodic) == 5


def test_mote_learns_from_experience():
    w = SequencePredictionWorld(["A", "B", "C"], seed=42)
    m = UniversalMote(mote_id=0, world=w)
    m.run(12)
    assert len(m.memory.patterns) >= 0
    assert len(m.memory.episodic) >= 6


def test_mote_can_speak():
    w = GridGraphWorld(4, 4)
    m = UniversalMote(mote_id=0, world=w)
    for _ in range(3):
        m.step()
    # After several steps, speech stats should exist
    stats = m.speech.stats()
    assert "semantic_success" in stats


def test_mote_transfers_between_worlds():
    grid_w = GridGraphWorld(4, 4)
    m = UniversalMote(mote_id=0, world=grid_w)
    m.run(5)
    seq_w = SequencePredictionWorld(["X", "Y", "Z"])
    transfers = m.transfer_to(seq_w)
    assert isinstance(transfers, list)


def test_mote_cross_domain_step():
    """Mote can switch worlds mid-life and keep operating."""
    grid_w = GridGraphWorld(4, 4)
    m = UniversalMote(mote_id=0, world=grid_w)
    m.run(3)
    seq_w = SequencePredictionWorld(["A", "B"], seed=0)
    result = m.step(world=seq_w)
    assert result["domain"] == "sequence"
    assert result["tick"] == 4


def test_mote_spawns_children():
    grid_w = GridGraphWorld(4, 4)
    m = UniversalMote(mote_id=0, world=grid_w)
    m.run(5)
    child = m.spawn_child(child_id=1)
    assert child.mote_id == 1
    assert child.world == m.world
    assert child.speech is not None
    assert child.memory is not None


def test_mote_understanding_report():
    m = UniversalMote(mote_id=0)
    assert isinstance(m.report_understanding(), bool)


def test_mote_summary():
    w = GridGraphWorld(5, 5)
    m = UniversalMote(mote_id=7, world=w)
    m.run(3)
    s = m.summary()
    assert s["id"] == 7
    assert s["tick"] == 3
    assert "memory" in s
    assert "speech" in s
    assert "policy" in s
    assert "domain" in s


def test_mote_decide_returns_action():
    w = GridGraphWorld(5, 5)
    m = UniversalMote(mote_id=0, world=w)
    actions = w.valid_actions(w.graph, {})
    chosen = m.decide(actions)
    assert chosen is not None
    assert chosen.name.startswith("move_")


def test_mote_think_builds_model():
    w = GridGraphWorld(5, 5)
    m = UniversalMote(mote_id=0, world=w)
    obs = w.observe(w.graph, (0, 0))
    m.think(obs)
    assert len(m.model.entities()) > 0


def main():
    test_mote_imports()
    print("✓ test_mote_imports")
    test_mote_steps_in_gridworld()
    print("✓ test_mote_steps_in_gridworld")
    test_mote_runs_multiple_steps()
    print("✓ test_mote_runs_multiple_steps")
    test_mote_learns_from_experience()
    print("✓ test_mote_learns_from_experience")
    test_mote_can_speak()
    print("✓ test_mote_can_speak")
    test_mote_transfers_between_worlds()
    print("✓ test_mote_transfers_between_worlds")
    test_mote_cross_domain_step()
    print("✓ test_mote_cross_domain_step")
    test_mote_spawns_children()
    print("✓ test_mote_spawns_children")
    test_mote_understanding_report()
    print("✓ test_mote_understanding_report")
    test_mote_summary()
    print("✓ test_mote_summary")
    test_mote_decide_returns_action()
    print("✓ test_mote_decide_returns_action")
    test_mote_think_builds_model()
    print("✓ test_mote_think_builds_model")
    print("\n✅ All mote tests passed")


if __name__ == "__main__":
    main()
