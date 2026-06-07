"""
TAIS-LANG v3: Living Speech
============================

No codebook. No LLM. No pretraining.

Architecture:
  Mote State → Intent → Concept Vector → Token Generator → Utterance
  → Listener Parses → Action → Survival → Lexicon Update

Each mote owns its speech:
  - SpeechGenome: how it forms utterances (inherited, mutable)
  - Lexicon: private token→concept weights learned from consequences
  - IntentSystem: maps internal state to what it wants to express

Meaning emerges when tokens consistently precede survival or death.
Grammar emerges when word-order styles that aid survival outreproduce others.
Human words enter only by grounded teaching: player says a word near a concept/event.
"""

from __future__ import annotations

import json
import math
import random
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from typing import Deque, Dict, List, Optional, Tuple

from flask import Flask, Response, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ─── UNIVERSAL PHONETIC SEED VOCABULARY ──────────────────────────────────────
# Motes start with these sounds but do not know what they mean.
TOKENS = [
    "ka", "mi", "tor", "lum", "sha", "nek", "vo", "pra", "tel", "du",
    "ra", "si", "fel", "nox", "wen", "bru", "ya", "ko", "dex", "ith",
]

# ─── INTERNAL CONCEPT SPACE ──────────────────────────────────────────────────
# Motes reason in concepts and speak in tokens. Token↔concept mappings are learned.
CONCEPTS = [
    "FOOD_HIGH",  # high-fitness place / energy source
    "FOOD_LOW",   # poor place
    "PREDATOR",   # danger nearby
    "SAFE",       # no immediate predator threat
    "COME",       # approach advertised point
    "GO",         # leave advertised point
    "DYING",      # low energy
    "STRONG",     # high energy
    "NORTH", "SOUTH", "EAST", "WEST",
    "HERE",
    "TRUST",
]
C_IDX = {c: i for i, c in enumerate(CONCEPTS)}

# ─── CONFIG ──────────────────────────────────────────────────────────────────
CFG = {
    "grid": 8.0,
    "population": 12,
    "ticks_per_sec": 1.0,
    "signal_range": 2.8,
    "speak_cost": 3.5,
    "direct_cost": 1.8,
    "silence_bonus": 1.2,
    "base_decay": 2.2,
    "fitness_scale": 1.3,
    "mitosis_thresh": 125.0,
    "death_thresh": 0.0,
    "initial_energy": 90.0,
    "predator_count": 2,
    "predator_speed": 0.55,
    "predator_range": 2.2,
    "predator_kill_e": 35.0,
    "predator_broadcast_detect": 4.0,
    "predator_directed_detect": 1.4,
    "peak_positions": [[2.0, 2.0], [5.5, 6.0], [6.5, 1.5]],
    "peak_strengths": [10.0, 8.5, 6.5],
    "noise": 0.2,
    "player_range": 3.2,
    "max_population": 50,
    # Speech learning
    "lexicon_lr": 0.15,
    "self_ground_lr": 0.10,       # speaker privately grounds what it meant
    "teaching_boost": 0.45,
    "trust_decay": 0.93,
    "grammar_mutate": 0.06,
    "min_utterance_e": 5.0,
    "known_word_max": 8,          # human words are truncated into stable acoustic tokens
}


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def tokenise_text(text: str) -> List[str]:
    toks: List[str] = []
    for raw in text.lower().replace(",", " ").replace(".", " ").split():
        cleaned = "".join(ch for ch in raw if ch.isalnum() or ch in "_-')")
        cleaned = cleaned.strip("'\"")[: CFG["known_word_max"]]
        if cleaned:
            toks.append(cleaned)
    return toks[:6]


def landscape_fitness(x: float, y: float, noisy: bool = True) -> float:
    f = 0.0
    for (px, py), s in zip(CFG["peak_positions"], CFG["peak_strengths"]):
        d = math.sqrt((x - px) ** 2 + (y - py) ** 2)
        f += s * math.exp(-0.4 * d)
    if noisy:
        f += random.gauss(0, CFG["noise"])
    return max(0.0, f)


# ─── SPEECH GENOME ───────────────────────────────────────────────────────────

