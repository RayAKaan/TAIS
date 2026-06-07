"""
TAIS-LANG Conversational Swarm — Backend Server
================================================

Flask SSE server. Swarm runs in a background thread.
Player injects signals. Motes respond via codebook translation.
Predators follow signal content, not volume.
Silence tracked as explicit decisions with reasons.
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

# ─── CONFIG ──────────────────────────────────────────────────────────────────

CFG = {
    "grid": 8.0,
    "population": 14,
    "ticks_per_sec": 1.2,
    "signal_range": 2.8,
    "speak_cost": 4.0,
    "direct_cost": 2.0,
    "silence_bonus": 1.5,
    "base_decay": 2.5,
    "fitness_scale": 1.4,
    "mitosis_thresh": 130.0,
    "death_thresh": 0.0,
    "initial_energy": 85.0,
    "predator_count": 2,
    "predator_speed": 0.6,
    "predator_range": 2.5,
    "predator_kill_e": 40.0,  # energy drain on contact
    "predator_broadcast_detect": 4.0,
    "predator_directed_detect": 1.6,
    "info_threshold": 1.8,
    "trust_decay": 0.92,
    "memory": 6,
    "peak_positions": [[2.0, 2.0], [5.5, 6.0], [6.5, 1.5]],
    "peak_strengths": [10.0, 8.5, 6.5],
    "noise": 0.25,
    "player_range": 3.0,  # how far player signal travels
    "max_population": 60,
}


# ─── CODEBOOK ────────────────────────────────────────────────────────────────
# State → language. Fixed mappings. No generation, no prediction.
# The "voice" of a Mote is entirely its thermodynamic state.


def energy_phrase(e: float, ctx: str = "neutral") -> str:
    if e > 150:
        return random.choice(["I overflow.", "Come. I have much to share.", "Abundance here."])
    if e > 110:
        return random.choice(["I am well.", "The ground is good.", "Strong."])
    if e > 75:
        return random.choice(["I hold.", "Enough for now.", "Surviving."])
    if e > 45:
        return random.choice(["I fade.", "Thinner now.", "Help if you have it."])
    if e > 20:
        return random.choice(["Dying.", "Almost gone.", "Little left."])
    return random.choice(["...", "...", "last breath."])


def fitness_phrase(f: float) -> str:
    if f > 8.5:
        return random.choice(["This place is rich.", "Stay here. This is it.", "The peak. I found it."])
    if f > 6.0:
        return random.choice(["Good here.", "Worth staying.", "Strong ground."])
    if f > 3.5:
        return random.choice(["Thin.", "Searching still.", "Not yet."])
    if f > 1.5:
        return random.choice(["Nothing here.", "Barren.", "I must move."])
    return random.choice(["Empty.", "Dead ground.", "Wrong place."])


def predator_phrase(dist: float) -> Optional[str]:
    if dist < 1.8:
        return None  # SILENCE — too dangerous
    if dist < 2.5:
        return random.choice(["Something hunts near.", "Careful. Close.", "Quiet now."])
    if dist < 3.5:
        return random.choice(["A hunter moves.", "I sense danger.", "Watch yourself."])
    return None


def landscape_fitness(x: float, y: float, noisy: bool = True) -> float:
    f = 0.0
    for (px, py), s in zip(CFG["peak_positions"], CFG["peak_strengths"]):
        d = math.sqrt((x - px) ** 2 + (y - py) ** 2)
        f += s * math.exp(-0.4 * d)
    if noisy:
        f += random.gauss(0, CFG["noise"])
    return max(0.0, f)


def response_to_player(mote: "Mote", player_signal: dict, predators: List["Predator"]) -> Optional[str]:
    """Mote reacts to player's injected signal."""
    player_fitness = player_signal.get("fitness", 0.0)
    player_pos = player_signal.get("position", [4.0, 4.0])

    # Check predator proximity first — mote may be too scared.
    pred_dist = mote.nearest_predator_dist
    if pred_dist < 1.8:
        return None  # silence — chosen, fear-driven

    responses: List[str] = []

    # React to fitness information.
    if player_fitness > mote.best_known_fitness + 2.0:
        responses.append(random.choice(["Where? Show me the way.", "Better than I know. Lead me.", "I will come."]))
    elif player_fitness > mote.best_known_fitness:
        responses.append(random.choice(["Slightly better. I consider it.", "Possible. I will see.", "Interesting."]))
    elif player_fitness < mote.fitness - 1.5:
        responses.append(random.choice(["I know better ground.", "Stay here. Better than where you are.", "Come to me instead."]))

    # Warn player if predator near player position.
    player_near_pred = min((p.dist_to(player_pos[0], player_pos[1]) for p in predators), default=99.0)
    if player_near_pred < 2.5:
        responses.append(random.choice(["Danger near you.", "A hunter is close to you.", "Do not stay there."]))

    # Dying mote reaches out.
    if mote.energy < 35:
        responses.append(random.choice(["I am almost gone. Remember where I was.", "Fading. Pass on what I knew.", "Dying here."]))

    if not responses:
        # Default: state report.
        responses.append(fitness_phrase(mote.fitness))

    return " ".join(responses[:2])  # max 2 ideas per response


