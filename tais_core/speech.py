"""
tais_core.speech
================

Emergent speech system for universal motes.

No codebook. No LLM. No pretraining.

Meaning emerges from consequences, repair, teaching, and understanding audits.
"""

from __future__ import annotations

import random
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional

from .reality import Consequence


BASE_TOKENS = [
    "ka", "mi", "tor", "lum", "sha", "nek", "vo", "pra",
    "tel", "du", "ra", "si", "fel", "nox", "wen", "bru",
    "ya", "ko", "dex", "ith", "um", "zal", "pho", "rei",
]

UNIVERSAL_CONCEPTS = [
    "GOOD", "BAD", "DANGER", "SAFE", "RESOURCE", "VOID",
    "COME", "GO", "HERE", "THERE", "NORTH", "SOUTH", "EAST", "WEST",
    "STRONG", "WEAK", "TRUST", "DOUBT", "QUERY", "CONFIRM", "DENY", "UNKNOWN",
]
C_IDX = {c: i for i, c in enumerate(UNIVERSAL_CONCEPTS)}


class Lexicon:
    """Private token→concept weight table."""

    def __init__(self, vocab: Optional[List[str]] = None):
        self.vocab = list(vocab or BASE_TOKENS)
        self.table: Dict[str, Dict[str, float]] = {
            tok: {c: random.uniform(-0.02, 0.02) for c in UNIVERSAL_CONCEPTS}
            for tok in self.vocab
        }
        self.update_count = 0

    def ensure(self, token: str):
        if token not in self.table:
            self.table[token] = {c: 0.0 for c in UNIVERSAL_CONCEPTS}
            if token not in self.vocab:
                self.vocab.append(token)

    def weight(self, token: str, concept: str) -> float:
        return self.table.get(token, {}).get(concept, 0.0)

    def top_concept(self, token: str, threshold: float = 0.08) -> Optional[str]:
        if token not in self.table:
            return None
        best = max(self.table[token], key=self.table[token].get)
        return best if self.table[token][best] > threshold else None

    def top_token(self, concept: str, available: Optional[List[str]] = None, threshold: float = 0.08) -> Optional[str]:
        pool = available or self.vocab
        best_tok, best_w = None, threshold
        for tok in pool:
            w = self.weight(tok, concept)
            if w > best_w:
                best_tok, best_w = tok, w
        return best_tok

    def interpret(self, tokens: List[str]) -> Dict[str, float]:
        vec = {c: 0.0 for c in UNIVERSAL_CONCEPTS}
        for tok in tokens:
            if tok in self.table:
                for c, w in self.table[tok].items():
                    vec[c] += w
        total = max(1.0, sum(abs(v) for v in vec.values()))
        return {c: v / total for c, v in vec.items()}

    def dominant_concept(self, tokens: List[str], threshold: float = 0.10) -> Optional[str]:
        vec = self.interpret(tokens)
        best = max(vec, key=vec.get)
        return best if vec[best] > threshold else None

    def update(self, token: str, concept: str, delta: float, lr: float = 0.12):
        if concept not in C_IDX:
            return
        self.ensure(token)
        self.table[token][concept] = max(-1.0, min(1.0, self.table[token].get(concept, 0.0) + delta * lr))
        self.update_count += 1

    def update_from_consequence(self, tokens: List[str], consequence: Consequence, lr: float = 0.10):
        sign = 1.0 if consequence.net > 0 else -0.5
        for concept, signal in consequence.concept_signals.items():
            if concept not in C_IDX:
                continue
            for tok in tokens:
                self.update(tok, concept, signal * sign, lr)

    def apply_repair(self, tokens: List[str], intended_concept: str, lr: float = 0.15):
        if intended_concept not in C_IDX:
            return
        for tok in tokens:
            current = self.top_concept(tok)
            if current and current != intended_concept:
                self.update(tok, current, -1.0, lr * 0.5)
            self.update(tok, intended_concept, 1.0, lr)

    def teach(self, token: str, concept: str, strength: float = 0.4, corrective: bool = True):
        if concept not in C_IDX:
            return
        self.ensure(token)
        self.table[token][concept] = min(1.0, self.table[token].get(concept, 0.0) + strength)
        if corrective:
            for c in UNIVERSAL_CONCEPTS:
                if c != concept:
                    self.table[token][c] = max(-1.0, self.table[token][c] - strength * 0.25)
        self.update_count += 1

    def inherit_from(self, parent: "Lexicon", noise: float = 0.02):
        for tok in set(self.vocab) | set(parent.vocab):
            self.ensure(tok)
            if tok in parent.table:
                for concept in UNIVERSAL_CONCEPTS:
                    self.table[tok][concept] = max(-1.0, min(1.0, parent.table[tok].get(concept, 0.0) + random.gauss(0, noise)))

    def divergence(self, other: "Lexicon") -> float:
        toks = set(self.vocab) | set(other.vocab)
        total, count = 0.0, 0
        for tok in toks:
            for concept in UNIVERSAL_CONCEPTS:
                total += abs(self.weight(tok, concept) - other.weight(tok, concept))
                count += 1
        return total / max(1, count) / 2.0

    def snapshot(self, threshold: float = 0.10) -> Dict[str, Dict[str, Any]]:
        out = {}
        for tok, weights in self.table.items():
            best = max(weights, key=weights.get)
            if weights[best] > threshold:
                out[tok] = {"concept": best, "weight": round(weights[best], 3)}
        return out


