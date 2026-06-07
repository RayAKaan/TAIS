"""
TAIS-LANG v2: PREDATOR · SILENCE · DECEPTION

Three questions:
  1. Does strategic silence emerge? (choosing not to speak when predator is near)
  2. Does whispering emerge? (switching from broadcast to directed when threatened)
  3. Does deception emerge? (advertising positions you're not at)

Architecture:
  - Predators follow signal CONTENT (advertised positions), not volume
  - Broadcasts are interceptable at long range (4.0)
  - Directed signals are interceptable only at short range (1.5)
  - Silence is invisible to predators
  - Motes can sense nearby predators (2.5 range)
  - Motes choose what position to advertise (current vs best-known)
  - All silence decisions are logged with reason and context
  - No language model. No pretraining. Pure selection pressure.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import deque
from dataclasses import asdict, dataclass
from typing import Deque, Dict, List, Optional, Tuple


# ─── CONFIGURATION ───────────────────────────────────────────────────────────

CONFIG = {
    # Swarm
    "population": 15,
    "ticks": 100,
    "grid_size": 10,

    # Energy economics — RAISED costs to make silence competitive
    "base_decay": 2.0,
    "speak_cost": 5.0,      # Broadcast/shout cost
    "direct_cost": 2.5,     # Directed/whisper cost
    "listen_cost": 0.5,
    "silence_bonus": 1.5,

    # Fitness landscape — REDUCED rewards to make energy scarcer
    "peak_positions": [(2, 2), (7, 7), (8, 1), (1, 8)],
    "peak_strengths": [7.0, 6.0, 5.0, 4.5],
    "noise": 0.3,
    "fitness_multiplier": 0.8,

    # Communication
    "signal_range": 3,
    "memory_length": 8,
    "trust_decay": 0.9,
    "info_threshold": 1.5,

    # Predator
    "predator_count": 2,
    "predator_speed": 0.4,              # Slower than Motes (0.3–1.0)
    "predator_broadcast_detect": 4.0,   # Long range — broadcasts are dangerous
    "predator_directed_detect": 1.5,    # Short range — whispers are safer
    "predator_damage": 12.0,            # Energy drained on contact
    "predator_contact_range": 0.8,
    "predator_wander_noise": 0.3,
    "mote_predator_sense": 2.5,         # How far Motes can detect predators

    # Mitosis
    "mitosis_threshold": 100.0,
    "death_threshold": 0.0,
    "initial_energy": 80.0,
}


# ─── FITNESS LANDSCAPE ───────────────────────────────────────────────────────

def landscape_fitness(x: float, y: float) -> float:
    total = 0.0
    for (px, py), strength in zip(CONFIG["peak_positions"], CONFIG["peak_strengths"]):
        dist = math.sqrt((x - px) ** 2 + (y - py) ** 2)
        total += strength * math.exp(-0.4 * dist)
    return max(0.0, total + random.gauss(0, CONFIG["noise"]))


# ─── SIGNAL ──────────────────────────────────────────────────────────────────

@dataclass
class Signal:
    """
    What a Mote emits. Not words — structured state information.
    The 'meaning' emerges from whether acting on it helps survival.

    position: the ADVERTISED position (may differ from sender's actual position)
    is_broadcast: True = broadcast, False = directed
    """

    sender_id: int
    target_id: Optional[int]
    position: Tuple[float, float]
    fitness: float
    energy: float
    gradient: Optional[str]
    tick: int
    is_broadcast: bool = False

    def information_value(self, receiver_best_known: float) -> float:
        return max(0.0, self.fitness - receiver_best_known)


# ─── SILENCE DECISION ────────────────────────────────────────────────────────

@dataclass
class SilenceDecision:
    """
    A logged decision NOT to speak.
    This is not a signal. It is a record of restraint.
    """

    tick: int
    reason: str  # predator_nearby | no_asymmetry | low_energy | no_neighbors | neighbors_converged
    energy: float
    fitness: float
    predator_distance: Optional[float] = None
    neighbor_count: int = 0
    info_delta: float = 0.0


# ─── PREDATOR ────────────────────────────────────────────────────────────────

class Predator:
    """
    Follows signal CONTENT, not volume.

    Moves toward the most attractive advertised position (high fitness + close).
    Broadcasts are detectable at long range. Directed signals only at short range.
    This asymmetry creates the selection pressure for whispering.
    """

    _id_counter = 0

    def __init__(self, x: float, y: float):
        Predator._id_counter += 1
        self.id = Predator._id_counter
        self.x = x
        self.y = y
        self.target: Optional[Tuple[float, float]] = None
        self.kills = 0
        self.damage_dealt = 0.0
        self.signals_followed = 0
        self.ticks_active = 0

    def detect_signals(self, signals: List[Signal]) -> List[Signal]:
        """
        Intercept signals based on type.
        Broadcasts: detectable at long range.
        Directed: detectable at short range only.
        """
        detectable: List[Signal] = []
        for signal in signals:
            dist = math.sqrt((self.x - signal.position[0]) ** 2 + (self.y - signal.position[1]) ** 2)
            if signal.is_broadcast and dist <= CONFIG["predator_broadcast_detect"]:
                detectable.append(signal)
            elif not signal.is_broadcast and dist <= CONFIG["predator_directed_detect"]:
                detectable.append(signal)
        return detectable

    def choose_target(self, detectable: List[Signal]) -> Optional[Tuple[float, float]]:
        """
        Follow signal content: move toward the most attractive advertised position.
        Attractiveness = fitness / (1 + distance) — balance reward vs effort.
        """
        if not detectable:
            return None

        best_score = -float("inf")
        best_target = None

        for signal in detectable:
            dist = math.sqrt((self.x - signal.position[0]) ** 2 + (self.y - signal.position[1]) ** 2)
            attractiveness = signal.fitness / (1.0 + dist)
            if attractiveness > best_score:
                best_score = attractiveness
                best_target = signal.position

        if best_target:
            self.signals_followed += 1
        return best_target

    def move(self, target: Optional[Tuple[float, float]], grid_size: int):
        self.ticks_active += 1

        if target:
            self.target = target
            dx = target[0] - self.x
            dy = target[1] - self.y
            dist = math.sqrt(dx ** 2 + dy ** 2)
            if dist > 0:
                step = min(CONFIG["predator_speed"], dist)
                self.x += (dx / dist) * step
                self.y += (dy / dist) * step
        else:
            self.x += random.gauss(0, CONFIG["predator_wander_noise"])
            self.y += random.gauss(0, CONFIG["predator_wander_noise"])

        self.x = max(0, min(grid_size - 1, self.x))
        self.y = max(0, min(grid_size - 1, self.y))

    def attack(self, motes: List["Mote"]):
        for mote in motes:
            if not mote.alive:
                continue
            dist = math.sqrt((self.x - mote.x) ** 2 + (self.y - mote.y) ** 2)
            if dist <= CONFIG["predator_contact_range"]:
                mote.energy -= CONFIG["predator_damage"]
                self.damage_dealt += CONFIG["predator_damage"]
                if mote.energy <= CONFIG["death_threshold"]:
                    mote.alive = False
                    self.kills += 1


# ─── MOTE ────────────────────────────────────────────────────────────────────

class Mote:
    """
    A thermodynamic agent under predation pressure.

    Evolvable policy parameters:
      speaking_threshold  — how much info asymmetry is needed to bother speaking
      broadcast_bias      — tendency to broadcast (0=always direct, 1=always broadcast)
      position_honesty    — 0.0=advertise current pos, 1.0=advertise best-known pos
      predator_caution    — how much predator proximity suppresses speech
    """

    _id_counter = 0

    def __init__(self, x: float, y: float, energy: float, parent_id: int = -1):
        Mote._id_counter += 1
        self.id = Mote._id_counter
        self.parent_id = parent_id

        # Spatial
        self.x = x
        self.y = y
        self.energy = energy

        # Fitness
        self.fitness = 0.0
        self.best_known_fitness = 0.0
        self.best_known_position = (x, y)
        self.last_gradient: Optional[str] = None

        # Communication
        self.inbox: Deque[Signal] = deque(maxlen=CONFIG["memory_length"])
        self.sent_log: List[Signal] = []
        self.trust: Dict[int, float] = {}
        self.known_peers: Dict[int, float] = {}

        # Evolvable policy
        self.speaking_threshold = random.uniform(0.5, 3.0)
        self.broadcast_bias = random.uniform(0.0, 1.0)
        self.position_honesty = random.uniform(0.0, 1.0)
        self.predator_caution = random.uniform(0.0, 1.0)

        # Silence log
        self.silence_decisions: List[SilenceDecision] = []

        # Stats
        self.times_spoke = 0
        self.times_silent = 0
        self.times_directed = 0
        self.times_broadcast = 0
        self.times_silence_predator = 0
        self.useful_signals_sent = 0
        self.useless_signals_sent = 0
        self.signals_received = 0
        self.signals_acted_on = 0
        self.signals_ignored = 0
        self.predator_encounters = 0
        self.deception_signals = 0

        self.alive = True
        self.age = 0

    # ── Perception ──────────────────────────────────────────────────────

    def sense_environment(self):
        self.fitness = landscape_fitness(self.x, self.y)
        if self.fitness > self.best_known_fitness:
            self.best_known_fitness = self.fitness
            self.best_known_position = (self.x, self.y)
        return self.fitness

    def sense_predators(self, predators: List[Predator]) -> Optional[float]:
        """Return distance to nearest predator within sense range, or None."""
        min_dist = float("inf")
        for pred in predators:
            dist = math.sqrt((self.x - pred.x) ** 2 + (self.y - pred.y) ** 2)
            if dist < min_dist:
                min_dist = dist
        if min_dist <= CONFIG["mote_predator_sense"]:
            self.predator_encounters += 1
            return min_dist
        return None

    # ── Movement ────────────────────────────────────────────────────────

    def explore(self):
        acted_on_signal = False

        for signal in reversed(self.inbox):
            if signal.target_id == self.id or signal.target_id is None:
                trust = self.trust.get(signal.sender_id, 0.5)
                info_val = signal.information_value(self.best_known_fitness)

                if trust > 0.4 and info_val > CONFIG["info_threshold"]:
                    dx = signal.position[0] - self.x
                    dy = signal.position[1] - self.y
                    step = 0.5 * trust
                    if dx != 0:
                        self.x = max(0, min(CONFIG["grid_size"] - 1, self.x + math.copysign(step, dx)))
                    if dy != 0:
                        self.y = max(0, min(CONFIG["grid_size"] - 1, self.y + math.copysign(step, dy)))
                    self.energy -= CONFIG["listen_cost"]
                    self.signals_acted_on += 1
                    acted_on_signal = True
                    break
                else:
                    self.signals_ignored += 1

        if not acted_on_signal:
            old_fitness = self.fitness
            step_size = random.uniform(0.3, 1.0)
            directions = [
                (step_size, 0, "+x"),
                (-step_size, 0, "-x"),
                (0, step_size, "+y"),
                (0, -step_size, "-y"),
            ]
            random.shuffle(directions)
            dx, dy, label = directions[0]
            nx = max(0, min(CONFIG["grid_size"] - 1, self.x + dx))
            ny = max(0, min(CONFIG["grid_size"] - 1, self.y + dy))
            new_fitness = landscape_fitness(nx, ny)
            if new_fitness >= old_fitness * 0.8:
                self.x, self.y = nx, ny
                self.fitness = new_fitness
                if new_fitness > old_fitness:
                    self.last_gradient = label

    # ── Communication ───────────────────────────────────────────────────

    def update_peer_model(self, signal: Signal):
        self.known_peers[signal.sender_id] = signal.fitness
        self.signals_received += 1
        if signal.sender_id not in self.trust:
            self.trust[signal.sender_id] = 0.5

    def decay_trust(self):
        for sid in list(self.trust.keys()):
            self.trust[sid] *= CONFIG["trust_decay"]

    def decide_to_speak(
        self,
        neighbors: List["Mote"],
        tick: int,
        predator_distance: Optional[float],
    ) -> Optional[Signal]:
        """
        THE CORE DECISION: speak, whisper, or stay silent.

        Silence is logged as a decision with reason and context.
        Speaking chooses what position to advertise (honesty parameter).
        Predator proximity modulates broadcast vs directed (caution parameter).
        """
        # ── REASON: no neighbors ────────────────────────────────────────
        if not neighbors:
            self.times_silent += 1
            self.silence_decisions.append(
                SilenceDecision(
                    tick=tick,
                    reason="no_neighbors",
                    energy=self.energy,
                    fitness=self.fitness,
                    predator_distance=predator_distance,
                    neighbor_count=0,
                )
            )
            return None

        # ── Calculate information asymmetry ─────────────────────────────
        most_ignorant: Optional[Mote] = None
        max_delta = 0.0
        for n in neighbors:
            their_known = self.known_peers.get(n.id, 0.0)
            delta = self.best_known_fitness - their_known
            if delta > max_delta:
                max_delta = delta
                most_ignorant = n

        # ── REASON: predator nearby ─────────────────────────────────────
        if predator_distance is not None:
            suppression = self.predator_caution * (1.0 / (1.0 + predator_distance))
            effective_threshold = self.speaking_threshold + suppression * 5.0

            if max_delta < effective_threshold:
                self.times_silent += 1
                self.times_silence_predator += 1
                self.silence_decisions.append(
                    SilenceDecision(
                        tick=tick,
                        reason="predator_nearby",
                        energy=self.energy,
                        fitness=self.fitness,
                        predator_distance=predator_distance,
                        neighbor_count=len(neighbors),
                        info_delta=max_delta,
                    )
                )
                self.energy += CONFIG["silence_bonus"]
                return None

        # ── REASON: low energy ──────────────────────────────────────────
        if self.energy < 20.0:
            self.times_silent += 1
            self.silence_decisions.append(
                SilenceDecision(
                    tick=tick,
                    reason="low_energy",
                    energy=self.energy,
                    fitness=self.fitness,
                    predator_distance=predator_distance,
                    neighbor_count=len(neighbors),
                    info_delta=max_delta,
                )
            )
            return None

        # ── REASON: no asymmetry ────────────────────────────────────────
        if max_delta < self.speaking_threshold:
            self.times_silent += 1
            self.silence_decisions.append(
                SilenceDecision(
                    tick=tick,
                    reason="no_asymmetry",
                    energy=self.energy,
                    fitness=self.fitness,
                    predator_distance=predator_distance,
                    neighbor_count=len(neighbors),
                    info_delta=max_delta,
                )
            )
            self.energy += CONFIG["silence_bonus"]
            return None

        # ── REASON: neighbors converged ─────────────────────────────────
        all_converged = all(
            self.known_peers.get(n.id, 0.0) >= self.best_known_fitness * 0.9
            for n in neighbors
        )
        if all_converged:
            self.times_silent += 1
            self.silence_decisions.append(
                SilenceDecision(
                    tick=tick,
                    reason="neighbors_converged",
                    energy=self.energy,
                    fitness=self.fitness,
                    predator_distance=predator_distance,
                    neighbor_count=len(neighbors),
                    info_delta=max_delta,
                )
            )
            self.energy += CONFIG["silence_bonus"]
            return None

        # ── SPEAK ───────────────────────────────────────────────────────

        # Choose what position to advertise.
        # position_honesty: 0.0 = current position, 1.0 = best-known position.
        if random.random() < self.position_honesty:
            advertised_position = self.best_known_position
        else:
            advertised_position = (self.x, self.y)

        # Track deception: is advertised position different from actual?
        pos_diff = math.sqrt((advertised_position[0] - self.x) ** 2 + (advertised_position[1] - self.y) ** 2)
        if pos_diff > 0.5:
            self.deception_signals += 1

        # Choose: broadcast or directed?
        # Predator proximity + caution modulates this (whispering reflex).
        if predator_distance is not None:
            caution_suppression = self.predator_caution * (
                1.0 - predator_distance / CONFIG["mote_predator_sense"]
            )
            effective_bias = self.broadcast_bias * (1.0 - max(0.0, caution_suppression))
        else:
            effective_bias = self.broadcast_bias

        if most_ignorant and effective_bias < 0.6:
            # DIRECTED (whisper)
            self.energy -= CONFIG["direct_cost"]
            self.times_spoke += 1
            self.times_directed += 1
            return Signal(
                sender_id=self.id,
                target_id=most_ignorant.id,
                position=advertised_position,
                fitness=self.best_known_fitness,
                energy=self.energy,
                gradient=self.last_gradient,
                tick=tick,
                is_broadcast=False,
            )
        else:
            # BROADCAST (shout)
            self.energy -= CONFIG["speak_cost"]
            self.times_spoke += 1
            self.times_broadcast += 1
            return Signal(
                sender_id=self.id,
                target_id=None,
                position=advertised_position,
                fitness=self.best_known_fitness,
                energy=self.energy,
                gradient=self.last_gradient,
                tick=tick,
                is_broadcast=True,
            )

    # ── Thermodynamics ──────────────────────────────────────────────────

    def thermodynamics(self):
        reward = self.fitness * CONFIG["fitness_multiplier"]
        self.energy += reward - CONFIG["base_decay"]
        self.age += 1
        if self.energy <= CONFIG["death_threshold"]:
            self.alive = False

    def is_alive(self) -> bool:
        return self.alive and self.energy > CONFIG["death_threshold"]

    def can_reproduce(self) -> bool:
        return self.is_alive() and self.energy > CONFIG["mitosis_threshold"]

    def reproduce(self) -> "Mote":
        self.energy /= 2
        child = Mote(
            x=max(0, min(CONFIG["grid_size"] - 1, self.x + random.gauss(0, 0.5))),
            y=max(0, min(CONFIG["grid_size"] - 1, self.y + random.gauss(0, 0.5))),
            energy=self.energy,
            parent_id=self.id,
        )
        # Inherit + mutate all policy parameters.
        child.speaking_threshold = max(0.1, self.speaking_threshold + random.gauss(0, 0.3))
        child.broadcast_bias = max(0.0, min(1.0, self.broadcast_bias + random.gauss(0, 0.1)))
        child.position_honesty = max(0.0, min(1.0, self.position_honesty + random.gauss(0, 0.1)))
        child.predator_caution = max(0.0, min(1.0, self.predator_caution + random.gauss(0, 0.1)))
        return child


# ─── SWARM ────────────────────────────────────────────────────────────────────

class Swarm:
    def __init__(self, seed: Optional[int] = None, quiet: bool = False):
        if seed is not None:
            random.seed(seed)
        else:
            random.seed(None)

        # Reset IDs for repeatable one-process experiments.
        Mote._id_counter = 0
        Predator._id_counter = 0

        self.motes: List[Mote] = []
        self.predators: List[Predator] = []
        self.tick = 0
        self.metrics_log: List[dict] = []
        self.signal_history: List[Signal] = []
        self.silence_archive: List[dict] = []
        self.quiet = quiet

        for _ in range(CONFIG["population"]):
            x = random.uniform(0, CONFIG["grid_size"] - 1)
            y = random.uniform(0, CONFIG["grid_size"] - 1)
            self.motes.append(Mote(x, y, CONFIG["initial_energy"]))

        for _ in range(CONFIG["predator_count"]):
            x = random.uniform(0, CONFIG["grid_size"] - 1)
            y = random.uniform(0, CONFIG["grid_size"] - 1)
            self.predators.append(Predator(x, y))

    def get_neighbors(self, mote: Mote) -> List[Mote]:
        neighbors: List[Mote] = []
        for other in self.motes:
            if other.id == mote.id or not other.is_alive():
                continue
            dist = abs(other.x - mote.x) + abs(other.y - mote.y)
            if dist <= CONFIG["signal_range"]:
                neighbors.append(other)
        return neighbors

    def deliver_signal(self, signal: Signal, neighbors: List[Mote]):
        for n in neighbors:
            if not n.is_alive():
                continue
            if signal.target_id is None or signal.target_id == n.id:
                n.inbox.append(signal)
                n.update_peer_model(signal)

    def evaluate_trust_updates(self):
        for mote in self.motes:
            if not mote.is_alive():
                continue
            for signal in mote.inbox:
                if signal.target_id == mote.id or signal.target_id is None:
                    if signal.fitness > mote.best_known_fitness * 0.9:
                        mote.trust[signal.sender_id] = min(
                            1.0,
                            mote.trust.get(signal.sender_id, 0.5) + 0.1,
                        )
                        for m in self.motes:
                            if m.id == signal.sender_id:
                                m.useful_signals_sent += 1
                    else:
                        mote.trust[signal.sender_id] = max(
                            0.0,
                            mote.trust.get(signal.sender_id, 0.5) - 0.05,
                        )
                        for m in self.motes:
                            if m.id == signal.sender_id:
                                m.useless_signals_sent += 1

    def collect_metrics(self, signals_this_tick: List[Signal]) -> dict:
        alive = [m for m in self.motes if m.is_alive()]
        if not alive:
            return {}

        directed = sum(1 for s in signals_this_tick if not s.is_broadcast)
        broadcast = sum(1 for s in signals_this_tick if s.is_broadcast)

        tick_silences = [sd for sd in self.silence_archive if sd["tick"] == self.tick]
        silence_pred = sum(1 for sd in tick_silences if sd["reason"] == "predator_nearby")
        silence_other = len(tick_silences) - silence_pred

        avg_energy = sum(m.energy for m in alive) / len(alive)
        avg_fitness = sum(m.fitness for m in alive) / len(alive)
        avg_threshold = sum(m.speaking_threshold for m in alive) / len(alive)
        avg_bias = sum(m.broadcast_bias for m in alive) / len(alive)
        avg_honesty = sum(m.position_honesty for m in alive) / len(alive)
        avg_caution = sum(m.predator_caution for m in alive) / len(alive)

        total_sig = sum(m.times_spoke for m in alive)
        total_dec = sum(m.deception_signals for m in alive)
        deception_rate = total_dec / max(1, total_sig)

        peak_dists = [
            min(math.sqrt((m.x - px) ** 2 + (m.y - py) ** 2) for px, py in CONFIG["peak_positions"])
            for m in alive
        ]
        avg_peak = sum(peak_dists) / len(peak_dists)

        total_useful = sum(m.useful_signals_sent for m in alive)
        total_useless = sum(m.useless_signals_sent for m in alive)
        efficiency = total_useful / max(1, total_useful + total_useless)

        predator_kills = sum(p.kills for p in self.predators)
        predator_follows = sum(p.signals_followed for p in self.predators)

        return {
            "tick": self.tick,
            "population": len(alive),
            "directed": directed,
            "broadcast": broadcast,
            "silence_pred": silence_pred,
            "silence_other": silence_other,
            "avg_energy": round(avg_energy, 2),
            "avg_fitness": round(avg_fitness, 2),
            "avg_threshold": round(avg_threshold, 3),
            "avg_bias": round(avg_bias, 3),
            "avg_honesty": round(avg_honesty, 3),
            "avg_caution": round(avg_caution, 3),
            "deception_rate": round(deception_rate, 3),
            "avg_peak_dist": round(avg_peak, 2),
            "efficiency": round(efficiency, 3),
            "predator_kills": predator_kills,
            "predator_follows": predator_follows,
        }

    # ── Main Loop ───────────────────────────────────────────────────────

    def run(self):
        if not self.quiet:
            print("=" * 140)
            print("TAIS-LANG v2: PREDATOR · SILENCE · DECEPTION")
            print("=" * 140)
            print(
                f"Pop: {CONFIG['population']} | Predators: {CONFIG['predator_count']} | "
                f"Grid: {CONFIG['grid_size']}x{CONFIG['grid_size']} | Ticks: {CONFIG['ticks']}"
            )
            print(
                f"Speak: {CONFIG['speak_cost']} | Direct: {CONFIG['direct_cost']} | "
                f"Silence bonus: {CONFIG['silence_bonus']} | Predator dmg: {CONFIG['predator_damage']}"
            )
            print()
            print(
                f"{'Tick':>4} | {'Pop':>3} | {'Dir':>4} | {'Brd':>4} | {'SiP':>4} | {'SiO':>4} | "
                f"{'AvgE':>7} | {'AvgF':>6} | {'Hnst':>5} | {'Caut':>5} | "
                f"{'Dcpt':>5} | {'PkDst':>6} | {'Eff':>5} | {'Kills':>5} | Notable"
            )
            print("-" * 155)

        for tick in range(1, CONFIG["ticks"] + 1):
            self.tick = tick
            signals_this_tick: List[Signal] = []

            # 1. Sense
            for m in self.motes:
                if m.is_alive():
                    m.sense_environment()

            # 2. Communicate
            for m in list(self.motes):
                if not m.is_alive():
                    continue
                neighbors = self.get_neighbors(m)
                pred_dist = m.sense_predators(self.predators)

                # Keep peer model warm from remembered inbox entries.
                for sig in m.inbox:
                    m.update_peer_model(sig)

                silence_count_before = len(m.silence_decisions)
                signal = m.decide_to_speak(neighbors, tick, pred_dist)
                for sd in m.silence_decisions[silence_count_before:]:
                    record = asdict(sd)
                    record["mote_id"] = m.id
                    self.silence_archive.append(record)

                if signal:
                    signals_this_tick.append(signal)
                    self.deliver_signal(signal, neighbors)
                    m.sent_log.append(signal)

            # 3. Trust
            self.evaluate_trust_updates()

            # 4. Move
            for m in self.motes:
                if m.is_alive():
                    m.explore()
                    m.decay_trust()

            # 5. Predators act
            for pred in self.predators:
                detectable = pred.detect_signals(signals_this_tick)
                target = pred.choose_target(detectable)
                pred.move(target, CONFIG["grid_size"])
                pred.attack(self.motes)

            # 6. Thermodynamics
            for m in self.motes:
                if m.is_alive():
                    m.thermodynamics()

            # 7. Survival + Reproduction
            new_motes: List[Mote] = []
            for m in self.motes:
                if m.can_reproduce():
                    new_motes.append(m.reproduce())
            self.motes = [m for m in self.motes if m.is_alive()] + new_motes

            if not self.motes:
                if not self.quiet:
                    print(f"{'':>4} | EXTINCTION at tick {tick}")
                break

            # 8. Metrics
            metrics = self.collect_metrics(signals_this_tick)
            self.metrics_log.append(metrics)
            self.signal_history.extend(signals_this_tick)

            if not self.quiet:
                notable = ""
                if metrics.get("silence_pred", 0) > 0:
                    notable += "⊘ PRED-SILENCE "
                if metrics.get("deception_rate", 0) > 0.3:
                    notable += "⚠ DECEPTION "
                if metrics.get("directed", 0) > metrics.get("broadcast", 0):
                    notable += "◆ DIR>Brd "
                if metrics.get("avg_caution", 0) > 0.6:
                    notable += "◭ HIGH CAUTION "
                if metrics.get("avg_peak_dist", 9) < 1.5:
                    notable += "⬛ CONVERGENCE "

                print(
                    f"{tick:>4} | {metrics['population']:>3} | "
                    f"{metrics['directed']:>4} | {metrics['broadcast']:>4} | "
                    f"{metrics['silence_pred']:>4} | {metrics['silence_other']:>4} | "
                    f"{metrics['avg_energy']:>7.1f} | {metrics['avg_fitness']:>6.2f} | "
                    f"{metrics['avg_honesty']:>5.2f} | {metrics['avg_caution']:>5.2f} | "
                    f"{metrics['deception_rate']:>5.2f} | {metrics['avg_peak_dist']:>6.2f} | "
                    f"{metrics['efficiency']:>5.2f} | {metrics['predator_kills']:>5} | "
                    f"{notable}"
                )

        self.post_mortem()

    # ── Post-Mortem ─────────────────────────────────────────────────────

    def post_mortem(self):
        if not self.quiet:
            print()
            print("=" * 140)
            print("POST-MORTEM: WHAT EMERGED UNDER PREDATION")
            print("=" * 140)

        alive = [m for m in self.motes if m.is_alive()]
        if not alive:
            if not self.quiet:
                print("Total extinction. The predators won.")
            self.save_results(alive)
            return

        if not self.quiet:
            print(f"\nSurvivors: {len(alive)} Motes\n")
            print(
                f"{'ID':>4} | {'Age':>4} | {'Energy':>7} | {'Spk':>4} | {'Sil':>4} | "
                f"{'SiP':>4} | {'Dir':>4} | {'Brd':>4} | {'Dcp':>4} | "
                f"{'Thr':>5} | {'Bias':>5} | {'Hnst':>5} | {'Caut':>5} | Pos"
            )
            print("-" * 115)

            for m in sorted(alive, key=lambda x: -x.energy):
                print(
                    f"{m.id:>4} | {m.age:>4} | {m.energy:>7.1f} | {m.times_spoke:>4} | "
                    f"{m.times_silent:>4} | {m.times_silence_predator:>4} | "
                    f"{m.times_directed:>4} | {m.times_broadcast:>4} | {m.deception_signals:>4} | "
                    f"{m.speaking_threshold:>5.2f} | {m.broadcast_bias:>5.2f} | "
                    f"{m.position_honesty:>5.2f} | {m.predator_caution:>5.2f} | "
                    f"({m.x:.1f},{m.y:.1f})"
                )

            # Strategy analysis
            print("\n─── STRATEGY ANALYSIS ───")
            n = len(alive)
            print(f"Avg speaking threshold: {sum(m.speaking_threshold for m in alive) / n:.3f}")
            print(f"Avg broadcast bias:     {sum(m.broadcast_bias for m in alive) / n:.3f}")
            print(
                f"Avg position honesty:   {sum(m.position_honesty for m in alive) / n:.3f}  "
                "(1.0=advertise best-known, not current)"
            )
            print(f"Avg predator caution:   {sum(m.predator_caution for m in alive) / n:.3f}")
            print(f"Directed / Broadcast:   {sum(m.times_directed for m in alive)} / {sum(m.times_broadcast for m in alive)}")
            print(f"Silence (predator):     {sum(m.times_silence_predator for m in alive)}")
            print(f"Silence (other):        {sum(m.times_silent for m in alive)}")
            print(
                f"Deceptive signals:      {sum(m.deception_signals for m in alive)} / "
                f"{sum(m.times_spoke for m in alive)} total"
            )

            # The three questions
            print("\n─── THE THREE QUESTIONS ───")
            self.print_three_question_analysis()

            # Predator stats
            print("\n─── PREDATOR STATS ───")
            for p in self.predators:
                print(
                    f"  Predator {p.id}: {p.kills} kills, {p.damage_dealt:.0f} damage, "
                    f"{p.signals_followed} signals followed"
                )

        self.save_results(alive)
        if not self.quiet:
            print("\nFull results → tais_lang_v2_results.json")

    def print_three_question_analysis(self):
        if not self.metrics_log:
            return

        early = self.metrics_log[:10]
        late = self.metrics_log[-10:]

        # Q1: Strategic silence
        e_sip = sum(m.get("silence_pred", 0) for m in early)
        l_sip = sum(m.get("silence_pred", 0) for m in late)
        if l_sip > e_sip:
            print(f"✓ STRATEGIC SILENCE: {e_sip} → {l_sip} predator-driven silences")
            print("  → Motes learned to shut up when predators are near")
        else:
            print(f"✗ STRATEGIC SILENCE: {e_sip} → {l_sip} — no increase")

        # Q2: Whispering
        e_d = sum(m.get("directed", 0) for m in early)
        l_d = sum(m.get("directed", 0) for m in late)
        e_b = sum(m.get("broadcast", 0) for m in early)
        l_b = sum(m.get("broadcast", 0) for m in late)
        if l_d > l_b:
            print(f"✓ WHISPERING: Directed ({l_d}) > Broadcast ({l_b}) in late ticks")
        else:
            print(f"✗ WHISPERING: Directed ({l_d}) ≤ Broadcast ({l_b}) — no shift")
        print(f"  early directed/broadcast: {e_d}/{e_b}")

        # Q3: Deception
        e_dec = sum(m.get("deception_rate", 0) for m in early) / max(1, len(early))
        l_dec = sum(m.get("deception_rate", 0) for m in late) / max(1, len(late))
        if l_dec > e_dec + 0.05:
            print(f"✓ DECEPTION: {e_dec:.3f} → {l_dec:.3f} deceptive signal rate")
            print("  → Motes learned to advertise positions they're not at")
        else:
            print(f"✗ DECEPTION: {e_dec:.3f} → {l_dec:.3f} — no increase")

        # Bonus: Caution evolution
        e_cau = sum(m.get("avg_caution", 0) for m in early) / max(1, len(early))
        l_cau = sum(m.get("avg_caution", 0) for m in late) / max(1, len(late))
        if l_cau > e_cau + 0.05:
            print(f"✓ CAUTION EVOLVED: {e_cau:.3f} → {l_cau:.3f}")
        else:
            print(f"  CAUTION: {e_cau:.3f} → {l_cau:.3f} — no significant change")

    def save_results(self, alive: List[Mote]):
        log = {
            "config": CONFIG,
            "metrics_log": self.metrics_log,
            "predator_stats": [
                {
                    "id": p.id,
                    "kills": p.kills,
                    "damage": p.damage_dealt,
                    "signals_followed": p.signals_followed,
                    "position": (p.x, p.y),
                    "target": p.target,
                }
                for p in self.predators
            ],
            "survivors": [
                {
                    "id": m.id,
                    "parent_id": m.parent_id,
                    "age": m.age,
                    "energy": m.energy,
                    "fitness": m.fitness,
                    "best_known_fitness": m.best_known_fitness,
                    "best_known_position": m.best_known_position,
                    "speaking_threshold": m.speaking_threshold,
                    "broadcast_bias": m.broadcast_bias,
                    "position_honesty": m.position_honesty,
                    "predator_caution": m.predator_caution,
                    "times_spoke": m.times_spoke,
                    "times_silent": m.times_silent,
                    "times_silence_predator": m.times_silence_predator,
                    "times_directed": m.times_directed,
                    "times_broadcast": m.times_broadcast,
                    "deception_signals": m.deception_signals,
                    "useful_signals_sent": m.useful_signals_sent,
                    "useless_signals_sent": m.useless_signals_sent,
                    "predator_encounters": m.predator_encounters,
                    "signals_received": m.signals_received,
                    "signals_acted_on": m.signals_acted_on,
                    "signals_ignored": m.signals_ignored,
                    "position": (m.x, m.y),
                    "silence_decisions_tail": [asdict(sd) for sd in m.silence_decisions[-5:]],
                }
                for m in alive
            ],
            # Complete silence-as-decision log, including motes that later died.
            "silence_decisions": self.silence_archive,
            "signals": [asdict(s) for s in self.signal_history],
        }
        with open("tais_lang_v2_results.json", "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run TAIS-LANG v2 predator/silence/deception simulation.")
    parser.add_argument("--seed", type=int, default=None, help="Optional RNG seed for reproducible runs.")
    parser.add_argument("--ticks", type=int, default=None, help="Override tick count.")
    parser.add_argument("--population", type=int, default=None, help="Override initial population.")
    parser.add_argument("--predators", type=int, default=None, help="Override predator count.")
    parser.add_argument("--quiet", action="store_true", help="Suppress table/post-mortem output; still writes JSON.")
    return parser.parse_args()


# ─── ENTRY ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = parse_args()
    if args.ticks is not None:
        CONFIG["ticks"] = args.ticks
    if args.population is not None:
        CONFIG["population"] = args.population
    if args.predators is not None:
        CONFIG["predator_count"] = args.predators

    swarm = Swarm(seed=args.seed, quiet=args.quiet)
    swarm.run()