def compose_mote_voice(mote: "Mote", context: str = "ambient") -> Optional[str]:
    """Full voice composition for a Mote. Returns None if mote chooses silence."""
    # Fear silences.
    if mote.nearest_predator_dist < 1.8:
        mote.silence_reason = "predator"
        return None

    parts: List[str] = []

    pred_warn = predator_phrase(mote.nearest_predator_dist)
    if pred_warn:
        parts.append(pred_warn)

    parts.append(fitness_phrase(mote.fitness))

    if mote.energy < 50 or mote.energy > 120:
        parts.append(energy_phrase(mote.energy))

    if mote.last_gradient:
        grad_map = {"+x": "east", "-x": "west", "+y": "north", "-y": "south"}
        direction = grad_map.get(mote.last_gradient, "")
        if direction and mote.fitness > 4:
            parts.append(random.choice([f"Better to the {direction}.", f"I came from the {direction}.", f"Go {direction}."]))

    return " ".join(parts[:3])


# ─── SIGNAL / SILENCE ────────────────────────────────────────────────────────

@dataclass
class Signal:
    sender_id: int
    target_id: Optional[int]
    position: List[float]
    fitness: float
    energy: float
    gradient: Optional[str]
    tick: int
    is_silence: bool = False
    is_player: bool = False
    is_broadcast: bool = False

    def info_value(self, receiver_best: float) -> float:
        if self.is_silence:
            return 0.0
        return max(0.0, self.fitness - receiver_best)


@dataclass
class SilenceDecision:
    tick: int
    mote_id: int
    reason: str  # predator | alone | no_info | energy | fear
    energy: float
    fitness: float
    predator_distance: float
    neighbors: int = 0
    info_delta: float = 0.0
    context: str = "mote"


# ─── PREDATOR ────────────────────────────────────────────────────────────────

