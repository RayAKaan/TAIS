"""
TAIS V6 Batch Experiment Runner.

Supports ablation studies and multi-seed replication.
Wires into SwarmV6 engine and exports JSON results.
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Callable

from ..engine.core import SwarmV6
from ..engine.config import SwarmConfig
from ..agents.mote_v6 import MoteV6


@dataclass
class AblationConfig:
    metacognition: bool = True
    causal_reasoning: bool = True
    hierarchical_planning: bool = True
    grammar_discovery: bool = True
    trust_networks: bool = True


@dataclass
class ExperimentResult:
    seed: int
    ablation: str
    ticks: int
    final_population: int
    avg_energy: float
    avg_prediction_accuracy: float
    total_plans_created: int
    total_plans_completed: int
    total_plans_failed: int
    avg_causal_links: float
    avg_lexicon_size: float
    grammar_rules: int
    births: int
    deaths: int
    predator_kills: int
    wall_time_seconds: float
    tick_records: List[Dict[str, Any]]


class BatchRunner:
    def __init__(self, config: SwarmConfig, output_dir: str = "results"):
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _make_mote_factory(self, ablation: AblationConfig) -> Callable:
        def factory(x: float, y: float, config: SwarmConfig) -> MoteV6:
            mote = MoteV6(x, y, config)
            if not ablation.metacognition:
                mote.metacog = None
            if not ablation.causal_reasoning:
                mote.causal = None
            if not ablation.hierarchical_planning:
                mote.planner = None
            return mote
        return factory

    def run_single(
        self,
        seed: int,
        ticks: int,
        ablation: AblationConfig,
        label: str = "full",
        progress: bool = False,
    ) -> ExperimentResult:
        swarm = SwarmV6(config=self.config, seed=seed)
        factory = self._make_mote_factory(ablation)
        swarm.set_mote_factory(factory)
        swarm.init_population()

        tick_records: List[Dict[str, Any]] = []
        start_time = time.time()

        for _ in range(ticks):
            record = swarm.tick_step()
            tick_records.append(dict(record))
            if record.get("population", 0) == 0:
                break

        wall_time = time.time() - start_time
        final = tick_records[-1] if tick_records else {}

        def avg(key: str) -> float:
            vals = [r.get(key, 0) for r in tick_records]
            return sum(vals) / max(len(vals), 1)

        motes = swarm.get_motes()
        avg_causal = 0.0
        avg_lexicon = 0.0
        if motes:
            alive = [m for m in motes if m.alive]
            if alive:
                avg_causal = sum(
                    len(m.causal.links) if m.causal else 0 for m in alive
                ) / len(alive)
                avg_lexicon = sum(
                    len(m.genome.rules) if hasattr(m, 'genome') and m.genome else 0
                    for m in alive
                ) / len(alive)

        grammar_rules = sum(
            len(m.genome.rules) for m in motes if m.alive and hasattr(m, 'genome') and m.genome
        )

        return ExperimentResult(
            seed=seed,
            ablation=label,
            ticks=len(tick_records),
            final_population=final.get("population", 0),
            avg_energy=avg("avg_energy"),
            avg_prediction_accuracy=avg("avg_prediction_accuracy"),
            total_plans_created=sum(r.get("plans_created", 0) for r in tick_records),
            total_plans_completed=sum(r.get("plans_completed", 0) for r in tick_records),
            total_plans_failed=sum(r.get("plans_failed", 0) for r in tick_records),
            avg_causal_links=avg_causal,
            avg_lexicon_size=avg_lexicon,
            grammar_rules=grammar_rules,
            births=sum(r.get("births", 0) for r in tick_records),
            deaths=sum(r.get("deaths", 0) for r in tick_records),
            predator_kills=sum(r.get("predator_kills", 0) for r in tick_records),
            wall_time_seconds=wall_time,
            tick_records=tick_records,
        )

    def run_ablation_suite(
        self,
        seeds: List[int],
        ticks: int,
        conditions: Optional[Dict[str, AblationConfig]] = None,
    ) -> List[ExperimentResult]:
        if conditions is None:
            conditions = {
                "full": AblationConfig(),
                "no_metacognition": AblationConfig(metacognition=False),
                "no_causal": AblationConfig(causal_reasoning=False),
                "no_planning": AblationConfig(hierarchical_planning=False),
                "no_grammar": AblationConfig(grammar_discovery=False),
                "no_trust": AblationConfig(trust_networks=False),
                "minimal": AblationConfig(
                    metacognition=False, causal_reasoning=False,
                    hierarchical_planning=False, grammar_discovery=False,
                    trust_networks=False,
                ),
            }

        results: List[ExperimentResult] = []
        for label, ablation in conditions.items():
            for seed in seeds:
                result = self.run_single(seed, ticks, ablation, label=label)
                results.append(result)
        return results

    def save_results(self, results: List[ExperimentResult], filename: str):
        path = self.output_dir / filename
        data = [asdict(r) for r in results]
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Saved results to {path}")
