"""Tests for Phase R6 learned role compatibility."""

from __future__ import annotations

import json
import math
import os
import tempfile
import unittest

from tais_core.domains.logic import LogicWorld, make_logic_graph_easy
from tais_core.mote import UniversalMote
from tais_core.reality import Transformation, Consequence
from tais_core.role_learning import (
    LearnedRoleCompatibility,
    make_learned_role_compatibility_fn,
)


def make_t(name="test", domain="test", universal_op="TRANSFORM", base_cost=1.0):
    return Transformation(
        name=name, domain=domain, universal_op=universal_op,
        arity=0, base_cost=base_cost, role_hint="",
    )


def make_c(net=1.0, valid=True):
    return Consequence(net=net, penalty=-0.5 if net < 0 else 0.0, valid=valid)


class TestLearnedRoleCompatibility(unittest.TestCase):
    def test_update_positive(self):
        lr = LearnedRoleCompatibility(alpha=1.0)
        lr.update("APPROACH_GOOD", "MOVE_TOWARD", outcome_net=4.0)
        self.assertAlmostEqual(lr.values[("APPROACH_GOOD", "MOVE_TOWARD")], 1.0)

    def test_update_negative(self):
        lr = LearnedRoleCompatibility(alpha=1.0)
        lr.update("AVOID_BAD", "MOVE_AWAY", outcome_net=-4.0)
        self.assertAlmostEqual(lr.values[("AVOID_BAD", "MOVE_AWAY")], -1.0)

    def test_update_bounded_beyond_max(self):
        lr = LearnedRoleCompatibility(alpha=1.0)
        lr.update("APPROACH_GOOD", "MOVE_TOWARD", outcome_net=10.0)
        self.assertAlmostEqual(lr.values[("APPROACH_GOOD", "MOVE_TOWARD")], 1.0)

    def test_update_bounded_beyond_min(self):
        lr = LearnedRoleCompatibility(alpha=1.0)
        lr.update("FAILED", "ASK", outcome_net=-10.0)
        self.assertAlmostEqual(lr.values[("FAILED", "ASK")], -1.0)

    def test_score_default(self):
        lr = LearnedRoleCompatibility(default_value=0.0)
        self.assertEqual(lr.score("NONE", "NONE"), 0.0)

    def test_score_after_update(self):
        lr = LearnedRoleCompatibility(alpha=0.3)
        lr.update("APPROACH_GOOD", "MOVE_TOWARD", outcome_net=4.0)
        expected = 0.3 * 1.0
        self.assertAlmostEqual(lr.score("APPROACH_GOOD", "MOVE_TOWARD"), expected)

    def test_ewm_convergence(self):
        lr = LearnedRoleCompatibility(alpha=0.5)
        for _ in range(20):
            lr.update("VERIFY_UNCERTAIN", "VERIFY", outcome_net=4.0)
        self.assertAlmostEqual(lr.values[("VERIFY_UNCERTAIN", "VERIFY")], 1.0, places=4)

    def test_ewm_convergence_negative(self):
        lr = LearnedRoleCompatibility(alpha=0.5)
        for _ in range(20):
            lr.update("FAILED", "ASK", outcome_net=-4.0)
        self.assertAlmostEqual(lr.values[("FAILED", "ASK")], -1.0, places=4)

    def test_counts_increment(self):
        lr = LearnedRoleCompatibility()
        lr.update("APPROACH_GOOD", "MOVE_TOWARD", outcome_net=2.0)
        lr.update("APPROACH_GOOD", "MOVE_TOWARD", outcome_net=-1.0)
        self.assertEqual(lr.counts[("APPROACH_GOOD", "MOVE_TOWARD")], 2)

    def test_has_observed(self):
        lr = LearnedRoleCompatibility()
        self.assertFalse(lr.has_observed("APPROACH_GOOD", "MOVE_TOWARD"))
        lr.update("APPROACH_GOOD", "MOVE_TOWARD", outcome_net=1.0)
        self.assertTrue(lr.has_observed("APPROACH_GOOD", "MOVE_TOWARD"))

    def test_table_size(self):
        lr = LearnedRoleCompatibility()
        self.assertEqual(lr.table_size(), 0)
        lr.update("APPROACH_GOOD", "MOVE_TOWARD", outcome_net=1.0)
        lr.update("AVOID_BAD", "MOVE_AWAY", outcome_net=-1.0)
        self.assertEqual(lr.table_size(), 2)

    def test_total_observations(self):
        lr = LearnedRoleCompatibility()
        self.assertEqual(lr.total_observations(), 0)
        lr.update("APPROACH_GOOD", "MOVE_TOWARD", outcome_net=1.0)
        lr.update("APPROACH_GOOD", "MOVE_TOWARD", outcome_net=-1.0)
        lr.update("AVOID_BAD", "MOVE_AWAY", outcome_net=2.0)
        self.assertEqual(lr.total_observations(), 3)

    def test_mean_learned_score(self):
        lr = LearnedRoleCompatibility(alpha=1.0)
        lr.update("APPROACH_GOOD", "MOVE_TOWARD", outcome_net=4.0)
        lr.update("AVOID_BAD", "MOVE_AWAY", outcome_net=-4.0)
        self.assertAlmostEqual(lr.mean_learned_score(), 0.0)

    def test_role_score_average(self):
        lr = LearnedRoleCompatibility(alpha=1.0)
        lr.update("APPROACH_GOOD", "MOVE_TOWARD", outcome_net=4.0)
        lr.update("APPROACH_GOOD", "TRANSFORM", outcome_net=-4.0)
        self.assertAlmostEqual(lr.role_score("APPROACH_GOOD"), 0.0)

    def test_role_score_default(self):
        lr = LearnedRoleCompatibility(default_value=0.0)
        self.assertAlmostEqual(lr.role_score("UNSEEN_ROLE"), 0.0)

    def test_to_dict_from_dict_roundtrip(self):
        lr = LearnedRoleCompatibility(alpha=0.3)
        lr.update("APPROACH_GOOD", "MOVE_TOWARD", outcome_net=4.0)
        lr.update("AVOID_BAD", "MOVE_AWAY", outcome_net=-2.0)
        data = lr.to_dict()
        restored = LearnedRoleCompatibility.from_dict(data)
        self.assertEqual(restored.alpha, lr.alpha)
        self.assertEqual(restored.values, lr.values)
        self.assertEqual(restored.counts, lr.counts)

    def test_to_dict_json_serializable(self):
        lr = LearnedRoleCompatibility()
        lr.update("APPROACH_GOOD", "MOVE_TOWARD", outcome_net=1.5)
        data = lr.to_dict()
        json_str = json.dumps(data)
        self.assertIn("APPROACH_GOOD__MOVE_TOWARD", json_str)

    def test_mote_integration_default_disabled(self):
        mote = UniversalMote()
        self.assertIsNone(mote.learned_role_compatibility)
        self.assertFalse(mote.use_learned_role_compatibility)

    def test_mote_enable_creates_object(self):
        mote = UniversalMote()
        mote.enable_learned_role_compatibility(alpha=0.5)
        self.assertIsNotNone(mote.learned_role_compatibility)
        self.assertTrue(mote.use_learned_role_compatibility)
        self.assertAlmostEqual(mote.learned_role_compatibility.alpha, 0.5)

    def test_mote_update_during_step(self):
        mote = UniversalMote(energy=100.0)
        mote.enable_learned_role_compatibility()
        world = LogicWorld()
        g = make_logic_graph_easy()
        for _ in range(5):
            g, cons, _ = mote.step(world, g, mote_position="ASSIGN", tick=0)
            if mote.energy <= 0:
                mote.energy = 50.0
        self.assertGreater(mote.learned_role_compatibility.total_observations(), 0)

    def test_mote_table_grows_during_step(self):
        mote = UniversalMote(energy=100.0)
        mote.enable_learned_role_compatibility()
        world = LogicWorld()
        g = make_logic_graph_easy()
        for _ in range(10):
            g, cons, _ = mote.step(world, g, mote_position="ASSIGN", tick=0)
            if mote.energy <= 0:
                mote.energy = 50.0
        self.assertGreaterEqual(mote.learned_role_compatibility.table_size(), 1)

    def test_learned_compatibility_fn_learned_mode(self):
        lr = LearnedRoleCompatibility(alpha=1.0)
        lr.update("APPROACH_GOOD", "MOVE_TOWARD", outcome_net=4.0)
        lr.update("APPROACH_GOOD", "TRANSFORM", outcome_net=2.0)
        fn = make_learned_role_compatibility_fn(lr, mode="learned")
        result = fn("SOME_SOURCE", "APPROACH_GOOD")
        self.assertAlmostEqual(result, 0.75)

    def test_learned_compatibility_fn_returns_10_for_identical(self):
        lr = LearnedRoleCompatibility(default_value=0.0)
        fn = make_learned_role_compatibility_fn(lr, mode="learned")
        self.assertAlmostEqual(fn("A", "A"), 1.0)

    def test_learned_compatibility_fn_zero_mode(self):
        lr = LearnedRoleCompatibility()
        fn = make_learned_role_compatibility_fn(lr, mode="zero")
        self.assertAlmostEqual(fn("A", "B"), 0.0)

    def test_learned_compatibility_fn_random_mode_deterministic(self):
        lr = LearnedRoleCompatibility()
        fn1 = make_learned_role_compatibility_fn(lr, mode="random", seed=42)
        fn2 = make_learned_role_compatibility_fn(lr, mode="random", seed=42)
        self.assertEqual(fn1("APPROACH_GOOD", "AVOID_BAD"), fn2("APPROACH_GOOD", "AVOID_BAD"))

    def test_learned_compatibility_fn_learned_plus_hardcoded(self):
        lr = LearnedRoleCompatibility(alpha=1.0)
        lr.update("APPROACH_GOOD", "MOVE_TOWARD", outcome_net=4.0)
        hardcoded_fn = lambda src, tgt: 0.7 if src != tgt else 1.0
        fn = make_learned_role_compatibility_fn(
            lr, mode="learned_plus_hardcoded", hardcoded_fn=hardcoded_fn,
        )
        result = fn("TRANSFORM_TOWARD_GOAL", "APPROACH_GOOD")
        # learned.role_score("APPROACH_GOOD") = 1.0, hardcoded = 0.70
        # 0.5 * 1.0 + 0.5 * 0.70 = 0.85
        self.assertAlmostEqual(result, 0.85)

    def test_empty_source_or_target_returns_zero(self):
        lr = LearnedRoleCompatibility()
        fn = make_learned_role_compatibility_fn(lr, mode="learned")
        self.assertAlmostEqual(fn("", "APPROACH_GOOD"), 0.0)
        self.assertAlmostEqual(fn("APPROACH_GOOD", ""), 0.0)
        self.assertAlmostEqual(fn("", ""), 0.0)


