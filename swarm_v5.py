"""
TAIS-LANG v5.5: Conversation · Query · Culture
=========================================

No LLM. No pretrained language model. No codebook sentence generation.

v5 expands the ecological speech world with a hard audit layer: speech is only
counted as communication when a listener interprets it, acts, and the outcome
is measured. The world still forces motes to talk about absent things:

  - Large structured world with food, water, shelter, poison, landmarks
  - Multi-need survival: energy, hydration, toxicity, predation
  - Mote place-memory: remembered resources/dangers away from current position
  - Referential utterances: concept + direction/near/far/landmark-ish tokens
  - Private lexicons inherited through reproduction and updated by outcomes
  - Human teaching: words are grounded into nearby motes' private lexicons
  - Headless evolution mode with save/load colonies

Core loop:
  world sensing → memory update → intent/reference selection → utterance/silence
  → listener interpretation/action → survival outcome → lexicon/trust update
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import threading
import time
from collections import Counter, deque
from dataclasses import asdict, dataclass
from typing import Deque, Dict, Iterable, List, Optional, Tuple

from flask import Flask, Response, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ─── VOCABULARY / CONCEPTS ───────────────────────────────────────────────────

TOKENS = [
    "ka", "mi", "tor", "lum", "sha", "nek", "vo", "pra", "tel", "du",
    "ra", "si", "fel", "nox", "wen", "bru", "ya", "ko", "dex", "ith",
    "zu", "mar", "ol", "tri", "ban", "esh", "ulo", "kir", "sam", "vai",
    "oro", "tin", "bez", "ari", "mun", "lef", "qor", "hal", "iva", "ruk",
]

CONCEPTS = [
    "FOOD", "WATER", "SHELTER", "POISON", "PREDATOR", "SAFE",
    "COME", "GO", "HELP", "TRUST",
    "NORTH", "SOUTH", "EAST", "WEST", "NEAR", "FAR", "HERE", "LANDMARK",
    "DYING", "STRONG", "UNKNOWN",
]
C_IDX = {c: i for i, c in enumerate(CONCEPTS)}
RESOURCE_CONCEPTS = {"FOOD", "WATER", "SHELTER", "POISON"}
DIRECTION_CONCEPTS = ["NORTH", "SOUTH", "EAST", "WEST"]

# Human teaching priors are not a language model. They are safety rails for the
# teacher UI so accidental bad grounding like `food → GO` can be warned/avoided.
HUMAN_WORD_PRIORS = {
    "food": "FOOD", "eat": "FOOD", "yum": "FOOD",
    "water": "WATER", "drink": "WATER", "wet": "WATER",
    "danger": "PREDATOR", "pred": "PREDATOR", "run": "PREDATOR",
    "home": "SHELTER", "nest": "SHELTER", "shelter": "SHELTER", "hide": "SHELTER", "cover": "SHELTER",
    "safe": "SAFE", "come": "COME", "go": "GO", "help": "HELP",
    "north": "NORTH", "south": "SOUTH", "east": "EAST", "west": "WEST",
}

# ─── CONFIG ──────────────────────────────────────────────────────────────────

CFG = {
    "world_size": 32.0,
    "population": 80,
    "max_population": 220,
    "predator_count": 6,
    "landmark_count": 28,
    "resource_count": 125,
    "ticks_per_sec": 4.0,
    "signal_range": 4.5,
    "player_range": 6.0,
    "memory_slots": 32,
    "initial_energy": 90.0,
    "initial_hydration": 90.0,
    "death_threshold": 0.0,
    "mitosis_thresh": 145.0,
    # Need dynamics
    "base_decay": 1.05,
    "hydration_decay": 0.78,
    "toxicity_decay": 0.94,
    "toxicity_energy_damage": 0.035,
    "dehydration_damage": 1.8,
    "food_gain": 5.8,
    "water_gain": 6.8,
    "shelter_decay_mult": 0.38,
    "poison_gain": 1.05,
    # Movement / predators
    "mote_step_min": 0.35,
    "mote_step_max": 1.0,
    "predator_speed": 0.72,
    "predator_contact": 0.88,
    "predator_damage": 16.0,
    "predator_broadcast_detect": 7.0,
    "predator_directed_detect": 2.4,
    "predator_wander": 1.25,
    # Speech economics
    "speak_cost": 3.7,
    "direct_cost": 1.8,
    "silence_bonus": 0.75,
    "min_speech_energy": 8.0,
    "lexicon_lr": 0.12,
    "self_ground_lr": 0.075,
    "teaching_boost": 0.55,
    "trust_decay": 0.96,
    "grammar_mutate": 0.055,
    "known_word_max": 10,
    # Learning/action
    "curiosity": 0.20,           # chance to test a high-value signal even if poorly understood
    "memory_merge_dist": 2.2,
    "memory_forget": 0.992,
}


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def dist(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def tokenise_text(text: str) -> List[str]:
    out: List[str] = []
    for raw in text.lower().replace(",", " ").replace(".", " ").replace("?", " ").split():
        tok = "".join(ch for ch in raw if ch.isalnum() or ch in "_-')")
        tok = tok.strip("'\"")[: CFG["known_word_max"]]
        if tok:
            out.append(tok)
    return out[:8]


def direction_from_to(x: float, y: float, tx: float, ty: float) -> str:
    dx, dy = tx - x, ty - y
    if abs(dx) >= abs(dy):
        return "EAST" if dx >= 0 else "WEST"
    return "NORTH" if dy >= 0 else "SOUTH"


def concept_for_resource(kind: str) -> str:
    return {"food": "FOOD", "water": "WATER", "shelter": "SHELTER", "poison": "POISON"}.get(kind, "UNKNOWN")


# ─── WORLD ───────────────────────────────────────────────────────────────────

@dataclass
class ResourceNode:
    id: int
    kind: str              # food | water | shelter | poison
    x: float
    y: float
    strength: float
    radius: float
    regen_phase: float = 0.0

    def value_at(self, x: float, y: float, tick: int = 0) -> float:
        d = math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)
        if d > self.radius * 3:
            return 0.0
        # Gentle dynamic world: resources breathe over time.
        breath = 0.86 + 0.14 * math.sin(0.015 * tick + self.regen_phase)
        return self.strength * breath * math.exp(-(d * d) / (2 * self.radius * self.radius))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "strength": round(self.strength, 2),
            "radius": round(self.radius, 2),
        }


@dataclass
class Landmark:
    id: int
    kind: str              # stone | cave | tree | tower | river | bone
    x: float
    y: float
    token: str

    def to_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind, "x": round(self.x, 2), "y": round(self.y, 2), "token": self.token}


class World:
    def __init__(self, size: float = CFG["world_size"], resource_count: int = CFG["resource_count"], landmark_count: int = CFG["landmark_count"]):
        self.size = float(size)
        self.resources: List[ResourceNode] = []
        self.landmarks: List[Landmark] = []
        self._build(resource_count, landmark_count)

    def _build(self, resource_count: int, landmark_count: int):
        # Landmarks first; they become reference anchors.
        landmark_kinds = ["stone", "cave", "tree", "tower", "river", "bone"]
        for i in range(landmark_count):
            kind = random.choice(landmark_kinds)
            self.landmarks.append(Landmark(
                id=i + 1,
                kind=kind,
                x=random.uniform(1.0, self.size - 1.0),
                y=random.uniform(1.0, self.size - 1.0),
                token=f"lm{i+1}",
            ))

        # Ecological clustering around landmarks + some scattered nodes.
        kinds = ["food", "water", "shelter", "poison"]
        weights = [0.37, 0.28, 0.20, 0.15]
        for i in range(resource_count):
            kind = random.choices(kinds, weights=weights)[0]
            if self.landmarks and random.random() < 0.70:
                lm = random.choice(self.landmarks)
                x = clamp(random.gauss(lm.x, self.size * 0.055), 0, self.size)
                y = clamp(random.gauss(lm.y, self.size * 0.055), 0, self.size)
            else:
                x = random.uniform(0, self.size)
                y = random.uniform(0, self.size)
            if kind == "food":
                strength, radius = random.uniform(5.5, 10.5), random.uniform(1.2, 2.8)
            elif kind == "water":
                strength, radius = random.uniform(6.5, 11.5), random.uniform(1.3, 3.2)
            elif kind == "shelter":
                strength, radius = random.uniform(4.5, 8.5), random.uniform(1.1, 2.5)
            else:
                strength, radius = random.uniform(5.0, 10.0), random.uniform(1.0, 2.7)
            self.resources.append(ResourceNode(i + 1, kind, x, y, strength, radius, random.random() * math.tau))

    def sense(self, x: float, y: float, tick: int) -> dict:
        vals = {"food": 0.0, "water": 0.0, "shelter": 0.0, "poison": 0.0}
        nearest_nodes: Dict[str, Optional[ResourceNode]] = {k: None for k in vals}
        best_node_val = {k: 0.0 for k in vals}
        for r in self.resources:
            v = r.value_at(x, y, tick)
            vals[r.kind] += v
            if v > best_node_val[r.kind]:
                best_node_val[r.kind] = v
                nearest_nodes[r.kind] = r

        nearest_landmark = None
        nearest_landmark_dist = 999.0
        for lm in self.landmarks:
            d = math.sqrt((x - lm.x) ** 2 + (y - lm.y) ** 2)
            if d < nearest_landmark_dist:
                nearest_landmark = lm
                nearest_landmark_dist = d

        return {
            **vals,
            "nearest_nodes": nearest_nodes,
            "nearest_landmark": nearest_landmark,
            "nearest_landmark_dist": nearest_landmark_dist,
        }

    def nearest_landmark_to(self, x: float, y: float) -> Tuple[Optional[Landmark], float]:
        best, best_d = None, 999.0
        for lm in self.landmarks:
            d = math.sqrt((x - lm.x) ** 2 + (y - lm.y) ** 2)
            if d < best_d:
                best, best_d = lm, d
        return best, best_d

    def to_dict(self) -> dict:
        return {
            "size": self.size,
            "resources": [r.to_dict() for r in self.resources],
            "landmarks": [lm.to_dict() for lm in self.landmarks],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "World":
        w = cls(size=data.get("size", CFG["world_size"]), resource_count=0, landmark_count=0)
        w.resources = [ResourceNode(**r) for r in data.get("resources", [])]
        w.landmarks = [Landmark(**lm) for lm in data.get("landmarks", [])]
        return w


# ─── SPEECH ──────────────────────────────────────────────────────────────────

class SpeechGenome:
    def __init__(self):
        self.order = random.choice([
            "concept-direction-distance",
            "direction-concept-distance",
            "risk-concept-direction",
            "landmark-concept-direction",
            "concept-landmark-distance",
        ])
        self.max_len = random.randint(1, 4)
        self.repeat_urgency = random.random() < 0.25
        self.silence_bias = random.uniform(0.25, 0.85)
        self.danger_silence = random.random() < 0.55
        self.direct_bias = random.uniform(0.35, 0.85)
        self.vocab_size = random.randint(8, len(TOKENS))

    def mutate(self) -> "SpeechGenome":
        g = SpeechGenome()
        if random.random() > CFG["grammar_mutate"]:
            g.order = self.order
        g.max_len = max(1, min(5, self.max_len + random.choice([-1, 0, 0, 1])))
        g.repeat_urgency = self.repeat_urgency if random.random() > CFG["grammar_mutate"] else not self.repeat_urgency
        g.silence_bias = clamp(self.silence_bias + random.gauss(0, 0.045), 0.05, 0.97)
        g.danger_silence = self.danger_silence if random.random() > CFG["grammar_mutate"] else not self.danger_silence
        g.direct_bias = clamp(self.direct_bias + random.gauss(0, 0.055), 0.0, 1.0)
        g.vocab_size = max(4, min(len(TOKENS), self.vocab_size + random.choice([-1, 0, 0, 1])))
        return g

    def to_dict(self) -> dict:
        return {
            "order": self.order,
            "max_len": self.max_len,
            "repeat_urgency": self.repeat_urgency,
            "silence_bias": round(self.silence_bias, 2),
            "danger_silence": self.danger_silence,
            "direct_bias": round(self.direct_bias, 2),
            "vocab_size": self.vocab_size,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SpeechGenome":
        g = cls()
        for k, v in d.items():
            setattr(g, k, v)
        return g


class Lexicon:
    def __init__(self):
        self.table: Dict[str, Dict[str, float]] = {
            tok: {c: random.uniform(-0.025, 0.025) for c in CONCEPTS} for tok in TOKENS
        }

    def ensure(self, tok: str):
        if tok not in self.table:
            self.table[tok] = {c: 0.0 for c in CONCEPTS}

    def update(self, tok: str, concept: str, amount: float):
        if concept not in C_IDX:
            return
        self.ensure(tok)
        self.table[tok][concept] = clamp(self.table[tok].get(concept, 0.0) + amount * CFG["lexicon_lr"], -1.0, 1.0)
        if amount > 0:
            for c in CONCEPTS:
                if c != concept:
                    self.table[tok][c] = clamp(self.table[tok][c] - amount * CFG["lexicon_lr"] * 0.01, -1.0, 1.0)

    def self_ground(self, tok: str, concept: str):
        if concept in C_IDX:
            self.ensure(tok)
            self.table[tok][concept] = clamp(self.table[tok][concept] + CFG["self_ground_lr"], -1.0, 1.0)

    def teach_ground(self, tok: str, concept: str, strength: float = 0.55, corrective: bool = True):
        """Ground a human-provided sound. Corrective teaching suppresses prior wrong meanings."""
        if concept not in C_IDX:
            return
        self.ensure(tok)
        self.table[tok][concept] = clamp(self.table[tok][concept] + strength, -1.0, 1.0)
        if corrective:
            for c in CONCEPTS:
                if c != concept:
                    self.table[tok][c] = clamp(self.table[tok][c] - strength * 0.35, -1.0, 1.0)

    def strongest_token_for(self, concept: str, vocab: Iterable[str], threshold: float = 0.055) -> Optional[str]:
        best_tok, best_w = None, threshold
        for tok in vocab:
            w = self.table.get(tok, {}).get(concept, 0.0)
            if w > best_w:
                best_tok, best_w = tok, w
        return best_tok

    def interpret(self, tokens: List[str]) -> Dict[str, float]:
        vec = {c: 0.0 for c in CONCEPTS}
        for tok in tokens:
            if tok in self.table:
                for c, w in self.table[tok].items():
                    vec[c] += w
        total = sum(abs(v) for v in vec.values()) or 1.0
        return {c: v / total for c, v in vec.items()}

    def to_dict(self, threshold: float = 0.16) -> dict:
        out = {}
        for tok, weights in sorted(self.table.items()):
            best = max(weights, key=weights.get)
            if weights[best] > threshold:
                out[tok] = {"concept": best, "weight": round(weights[best], 3)}
        return out

    def full_dict(self) -> dict:
        return self.table

    @classmethod
    def from_dict(cls, data: dict) -> "Lexicon":
        lx = cls()
        lx.table = {tok: {c: float(w) for c, w in weights.items()} for tok, weights in data.items()}
        for tok in TOKENS:
            lx.ensure(tok)
        return lx


@dataclass
class MemoryItem:
    concept: str
    x: float
    y: float
    value: float
    confidence: float
    tick: int
    landmark_id: Optional[int] = None
    source: str = "sense"  # sense | heard | player

    def to_dict(self) -> dict:
        return {
            "concept": self.concept,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "value": round(self.value, 2),
            "confidence": round(self.confidence, 2),
            "tick": self.tick,
            "landmark_id": self.landmark_id,
            "source": self.source,
        }


@dataclass
class Utterance:
    tokens: List[str]
    speaker_id: int
    target_id: Optional[int]
    intended_concept: str
    position: List[float]
    value: float
    energy: float
    hydration: float
    tick: int
    landmark_id: Optional[int] = None
    is_broadcast: bool = False
    is_player: bool = False
    is_teaching: bool = False

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
            "position": [round(self.position[0], 2), round(self.position[1], 2)],
            "value": round(self.value, 2),
            "energy": round(self.energy, 1),
            "hydration": round(self.hydration, 1),
            "tick": self.tick,
            "landmark_id": self.landmark_id,
            "is_broadcast": self.is_broadcast,
            "is_player": self.is_player,
            "is_teaching": self.is_teaching,
        }


@dataclass
class SilenceDecision:
    tick: int
    mote_id: int
    reason: str
    energy: float
    hydration: float
    toxicity: float
    predator_distance: float
    neighbor_count: int
    info_value: float

    def to_dict(self) -> dict:
        d = asdict(self)
        for k in ["energy", "hydration", "toxicity", "predator_distance", "info_value"]:
            d[k] = round(d[k], 2)
        return d


@dataclass
class ComprehensionEvent:
    """
    v5 audit record: did a listener actually understand/use an utterance?
    This is the difference between speech emission and communication.
    """
    utterance_tick: int
    outcome_tick: int
    speaker_id: int
    listener_id: int
    tokens: List[str]
    text: str
    speaker_intent: str
    listener_interpretation: str
    interpretation_confidence: float
    action: str
    energy_before: float
    energy_after: float
    hydration_before: float
    hydration_after: float
    trust_before: float
    trust_after: float
    outcome: str
    success: bool          # useful action: did acting help or avoid harm?
    semantic_match: bool   # stricter: did listener interpretation/outcome match speaker intent?

    def to_dict(self) -> dict:
        d = asdict(self)
        for k in ["interpretation_confidence", "energy_before", "energy_after", "hydration_before", "hydration_after", "trust_before", "trust_after"]:
            d[k] = round(d[k], 3)
        d["delta_energy"] = round(self.energy_after - self.energy_before, 3)
        d["delta_hydration"] = round(self.hydration_after - self.hydration_before, 3)
        return d


# ─── PREDATOR ────────────────────────────────────────────────────────────────

class Predator:
    _id = 0

    def __init__(self, world_size: float):
        Predator._id += 1
        self.id = Predator._id
        self.x = random.uniform(0, world_size)
        self.y = random.uniform(0, world_size)
        self.target_x = self.x
        self.target_y = self.y
        self.signals_followed = 0
        self.damage_dealt = 0.0
        self.kills = 0

    def update(self, utterances: List[Utterance], motes: List["Mote"], world_size: float, tick: int):
        best_u, best_score = None, 0.7
        for u in utterances:
            if u.is_player or u.tick < tick - 2:
                continue
            d = math.sqrt((self.x - u.position[0]) ** 2 + (self.y - u.position[1]) ** 2)
            detect = CFG["predator_broadcast_detect"] if u.is_broadcast else CFG["predator_directed_detect"]
            if d > detect:
                continue
            # Content following: high value food/water signals attract predators.
            attractive = u.value / (1.0 + d)
            if u.intended_concept in ["FOOD", "WATER", "SHELTER"]:
                attractive *= 1.25
            if attractive > best_score:
                best_score, best_u = attractive, u
        if best_u:
            self.target_x, self.target_y = best_u.position
            self.signals_followed += 1

        dx, dy = self.target_x - self.x, self.target_y - self.y
        d = math.sqrt(dx * dx + dy * dy)
        if d > 0.15:
            self.x += (dx / d) * CFG["predator_speed"]
            self.y += (dy / d) * CFG["predator_speed"]
        else:
            self.target_x = clamp(self.x + random.gauss(0, CFG["predator_wander"]), 0, world_size)
            self.target_y = clamp(self.y + random.gauss(0, CFG["predator_wander"]), 0, world_size)

        self.x = clamp(self.x, 0, world_size)
        self.y = clamp(self.y, 0, world_size)

        for m in motes:
            if not m.is_alive():
                continue
            if self.dist_to(m.x, m.y) <= CFG["predator_contact"]:
                m.energy -= CFG["predator_damage"]
                self.damage_dealt += CFG["predator_damage"]
                if m.energy <= CFG["death_threshold"]:
                    m.alive = False
                    self.kills += 1

    def dist_to(self, x: float, y: float) -> float:
        return math.sqrt((self.x - x) ** 2 + (self.y - y) ** 2)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "target_x": round(self.target_x, 2),
            "target_y": round(self.target_y, 2),
            "signals_followed": self.signals_followed,
            "kills": self.kills,
            "damage": round(self.damage_dealt, 1),
        }

    @classmethod
    def from_dict(cls, d: dict, world_size: float) -> "Predator":
        p = cls(world_size)
        p.id = d.get("id", p.id)
        p.x = d.get("x", p.x)
        p.y = d.get("y", p.y)
        p.target_x = d.get("target_x", p.x)
        p.target_y = d.get("target_y", p.y)
        p.signals_followed = d.get("signals_followed", 0)
        p.kills = d.get("kills", 0)
        p.damage_dealt = d.get("damage", 0.0)
        return p


# ─── MOTE ────────────────────────────────────────────────────────────────────

class Mote:
    _id = 0

    def __init__(self, x: float, y: float, energy: float, hydration: float, parent_id: int = -1):
        Mote._id += 1
        self.id = Mote._id
        self.parent_id = parent_id
        self.x = x
        self.y = y
        self.energy = energy
        self.hydration = hydration
        self.toxicity = 0.0
        self.age = 0
        self.alive = True

        self.sensed = {"food": 0.0, "water": 0.0, "shelter": 0.0, "poison": 0.0}
        self.nearest_predator_dist = 999.0
        self.nearest_landmark_id: Optional[int] = None
        self.nearest_landmark_dist = 999.0
        self.last_gradient: Optional[str] = None

        self.genome = SpeechGenome()
        self.lexicon = Lexicon()
        self.memories: List[MemoryItem] = []
        self.inbox: Deque[Utterance] = deque(maxlen=14)
        self.trust: Dict[int, float] = {}
        self.known_peer_state: Dict[int, Tuple[float, float]] = {}  # energy, hydration
        self.last_acted: Optional[Utterance] = None
        self.energy_before_acting = 0.0
        self.hydration_before_acting = 0.0
        self.last_listener_interpretation = "UNKNOWN"
        self.last_interpretation_confidence = 0.0
        self.last_action = "none"
        self.last_trust_before = 0.5

        self.silence_reason: Optional[str] = None
        self.times_spoke = 0
        self.times_directed = 0
        self.times_broadcast = 0
        self.times_silent_choice = 0
        self.times_silent_fear = 0
        self.times_silent_alone = 0
        self.lexicon_updates = 0
        self.memory_updates = 0
        self.comprehension_trials = 0
        self.comprehension_success = 0
        self.semantic_matches = 0
        self.utterances: Deque[Utterance] = deque(maxlen=10)
        self.silences: Deque[SilenceDecision] = deque(maxlen=10)

    def is_alive(self) -> bool:
        return self.alive and self.energy > CFG["death_threshold"] and self.hydration > -25

    def vitality(self) -> float:
        return min(self.energy, self.hydration) - self.toxicity * 2.0

    # ── Sensing/memory ───────────────────────────────────────────────────────
    def sense_world(self, world: World, predators: List[Predator], tick: int):
        s = world.sense(self.x, self.y, tick)
        self.sensed = {k: s[k] for k in ["food", "water", "shelter", "poison"]}
        lm = s["nearest_landmark"]
        self.nearest_landmark_id = lm.id if lm else None
        self.nearest_landmark_dist = s["nearest_landmark_dist"]
        self.nearest_predator_dist = min((p.dist_to(self.x, self.y) for p in predators), default=999.0)

        # Ground memories from direct sensing.
        for kind in ["food", "water", "shelter", "poison"]:
            val = self.sensed[kind]
            if val > (1.4 if kind != "poison" else 0.8):
                node = s["nearest_nodes"].get(kind)
                if node:
                    lm2, ld = world.nearest_landmark_to(node.x, node.y)
                    self.update_memory(concept_for_resource(kind), node.x, node.y, val, 0.75, tick, lm2.id if lm2 and ld < 5.0 else None, "sense")

        if self.nearest_predator_dist < 4.0:
            self.update_memory("PREDATOR", self.x, self.y, max(1.0, 5.0 - self.nearest_predator_dist), 0.65, tick, self.nearest_landmark_id, "sense")

        # Decay memory confidence.
        for mem in self.memories:
            mem.confidence *= CFG["memory_forget"]
        self.memories = [m for m in self.memories if m.confidence > 0.05]

    def update_memory(self, concept: str, x: float, y: float, value: float, confidence: float, tick: int, landmark_id: Optional[int], source: str):
        if concept not in C_IDX:
            return
        for mem in self.memories:
            if mem.concept == concept and math.sqrt((mem.x - x) ** 2 + (mem.y - y) ** 2) <= CFG["memory_merge_dist"]:
                w_old = mem.confidence
                w_new = confidence
                total = w_old + w_new + 1e-6
                mem.x = (mem.x * w_old + x * w_new) / total
                mem.y = (mem.y * w_old + y * w_new) / total
                mem.value = max(mem.value * 0.9, value)
                mem.confidence = clamp(max(mem.confidence, confidence) + 0.08, 0.0, 1.0)
                mem.tick = tick
                mem.landmark_id = landmark_id or mem.landmark_id
                mem.source = source
                self.memory_updates += 1
                return
        self.memories.append(MemoryItem(concept, x, y, value, confidence, tick, landmark_id, source))
        self.memories.sort(key=lambda m: (m.confidence * m.value), reverse=True)
        self.memories = self.memories[: CFG["memory_slots"]]
        self.memory_updates += 1

    # ── Intent/reference selection ───────────────────────────────────────────
    def derive_current_intent(self) -> str:
        if self.nearest_predator_dist < 3.0:
            return "PREDATOR"
        if self.toxicity > 35 or self.sensed["poison"] > 2.2:
            return "POISON"
        if self.hydration < 30:
            return "WATER"
        if self.energy < 32:
            return "FOOD"
        if self.sensed["food"] > 5.0:
            return "FOOD"
        if self.sensed["water"] > 5.0:
            return "WATER"
        if self.sensed["shelter"] > 4.0:
            return "SHELTER"
        if self.vitality() > 105:
            return "STRONG"
        return "SAFE"

    def best_memory_for_need(self) -> Optional[MemoryItem]:
        wanted: List[str] = []
        if self.nearest_predator_dist < 4.5:
            wanted.append("SHELTER")
            wanted.append("PREDATOR")
        if self.hydration < 65:
            wanted.append("WATER")
        if self.energy < 70:
            wanted.append("FOOD")
        wanted.extend(["FOOD", "WATER", "SHELTER", "POISON", "PREDATOR"])

        best, best_score = None, -999.0
        for mem in self.memories:
            d = math.sqrt((self.x - mem.x) ** 2 + (self.y - mem.y) ** 2)
            priority = 1.4 if mem.concept in wanted[:3] else 1.0
            if mem.concept in ["POISON", "PREDATOR"]:
                # Dangers are useful to announce even if not personally needed.
                priority *= 1.1
            score = mem.value * mem.confidence * priority / (1.0 + d * 0.08)
            if score > best_score:
                best, best_score = mem, score
        return best

    def select_target_neighbor(self, neighbors: List["Mote"], concept: str) -> Optional["Mote"]:
        if not neighbors:
            return None
        if concept == "FOOD":
            return min(neighbors, key=lambda n: n.energy)
        if concept == "WATER":
            return min(neighbors, key=lambda n: n.hydration)
        if concept in ["PREDATOR", "POISON", "SHELTER"]:
            return min(neighbors, key=lambda n: n.nearest_predator_dist if concept == "SHELTER" else n.vitality())
        return min(neighbors, key=lambda n: n.vitality())

    def make_silence(self, tick: int, reason: str, neighbors: List["Mote"], info_value: float) -> SilenceDecision:
        if reason == "predator":
            self.times_silent_fear += 1
        elif reason == "alone":
            self.times_silent_alone += 1
        else:
            self.times_silent_choice += 1
        self.silence_reason = reason
        if reason in ["no_info", "low_value"]:
            self.energy += CFG["silence_bonus"]
        sd = SilenceDecision(tick, self.id, reason, self.energy, self.hydration, self.toxicity, self.nearest_predator_dist, len(neighbors), info_value)
        self.silences.append(sd)
        return sd

    def generate_utterance(self, neighbors: List["Mote"], world: World, tick: int) -> Tuple[Optional[Utterance], Optional[SilenceDecision]]:
        self.silence_reason = None
        if self.genome.danger_silence and self.nearest_predator_dist < 1.7:
            return None, self.make_silence(tick, "predator", neighbors, 0.0)
        if self.energy < CFG["min_speech_energy"]:
            return None, self.make_silence(tick, "energy", neighbors, 0.0)
        if not neighbors:
            return None, self.make_silence(tick, "alone", neighbors, 0.0)

        mem = self.best_memory_for_need()
        current_intent = self.derive_current_intent()
        if mem and mem.confidence * mem.value > 1.25:
            concept = mem.concept
            ref_x, ref_y = mem.x, mem.y
            value = mem.value * mem.confidence
            landmark_id = mem.landmark_id
        else:
            concept = current_intent
            ref_x, ref_y = self.x, self.y
            value = max(self.sensed.get("food", 0), self.sensed.get("water", 0), self.sensed.get("shelter", 0), self.sensed.get("poison", 0), 1.0)
            landmark_id = self.nearest_landmark_id

        # Information value: worth telling if high value, danger, or neighbor need.
        neediest = self.select_target_neighbor(neighbors, concept)
        neighbor_need = 0.0
        if neediest:
            if concept == "FOOD":
                neighbor_need = max(0, 80 - neediest.energy) / 40
            elif concept == "WATER":
                neighbor_need = max(0, 80 - neediest.hydration) / 40
            elif concept in ["PREDATOR", "POISON"]:
                neighbor_need = 1.0
            elif concept == "SHELTER":
                neighbor_need = max(0, 5.0 - neediest.nearest_predator_dist) / 5.0
        info_value = value + neighbor_need * 2.0
        if info_value < self.genome.silence_bias * 2.4:
            return None, self.make_silence(tick, "low_value", neighbors, info_value)

        tokens = self.compose_tokens(concept, ref_x, ref_y, landmark_id, world)
        if not tokens:
            return None, self.make_silence(tick, "no_tokens", neighbors, info_value)

        for tok in tokens:
            # Ground each token in the primary concept and some structural concepts.
            self.lexicon.self_ground(tok, concept)
            self.lexicon_updates += 1

        directed = bool(neediest and (random.random() < self.genome.direct_bias or self.nearest_predator_dist < 4.0))
        target_id = neediest.id if directed and neediest else None
        if directed:
            self.energy -= CFG["direct_cost"]
            self.times_directed += 1
        else:
            self.energy -= CFG["speak_cost"]
            self.times_broadcast += 1
        self.times_spoke += 1

        utt = Utterance(tokens, self.id, target_id, concept, [ref_x, ref_y], value, self.energy, self.hydration, tick, landmark_id, is_broadcast=not directed)
        self.utterances.append(utt)
        return utt, None

    def answer_query(self, concept: str, world: World, tick: int) -> Tuple[Optional[Utterance], Optional[SilenceDecision]]:
        """Answer the player from memory. This is v5.5's conversation mode."""
        if concept not in C_IDX:
            concept = "UNKNOWN"
        if self.genome.danger_silence and self.nearest_predator_dist < 1.7:
            return None, self.make_silence(tick, "query_predator", [], 0.0)
        if self.energy < CFG["min_speech_energy"]:
            return None, self.make_silence(tick, "query_energy", [], 0.0)

        candidates = [m for m in self.memories if m.concept == concept]
        if not candidates and concept == "SAFE":
            candidates = [m for m in self.memories if m.concept in ["SHELTER", "PREDATOR", "POISON"]]
        if not candidates:
            return None, self.make_silence(tick, "query_no_memory", [], 0.0)

        mem = max(candidates, key=lambda m: m.value * m.confidence / (1.0 + 0.03 * math.sqrt((self.x-m.x)**2 + (self.y-m.y)**2)))
        answer_concept = mem.concept if concept != "SAFE" else ("SHELTER" if mem.concept == "SHELTER" else "SAFE")
        tokens = self.compose_tokens(answer_concept, mem.x, mem.y, mem.landmark_id, world)
        for tok in tokens:
            self.lexicon.self_ground(tok, answer_concept)
            self.lexicon_updates += 1
        self.energy -= CFG["direct_cost"]
        self.times_spoke += 1
        self.times_directed += 1
        utt = Utterance(tokens, self.id, -1, answer_concept, [mem.x, mem.y], mem.value * mem.confidence, self.energy, self.hydration, tick, mem.landmark_id, is_broadcast=False)
        self.utterances.append(utt)
        return utt, None

    def token_for(self, concept: str, vocab: List[str]) -> str:
        return self.lexicon.strongest_token_for(concept, vocab) or random.choice(vocab)

    def compose_tokens(self, concept: str, ref_x: float, ref_y: float, landmark_id: Optional[int], world: World) -> List[str]:
        vocab = TOKENS[: self.genome.vocab_size]
        concept_tok = self.token_for(concept, vocab)
        direction = direction_from_to(self.x, self.y, ref_x, ref_y)
        direction_tok = self.token_for(direction, vocab)
        distance = math.sqrt((self.x - ref_x) ** 2 + (self.y - ref_y) ** 2)
        dist_concept = "FAR" if distance > world.size * 0.18 else "NEAR"
        distance_tok = self.token_for(dist_concept, vocab)
        risk_tok = self.token_for("PREDATOR", vocab) if self.nearest_predator_dist < 5.0 or concept in ["PREDATOR", "POISON"] else None
        landmark_tok = None
        if landmark_id is not None and random.random() < 0.50:
            # Landmark token can enter as an acoustic proper-name. It can become grounded by use.
            landmark_tok = f"lm{landmark_id}"
            self.lexicon.ensure(landmark_tok)
            self.lexicon.self_ground(landmark_tok, "LANDMARK")

        order = self.genome.order
        if order == "concept-direction-distance":
            parts = [concept_tok, direction_tok, distance_tok]
        elif order == "direction-concept-distance":
            parts = [direction_tok, concept_tok, distance_tok]
        elif order == "risk-concept-direction":
            parts = ([risk_tok] if risk_tok else []) + [concept_tok, direction_tok]
        elif order == "landmark-concept-direction":
            parts = ([landmark_tok] if landmark_tok else []) + [concept_tok, direction_tok]
        elif order == "concept-landmark-distance":
            parts = [concept_tok] + ([landmark_tok] if landmark_tok else []) + [distance_tok]
        else:
            parts = [concept_tok]
        parts = [p for p in parts if p]
        deduped: List[str] = []
        for p in parts:
            if not deduped or deduped[-1] != p:
                deduped.append(p)
        parts = deduped[: self.genome.max_len]
        if self.genome.repeat_urgency and (self.energy < 30 or self.hydration < 30) and parts:
            parts = [parts[0]] + parts[: self.genome.max_len - 1]
        return parts

    # ── Listening/action/learning ────────────────────────────────────────────
    def receive(self, utt: Utterance):
        self.inbox.append(utt)
        self.trust.setdefault(utt.speaker_id, 0.5)

    def act_on_inbox(self, world: World, tick: int):
        for utt in reversed(self.inbox):
            if utt.target_id is not None and utt.target_id != self.id and not utt.is_player:
                continue
            trust = self.trust.get(utt.speaker_id, 0.5)
            concepts = self.lexicon.interpret(utt.tokens)
            # Curiosity lets meaning bootstrap: high-value content can be tested even before the token is understood.
            top_concept = max(concepts, key=concepts.get)
            top_score = concepts[top_concept]
            inferred = top_concept if top_score > 0.18 else "UNKNOWN"
            curious = random.random() < CFG["curiosity"] and utt.value > 2.0 and trust > 0.25

            move_toward = inferred in ["FOOD", "WATER", "SHELTER", "COME", "LANDMARK"] or (utt.is_player and curious)
            move_away = inferred in ["PREDATOR", "POISON", "GO"]
            if not (move_toward or move_away or curious):
                continue

            self.energy_before_acting = self.energy
            self.hydration_before_acting = self.hydration
            self.last_acted = utt
            self.last_listener_interpretation = inferred
            self.last_interpretation_confidence = float(top_score)
            self.last_trust_before = trust
            self.last_action = "away" if move_away else "toward"
            self.comprehension_trials += 1

            dx, dy = utt.position[0] - self.x, utt.position[1] - self.y
            d = math.sqrt(dx * dx + dy * dy) or 0.001
            step = CFG["mote_step_max"] * (0.55 + 0.45 * trust)
            if move_away:
                self.x = clamp(self.x - (dx / d) * step, 0, world.size)
                self.y = clamp(self.y - (dy / d) * step, 0, world.size)
            else:
                self.x = clamp(self.x + (dx / d) * step, 0, world.size)
                self.y = clamp(self.y + (dy / d) * step, 0, world.size)
                # Hearing creates a provisional map entry; outcome later strengthens/weakens token meaning.
                if utt.intended_concept in C_IDX:
                    self.update_memory(utt.intended_concept, utt.position[0], utt.position[1], utt.value, 0.35 * trust, tick, utt.landmark_id, "heard")
            break

    def update_lexicon_from_outcome(self, tick: int) -> Optional[ComprehensionEvent]:
        if self.last_acted is None:
            return None
        utt = self.last_acted
        delta_e = self.energy - self.energy_before_acting
        delta_h = self.hydration - self.hydration_before_acting
        outcome: Optional[str] = None
        if delta_e > 1.0 and self.sensed["food"] > 1.0:
            outcome = "FOOD"
        elif delta_h > 1.0 and self.sensed["water"] > 1.0:
            outcome = "WATER"
        elif self.sensed["shelter"] > 2.0 and self.nearest_predator_dist < 5.0:
            outcome = "SHELTER"
        elif self.sensed["poison"] > 1.2 or self.toxicity > 35 or self.nearest_predator_dist < 1.8 or delta_e < -8:
            outcome = "PREDATOR" if self.nearest_predator_dist < 1.8 else "POISON"

        if outcome:
            for tok in utt.tokens:
                self.lexicon.update(tok, outcome, 1.0)
                self.lexicon_updates += 1
            trust_delta = 0.08 if outcome in ["FOOD", "WATER", "SHELTER"] else -0.07
            self.trust[utt.speaker_id] = clamp(self.trust.get(utt.speaker_id, 0.5) + trust_delta, 0.0, 1.0)
        else:
            outcome = "NEUTRAL"

        trust_after = self.trust.get(utt.speaker_id, 0.5)
        success = (
            outcome == utt.intended_concept
            or (outcome in ["FOOD", "WATER", "SHELTER"] and self.last_action == "toward" and (delta_e > 0 or delta_h > 0))
            or (outcome in ["PREDATOR", "POISON"] and self.last_action == "away")
        )
        semantic_match = (self.last_listener_interpretation == utt.intended_concept and outcome == utt.intended_concept)
        if success:
            self.comprehension_success += 1
        if semantic_match:
            self.semantic_matches += 1

        ev = ComprehensionEvent(
            utterance_tick=utt.tick,
            outcome_tick=tick,
            speaker_id=utt.speaker_id,
            listener_id=self.id,
            tokens=list(utt.tokens),
            text=utt.text,
            speaker_intent=utt.intended_concept,
            listener_interpretation=self.last_listener_interpretation,
            interpretation_confidence=self.last_interpretation_confidence,
            action=self.last_action,
            energy_before=self.energy_before_acting,
            energy_after=self.energy,
            hydration_before=self.hydration_before_acting,
            hydration_after=self.hydration,
            trust_before=self.last_trust_before,
            trust_after=trust_after,
            outcome=outcome,
            success=bool(success),
            semantic_match=bool(semantic_match),
        )
        self.last_acted = None
        return ev

    def teach(self, word: str, concept: str, corrective: bool = True):
        tok = word.lower()[: CFG["known_word_max"]]
        if not tok or concept not in C_IDX:
            return
        self.lexicon.teach_ground(tok, concept, strength=CFG["teaching_boost"], corrective=corrective)
        self.lexicon_updates += 1

    # ── Movement/survival/reproduction ───────────────────────────────────────
    def explore(self, world: World, predators: List[Predator]):
        # Flee predator first.
        self.nearest_predator_dist = min((p.dist_to(self.x, self.y) for p in predators), default=999.0)
        if self.nearest_predator_dist < 1.8 and predators:
            p = min(predators, key=lambda pr: pr.dist_to(self.x, self.y))
            dx, dy = self.x - p.x, self.y - p.y
            d = math.sqrt(dx * dx + dy * dy) or 0.001
            self.x = clamp(self.x + (dx / d) * 1.15, 0, world.size)
            self.y = clamp(self.y + (dy / d) * 1.15, 0, world.size)
            return

        # If thirsty/hungry and memory exists, bias exploration toward that memory.
        wanted = "WATER" if self.hydration < 45 else "FOOD" if self.energy < 55 else None
        target = None
        if wanted:
            candidates = [m for m in self.memories if m.concept == wanted]
            if candidates:
                target = max(candidates, key=lambda m: m.value * m.confidence)
        if target and random.random() < 0.65:
            dx, dy = target.x - self.x, target.y - self.y
            d = math.sqrt(dx * dx + dy * dy) or 0.001
            step = random.uniform(CFG["mote_step_min"], CFG["mote_step_max"])
            self.x = clamp(self.x + (dx / d) * step, 0, world.size)
            self.y = clamp(self.y + (dy / d) * step, 0, world.size)
            return

        old_score = self.sensed["food"] + self.sensed["water"] + self.sensed["shelter"] - self.sensed["poison"] * 1.2
        step = random.uniform(CFG["mote_step_min"], CFG["mote_step_max"])
        dirs = [(step, 0, "EAST"), (-step, 0, "WEST"), (0, step, "NORTH"), (0, -step, "SOUTH")]
        random.shuffle(dirs)
        dx, dy, lab = dirs[0]
        nx, ny = clamp(self.x + dx, 0, world.size), clamp(self.y + dy, 0, world.size)
        s = world.sense(nx, ny, 0)
        new_score = s["food"] + s["water"] + s["shelter"] - s["poison"] * 1.2
        if new_score >= old_score * 0.65 or random.random() < 0.25:
            self.x, self.y = nx, ny
            if new_score > old_score:
                self.last_gradient = lab

    def metabolize(self, world: World, tick: int):
        s = world.sense(self.x, self.y, tick)
        food, water, shelter, poison = s["food"], s["water"], s["shelter"], s["poison"]
        shelter_mult = CFG["shelter_decay_mult"] if shelter > 2.0 else 1.0
        self.energy += min(food * CFG["food_gain"], 9.5) - CFG["base_decay"] * shelter_mult
        self.hydration += min(water * CFG["water_gain"], 10.0) - CFG["hydration_decay"]
        self.toxicity = self.toxicity * CFG["toxicity_decay"] + poison * CFG["poison_gain"]
        self.energy -= self.toxicity * CFG["toxicity_energy_damage"]
        if self.hydration < 0:
            self.energy += self.hydration * 0.18 - CFG["dehydration_damage"]
        self.energy = min(self.energy, 190.0)
        self.hydration = min(self.hydration, 150.0)
        self.age += 1
        for sid in list(self.trust):
            self.trust[sid] *= CFG["trust_decay"]
        if self.energy <= CFG["death_threshold"] or self.hydration <= -25:
            self.alive = False

    def reproduce(self, world: World) -> "Mote":
        self.energy /= 2
        self.hydration /= 2
        child = Mote(clamp(self.x + random.gauss(0, 0.7), 0, world.size), clamp(self.y + random.gauss(0, 0.7), 0, world.size), self.energy, self.hydration, self.id)
        child.toxicity = self.toxicity * 0.2
        child.genome = self.genome.mutate()
        child.lexicon = Lexicon.from_dict(self.lexicon.full_dict())
        # Noisy cultural inheritance.
        for tok in child.lexicon.table:
            for concept in CONCEPTS:
                child.lexicon.table[tok][concept] = clamp(child.lexicon.table[tok][concept] + random.gauss(0, 0.018), -1, 1)
        # Some memories pass to child.
        for mem in random.sample(self.memories, k=min(len(self.memories), CFG["memory_slots"] // 3)):
            child.memories.append(MemoryItem(mem.concept, mem.x + random.gauss(0, 0.25), mem.y + random.gauss(0, 0.25), mem.value, mem.confidence * 0.8, mem.tick, mem.landmark_id, "inherited"))
        return child

    # ── Serialization/UI ─────────────────────────────────────────────────────
    def to_save(self) -> dict:
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "x": self.x,
            "y": self.y,
            "energy": self.energy,
            "hydration": self.hydration,
            "toxicity": self.toxicity,
            "age": self.age,
            "genome": self.genome.to_dict(),
            "lexicon": self.lexicon.full_dict(),
            "memories": [asdict(m) for m in self.memories],
            "stats": {
                "spoke": self.times_spoke,
                "directed": self.times_directed,
                "broadcast": self.times_broadcast,
                "silent_choice": self.times_silent_choice,
                "silent_fear": self.times_silent_fear,
                "lexicon_updates": self.lexicon_updates,
                "memory_updates": self.memory_updates,
                "comprehension_trials": self.comprehension_trials,
                "comprehension_success": self.comprehension_success,
                "semantic_matches": self.semantic_matches,
            },
        }

    @classmethod
    def from_save(cls, d: dict) -> "Mote":
        m = cls(d["x"], d["y"], d.get("energy", 80), d.get("hydration", 80), d.get("parent_id", -1))
        m.id = d.get("id", m.id)
        m.toxicity = d.get("toxicity", 0.0)
        m.age = d.get("age", 0)
        m.genome = SpeechGenome.from_dict(d.get("genome", {}))
        m.lexicon = Lexicon.from_dict(d.get("lexicon", {}))
        m.memories = [MemoryItem(**mem) for mem in d.get("memories", [])]
        st = d.get("stats", {})
        m.times_spoke = st.get("spoke", 0)
        m.times_directed = st.get("directed", 0)
        m.times_broadcast = st.get("broadcast", 0)
        m.times_silent_choice = st.get("silent_choice", 0)
        m.times_silent_fear = st.get("silent_fear", 0)
        m.lexicon_updates = st.get("lexicon_updates", 0)
        m.memory_updates = st.get("memory_updates", 0)
        m.comprehension_trials = st.get("comprehension_trials", 0)
        m.comprehension_success = st.get("comprehension_success", 0)
        m.semantic_matches = st.get("semantic_matches", 0)
        return m

    def to_dict(self) -> dict:
        top = self.lexicon.to_dict(threshold=0.18)
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "energy": round(self.energy, 1),
            "hydration": round(self.hydration, 1),
            "toxicity": round(self.toxicity, 1),
            "vitality": round(self.vitality(), 1),
            "age": self.age,
            "sensed": {k: round(v, 2) for k, v in self.sensed.items()},
            "pred_dist": round(self.nearest_predator_dist, 2),
            "landmark_id": self.nearest_landmark_id,
            "spoke": self.times_spoke,
            "directed": self.times_directed,
            "broadcast": self.times_broadcast,
            "silent_choice": self.times_silent_choice,
            "silent_fear": self.times_silent_fear,
            "silent_alone": self.times_silent_alone,
            "lexicon_updates": self.lexicon_updates,
            "memory_updates": self.memory_updates,
            "comprehension_trials": self.comprehension_trials,
            "comprehension_success": self.comprehension_success,
            "semantic_matches": self.semantic_matches,
            "utility_rate": round(self.comprehension_success / max(1, self.comprehension_trials), 3),
            "semantic_rate": round(self.semantic_matches / max(1, self.comprehension_trials), 3),
            "genome": self.genome.to_dict(),
            "top_lexicon": top,
            "memories": [m.to_dict() for m in self.memories[:8]],
            "recent_utterances": [u.text for u in list(self.utterances)[-4:]],
            "intent": self.derive_current_intent(),
            "silence_reason": self.silence_reason,
        }


