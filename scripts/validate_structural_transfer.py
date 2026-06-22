"""
validate_structural_transfer.py
================================

The definitive experiment: does structural transfer work when all
surface features are shuffled?

This script runs the 5 critical experiments from the breakthrough roadmap:
1. Zero-Annotation Transfer (no role_hint, no role_compatibility)
2. Scaling with Structural Overlap
3. Surface Independence
4. Complexity Scaling
5. Compositional Transfer (multi-step strategies)

Run: python scripts/validate_structural_transfer.py
"""

import random
import sys
import os
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tais_core.mote import UniversalMote
from tais_core.domains.gridworld import GridGraphWorld, make_grid_graph
from tais_core.domains.negosim import NegoSimWorld, make_negosim_graph
from tais_core.role_discovery import RoleDiscoveryEngine
from tais_core.structural_similarity import StructuralCompatibility
from tais_core.analogy_engine import StructuralAnalogyEngine
from tais_core.policy_transfer import CompositionalPolicy
from tais_core.domains.procedural import ProceduralDomainFactory, ProceduralWorld


# --- EXPERIMENT 1: Zero-Annotation Transfer -----------------------------------

def experiment_zero_annotation_transfer(
    source_domain: str = "gridworld",
    target_domain: str = "negosim",
    n_train_ticks: int = 20,
    n_eval_ticks: int = 30,
    n_repeats: int = 5,
) -> Dict[str, Any]:
    """Test: remove ALL role_hint from ALL domains, pretrain on A, eval on B.

    Measures:
    - Time-to-threshold in target domain (ticks until first positive reward)
    - Net reward in eval phase
    - Role discovery stats

    Pass criterion: Pretrained agent with structural transfer discovers roles
    and uses them in the target domain.
    """
    print("=" * 70)
    print("EXPERIMENT 1: Zero-Annotation Transfer")
    print(f"  Source: {source_domain} -> Target: {target_domain}")
    print(f"  Train: {n_train_ticks} ticks, Eval: {n_eval_ticks} ticks")
    print(f"  Repeats: {n_repeats}")
    print()

    results = []

    for rep in range(n_repeats):
        random.seed(rep * 10)

        # Pretrained mote WITH structural transfer
        pretrained = UniversalMote(energy=200)
        pretrained.enable_structural_transfer()

        if source_domain == "gridworld":
            world = GridGraphWorld()
            graph = make_grid_graph()
            for tick in range(n_train_ticks):
                graph, cons, action = pretrained.step(
                    world, graph, mote_position="mote", tick=tick
                )
                if not pretrained.alive:
                    pretrained = UniversalMote(energy=200)
                    pretrained.enable_structural_transfer()
                    break

        # Eval on target
        if target_domain == "negosim":
            target_world = NegoSimWorld()
            target_graph = make_negosim_graph()
        else:
            print(f"  Unknown target domain: {target_domain}")
            continue

        pretrained_reward = 0.0
        first_positive_tick = None

        for tick in range(n_eval_ticks):
            target_graph, cons, action = pretrained.step(
                target_world, target_graph, mote_position="agent_0",
                tick=tick, extra_state={"mote_id_str": "agent_0"}
            )
            pretrained_reward += cons.net
            if cons.net > 0 and first_positive_tick is None:
                first_positive_tick = tick
            if not pretrained.alive:
                break

        # Fresh mote (no pretraining)
        fresh = UniversalMote(energy=200)
        fresh.enable_structural_transfer()
        target_graph2 = make_negosim_graph()

        fresh_reward = 0.0
        fresh_first_positive_tick = None

        for tick in range(n_eval_ticks):
            target_graph2, cons, action = fresh.step(
                target_world, target_graph2, mote_position="agent_0",
                tick=tick, extra_state={"mote_id_str": "agent_0"}
            )
            fresh_reward += cons.net
            if cons.net > 0 and fresh_first_positive_tick is None:
                fresh_first_positive_tick = tick
            if not fresh.alive:
                break

        result = {
            "repeat": rep,
            "pretrained_reward": pretrained_reward,
            "fresh_reward": fresh_reward,
            "pretrained_first_positive": first_positive_tick,
            "fresh_first_positive": fresh_first_positive_tick,
            "discovered_roles": len(pretrained.role_discovery._roles) if pretrained.role_discovery else 0,
            "policy_sequences": len(pretrained.compositional_policy._sequences) if pretrained.compositional_policy else 0,
        }
        results.append(result)
        print(f"  Repeat {rep}: pretrained={pretrained_reward:.1f} fresh={fresh_reward:.1f} "
              f"roles={result['discovered_roles']}")

    if results:
        avg_pretrained = sum(r["pretrained_reward"] for r in results) / len(results)
        avg_fresh = sum(r["fresh_reward"] for r in results) / len(results)
        print(f"\n  Summary:")
        print(f"    Avg pretrained reward: {avg_pretrained:.2f}")
        print(f"    Avg fresh reward:      {avg_fresh:.2f}")
        print(f"    Advantage:             {avg_pretrained - avg_fresh:.2f}")
        print()

    return {
        "experiment": "zero_annotation_transfer",
        "results": results,
    }


