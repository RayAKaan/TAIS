#!/usr/bin/env python3
"""Phase F2 — Experiment 2: Repair Convergence.

Simulates two colonies with different lexical conventions (ka->DANGER vs ka->RESOURCE).
Measures whether speech repair enables lexicon alignment and reduces misactions.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from tais_core.domains import GridGraphWorld, make_grid_graph
from tais_core.mote import UniversalMote
from tais_core.reality import Transformation, WorldInterface
from tais_core.speech import SpeechOrgan


# ─── STAT HELPERS ─────────────────────────────────────────────────────────────

def mean(xs: List[float]) -> float:
    return sum(xs) / max(1, len(xs))


def std(xs: List[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def cohens_d_paired(pre: List[float], fresh: List[float]) -> float:
    diffs = [p - f for p, f in zip(pre, fresh)]
    s = std(diffs)
    return 0.0 if s < 1e-12 else mean(diffs) / s


def norm_cdf(x: float) -> float:
    if x < 0:
        return 1.0 - norm_cdf(-x)
    k = 1.0 / (1.0 + 0.2316419 * x)
    poly = k * (0.319381530 + k * (-0.356563782 + k * (1.781477937 + k * (-1.821255978 + k * 1.330274429))))
    return 1.0 - (1.0 / math.sqrt(2 * math.pi)) * math.exp(-x * x / 2.0) * poly


def paired_ttest(pre: List[float], fresh: List[float]) -> Tuple[float, float]:
    diffs = [p - f for p, f in zip(pre, fresh)]
    if len(diffs) < 2:
        return 0.0, 1.0
    s = std(diffs)
    m = mean(diffs)
    if s < 1e-12:
        return (0.0, 1.0) if abs(m) < 1e-12 else (float("inf"), 0.0)
    t = m / (s / math.sqrt(len(diffs)))
    p = 2.0 * (1.0 - norm_cdf(abs(t)))
    return t, max(0.0, min(1.0, p))


# ─── CUSTOM WORLD FOR SIMULATION ─────────────────────────────────────────────

class RepairTestWorld(WorldInterface):
    """Minimal world for repair convergence simulation."""

    domain_name = "repair_test"

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)

    def initial_graph(self):
        return make_grid_graph(threat_near_resource=True)

    def observe(self, graph, mote_position):
        return graph

    def valid_actions(self, graph, mote_state):
        return [
            Transformation("approach_resource", self.domain_name, "MOVE_TOWARD", base_cost=0.2),
            Transformation("avoid_threat", self.domain_name, "MOVE_AWAY", base_cost=0.2),
            Transformation("verify_safety", self.domain_name, "VERIFY", base_cost=0.1),
            Transformation("wait", self.domain_name, "OBSERVE", base_cost=0.1),
        ]

    def act(self, graph, transformation, mote_state):
        valid = self.rng.random() > 0.15
        reward = self.rng.uniform(0, 1.0) if valid else 0.0
        penalty = 1.0 if not valid else 0.0
        signal = "NONE"
        if transformation.universal_op == "MOVE_TOWARD":
            signal = "GOOD" if self.rng.random() > 0.5 else "BAD"
        elif transformation.universal_op == "MOVE_AWAY":
            signal = "GOOD" if self.rng.random() > 0.5 else "BAD"
        return graph, Consequence(
            reward=reward, penalty=penalty, valid=valid,
            task_signal=signal,
            concept_signals={"GOOD": reward, "BAD": penalty},
        )

    def evaluate(self, graph, mote_state):
        return 0.0


from tais_core.reality import Consequence


# ─── LEXICON AGREEMENT HELPER ────────────────────────────────────────────────

def compute_pairwise_lexicon_agreement(lexicons: List[Dict]) -> float:
    """Compute mean pairwise agreement across a list of lexicons.

    Each lexicon table is a Dict[str, Dict[str, float]] mapping token -> {concept: weight}.
    We compare the dominant concept for each shared token across pairs of motes.
    Returns agreement in [0, 1].
    """
    def dominant_concept(table):
        return {tok: max(concepts, key=concepts.get) if concepts else None
                for tok, concepts in table.items()}

    doms = [dominant_concept(lex) for lex in lexicons]
    total_agreement = 0.0
    count = 0
    n = len(doms)
    for i in range(n):
        for j in range(i + 1, n):
            shared = set(doms[i]) & set(doms[j])
            if not shared:
                continue
            matches = sum(1 for t in shared if doms[i][t] == doms[j][t])
            total_agreement += matches / len(shared)
            count += 1
    return total_agreement / count if count > 0 else 0.0


# ─── MOTE WITH CUSTOM LEXICON ────────────────────────────────────────────────

def make_mote_with_lexicon(seed: int, map_ka_to: str) -> UniversalMote:
    """Create a mote with a pre-configured lexicon.

    map_ka_to: 'DANGER' or 'RESOURCE' — maps the word 'ka' to a concept.
    """
    rng = random.Random(seed)
    mote = UniversalMote(energy=100.0)
    mote.speech = SpeechOrgan(mote)
    lex = mote.speech.lexicon
    if map_ka_to == "DANGER":
        lex.teach("ka", "DANGER", strength=0.9)
        lex.teach("gizmo", "RESOURCE", strength=0.8)
        lex.teach("zork", "MOVE_TOWARD", strength=0.7)
        lex.teach("zork", "MOVE_AWAY", strength=0.3)
    else:
        lex.teach("ka", "RESOURCE", strength=0.9)
        lex.teach("gizmo", "DANGER", strength=0.8)
        lex.teach("zork", "MOVE_TOWARD", strength=0.3)
        lex.teach("zork", "MOVE_AWAY", strength=0.7)
    return mote


# ─── AGENT SIMULATION ────────────────────────────────────────────────────────

@dataclass
class Agent:
    mote: UniversalMote
    colony: str
    map_ka_to: str

    def tick(self, world, graph, tick: int):
        g, cons, _ = self.mote.step(world, graph, mote_position="mote", tick=tick)
        if self.mote.energy <= 0:
            self.mote.energy = 50.0
        return g, cons


def simulate_agents(
    seeds: int,
    ticks: int,
    colony_size: int,
    repair_enabled: bool,
    verbose: bool = False,
) -> Dict[str, List[float]]:
    """Run swarm simulation of two colonies with different lexicons.

    Returns dict of per-tick metrics across seeds.
    """
    ticks_data: Dict[int, Dict[str, List[float]]] = {}

    for seed in range(seeds):
        rng = random.Random(10_000 + seed)
        world = RepairTestWorld(seed=seed)

        # Create two colonies
        colony_a = [make_mote_with_lexicon(rng.randint(0, 1_000_000), "DANGER") for _ in range(colony_size)]
        colony_b = [make_mote_with_lexicon(rng.randint(0, 1_000_000), "RESOURCE") for _ in range(colony_size)]
        all_agents = [Agent(m, "A", "DANGER") for m in colony_a] + [Agent(m, "B", "RESOURCE") for m in colony_b]

        # Initial lexicon divergence
        lexicons = [dict(a.mote.speech.lexicon.table) for a in all_agents]

        for t in range(ticks):
            tick_rng = random.Random(10_000 + seed * 1000 + t)
            g = world.initial_graph()

            # Shuffle agents
            tick_rng.shuffle(all_agents)

            # Exchange lexicon mappings between colonies
            if repair_enabled and t > 0:
                a_agents = [a for a in all_agents if a.colony == "A"]
                b_agents = [a for a in all_agents if a.colony == "B"]
                for a_agent in a_agents:
                    for b_agent in b_agents:
                        a_lex = a_agent.mote.speech.lexicon
                        b_lex = b_agent.mote.speech.lexicon
                        pick = tick_rng.choice(list(a_lex.table.keys()))
                        if a_lex.top_concept(pick) is not None and b_lex.top_concept(pick) != a_lex.top_concept(pick):
                            b_lex.teach(pick, a_lex.top_concept(pick), strength=0.15)

            # Each agent acts
            misactions = 0
            repair_count = 0
            for agent in all_agents:
                g, cons = agent.tick(world, g, t)
                if cons.task_signal == "TASK_FAILURE" or (cons.penalty > 0 and cons.valid is False):
                    misactions += 1
                if cons.task_signal == "REPAIR":
                    repair_count += 1

            # Record per-tick metrics
            lexicons_now = [dict(a.mote.speech.lexicon.table) for a in all_agents]
            agreement = compute_pairwise_lexicon_agreement(lexicons_now)

            if t not in ticks_data:
                ticks_data[t] = {
                    "semantic_success_rate": [],
                    "lexicon_divergence": [],
                    "misaction_rate": [],
                    "repair_count": [],
                }

            ticks_data[t]["semantic_success_rate"].append(
                1.0 - (misactions / max(1, len(all_agents) * 10))
            )
            ticks_data[t]["lexicon_divergence"].append(1.0 - agreement)
            ticks_data[t]["misaction_rate"].append(misactions / max(1, len(all_agents)))
            ticks_data[t]["repair_count"].append(float(repair_count))

        if verbose and (seed + 1) % 10 == 0:
            print(f"  seed {seed + 1}/{seeds}")

    # Aggregate across seeds
    result: Dict[str, List[float]] = {
        "tick": [],
        "semantic_success_rate": [],
        "lexicon_divergence": [],
        "misaction_rate": [],
        "repair_count": [],
    }
    for t in sorted(ticks_data.keys()):
        result["tick"].append(float(t))
        for key in ["semantic_success_rate", "lexicon_divergence", "misaction_rate", "repair_count"]:
            result[key].append(mean(ticks_data[t][key]))

    return result


# ─── OUTPUT ───────────────────────────────────────────────────────────────────

def format_results(
    enabled_data: Dict[str, List[float]],
    disabled_data: Dict[str, List[float]],
    seeds: int,
    ticks: int,
) -> str:
    lines = []
    lines.append("=" * 100)
    lines.append("  PHASE F2 — Experiment 2: Repair Convergence")
    lines.append("=" * 100)
    lines.append(f"\n  Seeds: {seeds} | Ticks: {ticks} | Colony size: 10\n")

    for cond_name, data in [("Repair Enabled", enabled_data), ("Repair Disabled", disabled_data)]:
        lines.append(f"\n  --- {cond_name} ---")
        lines.append(f"  {'Tick':>6} {'Semantic Success':>18} {'Lexicon Divergence':>20} {'Misaction Rate':>16} {'Repair Count':>14}")
        lines.append(f"  {'-'*6} {'-'*18} {'-'*20} {'-'*16} {'-'*14}")
        for i, t in enumerate(data["tick"]):
            if i % 5 == 0 or i == len(data["tick"]) - 1:
                lines.append(
                    f"  {int(t):>6} {data['semantic_success_rate'][i]:>18.4f} "
                    f"{data['lexicon_divergence'][i]:>20.4f} {data['misaction_rate'][i]:>16.4f} "
                    f"{data['repair_count'][i]:>14.2f}"
                )

    # Final tick comparison
    lines.append("\n  --- Final Tick Comparison ---")
    last_t = int(enabled_data["tick"][-1])
    e_ss = enabled_data["semantic_success_rate"][-1]
    d_ss = disabled_data["semantic_success_rate"][-1]
    e_div = enabled_data["lexicon_divergence"][-1]
    d_div = disabled_data["lexicon_divergence"][-1]
    e_mis = enabled_data["misaction_rate"][-1]
    d_mis = disabled_data["misaction_rate"][-1]

    lines.append(f"  {'Metric':<25} {'Repair Enabled':>16} {'Repair Disabled':>17}")
    lines.append(f"  {'-'*25} {'-'*16} {'-'*17}")
    lines.append(f"  {'Semantic Success Rate':<25} {e_ss:>16.4f} {d_ss:>17.4f}")
    lines.append(f"  {'Lexicon Divergence':<25} {e_div:>16.4f} {d_div:>17.4f}")
    lines.append(f"  {'Misaction Rate':<25} {e_mis:>16.4f} {d_mis:>17.4f}")

    lines.append("\n" + "=" * 100)
    return "\n".join(lines)


def write_csv(data: Dict[str, List[float]], path: str, label: str = ""):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["tick", "semantic_success_rate", "lexicon_divergence", "misaction_rate", "repair_count", "condition"])
        for i, t in enumerate(data["tick"]):
            w.writerow([int(t), data["semantic_success_rate"][i], data["lexicon_divergence"][i],
                       data["misaction_rate"][i], data["repair_count"][i], label])


def main():
    p = argparse.ArgumentParser(description="Phase F2 — Repair Convergence")
    p.add_argument("--seeds", type=int, default=200)
    p.add_argument("--ticks", type=int, default=100)
    p.add_argument("--colony-size", type=int, default=10)
    p.add_argument("--output", type=str, default="results/phase_f2/repair_convergence.txt")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    print(f"Repair Convergence: seeds={args.seeds}, ticks={args.ticks}, colony_size={args.colony_size}",
          file=sys.stderr)
    t0 = time.time()

    print("  Running repair_enabled...", file=sys.stderr)
    enabled_data = simulate_agents(args.seeds, args.ticks, args.colony_size, repair_enabled=True, verbose=args.verbose)
    print("  Running repair_disabled...", file=sys.stderr)
    disabled_data = simulate_agents(args.seeds, args.ticks, args.colony_size, repair_enabled=False, verbose=args.verbose)

    elapsed = time.time() - t0
    table = format_results(enabled_data, disabled_data, args.seeds, args.ticks)
    print(table, file=sys.stderr if not args.verbose else sys.stdout)

    out = args.output
    with open(out, "w", encoding="utf-8") as f:
        f.write(table + f"\n\nElapsed: {elapsed:.2f}s\n")
    csv_enabled = out.rsplit(".", 1)[0] + "_enabled.csv"
    csv_disabled = out.rsplit(".", 1)[0] + "_disabled.csv"
    write_csv(enabled_data, csv_enabled, "repair_enabled")
    write_csv(disabled_data, csv_disabled, "repair_disabled")
    json_path = out.rsplit(".", 1)[0] + ".json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"repair_enabled": enabled_data, "repair_disabled": disabled_data}, f, indent=2)
    print(f"Wrote: {out}\nWrote: {csv_enabled}\nWrote: {csv_disabled}\nWrote: {json_path}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
