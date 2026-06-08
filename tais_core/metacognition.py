"""
tais_core.metacognition
=======================

Metacognitive engine for the universal mote.

Tracks prediction accuracy per action-role, modulates exploration
vs exploitation, and maintains a self-model of learning competence.

This is domain-agnostic: it works with any WorldInterface because it
operates on action-role strings and prediction error floats, not on
domain-specific concepts.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Tuple
from dataclasses import dataclass
from collections import defaultdict, deque


class PredictionTracker:
    """Rolling window of prediction correctness per strategy/action-role."""

    def __init__(self, window_size: int = 20):
        self.window_size = window_size
        self.strategies: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))

    def record(self, strategy: str, prediction: Any, outcome: Any, correct: bool):
        self.strategies[strategy].append({
            "strategy": strategy,
            "prediction": prediction,
            "outcome": outcome,
            "correct": correct,
        })

    def accuracy(self, strategy: str) -> float:
        if strategy not in self.strategies or not self.strategies[strategy]:
            return 0.5
        correct = sum(1 for r in self.strategies[strategy] if r["correct"])
        return correct / len(self.strategies[strategy])

    def best_strategy(self, strategies: List[str]) -> str:
        if not strategies:
            return "explore"
        scored = [(s, self.accuracy(s) + random.uniform(0, 0.05)) for s in strategies]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0]

    def to_dict(self) -> dict:
        return {
            s: {"accuracy": round(self.accuracy(s), 3), "samples": len(q)}
            for s, q in self.strategies.items()
        }


@dataclass
class SelfModel:
    """The mote's model of its own competence."""

    learning_speed: float = 0.5
    memory_reliability: float = 0.5
    social_trust_bias: float = 0.5
    exploration_tendency: float = 0.3
    planning_depth: int = 1
    prediction_count: int = 0

    def update_from_accuracy(self, accuracy: float, confidence: float):
        self.prediction_count += 1
        if self.prediction_count < 10:
            return
        lr = 0.05 * confidence
        self.learning_speed = self.learning_speed + lr * (accuracy - self.learning_speed)
        self.memory_reliability = min(
            1.0, max(0.1, self.memory_reliability + lr * (accuracy - 0.5) * 2)
        )
        self.exploration_tendency = max(
            0.05, min(0.8, self.exploration_tendency + lr * (0.5 - accuracy))
        )
        if accuracy > 0.7 and self.planning_depth < 3:
            self.planning_depth += 1
        elif accuracy < 0.3 and self.planning_depth > 1:
            self.planning_depth -= 1

    def to_dict(self) -> dict:
        return {
            "learning_speed": round(self.learning_speed, 3),
            "memory_reliability": round(self.memory_reliability, 3),
            "social_trust_bias": round(self.social_trust_bias, 3),
            "exploration_tendency": round(self.exploration_tendency, 3),
            "planning_depth": self.planning_depth,
            "prediction_count": self.prediction_count,
        }


class MetacognitiveEngine:
    """
    Self-monitoring engine for UniversalMote.

    Provides:
    - Prediction error tracking per action-role
    - Strategy selection (which action-role to prefer)
    - Self-model updates (learning speed, exploration rate)
    - Confidence estimation
    """

    def __init__(self):
        self.predictions = PredictionTracker()
        self.self_model = SelfModel()
        self.strategy_history: List[Tuple[int, str, float]] = []

    def select_strategy(self, tick: int, strategies: List[str], urgency: float = 0.5) -> str:
        """Pick the best strategy from candidates, with exploration noise."""
        strategy = self.predictions.best_strategy(strategies)
        if strategies and random.random() < self.self_model.exploration_tendency:
            alt = random.choice(strategies)
            if alt != strategy:
                strategy = alt
        self.strategy_history.append((tick, strategy, urgency))
        return strategy

    def record_outcome(
        self,
        strategy: str,
        prediction: Any,
        outcome: Any,
        correct: bool,
        tick: int,
    ):
        """Record whether a chosen strategy's prediction was correct."""
        self.predictions.record(strategy, prediction, outcome, correct)
        self.strategy_history.append((tick, strategy, 1.0 if correct else 0.0))
        self.self_model.prediction_count += 1
        if self.self_model.prediction_count % 10 == 0:
            overall = sum(self.predictions.accuracy(s) for s in self.predictions.strategies)
            n = len(self.predictions.strategies)
            self.self_model.update_from_accuracy(overall / max(n, 1), confidence=0.6)

    def record_prediction(self, tick: int, cue: str, expected: Any, confidence: float):
        self.predictions.record(
            "prediction",
            {"cue": cue, "expected": expected, "confidence": confidence},
            None,
            True,
        )
        self.self_model.prediction_count += 1

    def resolve_prediction(self, expected: Any, actual: Any):
        correct = expected == actual
        self.predictions.record("prediction", {"expected": expected}, {"actual": actual}, correct)
        if self.self_model.prediction_count >= 10 and self.self_model.prediction_count % 10 == 0:
            overall = sum(self.predictions.accuracy(s) for s in self.predictions.strategies)
            n = len(self.predictions.strategies)
            self.self_model.update_from_accuracy(overall / max(n, 1), confidence=0.6)

    def get_confidence(self) -> float:
        """Mean prediction accuracy across all tracked strategies."""
        accuracies = [self.predictions.accuracy(s) for s in self.predictions.strategies]
        return sum(accuracies) / max(len(accuracies), 1)

    def get_accuracy(self) -> float:
        return self.get_confidence()

    def get_exploration_rate(self) -> float:
        return self.self_model.exploration_tendency

    def to_dict(self) -> dict:
        return {
            "predictions": self.predictions.to_dict(),
            "self_model": self.self_model.to_dict(),
            "strategy_history": [(t, s, round(u, 2)) for t, s, u in self.strategy_history[-20:]],
        }
