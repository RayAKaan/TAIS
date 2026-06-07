"""
200-seed statistical replication for the first positive TAIS transfer signal.

Question:
    Does mixed GridWorld pretraining improve early RuleWorld performance?

Design:
    Paired seeds.
    For each seed:
      A) fresh mote -> RuleWorld for 12 ticks
      B) mixed GridWorld-pretrained mote -> RuleWorld for 12 ticks
    Compare pretrained - fresh.

Statistics:
    - paired mean delta
    - bootstrap 95% CI
    - paired Cohen's d
    - sign-flip permutation p-value

Run:
    PYTHONPATH=. python3 experiments_statistical_replication.py
"""

from __future__ import annotations

import json
import math
import random
import statistics
from typing import Callable, Dict, List, Optional

from tais_core.mote import UniversalMote
from experiments.cross_domain_transfer import pretrain_grid, run_rule_trial


def paired_trials(seeds: int = 200, pretrain_ticks: int = 20, rule_ticks: int = 12):
    rows = []
    for seed in range(seeds):
        eval_seed = 100_000 + seed
        pre_seed = 200_000 + seed

        fresh = UniversalMote(energy=100)
        fresh_res = run_rule_trial(fresh, rule_ticks, seed=eval_seed, condition="fresh")

        pre = UniversalMote(energy=100)
        pretrain_grid(pre, pretrain_ticks, seed=pre_seed, mixed=True)
        pre_res = run_rule_trial(pre, rule_ticks, seed=eval_seed, condition="mixed_grid_pretrained")

        rows.append({"seed": seed, "fresh": fresh_res, "pretrained": pre_res})
    return rows


def first_apply_value(x: Optional[int], rule_ticks: int) -> int:
    # lower is better; never applied is worst and encoded as rule_ticks
    return rule_ticks if x is None else x


def metric_delta(row: dict, metric: str, rule_ticks: int) -> float:
    f = row["fresh"]
    p = row["pretrained"]
    if metric == "first_apply_tick":
        return first_apply_value(p.first_apply_tick, rule_ticks) - first_apply_value(f.first_apply_tick, rule_ticks)
    return float(getattr(p, metric)) - float(getattr(f, metric))


def bootstrap_ci(values: List[float], samples: int = 10000, alpha: float = 0.05, seed: int = 1234):
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(samples):
        means.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    lo = means[int((alpha / 2) * samples)]
    hi = means[int((1 - alpha / 2) * samples)]
    return lo, hi


def sign_flip_pvalue(values: List[float], samples: int = 50000, seed: int = 4321) -> float:
    """Two-sided paired randomization test under sign-flip null."""
    rng = random.Random(seed)
    observed = abs(sum(values) / len(values))
    count = 0
    for _ in range(samples):
        mean = sum((v if rng.random() < 0.5 else -v) for v in values) / len(values)
        if abs(mean) >= observed:
            count += 1
    return (count + 1) / (samples + 1)


def cohen_d_paired(values: List[float]) -> Optional[float]:
    if len(values) < 2:
        return None
    sd = statistics.stdev(values)
    if sd == 0:
        return None
    return statistics.mean(values) / sd


def summarize_metric(rows: List[dict], metric: str, rule_ticks: int, higher_is_better: bool = True):
    diffs = [metric_delta(r, metric, rule_ticks) for r in rows]
    mean_delta = statistics.mean(diffs)
    ci = bootstrap_ci(diffs)
    p = sign_flip_pvalue(diffs)
    d = cohen_d_paired(diffs)
    direction_ok = mean_delta > 0 if higher_is_better else mean_delta < 0
    return {
        "metric": metric,
        "n": len(diffs),
        "mean_delta_pretrained_minus_fresh": round(mean_delta, 6),
        "bootstrap_95ci": [round(ci[0], 6), round(ci[1], 6)],
        "sign_flip_p_two_sided": round(p, 6),
        "paired_cohens_d": None if d is None else round(d, 6),
        "direction_expected": "higher" if higher_is_better else "lower",
        "direction_matched": bool(direction_ok),
    }


def run(seeds: int = 200, pretrain_ticks: int = 20, rule_ticks: int = 12):
    rows = paired_trials(seeds=seeds, pretrain_ticks=pretrain_ticks, rule_ticks=rule_ticks)
    metrics = [
        ("total_reward", True),
        ("final_energy", True),
        ("invalid_actions", False),
        ("first_apply_tick", False),
        ("mean_prediction_error", False),
        ("transfer_prior_uses", True),
        ("transfer_prior_total_strength", True),
        ("transfer_prior_precision", True),
    ]
    summaries = {m: summarize_metric(rows, m, rule_ticks, higher_is_better=hib) for m, hib in metrics}

    # Raw group means for readability.
    group_means: Dict[str, Dict[str, float]] = {"fresh": {}, "pretrained": {}}
    for m, _hib in metrics:
        for group in ["fresh", "pretrained"]:
            vals = []
            for r in rows:
                obj = r[group]
                if m == "first_apply_tick":
                    vals.append(first_apply_value(obj.first_apply_tick, rule_ticks))
                else:
                    vals.append(float(getattr(obj, m)))
            group_means[group][m] = round(statistics.mean(vals), 6)

    result = {
        "experiment": "mixed_gridworld_to_ruleworld_200seed_replication",
        "seeds": seeds,
        "pretrain_ticks": pretrain_ticks,
        "rule_ticks": rule_ticks,
        "group_means": group_means,
        "paired_statistics": summaries,
        "interpretation": interpret(summaries),
        "rows": [
            {
                "seed": r["seed"],
                "fresh": r["fresh"].__dict__,
                "pretrained": r["pretrained"].__dict__,
            }
            for r in rows
        ],
    }
    return result


def interpret(summaries: Dict[str, dict]) -> str:
    reward = summaries["total_reward"]
    ci = reward["bootstrap_95ci"]
    p = reward["sign_flip_p_two_sided"]
    if ci[0] > 0 and p < 0.05:
        return "PASS: mixed GridWorld pretraining significantly improves early RuleWorld reward."
    if reward["mean_delta_pretrained_minus_fresh"] > 0:
        return "SUGGESTIVE: reward delta is positive, but CI/p-value do not establish significance."
    return "FAIL/INCONCLUSIVE: no positive early RuleWorld reward advantage."


if __name__ == "__main__":
    result = run()
    printable = {k: v for k, v in result.items() if k != "rows"}
    print(json.dumps(printable, indent=2))
    with open("statistical_replication_results.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print("saved → statistical_replication_results.json")
