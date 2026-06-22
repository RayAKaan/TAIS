"""
tais_core.open_ended_learning
==============================

AGI Roadmap Step 5: Open-ended learning with curiosity and self-evaluation.

This module implements the mechanisms that drive the mote to independently
set learning goals, explore novel situations, and evaluate its own competence.

Five components:
    1. CuriosityDrive — intrinsic motivation from novelty + prediction error
    2. SchemaGapDetector — identifies what the mote doesn't know
    3. GoalGenerator — converts gaps into prioritized learning goals
    4. ExplorationController — decides when to explore vs exploit
    5. SelfEvaluator — measures competence across domains
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .reality import Consequence, GraphPattern, RealityGraph
from .schema_learning import AbstractSchema, SchemaLearner
from .structural_similarity import wl_relabeled_graph, wl_similarity


# ─── CURIOSITY DRIVE ─────────────────────────────────────────────────────────


@dataclass
class NoveltyRecord:
    """Record of a graph's novelty for curiosity decay."""

    structural_key: str
    times_seen: int = 0
    last_seen_tick: int = 0
    peak_similarity: float = 0.0
    prediction_errors: List[float] = field(default_factory=list)


class CuriosityDrive:
    """Intrinsic motivation engine driven by structural novelty.

    Curiosity comes from three sources:
    1. Novelty decay — graphs become less interesting the more you see them
    2. Prediction error — graphs that surprised you are more interesting
    3. Schema gaps — structural patterns you don't have schemas for

    The curiosity signal is used by ExplorationController to decide
    when to explore vs exploit.
    """

    def __init__(
        self,
        novelty_decay_rate: float = 0.3,
        prediction_error_weight: float = 0.4,
        schema_gap_weight: float = 0.3,
        max_history: int = 500,
    ):
        self.novelty_decay_rate = novelty_decay_rate
        self.prediction_error_weight = prediction_error_weight
        self.schema_gap_weight = schema_gap_weight
        self.max_history = max_history

        self._seen: Dict[str, NoveltyRecord] = {}
        self._tick: int = 0
        self._curiosity_history: List[float] = []

    def observe(
        self,
        graph: RealityGraph,
        prediction_error: float = 0.0,
        schema_learner: Optional[SchemaLearner] = None,
    ) -> float:
        """Observe a graph and compute curiosity signal.

        Returns a curiosity score in [0, 1] where higher = more interesting.
        """
        self._tick += 1

        # Compute structural key
        etypes = sorted(set(e.etype for e in graph.entities()))
        rtypes = sorted(set(r.rtype for r in graph.relations()))
        n = len(graph._entities)
        s_key = f"E[{','.join(etypes)}]_R[{','.join(rtypes)}]_N{n}"

        if s_key not in self._seen:
            self._seen[s_key] = NoveltyRecord(
                structural_key=s_key, times_seen=0
            )

        record = self._seen[s_key]
        record.times_seen += 1
        record.last_seen_tick = self._tick
        if prediction_error > 0:
            record.prediction_errors.append(prediction_error)
            # Keep recent errors only
            if len(record.prediction_errors) > 20:
                record.prediction_errors = record.prediction_errors[-20:]

        # 1. Novelty score (decays with times seen)
        novelty = math.exp(-self.novelty_decay_rate * (record.times_seen - 1))

        # 2. Prediction error score
        if record.prediction_errors:
            avg_error = sum(record.prediction_errors) / len(record.prediction_errors)
            error_score = min(1.0, avg_error * 2)
        else:
            error_score = 0.0

        # 3. Schema gap score
        gap_score = 0.0
        if schema_learner is not None:
            matches = schema_learner.match_graph(graph)
            gap_score = 1.0 - min(1.0, len(matches) * 0.25)

        # Combine
        curiosity = (
            0.4 * novelty
            + self.prediction_error_weight * error_score
            + self.schema_gap_weight * gap_score
        )

        self._curiosity_history.append(curiosity)
        if len(self._curiosity_history) > self.max_history:
            self._curiosity_history = self._curiosity_history[-self.max_history:]

        return min(1.0, max(0.0, curiosity))

    def get_novelty(self, graph: RealityGraph) -> float:
        """Get the novelty score for a graph (without updating)."""
        etypes = sorted(set(e.etype for e in graph.entities()))
        rtypes = sorted(set(r.rtype for r in graph.relations()))
        n = len(graph._entities)
        s_key = f"E[{','.join(etypes)}]_R[{','.join(rtypes)}]_N{n}"

        record = self._seen.get(s_key)
        if record is None:
            return 1.0  # Completely novel

        return math.exp(-self.novelty_decay_rate * (record.times_seen - 1))

    def get_average_curiosity(self, window: int = 50) -> float:
        """Get average curiosity over recent window."""
        if not self._curiosity_history:
            return 0.0
        recent = self._curiosity_history[-window:]
        return sum(recent) / len(recent)

    def reset(self):
        self._seen.clear()
        self._curiosity_history.clear()

    def to_dict(self) -> dict:
        return {
            "unique_graphs_seen": len(self._seen),
            "total_observations": sum(r.times_seen for r in self._seen.values()),
            "average_curiosity": round(self.get_average_curiosity(), 4),
            "tick": self._tick,
        }


