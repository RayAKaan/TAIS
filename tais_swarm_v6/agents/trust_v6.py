"""
Vector trust and reputation system for TAIS Swarm V6.
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict

from ..engine.config import CommunicationConfig


@dataclass
class TrustVector:
    peer_id: int
    concept_trust: Dict[str, float] = field(default_factory=lambda: defaultdict(lambda: 0.5))
    action_trust: Dict[str, float] = field(default_factory=lambda: defaultdict(lambda: 0.5))
    global_trust: float = 0.5
    interactions: int = 0
    successful_interactions: int = 0
    last_interaction_tick: int = 0

    def get_concept_trust(self, concept: str) -> float:
        return self.concept_trust.get(concept, 0.5)

    def get_action_trust(self, action: str) -> float:
        return self.action_trust.get(action, 0.5)

    def update_concept(self, concept: str, outcome: str, tick: int):
        current = self.concept_trust[concept]
        if outcome == "positive":
            self.concept_trust[concept] = min(1.0, current + 0.08)
        elif outcome == "negative":
            self.concept_trust[concept] = max(0.0, current - 0.12)
        else:
            self.concept_trust[concept] = current * 0.99
        self.interactions += 1
        if outcome == "positive":
            self.successful_interactions += 1
        self.last_interaction_tick = tick
        self._update_global()

    def update_action(self, action: str, outcome: str, tick: int):
        current = self.action_trust[action]
        if outcome == "positive":
            self.action_trust[action] = min(1.0, current + 0.06)
        elif outcome == "negative":
            self.action_trust[action] = max(0.0, current - 0.10)
        self.last_interaction_tick = tick

    def _update_global(self):
        if not self.concept_trust:
            return
        avg = sum(self.concept_trust.values()) / len(self.concept_trust)
        self.global_trust = 0.7 * avg + 0.3 * self.global_trust
        self.global_trust = max(0.0, min(1.0, self.global_trust))

    def decay(self, tick: int, decay_rate: float = 0.94):
        ticks_since = tick - self.last_interaction_tick
        if ticks_since > 50:
            factor = decay_rate ** (ticks_since / 50)
            for concept in self.concept_trust:
                self.concept_trust[concept] = 0.5 + (self.concept_trust[concept] - 0.5) * factor
            for action in self.action_trust:
                self.action_trust[action] = 0.5 + (self.action_trust[action] - 0.5) * factor
            self.global_trust = 0.5 + (self.global_trust - 0.5) * factor

    def to_dict(self) -> dict:
        return {
            "peer_id": self.peer_id,
            "concept_trust": dict(self.concept_trust),
            "action_trust": dict(self.action_trust),
            "global_trust": round(self.global_trust, 3),
            "interactions": self.interactions,
            "successful_interactions": self.successful_interactions,
        }


class ReputationNetwork:
    def __init__(self, config: CommunicationConfig):
        self.cfg = config
        self.vectors: Dict[int, TrustVector] = {}
        self.gossip_received: List[Tuple[int, int, str, float, int]] = []

    def get_or_create(self, peer_id: int) -> TrustVector:
        if peer_id not in self.vectors:
            self.vectors[peer_id] = TrustVector(peer_id=peer_id)
        return self.vectors[peer_id]

    def update(self, peer_id: int, concept: str, action: str, outcome: str, tick: int):
        vec = self.get_or_create(peer_id)
        vec.update_concept(concept, outcome, tick)
        vec.update_action(action, outcome, tick)

    def get_trust_for(self, peer_id: int, concept=None, action=None) -> float:
        if peer_id not in self.vectors:
            return 0.5
        vec = self.vectors[peer_id]
        if concept:
            return vec.get_concept_trust(concept)
        if action:
            return vec.get_action_trust(action)
        return vec.global_trust

    def get_most_trusted(self, concept=None, min_trust=0.6) -> List[Tuple[int, float]]:
        scores = []
        for peer_id, vec in self.vectors.items():
            t = vec.get_concept_trust(concept) if concept else vec.global_trust
            if t >= min_trust:
                scores.append((peer_id, t))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    def decay_all(self, tick: int):
        for vec in self.vectors.values():
            vec.decay(tick, self.cfg.trust_decay)

    def to_dict(self) -> dict:
        return {str(k): v.to_dict() for k, v in self.vectors.items()}


class GossipProtocol:
    def __init__(self, config: CommunicationConfig):
        self.cfg = config

    def should_gossip(self, mote_trust_in_peer: float) -> bool:
        return random.random() < self.cfg.trust_gossip_prob and mote_trust_in_peer > 0.4

    def generate_gossip(self, speaker_network: ReputationNetwork, listener_id: int, tick: int) -> Optional[List[Tuple[int, str, float]]]:
        gossip_items = []
        for peer_id, vec in speaker_network.vectors.items():
            if peer_id == listener_id or vec.interactions < 2:
                continue
            for concept, trust in vec.concept_trust.items():
                if abs(trust - 0.5) > 0.3:
                    gossip_items.append((peer_id, concept, trust))
        if len(gossip_items) > 3:
            gossip_items = random.sample(gossip_items, 3)
        return gossip_items if gossip_items else None

    def receive_gossip(self, listener_network: ReputationNetwork, speaker_id: int, gossip_items: List[Tuple[int, str, float]], tick: int):
        speaker_trust = listener_network.get_trust_for(speaker_id)
        for about_id, concept, reported_trust in gossip_items:
            credibility = speaker_trust
            current_prior = listener_network.get_trust_for(about_id, concept)
            weight = 0.3 * credibility
            new_trust = current_prior * (1 - weight) + reported_trust * weight
            vec = listener_network.get_or_create(about_id)
            vec.concept_trust[concept] = max(0.0, min(1.0, new_trust))
            listener_network.gossip_received.append((speaker_id, about_id, concept, reported_trust, tick))

    def detect_echo_chambers(self, network: ReputationNetwork, min_agreement=0.8) -> List[Set[int]]:
        high_trust_edges: Dict[int, Set[int]] = defaultdict(set)
        for peer_id, vec in network.vectors.items():
            for other_id, other_vec in network.vectors.items():
                if peer_id != other_id and vec.global_trust > min_agreement and other_vec.global_trust > min_agreement:
                    high_trust_edges[peer_id].add(other_id)
        visited = set()
        chambers = []
        for peer_id in high_trust_edges:
            if peer_id in visited:
                continue
            chamber = set()
            stack = [peer_id]
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                chamber.add(current)
                for neighbor in high_trust_edges.get(current, set()):
                    if neighbor not in visited:
                        stack.append(neighbor)
            if len(chamber) >= 3:
                chambers.append(chamber)
        return chambers