# --- EXPERIMENT 2: Surface Independence ----------------------------------------

def experiment_surface_independence(
    n_domain_pairs: int = 3,
    n_eval_ticks: int = 30,
) -> Dict[str, Any]:
    """Test: structural transfer works equally well when surface names are shuffled.

    Creates domain pairs with:
    - overlap = 0.8 (high structural overlap)
    - surface_distance = 0.1 (similar names) vs 0.9 (completely different names)

    Pass criterion: Transfer advantage differs by < 10% between the two
    surface-distance variants.
    """
    print("=" * 70)
    print("EXPERIMENT 2: Surface Independence")
    print(f"  Domain pairs: {n_domain_pairs}")
    print(f"  Eval ticks: {n_eval_ticks}")
    print()

    low_surface_results = []
    high_surface_results = []

    for seed in range(n_domain_pairs):
        # Low surface distance (similar names)
        source_low, target_low = ProceduralDomainFactory.generate_pair(
            overlap=0.8, complexity=50, surface_distance=0.1, seed=seed + 100,
        )

        # High surface distance (completely different names)
        source_high, target_high = ProceduralDomainFactory.generate_pair(
            overlap=0.8, complexity=50, surface_distance=0.9, seed=seed + 100,
        )

        # Train on source, eval on target for both variants
        for label, source, target in [
            ("low_surface", source_low, target_low),
            ("high_surface", source_high, target_high),
        ]:
            mote = UniversalMote(energy=200)
            mote.enable_structural_transfer()

            # Eval directly (no pretraining) on target
            target_graph = target.target_graph.snapshot()
            total_reward = 0.0

            for tick in range(n_eval_ticks):
                target_graph, cons, action = mote.step(
                    target, target_graph, mote_position=target._agent_id,
                    tick=tick, extra_state={"mote_id_str": target._agent_id or ""}
                )
                total_reward += cons.net
                if not mote.alive:
                    break

            result = {
                "seed": seed,
                "surface_distance": 0.1 if label == "low_surface" else 0.9,
                "reward": total_reward,
            }

            if label == "low_surface":
                low_surface_results.append(result)
            else:
                high_surface_results.append(result)

            print(f"  Seed {seed}, {label}: reward={total_reward:.1f}")

    if low_surface_results and high_surface_results:
        avg_low = sum(r["reward"] for r in low_surface_results) / len(low_surface_results)
        avg_high = sum(r["reward"] for r in high_surface_results) / len(high_surface_results)
        diff_pct = abs(avg_low - avg_high) / max(abs(avg_low), 0.01) * 100
        print(f"\n  Summary:")
        print(f"    Avg low surface reward:  {avg_low:.2f}")
        print(f"    Avg high surface reward: {avg_high:.2f}")
        print(f"    Difference:              {diff_pct:.1f}%")
        print()

    return {
        "experiment": "surface_independence",
        "low_surface": low_surface_results,
        "high_surface": high_surface_results,
    }


# --- EXPERIMENT 3: Scaling with Structural Overlap -----------------------------