# ─── SCHEMA GAP DETECTOR ────────────────────────────────────────────────────


@dataclass
class SchemaGap:
    """A detected gap in the mote's understanding."""

    gap_type: str
    description: str
    structural_key: Optional[str] = None
    severity: float = 0.5  # 0-1, how important to fill this gap
    domain: str = ""
    tick: int = 0


class SchemaGapDetector:
    """Identify what the mote doesn't know but should.

    Types of gaps:
    1. no_schema — encountered a structural pattern with no matching schema
    2. no_effective_action — recognized the situation but no good action
    3. low_confidence — schemas exist but below promotion threshold
    4. no_causal_understanding — no causal effect data for this structural key
    """

    def __init__(self):
        self._gaps: List[SchemaGap] = []
        self._tick: int = 0

    def detect_gaps(
        self,
        graph: RealityGraph,
        schema_learner: SchemaLearner,
        consequence: Optional[Consequence] = None,
    ) -> List[SchemaGap]:
        """Detect gaps in understanding for a given observation.

        Returns list of SchemaGap objects discovered.
        """
        self._tick += 1
        gaps: List[SchemaGap] = []

        # Structural key for this graph
        etypes = sorted(set(e.etype for e in graph.entities()))
        rtypes = sorted(set(r.rtype for r in graph.relations()))
        s_key = f"E[{','.join(etypes)}]_R[{','.join(rtypes)}]"

        # Gap 1: No matching schema
        matches = schema_learner.match_graph(graph)
        if not matches:
            gap = SchemaGap(
                gap_type="no_schema",
                description=f"No schema matches structural key {s_key}",
                structural_key=s_key,
                severity=0.7,
                domain=graph.domain,
                tick=self._tick,
            )
            gaps.append(gap)

        # Gap 2: Low confidence in best match
        elif matches and matches[0][1] < schema_learner.promote_threshold:
            schema, score = matches[0]
            gap = SchemaGap(
                gap_type="low_confidence",
                description=f"Schema '{schema.name}' has low confidence ({score:.2f})",
                structural_key=s_key,
                severity=0.5 * (1.0 - score),
                domain=graph.domain,
                tick=self._tick,
            )
            gaps.append(gap)

        # Gap 3: No effective action
        if consequence is not None and consequence.penalty > consequence.reward:
            # Bad outcome — we need a better action
            gap = SchemaGap(
                gap_type="no_effective_action",
                description=f"No effective action in situation {s_key} (penalty={consequence.penalty})",
                structural_key=s_key,
                severity=0.8,
                domain=graph.domain,
                tick=self._tick,
            )
            gaps.append(gap)

        self._gaps.extend(gaps)
        return gaps

    def get_all_gaps(self) -> List[SchemaGap]:
        return list(self._gaps)

    def get_unresolved_gaps(self) -> List[SchemaGap]:
        """Get gaps that haven't been addressed yet."""
        return [g for g in self._gaps if g.severity > 0.3]

    def resolve_gap(self, gap: SchemaGap):
        """Mark a gap as resolved by reducing its severity."""
        gap.severity *= 0.3

    def to_dict(self) -> dict:
        return {
            "total_gaps_detected": len(self._gaps),
            "unresolved": len(self.get_unresolved_gaps()),
            "gap_types": dict(
                Counter(g.gap_type for g in self._gaps)
            ),
        }


