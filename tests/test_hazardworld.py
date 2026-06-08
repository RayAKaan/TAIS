"""Phase 4 tests for HazardGraphWorld.

Pin the contract HazardGraphWorld must satisfy so the runner / transfer
experiments can trust it the way they trust RuleWorld v2.

Coverage:
- TARGET marker present, evaluate() reflects it
- task_signal channel: TASK_SUCCESS on first exit, TASK_FAILURE on hazard,
  TASK_PROGRESS on resource, None on normal step / verify
- Exit re-step is near-neutral (does not re-emit TASK_SUCCESS)
- verify_node can't outpay one true exit by an order of magnitude
- approach_resource preferentially picks a RESOURCE/EXIT neighbor
- avoid_hazard preferentially picks a non-hazard, non-near-hazard neighbor
- UniversalMote can run a trial without architectural changes
"""

import random
import unittest

from tais_core.domains import (
    HazardGraphWorld,
    make_hazard_graph_easy,
    make_hazard_graph_distractor,
)
from tais_core.domains.hazard import (
    EXIT_REWARD_FIRST,
    HAZARD_PENALTY,
    RESOURCE_REWARD,
    VERIFY_REWARD,
)
from tais_core.mote import UniversalMote
from tais_core.reality import Transformation


VERIFY = Transformation("verify_node",       "hazard", "VERIFY",      base_cost=0.2)
APPROACH = Transformation("approach_resource", "hazard", "MOVE_TOWARD", base_cost=0.2, role_hint="APPROACH_GOOD")
AVOID = Transformation("avoid_hazard",       "hazard", "MOVE_AWAY",   base_cost=0.2, role_hint="AVOID_BAD")
MOVE = Transformation("move_to_neighbor",  "hazard", "MOVE_TOWARD", base_cost=0.2)


def _agent_at(graph) -> str:
    for _rel, ent in graph.neighbors_out("agent", "AT"):
        return ent.id
    return "?"


class HazardWorldEasyTests(unittest.TestCase):
    def setUp(self):
        self.world = HazardGraphWorld()
        self.graph = make_hazard_graph_easy()

    def test_target_marker_present(self):
        tgt = self.graph.get_entity("TARGET")
        self.assertIsNotNone(tgt)
        self.assertEqual(tgt.get("derive_id"), "E")

    def test_initial_position_is_start(self):
        self.assertEqual(_agent_at(self.graph), "S")
        self.assertEqual(self.world.evaluate(self.graph, {}), 1.0)

    def test_approach_resource_picks_resource_neighbor(self):
        """At A, the neighbors are S, R, H. approach_resource must pick R."""
        random.seed(0)
        # Move from S to A first.
        g2, _ = self.world.act(self.graph, MOVE, {})
        # Now from A, approach_resource should land on R.
        random.seed(0)
        g3, cons = self.world.act(g2, APPROACH, {})
        self.assertEqual(_agent_at(g3), "R")
        self.assertEqual(cons.task_signal, "TASK_PROGRESS")
        self.assertEqual(cons.reward, RESOURCE_REWARD)

    def test_avoid_hazard_does_not_pick_hazard_neighbor(self):
        """At A, neighbors are S, R, H. avoid_hazard must NOT pick H."""
        random.seed(0)
        g2, _ = self.world.act(self.graph, MOVE, {})  # at A
        # Repeat 10 times with different seeds: never land on H.
        for s in range(10):
            random.seed(s)
            g3, cons = self.world.act(g2, AVOID, {})
            self.assertNotEqual(_agent_at(g3), "H",
                                f"seed {s}: avoid_hazard chose H")
            self.assertNotEqual(cons.task_signal, "TASK_FAILURE")

    def test_reaching_exit_emits_TASK_SUCCESS(self):
        # Manually walk S -> A -> R -> E.
        random.seed(0)
        g = self.graph
        for _ in range(10):
            g_next, cons = self.world.act(g, APPROACH, {})
            if cons.task_signal == "TASK_SUCCESS":
                self.assertEqual(cons.reward, EXIT_REWARD_FIRST)
                self.assertEqual(_agent_at(g_next), "E")
                self.assertEqual(self.world.evaluate(g_next, {}), 10.0)
                return
            g = g_next
        self.fail("did not reach the exit within 10 approach_resource steps")

    def test_re_step_at_exit_does_not_re_emit_TASK_SUCCESS(self):
        random.seed(0)
        g = self.graph
        # Walk to E via APPROACH.
        for _ in range(10):
            g, cons = self.world.act(g, APPROACH, {})
            if cons.task_signal == "TASK_SUCCESS":
                break
        else:
            self.fail("did not reach exit")
        # Now any further action that lands on E again must not re-emit SUCCESS.
        # From E, neighbors are R only, so APPROACH bounces to R, then back.
        for _ in range(4):
            g, cons = self.world.act(g, APPROACH, {})
            self.assertNotEqual(cons.task_signal, "TASK_SUCCESS",
                                "TASK_SUCCESS re-emitted on subsequent visit")

    def test_hazard_step_emits_TASK_FAILURE(self):
        """Force a step into H by using move_to_neighbor with rigged RNG."""
        random.seed(0)
        g2, _ = self.world.act(self.graph, MOVE, {})  # at A
        # From A, neighbors are S, R, H. We want H. Try a few seeds.
        for s in range(20):
            random.seed(s)
            _, cons = self.world.act(g2, MOVE, {})
            if cons.task_signal == "TASK_FAILURE":
                self.assertEqual(cons.penalty, HAZARD_PENALTY)
                return
        self.fail("could not force a hazard step in 20 random seeds")

    def test_verify_cannot_outpay_one_true_exit(self):
        """Regression guard mirroring RuleWorld's Phase 2 verify-spam test.

        100 verifies must pay strictly less than one true TASK_SUCCESS.
        """
        total = 0.0
        for _ in range(100):
            _, cons = self.world.act(self.graph, VERIFY, {})
            total += cons.reward
        self.assertLess(total, EXIT_REWARD_FIRST,
                        f"verify spam ({total:.2f}) must not exceed one true exit "
                        f"({EXIT_REWARD_FIRST}); calibration regression")


