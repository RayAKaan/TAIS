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
        """Classify functional action role from consequence and evaluate() delta."""
        try:
            score_before = world.evaluate(graph_before, mote_state)
            score_after = world.evaluate(graph_after, mote_state)
        except Exception:
            score_before = score_after = 0.0
        delta_score = score_after - score_before
        pred_error = abs(predicted - consequence.net)

        if not consequence.valid or consequence.net < -0.5:
            return "FAILED"
        if action.role_hint:
            return action.role_hint
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
            # predictions are recorded for error metrics and should_explore(),
            # but removed from the score formula.  See Phase 1.5 diagnostic:
            # no_prediction consistently beats full on first_task_success_tick
            # because early-domain predictions (cost-anchored valence fallback)
            # are systematically mismatched to the new reward scale and even
            # the EWM accumulates too slowly to help within a short eval horizon.
            historical = self.memory.episodic.action_value(action.name, domain=observation.domain)
            risk = self.memory.episodic.action_risk(action.name, domain=observation.domain)
            cost = action.compute_cost(observation, self.state())
            gating_factor = 1.0
            if historical < -0.1:
                gating_factor = math.exp(historical)
            transfer = gating_factor * effective_analogy_weight * transfer_boosts.get(action.name, 0.0)
            continuity_boost = 0.0
            if len(self.memory.episodic.episodes) > 0:
                last_ep = self.memory.episodic.episodes[-1]
                if last_ep.consequence.net > 0:
                    current_fp = self.memory._graph_fingerprint(observation)
                    if current_fp == last_ep.after_state_fingerprint:
                        for ep in self.memory.episodic.episodes:
                            if ep.state_fingerprint == current_fp and ep.consequence.net > 0:
                                if action.name == ep.transformation.name:
                                    continuity_boost = 10.0
                                    break
            score = historical + transfer + retrieval_boosts.get(action.name, 0.0) + continuity_boost - cost - self.meta.skepticism * risk
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
            return graph, cons, None

        predicted = self.memory.predict_action(action, observation)
        self.last_prediction = predicted
        new_graph, cons = world.act(graph, action, mote_state)
        action_role = self.classify_action_role(action, world, graph, new_graph, cons, mote_state, predicted)

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
        # Causal: record action→outcome
        if self.causal is not None and (self._engine_policy is None or self._engine_policy.use_causal_reasoning):
            positive = cons.net > 0
            outcome_concept = list(cons.concept_signals.keys())[0] if cons.concept_signals else "unknown"
            self.causal.record_action(tick, action.name, outcome_concept, positive)

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

        # ── Cognitive engine metrics ──
        if self.metacog is not None:
            result["metacog_confidence"] = round(self.metacog.get_confidence(), 3)
            result["metacog_exploration_rate"] = round(self.metacog.get_exploration_rate(), 3)
        if self.causal is not None:
            result["causal_links_count"] = len(self.causal.links)
            result["causal_is_causal_count"] = sum(1 for l in self.causal.links.values() if l.is_causal)
        if self.planner is not None:
            result["planner_active"] = self.planner.active_plan is not None
            result["planner_library_size"] = sum(len(plans) for plans in self.planner._plan_library.values())
        return result