class SpeechGenome:
    """Heritable structure governing how a mote forms utterances."""

    def __init__(self):
        self.order = random.choice([
            "thing-direction",      # lum east
            "direction-thing",      # east lum
            "thing-risk-direction", # lum ka east
            "risk-thing",           # ka lum
        ])
        self.max_len = random.randint(1, 3)
        self.repeat_urgency = random.random() < 0.3
        self.silence_bias = random.uniform(0.3, 0.8)
        self.danger_silence = random.random() < 0.55
        self.vocab_size = random.randint(4, len(TOKENS))
        self.direct_bias = random.uniform(0.35, 0.85)

    def mutate(self) -> "SpeechGenome":
        g = SpeechGenome()
        if random.random() > CFG["grammar_mutate"]:
            g.order = self.order
        g.max_len = max(1, min(4, self.max_len + random.choice([-1, 0, 0, 1])))
        g.repeat_urgency = self.repeat_urgency if random.random() > CFG["grammar_mutate"] else not self.repeat_urgency
        g.silence_bias = clamp(self.silence_bias + random.gauss(0, 0.05), 0.1, 0.95)
        g.danger_silence = self.danger_silence if random.random() > CFG["grammar_mutate"] else not self.danger_silence
        g.vocab_size = max(3, min(len(TOKENS), self.vocab_size + random.choice([-1, 0, 0, 1])))
        g.direct_bias = clamp(self.direct_bias + random.gauss(0, 0.06), 0.0, 1.0)
        return g

    def to_dict(self) -> dict:
        return {
            "order": self.order,
            "max_len": self.max_len,
            "repeat_urgency": self.repeat_urgency,
            "silence_bias": round(self.silence_bias, 2),
            "danger_silence": self.danger_silence,
            "vocab_size": self.vocab_size,
            "direct_bias": round(self.direct_bias, 2),
        }


# ─── LEXICON ─────────────────────────────────────────────────────────────────

class Lexicon:
    """
    Private token→concept mapping.
    Starts with tiny random noise. Updated by teaching, self-grounding, and outcome.
    """

    def __init__(self):
        self.table: Dict[str, Dict[str, float]] = {
            tok: {c: random.uniform(-0.04, 0.04) for c in CONCEPTS} for tok in TOKENS
        }

    def ensure_token(self, token: str):
        if token not in self.table:
            self.table[token] = {c: 0.0 for c in CONCEPTS}

    def top_concept(self, token: str, threshold: float = 0.12) -> Optional[str]:
        if token not in self.table:
            return None
        weights = self.table[token]
        best = max(weights, key=weights.get)
        return best if weights[best] > threshold else None

    def update(self, token: str, concept: str, delta: float):
        if concept not in C_IDX:
            return
        self.ensure_token(token)
        self.table[token][concept] = clamp(self.table[token].get(concept, 0.0) + delta * CFG["lexicon_lr"], -1.0, 1.0)
        # Slightly suppress competitors to reduce ambiguous babble.
        if delta > 0:
            for c in CONCEPTS:
                if c != concept:
                    self.table[token][c] = clamp(self.table[token][c] - abs(delta) * CFG["lexicon_lr"] * 0.015, -1.0, 1.0)

    def self_ground(self, token: str, concept: str):
        """A speaker privately reinforces: 'when I used this sound, I meant this.'"""
        if concept in C_IDX:
            self.ensure_token(token)
            self.table[token][concept] = clamp(self.table[token][concept] + CFG["self_ground_lr"], -1.0, 1.0)

    def interpret(self, tokens: List[str]) -> Dict[str, float]:
        vec = {c: 0.0 for c in CONCEPTS}
        for tok in tokens:
            if tok in self.table:
                for c, w in self.table[tok].items():
                    vec[c] += w
        total = sum(abs(v) for v in vec.values()) or 1.0
        return {c: v / total for c, v in vec.items()}

    def strongest_token_for(self, concept: str, vocab: List[str], threshold: float = 0.08) -> Optional[str]:
        best_tok, best_w = None, threshold
        for tok in vocab:
            w = self.table.get(tok, {}).get(concept, 0.0)
            if w > best_w:
                best_tok, best_w = tok, w
        return best_tok

    def to_dict(self, threshold: float = 0.10) -> dict:
        out = {}
        for tok, weights in sorted(self.table.items()):
            best = max(weights, key=weights.get)
            if weights[best] > threshold:
                out[tok] = {"concept": best, "weight": round(weights[best], 2)}
        return out


# ─── UTTERANCE / SILENCE ─────────────────────────────────────────────────────

@dataclass
class Utterance:
    tokens: List[str]
    speaker_id: int
    target_id: Optional[int]
    intended_concept: str
    position: List[float]
    fitness: float
    energy: float
    tick: int
    is_silence: bool = False
    is_player: bool = False
    is_teaching: bool = False
    is_broadcast: bool = False

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
            "position": self.position,
            "fitness": round(self.fitness, 2),
            "energy": round(self.energy, 1),
            "tick": self.tick,
            "is_silence": self.is_silence,
            "is_player": self.is_player,
            "is_teaching": self.is_teaching,
            "is_broadcast": self.is_broadcast,
        }


@dataclass
class SilenceDecision:
    tick: int
    mote_id: int
    reason: str
    energy: float
    fitness: float
    predator_distance: float
    neighbor_count: int
    info_delta: float

    def to_dict(self) -> dict:
        d = asdict(self)
        d["energy"] = round(self.energy, 1)
        d["fitness"] = round(self.fitness, 2)
        d["predator_distance"] = round(self.predator_distance, 2)
        d["info_delta"] = round(self.info_delta, 2)
        return d


# ─── INTENT SYSTEM ───────────────────────────────────────────────────────────

