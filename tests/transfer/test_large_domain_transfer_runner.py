"""Tests for Phase R4 large-domain transfer runner."""

from __future__ import annotations

import json
import math
import os
import tempfile
import unittest


class TestLargeDomainTransferRunner(unittest.TestCase):
    def test_import_runner(self):
        from tais_core.experiments.runners.phase_r import large_domain_transfer
        self.assertTrue(hasattr(large_domain_transfer, "run_experiment"))
        self.assertTrue(hasattr(large_domain_transfer, "TARGETS"))
        self.assertEqual(len(large_domain_transfer.TARGETS), 3)

    def test_2seed_smoke_completes(self):
        from tais_core.experiments.runners.phase_r.large_domain_transfer import (run_experiment,
                                                                CONDITIONS, TARGETS)
        results = run_experiment(seeds=2, pretrain_ticks=3, eval_ticks=5, verbose=False)
        self.assertEqual(len(results), 3)
        for target in TARGETS:
            self.assertIn(target, results)
            for cond in CONDITIONS:
                self.assertIn(cond, results[target])
                self.assertEqual(len(results[target][cond].values), 2)

    def test_output_files_created(self):
        from tais_core.experiments.runners.phase_r import large_domain_transfer as ldt
        results = ldt.run_experiment(seeds=2, pretrain_ticks=3, eval_ticks=5, verbose=False)
        with tempfile.TemporaryDirectory() as tmp:
            base = os.path.join(tmp, "test_r4")
            csv_path = base + ".csv"
            ldt.write_csv(results, csv_path)
            self.assertTrue(os.path.exists(csv_path))
            with open(csv_path) as f:
                content = f.read()
            self.assertIn("logic_large", content)
            self.assertIn("hazard_large", content)
            self.assertIn("rules_chain_long", content)
            json_path = base + ".json"
            ldt.write_json(results, json_path)
            self.assertTrue(os.path.exists(json_path))
            md_path = base + ".md"
            ldt.write_md(results, 2, 3, 5, md_path)
            self.assertTrue(os.path.exists(md_path))

    def test_json_contains_all_targets(self):
        from tais_core.experiments.runners.phase_r import large_domain_transfer as ldt
        results = ldt.run_experiment(seeds=2, pretrain_ticks=3, eval_ticks=5, verbose=False)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.json")
            ldt.write_json(results, path)
            with open(path) as f:
                data = json.load(f)
            self.assertIn("logic_large", data)
            self.assertIn("hazard_large", data)
            self.assertIn("rules_chain_long", data)
            self.assertIn("_meta", data)

    def test_summary_not_nan(self):
        from tais_core.experiments.runners.phase_r import large_domain_transfer as ldt
        results = ldt.run_experiment(seeds=3, pretrain_ticks=3, eval_ticks=5, verbose=False)
        for target in ldt.TARGETS:
            for cond in ldt.CONDITIONS:
                s = results[target][cond].summary()
                for key in ["first_task_success_tick", "task_completion_rate", "reward"]:
                    self.assertFalse(
                        math.isnan(s[key]["mean"]),
                        f"{target}/{cond}/{key} mean is NaN"
                    )


if __name__ == "__main__":
    unittest.main()
