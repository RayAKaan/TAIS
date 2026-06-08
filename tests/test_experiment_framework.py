"""Tests for the TAIS experiment framework."""
import json
import os
import tempfile
import unittest
from pathlib import Path


class TestMetrics(unittest.TestCase):
    def test_mean(self):
        from tais_core.experiments.metrics import mean
        self.assertEqual(mean([1, 2, 3]), 2.0)
        self.assertEqual(mean([]), 0.0)

    def test_std(self):
        from tais_core.experiments.metrics import std
        s = std([1, 2, 3])
        self.assertGreater(s, 0)

    def test_cohens_d_paired_negative(self):
        from tais_core.experiments.metrics import cohens_d_paired
        d = cohens_d_paired([1, 2, 3], [5, 3, 4])
        self.assertLess(d, 0)

    def test_paired_ttest_valid_p(self):
        from tais_core.experiments.metrics import paired_ttest
        t, p = paired_ttest([1, 2, 3], [2, 3, 4])
        self.assertGreaterEqual(p, 0)
        self.assertLessEqual(p, 1)

    def test_summarize_paired_keys(self):
        from tais_core.experiments.metrics import summarize_paired
        result = summarize_paired([2, 3, 4], [1, 2, 3])
        for key in ("baseline", "condition", "delta", "p", "d"):
            self.assertIn(key, result)


class TestCondition(unittest.TestCase):
    def test_fresh_is_fresh(self):
        from tais_core.experiments import Condition
        c = Condition("fresh")
        self.assertTrue(c.is_fresh())

    def test_pretrained_is_not_fresh(self):
        from tais_core.experiments import Condition
        c = Condition("grid", pretrain_domains=["gridworld"])
        self.assertFalse(c.is_fresh())

    def test_to_dict(self):
        from tais_core.experiments import Condition
        c = Condition("test", pretrain_domains=["grid"], engines={"metacognition": True})
        d = c.to_dict()
        self.assertEqual(d["name"], "test")
        self.assertEqual(d["pretrain_domains"], ["grid"])
        self.assertEqual(d["engines"], {"metacognition": True})


class TestProvenance(unittest.TestCase):
    def test_capture_provenance_returns_dict(self):
        from tais_core.experiments.provenance import capture_provenance
        prov = capture_provenance("test", {"seeds": 2})
        self.assertIsInstance(prov, dict)
        self.assertIn("timestamp_utc", prov)
        self.assertIn("python", prov)
        self.assertIn("parameters", prov)
        self.assertEqual(prov["parameters"]["seeds"], 2)


class TestExperimentResults(unittest.TestCase):
    def setUp(self):
        from tais_core.experiments import Condition, TrialRecord, ExperimentResults, Metric
        self.results = ExperimentResults(
            name="test_results",
            baseline_condition="fresh",
            metrics=[
                Metric("first_task_success_tick", lower_is_better=True),
                Metric("reward"),
            ],
        )
        for seed in range(3):
            self.results.add_record(TrialRecord(
                seed=seed, condition="fresh",
                metrics={"first_task_success_tick": 12.0, "reward": 1.0},
            ))
            self.results.add_record(TrialRecord(
                seed=seed, condition="grid_only",
                metrics={"first_task_success_tick": 8.0, "reward": 3.0},
            ))

    def test_paired_summary_works(self):
        summary = self.results.paired_summary("grid_only", "first_task_success_tick")
        self.assertIn("baseline", summary)
        self.assertIn("delta", summary)
        self.assertEqual(summary["baseline"], 12.0)
        self.assertEqual(summary["condition"], 8.0)
        self.assertEqual(summary["delta"], -4.0)

    def test_mismatched_seeds_raises(self):
        from tais_core.experiments import TrialRecord
        self.results.add_record(TrialRecord(
            seed=99, condition="grid_only",
            metrics={"first_task_success_tick": 5.0, "reward": 5.0},
        ))
        with self.assertRaises(ValueError):
            self.results.paired_summary("grid_only", "first_task_success_tick")

    def test_save_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.json"
            self.results.save_json(path)
            self.assertTrue(path.exists())
            data = json.loads(path.read_text())
            self.assertEqual(data["name"], "test_results")

    def test_save_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.csv"
            self.results.save_csv(path)
            self.assertTrue(path.exists())
            content = path.read_text()
            self.assertIn("condition,metric", content)


class TestExperimentReport(unittest.TestCase):
    def setUp(self):
        from tais_core.experiments import TrialRecord, ExperimentResults, Metric
        self.results = ExperimentResults(
            name="test_report",
            baseline_condition="fresh",
            metrics=[Metric("first_task_success_tick", lower_is_better=True)],
        )
        for seed in range(2):
            self.results.add_record(TrialRecord(
                seed=seed, condition="fresh",
                metrics={"first_task_success_tick": 12.0},
            ))
            self.results.add_record(TrialRecord(
                seed=seed, condition="grid_only",
                metrics={"first_task_success_tick": 8.0},
            ))

    def test_markdown_contains_name(self):
        from tais_core.experiments import ExperimentReport
        report = ExperimentReport(self.results)
        md = report.markdown()
        self.assertIn("test_report", md)

    def test_latex_contains_tabular(self):
        from tais_core.experiments import ExperimentReport
        report = ExperimentReport(self.results)
        latex = report.latex_table()
        self.assertIn("tabular", latex)
        self.assertIn("grid_only", latex)


class TestExperimentSuiteSmoke(unittest.TestCase):
    def test_tiny_suite_runs(self):
        from tais_core.experiments import Condition, ExperimentSuite, Metric
        suite = ExperimentSuite(
            name="test_grid_to_logic_smoke",
            seeds=3,
            conditions=[
                Condition("fresh", pretrain_domains=[]),
                Condition("grid_only", pretrain_domains=["gridworld"]),
            ],
            eval_domain="logic",
            eval_ticks=5,
            pretrain_ticks=3,
            metrics=[
                Metric("first_task_success_tick", lower_is_better=True),
                Metric("task_completion_rate"),
            ],
        )
        results = suite.run()
        self.assertIn("fresh", results.records)
        self.assertIn("grid_only", results.records)
        self.assertEqual(len(results.records["fresh"]), 3)

    def test_tiny_suite_with_output(self):
        from tais_core.experiments import Condition, ExperimentSuite, Metric
        suite = ExperimentSuite(
            name="test_output_suite",
            seeds=2,
            conditions=[
                Condition("fresh", pretrain_domains=[]),
                Condition("grid_only", pretrain_domains=["gridworld"]),
            ],
            eval_domain="logic",
            eval_ticks=5,
            pretrain_ticks=3,
            metrics=[
                Metric("first_task_success_tick", lower_is_better=True),
                Metric("task_completion_rate"),
            ],
        )
        with tempfile.TemporaryDirectory() as tmp:
            results = suite.run(output_dir=tmp)
            d = Path(tmp)
            self.assertTrue((d / "test_output_suite.json").exists())
            self.assertTrue((d / "test_output_suite.csv").exists())
            self.assertTrue((d / "test_output_suite.md").exists())
            self.assertTrue((d / "test_output_suite.tex").exists())


if __name__ == "__main__":
    unittest.main()