def derive_intent(mote: "Mote") -> str:
    """Internal pre-linguistic drive. Not output language."""
    if mote.nearest_predator_dist < 2.5:
        return "PREDATOR"
    if mote.energy < 30:
        return "DYING"
    if mote.fitness > 7.0:
        return "FOOD_HIGH"
    if mote.fitness < 2.0:
        return "FOOD_LOW"
    if mote.fitness > 4.0 and mote.last_gradient:
        return {"+x": "EAST", "-x": "WEST", "+y": "NORTH", "-y": "SOUTH"}.get(mote.last_gradient, "FOOD_HIGH")
    if mote.energy > 105:
        return "STRONG"
    return "SAFE"


# ─── MOTE ────────────────────────────────────────────────────────────────────

class Mote:
    _id = 0

    def __init__(self, x: float, y: float, energy: float, parent_id: int = -1):
        Mote._id += 1
        self.id = Mote._id
        self.parent_id = parent_id
        self.x = x
        self.y = y
        self.energy = energy
        self.fitness = 0.0
        self.best_known_fitness = 0.0
        self.best_known_pos = [x, y]
        self.last_gradient: Optional[str] = None
        self.nearest_predator_dist = 99.0
        self.age = 0
        self.alive = True

        self.genome = SpeechGenome()
        self.lexicon = Lexicon()

        self.inbox: Deque[Utterance] = deque(maxlen=10)
        self.trust: Dict[int, float] = {}
        self.known_peer_fitness: Dict[int, float] = {}
        self.last_acted_utterance: Optional[Utterance] = None
        self.energy_before_acting = 0.0
        self.silence_reason: Optional[str] = None

        self.times_spoke = 0
        self.times_silent_chosen = 0
        self.times_silent_fear = 0
        self.times_silent_alone = 0
        self.times_directed = 0
        self.times_broadcast = 0
        self.lexicon_updates = 0
        self.utterances_history: Deque[Utterance] = deque(maxlen=12)
        self.silence_history: Deque[SilenceDecision] = deque(maxlen=20)

    def is_alive(self) -> bool:
        return self.alive and self.energy > CFG["death_thresh"]

    # ── Sensing ──────────────────────────────────────────────────────────────
    def sense(self):
        self.fitness = landscape_fitness(self.x, self.y, noisy=True)
        if self.fitness > self.best_known_fitness:
            self.best_known_fitness = self.fitness
            self.best_known_pos = [self.x, self.y]

    # ── Speech generation ────────────────────────────────────────────────────
    def generate_utterance(self, neighbors: List["Mote"], tick: int) -> Tuple[Optional[Utterance], Optional[SilenceDecision]]:
        self.silence_reason = None

        max_delta = 0.0
        neediest: Optional[Mote] = None
        for n in neighbors:
            their_f = self.known_peer_fitness.get(n.id, 0.0)
            delta = self.best_known_fitness - their_f
            if delta > max_delta:
                max_delta = delta
                neediest = n

        def silence(reason: str) -> Tuple[None, SilenceDecision]:
            sd = SilenceDecision(
                tick=tick,
                mote_id=self.id,
                reason=reason,
                energy=self.energy,
                fitness=self.fitness,
                predator_distance=self.nearest_predator_dist,
                neighbor_count=len(neighbors),
                info_delta=max_delta,
            )
            self.silence_reason = reason
            self.silence_history.append(sd)
            return None, sd

        # Fear silence.
        if self.genome.danger_silence and self.nearest_predator_dist < 1.8:
            self.times_silent_fear += 1
            return silence("predator")

        if self.energy < CFG["min_utterance_e"]:
            self.times_silent_chosen += 1
            return silence("energy")

        if not neighbors:
            self.times_silent_alone += 1
            return silence("alone")

        # Chosen silence: no information asymmetry.
        if max_delta < self.genome.silence_bias * 2.0:
            self.times_silent_chosen += 1
            self.energy += CFG["silence_bonus"]
            return silence("no_info")

        intent = derive_intent(self)
        vocab = TOKENS[: self.genome.vocab_size]
        tokens = self._compose_tokens(intent, vocab)
        if not tokens:
            self.times_silent_chosen += 1
            return silence("no_tokens")

        # Self-grounding gives each mote ownership of the sound it used.
        for tok in tokens:
            self.lexicon.self_ground(tok, intent)
            self.lexicon_updates += 1

        # Directed speech is favored when predator is nearby and by direct_bias.
        target_id = None
        is_broadcast = True
        if neediest and (random.random() < self.genome.direct_bias or self.nearest_predator_dist < 3.0):
            target_id = neediest.id
            is_broadcast = False
            cost = CFG["direct_cost"]
            self.times_directed += 1
        else:
            cost = CFG["speak_cost"]
            self.times_broadcast += 1

        self.energy -= cost
        self.times_spoke += 1
        utt = Utterance(
            tokens=tokens,
            speaker_id=self.id,
            target_id=target_id,
            intended_concept=intent,
            position=[round(self.best_known_pos[0], 2), round(self.best_known_pos[1], 2)],
            fitness=self.best_known_fitness,
            energy=self.energy,
            tick=tick,
            is_broadcast=is_broadcast,
        )
        self.utterances_history.append(utt)
        return utt, None

    def _compose_tokens(self, intent: str, vocab: List[str]) -> List[str]:
        primary = self.lexicon.strongest_token_for(intent, vocab) or random.choice(vocab)

        direction_token = None
        if intent in ["NORTH", "SOUTH", "EAST", "WEST"]:
            direction_token = self.lexicon.strongest_token_for(intent, vocab) or random.choice(vocab)
        elif self.last_gradient:
            dir_c = {"+x": "EAST", "-x": "WEST", "+y": "NORTH", "-y": "SOUTH"}.get(self.last_gradient)
            if dir_c:
                direction_token = self.lexicon.strongest_token_for(dir_c, vocab)

        risk_token = None
        if self.nearest_predator_dist < 4.0:
            risk_token = self.lexicon.strongest_token_for("PREDATOR", vocab)

        if self.genome.order == "thing-direction":
            parts = [primary] + ([direction_token] if direction_token else [])
        elif self.genome.order == "direction-thing":
            parts = ([direction_token] if direction_token else []) + [primary]
        elif self.genome.order == "thing-risk-direction":
            parts = [primary] + ([risk_token] if risk_token else []) + ([direction_token] if direction_token else [])
        elif self.genome.order == "risk-thing":
            parts = ([risk_token] if risk_token else []) + [primary]
        else:
            parts = [primary]

        parts = [p for p in parts if p]
        deduped: List[str] = []
        for p in parts:
            if not deduped or deduped[-1] != p:
                deduped.append(p)
        parts = deduped[: self.genome.max_len]

        # Urgent low-energy repetition.
        if self.genome.repeat_urgency and self.energy < 35 and parts:
            parts = [parts[0], parts[0]][: self.genome.max_len]

        return parts or [random.choice(vocab)]

    # ── Listening + lexicon update ───────────────────────────────────────────
    def receive(self, utt: Utterance):
        self.inbox.append(utt)
        self.known_peer_fitness[utt.speaker_id] = utt.fitness
        self.trust.setdefault(utt.speaker_id, 0.5)

    def act_on_inbox(self):
        """Parse utterances through own lexicon and optionally act."""
        for utt in reversed(self.inbox):
            if utt.is_silence:
                continue
            if utt.target_id is not None and utt.target_id != self.id and not utt.is_player:
                continue

            trust = self.trust.get(utt.speaker_id, 0.5)
            concepts = self.lexicon.interpret(utt.tokens)

            danger = concepts.get("PREDATOR", 0.0) + concepts.get("GO", 0.0) * 0.4
            food = concepts.get("FOOD_HIGH", 0.0) + concepts.get("COME", 0.0) * 0.4 + concepts.get("HERE", 0.0) * 0.2

            if danger > 0.25 and trust > 0.25 and not utt.is_player:
                # Flee from advertised position.
                dx = self.x - utt.position[0]
                dy = self.y - utt.position[1]
                dist = math.sqrt(dx * dx + dy * dy) or 0.001
                step = 0.7 * trust * min(1.0, danger * 2)
                self.x = clamp(self.x + (dx / dist) * step, 0, CFG["grid"])
                self.y = clamp(self.y + (dy / dist) * step, 0, CFG["grid"])
                self.energy_before_acting = self.energy
                self.last_acted_utterance = utt
                break

            # A high claimed fitness can matter, but only if token interpretation supports it.
            if food > 0.20 and trust > 0.25 and utt.fitness > self.best_known_fitness * 0.75:
                dx = utt.position[0] - self.x
                dy = utt.position[1] - self.y
                dist = math.sqrt(dx * dx + dy * dy) or 0.001
                step = 0.55 * trust * min(1.0, food * 2)
                self.x = clamp(self.x + (dx / dist) * step, 0, CFG["grid"])
                self.y = clamp(self.y + (dy / dist) * step, 0, CFG["grid"])
                self.energy_before_acting = self.energy
                self.last_acted_utterance = utt
                break

    def update_lexicon_from_outcome(self):
        """Ground tokens by energy outcome after acting on them."""
        if self.last_acted_utterance is None:
            return
        utt = self.last_acted_utterance
        delta_e = self.energy - self.energy_before_acting

        if delta_e > 1.5:
            outcome_concept = "FOOD_HIGH" if self.fitness > 5.0 else "SAFE"
            sign = 1.0
        elif delta_e < -4.0 or self.nearest_predator_dist < 1.6:
            outcome_concept = "PREDATOR"
            sign = 1.0
        else:
            self.last_acted_utterance = None
            return

        for tok in utt.tokens:
            self.lexicon.update(tok, outcome_concept, sign)
            self.lexicon_updates += 1

        trust_delta = 0.10 if delta_e > 0 else -0.08
        self.trust[utt.speaker_id] = clamp(self.trust.get(utt.speaker_id, 0.5) + trust_delta, 0.0, 1.0)
        self.last_acted_utterance = None

    def teach(self, human_word: str, context_concept: str):
        tok = human_word.lower()[: CFG["known_word_max"]]
        if not tok or context_concept not in C_IDX:
            return
        self.lexicon.ensure_token(tok)
        self.lexicon.update(tok, context_concept, CFG["teaching_boost"] / CFG["lexicon_lr"])
        self.lexicon_updates += 1

    # ── Movement / thermodynamics ────────────────────────────────────────────
    def explore(self, predators: List["Predator"]):
        self.nearest_predator_dist = min((p.dist_to(self.x, self.y) for p in predators), default=99.0)

        # Flee if predator very close.
        if self.nearest_predator_dist < 1.3 and predators:
            closest = min(predators, key=lambda p: p.dist_to(self.x, self.y))
            dx, dy = self.x - closest.x, self.y - closest.y
            dist = math.sqrt(dx * dx + dy * dy) or 0.001
            self.x = clamp(self.x + (dx / dist) * 0.9, 0, CFG["grid"])
            self.y = clamp(self.y + (dy / dist) * 0.9, 0, CFG["grid"])
            return

        old_f = self.fitness
        step = random.uniform(0.2, 0.75)
        dirs = [(step, 0, "+x"), (-step, 0, "-x"), (0, step, "+y"), (0, -step, "-y")]
        random.shuffle(dirs)
        dx, dy, label = dirs[0]
        nx = clamp(self.x + dx, 0, CFG["grid"])
        ny = clamp(self.y + dy, 0, CFG["grid"])
        nf = landscape_fitness(nx, ny, noisy=False)
        if nf >= old_f * 0.72:
            self.x, self.y = nx, ny
            if nf > old_f:
                self.last_gradient = label

    def thermodynamics(self):
        self.energy += self.fitness * CFG["fitness_scale"] - CFG["base_decay"]
        self.age += 1
        for sid in list(self.trust):
            self.trust[sid] *= CFG["trust_decay"]
        if self.energy <= CFG["death_thresh"]:
            self.alive = False

    def reproduce(self) -> "Mote":
        self.energy /= 2
        child = Mote(
            clamp(self.x + random.gauss(0, 0.35), 0, CFG["grid"]),
            clamp(self.y + random.gauss(0, 0.35), 0, CFG["grid"]),
            self.energy,
            self.id,
        )
        child.genome = self.genome.mutate()
        # Partial language inheritance with noise.
        all_tokens = set(self.lexicon.table.keys()) | set(child.lexicon.table.keys())
        for tok in all_tokens:
            child.lexicon.ensure_token(tok)
            self.lexicon.ensure_token(tok)
            for concept in CONCEPTS:
                child.lexicon.table[tok][concept] = clamp(self.lexicon.table[tok][concept] + random.gauss(0, 0.025), -1.0, 1.0)
        return child

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "energy": round(self.energy, 1),
            "fitness": round(self.fitness, 2),
            "age": self.age,
            "spoke": self.times_spoke,
            "silent_choice": self.times_silent_chosen,
            "silent_fear": self.times_silent_fear,
            "silent_alone": self.times_silent_alone,
            "directed": self.times_directed,
            "broadcast": self.times_broadcast,
            "lexicon_updates": self.lexicon_updates,
            "genome": self.genome.to_dict(),
            "top_lexicon": self.lexicon.to_dict(threshold=0.16),
            "recent_utterances": [u.text for u in list(self.utterances_history)[-4:]],
            "last_intent": derive_intent(self),  # diagnostic, not what it literally says
            "silence_reason": self.silence_reason,
            "pred_dist": round(self.nearest_predator_dist, 2),
        }