class Predator:
    _id = 0

    def __init__(self):
        Predator._id += 1
        self.id = Predator._id
        self.x = random.uniform(0, CFG["grid"])
        self.y = random.uniform(0, CFG["grid"])
        self.target_x = self.x
        self.target_y = self.y
        self.last_signal_tick = -1
        self.signals_followed = 0
        self.damage_dealt = 0.0

    def update(self, signals: List[Signal], motes: List["Mote"], tick: int):
        """
        KEY DESIGN: predator follows signal CONTENT (advertised positions),
        not signal volume. It hunts where Motes say good things are.
        This makes honest signaling dangerous near peaks.
        """
        best_signal: Optional[Signal] = None
        best_score = 3.0  # minimum threshold to bother chasing

        for sig in signals:
            if sig.is_silence or sig.is_player:
                continue
            # Broadcasts leak farther; directed signals are only detectable near the advertised content.
            d_to_content = self.dist_to(sig.position[0], sig.position[1])
            detect_range = CFG["predator_broadcast_detect"] if sig.is_broadcast else CFG["predator_directed_detect"]
            if d_to_content > detect_range:
                continue
            score = sig.fitness / (1.0 + d_to_content)
            if score > best_score:
                best_score = score
                best_signal = sig

        if best_signal and best_signal.tick >= tick - 2:
            # Move toward the ADVERTISED position.
            self.target_x = best_signal.position[0]
            self.target_y = best_signal.position[1]
            self.last_signal_tick = tick
            self.signals_followed += 1

        # Move toward target.
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist > 0.1:
            speed = CFG["predator_speed"]
            self.x += (dx / dist) * speed
            self.y += (dy / dist) * speed
        else:
            # Arrived, patrol randomly.
            self.target_x = random.uniform(0, CFG["grid"])
            self.target_y = random.uniform(0, CFG["grid"])

        self.x = max(0, min(CFG["grid"], self.x))
        self.y = max(0, min(CFG["grid"], self.y))

        # Attack motes in range.
        for mote in motes:
            if not mote.alive:
                continue
            d = self.dist_to(mote.x, mote.y)
            if d < CFG["predator_range"] * 0.5:
                mote.energy -= CFG["predator_kill_e"]
                self.damage_dealt += CFG["predator_kill_e"]
                if mote.energy <= CFG["death_thresh"]:
                    mote.alive = False

    def dist_to(self, x: float, y: float) -> float:
        return math.sqrt((self.x - x) ** 2 + (self.y - y) ** 2)


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
        self.inbox: Deque[Signal] = deque(maxlen=CFG["memory"])
        self.trust: Dict[int, float] = {}
        self.known_peers: Dict[int, float] = {}
        self.speaking_threshold = random.uniform(0.8, 3.5)
        self.broadcast_bias = random.uniform(0.0, 1.0)
        self.nearest_predator_dist = 99.0
        self.silence_reason: Optional[str] = None  # predator | no_info | energy | alone | None
        self.age = 0
        self.alive = True

        # Stats.
        self.times_spoke = 0
        self.times_silent_chosen = 0
        self.times_silent_predator = 0
        self.times_silent_alone = 0
        self.times_directed = 0
        self.times_broadcast = 0

        # Recent voice log for conversation panel.
        self.recent_voice: Optional[str] = None
        self.voice_tick = -1

    def is_alive(self) -> bool:
        return self.alive and self.energy > CFG["death_thresh"]

    def sense(self):
        self.fitness = landscape_fitness(self.x, self.y, noisy=True)
        if self.fitness > self.best_known_fitness:
            self.best_known_fitness = self.fitness
            self.best_known_pos = [self.x, self.y]

    def explore(self, predators: List[Predator]):
        # Check predator proximity.
        self.nearest_predator_dist = min((p.dist_to(self.x, self.y) for p in predators), default=99.0)

        # Fear response: flee if predator very close.
        if self.nearest_predator_dist < 1.5 and predators:
            closest = min(predators, key=lambda p: p.dist_to(self.x, self.y))
            dx = self.x - closest.x
            dy = self.y - closest.y
            dist = math.sqrt(dx * dx + dy * dy) or 0.001
            flee_speed = 0.8
            self.x = max(0, min(CFG["grid"], self.x + (dx / dist) * flee_speed))
            self.y = max(0, min(CFG["grid"], self.y + (dy / dist) * flee_speed))
            return

        # Check inbox for useful signals.
        acted = False
        for sig in reversed(self.inbox):
            if sig.is_silence:
                continue
            if sig.target_id is not None and sig.target_id != self.id and not sig.is_player:
                continue
            trust = self.trust.get(sig.sender_id, 0.5)
            info = sig.info_value(self.best_known_fitness)
            if trust > 0.35 and info > CFG["info_threshold"]:
                dx = sig.position[0] - self.x
                dy = sig.position[1] - self.y
                step = 0.5 * trust
                if abs(dx) > 0.01:
                    self.x = max(0, min(CFG["grid"], self.x + math.copysign(step, dx)))
                if abs(dy) > 0.01:
                    self.y = max(0, min(CFG["grid"], self.y + math.copysign(step, dy)))
                acted = True
                break

        if not acted:
            old_f = self.fitness
            step = random.uniform(0.25, 0.8)
            dirs = [(step, 0, "+x"), (-step, 0, "-x"), (0, step, "+y"), (0, -step, "-y")]
            random.shuffle(dirs)
            dx, dy, label = dirs[0]
            nx = max(0, min(CFG["grid"], self.x + dx))
            ny = max(0, min(CFG["grid"], self.y + dy))
            nf = landscape_fitness(nx, ny, noisy=False)
            if nf >= old_f * 0.75:
                self.x, self.y = nx, ny
                if nf > old_f:
                    self.last_gradient = label

    def decide_speak(self, neighbors: List["Mote"], tick: int) -> Tuple[Optional[Signal], Optional[SilenceDecision]]:
        """
        Speak / direct / whisper / chosen-silence.
        Silence tracked as DECISION with reason logged.
        Returns (Signal | None, SilenceDecision | None).
        """
        self.silence_reason = None

        # Predator silence.
        if self.nearest_predator_dist < 1.8:
            self.times_silent_predator += 1
            self.silence_reason = "predator"
            return None, SilenceDecision(
                tick=tick,
                mote_id=self.id,
                reason="predator",
                energy=self.energy,
                fitness=self.fitness,
                predator_distance=self.nearest_predator_dist,
                neighbors=len(neighbors),
                context="mote",
            )

        if self.energy < 20.0:
            self.times_silent_chosen += 1
            self.silence_reason = "energy"
            return None, SilenceDecision(
                tick=tick,
                mote_id=self.id,
                reason="energy",
                energy=self.energy,
                fitness=self.fitness,
                predator_distance=self.nearest_predator_dist,
                neighbors=len(neighbors),
                context="mote",
            )

        if not neighbors:
            self.times_silent_alone += 1
            self.silence_reason = "alone"
            return None, SilenceDecision(
                tick=tick,
                mote_id=self.id,
                reason="alone",
                energy=self.energy,
                fitness=self.fitness,
                predator_distance=self.nearest_predator_dist,
                neighbors=0,
                context="mote",
            )

        # Information asymmetry check.
        best_delta = 0.0
        neediest: Optional[Mote] = None
        for n in neighbors:
            their_known = self.known_peers.get(n.id, 0.0)
            delta = self.best_known_fitness - their_known
            if delta > best_delta:
                best_delta = delta
                neediest = n

        # Chosen silence: nothing worth saying.
        if best_delta < self.speaking_threshold:
            self.times_silent_chosen += 1
            self.silence_reason = "no_info"
            self.energy += CFG["silence_bonus"]
            return None, SilenceDecision(
                tick=tick,
                mote_id=self.id,
                reason="no_info",
                energy=self.energy,
                fitness=self.fitness,
                predator_distance=self.nearest_predator_dist,
                neighbors=len(neighbors),
                info_delta=best_delta,
                context="mote",
            )

        # Whisper if predator nearby (short range, lower cost).
        if self.nearest_predator_dist < 3.0:
            self.energy -= CFG["direct_cost"] * 0.4
            self.times_spoke += 1
            self.times_directed += 1
            return Signal(
                sender_id=self.id,
                target_id=neediest.id if neediest else None,
                position=list(self.best_known_pos),
                fitness=self.best_known_fitness,
                energy=self.energy,
                gradient=self.last_gradient,
                tick=tick,
                is_broadcast=False,
            ), None

        # Directed vs broadcast.
        if neediest and self.broadcast_bias < 0.55:
            self.energy -= CFG["direct_cost"]
            self.times_spoke += 1
            self.times_directed += 1
            return Signal(
                sender_id=self.id,
                target_id=neediest.id,
                position=list(self.best_known_pos),
                fitness=self.best_known_fitness,
                energy=self.energy,
                gradient=self.last_gradient,
                tick=tick,
                is_broadcast=False,
            ), None

        self.energy -= CFG["speak_cost"]
        self.times_spoke += 1
        self.times_broadcast += 1
        return Signal(
            sender_id=self.id,
            target_id=None,
            position=list(self.best_known_pos),
            fitness=self.best_known_fitness,
            energy=self.energy,
            gradient=self.last_gradient,
            tick=tick,
            is_broadcast=True,
        ), None

    def update_peer(self, sig: Signal, append: bool = True):
        if sig.is_silence:
            return
        self.known_peers[sig.sender_id] = sig.fitness
        if sig.sender_id not in self.trust:
            self.trust[sig.sender_id] = 0.5
        # Trust rises if signal information was locally plausible.
        if sig.fitness > self.fitness * 0.85:
            self.trust[sig.sender_id] = min(1.0, self.trust.get(sig.sender_id, 0.5) + 0.08)
        else:
            self.trust[sig.sender_id] = max(0.0, self.trust.get(sig.sender_id, 0.5) - 0.02)
        if append:
            self.inbox.append(sig)

    def thermodynamics(self):
        reward = self.fitness * CFG["fitness_scale"]
        self.energy += reward - CFG["base_decay"]
        self.age += 1
        for sid in list(self.trust):
            self.trust[sid] *= CFG["trust_decay"]
        if self.energy <= CFG["death_thresh"]:
            self.alive = False

    def reproduce(self) -> "Mote":
        self.energy /= 2
        child = Mote(
            max(0, min(CFG["grid"], self.x + random.gauss(0, 0.4))),
            max(0, min(CFG["grid"], self.y + random.gauss(0, 0.4))),
            self.energy,
            self.id,
        )
        child.speaking_threshold = max(0.2, self.speaking_threshold + random.gauss(0, 0.25))
        child.broadcast_bias = max(0.0, min(1.0, self.broadcast_bias + random.gauss(0, 0.08)))
        return child


