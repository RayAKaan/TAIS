from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt


def ensure_parent(path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def save_figure(fig, path: str | Path, dpi: int = 160) -> Path:
    p = ensure_parent(path)
    fig.savefig(p, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return p


def load_json(path: str | Path) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_summary_csv(path: str | Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({k.strip(): v.strip() for k, v in row.items()})
    return rows


def filter_metric(rows: List[Dict[str, str]], metric: str) -> List[Dict[str, str]]:
    return [r for r in rows if r.get("metric", "").strip() == metric]


def as_float(row: Dict[str, str], key: str, default: float = 0.0) -> float:
    try:
        return float(row[key])
    except (KeyError, ValueError, TypeError):
        return default
