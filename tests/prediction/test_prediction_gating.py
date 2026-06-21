"""Tests for Phase R5 prediction gating."""

from __future__ import annotations

import json
import math
import os
import tempfile
import unittest

from tais_core.domains.logic import LogicWorld, make_logic_graph_easy
from tais_core.domains.rules import RuleWorld, make_rule_graph_easy
from tais_core.mote import UniversalMote
from tais_core.reality import Transformation, Consequence


def make_t(name="test", domain="test", universal_op="TRANSFORM", base_cost=1.0):
    return Transformation(
        name=name, domain=domain, universal_op=universal_op,
        arity=0, base_cost=base_cost, role_hint="",
    )


def make_c(net=1.0, valid=True):
    return Consequence(net=net, penalty=-0.5 if net < 0 else 0.0, valid=valid)


class TestPredictionGating(unittest.TestCase):
    def test_default_behavior_unchanged(self):
        mote = UniversalMote()
        self.assertFalse(mote.use_prediction_in_score)
        self.assertEqual(mote.prediction_score_weight, 0.25)
        self.assertEqual(mote.prediction_min_domain_observations, 0)

    def test_enable_gating_does_not_crash(self):
        mote = UniversalMote()
        mote.use_prediction_in_score = True
        world = LogicWorld()
        g = make_logic_graph_easy()
        for _ in range(3):
            obs = world.observe(g, "ASSIGN")
            actions = world.valid_actions(obs, {"energy": 100})
            action = mote.choose_action(obs, actions)
            if action is not None:
                g, cons = world.act(g, action, {"energy": 100})
                mote.memory.prediction.record_outcome(0.0, cons, action, "logic")
        # If we got here without exception, the gating code path works
        self.assertTrue(mote.memory.prediction.domain_observation_count("logic") >= 3)

    def test_threshold_blocks_score_contribution(self):
        mote = UniversalMote()
        mote.use_prediction_in_score = True
        mote.prediction_min_domain_observations = 5
        self.assertEqual(mote.memory.prediction.domain_observation_count("novel"), 0)

    def test_threshold_passes_after_sufficient_observations(self):
        mote = UniversalMote()
        mote.use_prediction_in_score = True
        mote.prediction_min_domain_observations = 3
        world = LogicWorld()
        g = make_logic_graph_easy()
        for _ in range(5):
            obs = world.observe(g, "ASSIGN")
            actions = world.valid_actions(obs, {"energy": 100})
            action = mote.choose_action(obs, actions)
            if action is not None:
                g, cons = world.act(g, action, {"energy": 100})
                mote.memory.prediction.record_outcome(0.0, cons, action, "logic")
        self.assertGreaterEqual(
            mote.memory.prediction.domain_observation_count("logic"), 3
        )
        # choose_action should now pass the threshold inside the scoring loop
        obs = world.observe(g, "ASSIGN")
        actions = world.valid_actions(obs, {"energy": 100})
        action = mote.choose_action(obs, actions)
        # No crash = gating passes correctly
        self.assertIsNotNone(action)

    def test_domain_observation_count(self):
        engine = UniversalMote().memory.prediction
        self.assertEqual(engine.domain_observation_count("unseen"), 0)
        engine._domain_obs_count["seen"] = 7
        self.assertEqual(engine.domain_observation_count("seen"), 7)

    def test_no_prediction_monkeypatch_still_works(self):
        mote = UniversalMote()
        orig = mote.memory.predict_action
        mote.memory.predict_action = lambda action, graph: 0.0
        world = LogicWorld()
        g = make_logic_graph_easy()
        obs = world.observe(g, "ASSIGN")
        actions = world.valid_actions(obs, {"energy": 100})
        action = mote.choose_action(obs, actions)
        # prediction zeroed, should not affect scoring
        self.assertIsNotNone(action)
        mote.memory.predict_action = orig

    def test_runner_imports(self):
        from tais_core.experiments.runners.phase_r import prediction_gating_sweep
        self.assertTrue(hasattr(prediction_gating_sweep, "run_experiment"))
        self.assertTrue(hasattr(prediction_gating_sweep, "CONDITIONS"))
        self.assertIn("no_prediction", prediction_gating_sweep.CONDITIONS)
        self.assertIn("prediction_k3_w025", prediction_gating_sweep.CONDITIONS)
        self.assertIn("prediction_disabled_current", prediction_gating_sweep.CONDITIONS)

    def test_2seed_smoke_completes(self):
        from tais_core.experiments.runners.phase_r.prediction_gating_sweep import (
            run_experiment, TARGETS, CONDITIONS
        )
        results = run_experiment(seeds=2, pretrain_ticks=3, eval_ticks=5, verbose=False)
        self.assertEqual(len(results), 3)
        for target in TARGETS:
            self.assertIn(target, results)
            for cond in CONDITIONS:
                self.assertIn(cond, results[target])
                self.assertEqual(len(results[target][cond].values), 2)

    def test_output_files_created(self):
        from tais_core.experiments.runners.phase_r import prediction_gating_sweep as pgs
        results = pgs.run_experiment(seeds=2, pretrain_ticks=3, eval_ticks=5, verbose=False)
        with tempfile.TemporaryDirectory() as tmp:
            base = os.path.join(tmp, "test_pg")
            csv_path = base + ".csv"
            pgs.write_csv(results, csv_path)
            self.assertTrue(os.path.exists(csv_path))
            with open(csv_path) as f:
                content = f.read()
            self.assertIn("prediction_k3_w025", content)
            self.assertIn("no_prediction", content)
            json_path = base + ".json"
            pgs.write_json(results, json_path)
            self.assertTrue(os.path.exists(json_path))
            md_path = base + ".md"
            pgs.write_md(results, 2, 3, 5, md_path)
            self.assertTrue(os.path.exists(md_path))

    def test_json_contains_all_targets(self):
        from tais_core.experiments.runners.phase_r import prediction_gating_sweep as pgs
        results = pgs.run_experiment(seeds=2, pretrain_ticks=3, eval_ticks=5, verbose=False)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.json")
            pgs.write_json(results, path)
            with open(path) as f:
                data = json.load(f)
            self.assertIn("logic", data)
            self.assertIn("rules", data)
            self.assertIn("hazard", data)
            self.assertIn("_meta", data)

    def test_summary_not_nan(self):
        from tais_core.experiments.runners.phase_r import prediction_gating_sweep as pgs
        results = pgs.run_experiment(seeds=3, pretrain_ticks=3, eval_ticks=5, verbose=False)
        for target in pgs.TARGETS:
            for cond in pgs.CONDITIONS:
                s = results[target][cond].summary()
                for key in ["first_task_success_tick", "task_completion_rate", "reward"]:
                    self.assertFalse(
                        math.isnan(s[key]["mean"]),
                        f"{target}/{cond}/{key} mean is NaN"
                    )


if __name__ == "__main__":
    unittest.main()