# ─── SWARM STATE ─────────────────────────────────────────────────────────────

class SwarmState:
    def __init__(self):
        self.motes: List[Mote] = []
        self.predators: List[Predator] = []
        self.tick = 0
        self.lock = threading.RLock()
        self.signal_log: List[dict] = []        # recent signals for SSE
        self.silence_log: List[dict] = []       # recent silence decisions for SSE / diagnostics
        self.conversation_log: List[dict] = []  # mote voices for conversation panel
        self.player = {
            "x": 4.0,
            "y": 4.0,
            "fitness": 0.0,
            "last_signal": None,
        }
        self.running = False
        self.pending_player_signals: List[dict] = []  # injected by REST endpoint

        # Spawn initial population.
        Mote._id = 0
        Predator._id = 0
        for _ in range(CFG["population"]):
            m = Mote(random.uniform(0, CFG["grid"]), random.uniform(0, CFG["grid"]), CFG["initial_energy"])
            self.motes.append(m)

        # Start predators in corners, away from initial population as much as possible.
        corners = [(0.5, 0.5), (CFG["grid"] - 0.5, 0.5), (0.5, CFG["grid"] - 0.5), (CFG["grid"] - 0.5, CFG["grid"] - 0.5)]
        for i in range(CFG["predator_count"]):
            p = Predator()
            p.x, p.y = corners[i % len(corners)]
            p.target_x, p.target_y = p.x, p.y
            self.predators.append(p)

    def get_neighbors(self, mote: Mote, extra_range: float = 0.0) -> List[Mote]:
        result: List[Mote] = []
        for other in self.motes:
            if other.id == mote.id or not other.is_alive():
                continue
            d = math.sqrt((other.x - mote.x) ** 2 + (other.y - mote.y) ** 2)
            if d <= CFG["signal_range"] + extra_range:
                result.append(other)
        return result

    def player_neighbors(self) -> List[Tuple[Mote, float]]:
        px, py = self.player["x"], self.player["y"]
        result: List[Tuple[Mote, float]] = []
        for m in self.motes:
            if not m.is_alive():
                continue
            d = math.sqrt((m.x - px) ** 2 + (m.y - py) ** 2)
            if d <= CFG["player_range"]:
                result.append((m, d))
        result.sort(key=lambda x: x[1])
        return result

    def _voice_record(self, mote: Mote, text: Optional[str], msg_type: str, tick: int, silence_reason: Optional[str] = None) -> dict:
        return {
            "mote_id": mote.id,
            "text": text,
            "energy": round(mote.energy, 1),
            "fitness": round(mote.fitness, 2),
            "x": round(mote.x, 2),
            "y": round(mote.y, 2),
            "type": msg_type,
            "silence_reason": silence_reason,
            "tick": tick,
        }

    def tick_step(self) -> List[dict]:
        self.tick += 1
        tick_signals: List[Signal] = []
        tick_silences: List[SilenceDecision] = []
        new_voices: List[dict] = []

        # Process pending player signals.
        with self.lock:
            player_sigs = list(self.pending_player_signals)
            self.pending_player_signals = []

        # Update player fitness.
        px, py = self.player["x"], self.player["y"]
        pf = landscape_fitness(px, py, noisy=False)
        self.player["fitness"] = round(pf, 2)

        # Phase 1: Sense and update predator proximity before speech decisions.
        for m in self.motes:
            if not m.is_alive():
                continue
            m.sense()
            m.nearest_predator_dist = min((p.dist_to(m.x, m.y) for p in self.predators), default=99.0)

        # Phase 2: Deliver player signals to nearby motes.
        for psig in player_sigs:
            self.player["last_signal"] = psig
            for m in self.motes:
                if not m.is_alive():
                    continue
                d = math.sqrt((m.x - psig["position"][0]) ** 2 + (m.y - psig["position"][1]) ** 2)
                if d <= CFG["player_range"]:
                    sig = Signal(
                        sender_id=-1,
                        target_id=m.id,
                        position=list(psig["position"]),
                        fitness=psig["fitness"],
                        energy=999.0,
                        gradient=None,
                        tick=self.tick,
                        is_player=True,
                    )
                    m.inbox.append(sig)
                    m.known_peers[-1] = psig["fitness"]

                    # Mote decides whether to respond to player.
                    resp = response_to_player(m, psig, self.predators)
                    if resp:
                        new_voices.append(self._voice_record(m, resp, "response", self.tick, None))
                    else:
                        # Report silence with reason.
                        reason = "predator" if m.nearest_predator_dist < 1.8 else "fear"
                        sd = SilenceDecision(
                            tick=self.tick,
                            mote_id=m.id,
                            reason=reason,
                            energy=m.energy,
                            fitness=m.fitness,
                            predator_distance=m.nearest_predator_dist,
                            neighbors=0,
                            context="player_response",
                        )
                        tick_silences.append(sd)
                        new_voices.append(self._voice_record(m, None, "silence", self.tick, reason))

        # Phase 3: Mote-to-mote communication.
        for m in self.motes:
            if not m.is_alive():
                continue
            neighbors = self.get_neighbors(m)

            # Read remembered inbox entries into peer model without duplicating them.
            for sig in list(m.inbox):
                m.update_peer(sig, append=False)

            sig, silence = m.decide_speak(neighbors, self.tick)
            if silence:
                tick_silences.append(silence)

            if sig:
                tick_signals.append(sig)
                for n in neighbors:
                    if sig.target_id is None or sig.target_id == n.id:
                        n.update_peer(sig, append=True)

                # Ambient voice: motes near player might speak into conversation.
                md = math.sqrt((m.x - px) ** 2 + (m.y - py) ** 2)
                if md <= CFG["player_range"] * 1.2 and random.random() < 0.35:
                    voice = compose_mote_voice(m)
                    if voice:
                        new_voices.append(self._voice_record(m, voice, "ambient", self.tick, None))
                    elif m.silence_reason:
                        new_voices.append(self._voice_record(m, None, "silence", self.tick, m.silence_reason))

        # Phase 4: Predators hunt.
        for pred in self.predators:
            pred.update(tick_signals, self.motes, self.tick)

        # Phase 5: Explore.
        for m in self.motes:
            if m.is_alive():
                m.explore(self.predators)

        # Phase 6: Thermodynamics + survival + reproduction.
        survivors: List[Mote] = []
        children: List[Mote] = []
        for m in self.motes:
            if not m.is_alive():
                continue
            m.thermodynamics()
            if not m.is_alive():
                continue
            if m.energy >= CFG["mitosis_thresh"] and len(survivors) + len(children) < CFG["max_population"]:
                child = m.reproduce()
                children.append(child)
                new_voices.append({
                    "mote_id": child.id,
                    "text": random.choice(["Born.", "Here.", "New."]),
                    "energy": round(child.energy, 1),
                    "fitness": 0.0,
                    "x": round(child.x, 2),
                    "y": round(child.y, 2),
                    "type": "birth",
                    "silence_reason": None,
                    "tick": self.tick,
                })
            survivors.append(m)

        self.motes = survivors + children

        with self.lock:
            self.signal_log = [asdict(s) for s in tick_signals[-30:]]
            self.silence_log = (self.silence_log + [asdict(s) for s in tick_silences])[-500:]
            self.conversation_log = (self.conversation_log + new_voices)[-200:]

        return new_voices

    def get_state_snapshot(self) -> dict:
        """Full state for SSE broadcast."""
        with self.lock:
            motes_data = [
                {
                    "id": m.id,
                    "x": round(m.x, 2),
                    "y": round(m.y, 2),
                    "energy": round(m.energy, 1),
                    "fitness": round(m.fitness, 2),
                    "age": m.age,
                    "spoke": m.times_spoke,
                    "silent": m.times_silent_chosen,
                    "silent_pred": m.times_silent_predator,
                    "silent_alone": m.times_silent_alone,
                    "directed": m.times_directed,
                    "broadcast": m.times_broadcast,
                    "threshold": round(m.speaking_threshold, 2),
                    "bias": round(m.broadcast_bias, 2),
                    "pred_dist": round(m.nearest_predator_dist, 2),
                }
                for m in self.motes
                if m.is_alive()
            ]

            pred_data = [
                {
                    "id": p.id,
                    "x": round(p.x, 2),
                    "y": round(p.y, 2),
                    "target_x": round(p.target_x, 2),
                    "target_y": round(p.target_y, 2),
                    "signals_followed": p.signals_followed,
                    "damage_dealt": round(p.damage_dealt, 1),
                }
                for p in self.predators
            ]

            voices = list(self.conversation_log)
            silence = list(self.silence_log)
            signals = list(self.signal_log)

        total_spoke = sum(m["spoke"] for m in motes_data)
        total_directed = sum(m["directed"] for m in motes_data)
        total_broadcast = sum(m["broadcast"] for m in motes_data)
        total_silent = sum(m["silent"] for m in motes_data)
        total_fear = sum(m["silent_pred"] for m in motes_data)

        return {
            "tick": self.tick,
            "motes": motes_data,
            "predators": pred_data,
            "player": dict(self.player),
            "voices": voices[-40:],
            "signals": signals,
            "silence": silence[-80:],
            "population": len(motes_data),
            "stats": {
                "spoke": total_spoke,
                "directed": total_directed,
                "broadcast": total_broadcast,
                "silent": total_silent,
                "fear_silence": total_fear,
                "directed_ratio": round(total_directed / max(1, total_spoke), 3),
            },
            "peaks": [{"x": p[0], "y": p[1], "s": s} for p, s in zip(CFG["peak_positions"], CFG["peak_strengths"])],
        }


