from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tais_core import load_domain, UniversalMote
from tais_core.viz import (
    compute_pairwise_lexicon_agreement,
    graph_snapshot_dict,
    heatmap_from_summary_rows,
    normalize_summary_for_radar,
    plot_lexicon_convergence,
    plot_radar_chart,
    plot_scaling_curve,
    plot_transfer_heatmap,
    record_mote_trajectory,
    save_trajectory_html,
    save_trajectory_json,
)


class TestVizCommon(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())


class TestPlotTransferHeatmap(TestVizCommon):
    def test_writes_png(self):
        matrix = [[0.5, -0.3], [0.0, 0.8]]
        row_labels = ["A", "B"]
        col_labels = ["X", "Y"]
        out = self.tmp / "heatmap.png"
        result = plot_transfer_heatmap(matrix, row_labels, col_labels, output=str(out))
        self.assertTrue(out.exists())
        self.assertGreater(out.stat().st_size, 100)

    def test_heatmap_from_summary_rows(self):
        rows = [
            {"condition": "cond_a", "metric": "success", "d": "0.5"},
            {"condition": "cond_b", "metric": "success", "d": "-0.3"},
            {"condition": "cond_a", "metric": "other", "d": "0.1"},
        ]
        matrix, row_labels, col_labels = heatmap_from_summary_rows(
            rows, ["cond_a", "cond_b"], metric="success", value_key="d"
        )
        self.assertEqual(len(matrix), 2)
        self.assertEqual(len(matrix[0]), 1)
        self.assertAlmostEqual(matrix[0][0], 0.5)
        self.assertAlmostEqual(matrix[1][0], -0.3)

    def test_heatmap_missing_condition_defaults_zero(self):
        rows = [
            {"condition": "cond_a", "metric": "success", "d": "0.5"},
        ]
        matrix, _, _ = heatmap_from_summary_rows(
            rows, ["cond_a", "missing"], metric="success", value_key="d"
        )
        self.assertAlmostEqual(matrix[0][0], 0.5)
        self.assertAlmostEqual(matrix[1][0], 0.0)


class TestPlotRadarChart(TestVizCommon):
    def test_writes_png(self):
        series = {
            "A": {"m1": 0.8, "m2": 0.3},
            "B": {"m1": 0.2, "m2": 0.9},
        }
        out = self.tmp / "radar.png"
        result = plot_radar_chart(series, ["m1", "m2"], output=str(out))
        self.assertTrue(out.exists())
        self.assertGreater(out.stat().st_size, 100)

    def test_normalize_summary_for_radar(self):
        rows = [
            {"condition": "cond_a", "metric": "m1", "condition_value": "10"},
            {"condition": "cond_b", "metric": "m1", "condition_value": "20"},
            {"condition": "cond_a", "metric": "m2", "condition_value": "5"},
            {"condition": "cond_b", "metric": "m2", "condition_value": "1"},
        ]
        series = normalize_summary_for_radar(
            rows, ["cond_a", "cond_b"], ["m1", "m2"],
            lower_is_better={"m2"},
        )
        self.assertIn("cond_a", series)
        self.assertIn("cond_b", series)
        self.assertAlmostEqual(series["cond_a"]["m1"], 0.0)
        self.assertAlmostEqual(series["cond_b"]["m1"], 1.0)
        self.assertAlmostEqual(series["cond_a"]["m2"], 0.0)
        self.assertAlmostEqual(series["cond_b"]["m2"], 1.0)

    def test_normalize_lower_is_better(self):
        rows = [
            {"condition": "cond_a", "metric": "error", "condition_value": "10"},
            {"condition": "cond_b", "metric": "error", "condition_value": "30"},
        ]
        series = normalize_summary_for_radar(
            rows, ["cond_a", "cond_b"], ["error"],
            lower_is_better={"error"},
        )
        self.assertAlmostEqual(series["cond_a"]["error"], 1.0)
        self.assertAlmostEqual(series["cond_b"]["error"], 0.0)


class TestPlotScalingCurve(TestVizCommon):
    def test_writes_png(self):
        out = self.tmp / "scaling.png"
        result = plot_scaling_curve(
            [1, 2, 3], [0.1, 0.5, 0.9],
            xlabel="X", ylabel="Y", title="Test", output=str(out),
        )
        self.assertTrue(out.exists())
        self.assertGreater(out.stat().st_size, 100)


class TestLexicon(TestVizCommon):
    def test_compute_pairwise_lexicon_agreement_identical(self):
        lexicons = [
            {"a": "cat", "b": "dog"},
            {"a": "cat", "b": "dog"},
            {"a": "cat", "b": "dog"},
        ]
        agreement = compute_pairwise_lexicon_agreement(lexicons)
        self.assertAlmostEqual(agreement, 1.0)

    def test_compute_pairwise_lexicon_agreement_disjoint(self):
        lexicons = [
            {"a": "cat"},
            {"b": "dog"},
        ]
        agreement = compute_pairwise_lexicon_agreement(lexicons)
        self.assertEqual(agreement, 0.0)

    def test_compute_pairwise_lexicon_agreement_empty(self):
        self.assertEqual(compute_pairwise_lexicon_agreement([]), 0.0)
        self.assertEqual(compute_pairwise_lexicon_agreement([{"a": "x"}]), 0.0)

    def test_plot_lexicon_convergence_writes_png(self):
        out = self.tmp / "lexicon.png"
        result = plot_lexicon_convergence(
            [0, 1, 2], [0.0, 0.5, 0.8],
            output=str(out),
        )
        self.assertTrue(out.exists())
        self.assertGreater(out.stat().st_size, 100)


class TestTrajectory(TestVizCommon):
    def test_record_mote_trajectory_records_at_least_one_tick(self):
        try:
            world = load_domain("chemistry_lite")
        except Exception as e:
            self.skipTest(f"chemistry_lite not loadable: {e}")
        graph = world.initial_graph()
        mote = UniversalMote(energy=100)
        records = record_mote_trajectory(world, graph, mote, mote_position="atom_c", ticks=5)
        self.assertGreaterEqual(len(records), 1)
        self.assertIn("tick", records[0])
        self.assertIn("action", records[0])
        self.assertIn("net", records[0])
        self.assertIn("graph", records[0])

    def test_save_trajectory_json(self):
        records = [{"tick": 0, "action": "test", "net": 1.0, "graph": {"entities": [], "relations": []}}]
        out = self.tmp / "traj.json"
        save_trajectory_json(records, str(out))
        self.assertTrue(out.exists())
        with open(out) as f:
            data = json.load(f)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["action"], "test")

    def test_save_trajectory_html(self):
        records = [{"tick": 0, "action": "test", "net": 1.0, "graph": {"entities": [], "relations": []}}]
        out = self.tmp / "traj.html"
        save_trajectory_html(records, str(out), title="TAIS Mote Trajectory")
        self.assertTrue(out.exists())
        content = out.read_text(encoding="utf-8")
        self.assertIn("TAIS Mote Trajectory", content)

    def test_graph_snapshot_dict(self):
        from tais_core import RealityGraph, Entity, Relation
        g = RealityGraph(domain="test")
        g.add_entity(Entity(id="e1", etype="TEST", properties={"x": 1}))
        g.add_relation(Relation(source="e1", rtype="connects", target="e1", directed=False))
        snap = graph_snapshot_dict(g)
        self.assertIn("entities", snap)
        self.assertIn("relations", snap)
        self.assertEqual(len(snap["entities"]), 1)
        self.assertEqual(snap["entities"][0]["id"], "e1")


if __name__ == "__main__":
    unittest.main()