# ─── PREDATOR ────────────────────────────────────────────────────────────────

class Predator:
    _id = 0

    def __init__(self):
        Predator._id += 1
        self.id = Predator._id
        corners = [[0.5, 0.5], [7.5, 0.5], [0.5, 7.5], [7.5, 7.5]]
        self.x, self.y = random.choice(corners)
        self.target_x, self.target_y = self.x, self.y
        self.signals_followed = 0
        self.damage_dealt = 0.0

    def update(self, utterances: List[Utterance], motes: List[Mote], tick: int):
        """Content-following predator: chases advertised positions in meaningful utterances."""
        best_u = None
        best_score = 1.0
        for u in utterances:
            if u.is_silence or u.is_player or u.tick < tick - 2:
                continue
            d = self.dist_to(u.position[0], u.position[1])
            detect = CFG["predator_broadcast_detect"] if u.is_broadcast else CFG["predator_directed_detect"]
            if d > detect:
                continue
            score = u.fitness / (1.0 + d)
            if score > best_score:
                best_score = score
                best_u = u
        if best_u:
            self.target_x, self.target_y = best_u.position
            self.signals_followed += 1

        dx, dy = self.target_x - self.x, self.target_y - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > 0.1:
            self.x += (dx / dist) * CFG["predator_speed"]
            self.y += (dy / dist) * CFG["predator_speed"]
        else:
            self.target_x = random.uniform(1, CFG["grid"] - 1)
            self.target_y = random.uniform(1, CFG["grid"] - 1)

        self.x = clamp(self.x, 0, CFG["grid"])
        self.y = clamp(self.y, 0, CFG["grid"])

        for m in motes:
            if not m.is_alive():
                continue
            d = self.dist_to(m.x, m.y)
            if d < CFG["predator_range"] * 0.5:
                m.energy -= CFG["predator_kill_e"]
                self.damage_dealt += CFG["predator_kill_e"]
                if m.energy <= CFG["death_thresh"]:
                    m.alive = False

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
            "damage_dealt": round(self.damage_dealt, 1),
        }


