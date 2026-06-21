"""Tests for Phase A prediction calibration in PredictionEngine."""

import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tais_core.memory import PredictionEngine, MoteMemory
from tais_core.reality import Consequence, RealityGraph, Transformation


def make_t(name="test_op", domain="test_domain", universal_op="VERIFY",
           base_cost=0.5):
    return Transformation(name, domain, universal_op, base_cost=base_cost)


def make_c(net=1.0, valid=True):
    c = Consequence()
    if net >= 0:
        c.reward = net
        c.penalty = 0.0
    else:
        c.reward = 0.0
        c.penalty = -net
    c.valid = valid
    return c


class TestPredictionCalibration:
    def setup_method(self):
        self.engine = PredictionEngine()

    def test_calibrate_unseen_domain(self):
        raw = self.engine._calibrate(2.0, "never_seen")
        assert raw == 2.0

    def test_calibrate_large_reward_domain(self):
        self.engine._update_domain_scale("big", 5.0)
        result = self.engine._calibrate(2.0, "big")
        assert result == 2.0

    def test_calibrate_small_reward_domain(self):
        self.engine._update_domain_scale("tiny", 0.02)
        self.engine._update_domain_scale("tiny", 0.02)
        result = self.engine._calibrate(0.20, "tiny")
        assert result < 0.02

    def test_ewm_not_calibrated(self):
        t = make_t(domain="logic", base_cost=0.2)
        self.engine._update_domain_scale("logic", 0.02)
        self.engine.record_outcome(0.25, make_c(net=0.02), t, "logic")
        second = self.engine.predict(t, None, None)
        assert abs(second - 0.02) < 0.01

    def test_domain_error_finite(self):
        self.engine.record_outcome(0.25, make_c(net=0.02),
                                   make_t(domain="logic"), "logic")
        err = self.engine.domain_error("logic")
        assert err != float("inf")
        assert err > 0

    def test_should_explore_uses_domain_error(self):
        mem = MoteMemory()
        mem.prediction.record_outcome(0.25, make_c(net=0.02),
                                      make_t(domain="logic"), "logic")
        t = make_t()
        result = mem.should_explore([t], domain="logic")
        assert isinstance(result, bool)