# ─── GLOBAL SWARM ────────────────────────────────────────────────────────────

swarm = SwarmState()


def run_swarm():
    swarm.running = True
    while swarm.running:
        try:
            swarm.tick_step()
        except Exception as exc:  # keep the background loop from dying silently
            print(f"[swarm error] {exc}")
        time.sleep(1.0 / CFG["ticks_per_sec"])


swarm_thread = threading.Thread(target=run_swarm, daemon=True)
swarm_thread.start()


# ─── SSE ENDPOINT ────────────────────────────────────────────────────────────

@app.route("/stream")
def stream():
    def generate():
        last_tick = -1
        while True:
            if swarm.tick != last_tick:
                last_tick = swarm.tick
                data = swarm.get_state_snapshot()
                yield f"data: {json.dumps(data)}\n\n"
            time.sleep(0.1)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─── REST ENDPOINTS ───────────────────────────────────────────────────────────

@app.route("/player/move", methods=["POST"])
def player_move():
    data = request.json or {}
    with swarm.lock:
        swarm.player["x"] = max(0, min(CFG["grid"], float(data.get("x", 4))))
        swarm.player["y"] = max(0, min(CFG["grid"], float(data.get("y", 4))))
        player = dict(swarm.player)
    return jsonify({"ok": True, "player": player})