class HazardWorldUniversalMoteIntegration(unittest.TestCase):
    """Validate the domain works with UniversalMote and zero mote-side changes."""

    def test_fresh_mote_can_solve_with_decent_probability(self):
        """Across 30 seeds, fresh motes should reach the exit a healthy fraction
        of the time within 15 ticks. We require >= 50% to leave headroom for
        future calibration changes without false-failing this test.
        """
        world = HazardGraphWorld()
        hits = 0
        seeds = 30
        for s in range(seeds):
            random.seed(10_000 + s)
            mote = UniversalMote(energy=100.0)
            g = make_hazard_graph_easy()
            for t in range(15):
                g, cons, _ = mote.step(world, g, mote_position="agent", tick=t)
                if cons.task_signal == "TASK_SUCCESS":
                    hits += 1
                    break
                if mote.energy <= 0:
                    mote.energy = 50.0
        self.assertGreaterEqual(hits, seeds // 2,
                                f"fresh motes solved {hits}/{seeds}; calibration looks off")

    def test_mote_metrics_populate_correctly(self):
        random.seed(42)
        mote = UniversalMote(energy=100.0)
        world = HazardGraphWorld()
        g = make_hazard_graph_easy()
        for t in range(10):
            g, _, _ = mote.step(world, g, mote_position="agent", tick=t)
            if mote.energy <= 0:
                mote.energy = 50.0
        m = mote.metrics()
        self.assertEqual(m["actions"], 10)
        self.assertIn("hazard", m["domains"])
        self.assertIsNotNone(m["mean_prediction_error"])


class HazardWorldDistractorTests(unittest.TestCase):
    def test_distractor_graph_has_two_hazards_two_resources(self):
        g = make_hazard_graph_distractor()
        self.assertEqual(len(g.entities("HAZARD_NODE")), 2)
        self.assertEqual(len(g.entities("RESOURCE_NODE")), 2)
        self.assertEqual(len(g.entities("EXIT_NODE")), 1)

    def test_distractor_target_is_exit(self):
        g = make_hazard_graph_distractor()
        tgt = g.get_entity("TARGET")
        self.assertEqual(tgt.get("derive_id"), "E")


if __name__ == "__main__":
    unittest.main()
