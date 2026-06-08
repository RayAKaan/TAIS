from __future__ import annotations

import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tais_core import UniversalMote, load_domain

from .condition import Condition
from .metrics import Metric, mean
from .provenance import capture_provenance
from .results import ExperimentResults, TrialRecord
from .report import ExperimentReport

DEFAULT_POSITIONS = {
    "gridworld": "mote",
    "grid": "mote",
    "rules": "rule_ab",
    "ruleworld": "rule_ab",
    "logic": "ASSIGN",
    "logicworld": "ASSIGN",
    "chemistry_lite": "atom_c",
}


class ExperimentSuite:
    def __init__(
        self,
        name: str,
        seeds: int,
        conditions: List[Condition],
        eval_domain: str,
        eval_ticks: int,
        metrics: List[Metric],
        baseline_condition: str = "fresh",
        pretrain_ticks: int = 20,
        domain_positions: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.seeds = seeds
        self.conditions = conditions
        self.eval_domain = eval_domain
        self.eval_ticks = eval_ticks
        self.metrics = metrics
        self.baseline_condition = baseline_condition
        self.pretrain_ticks = pretrain_ticks
        self._positions = {**DEFAULT_POSITIONS, **(domain_positions or {})}

        cond_names = {c.name for c in conditions}
        if baseline_condition not in cond_names:
            raise ValueError(
                f"Baseline condition {baseline_condition!r} not found in conditions: {sorted(cond_names)}"
            )

    def position_for(self, domain_name: str) -> Any:
        return self._positions.get(domain_name, "mote")

    def make_mote(self, condition: Condition) -> UniversalMote:
        mote = UniversalMote(energy=100.0)
        if condition.engines:
            mote.enable_cognitive_engines(**condition.engines)
        return mote

    def pretrain(self, mote: UniversalMote, domains: List[str], ticks: int, seed: int) -> None:
        rng = random.Random(seed)
        for domain_name in domains:
            world = load_domain(domain_name)
            graph = world.initial_graph()
            position = self.position_for(domain_name)
            for t in range(ticks):
                if mote.energy <= 0:
                    mote.energy = 50.0
                graph, cons, action = mote.step(world, graph, mote_position=position, tick=t)

    def evaluate(self, mote: UniversalMote, domain_name: str, ticks: int, start_tick: int = 0) -> Dict[str, float]:
        world = load_domain(domain_name)
        graph = world.initial_graph()
        position = self.position_for(domain_name)

        reward0 = mote.total_reward
        penalty0 = mote.total_penalty
        invalid0 = mote.invalid_actions
        tu0 = mote.transfer_prior_uses
        ts0 = mote.transfer_prior_total_strength
        correct0 = mote.transfer_prior_correct
        incorrect0 = mote.transfer_prior_incorrect

        first_success: Optional[int] = None
        pred_errors: List[float] = []

        for t in range(ticks):
            graph, cons, action = mote.step(world, graph, mote_position=position, tick=start_tick + t)
            pe = abs(mote.last_prediction - cons.net)
            pred_errors.append(pe)
            if first_success is None:
                if cons.task_signal == "TASK_SUCCESS":
                    first_success = t
                elif cons.concept_signals.get("TASK_SUCCESS"):
                    first_success = t

        correct_after = mote.transfer_prior_correct - correct0
        incorrect_after = mote.transfer_prior_incorrect - incorrect0

        return {
            "first_task_success_tick": float(first_success if first_success is not None else ticks + 1),
            "task_completion_rate": 1.0 if first_success is not None else 0.0,
            "reward": mote.total_reward - reward0,
            "penalty": mote.total_penalty - penalty0,
            "invalid_actions": mote.invalid_actions - invalid0,
            "final_energy": mote.energy,
            "prediction_error": mean(pred_errors) if pred_errors else 0.0,
            "transfer_uses": mote.transfer_prior_uses - tu0,
            "transfer_strength": mote.transfer_prior_total_strength - ts0,
            "transfer_precision": correct_after / max(1, correct_after + incorrect_after),
            "alive": 1.0 if mote.alive else 0.0,
            "actions_taken": float(mote.actions_taken),
        }

    def run_condition(self, condition: Condition, seed: int) -> Dict[str, float]:
        mote = self.make_mote(condition)
        if condition.pretrain_domains:
            pt_ticks = condition.pretrain_ticks if condition.pretrain_ticks > 0 else self.pretrain_ticks
            self.pretrain(mote, condition.pretrain_domains, pt_ticks, seed)
        eval_domain = condition.eval_domain or self.eval_domain
        eval_ticks = condition.eval_ticks or self.eval_ticks
        return self.evaluate(mote, eval_domain, eval_ticks)

    def run(self, output_dir: Optional[str | Path] = None, verbose: bool = False) -> ExperimentResults:
        params = {
            "seeds": self.seeds,
            "eval_domain": self.eval_domain,
            "eval_ticks": self.eval_ticks,
            "pretrain_ticks": self.pretrain_ticks,
            "conditions": [c.to_dict() for c in self.conditions],
        }
        provenance = capture_provenance(self.name, params)
        results = ExperimentResults(
            name=self.name,
            baseline_condition=self.baseline_condition,
            metrics=self.metrics,
            provenance=provenance,
        )

        for seed_idx in range(self.seeds):
            trial_seed = 10_000 + seed_idx
            random.seed(trial_seed)

            for cond in self.conditions:
                cond_metrics = self.run_condition(cond, trial_seed)
                record = TrialRecord(seed=seed_idx, condition=cond.name, metrics=cond_metrics)
                results.add_record(record)

            if verbose:
                elapsed = time.time()
                print(f"  seed {seed_idx + 1}/{self.seeds} ({elapsed - results.provenance.get('_start', elapsed):.1f}s)")
            if "_start" not in provenance:
                provenance["_start"] = time.time()

        provenance.pop("_start", None)
        results.provenance = provenance

        if output_dir:
            odir = Path(output_dir)
            odir.mkdir(parents=True, exist_ok=True)
            results.save_json(odir / f"{self.name}.json")
            results.save_csv(odir / f"{self.name}.csv")
            report = ExperimentReport(results)
            report.save_markdown(odir / f"{self.name}.md")
            report.save_latex(odir / f"{self.name}.tex")

        return results