@app.route("/player/speak", methods=["POST"])
def player_speak():
    """
    Inject a signal from the player into the swarm.
    Player claims a position and fitness value.
    Motes in range respond based on their state.
    """
    data = request.json or {}
    with swarm.lock:
        px, py = swarm.player["x"], swarm.player["y"]
        current_fitness = swarm.player["fitness"]

    sig = {
        "position": [
            max(0, min(CFG["grid"], float(data.get("x", px)))),
            max(0, min(CFG["grid"], float(data.get("y", py)))),
        ],
        "fitness": float(data.get("fitness", current_fitness)),
        "message": data.get("message", ""),
    }

    with swarm.lock:
        swarm.pending_player_signals.append(sig)

    # Immediate nearby motes snapshot for fast response.
    nearby = swarm.player_neighbors()
    return jsonify({"ok": True, "nearby_count": len(nearby), "signal": sig})


@app.route("/player/listen", methods=["GET"])
def player_listen():
    """Get all recent voices from motes near the player."""
    nearby_pairs = swarm.player_neighbors()
    nearby = [m for m, _d in nearby_pairs]
    nearby_ids = {m.id for m in nearby}
    with swarm.lock:
        relevant = [v for v in swarm.conversation_log if v["mote_id"] in nearby_ids]
    return jsonify({"voices": relevant[-20:], "count": len(relevant)})


@app.route("/state")
def state():
    return jsonify(swarm.get_state_snapshot())


@app.route("/reset", methods=["POST"])
def reset():
    global swarm
    old = swarm
    old.running = False
    time.sleep(0.2)
    swarm = SwarmState()
    t = threading.Thread(target=run_swarm, daemon=True)
    t.start()
    return jsonify({"ok": True})


@app.route("/config")
def get_config():
    return jsonify(CFG)


@app.route("/health")
def health():
    return jsonify({"ok": True, "tick": swarm.tick, "population": len(swarm.motes)})


if __name__ == "__main__":
    print("TAIS-LANG Swarm Server starting on http://localhost:5123")
    print(f"Population: {CFG['population']} | Predators: {CFG['predator_count']}")
    print(f"Peaks: {CFG['peak_positions']}")
    print("Endpoints: /stream (SSE) | /player/move | /player/speak | /player/listen | /state | /reset")
    app.run(host="0.0.0.0", port=5123, debug=False, threaded=True)