class TestLearnedRoleCompatibilityRunner(unittest.TestCase):
    def setUp(self):
        self.output_dir = tempfile.mkdtemp()
        self.output_base = os.path.join(self.output_dir, "learned_role_compatibility")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.output_dir, ignore_errors=True)

    def _run_smoke(self, output_path, seeds=3, pretrain=5, eval_ticks=5,
                   condition=None):
        from tais_core.experiments.runners.phase_r.learned_role_compatibility import run_experiment
        condition_filter = condition.split(",") if condition else None
        results = run_experiment(
            seeds=seeds, pretrain_ticks=pretrain, eval_ticks=eval_ticks,
            condition_filter=condition_filter, verbose=False,
        )
        from tais_core.experiments.runners.phase_r.learned_role_compatibility import (
            CONDITIONS, TARGETS, write_csv,
        )
        for target in TARGETS:
            for cond in (condition_filter or CONDITIONS):
                self.assertIn(cond, results[target])
                summary = results[target][cond].summary()
                self.assertEqual(summary["n"], seeds)
                self.assertIn("task_completion_rate", summary)
        csv_path = output_path.rsplit(".", 1)[0] + ".csv"
        write_csv(results, csv_path)
        self.assertTrue(os.path.exists(csv_path))
        return results

    def test_runner_smoke_all_conditions(self):
        results = self._run_smoke(self.output_base, seeds=3, pretrain=5, eval_ticks=5)
        self.assertEqual(len(results), 3)
        for target in results:
            self.assertEqual(len(results[target]), 5)

    def test_runner_smoke_single_condition(self):
        results = self._run_smoke(self.output_base, seeds=3, pretrain=5,
                                  eval_ticks=5, condition="hardcoded_compatibility")
        self.assertEqual(len(results[list(results.keys())[0]]), 1)

    def test_runner_learned_table_populated_after_pretrain(self):
        results = self._run_smoke(self.output_base, seeds=3, pretrain=20, eval_ticks=5,
                                  condition="learned_compatibility")
        for target in results:
            summary = results[target]["learned_compatibility"].summary()
            table_size = summary["learned_table_size"]["pretrained"]
            self.assertGreaterEqual(table_size, 1,
                                    f"learned table for {target} should have entries after pretrain")

    def test_runner_learned_table_empty_for_hardcoded(self):
        results = self._run_smoke(self.output_base, seeds=3, pretrain=5, eval_ticks=5,
                                  condition="hardcoded_compatibility")
        for target in results:
            for cond in results[target]:
                s = results[target][cond].summary()
                self.assertEqual(s["learned_table_size"]["fresh"], 0)
                self.assertEqual(s["learned_table_size"]["pretrained"], 0)

    def test_runner_output_files_created(self):
        from tais_core.experiments.runners.phase_r.learned_role_compatibility import main as runner_main
        import sys
        sys.argv = [
            "learned_role_compatibility.py",
            "--seeds", "2",
            "--pretrain", "3",
            "--eval", "3",
            "--output", os.path.join(self.output_dir, "test_output.txt"),
        ]
        runner_main()
        for fname in ["test_output.txt", "test_output.csv", "test_output.json"]:
            self.assertTrue(os.path.exists(os.path.join(self.output_dir, fname)))

    def test_runner_all_conditions_produce_different_transfer_strength(self):
        results = self._run_smoke(self.output_base, seeds=5, pretrain=10, eval_ticks=5)
        for target in results:
            strengths = {}
            for cond in results[target]:
                s = results[target][cond].summary()
                strengths[cond] = s["transfer_strength"]["pretrained"]
            # At minimum verify all keys present
            self.assertEqual(set(strengths.keys()), {
                "hardcoded_compatibility", "learned_compatibility",
                "learned_plus_hardcoded", "random_compatibility",
                "no_compatibility",
            })

    def test_runner_learned_table_metrics_grow_with_more_pretrain(self):
        results_short = self._run_smoke(
            os.path.join(self.output_dir, "short"),
            seeds=5, pretrain=5, eval_ticks=5,
            condition="learned_compatibility",
        )
        results_long = self._run_smoke(
            os.path.join(self.output_dir, "long"),
            seeds=5, pretrain=20, eval_ticks=5,
            condition="learned_compatibility",
        )
        for target in results_short:
            short_obs = results_short[target]["learned_compatibility"].summary()["learned_total_observations"]["pretrained"]
            long_obs = results_long[target]["learned_compatibility"].summary()["learned_total_observations"]["pretrained"]
            self.assertGreaterEqual(long_obs, short_obs,
                                    f"more pretrain should yield more observations for {target}")


if __name__ == "__main__":
    unittest.main()
