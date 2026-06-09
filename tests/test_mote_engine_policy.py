"""Integration tests: mote with engine policy in GridWorld and RuleWorld."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tais_core.mote import UniversalMote
from tais_core.domains.gridworld import GridGraphWorld, make_grid_graph
from tais_core.domains.rules import RuleWorld, make_rule_graph


def test_gridworld_mote_with_policy():
    """Mote in GridWorld (sensorimotor+verify) should still work with policy."""
    world = GridGraphWorld()
    mote = UniversalMote(energy=100.0)
    mote.enable_cognitive_engines(metacognition=True, causal_reasoning=True, hierarchical_planning=True)
    mote.use_engine_policy = True
    g = make_grid_graph()
    for t in range(10):
        g, cons, action = mote.step(world, g, tick=t)
    assert mote.energy > 0


def test_ruleworld_mote_with_policy():
    """Mote in RuleWorld (VERIFY, TRANSFORM) should have engines active."""
    world = RuleWorld()
    mote = UniversalMote(energy=100.0)
    mote.enable_cognitive_engines(metacognition=True, causal_reasoning=True, hierarchical_planning=True)
    mote.use_engine_policy = True
    g = make_rule_graph()
    for t in range(10):
        g, cons, action = mote.step(world, g, tick=t)
    assert mote._engine_policy is not None
    assert mote._engine_policy.use_metacognition
