"""AttentionDB-backed episodic memory retrieval for TAIS."""

from __future__ import annotations
import math
from typing import Any, Dict, List, Optional, Tuple
from .reality import RealityGraph, Transformation
from .memory import Episode, EpisodicMemory

class AttentionDBEpisodicMemory(EpisodicMemory):
    """
    Episodic memory that uses multi-head attention to retrieve relevant past experiences.

    Simulates the behavior of AttentionDB for cross-layer integration.
    """

    def __init__(self, capacity: int = 100, heads: int = 3):
        super().__init__(capacity=capacity)
        self.heads = heads
        self.head_weights = [0.4, 0.2, 0.4]

    def retrieve(
        self,
        current_graph: RealityGraph,
        available_actions: List[Transformation],
        tick: int,
        k: int = 5
    ) -> List[Tuple[Episode, float]]:
        """Queries the memory using multi-head attention."""
        if not self.episodes:
            return []

        scored_episodes = []

        for ep in self.episodes:
            # Head 1: Semantic Similarity (Action/Role overlap)
            semantic_score = 0.0
            for action in available_actions:
                if action.name == ep.transformation.name:
                    semantic_score = max(semantic_score, 1.0)
                elif action.universal_op == ep.transformation.universal_op:
                    semantic_score = max(semantic_score, 0.5)

            # Head 2: Temporal Recency
            temporal_score = math.exp(-(tick - ep.tick) / 50.0)

            # Head 3: Structural Similarity (Graph overlap)
            structural_score = 0.5

            # Weighted Fusion
            total_score = (
                self.head_weights[0] * semantic_score +
                self.head_weights[1] * temporal_score +
                self.head_weights[2] * structural_score
            )

            scored_episodes.append((ep, total_score))

        return sorted(scored_episodes, key=lambda x: x[1], reverse=True)[:k]

    def get_action_boosts(self, current_graph: RealityGraph, actions: List[Transformation], tick: int) -> Dict[str, float]:
        """Calculates action biases based on retrieved relevant episodes."""
        relevant = self.retrieve(current_graph, actions, tick)
        boosts = {a.name: 0.0 for a in actions}

        for ep, score in relevant:
            if ep.consequence.net > 0:
                for action in actions:
                    if action.name == ep.transformation.name:
                        boosts[action.name] += score * ep.consequence.net
                    elif action.universal_op == ep.transformation.universal_op:
                        boosts[action.name] += score * ep.consequence.net * 0.5
            elif ep.consequence.net < 0:
                for action in actions:
                    if action.name == ep.transformation.name:
                        boosts[action.name] -= score * abs(ep.consequence.net)

        return boosts