class SpeechGenome:
    """Heritable grammar structure."""

    ORDERS = [
        "thing", "thing-direction", "direction-thing", "risk-thing",
        "thing-risk-direction", "thing-thing", "query-thing",
    ]

    def __init__(self):
        self.order = random.choice(self.ORDERS)
        self.max_length = random.randint(1, 3)
        self.repetition_urgency = random.random() < 0.25
        self.silence_bias = random.uniform(0.3, 0.85)
        self.danger_suppression = random.random() < 0.6
        self.vocab_size = random.randint(6, len(BASE_TOKENS))
        self.query_bias = random.uniform(0.0, 0.3)
        self.metaphor_bias = random.uniform(0.0, 0.15)

    def mutate(self, rate: float = 0.07) -> "SpeechGenome":
        child = SpeechGenome()
        child.order = self.order if random.random() > rate else random.choice(self.ORDERS)
        child.max_length = max(1, min(4, self.max_length + random.choice([-1, 0, 0, 1])))
        child.repetition_urgency = self.repetition_urgency if random.random() > rate else not self.repetition_urgency
        child.silence_bias = max(0.1, min(0.95, self.silence_bias + random.gauss(0, 0.04)))
        child.danger_suppression = self.danger_suppression if random.random() > rate else not self.danger_suppression
        child.vocab_size = max(4, min(len(BASE_TOKENS), self.vocab_size + random.choice([-1, 0, 0, 1])))
        child.query_bias = max(0.0, min(0.6, self.query_bias + random.gauss(0, 0.03)))
        child.metaphor_bias = max(0.0, min(0.4, self.metaphor_bias + random.gauss(0, 0.02)))
        return child

    def active_vocab(self) -> List[str]:
        return BASE_TOKENS[: self.vocab_size]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order": self.order,
            "max_length": self.max_length,
            "repetition_urgency": self.repetition_urgency,
            "silence_bias": round(self.silence_bias, 3),
            "danger_suppression": self.danger_suppression,
            "vocab_size": self.vocab_size,
            "query_bias": round(self.query_bias, 3),
            "metaphor_bias": round(self.metaphor_bias, 3),
        }


@dataclass
class Utterance:
    tokens: List[str]
    speaker_id: int
    target_id: Optional[int]
    intended_concept: str
    position: List[float]
    fitness: float
    energy: float
    domain: str = "unknown"
    tick: int = 0
    is_silence: bool = False
    is_query: bool = False
    is_repair: bool = False
    is_teaching: bool = False
    confidence: float = 0.5

    @property
    def text(self) -> str:
        return " ".join(self.tokens)

    @property
    def is_directed(self) -> bool:
        return self.target_id is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tokens": self.tokens,
            "text": self.text,
            "speaker": self.speaker_id,
            "target": self.target_id,
            "concept": self.intended_concept,
            "pos": [round(p, 2) for p in self.position],
            "fitness": round(self.fitness, 2),
            "energy": round(self.energy, 1),
            "domain": self.domain,
            "tick": self.tick,
            "silence": self.is_silence,
            "query": self.is_query,
            "repair": self.is_repair,
            "teaching": self.is_teaching,
            "conf": round(self.confidence, 2),
        }