# ─── GOAL GENERATOR ──────────────────────────────────────────────────────────


@dataclass
class LearningGoal:
    """A self-generated learning goal."""

    goal_id: str
    description: str
    priority: float  # 0-1, higher = more urgent
    gap_type: str
    structural_key: Optional[str] = None
    created_tick: int = 0
    achieved: bool = False
    attempts: int = 0


class GoalGenerator:
    """Convert schema gaps into prioritized learning goals.

    The generator:
    1. Takes gaps from SchemaGapDetector
    2. Generates specific learning goals
    3. Prioritizes by severity and achievability
    4. Tracks progress toward each goal
    """

    def __init__(self, max_active_goals: int = 5):
        self.max_active_goals = max_active_goals
        self._goals: Dict[str, LearningGoal] = {}
        self._tick: int = 0
        self._goal_counter: int = 0

    def generate_goals(
        self,
        gaps: List[SchemaGap],
    ) -> List[LearningGoal]:
        """Generate learning goals from schema gaps.

        Returns new goals, prioritizing the most severe gaps.
        """
        self._tick += 1
        new_goals: List[LearningGoal] = []

        # Sort gaps by severity
        sorted_gaps = sorted(gaps, key=lambda g: g.severity, reverse=True)

        for gap in sorted_gaps:
            if len(self._goals) >= self.max_active_goals:
                break

            # Check if we already have a goal for this gap
            already_exists = any(
                g.structural_key == gap.structural_key
                and g.gap_type == gap.gap_type
                and not g.achieved
                for g in self._goals.values()
            )
            if already_exists:
                continue

            self._goal_counter += 1
            goal = LearningGoal(
                goal_id=f"goal_{self._goal_counter}",
                description=self._generate_description(gap),
                priority=gap.severity,
                gap_type=gap.gap_type,
                structural_key=gap.structural_key,
                created_tick=self._tick,
            )
            self._goals[goal.goal_id] = goal
            new_goals.append(goal)

        return new_goals

    def _generate_description(self, gap: SchemaGap) -> str:
        """Generate a human-readable goal description from a gap."""
        templates = {
            "no_schema": "Understand the structural pattern in {key}",
            "low_confidence": "Gather more evidence about the situation in {key}",
            "no_effective_action": "Find an effective action for {key}",
            "no_causal_understanding": "Learn causal relationships in {key}",
        }
        template = templates.get(
            gap.gap_type, "Learn more about {key}"
        )
        return template.format(
            key=gap.structural_key or gap.description
        )

    def mark_achieved(self, goal_id: str):
        """Mark a goal as achieved."""
        goal = self._goals.get(goal_id)
        if goal:
            goal.achieved = True

    def get_active_goals(self) -> List[LearningGoal]:
        return [
            g for g in self._goals.values()
            if not g.achieved
        ]

    def get_achieved_goals(self) -> List[LearningGoal]:
        return [
            g for g in self._goals.values()
            if g.achieved
        ]

    def to_dict(self) -> dict:
        active = self.get_active_goals()
        return {
            "active_goals": [
                {
                    "id": g.goal_id,
                    "description": g.description,
                    "priority": round(g.priority, 3),
                    "type": g.gap_type,
                    "attempts": g.attempts,
                }
                for g in active
            ],
            "achieved": len(self.get_achieved_goals()),
            "total_goals": len(self._goals),
        }


# ─── EXPLORATION CONTROLLER ──────────────────────────────────────────────────


