"""
Enhanced speech system for TAIS Swarm V6.

Replaces V5.5's fixed grammar with:
- Grammar innovation (adopt successful patterns from others)
- Creole formation (merge grammars when populations meet)
- Communication channels: whisper, speak, shout, broadcast
- Volume-based cost and range
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum, auto

from ..engine.config import CommunicationConfig


@dataclass
class UtteranceV6:
    tokens: List[str]
    speaker_id: int
    target_id: Optional[int]
    intended_concept: str
    position: Tuple[float, float]
    channel: ChannelType
    fitness: float
    energy: float
    tick: int
    is_silence: bool = False
    is_query: bool = False
    is_teaching: bool = False
    confidence: float = 0.5
    role: str = "info"

    @property
    def is_directed(self) -> bool:
        return self.target_id is not None

    @property
    def text(self) -> str:
        return " ".join(self.tokens)

    def to_dict(self) -> dict:
        return {
            "tokens": self.tokens,
            "text": self.text,
            "speaker_id": self.speaker_id,
            "target_id": self.target_id,
            "intended_concept": self.intended_concept,
            "position": [round(p, 2) for p in self.position],
            "channel": self.channel.name,
            "fitness": round(self.fitness, 3),
            "energy": round(self.energy, 2),
            "tick": self.tick,
            "is_silence": self.is_silence,
            "is_query": self.is_query,
            "is_teaching": self.is_teaching,
            "confidence": round(self.confidence, 3),
            "role": self.role,
        }


class UtteranceV6Booklet:
    def __init__(self):
        self.utterances: List[UtteranceV6] = []

    def add(self, utt: UtteranceV6):
        self.utterances.append(utt)

    def for_mote(self, mote_id: int) -> List[UtteranceV6]:
        return [u for u in self.utterances if u.target_id is None or u.target_id == mote_id]

    def from_speaker(self, speaker_id: int) -> List[UtteranceV6]:
        return [u for u in self.utterances if u.speaker_id == speaker_id]

    def all_directed(self) -> List[UtteranceV6]:
        return [u for u in self.utterances if u.is_directed]

    def clear(self):
        self.utterances.clear()

    def __len__(self) -> int:
        return len(self.utterances)


class ChannelType(Enum):
    WHISPER = auto()
    SPEAK = auto()
    SHOUT = auto()
    ENCRYPTED = auto()


@dataclass
class GrammarRule:
    pattern: str
    usage_count: int = 0
    success_count: int = 0
    created_tick: int = 0

    @property
    def success_rate(self) -> float:
        return self.success_count / max(1, self.usage_count)

    def to_dict(self) -> dict:
        return {
            "pattern": self.pattern,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "success_rate": round(self.success_rate, 3),
        }


@dataclass
class SpeechGenomeV6:
    rules: List[GrammarRule] = field(default_factory=list)
    preferred_channel: ChannelType = ChannelType.SPEAK
    channel_switch_threshold: float = 0.3
    max_len: int = 3
    silence_bias: float = 0.5
    danger_silence: bool = True
    repeat_urgency: bool = False
    vocab_size: int = 12
    innovation_rate: float = 0.08
    last_innovation_tick: int = 0

    def __post_init__(self):
        if not self.rules:
            self.rules = [
                GrammarRule("concept-direction-distance"),
                GrammarRule("direction-concept-distance"),
                GrammarRule("risk-concept-direction"),
            ]

    def select_rule(self, urgency: float = 0.5) -> GrammarRule:
        scored = [(r, r.success_rate + random.uniform(0, 0.1)) for r in self.rules]
        scored.sort(key=lambda x: x[1], reverse=True)
        if urgency > 0.7 and random.random() < self.innovation_rate:
            if len(scored) > 1:
                return scored[min(1, len(scored) - 1)][0]
        return scored[0][0]

    def select_channel(self, energy: float, danger: bool = False, need_broadcast: bool = False) -> ChannelType:
        if danger and self.danger_silence:
            return ChannelType.WHISPER
        if need_broadcast and energy > 30:
            return ChannelType.SHOUT
        if energy < 15:
            return ChannelType.WHISPER
        return self.preferred_channel

    def mutate(self) -> "SpeechGenomeV6":
        child = SpeechGenomeV6(
            rules=[GrammarRule(r.pattern, r.usage_count, r.success_count, r.created_tick) for r in self.rules],
            preferred_channel=self.preferred_channel,
            max_len=max(1, min(5, self.max_len + random.choice([-1, 0, 0, 1]))),
            silence_bias=max(0.05, min(0.97, self.silence_bias + random.gauss(0, 0.04))),
            danger_silence=self.danger_silence if random.random() > 0.04 else not self.danger_silence,
            repeat_urgency=self.repeat_urgency if random.random() > 0.04 else not self.repeat_urgency,
            vocab_size=max(4, min(40, self.vocab_size + random.choice([-1, 0, 0, 1]))),
            innovation_rate=max(0.01, min(0.3, self.innovation_rate + random.gauss(0, 0.01))),
        )
        return child

    def to_dict(self) -> dict:
        return {
            "rules": [r.to_dict() for r in self.rules],
            "preferred_channel": self.preferred_channel.name,
            "max_len": self.max_len,
            "silence_bias": round(self.silence_bias, 2),
            "danger_silence": self.danger_silence,
            "repeat_urgency": self.repeat_urgency,
            "vocab_size": self.vocab_size,
            "innovation_rate": round(self.innovation_rate, 3),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SpeechGenomeV6":
        g = cls()
        g.rules = [GrammarRule(r["pattern"], r.get("usage_count", 0), r.get("success_count", 0)) for r in d.get("rules", [])]
        g.max_len = d.get("max_len", 3)
        g.silence_bias = d.get("silence_bias", 0.5)
        g.danger_silence = d.get("danger_silence", True)
        g.repeat_urgency = d.get("repeat_urgency", False)
        g.vocab_size = d.get("vocab_size", 12)
        g.innovation_rate = d.get("innovation_rate", 0.08)
        return g


class GrammarInnovator:
    def __init__(self, config: CommunicationConfig):
        self.cfg = config

    def invent_rule(self, genome: SpeechGenomeV6, tick: int) -> Optional[GrammarRule]:
        if random.random() > self.cfg.grammar_innovation_prob:
            return None
        elements = ["concept", "direction", "distance", "risk", "landmark", "urgency"]
        n_elements = random.randint(2, 4)
        pattern = "-".join(random.sample(elements, n_elements))
        rule = GrammarRule(pattern, created_tick=tick)
        genome.rules.append(rule)
        if len(genome.rules) > 6:
            genome.rules.sort(key=lambda r: r.success_rate)
            genome.rules = genome.rules[-6:]
        genome.last_innovation_tick = tick
        return rule

    def adopt_rule(self, genome: SpeechGenomeV6, successful_utterance: dict, tick: int) -> bool:
        inferred_pattern = self._infer_pattern(successful_utterance)
        if not inferred_pattern:
            return False
        for rule in genome.rules:
            if rule.pattern == inferred_pattern:
                rule.usage_count += 1
                rule.success_count += 1
                return False
        new_rule = GrammarRule(inferred_pattern, usage_count=1, success_count=1, created_tick=tick)
        genome.rules.append(new_rule)
        if len(genome.rules) > 6:
            genome.rules.sort(key=lambda r: r.success_rate)
            genome.rules = genome.rules[-6:]
        return True

    def merge_grammars(self, genome_a: SpeechGenomeV6, genome_b: SpeechGenomeV6, tick: int) -> SpeechGenomeV6:
        all_rules = list(genome_a.rules) + list(genome_b.rules)
        rule_scores: Dict[str, Tuple[GrammarRule, float]] = {}
        for rule in all_rules:
            if rule.pattern not in rule_scores or rule.success_rate > rule_scores[rule.pattern][1]:
                rule_scores[rule.pattern] = (rule, rule.success_rate)
        top_rules = sorted(rule_scores.values(), key=lambda x: x[1], reverse=True)
        selected = [r[0] for r in top_rules[:4]]
        if len(selected) >= 2 and random.random() < 0.2:
            parts_a = selected[0].pattern.split("-")
            parts_b = selected[1].pattern.split("-")
            hybrid = "-".join(random.sample(parts_a + parts_b, min(3, len(parts_a) + len(parts_b))))
            selected.append(GrammarRule(hybrid, created_tick=tick))
        creole = SpeechGenomeV6(
            rules=selected,
            preferred_channel=random.choice([genome_a.preferred_channel, genome_b.preferred_channel]),
            max_len=max(genome_a.max_len, genome_b.max_len),
            silence_bias=(genome_a.silence_bias + genome_b.silence_bias) / 2,
            vocab_size=max(genome_a.vocab_size, genome_b.vocab_size),
        )
        return creole

    def _infer_pattern(self, utterance: dict) -> Optional[str]:
        tokens = utterance.get("tokens", [])
        has_concept = utterance.get("intended_concept") is not None
        has_direction = any(t in ["NORTH", "SOUTH", "EAST", "WEST"] for t in tokens)
        has_distance = any(t in ["NEAR", "FAR"] for t in tokens)
        has_risk = utterance.get("nearest_predator_dist", 999) < 5.0
        parts = []
        if has_concept:
            parts.append("concept")
        if has_risk:
            parts.append("risk")
        if has_direction:
            parts.append("direction")
        if has_distance:
            parts.append("distance")
        return "-".join(parts) if parts else None