# ─── SWARM ───────────────────────────────────────────────────────────────────

class Swarm:
    def __init__(self):
        self.motes: List[Mote] = []
        self.predators: List[Predator] = []
        self.tick = 0
        self.lock = threading.RLock()
        self.recent_utterances: List[dict] = []
        self.silence_log: Deque[dict] = deque(maxlen=500)
        self.events: Deque[dict] = deque(maxlen=400)
        self.player = {"x": 4.0, "y": 4.0, "fitness": 0.0}
        self.running = False
        self.pending_player_actions: List[dict] = []

        Mote._id = 0
        Predator._id = 0
        for _ in range(CFG["population"]):
            self.motes.append(Mote(random.uniform(0, CFG["grid"]), random.uniform(0, CFG["grid"]), CFG["initial_energy"]))
        for _ in range(CFG["predator_count"]):
            self.predators.append(Predator())

    def neighbors_of(self, mote: Mote) -> List[Mote]:
        return [
            o for o in self.motes
            if o.id != mote.id and o.is_alive() and math.sqrt((o.x - mote.x) ** 2 + (o.y - mote.y) ** 2) <= CFG["signal_range"]
        ]

    def player_nearby(self) -> List[Tuple[Mote, float]]:
        px, py = self.player["x"], self.player["y"]
        res = []
        for m in self.motes:
            if not m.is_alive():
                continue
            d = math.sqrt((m.x - px) ** 2 + (m.y - py) ** 2)
            if d <= CFG["player_range"]:
                res.append((m, d))
        return sorted(res, key=lambda x: x[1])

    def event_for_utterance(self, utt: Utterance, mote: Optional[Mote], event_type: str = "utterance") -> dict:
        return {
            "type": event_type,
            "mote_id": utt.speaker_id if mote is None else mote.id,
            "tokens": utt.tokens,
            "text": utt.text,
            "intent": utt.intended_concept,
            "target_id": utt.target_id,
            "fitness": round(utt.fitness, 2),
            "energy": round(utt.energy if mote is None else mote.energy, 1),
            "x": round(utt.position[0] if mote is None else mote.x, 2),
            "y": round(utt.position[1] if mote is None else mote.y, 2),
            "tick": utt.tick,
            "silence": False,
            "silence_reason": None,
            "is_player": utt.is_player,
            "is_teaching": utt.is_teaching,
            "broadcast": utt.is_broadcast,
        }

    def tick_step(self) -> List[dict]:
        self.tick += 1
        tick_utts: List[Utterance] = []
        new_events: List[dict] = []

        with self.lock:
            actions = list(self.pending_player_actions)
            self.pending_player_actions = []

        px, py = self.player["x"], self.player["y"]
        self.player["fitness"] = round(landscape_fitness(px, py, noisy=False), 2)

        # Phase 1: sense.
        for m in self.motes:
            if not m.is_alive():
                continue
            m.sense()
            m.nearest_predator_dist = min((p.dist_to(m.x, m.y) for p in self.predators), default=99.0)

        # Phase 2: player actions.
        for action in actions:
            if action.get("type") != "speak":
                continue
            tokens = action.get("tokens") or ["?"]
            pos = action.get("position", [self.player["x"], self.player["y"]])
            pu = Utterance(
                tokens=tokens,
                speaker_id=-1,
                target_id=None,
                intended_concept=action.get("concept") or "UNKNOWN",
                position=[clamp(float(pos[0]), 0, CFG["grid"]), clamp(float(pos[1]), 0, CFG["grid"])],
                fitness=float(action.get("fitness", self.player["fitness"])),
                energy=999.0,
                tick=self.tick,
                is_player=True,
                is_teaching=bool(action.get("teaching", False)),
                is_broadcast=True,
            )
            tick_utts.append(pu)
            new_events.append(self.event_for_utterance(pu, None, "player"))

            for m, _d in self.player_nearby():
                m.receive(pu)
                if pu.is_teaching and pu.intended_concept in C_IDX:
                    for tok in tokens:
                        m.teach(tok, pu.intended_concept)
                    new_events.append({
                        "type": "teaching",
                        "mote_id": m.id,
                        "tokens": tokens,
                        "text": " ".join(tokens),
                        "concept": pu.intended_concept,
                        "tick": self.tick,
                        "energy": round(m.energy, 1),
                        "fitness": round(m.fitness, 2),
                        "x": round(m.x, 2),
                        "y": round(m.y, 2),
                    })

        # Phase 3: mote speech.
        for m in list(self.motes):
            if not m.is_alive():
                continue
            neighbors = self.neighbors_of(m)
            utt, sd = m.generate_utterance(neighbors, self.tick)
            if sd:
                self.silence_log.append(sd.to_dict())

            if utt:
                tick_utts.append(utt)
                for n in neighbors:
                    if utt.target_id is None or utt.target_id == n.id:
                        n.receive(utt)

                pd = math.sqrt((m.x - px) ** 2 + (m.y - py) ** 2)
                if pd <= CFG["player_range"] * 1.15:
                    new_events.append(self.event_for_utterance(utt, m, "utterance"))
            else:
                pd = math.sqrt((m.x - px) ** 2 + (m.y - py) ** 2)
                if pd <= CFG["player_range"] and m.silence_reason and random.random() < 0.45:
                    new_events.append({
                        "type": "silence",
                        "mote_id": m.id,
                        "tokens": [],
                        "text": "",
                        "intent": derive_intent(m),
                        "fitness": round(m.fitness, 2),
                        "energy": round(m.energy, 1),
                        "x": round(m.x, 2),
                        "y": round(m.y, 2),
                        "tick": self.tick,
                        "silence": True,
                        "silence_reason": m.silence_reason,
                    })

        # Phase 4: predators.
        for p in self.predators:
            p.update(tick_utts, self.motes, self.tick)

        # Phase 5: listen/act.
        for m in self.motes:
            if m.is_alive():
                m.act_on_inbox()

        # Phase 6: explore.
        for m in self.motes:
            if m.is_alive():
                m.explore(self.predators)

        # Phase 7: thermodynamics and learning.
        for m in self.motes:
            if m.is_alive():
                m.thermodynamics()
                m.update_lexicon_from_outcome()

        # Phase 8: birth/death.
        next_motes: List[Mote] = []
        for m in self.motes:
            if not m.is_alive():
                new_events.append({
                    "type": "death", "mote_id": m.id, "tick": self.tick, "text": "",
                    "tokens": [], "intent": "DYING", "silence": False, "silence_reason": None,
                    "fitness": 0, "energy": 0, "x": round(m.x, 2), "y": round(m.y, 2),
                })
                continue
            if m.energy >= CFG["mitosis_thresh"] and len(next_motes) < CFG["max_population"]:
                child = m.reproduce()
                next_motes.append(child)
                birth_token = random.choice(TOKENS[:4])
                new_events.append({
                    "type": "birth", "mote_id": child.id, "tick": self.tick, "text": birth_token,
                    "tokens": [birth_token], "intent": "SAFE", "silence": False, "silence_reason": None,
                    "fitness": 0, "energy": round(child.energy, 1), "x": round(child.x, 2), "y": round(child.y, 2),
                })
            next_motes.append(m)
        self.motes = next_motes[: CFG["max_population"]]

        with self.lock:
            self.recent_utterances = [u.to_dict() for u in tick_utts[-50:]]
            self.events.extend(new_events)

        return new_events

    def snapshot(self) -> dict:
        with self.lock:
            events = list(self.events)[-80:]
            recent = list(self.recent_utterances)
            silence = list(self.silence_log)[-80:]

        motes = [m.to_dict() for m in self.motes if m.is_alive()]
        total_spoke = sum(m["spoke"] for m in motes)
        total_directed = sum(m["directed"] for m in motes)
        total_broadcast = sum(m["broadcast"] for m in motes)
        total_choice_silence = sum(m["silent_choice"] for m in motes)
        total_fear_silence = sum(m["silent_fear"] for m in motes)
        total_updates = sum(m["lexicon_updates"] for m in motes)

        return {
            "tick": self.tick,
            "population": len(motes),
            "motes": motes,
            "predators": [p.to_dict() for p in self.predators],
            "player": dict(self.player),
            "events": events,
            "recent_utterances": recent,
            "silence": silence,
            "peaks": [{"x": p[0], "y": p[1], "s": s} for p, s in zip(CFG["peak_positions"], CFG["peak_strengths"])],
            "tokens": TOKENS,
            "concepts": CONCEPTS,
            "stats": {
                "spoke": total_spoke,
                "directed": total_directed,
                "broadcast": total_broadcast,
                "directed_ratio": round(total_directed / max(1, total_spoke), 3),
                "choice_silence": total_choice_silence,
                "fear_silence": total_fear_silence,
                "lexicon_updates": total_updates,
            },
        }


