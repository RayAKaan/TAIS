from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .metrics import Metric, summarize_paired


@dataclass
class TrialRecord:
    seed: int
    condition: str
    metrics: Dict[str, float]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seed": self.seed,
            "condition": self.condition,
            "metrics": dict(self.metrics),
            "metadata": dict(self.metadata),
        }


@dataclass
class ExperimentResults:
    name: str
    baseline_condition: str
    metrics: List[Metric]
    records: Dict[str, List[TrialRecord]] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)

    def add_record(self, record: TrialRecord) -> None:
        self.records.setdefault(record.condition, []).append(record)

    def metric_values(self, condition: str, metric_name: str) -> List[float]:
        records = sorted(self.records.get(condition, []), key=lambda r: r.seed)
        return [r.metrics[metric_name] for r in records if metric_name in r.metrics]

    def paired_summary(self, condition: str, metric_name: str) -> Dict[str, float]:
        baseline_vals = self.metric_values(self.baseline_condition, metric_name)
        condition_vals = self.metric_values(condition, metric_name)
        if len(baseline_vals) != len(condition_vals):
            raise ValueError(
                f"Seed mismatch for {condition}/{metric_name}: "
                f"{len(baseline_vals)} baseline vs {len(condition_vals)} condition"
            )
        return summarize_paired(baseline_vals, condition_vals)

    def summary(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "name": self.name,
            "baseline_condition": self.baseline_condition,
            "conditions": {},
        }
        for cond_name in self.records:
            if cond_name == self.baseline_condition:
                continue
            cond_info: Dict[str, Any] = {}
            for metric in self.metrics:
                cond_info[metric.name] = self.paired_summary(cond_name, metric.name)
            result["conditions"][cond_name] = cond_info
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "baseline_condition": self.baseline_condition,
            "provenance": self.provenance,
            "n_seeds": max((len(v) for v in self.records.values()), default=0),
            "conditions": {k: [r.to_dict() for r in sorted(v, key=lambda x: x.seed)] for k, v in self.records.items()},
            "summary": self.summary(),
        }

    def save_json(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

    def save_csv(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        summary = self.summary()
        with open(p, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["condition", "metric", "baseline", "condition_value", "delta", "ci_low", "ci_high", "p", "d"])
            for cond_name, metrics_dict in summary["conditions"].items():
                for metric_name, vals in metrics_dict.items():
                    writer.writerow([
                        cond_name, metric_name,
                        vals["baseline"], vals["condition"],
                        vals["delta"], vals["ci_low"], vals["ci_high"],
                        vals["p"], vals["d"],
                    ])