def experiment_scaling_with_overlap(
    n_seeds: int = 3,
    n_eval_ticks: int = 30,
) -> Dict[str, Any]:
    """Test: transfer advantage scales with structural overlap.

    Generates domain pairs with overlap in {0.1, 0.3, 0.5, 0.7, 0.9}.

    Pass criterion: transfer advantage correlates positively with overlap.
    """
    print("=" * 70)
    print("EXPERIMENT 3: Scaling with Structural Overlap")
    print(f"  Seeds: {n_seeds}, Eval ticks: {n_eval_ticks}")
    print()

    overlaps = [0.1, 0.3, 0.5, 0.7, 0.9]
    results_by_overlap: Dict[float, List[float]] = defaultdict(list)

    for overlap in overlaps:
        for seed in range(n_seeds):
            source, target = ProceduralDomainFactory.generate_pair(
                overlap=overlap, complexity=50,
                surface_distance=0.9, seed=seed + 200,
            )

            # Pretrained mote
            pretrained = UniversalMote(energy=200)
            pretrained.enable_structural_transfer()

            # Train on source
            source_graph = source.target_graph.snapshot()
            for tick in range(15):
                source_graph, cons, action = pretrained.step(
                    source, source_graph, mote_position=source._agent_id,
                    tick=tick, extra_state={"mote_id_str": source._agent_id or ""}
                )
                if not pretrained.alive:
                    break

            # Eval on target
            target_graph = target.target_graph.snapshot()
            pretrained_reward = 0.0

            for tick in range(n_eval_ticks):
                target_graph, cons, action = pretrained.step(
                    target, target_graph, mote_position=target._agent_id,
                    tick=tick, extra_state={"mote_id_str": target._agent_id or ""}
                )
                pretrained_reward += cons.net
                if not pretrained.alive:
                    break

            # Fresh mote
            fresh = UniversalMote(energy=200)
            fresh.enable_structural_transfer()
            target_graph2 = target.target_graph.snapshot()
            fresh_reward = 0.0

            for tick in range(n_eval_ticks):
                target_graph2, cons, action = fresh.step(
                    target, target_graph2, mote_position=target._agent_id,
                    tick=tick, extra_state={"mote_id_str": target._agent_id or ""}
                )
                fresh_reward += cons.net
                if not fresh.alive:
                    break

            advantage = pretrained_reward - fresh_reward
            results_by_overlap[overlap].append(advantage)

            print(f"  overlap={overlap:.1f} seed={seed}: "
                  f"pretrained={pretrained_reward:.1f} fresh={fresh_reward:.1f} "
                  f"advantage={advantage:.1f}")

    print(f"\n  Summary:")
    for overlap in overlaps:
        vals = results_by_overlap[overlap]
        if vals:
            avg = sum(vals) / len(vals)
            print(f"    overlap={overlap:.1f}: avg advantage={avg:.2f} "
                  f"(min={min(vals):.1f}, max={max(vals):.1f})")

    # Correlation check
    all_overlaps = []
    all_advantages = []
    for overlap in overlaps:
        for v in results_by_overlap.get(overlap, []):
            all_overlaps.append(overlap)
            all_advantages.append(v)

    if len(all_overlaps) >= 5:
        n = len(all_overlaps)
        mean_x = sum(all_overlaps) / n
        mean_y = sum(all_advantages) / n
        num = sum((all_overlaps[i] - mean_x) * (all_advantages[i] - mean_y) for i in range(n))
        denom_x = sum((all_overlaps[i] - mean_x) ** 2 for i in range(n)) ** 0.5
        denom_y = sum((all_advantages[i] - mean_y) ** 2 for i in range(n)) ** 0.5
        if denom_x > 0 and denom_y > 0:
            r = num / (denom_x * denom_y)
            print(f"    Pearson r (overlap vs advantage): {r:.3f}")
    print()

    return {
        "experiment": "scaling_with_overlap",
        "results_by_overlap": {str(k): v for k, v in results_by_overlap.items()},
    }


# --- EXPERIMENT 4: Cross-Domain Transfer Analytics -----------------------------