class ExplorationController:
    """Decide when to explore vs exploit.

    Exploration probability is dynamic:
    - Base rate: 0.1
    + Bump from curiosity: 0.3 * average_curiosity
    + Bump from active goals: 0.2 * sqrt(active_goals/max_goals)
    - Decay over time: 0.9^tick
    - Reward-aware payoff: reduces exploration if exploit consistently pays more
    - Energy safety: suppresses exploration when energy is low
    - Schema confidence: explores less when domain is well-understood
    """

    def __init__(
        self,
        base_explore_rate: float = 0.1,
        curiosity_influence: float = 0.3,
        goal_influence: float = 0.2,
        decay_rate: float = 0.999,
        energy_safety_margin: float = 20.0,
        explore_reward_window: int = 50,
    ):
        self.base_explore_rate = base_explore_rate
        self.curiosity_influence = curiosity_influence
        self.goal_influence = goal_influence
        self.decay_rate = decay_rate
        self.energy_safety_margin = energy_safety_margin
        self.explore_reward_window = explore_reward_window

        self._tick = 0
        self._exploration_history: List[bool] = []
        self._explore_rewards: List[float] = []
        self._exploit_rewards: List[float] = []
        self._explore_payoff: float = 0.0

    def record_outcome(self, was_explore: bool, reward: float):
        """Record whether exploration or exploitation paid off.

        Positive payoff means exploring yields higher rewards than exploiting.
        """
        if was_explore:
            self._explore_rewards.append(reward)
            if len(self._explore_rewards) > self.explore_reward_window:
                self._explore_rewards.pop(0)
        else:
            self._exploit_rewards.append(reward)
            if len(self._exploit_rewards) > self.explore_reward_window:
                self._exploit_rewards.pop(0)

        explore_avg = (
            sum(self._explore_rewards) / max(1, len(self._explore_rewards))
        )
        exploit_avg = (
            sum(self._exploit_rewards) / max(1, len(self._exploit_rewards))
        )
        self._explore_payoff = explore_avg - exploit_avg

    def should_explore(
        self,
        curiosity_drive: CuriosityDrive,
        goal_generator: GoalGenerator,
        current_energy: Optional[float] = None,
        schema_confidence: Optional[float] = None,
    ) -> bool:
        """Decide whether to explore in the current step.

        Args:
            curiosity_drive: Provides curiosity signal
            goal_generator: Provides active goals
            current_energy: If provided, reduces exploration when energy is low
            schema_confidence: If provided, reduces exploration when domain is well-understood
        """
        self._tick += 1

        # Base rate with decay
        base = self.base_explore_rate * (self.decay_rate ** self._tick)

        # Curiosity bump
        curiosity = curiosity_drive.get_average_curiosity()
        curiosity_bump = self.curiosity_influence * curiosity

        # Goal bump
        active_goals = goal_generator.get_active_goals()
        goal_bump = self.goal_influence * math.sqrt(
            len(active_goals) / max(1, goal_generator.max_active_goals)
        )

        explore_prob = base + curiosity_bump + goal_bump

        # Reward-aware modulation
        if self._explore_payoff < -0.5:
            explore_prob *= 0.7
        elif self._explore_payoff > 0.5:
            explore_prob *= 1.3

        # Energy safety: suppress exploration when low energy
        if current_energy is not None and current_energy < self.energy_safety_margin:
            explore_prob *= 0.5

        # Schema confidence: explore less when domain is well-understood
        if schema_confidence is not None:
            explore_prob *= max(0.2, 1.0 - 0.5 * schema_confidence)

        explore_prob = min(0.95, max(0.01, explore_prob))

        decision = random.random() < explore_prob
        self._exploration_history.append(decision)

        return decision

    def get_exploration_rate(self) -> float:
        """Get the current exploration probability."""
        if not self._exploration_history:
            return self.base_explore_rate
        return sum(self._exploration_history[-100:]) / min(100, len(self._exploration_history))

    def to_dict(self) -> dict:
        d = {
            "exploration_rate": round(self.get_exploration_rate(), 4),
            "explore_payoff": round(self._explore_payoff, 4),
            "total_explorations": sum(1 for d in self._exploration_history if d),
            "total_decisions": len(self._exploration_history),
        }
        if self._explore_rewards:
            d["mean_explore_reward"] = round(
                sum(self._explore_rewards) / len(self._explore_rewards), 4
            )
        if self._exploit_rewards:
            d["mean_exploit_reward"] = round(
                sum(self._exploit_rewards) / len(self._exploit_rewards), 4
            )
        return d