# ─── SERVER ──────────────────────────────────────────────────────────────────

swarm = Swarm()
swarm_thread: Optional[threading.Thread] = None


def run_loop():
    swarm.running = True
    while swarm.running:
        try:
            swarm.tick_step()
        except Exception as exc:
            print(f"[swarm error] {exc}")
        time.sleep(1.0 / CFG["ticks_per_sec"])


def start_swarm_thread():
    global swarm_thread
    swarm_thread = threading.Thread(target=run_loop, daemon=True)
    swarm_thread.start()


start_swarm_thread()


@app.route("/stream")
def stream():
    def gen():
        last_tick = -1
        while True:
            if swarm.tick != last_tick:
                last_tick = swarm.tick
                yield f"data: {json.dumps(swarm.snapshot())}\n\n"
            time.sleep(0.08)
    return Response(gen(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/player/move", methods=["POST"])
def move():
    d = request.json or {}
    with swarm.lock:
        swarm.player["x"] = clamp(float(d.get("x", 4)), 0, CFG["grid"])
        swarm.player["y"] = clamp(float(d.get("y", 4)), 0, CFG["grid"])
        swarm.player["fitness"] = round(landscape_fitness(swarm.player["x"], swarm.player["y"], noisy=False), 2)
        player = dict(swarm.player)
    return jsonify({"ok": True, "player": player})


@app.route("/player/speak", methods=["POST"])
def speak():
    """
    Player speaks tokens/words into the swarm.
    Body: { text, tokens, concept, teaching, fitness, x, y }
    - teaching=false: motes must understand via their learned lexicons.
    - teaching=true: nearby motes ground the word in the supplied concept.
    """
    d = request.json or {}
    raw_text = d.get("text", "").strip()
    tokens = tokenise_text(raw_text) if raw_text else [str(t).lower()[: CFG["known_word_max"]] for t in d.get("tokens", ["?"]) if str(t)]
    if not tokens:
        tokens = ["?"]

    with swarm.lock:
        default_pos = [swarm.player["x"], swarm.player["y"]]
        default_fit = swarm.player["fitness"]

    x = clamp(float(d.get("x", default_pos[0])), 0, CFG["grid"])
    y = clamp(float(d.get("y", default_pos[1])), 0, CFG["grid"])
    action = {
        "type": "speak",
        "tokens": tokens[:6],
        "concept": d.get("concept"),
        "teaching": bool(d.get("teaching", False)),
        "fitness": float(d.get("fitness", default_fit)),
        "position": [x, y],
    }
    with swarm.lock:
        swarm.pending_player_actions.append(action)
    return jsonify({"ok": True, "tokens": tokens[:6], "action": action})


@app.route("/player/teach", methods=["POST"])
def teach():
    """Explicit teaching: player says a word and labels its grounded concept."""
    d = request.json or {}
    word = (d.get("word") or d.get("text") or "").strip().lower()[: CFG["known_word_max"]]
    concept = d.get("concept", "SAFE")
    if concept not in CONCEPTS:
        return jsonify({"error": "unknown concept", "valid": CONCEPTS}), 400
    if not word:
        return jsonify({"error": "missing word"}), 400
    with swarm.lock:
        pos = [swarm.player["x"], swarm.player["y"]]
        fit = swarm.player["fitness"]
        swarm.pending_player_actions.append({
            "type": "speak",
            "tokens": [word],
            "concept": concept,
            "teaching": True,
            "fitness": fit,
            "position": pos,
        })
    return jsonify({"ok": True, "word": word, "concept": concept})


@app.route("/mote/<int:mote_id>/lexicon")
def mote_lexicon(mote_id: int):
    for m in swarm.motes:
        if m.id == mote_id and m.is_alive():
            return jsonify({
                "id": mote_id,
                "lexicon": m.lexicon.to_dict(threshold=0.08),
                "genome": m.genome.to_dict(),
                "utterances": [u.to_dict() for u in list(m.utterances_history)],
                "silences": [s.to_dict() for s in list(m.silence_history)],
                "intent": derive_intent(m),
                "trust": {str(k): round(v, 2) for k, v in m.trust.items()},
            })
    return jsonify({"error": "not found"}), 404


@app.route("/state")
def state():
    return jsonify(swarm.snapshot())


@app.route("/concepts")
def concepts():
    return jsonify({"concepts": CONCEPTS, "tokens": TOKENS})


@app.route("/health")
def health():
    return jsonify({"ok": True, "tick": swarm.tick, "population": len([m for m in swarm.motes if m.is_alive()])})


@app.route("/reset", methods=["POST"])
def reset():
    global swarm
    old = swarm
    old.running = False
    time.sleep(0.2)
    swarm = Swarm()
    start_swarm_thread()
    return jsonify({"ok": True})


if __name__ == "__main__":
    print("TAIS-LANG v3: Living Speech")
    print("http://localhost:5123")
    print(f"Seed tokens: {TOKENS[:8]}...")
    print(f"Concepts: {CONCEPTS}")
    print("Endpoints: /stream /state /player/move /player/speak /player/teach /mote/<id>/lexicon /reset")
    app.run(host="0.0.0.0", port=5123, debug=False, threaded=True)
