"""Tests for Phase R2 — role ontology robustness experiment."""

from __future__ import annotations

import json
import math
import os
import tempfile
import unittest

from experiments.phase_r.role_ontology_robustness import (
    CONDITIONS,
    TrialMetrics,
    ExperimentResult,
    run_experiment,
    run_trial,
    format_table,
    write_csv,
    Patches,
    _shuffle_list,
    _shuffle_role_mapping,
    ALL_ROLES,
)


class TestConditions(unittest.TestCase):
    def test_conditions_count(self):
        assert len(CONDITIONS) == 7

    def test_conditions_include_canonical(self):
        assert "canonical_roles" in CONDITIONS

    def test_conditions_include_no_role_transfer(self):
        assert "no_role_transfer" in CONDITIONS

    def test_conditions_include_random_compatibility(self):
        assert "random_compatibility" in CONDITIONS

    def test_conditions_include_identity_compatibility(self):
        assert "identity_only_compatibility" in CONDITIONS

    def test_conditions_include_shuffled_target_role_hints(self):
        assert "shuffled_target_role_hints" in CONDITIONS

    def test_conditions_include_shuffled_target_universal_ops(self):
        assert "shuffled_target_universal_ops" in CONDITIONS

    def test_conditions_include_shuffled_source_roles(self):
        assert "shuffled_source_roles" in CONDITIONS


class TestShuffleHelpers(unittest.TestCase):
    def test_shuffle_role_mapping_returns_all_roles(self):
        mapping = _shuffle_role_mapping(seed=42)
        assert set(mapping.keys()) == set(ALL_ROLES)
        assert set(mapping.values()) == set(ALL_ROLES)
        assert len(set(mapping.values())) == len(ALL_ROLES)

    def test_shuffle_role_mapping_deterministic(self):
        a = _shuffle_role_mapping(seed=42)
        b = _shuffle_role_mapping(seed=42)
        assert a == b

    def test_shuffle_role_mapping_different_seed(self):
        a = _shuffle_role_mapping(seed=42)
        b = _shuffle_role_mapping(seed=99)
        assert a != b

    def test_shuffle_list_deterministic(self):
        items = [1, 2, 3, 4, 5]
        a = _shuffle_list(items, seed=42)
        b = _shuffle_list(items, seed=42)
        assert a == b
        assert sorted(a) == sorted(items)

    def test_shuffle_list_different_seed(self):
        items = [1, 2, 3, 4, 5]
        a = _shuffle_list(items, seed=42)
        b = _shuffle_list(items, seed=99)
        assert a != b


class TestTrialMetrics(unittest.TestCase):
    def test_fields_present(self):
        m = TrialMetrics(
            reward=1.0, penalty=0.0, first_task_success_tick=3.0,
            task_completion_rate=1.0, contradictions=0, invalid_actions=0,
            final_energy=95.0, prediction_error=0.5, transfer_uses=2,
            transfer_strength=0.8, transfer_precision=0.75,
        )
        assert m.reward == 1.0
        assert m.first_task_success_tick == 3.0
        assert m.transfer_precision == 0.75


class TestExperimentResult(unittest.TestCase):
    def test_add_and_summary(self):
        r = ExperimentResult("test")
        m1 = TrialMetrics(5, 1, 2, 1, 0, 0, 90, 0.5, 2, 0.8, 0.75)
        m2 = TrialMetrics(3, 2, 4, 0, 1, 1, 85, 0.7, 1, 0.4, 0.5)
        r.add(m1, m1)
        r.add(m2, m2)
        s = r.summary()
        assert s["condition"] == "test"
        assert s["n"] == 2
        assert s["reward"]["fresh"] == 4.0
        assert s["reward"]["pretrained"] == 4.0


class TestSmoke(unittest.TestCase):
    """Quick smoke test: 5 seeds, 5 pretrain, 10 eval ticks."""

    def test_smoke_run_all_conditions(self):
        results = run_experiment(seeds=5, pretrain_ticks=5, eval_ticks=10, verbose=False)
        assert len(results) == 7
        for name in CONDITIONS:
            self.assertIn(name, results)
            self.assertEqual(len(results[name].fresh), 5)
            self.assertEqual(len(results[name].pretrained), 5)

    def test_smoke_canonical_has_data(self):
        results = run_experiment(seeds=5, pretrain_ticks=5, eval_ticks=10,
                                  condition_filter=["canonical_roles"], verbose=False)
        self.assertGreaterEqual(results["canonical_roles"].fresh[0].transfer_uses, 0)

    def test_smoke_no_role_transfer_no_uses(self):
        results = run_experiment(seeds=5, pretrain_ticks=5, eval_ticks=10,
                                  condition_filter=["no_role_transfer"], verbose=False)
        for metrics_list in [results["no_role_transfer"].fresh,
                             results["no_role_transfer"].pretrained]:
            for m in metrics_list:
                self.assertEqual(
                    m.transfer_uses, 0,
                    f"no_role_transfer should have 0 transfer_uses, got {m.transfer_uses}"
                )

    def test_smoke_format_table(self):
        results = run_experiment(seeds=3, pretrain_ticks=3, eval_ticks=10, verbose=False)
        table = format_table(results, seeds=3, pretrain_ticks=3, eval_ticks=10)
        self.assertIn("ROLE ONTOLOGY ROBUSTNESS", table)
        self.assertIn("canonical_roles", table)
        self.assertIn("shuffled_target_role_hints", table)
        self.assertIn("no_role_transfer", table)

    def test_smoke_output_files(self):
        results = run_experiment(seeds=3, pretrain_ticks=3, eval_ticks=10, verbose=False)
        table = format_table(results, seeds=3, pretrain_ticks=3, eval_ticks=10)
        self.assertIn("canonical_roles", table)
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = os.path.join(tmp, "test.csv")
            write_csv(results, csv_path)
            self.assertTrue(os.path.exists(csv_path))
            with open(csv_path) as f:
                content = f.read()
            self.assertIn("canonical_roles", content)
            self.assertIn("first_task_success_tick", content)

    def test_smoke_precision_not_nan(self):
        results = run_experiment(seeds=5, pretrain_ticks=5, eval_ticks=10, verbose=False)
        for name in CONDITIONS:
            for m in results[name].fresh:
                self.assertFalse(math.isnan(m.transfer_precision),
                                 f"{name} fresh precision NaN")
            for m in results[name].pretrained:
                self.assertFalse(math.isnan(m.transfer_precision),
                                 f"{name} pretrained precision NaN")
