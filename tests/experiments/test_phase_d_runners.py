"""Tests for Phase D experiment runners."""
import tempfile
import unittest
from pathlib import Path


class TestPhaseDImports(unittest.TestCase):
    def test_import_composition(self):
        import tais_core.experiments.runners.phase_d.composition
        self.assertTrue(hasattr(tais_core.experiments.runners.phase_d.composition, "build_suite"))

    def test_import_scaling_law(self):
        import tais_core.experiments.runners.phase_d.scaling_law
        self.assertTrue(hasattr(tais_core.experiments.runners.phase_d.scaling_law, "build_suite_domain_count"))

    def test_import_reverse_transfer(self):
        import tais_core.experiments.runners.phase_d.reverse_transfer
        self.assertTrue(hasattr(tais_core.experiments.runners.phase_d.reverse_transfer, "run_trial"))

    def test_import_curriculum(self):
        import tais_core.experiments.runners.phase_d.curriculum
        self.assertTrue(hasattr(tais_core.experiments.runners.phase_d.curriculum, "build_suite"))

    def test_import_cognitive_contribution(self):
        import tais_core.experiments.runners.phase_d.cognitive_contribution
        self.assertTrue(hasattr(tais_core.experiments.runners.phase_d.cognitive_contribution, "build_suite"))


class TestPhaseDSmoke(unittest.TestCase):
    def test_composition_smoke(self):
        from tais_core.experiments.runners.phase_d.composition import build_suite
        suite = build_suite(seeds=2, eval_ticks=5, pretrain_ticks=2)
        results = suite.run()
        self.assertIn("fresh", results.records)
        self.assertIn("grid_only", results.records)
        self.assertEqual(len(results.records["fresh"]), 2)

    def test_scaling_domain_count_smoke(self):
        from tais_core.experiments.runners.phase_d.scaling_law import build_suite_domain_count
        suite = build_suite_domain_count(seeds=2, eval_ticks=5, pretrain_ticks=2)
        results = suite.run()
        self.assertIn("fresh", results.records)

    def test_scaling_horizon_smoke(self):
        from tais_core.experiments.runners.phase_d.scaling_law import build_suite_horizon
        suite = build_suite_horizon(seeds=2, eval_ticks=5)
        results = suite.run()
        self.assertIn("fresh", results.records)
        self.assertIn("grid_h5", results.records)
        self.assertIn("grid_h100", results.records)

    def test_curriculum_smoke(self):
        from tais_core.experiments.runners.phase_d.curriculum import build_suite
        suite = build_suite(seeds=2, eval_ticks=5, pretrain_ticks=2)
        results = suite.run()
        self.assertIn("fresh", results.records)
        self.assertIn("grid_rules_chem", results.records)

    def test_cognitive_contribution_smoke(self):
        from tais_core.experiments.runners.phase_d.cognitive_contribution import build_suite
        suite = build_suite(seeds=2, eval_ticks=5, pretrain_ticks=2)
        results = suite.run()
        self.assertIn("fresh", results.records)
        self.assertIn("grid_all_engines", results.records)

    def test_reverse_transfer_trial(self):
        from tais_core.experiments.runners.phase_d.reverse_transfer import run_trial
        metrics = run_trial("fresh_grid_eval", [], 0, seed=42)
        self.assertIn("first_task_success_tick", metrics)
        self.assertIn("task_completion_rate", metrics)
        self.assertIsInstance(metrics["reward"], float)


class TestPhaseDOutput(unittest.TestCase):
    def test_composition_output(self):
        from tais_core.experiments.runners.phase_d.composition import build_suite
        suite = build_suite(seeds=2, eval_ticks=5, pretrain_ticks=2)
        with tempfile.TemporaryDirectory() as tmp:
            suite.run(output_dir=tmp)
            d = Path(tmp)
            self.assertTrue((d / "composition.json").exists())
            self.assertTrue((d / "composition.csv").exists())
            self.assertTrue((d / "composition.md").exists())
            self.assertTrue((d / "composition.tex").exists())

    def test_curriculum_output(self):
        from tais_core.experiments.runners.phase_d.curriculum import build_suite
        suite = build_suite(seeds=2, eval_ticks=5, pretrain_ticks=2)
        with tempfile.TemporaryDirectory() as tmp:
            suite.run(output_dir=tmp)
            d = Path(tmp)
            self.assertTrue((d / "curriculum.json").exists())

    def test_cognitive_output(self):
        from tais_core.experiments.runners.phase_d.cognitive_contribution import build_suite
        suite = build_suite(seeds=2, eval_ticks=5, pretrain_ticks=2)
        with tempfile.TemporaryDirectory() as tmp:
            suite.run(output_dir=tmp)
            d = Path(tmp)
            self.assertTrue((d / "cognitive_contribution.json").exists())

    def test_scaling_output(self):
        from tais_core.experiments.runners.phase_d.scaling_law import build_suite_domain_count
        suite = build_suite_domain_count(seeds=2, eval_ticks=5, pretrain_ticks=2)
        with tempfile.TemporaryDirectory() as tmp:
            suite.run(output_dir=tmp)
            d = Path(tmp)
            self.assertTrue((d / "domain_count.json").exists())

    def test_reverse_transfer_output(self):
        from tais_core.experiments.runners.phase_d.reverse_transfer import main as rt_main
        import sys
        tmp = tempfile.mkdtemp()
        try:
            old_argv = sys.argv
            sys.argv = ["reverse_transfer.py", "--seeds", "2", "--output", tmp]
            try:
                rt_main()
            except SystemExit:
                pass
            d = Path(tmp)
            self.assertTrue((d / "reverse_transfer.json").exists())
            self.assertTrue((d / "reverse_transfer.csv").exists())
        finally:
            sys.argv = old_argv


if __name__ == "__main__":
    unittest.main()
