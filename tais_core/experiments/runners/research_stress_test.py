"""
TAIS Research-Grade Stress Test (Phase 6): Multi-Source Transfer Depth
This script evaluates Universal Mote capabilities across increasingly complex 
dependency chains, noisy environments, and high-entropy states.

Scenarios:
1. [EASY] Pattern Completion (SequenceWorld)
2. [MEDIUM] Multi-Goal Interaction (WebNav with distractions)
3. [HARD] Recursive Synthesis (CodeSynt with nested dependencies)
4. [VERY HARD] Constrained Discovery (Noisy SciEx with control-loops)
5. [SUPER HARD] Competitive Negotiation (High-pressure NegoSim)
6. [EXTREMELY HARD] Fused Discovery (Cross-layer Science + Market)
"""

import random
import time
import json
import numpy as np
from tais_core.mote import UniversalMote
from tais_core.domains.registry import load_domain
from tais_core.reality import Entity, Relation, RealityGraph

class ResearchStressTest:
    def __init__(self, seeds=[42]):
        self.seeds = seeds
        self.domains = ["grid", "rules", "hazard", "logic", "sequences", "webnav", "codesynt", "sciex", "negosim"]
        self.results = {}

    def pretrain_mote(self, mote, pretrain_ticks=15):
        """Builds a rich pattern library across core domains."""
        core_set = ["grid", "rules", "sequences"]
        for d in core_set:
            world = load_domain(d)
            # Find a valid start pos
            g = world.initial_graph() if hasattr(world, 'initial_graph') else None
            # Standard pos heuristics
            pos_map = {"grid": "mote", "rules": "rule_ab", "sequences": "v0"}
            pos = pos_map.get(d)
            for t in range(pretrain_ticks):
                g, _, _ = mote.step(world, g, mote_position=pos, tick=t)

    def run_scenario(self, mote, scenario_config, partner_config=None):
        world = load_domain(scenario_config['domain'])
        graph = world.initial_graph()
        
        # Inject Complexity / Noise
        if scenario_config.get('noise_level'):
            for i in range(scenario_config['noise_level']):
                graph.add_entity(Entity(f"noise_{i}", "NOISE", {"val": random.random()}))
        
        # Partner mote setup
        partner_mote = None
        if partner_config:
            partner_mote = partner_config['mote']
        
        # Scenario Logic
        start_time = time.time()
        success = False
        trace = []
        
        for t in range(scenario_config['horizon']):
            # Special state handling for different domains
            extra = scenario_config.get('extra_state', {})
            pos = scenario_config.get('pos')
            
            # Partner mote steps first (if configured) to create state for main mote
            if partner_mote:
                ppos = partner_config.get('pos', 'agent_1')
                pextra = partner_config.get('extra_state', {"mote_id_str": "agent_1"})
                graph, _, _ = partner_mote.step(world, graph, mote_position=ppos, tick=t, extra_state=pextra)
            
            # Step
            graph, cons, action = mote.step(world, graph, mote_position=pos, tick=t, extra_state=extra)
            
            if action:
                trace.append({
                    "tick": t,
                    "action": action.name,
                    "role": action.role_hint,
                    "net": cons.net,
                    "signal": cons.task_signal
                })
            
            if cons.task_signal == "TASK_SUCCESS":
                success = True
                break

        elapsed = time.time() - start_time
        return {
            "success": success,
            "tick": t if success else None,
            "time": elapsed,
            "trace_len": len(trace),
            "final_energy": mote.energy,
            "metrics": mote.metrics()
        }

    def execute(self):
        scenarios = [
            {"id": "EASY", "name": "Sequence Patterning", "domain": "sequences", "horizon": 20, "pos": "v0"},
            {"id": "MEDIUM", "name": "Distracted Navigation", "domain": "webnav", "horizon": 30, "pos": "nav", "noise_level": 5},
            {"id": "HARD", "name": "Recursive AST Synt", "domain": "codesynt", "horizon": 60, "pos": "root", "noise_level": 10},
            {"id": "VERY_HARD", "name": "Constrained Science", "domain": "sciex", "horizon": 100, "pos": "hyp1", "noise_level": 15},
            {"id": "SUPER_HARD", "name": "High-Pressure Market", "domain": "negosim", "horizon": 70, "pos": "agent_0", "extra_state": {"mote_id_str": "agent_0"}},
            {"id": "EXTREMELY_HARD", "name": "Mega-Fused Discovery", "domain": "sciex", "horizon": 250, "pos": "hyp1", "noise_level": 30}
        ]

        for seed in self.seeds:
            print(f"\n--- SEED {seed} ---")
            random.seed(seed)
            mote = UniversalMote(energy=1000) # Research grade energy budget
            self.pretrain_mote(mote)
            
            # Enable Engines for Hard+ levels
            mote.enable_cognitive_engines(hierarchical_planning=True, causal_reasoning=True)
            
            # Partner mote for multi-agent scenarios
            partner_mote = UniversalMote(energy=1000)
            self.pretrain_mote(partner_mote)
            partner_mote.enable_cognitive_engines(hierarchical_planning=True, causal_reasoning=True)
            
            seed_results = []
            for sc in scenarios:
                print(f"Executing {sc['id']}: {sc['name']}...")
                partner_cfg = None
                if sc['id'] == "SUPER_HARD":
                    partner_cfg = {
                        "mote": partner_mote,
                        "pos": "agent_1",
                        "extra_state": {"mote_id_str": "agent_1"},
                    }
                res = self.run_scenario(mote, sc, partner_config=partner_cfg)
                status = "SUCCESS" if res['success'] else "FAILED"
                tick_info = f"at t={res['tick']}" if res['success'] else ""
                print(f"  [{status}] {tick_info} Precision: {res['metrics']['transfer_prior_precision']*100:.1f}% Patterns: {res['metrics']['memory']['patterns']}")
                seed_results.append(res)
            
            self.results[seed] = seed_results

        self.finalize_report()

    def finalize_report(self):
        print("\n\n" + "="*50)
        print("FINAL TAIS RESEARCH STRESS TEST REPORT")
        print("="*50)
        
        headers = ["Level", "Success %", "Avg Tick", "Avg Precision", "Avg Transfer Uses"]
        print(f"{headers[0]:<15} {headers[1]:<10} {headers[2]:<10} {headers[3]:<15} {headers[4]:<15}")
        
        levels = ["EASY", "MEDIUM", "HARD", "VERY_HARD", "SUPER_HARD", "EXTREMELY_HARD"]
        for i, lvl in enumerate(levels):
            successes = [self.results[s][i]['success'] for s in self.seeds]
            ticks = [self.results[s][i]['tick'] for s in self.seeds if self.results[s][i]['success']]
            precisions = [self.results[s][i]['metrics']['transfer_prior_precision'] for s in self.seeds]
            uses = [self.results[s][i]['metrics']['transfer_prior_uses'] for s in self.seeds]
            
            s_rate = (sum(successes) / len(self.seeds)) * 100
            a_tick = np.mean(ticks) if ticks else 0
            a_prec = np.mean(precisions) * 100
            a_uses = np.mean(uses)
            
            print(f"{lvl:<15} {s_rate:<10.1f} {a_tick:<10.1f} {a_prec:<15.1f} {a_uses:<15.1f}")

if __name__ == "__main__":
    # Test with 3 random seeds for statistical stability
    test = ResearchStressTest(seeds=[101, 202, 303])
    test.execute()