@dataclass
class RepairSignal:
    original_utterance: Utterance
    speaker_id: int
    listener_id: int
    correct_concept: str
    tick: int

    def to_repair_utterance(self, genome: SpeechGenome, lexicon: Lexicon) -> Utterance:
        deny_tok = lexicon.top_token("DENY", genome.active_vocab()) or random.choice(genome.active_vocab())
        correct_tok = lexicon.top_token(self.correct_concept, genome.active_vocab()) or random.choice(genome.active_vocab())
        return Utterance(
            tokens=[deny_tok, correct_tok][:genome.max_length],
            speaker_id=self.speaker_id,
            target_id=self.listener_id,
            intended_concept="DENY",
            position=self.original_utterance.position,
            fitness=self.original_utterance.fitness,
            energy=0.0,
            domain=self.original_utterance.domain,
            tick=self.tick,
            is_repair=True,
            confidence=0.8,
        )


class UnderstandingAudit:
    def __init__(self, capacity: int = 100):
        self.events: Deque[Dict[str, Any]] = deque(maxlen=capacity)

    def record_sent(self, utterance: Utterance):
        self.events.append({
            "tick": utterance.tick,
            "speaker": utterance.speaker_id,
            "target": utterance.target_id,
            "tokens": list(utterance.tokens),
            "concept": utterance.intended_concept,
            "received": False,
            "acted_on": False,
            "aligned": False,
            "outcome": None,
        })

    def record_received(self, utterance: Utterance, listener_id: int):
        for ev in reversed(self.events):
            if ev["speaker"] == utterance.speaker_id and ev["tokens"] == utterance.tokens and not ev["received"]:
                ev["received"] = True
                ev["listener"] = listener_id
                break

    def record_acted_on(self, utterance_tokens: List[str], speaker_id: int, listener_id: int, listener_action: str, aligned: bool, outcome: str):
        for ev in reversed(self.events):
            if ev["speaker"] == speaker_id and ev["tokens"] == utterance_tokens and ev["received"]:
                ev["acted_on"] = True
                ev["listener"] = listener_id
                ev["listener_action"] = listener_action
                ev["aligned"] = aligned
                ev["outcome"] = outcome
                break

    def semantic_success_rate(self, last_n: int = 20) -> float:
        recent = [e for e in list(self.events)[-last_n:] if e["acted_on"]]
        if not recent:
            return 0.5
        return sum(1 for e in recent if e["aligned"]) / len(recent)

    def delivery_rate(self, last_n: int = 20) -> float:
        recent = list(self.events)[-last_n:]
        if not recent:
            return 0.0
        return sum(1 for e in recent if e["received"]) / len(recent)

    def summary(self) -> Dict[str, Any]:
        return {
            "total_sent": len(self.events),
            "semantic_success": round(self.semantic_success_rate(), 3),
            "delivery_rate": round(self.delivery_rate(), 3),
        }


