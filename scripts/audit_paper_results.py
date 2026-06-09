#!/usr/bin/env python3
"""Paper result audit script.

Scans the repo for paper-relevant result artifacts, checks
their existence, extracts key metrics from CSV/JSON when possible,
and produces a summary.

Usage:
    PYTHONPATH=. python scripts/audit_paper_results.py
    PYTHONPATH=. python scripts/audit_paper_results.py --output results/paper_locked/audit_summary.json --markdown results/paper_locked/audit_summary.md
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent


def get_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=REPO_ROOT, timeout=10,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


KNOWN_RESULTS = [
    {
        "id": "legacy_grid_logic",
        "phase": "Phase 5 legacy",
        "runner": "experiments/logic_transfer_runner.py",
        "artifact": "docs/PHASE5_LOGIC_TRANSFER_REPORT.md",
        "paper_status": "include_legacy_context",
        "notes": "Strong legacy Grid->Logic result; not directly comparable to F2.",
    },
    {
        "id": "legacy_grid_hazard",
        "phase": "Phase 4 legacy",
        "runner": "experiments/hazard_transfer_runner.py",
        "artifact": "docs/PHASE4_HAZARD_TRANSFER_REPORT.md",
        "paper_status": "include_as_asymmetric_transfer",
        "notes": "Caution transfer positive; task-speed negative.",
    },
    {
        "id": "phase_a_prediction_calibration",
        "phase": "Phase A paper readiness",
        "runner": "experiments/logic_transfer_runner.py",
        "artifact": "docs/PHASE_A_PREDICTION_CALIBRATION_REPORT.md",
        "paper_status": "include_limitations",
        "notes": "Prediction paradox reduced but not fully eliminated.",
    },
    {
        "id": "phase_a_engine_selection",
        "phase": "Phase A paper readiness",
        "runner": "experiments/phase_d/cognitive_contribution.py",
        "artifact": "docs/PHASE_A_ENGINE_SELECTION_REPORT.md",
        "paper_status": "appendix_or_exclude_paper1",
        "notes": "Engine policy implemented; not central to Paper 1.",
    },
    {
        "id": "phase_a_speech_token",
        "phase": "Phase A paper readiness",
        "runner": "experiments/speech_token_portability.py",
        "artifact": "docs/PHASE_A_SPEECH_TOKEN_PORTABILITY_REPORT.md",
        "paper_status": "exclude_paper1",
        "notes": "Null speech result; Paper 2 material.",
    },
    {
        "id": "phase_d_composition",
        "phase": "Phase D",
        "runner": "experiments/phase_d/composition.py",
        "artifact": "results/phase_d/composition/composition.csv",
        "paper_status": "appendix_or_context",
        "notes": "Framework protocol; do not mix with legacy table.",
    },
    {
        "id": "phase_d_curriculum",
        "phase": "Phase D",
        "runner": "experiments/phase_d/curriculum.py",
        "artifact": "results/phase_d/curriculum/curriculum.csv",
        "paper_status": "include_as_domain_diversity",
        "notes": "Strong 3-domain curriculum results.",
    },
    {
        "id": "phase_d_scaling",
        "phase": "Phase D",
        "runner": "experiments/phase_d/scaling_law.py",
        "artifact": "results/phase_d/scaling_law/scaling_summary.csv",
        "paper_status": "appendix",
        "notes": "Earlier scaling sweep.",
    },
    {
        "id": "phase_d_cognitive",
        "phase": "Phase D",
        "runner": "experiments/phase_d/cognitive_contribution.py",
        "artifact": "results/phase_d/cognitive_contribution/cognitive_contribution.csv",
        "paper_status": "exclude_paper1_or_limitations",
        "notes": "Cognitive engines hurt; Paper 3 material.",
    },
    {
        "id": "phase_f2_role_balanced",
        "phase": "Phase F2",
        "runner": "experiments/phase_f2/role_balanced_curriculum.py",
        "artifact": "results/phase_f2/role_balanced_curriculum.csv",
        "paper_status": "include_negative_result",
        "notes": "Role-balanced hypothesis failed; approach-only strongest.",
    },
    {
        "id": "phase_f2_domain_count",
        "phase": "Phase F2",
        "runner": "experiments/phase_f2/domain_count_scaling.py",
        "artifact": "results/phase_f2/domain_count_scaling.csv",
        "paper_status": "include_main",
        "notes": "Best current diversity evidence.",
    },
    {
        "id": "phase_f2_repair",
        "phase": "Phase F2",
        "runner": "experiments/phase_f2/repair_convergence.py",
        "artifact": "results/phase_f2/repair_convergence.json",
        "paper_status": "exclude_paper1",
        "notes": "Paper 2 material; modest divergence reduction.",
    },
    {
        "id": "phase_f2_grid_logic_1000",
        "phase": "Phase F2",
        "runner": "experiments/phase_f2/grid_logic_1000_replication.py",
        "artifact": "results/phase_f2/grid_logic_1000_replication.csv",
        "paper_status": "include_main",
        "notes": "Canonical current Grid->Logic replication.",
    },
]

METRICS_TO_EXTRACT = [
    "first_task_success_tick",
    "task_completion_rate",
    "hazard_steps",
    "transfer_precision",
    "transfer_uses",
]

PRIORITY_CONDITIONS = [
    "full",
    "grid_pretrain",
    "grid_standard",
    "approach_only",
    "role_balanced",
    "three_grid_rules_chem",
    "four_grid_rules_chem_hazard",
    "five_grid_rules_chem_hazard_sequences",
    "logic_pretrain",
    "no_action_role",
    "no_pattern_transfer",
    "no_prediction",
    "empty_pretrain",
    "random_pretrain",
]


def extract_csv_metrics(path: Path, conditions: List[str]) -> List[Dict[str, Any]]:
    """Read a CSV summary and extract key metrics for priority conditions."""
    metrics = []
    try:
        with open(path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cond = row.get("condition", "").strip()
                metric_name = row.get("metric", "").strip()
                if cond in conditions and metric_name in METRICS_TO_EXTRACT:
                    metrics.append({
                        "condition": cond,
                        "metric": metric_name,
                        "fresh": row.get("fresh", ""),
                        "pretrained": row.get("pretrained", ""),
                        "delta": row.get("delta", ""),
                        "p": row.get("p", ""),
                        "d": row.get("d", ""),
                    })
    except Exception:
        pass
    return metrics


def extract_json_metrics(path: Path, conditions: List[str]) -> List[Dict[str, Any]]:
    """Read a JSON summary and extract key metrics for priority conditions."""
    metrics = []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for cond_name, cond_data in data.items():
            if cond_name not in conditions:
                continue
            if isinstance(cond_data, dict):
                for metric_name in METRICS_TO_EXTRACT:
                    m = cond_data.get(metric_name)
                    if isinstance(m, dict):
                        metrics.append({
                            "condition": cond_name,
                            "metric": metric_name,
                            "fresh": m.get("fresh", ""),
                            "pretrained": m.get("pretrained", ""),
                            "delta": m.get("delta", ""),
                            "p": m.get("p", ""),
                            "d": m.get("d", ""),
                        })
                    elif isinstance(m, (int, float)):
                        metrics.append({
                            "condition": cond_name,
                            "metric": metric_name,
                            "value": m,
                        })
    except Exception:
        pass
    return metrics


def audit_results() -> Dict[str, Any]:
    commit = get_commit()
    results: List[Dict[str, Any]] = []

    for entry in KNOWN_RESULTS:
        artifact_path = REPO_ROOT / entry["artifact"]
        exists = artifact_path.exists()

        result_entry: Dict[str, Any] = {
            "id": entry["id"],
            "phase": entry["phase"],
            "runner": entry["runner"],
            "artifact": entry["artifact"],
            "exists": exists,
            "paper_status": entry["paper_status"],
            "notes": entry["notes"],
            "key_metrics": [],
        }

        if exists and artifact_path.suffix == ".csv":
            result_entry["key_metrics"] = extract_csv_metrics(
                artifact_path, PRIORITY_CONDITIONS
            )
        elif exists and artifact_path.suffix == ".json":
            result_entry["key_metrics"] = extract_json_metrics(
                artifact_path, PRIORITY_CONDITIONS
            )

        results.append(result_entry)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "commit": commit,
        "results": results,
    }


def format_markdown(audit: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Paper Result Audit\n")
    lines.append(f"- **Generated at:** {audit['generated_at']}")
    lines.append(f"- **Commit:** {audit['commit']}\n")
    lines.append("## Summary Table\n")
    lines.append(
        "| ID | Phase | Runner | Artifact | Exists | Paper Status | Notes | Key Metrics |"
    )
    lines.append(
        "|----|-------|--------|----------|--------|-------------|-------|-------------|"
    )

    for r in audit["results"]:
        exists_mark = "Yes" if r["exists"] else "**NO**"
        metrics_str = "; ".join(
            f"{m['condition']}.{m['metric']}: d={m.get('d', '?')}"
            for m in r["key_metrics"][:5]
        ) or "-"
        lines.append(
            f"| {r['id']} | {r['phase']} | {r['runner']} |"
            f" {r['artifact']} | {exists_mark} | {r['paper_status']} |"
            f" {r['notes']} | {metrics_str} |"
        )

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Paper result audit")
    parser.add_argument("--output", type=str, default=None, help="JSON output path")
    parser.add_argument("--markdown", type=str, default=None, help="Markdown output path")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    audit = audit_results()

    # Print markdown to stdout
    md = format_markdown(audit)
    print(md)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(audit, f, indent=2)
        print(f"Wrote JSON: {out_path}", file=sys.stderr)

    if args.markdown:
        md_path = Path(args.markdown)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Wrote markdown: {md_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
