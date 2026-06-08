"""
Temporal memory system for TAIS Swarm V6.

Replaces V5.5's simple location memory with:
- Episodic narrative (what happened, when, outcome)
- Bayesian temporal decay (P(resource still there | time elapsed)
- Expected resource duration per type
- Confidence based on recency, repetition, and outcome consistency
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque

from ..engine.config import MemoryConfig


@dataclass
class EpisodicEvent:
    """A single episode in the mote's life."""
    tick: int
    event_type: str
    concept: str
    x: float
    y: float
    outcome: str
    energy_delta: float
    hydration_delta: float
    related_mote_id: Optional[int] = None
    utterance_tokens: Optional[List[str]] = None

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "event_type": self.event_type,
            "concept": self.concept,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "outcome": self.outcome,
            "energy_delta": round(self.energy_delta, 2),
            "hydration_delta": round(self.hydration_delta, 2),
            "related_mote_id": self.related_mote_id,
            "utterance_tokens": self.utterance_tokens,
        }


@dataclass
class MemoryItemV6:
    """A memory of a resource, danger, or location."""
    concept: str
    x: float
    y: float
    value: float
    confidence: float
    tick_created: int
    tick_last_updated: int
    tick_last_accessed: int
    access_count: int = 0
    positive_outcomes: int = 0
    negative_outcomes: int = 0
    landmark_id: Optional[int] = None
    source: str = "sense"
    expected_duration: float = 100.0
    observed_duration: Optional[float] = None

    @property
    def age(self, current_tick: int = 0) -> int:
        return current_tick - self.tick_created

    @property
    def time_since_update(self, current_tick: int = 0) -> int:
        return current_tick - self.tick_last_updated

    def bayesian_relevance(self, current_tick: int, concept_durations: Dict[str, float]) -> float:
        age = self.age(current_tick)
        expected = concept_durations.get(self.concept, self.expected_duration)
        temporal_likelihood = math.exp(-age / max(expected, 1.0))
        reliability = (self.positive_outcomes + 1) / (self.positive_outcomes + self.negative_outcomes + 2)
        time_decay = 0.995 ** self.time_since_update(current_tick)
        return self.confidence * temporal_likelihood * reliability * time_decay

    def update_outcome(self, outcome: str, tick: int):
        self.tick_last_accessed = tick
        self.access_count += 1
        if outcome == "positive":
            self.positive_outcomes += 1
            self.confidence = min(1.0, self.confidence + 0.05)
        elif outcome == "negative":
            self.negative_outcomes += 1
            self.confidence *= 0.7
        if self.observed_duration is None:
            self.observed_duration = tick - self.tick_created
        else:
            self.observed_duration = 0.7 * self.observed_duration + 0.3 * (tick - self.tick_created)
        self.tick_last_updated = tick

    def merge(self, other: "MemoryItemV6", current_tick: int) -> "MemoryItemV6":
        w1 = self.confidence * self.access_count
        w2 = other.confidence * other.access_count
        total = w1 + w2 + 1e-6
        self.x = (self.x * w1 + other.x * w2) / total
        self.y = (self.y * w1 + other.y * w2) / total
        self.value = max(self.value, other.value) * 0.9 + min(self.value, other.value) * 0.1
        self.confidence = min(1.0, max(self.confidence, other.confidence) + 0.05)
        self.tick_last_updated = current_tick
        self.access_count += other.access_count
        self.positive_outcomes += other.positive_outcomes
        self.negative_outcomes += other.negative_outcomes
        if other.observed_duration is not None:
            if self.observed_duration is None:
                self.observed_duration = other.observed_duration
            else:
                self.observed_duration = (self.observed_duration + other.observed_duration) / 2
        return self

    def to_dict(self) -> dict:
        return {
            "concept": self.concept,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "value": round(self.value, 2),
            "confidence": round(self.confidence, 3),
            "tick_created": self.tick_created,
            "tick_last_updated": self.tick_last_updated,
            "access_count": self.access_count,
            "positive_outcomes": self.positive_outcomes,
            "negative_outcomes": self.negative_outcomes,
            "expected_duration": round(self.expected_duration, 1),
            "observed_duration": round(self.observed_duration, 1) if self.observed_duration else None,
            "landmark_id": self.landmark_id,
            "source": self.source,
        }


class TemporalMemory:
    def __init__(self, config: MemoryConfig):
        self.cfg = config
        self.memories: List[MemoryItemV6] = []
        self.episodes: deque = deque(maxlen=100)
        self.narrative: List[str] = []
        self.concept_durations: Dict[str, float] = dict(config.expected_resource_duration)

    def add_memory(self, concept: str, x: float, y: float, value: float, confidence: float, tick: int, landmark_id=None, source="sense") -> MemoryItemV6:
        for mem in self.memories:
            if mem.concept == concept:
                d = math.sqrt((mem.x - x) ** 2 + (mem.y - y) ** 2)
                if d <= self.cfg.memory_merge_dist:
                    mem.merge(MemoryItemV6(
                        concept=concept, x=x, y=y, value=value, confidence=confidence,
                        tick_created=tick, tick_last_updated=tick, tick_last_accessed=tick,
                        landmark_id=landmark_id, source=source,
                        expected_duration=self.concept_durations.get(concept, 100.0),
                    ), tick)
                    return mem
        mem = MemoryItemV6(
            concept=concept, x=x, y=y, value=value, confidence=confidence,
            tick_created=tick, tick_last_updated=tick, tick_last_accessed=tick,
            landmark_id=landmark_id, source=source,
            expected_duration=self.concept_durations.get(concept, 100.0),
        )
        self.memories.append(mem)
        self._prune_memories()
        return mem

    def add_episode(self, episode: EpisodicEvent):
        self.episodes.append(episode)
        narrative_entry = f"t{episode.tick}: {episode.event_type} {episode.concept} at ({episode.x:.0f},{episode.y:.0f}) -> {episode.outcome}"
        self.narrative.append(narrative_entry)
        if len(self.narrative) > 50:
            self.narrative.pop(0)

    def query(self, concept=None, current_tick=0, wanted_concepts=None, position=None, k=5):
        results = []
        for mem in self.memories:
            if concept and mem.concept != concept:
                continue
            relevance = mem.bayesian_relevance(current_tick, self.concept_durations)
            if wanted_concepts and mem.concept in wanted_concepts:
                priority = 1.5 if mem.concept in wanted_concepts[:3] else 1.2
                relevance *= priority
            if position:
                d = math.sqrt((mem.x - position[0]) ** 2 + (mem.y - position[1]) ** 2)
                relevance /= (1 + d * 0.05)
            if relevance > 0.05:
                results.append((mem, relevance))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:k]

    def update_concept_duration(self, concept: str, observed_duration: float):
        current = self.concept_durations.get(concept, 100.0)
        self.concept_durations[concept] = 0.8 * current + 0.2 * observed_duration

    def _prune_memories(self):
        if len(self.memories) <= self.cfg.memory_slots:
            return
        self.memories.sort(key=lambda m: m.confidence * m.value, reverse=True)
        self.memories = self.memories[:self.cfg.memory_slots]

    def decay(self, current_tick: int):
        for mem in self.memories:
            mem.confidence *= self.cfg.memory_forget
        self.memories = [m for m in self.memories if m.confidence > 0.03]

    def get_narrative(self, max_entries: int = 10) -> List[str]:
        return self.narrative[-max_entries:]

    def to_dict(self) -> dict:
        return {
            "memories": [m.to_dict() for m in self.memories],
            "episodes": [e.to_dict() for e in self.episodes],
            "narrative": self.narrative,
            "concept_durations": self.concept_durations,
        }