class SpeechOrgan:
    """Unified speech interface: genome + lexicon + audit + repair."""

    def __init__(self, mote_id: int, genome: Optional[SpeechGenome] = None, lexicon: Optional[Lexicon] = None):
        self.mote_id = mote_id
        self.genome = genome or SpeechGenome()
        self.lexicon = lexicon or Lexicon(self.genome.active_vocab())
        self.audit = UnderstandingAudit()
        self.silence_reason: Optional[str] = None
        self._last_utterance: Optional[Utterance] = None
        self.times_spoke = 0
        self.times_silent_choice = 0
        self.times_silent_fear = 0
        self.times_directed = 0
        self.times_broadcast = 0
        self.times_repair = 0
        self.times_queried = 0
        self.times_taught = 0
        self._recent_utts: Deque[Utterance] = deque(maxlen=8)

    def compose(
        self,
        intent: str,
        neighbors: List[Any],
        mote_state: Dict[str, Any],
        domain: str,
        tick: int,
        info_delta: float = 0.0,
    ) -> Optional[Utterance]:
        self.silence_reason = None
        if self.genome.danger_suppression and mote_state.get("nearest_threat", 99) < 1.8:
            self.times_silent_fear += 1
            self.silence_reason = "fear"
            return None
        if mote_state.get("energy", 0) < 5.0:
            self.silence_reason = "energy"
            return None
        if not neighbors:
            self.silence_reason = "alone"
            return None
        if info_delta < self.genome.silence_bias * 1.8:
            self.times_silent_choice += 1
            self.silence_reason = "no_info"
            return None

        vocab = self.genome.active_vocab()
        tokens = self._compose_tokens(intent, mote_state, vocab)
        target_id = None
        neediest = mote_state.get("neediest_neighbor_id")
        if neediest is not None and random.random() > self.genome.silence_bias * 0.6:
            target_id = neediest
            self.times_directed += 1
        else:
            self.times_broadcast += 1
        is_query = random.random() < self.genome.query_bias
        if is_query:
            self.times_queried += 1
        confidence = max(0.1, min(1.0, info_delta / 5.0))
        utt = Utterance(
            tokens=tokens,
            speaker_id=self.mote_id,
            target_id=target_id,
            intended_concept=intent,
            position=mote_state.get("position", [0.0, 0.0]),
            fitness=mote_state.get("fitness", 0.0),
            energy=mote_state.get("energy", 0.0),
            domain=domain,
            tick=tick,
            is_query=is_query,
            confidence=confidence,
        )
        self.audit.record_sent(utt)
        self._last_utterance = utt
        self._recent_utts.append(utt)
        self.times_spoke += 1
        return utt

    def _compose_tokens(self, intent: str, mote_state: Dict[str, Any], vocab: List[str]) -> List[str]:
        slots = self.genome.order.split("-")
        slot_concepts = {
            "thing": intent,
            "direction": mote_state.get("gradient_concept", "EAST"),
            "risk": "DANGER" if mote_state.get("nearest_threat", 99) < 3.5 else None,
            "query": "QUERY" if self.genome.query_bias > 0.2 else None,
        }
        tokens: List[str] = []
        for slot in slots[:self.genome.max_length]:
            concept = slot_concepts.get(slot)
            if concept is None:
                continue
            tok = self.lexicon.top_token(concept, vocab) or random.choice(vocab)
            if not tokens or tokens[-1] != tok:
                tokens.append(tok)
        if self.genome.repetition_urgency and mote_state.get("energy", 100) < 30 and tokens:
            tokens = [tokens[0], tokens[0]]
        if self.genome.metaphor_bias > 0.1 and random.random() < self.genome.metaphor_bias and len(tokens) < self.genome.max_length:
            extra = self.lexicon.top_token(random.choice(UNIVERSAL_CONCEPTS), vocab)
            if extra and extra not in tokens:
                tokens.append(extra)
        return tokens or [random.choice(vocab)]

    def receive(self, utterance: Utterance) -> Dict[str, float]:
        self.audit.record_received(utterance, self.mote_id)
        return self.lexicon.interpret(utterance.tokens)

    def record_action_outcome(self, utterance: Utterance, action_taken: str, aligned: bool, outcome: str):
        self.audit.record_acted_on(utterance.tokens, utterance.speaker_id, self.mote_id, action_taken, aligned, outcome)

    def fire_repair(self, original: Utterance, listener_id: int, tick: int) -> Optional[Utterance]:
        self.times_repair += 1
        return RepairSignal(original, self.mote_id, listener_id, original.intended_concept, tick).to_repair_utterance(self.genome, self.lexicon)

    def receive_repair(self, repair_utt: Utterance):
        if repair_utt.is_repair and repair_utt.intended_concept in UNIVERSAL_CONCEPTS:
            self.lexicon.apply_repair(repair_utt.tokens, repair_utt.intended_concept)

    def teach(self, token: str, concept: str, strength: float = 0.4):
        self.lexicon.teach(token, concept, strength)
        self.times_taught += 1

    def update_from_consequence(self, consequence: Consequence, utterance_that_led_here: Optional[Utterance]):
        if utterance_that_led_here:
            self.lexicon.update_from_consequence(utterance_that_led_here.tokens, consequence)

    def spawn_child(self, child_id: int) -> "SpeechOrgan":
        child_genome = self.genome.mutate()
        child_lexicon = Lexicon(child_genome.active_vocab())
        child_lexicon.inherit_from(self.lexicon, noise=0.015)
        return SpeechOrgan(child_id, child_genome, child_lexicon)

    def recent_speech(self, n: int = 3) -> List[str]:
        return [u.text for u in list(self._recent_utts)[-n:]]

    def stats(self) -> Dict[str, Any]:
        total = self.times_spoke + self.times_silent_choice + self.times_silent_fear
        return {
            "id": self.mote_id,
            "spoke": self.times_spoke,
            "silent_choice": self.times_silent_choice,
            "silent_fear": self.times_silent_fear,
            "directed": self.times_directed,
            "broadcast": self.times_broadcast,
            "repairs_sent": self.times_repair,
            "queries": self.times_queried,
            "taught": self.times_taught,
            "speak_rate": round(self.times_spoke / max(1, total), 3),
            "direct_rate": round(self.times_directed / max(1, self.times_spoke), 3),
            "semantic_success": self.audit.semantic_success_rate(),
            "genome": self.genome.to_dict(),
            "lexicon": self.lexicon.snapshot(),
            "recent": self.recent_speech(),
        }