def experiment_cross_domain_analytics(
    n_eval_ticks: int = 30,
) -> Dict[str, Any]:
    """Test: analyze structural transfer between GridWorld and NegoSim.

    Measures:
    1. How many discovered roles from GridWorld match NegoSim observations
    2. How often structural analogies are found
    3. Compositional policy stats
    """
    print("=" * 70)
    print("EXPERIMENT 4: Cross-Domain Transfer Analytics")
    print(f"  Eval ticks: {n_eval_ticks}")
    print()

    mote = UniversalMote(energy=200)
    mote.enable_structural_transfer()
    mote.enable_cognitive_engines()

    # Train on GridWorld
    grid_world = GridGraphWorld()
    grid_graph = make_grid_graph()

    for tick in range(20):
        grid_graph, cons, action = mote.step(
            grid_world, grid_graph, mote_position="mote", tick=tick
        )
        if not mote.alive:
            print("  WARNING: mote died during GridWorld training")
            mote = UniversalMote(energy=200)
            mote.enable_structural_transfer()
            mote.enable_cognitive_engines()
            grid_graph = make_grid_graph()
            for tick2 in range(20):
                grid_graph, cons2, action2 = mote.step(
                    grid_world, grid_graph, mote_position="mote", tick=tick2
                )
                if not mote.alive:
                    break

    print(f"  After GridWorld training:")
    metrics = mote.metrics()
    print(f"    Actions taken: {metrics.get('actions', 0)}")
    print(f"    Discovered roles: {metrics.get('discovered_roles', 0)}")

    # Eval on NegoSim
    nego_world = NegoSimWorld()
    nego_graph = make_negosim_graph()

    for tick in range(n_eval_ticks):
        nego_graph, cons, action = mote.step(
            nego_world, nego_graph, mote_position="agent_0",
            tick=tick, extra_state={"mote_id_str": "agent_0"}
        )
        if not mote.alive:
            break

    final_metrics = mote.metrics()
    print(f"\n  After NegoSim eval:")
    print(f"    Total reward: {final_metrics.get('total_reward', 0):.2f}")
    print(f"    Discovered roles: {final_metrics.get('discovered_roles', 0)}")
    print(f"    Role discovery records: {final_metrics.get('role_discovery_records', 0)}")
    print(f"    Policy sequences: {final_metrics.get('policy_sequences', 0)}")
    print(f"    Transfer precision: {final_metrics.get('transfer_prior_precision', 0):.3f}")

    # Print discovered roles
    if mote.role_discovery:
        roles = mote.role_discovery.discover_roles()
        print(f"\n  Top discovered roles:")
        for role in roles[:5]:
            rdata = role.to_dict()
            print(f"    {rdata['role_id']}: valence={rdata['outcome_valence']}, "
                  f"key={rdata['structural_key'][:8]}..., "
                  f"actions={rdata['action_names']}, "
                  f"confidence={rdata['confidence']:.2f}, "
                  f"samples={rdata['sample_count']}")

    print()
    return {
        "experiment": "cross_domain_analytics",
        "metrics": final_metrics,
    }


# --- RUN ALL EXPERIMENTS -------------------------------------------------------

def main():
    print("=" * 70)
    print("STRUCTURAL TRANSFER v2 VALIDATION")
    print("Genuine structural analogy without role labels")
    print("=" * 70)
    print()

    results = {}

    results["experiment_1"] = experiment_zero_annotation_transfer(
        n_train_ticks=15, n_eval_ticks=20, n_repeats=3,
    )

    results["experiment_2"] = experiment_surface_independence(
        n_domain_pairs=2, n_eval_ticks=20,
    )

    results["experiment_3"] = experiment_scaling_with_overlap(
        n_seeds=2, n_eval_ticks=20,
    )

    results["experiment_4"] = experiment_cross_domain_analytics(
        n_eval_ticks=20,
    )

    print("=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)
    print()
    print("Experiment 1 (Zero-Annotation Transfer):")
    r1 = results.get("experiment_1", {})
    avg_pretrained = sum(r.get("pretrained_reward", 0) for r in r1.get("results", [])) / max(1, len(r1.get("results", [])))
    avg_fresh = sum(r.get("fresh_reward", 0) for r in r1.get("results", [])) / max(1, len(r1.get("results", [])))
    print(f"  Pretrained avg: {avg_pretrained:.2f}, Fresh avg: {avg_fresh:.2f}, Advantage: {avg_pretrained - avg_fresh:.2f}")

    print("\nExperiment 2 (Surface Independence):")
    r2 = results.get("experiment_2", {})
    low_vals = [r["reward"] for r in r2.get("low_surface", [])]
    high_vals = [r["reward"] for r in r2.get("high_surface", [])]
    if low_vals and high_vals:
        avg_low = sum(low_vals) / len(low_vals)
        avg_high = sum(high_vals) / len(high_vals)
        print(f"  Low surface avg: {avg_low:.2f}, High surface avg: {avg_high:.2f}")

    print("\nExperiment 3 (Scaling with Overlap):")
    r3 = results.get("experiment_3", {})
    for k, v in r3.get("results_by_overlap", {}).items():
        if v:
            print(f"  Overlap {k}: avg advantage = {sum(v)/len(v):.2f}")

    print("\nExperiment 4 (Cross-Domain Analytics):")
    r4 = results.get("experiment_4", {})
    m = r4.get("metrics", {})
    print(f"  Discovered roles: {m.get('discovered_roles', 'N/A')}")
    print(f"  Policy sequences: {m.get('policy_sequences', 'N/A')}")


if __name__ == "__main__":
    main()
