"""Phase 5 tests for LogicWorld.

Pin the contract LogicWorld must satisfy so the transfer experiment can
trust it the way the runner trusts RuleWorld v2 and HazardGraphWorld.
"""

import random
import unittest

from tais_core.domains import (
    LogicWorld,
    LogicWorldChain,
    LogicWorldUnsat,
    make_logic_graph_easy,
    make_logic_graph_chain,
    make_logic_graph_unsat,
)
from tais_core.domains.logic import (
    SAT_REWARD,
    PROGRESS_REWARD,
    CONTRADICTION_PENALTY,
    CHECK_CONSISTENCY_REWARD,
    RETRACT_RECOVERY_REWARD,
)
from tais_core.mote import UniversalMote
from tais_core.reality import Transformation


ASSERT  = Transformation("assert_literal",    "logic", "TRANSFORM", base_cost=0.3, role_hint="APPROACH_GOOD")
RETRACT = Transformation("retract_literal",   "logic", "MUTATE",    base_cost=0.3, role_hint="REPAIR_MISMATCH")
CHECK   = Transformation("check_consistency", "logic", "VERIFY",    base_cost=0.2, role_hint="VERIFY_UNCERTAIN")
RANDOM  = Transformation("random_assert",     "logic", "MUTATE",    base_cost=0.3)


def _values(graph) -> dict:
    a = graph.get_entity("ASSIGN")
    return dict(a.get("values", {})) if a else {}


def _solved(graph) -> bool:
    a = graph.get_entity("ASSIGN")
    return bool(a and a.get("solved"))


class LogicWorldEasyTests(unittest.TestCase):
    def setUp(self):
        self.world = LogicWorld()
        self.graph = make_logic_graph_easy()

    def test_target_marker_present(self):
        tgt = self.graph.get_entity("TARGET")
        self.assertIsNotNone(tgt)
        self.assertEqual(tgt.get("derive_id"), "formula_easy")

    def test_initial_state_empty_unsolved(self):
        self.assertEqual(_values(self.graph), {})
        self.assertFalse(_solved(self.graph))
        # All 3 clauses unsatisfied initially.
        self.assertEqual(self.world._satisfied_count(self.graph), 0)
        # eval = 0 (no clauses satisfied, no contradiction).
        self.assertEqual(self.world.evaluate(self.graph, {}), 0.0)

    def test_check_consistency_is_passive(self):
        g2, cons = self.world.act(self.graph, CHECK, {})
        self.assertEqual(cons.reward, CHECK_CONSISTENCY_REWARD)
        self.assertIsNone(cons.task_signal)
        # graph unchanged
        self.assertEqual(_values(g2), {})

    def test_assert_literal_makes_progress(self):
        """The first assert should pick a useful variable (asserting x2=True
        satisfies C1 and C3 in one go)."""
        g2, cons = self.world.act(self.graph, ASSERT, {})
        self.assertIn(cons.task_signal, ("TASK_PROGRESS", "TASK_SUCCESS"))
        self.assertGreater(self.world._satisfied_count(g2), 0)

    def test_assert_then_assert_solves_easy_formula(self):
        """Two greedy asserts must solve the easy 3-clause formula."""
        g = self.graph
        for step in range(3):
            g, cons = self.world.act(g, ASSERT, {})
            if cons.task_signal == "TASK_SUCCESS":
                self.assertEqual(cons.reward, SAT_REWARD)
                self.assertTrue(_solved(g))
                self.assertEqual(self.world.evaluate(g, {}), 10.0)
                return
        self.fail("Easy formula should solve in <= 3 asserts; did not.")

    def test_check_spam_cannot_match_one_solve(self):
        """Regression guard mirroring RuleWorld Phase 2 + Hazard Phase 4:
        100 check_consistency calls must pay strictly less reward than
        one TASK_SUCCESS solve."""
        total = 0.0
        for _ in range(100):
            _, cons = self.world.act(self.graph, CHECK, {})
            total += cons.reward
        self.assertLess(total, SAT_REWARD,
            f"check_consistency spam ({total:.2f}) must not exceed one SAT solve "
            f"({SAT_REWARD}); calibration regression")

    def test_random_assert_emits_TASK_FAILURE(self):
        random.seed(0)
        _, cons = self.world.act(self.graph, RANDOM, {})
        self.assertEqual(cons.task_signal, "TASK_FAILURE")
        self.assertTrue(cons.penalty > 0)


class LogicWorldChainTests(unittest.TestCase):
    def setUp(self):
        self.world = LogicWorldChain()
        self.graph = make_logic_graph_chain()

    def test_chain_requires_at_least_two_asserts_to_solve(self):
        """Chain has 4 clauses; solving requires multiple correct asserts."""
        g = self.graph
        signals = []
        for _ in range(6):
            g, cons = self.world.act(g, ASSERT, {})
            signals.append(cons.task_signal)
            if cons.task_signal == "TASK_SUCCESS":
                break
        # Must have seen at least one progress before success.
        self.assertIn("TASK_PROGRESS", signals,
            f"chain didn't show any progress steps: {signals}")
        # And eventually a success.
        self.assertIn("TASK_SUCCESS", signals,
            f"chain didn't solve in 6 asserts: {signals}")


class LogicWorldUnsatTests(unittest.TestCase):
    def test_unsat_eventually_contradicts(self):
        """The unsat formula (x) ∧ (¬x) must produce a TASK_FAILURE
        once we've assigned x either way."""
        world = LogicWorldUnsat()
        g = make_logic_graph_unsat()
        # Force an assertion of x1.
        g2, cons = world.act(g, ASSERT, {})
        # In the unsat formula, asserting x1=True satisfies C1 but contradicts C2;
        # asserting x1=False satisfies C2 but contradicts C1. Either way contradiction.
        self.assertEqual(cons.task_signal, "TASK_FAILURE")
        self.assertEqual(cons.penalty, CONTRADICTION_PENALTY)


class LogicWorldUniversalMoteIntegration(unittest.TestCase):
    def test_fresh_mote_can_solve_easy_formula_a_meaningful_fraction(self):
        """LogicWorld is harder than RuleWorld/Hazard. We require >= 30%
        completion at h=15 to leave headroom; observed baseline is ~47%."""
        world = LogicWorld()
        hits = 0
        seeds = 30
        for s in range(seeds):
            random.seed(10_000 + s)
            mote = UniversalMote(energy=100.0)
            g = make_logic_graph_easy()
            for t in range(15):
                g, cons, _ = mote.step(world, g, mote_position="ASSIGN", tick=t)
                if cons.task_signal == "TASK_SUCCESS":
                    hits += 1; break
                if mote.energy <= 0: mote.energy = 50.0
        self.assertGreaterEqual(hits, seeds * 3 // 10,
            f"fresh motes solved {hits}/{seeds}; calibration looks off")

    def test_mote_metrics_populate(self):
        random.seed(42)
        mote = UniversalMote(energy=100.0)
        world = LogicWorld(); g = make_logic_graph_easy()
        for t in range(10):
            g, _, _ = mote.step(world, g, mote_position="ASSIGN", tick=t)
            if mote.energy <= 0: mote.energy = 50.0
        m = mote.metrics()
        self.assertEqual(m["actions"], 10)
        self.assertIn("logic", m["domains"])
        self.assertIsNotNone(m["mean_prediction_error"])


if __name__ == "__main__":
    unittest.main()
