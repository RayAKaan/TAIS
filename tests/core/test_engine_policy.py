"""Tests for Phase A engine selection policy."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tais_core.engine_policy import decide_engine_usage, EnginePolicyDecision
from tais_core.reality import Transformation


def make_action(name="a", op="MOVE_TOWARD", domain="test"):
    return Transformation(name, domain, op, base_cost=0.5)


class TestEnginePolicy:
    def test_sensorimotor_only_disables_all(self):
        actions = [
            make_action("move_toward", "MOVE_TOWARD"),
            make_action("move_away", "MOVE_AWAY"),
        ]
        d = decide_engine_usage(actions)
        assert not d.use_metacognition
        assert not d.use_causal_reasoning
        assert not d.use_planning
        assert "sensorimotor" in d.reason

    def test_symbolic_enables_all(self):
        actions = [
            make_action("verify", "VERIFY"),
            make_action("transform", "TRANSFORM"),
        ]
        d = decide_engine_usage(actions)
        assert d.use_metacognition
        assert d.use_causal_reasoning
        assert d.use_planning
        assert "symbolic" in d.reason

    def test_mixed_or_unknown_enables_metacog_only(self):
        """MUTATE is valid but not in SYMBOLIC_OPS or SENSORIMOTOR_OPS."""
        actions = [
            make_action("mutate", "MUTATE"),
            make_action("move_toward", "MOVE_TOWARD"),
        ]
        d = decide_engine_usage(actions)
        assert d.use_metacognition
        assert not d.use_causal_reasoning
        assert not d.use_planning

    def test_empty_actions_defaults_metacog(self):
        d = decide_engine_usage([])
        assert d.use_metacognition
        assert not d.use_causal_reasoning
        assert not d.use_planning

    def test_single_move_toward_disables_all(self):
        actions = [make_action("approach", "MOVE_TOWARD")]
        d = decide_engine_usage(actions)
        assert not d.use_metacognition
        assert not d.use_causal_reasoning
        assert not d.use_planning
