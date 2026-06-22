"""
tais_core.mote
==============

Universal domain-agnostic mote.

This is intentionally small. It does not know chemistry, math, physics, or
GridWorld. It knows only:

    observe through a WorldInterface
    choose a Transformation
    predict consequence
    act
    receive Consequence
    update memory and energy

If this class must be edited to add a new domain, the base model has failed.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .engine_policy import EnginePolicyDecision, decide_engine_usage
from .memory import MoteMemory
from .memory_attentiondb import AttentionDBEpisodicMemory
from .reality import Consequence, RealityGraph, Transformation, WorldInterface
from .role_learning import LearnedRoleCompatibility
from .speech import SpeechOrgan
from .metacognition import MetacognitiveEngine
from .causal import CausalReasoningEngine
from .planning import HierarchicalPlanner
from .role_discovery import RoleDiscoveryEngine
from .structural_similarity import StructuralCompatibility
from .analogy_engine import StructuralAnalogyEngine
from .policy_transfer import CompositionalPolicy, HierarchicalPlannerV2


@dataclass
class CognitiveConfig:
    temperature: float = 0.7
    top_p: float = 0.9
    skepticism_weight: float = 0.25
    continuity_lock: float = 0.0


@dataclass
class MetaGenes:
    curiosity: float = 0.25
    skepticism: float = 0.25
    risk_tolerance: float = 0.35
    teaching_bias: float = 0.20
    memory_compression: float = 0.30
    analogy_bias: float = 0.35

    def mutate(self, sigma: float = 0.04) -> "MetaGenes":
        def clamp(x):
            return max(0.0, min(1.0, x))
        return MetaGenes(
            curiosity=clamp(self.curiosity + random.gauss(0, sigma)),
            skepticism=clamp(self.skepticism + random.gauss(0, sigma)),
            risk_tolerance=clamp(self.risk_tolerance + random.gauss(0, sigma)),
            teaching_bias=clamp(self.teaching_bias + random.gauss(0, sigma)),
            memory_compression=clamp(self.memory_compression + random.gauss(0, sigma)),
            analogy_bias=clamp(self.analogy_bias + random.gauss(0, sigma)),
        )


class UniversalMote:
    """A domain-agnostic mote operating over any WorldInterface."""

    _id = 0

    def __init__(self, energy: float = 100.0, parent_id: int = -1):
        UniversalMote._id += 1
        self.id = UniversalMote._id
        self.parent_id = parent_id
        self.energy = energy
        self.age = 0
        self.alive = True
        self.memory = AttentionDBEpisodicMemory(episodic_capacity=128)
        self.speech = SpeechOrgan(self.id)
        self.meta = MetaGenes()
        self.domain_history: List[str] = []
        self.total_reward = 0.0
        self.total_penalty = 0.0
        self.actions_taken = 0
        self.invalid_actions = 0
        self.last_prediction = 0.0
        self.last_consequence: Optional[Consequence] = None
        self.transfer_prior_uses = 0
        self.transfer_prior_total_strength = 0.0
        self.transfer_prior_correct = 0
        self.transfer_prior_incorrect = 0
        self._last_chosen_transfer_boost = 0.0
        self.domain_action_counts: Dict[str, int] = {}

        # ── Phase R5: prediction gating (opt-in, default preserves legacy behavior) ──
        self.use_prediction_in_score: bool = False
        self.prediction_score_weight: float = 0.25
        self.prediction_min_domain_observations: int = 0

        # ── Phase R6: learned role compatibility (opt-in, None = disabled) ──
        self.learned_role_compatibility: Optional[LearnedRoleCompatibility] = None
        self.use_learned_role_compatibility: bool = False

        # ── Cognitive engines (None = ablation mode, mote works as before) ──
        self.metacog: Optional[MetacognitiveEngine] = None
        self.causal: Optional[CausalReasoningEngine] = None
        self.planner: Optional[HierarchicalPlanner] = None

        # ── Phase A: engine selection policy ──
        self.use_engine_policy: bool = True
        self._engine_policy: Optional["EnginePolicyDecision"] = None
        self.config = CognitiveConfig()

        # ── Structural Transfer v2: genuine structural analogy without role labels ──
        self.role_discovery: Optional[RoleDiscoveryEngine] = None
        self.structural_compat: Optional[StructuralCompatibility] = None
        self.analogy_engine: Optional[StructuralAnalogyEngine] = None
        self.compositional_policy: Optional[CompositionalPolicy] = None
        self.planner_v2: Optional[HierarchicalPlannerV2] = None
        self._use_structural_transfer: bool = False

    def enable_cognitive_engines(
        self,
        metacognition: bool = True,
        causal_reasoning: bool = True,
        hierarchical_planning: bool = True,
    ):
        """Activate cognitive engines. Call after construction."""
        if metacognition:
            self.metacog = MetacognitiveEngine()
        if causal_reasoning:
            self.causal = CausalReasoningEngine()
        if hierarchical_planning:
            self.planner = HierarchicalPlanner()

    def enable_learned_role_compatibility(self, alpha: float = 0.3):
        self.learned_role_compatibility = LearnedRoleCompatibility(alpha=alpha)
        self.use_learned_role_compatibility = True

    def enable_structural_transfer(
        self,
        wl_iterations: int = 3,
        min_cluster_size: int = 2,
    ):
        """Activate structural transfer v2 engines.

        This replaces hand-coded role_hint, role_compatibility(), and
        single-step planning with:
        - RoleDiscoveryEngine: discovers roles from structural clustering
        - StructuralCompatibility: WL-kernel-based compatibility
        - StructuralAnalogyEngine: genuine subgraph matching
        - CompositionalPolicy: transfer of action sequences
        - HierarchicalPlannerV2: multi-step planning over transferred policies
        """
        self.role_discovery = RoleDiscoveryEngine(min_cluster_size=min_cluster_size)
        self.structural_compat = StructuralCompatibility(wl_iterations=wl_iterations)
        self.analogy_engine = StructuralAnalogyEngine(wl_iterations=wl_iterations)
        self.compositional_policy = CompositionalPolicy()
        self.planner_v2 = HierarchicalPlannerV2(compositional_policy=self.compositional_policy)
        self._use_structural_transfer = True

    def state(self, **extra) -> Dict[str, Any]:
        base = {
            "mote_id": self.id,
            "energy": self.energy,
            "age": self.age,
            "curiosity": self.meta.curiosity,
            "skepticism": self.meta.skepticism,
            "risk_tolerance": self.meta.risk_tolerance,
        }
        base.update(extra)
        return base

    def classify_action_role(
        self,
        action: Transformation,
        world: WorldInterface,
        graph_before: RealityGraph,
        graph_after: RealityGraph,
        consequence: Consequence,
        mote_state: Dict[str, Any],
        predicted: float,
    ) -> str:
        """Classify functional action role from consequence and evaluate() delta.

        When structural transfer v2 is enabled, this uses the
        RoleDiscoveryEngine to find a discovered role that matches
        the current (observation, action, consequence) triple.
        Falls back to the legacy classification when no discovered role matches.
        """
        # Structural Transfer v2: use discovered roles
        if self._use_structural_transfer and self.role_discovery is not None:
            discovered_role_id = self.role_discovery.record_experience(
                observation=graph_before,
                action=action,
                consequence=consequence,
                domain=world.domain_name,
                tick=mote_state.get("age", 0),
            )
            if discovered_role_id is not None:
                return discovered_role_id

        # Legacy role classification (fallback)
        try:
            score_before = world.evaluate(graph_before, mote_state)
            score_after = world.evaluate(graph_after, mote_state)
        except Exception:
            score_before = score_after = 0.0
        delta_score = score_after - score_before
        pred_error = abs(predicted - consequence.net)

        if not consequence.valid or consequence.net < -0.5:
            return "FAILED"
        if delta_score > 0.25 and consequence.net > 0:
            if action.universal_op in {"TRANSFORM", "COMPOSE"}:
                return "TRANSFORM_TOWARD_GOAL"
            return "APPROACH_GOOD"
        if action.universal_op == "MOVE_TOWARD" and consequence.net > 0:
            return "APPROACH_GOOD"
        if action.universal_op in {"VERIFY", "TEST"} and consequence.net >= 0:
            return "VERIFY_UNCERTAIN"
        if action.universal_op == "MOVE_AWAY" and consequence.net > 0:
            return "AVOID_BAD"
        if pred_error > 2.0 and consequence.net >= -0.5:
            return "EXPLORE_UNCERTAIN"
        if consequence.net >= 0:
            return "MAINTAIN_STABLE"
        return "UNCLASSIFIED"

    def choose_action(self, observation: RealityGraph, actions: List[Transformation], episode_tick: int = 0) -> Optional[Transformation]:
        if not actions:
            return None

        # ── Phase 8: Active Planning ──
        # If a plan exists and is valid, follow it. This makes planning load-bearing.
        if self.planner is not None:
            planned_action_name = self.planner.get_next_step()
            if planned_action_name is not None:
                for a in actions:
                    if a.name == planned_action_name:
                        return a

        # ── Phase 6: exploration cooling ──
        if episode_tick > 40:
            cooling = max(0.0, 1.0 - (episode_tick - 40) / 60)
            effective_curiosity = self.meta.curiosity * cooling
        else:
            effective_curiosity = self.meta.curiosity

        # ── Metacognitive exploration modulation ──
        # If metacog is active and confidence is low, boost exploration.
        # If confidence is high, suppress unnecessary exploration.
        explore = self.memory.should_explore(actions, curiosity=effective_curiosity, domain=observation.domain)
        if self.metacog is not None and (self._engine_policy is None or self._engine_policy.use_metacognition):
            confidence = self.metacog.get_confidence()
            explore_rate = self.metacog.get_exploration_rate()
            if confidence < 0.3 and random.random() < explore_rate:
                explore = True
            elif confidence > 0.7 and explore and random.random() > explore_rate:
                explore = False
        if explore:
            return random.choice(actions)

        # ── Phase 7: Costly Cultural Memory ──
        # When energy permits and confidence is low, pay energy to query the archive.
        if self.energy > 20.0 and random.random() < 0.05:
            cultural_hints = self.memory.cultural.query(observation.domain, n=1, energy_cost=1.0)
            if cultural_hints:
                self.energy -= 1.0
                hinted_action = cultural_hints[0].get("action")
                if hinted_action is not None:
                    for a in actions:
                        if a.name == hinted_action:
                            return a

        # Structural Transfer v2: discovered-role and analogy-based boosts
        # When v2 is enabled, legacy action_priors (which depend on hand-coded
        # role_compatibility() and infer_action_role() via role_hint) are skipped.
        structural_boosts: Dict[str, float] = {}
        transfer_boosts: Dict[str, float] = {}
        transfer_used = 0
        if self._use_structural_transfer:
            # Discovered role boosts (replaces role_compatibility)
            if self.role_discovery is not None:
                role_boosts, _role_used = self.role_discovery.transfer_action_boosts(observation, actions)
                structural_boosts.update(role_boosts)
            # Structural analogy boosts (replaces analogize + role matching)
            if self.analogy_engine is not None and self.memory.patterns.patterns:
                analogy_boosts = self.analogy_engine.compute_structural_boosts(
                    self.memory.patterns.patterns,
                    observation,
                    actions,
                )
                for k, v in analogy_boosts.items():
                    structural_boosts[k] = structural_boosts.get(k, 0.0) + v
            # Compositional policy check (replaces single-step planner)
            if self.planner_v2 is not None and self.planner_v2.active_plan is None:
                plan_action = self.planner_v2.plan(observation, actions)
                if plan_action is not None:
                    for a in actions:
                        if a.universal_op == plan_action:
                            structural_boosts[a.name] = structural_boosts.get(a.name, 0.0) + 5.0
        else:
            # Legacy: use hand-coded action_priors (only when v2 is disabled)
            transfer_boosts, transfer_used = self.memory.transfer_action_priors(observation, actions)
            if transfer_used:
                self.transfer_prior_uses += transfer_used
                self.transfer_prior_total_strength += sum(abs(v) for v in transfer_boosts.values())

        # Transfer priors should help early in a new domain, then yield to local
        # evidence. Otherwise old-domain confidence becomes negative transfer.
        local_exp = self.domain_action_counts.get(observation.domain, 0)
        transfer_decay_rate = 0.08
        effective_analogy_weight = self.meta.analogy_bias / (1.0 + transfer_decay_rate * local_exp)

        # ── Phase 6: AttentionDB retrieval boosts ──
        retrieval_boosts = self.memory.get_action_boosts(observation, actions, episode_tick)

        best_action = None
        best_score = float("-inf")
        best_transfer = 0.0
        for action in actions:
            historical = self.memory.episodic.action_value(action.name, domain=observation.domain)
            risk = self.memory.episodic.action_risk(action.name, domain=observation.domain)
            cost = action.compute_cost(observation, self.state())
            gating_factor = 1.0
            if historical < -0.1:
                gating_factor = math.exp(historical)
            if self._use_structural_transfer:
                transfer = structural_boosts.get(action.name, 0.0)
            else:
                transfer = gating_factor * effective_analogy_weight * transfer_boosts.get(action.name, 0.0)
            score = historical + transfer + retrieval_boosts.get(action.name, 0.0) - cost - self.meta.skepticism * risk
            # Structural Transfer v2: boost at full strength (no analogy_bias damping)
            if self._use_structural_transfer:
                sb = structural_boosts.get(action.name, 0.0)
                score += sb
            if self.use_prediction_in_score:
                n = self.memory.prediction.domain_observation_count(observation.domain)
                if n >= self.prediction_min_domain_observations:
                    score += self.prediction_score_weight * self.memory.predict_action(action, observation)
            if score > best_score:
                best_score = score
                best_action = action
                best_transfer = transfer
        self._last_chosen_transfer_boost = best_transfer
        return best_action or random.choice(actions)

    def step(
        self,
        world: WorldInterface,
        graph: RealityGraph,
        mote_position: Any = None,
        tick: int = 0,
        extra_state: Optional[Dict[str, Any]] = None,
    ) -> Tuple[RealityGraph, Consequence, Optional[Transformation]]:
        """One observe→predict→act→learn cycle."""
        if not self.alive:
            return graph, Consequence(valid=False, penalty=999, explanation={"why": "dead"}), None

        mote_state = self.state(**(extra_state or {}))
        observation = world.observe(graph, mote_position)
        actions = world.valid_actions(observation, mote_state)
        action = self.choose_action(observation, actions, episode_tick=tick)
        if action is None:
            cons = Consequence(penalty=0.2, valid=False, concept_signals={"VOID": 1.0}, explanation={"why": "no actions"})
            self.energy += cons.net
            self.last_consequence = cons
            if self.causal is not None:
                self.causal.record_no_action(tick, "VOID", False)
            return graph, cons, None

        predicted = self.memory.predict_action(action, observation)
        self.last_prediction = predicted
        new_graph, cons = world.act(graph, action, mote_state)
        action_role = self.classify_action_role(action, world, graph, new_graph, cons, mote_state, predicted)

        # Structural Transfer v2: feed experience to compositional policy
        if self._use_structural_transfer and self.compositional_policy is not None:
            skey = ""
            etypes = frozenset()
            rtypes = frozenset()
            if self.role_discovery is not None:
                skey, etypes, rtypes = self.role_discovery.compute_structural_key_rich(observation)
            self.compositional_policy.learn_from_episodes([{
                "observation": observation,
                "action": action,
                "consequence": cons,
                "domain": world.domain_name,
                "tick": tick,
                "structural_key": skey,
                "outcome_net": cons.net,
                "valid": cons.valid,
                "universal_op": action.universal_op,
                "entity_types": etypes,
                "relation_types": rtypes,
            }])

        # ── Phase R6: learned role compatibility update (opt-in) ──
        if self.learned_role_compatibility is not None:
            self.learned_role_compatibility.update(
                role=action_role,
                op=action.universal_op,
                outcome_net=cons.net,
            )

        # ── Phase A: engine selection policy ──
        if self.use_engine_policy and actions:
            self._engine_policy = decide_engine_usage(actions)
        else:
            self._engine_policy = None

        # ── Cognitive engine updates (None-safe, policy-gated) ────────
        # Causal: record action→outcome + no_action counterfactual
        if self.causal is not None and (self._engine_policy is None or self._engine_policy.use_causal_reasoning):
            positive = cons.net > 0
            outcome_concept = list(cons.concept_signals.keys())[0] if cons.concept_signals else "unknown"
            self.causal.record_action(tick, action.name, outcome_concept, positive)
            self.causal.record_no_action(tick, outcome_concept, not positive)

        # Metacognitive: record prediction accuracy
        if self.metacog is not None and (self._engine_policy is None or self._engine_policy.use_metacognition):
            pred_correct = abs(predicted - cons.net) < 1.0
            self.metacog.record_outcome(
                strategy=action_role,
                prediction={"expected": predicted, "action": action.name},
                outcome={"actual": cons.net, "role": action_role},
                correct=pred_correct,
                tick=tick,
            )

        # Planner: advance on success, rollback on failure
        if self.planner is not None and (self._engine_policy is None or self._engine_policy.use_planning):
            # ── Phase 8: Auto-generate plan if goal detected and no plan active ──
            if self.planner.active_plan is None and self.causal is not None:
                goal_concept = "SUCCESS"
                self.planner.plan_for_goal({"type": goal_concept}, self.causal)
            if self.planner.active_plan is not None:
                if cons.net > 0:
                    self.planner.advance_step()
                elif cons.net < -0.5:
                    self.planner.rollback()

        # Planner v2: advance/rollback compositional policy plan
        if self._use_structural_transfer and self.planner_v2 is not None:
            if cons.net > 0:
                self.planner_v2.advance_on_success()
            elif cons.net < -0.5:
                self.planner_v2.rollback_on_failure()

        action_cost = action.compute_cost(observation, mote_state)
        self.energy += cons.net - action_cost
        self.total_reward += cons.reward
        self.total_penalty += cons.penalty + action_cost
        self.actions_taken += 1
        self.invalid_actions += 0 if cons.valid else 1
        self.domain_action_counts[world.domain_name] = self.domain_action_counts.get(world.domain_name, 0) + 1
        if abs(self._last_chosen_transfer_boost) > 1e-9:
            if cons.net > 0:
                self.transfer_prior_correct += 1
            elif cons.net < 0:
                self.transfer_prior_incorrect += 1
        self.age += 1
        self.last_consequence = cons
        self.domain_history.append(world.domain_name)

        self.memory.record_episode(
            state_before=observation,
            state_after=new_graph,
            transformation=action,
            consequence=cons,
            predicted=predicted,
            domain=world.domain_name,
            tick=tick,
            action_role=action_role,
        )

        if self.energy <= 0:
            self.alive = False

        return new_graph, cons, action

    def reproduce(self) -> "UniversalMote":
        self.energy /= 2
        child = UniversalMote(energy=self.energy, parent_id=self.id)
        child.meta = self.meta.mutate()
        child.speech = self.speech.spawn_child(child.id)
        # Cognitive engines: children inherit self-model parameters but get fresh trackers
        if self.metacog is not None:
            child.enable_cognitive_engines(metacognition=True, causal_reasoning=False, hierarchical_planning=False)
            child.metacog.self_model.learning_speed = self.metacog.self_model.learning_speed
            child.metacog.self_model.exploration_tendency = self.metacog.self_model.exploration_tendency
            child.metacog.self_model.memory_reliability = self.metacog.self_model.memory_reliability
        # Causal and planner are NOT inherited — child must learn its own causal model.
        # This is intentional: inherited causal beliefs would be domain-specific.
        # Pattern/episodic memory is not copied wholesale. The child receives
        # speech priors genetically; cultural memory is a separate mechanism.
        return child

    def metrics(self) -> Dict[str, Any]:
        mean_pred = self.memory.prediction.mean_error()
        result = {
            "id": self.id,
            "energy": round(self.energy, 3),
            "age": self.age,
            "alive": self.alive,
            "actions": self.actions_taken,
            "invalid_actions": self.invalid_actions,
            "total_reward": round(self.total_reward, 3),
            "total_penalty": round(self.total_penalty, 3),
            "mean_prediction_error": None if mean_pred == float("inf") else round(mean_pred, 3),
            "prediction_improving": self.memory.prediction.error_trend() < 0,
            "transfer_prior_uses": self.transfer_prior_uses,
            "transfer_prior_total_strength": round(self.transfer_prior_total_strength, 3),
            "transfer_prior_correct": self.transfer_prior_correct,
            "transfer_prior_incorrect": self.transfer_prior_incorrect,
            "transfer_prior_precision": round(self.transfer_prior_correct / max(1, self.transfer_prior_correct + self.transfer_prior_incorrect), 3),
            "memory": self.memory.summary(),
            "speech": self.speech.stats(),
            "domains": sorted(set(self.domain_history)),
        }

        # ── Research telemetry ──
        transfer_precision = round(
            self.transfer_prior_correct / max(1, self.transfer_prior_correct + self.transfer_prior_incorrect), 3
        )
        result["transfer_precision"] = transfer_precision
        n_ep = len(self.memory.episodic.episodes)
        result["structural_recall"] = round(
            min(1.0, n_ep / max(1, self.memory.episodic.capacity)), 3
        )
        pred_err = self.memory.prediction.mean_error()
        result["sequence_integrity"] = round(
            max(0.0, 1.0 - pred_err / 10.0) if pred_err != float("inf") else 0.0, 3
        )
        result["temperature"] = self.config.temperature
        result["top_p"] = self.config.top_p
        result["skepticism_weight"] = self.config.skepticism_weight
        result["continuity_lock"] = self.config.continuity_lock

        # ── Cognitive engine metrics ──
        if self.metacog is not None:
            result["metacog_confidence"] = round(self.metacog.get_confidence(), 3)
            result["metacog_exploration_rate"] = round(self.metacog.get_exploration_rate(), 3)
        if self.causal is not None:
            result["causal_links_count"] = len(self.causal.links)
            result["causal_is_causal_count"] = sum(1 for l in self.causal.links if l.is_causal)
        if self.planner is not None:
            result["planner_active"] = self.planner.active_plan is not None
            result["planner_library_size"] = sum(len(plans) for plans in self.planner._plan_library.values())

        # ── Structural Transfer v2 metrics ──
        if self._use_structural_transfer:
            if self.role_discovery is not None:
                result["discovered_roles"] = len(self.role_discovery._roles)
                result["role_discovery_records"] = len(self.role_discovery._records)
            if self.compositional_policy is not None:
                result["policy_sequences"] = len(self.compositional_policy._sequences)
            if self.planner_v2 is not None:
                result["planner_v2_active"] = self.planner_v2.active_plan is not None
        return result