# ─── SWARM ───────────────────────────────────────────────────────────────────

class Swarm:
    def __init__(self, world_size: float = CFG["world_size"], population: int = CFG["population"]):
        self.world = World(size=world_size, resource_count=CFG["resource_count"], landmark_count=CFG["landmark_count"])
        self.motes: List[Mote] = []
        self.predators: List[Predator] = []
        self.tick = 0
        self.running = False
        self.lock = threading.RLock()
        self.pending_player_actions: List[dict] = []
        self.events: Deque[dict] = deque(maxlen=800)
        self.silence_log: Deque[dict] = deque(maxlen=800)
        self.audit_log: Deque[dict] = deque(maxlen=1200)
        self.recent_utterances: Deque[dict] = deque(maxlen=200)
        self.player = {"x": world_size / 2, "y": world_size / 2, "fitness": 0.0}
        self._bins: Dict[Tuple[int, int], List[Mote]] = {}
        self._bin_size = CFG["signal_range"]

        Mote._id = 0
        Predator._id = 0
        for _ in range(population):
            self.motes.append(Mote(random.uniform(0, world_size), random.uniform(0, world_size), CFG["initial_energy"], CFG["initial_hydration"]))
        for _ in range(CFG["predator_count"]):
            self.predators.append(Predator(world_size))

    def rebuild_bins(self):
        """Spatial hash for local communication queries."""
        self._bins = {}
        bs = self._bin_size
        for m in self.motes:
            if not m.is_alive():
                continue
            key = (int(m.x // bs), int(m.y // bs))
            self._bins.setdefault(key, []).append(m)

    def nearby_motes(self, x: float, y: float, radius: float, exclude_id: Optional[int] = None) -> List[Tuple[Mote, float]]:
        bs = self._bin_size
        if not self._bins:
            self.rebuild_bins()
        bx, by = int(x // bs), int(y // bs)
        reach = int(math.ceil(radius / bs)) + 1
        out: List[Tuple[Mote, float]] = []
        r2 = radius * radius
        for ix in range(bx - reach, bx + reach + 1):
            for iy in range(by - reach, by + reach + 1):
                for m in self._bins.get((ix, iy), []):
                    if exclude_id is not None and m.id == exclude_id:
                        continue
                    dx, dy = m.x - x, m.y - y
                    d2 = dx * dx + dy * dy
                    if d2 <= r2:
                        out.append((m, math.sqrt(d2)))
        return out

    def neighbors_of(self, mote: Mote) -> List[Mote]:
        return [m for m, _d in self.nearby_motes(mote.x, mote.y, CFG["signal_range"], exclude_id=mote.id)]

    def motes_near_player(self) -> List[Tuple[Mote, float]]:
        px, py = self.player["x"], self.player["y"]
        return sorted(self.nearby_motes(px, py, CFG["player_range"]), key=lambda x: x[1])

    def event_for_utt(self, utt: Utterance, typ: str = "utterance") -> dict:
        return {"type": typ, **utt.to_dict(), "mote_id": utt.speaker_id, "silence": False, "silence_reason": None}

    def tick_step(self) -> List[dict]:
        self.tick += 1
        tick_utts: List[Utterance] = []
        new_events: List[dict] = []

        with self.lock:
            actions = list(self.pending_player_actions)
            self.pending_player_actions = []

        self.player["fitness"] = self.player_fitness()

        # Sense.
        for m in self.motes:
            if m.is_alive():
                m.sense_world(self.world, self.predators, self.tick)
        self.rebuild_bins()

        # Player actions.
        for action in actions:
            if action.get("type") == "query":
                concept = action.get("concept") or "UNKNOWN"
                tokens = action.get("tokens", ["?"])[:8]
                new_events.append({
                    "type": "query",
                    "mote_id": None,
                    "speaker_id": -1,
                    "tokens": tokens,
                    "text": " ".join(tokens),
                    "intended_concept": concept,
                    "tick": self.tick,
                    "x": round(self.player["x"], 2),
                    "y": round(self.player["y"], 2),
                })
                answer_count = 0
                silence_count = 0
                for m, _d in self.motes_near_player()[:24]:
                    utt, sd = m.answer_query(concept, self.world, self.tick)
                    if sd:
                        silence_count += 1
                        self.silence_log.append(sd.to_dict())
                    if utt:
                        answer_count += 1
                        tick_utts.append(utt)
                        new_events.append(self.event_for_utt(utt, "answer"))
                new_events.append({"type": "query_summary", "text": f"answers={answer_count} silence={silence_count}", "tokens": [], "concept": concept, "tick": self.tick})
                continue
            if action.get("type") != "speak":
                continue
            pos = action.get("position", [self.player["x"], self.player["y"]])
            concept = action.get("concept") or "UNKNOWN"
            utt = Utterance(
                tokens=action.get("tokens", ["?"])[:8],
                speaker_id=-1,
                target_id=None,
                intended_concept=concept,
                position=[clamp(float(pos[0]), 0, self.world.size), clamp(float(pos[1]), 0, self.world.size)],
                value=float(action.get("value", action.get("fitness", self.player["fitness"]))),
                energy=999,
                hydration=999,
                tick=self.tick,
                landmark_id=action.get("landmark_id"),
                is_broadcast=True,
                is_player=True,
                is_teaching=bool(action.get("teaching", False)),
            )
            tick_utts.append(utt)
            new_events.append(self.event_for_utt(utt, "player"))
            for m, _d in self.motes_near_player():
                m.receive(utt)
                if utt.is_teaching and concept in C_IDX:
                    for tok in utt.tokens:
                        m.teach(tok, concept)
                    m.update_memory(concept, utt.position[0], utt.position[1], utt.value, 0.55, self.tick, utt.landmark_id, "player")
                    new_events.append({
                        "type": "teaching",
                        "mote_id": m.id,
                        "tokens": utt.tokens,
                        "text": utt.text,
                        "concept": concept,
                        "x": round(m.x, 2),
                        "y": round(m.y, 2),
                        "tick": self.tick,
                    })

        # Mote utterances.
        for m in list(self.motes):
            if not m.is_alive():
                continue
            neighbors = self.neighbors_of(m)
            utt, sd = m.generate_utterance(neighbors, self.world, self.tick)
            if sd:
                self.silence_log.append(sd.to_dict())
            if utt:
                tick_utts.append(utt)
                for n in neighbors:
                    if utt.target_id is None or utt.target_id == n.id:
                        n.receive(utt)
                if self.near_player(utt.position[0], utt.position[1], CFG["player_range"] * 1.25) or self.near_player(m.x, m.y, CFG["player_range"] * 1.1):
                    new_events.append(self.event_for_utt(utt, "utterance"))
            elif m.silence_reason and self.near_player(m.x, m.y, CFG["player_range"]) and random.random() < 0.35:
                new_events.append({
                    "type": "silence",
                    "mote_id": m.id,
                    "tokens": [],
                    "text": "",
                    "intent": m.derive_current_intent(),
                    "x": round(m.x, 2),
                    "y": round(m.y, 2),
                    "energy": round(m.energy, 1),
                    "hydration": round(m.hydration, 1),
                    "tick": self.tick,
                    "silence": True,
                    "silence_reason": m.silence_reason,
                })

        # Predators follow signal content.
        for p in self.predators:
            p.update(tick_utts, self.motes, self.world.size, self.tick)

        # Motes act on speech, move, survive, learn.
        for m in self.motes:
            if m.is_alive():
                m.act_on_inbox(self.world, self.tick)
        for m in self.motes:
            if m.is_alive():
                m.explore(self.world, self.predators)
        for m in self.motes:
            if m.is_alive():
                m.sense_world(self.world, self.predators, self.tick)
                m.metabolize(self.world, self.tick)
                audit = m.update_lexicon_from_outcome(self.tick)
                if audit:
                    ad = audit.to_dict()
                    self.audit_log.append(ad)
                    # Surface the important understanding events near the player.
                    if audit.success or self.near_player(m.x, m.y, CFG["player_range"]) or random.random() < 0.08:
                        new_events.append({"type": "understanding", **ad})

        # Birth/death.
        next_motes: List[Mote] = []
        births_near_player = 0
        birth_samples: List[str] = []
        for m in self.motes:
            if not m.is_alive():
                if self.near_player(m.x, m.y, CFG["player_range"] * 1.2):
                    new_events.append({"type": "death", "mote_id": m.id, "text": "", "tokens": [], "x": round(m.x, 2), "y": round(m.y, 2), "tick": self.tick})
                continue
            if m.energy >= CFG["mitosis_thresh"] and m.hydration > 45 and len(next_motes) < CFG["max_population"]:
                child = m.reproduce(self.world)
                next_motes.append(child)
                if self.near_player(child.x, child.y, CFG["player_range"] * 1.2):
                    births_near_player += 1
                    if len(birth_samples) < 5:
                        birth_samples.append(random.choice(TOKENS[:5]))
                    # Only show rare individual births; otherwise summarize to avoid chat spam.
                    if random.random() < 0.025:
                        new_events.append({"type": "birth", "mote_id": child.id, "text": birth_samples[-1], "tokens": [birth_samples[-1]], "x": round(child.x, 2), "y": round(child.y, 2), "energy": round(child.energy, 1), "tick": self.tick})
            next_motes.append(m)
        if births_near_player:
            new_events.append({"type": "birth_summary", "mote_id": None, "text": f"{births_near_player} births nearby", "tokens": birth_samples, "count": births_near_player, "tick": self.tick})
        self.motes = next_motes[: CFG["max_population"]]

        with self.lock:
            self.recent_utterances.extend([u.to_dict() for u in tick_utts])
            self.events.extend(new_events)
        return new_events

    def near_player(self, x: float, y: float, radius: float) -> bool:
        return math.sqrt((x - self.player["x"]) ** 2 + (y - self.player["y"]) ** 2) <= radius

    def player_fitness(self) -> float:
        s = self.world.sense(self.player["x"], self.player["y"], self.tick)
        # generalized local richness score
        return round(s["food"] + s["water"] + s["shelter"] - s["poison"] * 1.2, 2)

    def add_player_speech(self, tokens: List[str], concept: Optional[str], value: float, x: float, y: float, teaching: bool = False):
        lm, ld = self.world.nearest_landmark_to(x, y)
        with self.lock:
            self.pending_player_actions.append({
                "type": "speak",
                "tokens": tokens,
                "concept": concept,
                "value": value,
                "position": [x, y],
                "teaching": teaching,
                "landmark_id": lm.id if lm and ld < 5.0 else None,
            })

    def add_player_query(self, tokens: List[str], concept: str):
        with self.lock:
            self.pending_player_actions.append({"type": "query", "tokens": tokens, "concept": concept})

    def stats(self) -> dict:
        alive = [m for m in self.motes if m.is_alive()]
        spoke = sum(m.times_spoke for m in alive)
        directed = sum(m.times_directed for m in alive)
        broadcast = sum(m.times_broadcast for m in alive)
        sil_choice = sum(m.times_silent_choice for m in alive)
        sil_fear = sum(m.times_silent_fear for m in alive)
        lex = sum(m.lexicon_updates for m in alive)
        mem = sum(m.memory_updates for m in alive)
        comp_trials = sum(m.comprehension_trials for m in alive)
        comp_success = sum(m.comprehension_success for m in alive)
        semantic_matches = sum(m.semantic_matches for m in alive)
        avg_energy = sum(m.energy for m in alive) / max(1, len(alive))
        avg_hyd = sum(m.hydration for m in alive) / max(1, len(alive))
        avg_tox = sum(m.toxicity for m in alive) / max(1, len(alive))
        common = Counter()
        for m in alive:
            for tok, obj in m.lexicon.to_dict(threshold=0.22).items():
                common[(tok, obj["concept"])] += 1
        return {
            "population": len(alive),
            "spoke": spoke,
            "directed": directed,
            "broadcast": broadcast,
            "directed_ratio": round(directed / max(1, spoke), 3),
            "choice_silence": sil_choice,
            "fear_silence": sil_fear,
            "lexicon_updates": lex,
            "memory_updates": mem,
            "comprehension_trials": comp_trials,
            "comprehension_success": comp_success,
            "semantic_matches": semantic_matches,
            "utility_rate": round(comp_success / max(1, comp_trials), 3),
            "semantic_rate": round(semantic_matches / max(1, comp_trials), 3),
            "avg_energy": round(avg_energy, 1),
            "avg_hydration": round(avg_hyd, 1),
            "avg_toxicity": round(avg_tox, 1),
            "predator_follows": sum(p.signals_followed for p in self.predators),
            "predator_kills": sum(p.kills for p in self.predators),
            "common_tokens": [{"token": k[0], "concept": k[1], "count": v} for k, v in common.most_common(16)],
        }

    def snapshot(self) -> dict:
        with self.lock:
            events = list(self.events)[-120:]
            recent = list(self.recent_utterances)[-120:]
            silence = list(self.silence_log)[-120:]
            audits = list(self.audit_log)[-120:]
        return {
            "version": "v5.5",
            "tick": self.tick,
            "world": self.world.to_dict(),
            "population": len([m for m in self.motes if m.is_alive()]),
            "motes": [m.to_dict() for m in self.motes if m.is_alive()],
            "predators": [p.to_dict() for p in self.predators],
            "player": dict(self.player),
            "events": events,
            "recent_utterances": recent,
            "silence": silence,
            "audits": audits,
            "tokens": TOKENS,
            "concepts": CONCEPTS,
            "stats": self.stats(),
        }

    def save(self, path: str):
        data = {
            "version": "v5.5",
            "tick": self.tick,
            "cfg": CFG,
            "world": self.world.to_dict(),
            "motes": [m.to_save() for m in self.motes if m.is_alive()],
            "predators": [p.to_dict() for p in self.predators],
            "player": self.player,
        }
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> "Swarm":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        world = World.from_dict(data["world"])
        sw = cls(world_size=world.size, population=0)
        sw.world = world
        sw.tick = data.get("tick", 0)
        sw.player = data.get("player", {"x": world.size / 2, "y": world.size / 2, "fitness": 0})
        sw.motes = [Mote.from_save(m) for m in data.get("motes", [])]
        Mote._id = max([m.id for m in sw.motes], default=0)
        sw.predators = [Predator.from_dict(p, world.size) for p in data.get("predators", [])]
        Predator._id = max([p.id for p in sw.predators], default=0)
        return sw


# ─── GLOBAL SERVER STATE ─────────────────────────────────────────────────────

swarm: Swarm = Swarm()
swarm_thread: Optional[threading.Thread] = None


def run_loop():
    swarm.running = True
    while swarm.running:
        try:
            swarm.tick_step()
        except Exception as exc:
            print(f"[swarm-v4 error] {exc}")
        time.sleep(1.0 / CFG["ticks_per_sec"])


def start_thread():
    global swarm_thread
    swarm_thread = threading.Thread(target=run_loop, daemon=True)
    swarm_thread.start()


# ─── FLASK ROUTES ────────────────────────────────────────────────────────────

@app.route("/stream")
def stream():
    def gen():
        last = -1
        while True:
            if swarm.tick != last:
                last = swarm.tick
                yield f"data: {json.dumps(swarm.snapshot())}\n\n"
            time.sleep(0.08)
    return Response(gen(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/state")
def state():
    return jsonify(swarm.snapshot())


@app.route("/health")
def health():
    return jsonify({"ok": True, "version": "v5.5", "tick": swarm.tick, "population": len([m for m in swarm.motes if m.is_alive()])})


@app.route("/concepts")
def concepts():
    return jsonify({"concepts": CONCEPTS, "tokens": TOKENS})


@app.route("/audit")
def audit():
    return jsonify({"audits": list(swarm.audit_log)[-300:], "stats": swarm.stats()})


@app.route("/player/move", methods=["POST"])
def player_move():
    d = request.json or {}
    with swarm.lock:
        swarm.player["x"] = clamp(float(d.get("x", swarm.player["x"])), 0, swarm.world.size)
        swarm.player["y"] = clamp(float(d.get("y", swarm.player["y"])), 0, swarm.world.size)
        swarm.player["fitness"] = swarm.player_fitness()
        p = dict(swarm.player)
    return jsonify({"ok": True, "player": p})


@app.route("/player/speak", methods=["POST"])
def player_speak():
    d = request.json or {}
    raw = d.get("text", "")
    tokens = tokenise_text(raw) if raw else [str(t).lower()[: CFG["known_word_max"]] for t in d.get("tokens", ["?"]) if str(t)]
    if not tokens:
        tokens = ["?"]
    with swarm.lock:
        x = clamp(float(d.get("x", swarm.player["x"])), 0, swarm.world.size)
        y = clamp(float(d.get("y", swarm.player["y"])), 0, swarm.world.size)
        value = float(d.get("value", d.get("fitness", swarm.player["fitness"])))
    concept = d.get("concept")
    teaching = bool(d.get("teaching", False))
    swarm.add_player_speech(tokens, concept, value, x, y, teaching)
    return jsonify({"ok": True, "tokens": tokens, "concept": concept, "teaching": teaching, "x": x, "y": y, "value": value})


@app.route("/player/teach", methods=["POST"])
def player_teach():
    d = request.json or {}
    word = (d.get("word") or d.get("text") or "").strip()
    concept = d.get("concept", "FOOD")
    if concept not in C_IDX:
        return jsonify({"error": "unknown concept", "valid": CONCEPTS}), 400
    tokens = tokenise_text(word)
    if not tokens:
        return jsonify({"error": "missing word"}), 400
    warnings = []
    for tok in tokens:
        prior = HUMAN_WORD_PRIORS.get(tok)
        if prior and prior != concept:
            warnings.append(f"'{tok}' is usually grounded as {prior}, not {concept}")
    with swarm.lock:
        x = clamp(float(d.get("x", swarm.player["x"])), 0, swarm.world.size)
        y = clamp(float(d.get("y", swarm.player["y"])), 0, swarm.world.size)
        value = float(d.get("value", swarm.player["fitness"]))
    swarm.add_player_speech(tokens, concept, value, x, y, teaching=True)
    return jsonify({"ok": True, "tokens": tokens, "concept": concept, "warnings": warnings})


@app.route("/player/query", methods=["POST"])
def player_query():
    d = request.json or {}
    concept = d.get("concept")
    text = d.get("text", "")
    tokens = tokenise_text(text) if text else []
    if not concept and tokens:
        concept = HUMAN_WORD_PRIORS.get(tokens[0], "UNKNOWN")
    concept = concept or "UNKNOWN"
    if concept not in C_IDX:
        return jsonify({"error": "unknown concept", "valid": CONCEPTS}), 400
    if not tokens:
        tokens = [concept.lower()]
    swarm.add_player_query(tokens, concept)
    return jsonify({"ok": True, "tokens": tokens, "concept": concept})


@app.route("/mote/<int:mote_id>/lexicon")
def mote_lexicon(mote_id: int):
    for m in swarm.motes:
        if m.id == mote_id and m.is_alive():
            return jsonify({
                "id": m.id,
                "lexicon": m.lexicon.to_dict(threshold=0.08),
                "genome": m.genome.to_dict(),
                "memories": [mem.to_dict() for mem in m.memories],
                "utterances": [u.to_dict() for u in m.utterances],
                "trust": {str(k): round(v, 2) for k, v in m.trust.items()},
            })
    return jsonify({"error": "not found"}), 404


@app.route("/save", methods=["POST"])
def save_route():
    d = request.json or {}
    path = d.get("path", f"colonies/v4_tick_{swarm.tick}.json")
    swarm.save(path)
    return jsonify({"ok": True, "path": path})


@app.route("/reset", methods=["POST"])
def reset_route():
    global swarm
    old = swarm
    old.running = False
    time.sleep(0.15)
    d = request.json or {}
    world_size = float(d.get("world_size", CFG["world_size"]))
    pop = int(d.get("population", CFG["population"]))
    swarm = Swarm(world_size=world_size, population=pop)
    start_thread()
    return jsonify({"ok": True, "version": "v5.5"})


# ─── CLI ─────────────────────────────────────────────────────────────────────

def run_headless(args: argparse.Namespace):
    global swarm
    if args.load:
        swarm = Swarm.load(args.load)
    else:
        swarm = Swarm(world_size=args.world, population=args.population)
    t0 = time.time()
    for i in range(1, args.ticks + 1):
        swarm.tick_step()
        if args.report and (i % args.report == 0 or i == 1):
            s = swarm.stats()
            print(
                f"tick={swarm.tick:>7} pop={s['population']:>4} "
                f"E={s['avg_energy']:>5.1f} H={s['avg_hydration']:>5.1f} Tox={s['avg_toxicity']:>4.1f} "
                f"spk={s['spoke']:>6} dir={s['directed_ratio']:.2f} "
                f"sem={s.get('semantic_rate',0):.2f} util={s.get('utility_rate',0):.2f} "
                f"sil={s['choice_silence']:>6}/{s['fear_silence']:<5} lex={s['lexicon_updates']:>7} mem={s['memory_updates']:>7}"
            )
        if not swarm.motes:
            print(f"EXTINCTION at tick {swarm.tick}")
            break
    dt = time.time() - t0
    print(f"done: {swarm.tick} ticks in {dt:.2f}s ({args.ticks / max(dt, 1e-6):.1f} ticks/s)")
    if args.save:
        swarm.save(args.save)
        print(f"saved → {args.save}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="TAIS-LANG v5.5 Conversation · Query · Culture")
    p.add_argument("--headless", action="store_true", help="run training without Flask server")
    p.add_argument("--ticks", type=int, default=10000, help="headless training ticks")
    p.add_argument("--world", type=float, default=CFG["world_size"], help="world size")
    p.add_argument("--population", type=int, default=CFG["population"], help="initial population")
    p.add_argument("--save", type=str, default=None, help="save colony JSON")
    p.add_argument("--load", type=str, default=None, help="load colony JSON")
    p.add_argument("--report", type=int, default=1000, help="headless report interval")
    p.add_argument("--port", type=int, default=5123, help="server port")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.headless:
        run_headless(args)
    else:
        if args.load:
            swarm = Swarm.load(args.load)
            print(f"Loaded colony {args.load} at tick {swarm.tick}")
        else:
            swarm = Swarm(world_size=args.world, population=args.population)
        start_thread()
        print("TAIS-LANG v5.5: Conversation · Query · Culture")
        print(f"http://localhost:{args.port}")
        print(f"World: {swarm.world.size}x{swarm.world.size} | Pop: {len(swarm.motes)} | Predators: {len(swarm.predators)}")
        print("Endpoints: /stream /state /player/speak /player/teach /mote/<id>/lexicon /save /reset")
        app.run(host="0.0.0.0", port=args.port, debug=False, threaded=True)
