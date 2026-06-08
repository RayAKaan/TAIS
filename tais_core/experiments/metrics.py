from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Metric:
    name: str
    lower_is_better: bool = False
    description: str = ""


def mean(xs: List[float]) -> float:
    return sum(xs) / max(1, len(xs))


def std(xs: List[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def cohens_d_paired(condition: List[float], baseline: List[float]) -> float:
    diffs = [c - b for c, b in zip(condition, baseline)]
    s = std(diffs)
    return 0.0 if s < 1e-12 else mean(diffs) / s


def norm_cdf(x: float) -> float:
    if x < 0:
        return 1.0 - norm_cdf(-x)
    k = 1.0 / (1.0 + 0.2316419 * x)
    poly = k * (0.319381530 + k * (-0.356563782 + k * (1.781477937 + k * (-1.821255978 + k * 1.330274429))))
    return 1.0 - (1.0 / math.sqrt(2 * math.pi)) * math.exp(-x * x / 2.0) * poly


def paired_ttest(condition: List[float], baseline: List[float]) -> Tuple[float, float]:
    diffs = [c - b for c, b in zip(condition, baseline)]
    n = len(diffs)
    if n < 2:
        return 0.0, 1.0
    m = mean(diffs)
    s = std(diffs)
    if s < 1e-12:
        return 0.0, 1.0
    t = m / (s / math.sqrt(n))
    df = n - 1
    p = 2.0 * (1.0 - norm_cdf(abs(t)))
    return float(t), float(p)


def ci95_delta(condition: List[float], baseline: List[float]) -> Tuple[float, float]:
    diffs = [c - b for c, b in zip(condition, baseline)]
    n = len(diffs)
    if n < 2:
        return 0.0, 0.0
    m = mean(diffs)
    s = std(diffs)
    se = s / math.sqrt(n)
    lo = m - 1.96 * se
    hi = m + 1.96 * se
    return lo, hi


def summarize_paired(baseline: List[float], condition: List[float]) -> Dict[str, float]:
    b_mean = mean(baseline)
    c_mean = mean(condition)
    delta = c_mean - b_mean
    lo, hi = ci95_delta(condition, baseline)
    _, p = paired_ttest(condition, baseline)
    d = cohens_d_paired(condition, baseline)
    return {
        "baseline": round(b_mean, 6),
        "condition": round(c_mean, 6),
        "delta": round(delta, 6),
        "ci_low": round(lo, 6),
        "ci_high": round(hi, 6),
        "p": round(p, 6),
        "d": round(d, 6),
    }
