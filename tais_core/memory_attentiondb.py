"""AttentionDB-backed episodic memory for TAIS.

Provides a drop-in replacement for ``MoteMemory`` that transparently
pushes episodes to a live AttentionDB server and retrieves action boosts
via multi-head attention queries.

Connection is attempted when ``ATTENTIONDB_ENABLED=1`` env var is set
(or when ``mode="live"`` is explicitly passed).  Falls back to local-only
memory if the server is unreachable.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from .attentiondb_client import AttentionDBClient
from .memory import CulturalMemory, MoteMemory
from .reality import Consequence, RealityGraph, Transformation

logger = logging.getLogger(__name__)

_DEFAULT_MODE = "live" if os.environ.get("ATTENTIONDB_ENABLED", "").strip() in ("1", "true", "yes") else "auto"


class AttentionDBEpisodicMemory(MoteMemory):
    """MoteMemory subclass that optionally mirrors episodes to AttentionDB.

    Parameters
    ----------
    mode : str
        ``"auto"`` — try to connect at startup, fall back to local.
        ``"live"`` — require connection, raise on failure.
        ``"local"`` — never connect (default when ``ATTENTIONDB_ENABLED`` is unset).
    """

    def __init__(
        self,
        episodic_capacity: int = 128,
        pattern_capacity: int = 32,
        mode: str = _DEFAULT_MODE,
    ):
        super().__init__(episodic_capacity=episodic_capacity, pattern_capacity=pattern_capacity)
        self._client: Optional[AttentionDBClient] = None
        self._mode = mode
        self._connect_attempted: bool = False

        self.head_names = ["semantic", "temporal", "structural"]
        self.cultural = CulturalMemory()

        if mode == "live":
            self._ensure_connected()

    # ── lazy connection ──────────────────────────────────────────────────

    def _ensure_connected(self) -> bool:
        if self._client is not None:
            return True
        if self._connect_attempted:
            return False
        self._connect_attempted = True

        if self._mode == "local":
            return False

        try:
            client = AttentionDBClient()
            if client.ensure_connected():
                client.create_collection("tais_episodes", 32)
                client.create_collection("tais_patterns", 64)
                client.create_collection("tais_action_values", 16)
                self._client = client
                logger.info("TAIS ↔ AttentionDB: live connection established (%s)",
                            "gRPC" if client._available == "grpc" else "REST")
                return True
        except Exception as exc:
            logger.warning("TAIS ↔ AttentionDB: connection failed — %s", exc)

        if self._mode == "live":
            logger.error("TAIS ↔ AttentionDB: required but unavailable")
        else:
            logger.info("TAIS ↔ AttentionDB: not available, using local memory")
        return False

    # ── helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _embed_graph(
        graph: RealityGraph,
        domain: str,
        tick: int,
    ) -> Dict[str, List[float]]:
        """Project a graph fragment into multi-head embedding vectors."""
        entities = list(graph.entities())
        relations = list(graph.relations())

        type_counts: Dict[str, int] = {}
        for e in entities:
            type_counts[e.etype] = type_counts.get(e.etype, 0) + 1

        rel_counts: Dict[str, int] = {}
        for r in relations:
            rel_counts[r.rtype] = rel_counts.get(r.rtype, 0) + 1

        # Structural: entity type distribution (padded to 16)
        struct = [0.0] * 16
        for i, (_, cnt) in enumerate(sorted(type_counts.items())[:16]):
            struct[i] = min(1.0, cnt / max(1, len(entities)))

        # Semantic: domain one-hot + action info (padded to 8)
        sem = [0.0] * 8
        domain_hash = hash(domain) % 7
        sem[domain_hash] = 1.0

        # Temporal: recency signal
        temp = [min(1.0, tick / 100.0)] * 8

        return {"semantic": sem, "temporal": temp, "structural": struct}

    def _episode_to_text(self, transformation, consequence, domain, action_role) -> str:
        return (f"domain={domain} action={transformation.name} "
                f"op={transformation.universal_op} role={action_role} "
                f"reward={consequence.net:.2f} signal={consequence.task_signal or 'none'}")

    # ── overrides ────────────────────────────────────────────────────────

    def record_episode(
        self,
        state_before: RealityGraph,
        state_after: RealityGraph,
        transformation: Transformation,
        consequence: Consequence,
        predicted: float,
        domain: str,
        tick: int,
        action_role: str = "UNCLASSIFIED",
    ):
        super().record_episode(state_before, state_after, transformation,
                               consequence, predicted, domain, tick, action_role)

        if self._client is not None:
            text = self._episode_to_text(transformation, consequence, domain, action_role)
            vectors = self._embed_graph(state_before, domain, tick)
            self._client.insert_episode(
                "tais_episodes",
                fields={
                    "action": transformation.name,
                    "domain": domain,
                    "reward": str(round(consequence.net, 4)),
                    "text": text,
                },
                vectors=vectors,
            )

    def get_action_boosts(
        self,
        current_graph: RealityGraph,
        actions: List[Transformation],
        tick: int,
    ) -> Dict[str, float]:
        if self._client is None:
            return self._get_local_boosts(current_graph, actions)

        query_text = f"domain={current_graph.domain or 'unknown'}"
        results = self._client.attend(
            "tais_episodes", query_text, heads=self.head_names)

        boosts: Dict[str, float] = {a.name: 0.0 for a in actions}
        for res in results:
            action_name = res.get("fields", {}).get("action")
            reward = float(res.get("fields", {}).get("reward", 0.0))
            score = res.get("score", 0.0)
            if action_name in boosts:
                boosts[action_name] += score * reward
        return boosts

    # ── local fallback ───────────────────────────────────────────────────

    def _get_local_boosts(
        self,
        current_graph: RealityGraph,
        actions: List[Transformation],
    ) -> Dict[str, float]:
        boosts, _ = self.patterns.action_priors(current_graph, actions)
        return boosts