# ─── SELF EVALUATOR ──────────────────────────────────────────────────────────


@dataclass
class CompetenceScore:
    """A competence measurement for a specific domain or skill."""

    domain: str
    schema_coverage: float  # fraction of observations that match known schemas
    causal_coverage: float  # fraction of structural keys with causal data
    average_confidence: float  # average confidence of matched schemas
    success_rate: float  # fraction of recent actions that succeeded
    overall: float  # combined competence score


class SelfEvaluator:
    """Measure the mote's competence across domains.

    Competence is computed from:
    1. Schema coverage — how well the mote understands the domain structure
    2. Causal coverage — how well the mote knows action effects
    3. Action success rate — how often chosen actions succeed
    4. Confidence calibration — how well confidence matches actual outcomes
    """

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self._outcomes: Dict[str, List[bool]] = defaultdict(list)
        self._domain_observations: Dict[str, int] = defaultdict(int)

    def record_outcome(
        self,
        domain: str,
        structural_key: str,
        success: bool,
        schema_confidence: float = 0.0,
    ):
        """Record an action outcome for competence evaluation."""
        self._outcomes[domain].append(success)
        self._domain_observations[domain] += 1

        # Bound history
        if len(self._outcomes[domain]) > self.window_size * 2:
            self._outcomes[domain] = self._outcomes[domain][-self.window_size:]

    def evaluate(
        self,
        domain: str,
        schema_learner: SchemaLearner,
        causal_keys: Set[str],
    ) -> CompetenceScore:
        """Evaluate competence in a specific domain."""
        # Schema coverage
        all_schemas = schema_learner.get_all_schemas()
        schema_coverage = min(1.0, len(all_schemas) / 10) if all_schemas else 0.0

        # Average schema confidence
        if all_schemas:
            avg_confidence = sum(s.confidence for s in all_schemas) / len(all_schemas)
        else:
            avg_confidence = 0.0

        # Causal coverage
        total_keys = max(1, len(self._outcomes))
        causal_coverage = len(causal_keys) / total_keys

        # Success rate
        outcomes = self._outcomes.get(domain, [])
        recent = outcomes[-self.window_size:] if outcomes else []
        success_rate = sum(recent) / len(recent) if recent else 0.0

        # Overall competence
        overall = (
            0.25 * schema_coverage
            + 0.25 * causal_coverage
            + 0.25 * avg_confidence
            + 0.25 * success_rate
        )

        return CompetenceScore(
            domain=domain,
            schema_coverage=schema_coverage,
            causal_coverage=causal_coverage,
            average_confidence=avg_confidence,
            success_rate=success_rate,
            overall=overall,
        )

    def evaluate_global(
        self,
        schema_learner: SchemaLearner,
        all_causal_keys: Set[str],
    ) -> CompetenceScore:
        """Evaluate overall competence across all domains."""
        domains = list(self._domain_observations.keys())
        if not domains:
            return CompetenceScore(
                domain="global",
                schema_coverage=0.0,
                causal_coverage=0.0,
                average_confidence=0.0,
                success_rate=0.0,
                overall=0.0,
            )

        # Aggregate across domains
        scores = [
            self.evaluate(d, schema_learner, all_causal_keys)
            for d in domains
        ]

        return CompetenceScore(
            domain="global",
            schema_coverage=sum(s.schema_coverage for s in scores) / len(scores),
            causal_coverage=sum(s.causal_coverage for s in scores) / len(scores),
            average_confidence=sum(s.average_confidence for s in scores) / len(scores),
            success_rate=sum(s.success_rate for s in scores) / len(scores),
            overall=sum(s.overall for s in scores) / len(scores),
        )

    def to_dict(self) -> dict:
        return {
            "domains": dict(self._domain_observations),
            "total_outcomes": sum(len(v) for v in self._outcomes.values()),
        }
