"""Tests for Phase F2 experiment runners."""
import tempfile
import unittest
from pathlib import Path


class TestPhaseF2Imports(unittest.TestCase):
    def test_import_role_balanced(self):
        import tais_core.experiments.runners.phase_f2.role_balanced_curriculum
        self.assertTrue(hasattr(tais_core.experiments.runners.phase_f2.role_balanced_curriculum, "run_experiment"))

    def test_import_repair_convergence(self):
        import tais_core.experiments.runners.phase_f2.repair_convergence
        self.assertTrue(hasattr(tais_core.experiments.runners.phase_f2.repair_convergence, "simulate_agents"))

    def test_import_domain_count_scaling(self):
        import tais_core.experiments.runners.phase_f2.domain_count_scaling
        self.assertTrue(hasattr(tais_core.experiments.runners.phase_f2.domain_count_scaling, "build_suite"))

    def test_import_grid_logic_replication(self):
        import tais_core.experiments.runners.phase_f2.grid_logic_1000_replication
        self.assertTrue(hasattr(tais_core.experiments.runners.phase_f2.grid_logic_1000_replication, "run_experiment"))

    def test_import_figure_generator(self):
        import tais_core.experiments.runners.phase_f2.generate_paper_figures
        self.assertTrue(hasattr(tais_core.experiments.runners.phase_f2.generate_paper_figures, "fig1_role_balanced"))


class TestPhaseF2Smoke(unittest.TestCase):
    def test_role_balanced_smoke(self):
        from tais_core.experiments.runners.phase_f2.role_balanced_curriculum import run_experiment
        results = run_experiment(seeds=2, pretrain_ticks=2, eval_ticks=3, verbose=False)
        self.assertIn("fresh", results)
        self.assertIn("role_balanced", results)
        self.assertEqual(len(results["fresh"].fresh), 2)

    def test_repair_convergence_smoke(self):
        from tais_core.experiments.runners.phase_f2.repair_convergence import simulate_agents
        enabled = simulate_agents(seeds=2, ticks=5, colony_size=3, repair_enabled=True, verbose=False)
        self.assertIn("lexicon_divergence", enabled)
        self.assertEqual(len(enabled["tick"]), 5)

    def test_repair_convergence_disabled_smoke(self):
        from tais_core.experiments.runners.phase_f2.repair_convergence import simulate_agents
        disabled = simulate_agents(seeds=2, ticks=5, colony_size=3, repair_enabled=False, verbose=False)
        self.assertIn("lexicon_divergence", disabled)
        self.assertEqual(len(disabled["tick"]), 5)

    def test_domain_count_scaling_smoke(self):
        from tais_core.experiments.runners.phase_f2.domain_count_scaling import build_suite
        suite = build_suite(seeds=2, eval_ticks=5, pretrain_ticks=2)
        results = suite.run()
        self.assertIn("fresh", results.records)
        self.assertIn("five_grid_rules_chem_hazard_sequences", results.records)
        self.assertEqual(len(results.records["fresh"]), 2)

    def test_grid_logic_replication_smoke(self):
        from tais_core.experiments.runners.phase_f2.grid_logic_1000_replication import run_experiment
        results = run_experiment(seeds=2, pretrain_ticks=2, eval_ticks=3, verbose=False)
        self.assertIn("full", results)
        self.assertIn("no_prediction", results)
        self.assertEqual(len(results["full"].fresh), 2)

    def test_figure_non_destructive(self):
        import tais_core.experiments.runners.phase_f2.generate_paper_figures
        self.assertIsNotNone(tais_core.experiments.runners.phase_f2.generate_paper_figures)


class TestPhaseF2RoleBalancedStructure(unittest.TestCase):
    def test_all_conditions_present(self):
        from tais_core.experiments.runners.phase_f2.role_balanced_curriculum import run_experiment
        results = run_experiment(seeds=2, pretrain_ticks=2, eval_ticks=3, verbose=False)
        expected = {"fresh", "grid_standard", "danger_only", "approach_only", "role_balanced", "logic_same_domain"}
        self.assertEqual(set(results.keys()), expected)

    def test_metrics_present(self):
        from tais_core.experiments.runners.phase_f2.role_balanced_curriculum import run_experiment
        results = run_experiment(seeds=2, pretrain_ticks=2, eval_ticks=3, verbose=False)
        for cond_name in results:
            summary = results[cond_name].summary()
            self.assertIn("task_completion_rate", summary)
            self.assertIn("first_task_success_tick", summary)
            self.assertIn("reward", summary)


class TestPhaseF2Output(unittest.TestCase):
    def test_role_balanced_output(self):
        from tais_core.experiments.runners.phase_f2.role_balanced_curriculum import main as rb_main
        import sys
        tmp = tempfile.mkdtemp()
        try:
            old_argv = sys.argv
            out = Path(tmp) / "role_balanced_curriculum.txt"
            sys.argv = ["role_balanced_curriculum.py", "--seeds", "2", "--pretrain", "2", "--eval", "3", "--output", str(out)]
            try:
                rb_main()
            except SystemExit:
                pass
            self.assertTrue(out.exists())
            self.assertTrue((Path(tmp) / "role_balanced_curriculum.csv").exists())
            self.assertTrue((Path(tmp) / "role_balanced_curriculum.json").exists())
        finally:
            sys.argv = old_argv

    def test_grid_logic_output(self):
        from tais_core.experiments.runners.phase_f2.grid_logic_1000_replication import main as gl_main
        import sys
        tmp = tempfile.mkdtemp()
        try:
            old_argv = sys.argv
            out = Path(tmp) / "grid_logic_1000_replication.txt"
            sys.argv = ["grid_logic_1000_replication.py", "--seeds", "2", "--pretrain", "2", "--eval", "3", "--output", str(out)]
            try:
                gl_main()
            except SystemExit:
                pass
            self.assertTrue(out.exists())
            self.assertTrue((Path(tmp) / "grid_logic_1000_replication.csv").exists())
        finally:
            sys.argv = old_argv

    def test_domain_count_output(self):
        from tais_core.experiments.runners.phase_f2.domain_count_scaling import main as dc_main
        import sys
        tmp = tempfile.mkdtemp()
        try:
            old_argv = sys.argv
            sys.argv = ["domain_count_scaling.py", "--seeds", "2", "--eval", "5", "--pretrain", "2", "--output", tmp]
            try:
                dc_main()
            except SystemExit:
                pass
            d = Path(tmp)
            self.assertTrue((d / "domain_count_scaling.json").exists())
            self.assertTrue((d / "domain_count_scaling.csv").exists())
        finally:
            sys.argv = old_argv


if __name__ == "__main__":
    unittest.main()
