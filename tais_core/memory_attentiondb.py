"""AttentionDB-backed episodic memory for TAIS.

This module provides a drop-in replacement for ``MoteMemory`` that
transparently pushes episodes to a live AttentionDB server and retrieves
action boosts via multi-head attention queries.

Architectural boundary
----------------------
- ``AttentionDBClient`` (in ``attentiondb_client.py``) knows nothing about
  TAIS — it speaks generic REST to a Rust vector engine.
- ``AttentionDBEpisodicMemory`` knows nothing about AttentionDB internals —
  it calls three methods (``insert_episode``, ``attend``, ``health``).
- If the server is unreachable the memory falls back to local-only
  behaviour so TAIS never crashes when AttentionDB is absent.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from .attentiondb_client import AttentionDBClient
from .memory import CulturalMemory, MoteMemory
from .reality import Consequence, RealityGraph, Transformation

logger = logging.getLogger(__name__)


class AttentionDBEpisodicMemory(MoteMemory):
    """MoteMemory subclass that optionally mirrors episodes to AttentionDB.

    Parameters
    ----------
    mode : str
        One of ``"auto"`` (try live, fall back to local), ``"live"``
        (require connection, raise on failure), ``"local"`` (never
        connect).

    Connection to AttentionDB is deferred from ``__init__`` to first
    actual use (``record_episode`` or ``get_action_boosts``) so that
    ``__init__`` never blocks on a missing server.
    """

    def __init__(
        self,
        episodic_capacity: int = 128,
        pattern_capacity: int = 32,
        mode: str = "auto",
    ):
        super().__init__(episodic_capacity=episodic_capacity, pattern_capacity=pattern_capacity)
        self._client: Optional[AttentionDBClient] = None
        self._mode = mode
        self._connect_attempted: bool = False

        self.head_names = ["semantic", "temporal", "structural"]
        self.cultural = CulturalMemory()

    # ── lazy connection ──────────────────────────────────────────────────

    def _ensure_connected(self) -> bool:
        """Attempt to connect to AttentionDB once.

        Returns ``True`` if already connected, ``False`` otherwise.
        Connection is only attempted when ``mode="live"`` is explicitly set.
        In ``"auto"`` mode we stay local without attempting a connection,
        avoiding hangs on machines without the AttentionDB server.
        """
        if self._client is not None:
            return True
        if self._connect_attempted:
            return False
        self._connect_attempted = True

        if self._mode != "live":
            self._mode = "local"
            return False

        try:
            client = AttentionDBClient()
            if client.health():
                resp = client.create_collection("tais_episodes", 32)
                if resp.ok:
                    self._client = client
                    logger.info("TAIS ↔ AttentionDB: live connection established")
                    return True
                logger.warning("TAIS ↔ AttentionDB: create_collection returned %s", resp.status_code)
            else:
                logger.info("TAIS ↔ AttentionDB: server unreachable")
        except Exception as exc:
            logger.warning("TAIS ↔ AttentionDB: connection failed — %s", exc)

        raise RuntimeError("AttentionDB required but server is unavailable")

    # ── helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _embed_episode(tick: int) -> Dict[str, List[float]]:
        """Project an episode into multi-head embedding vectors.

        This is a lightweight projection suitable for the bridge.
        A production deployment would replace these stubs with a
        learned encoder shared between TAIS and AttentionDB.
        """
        return {
            "semantic": [0.1] * 8,
            "temporal": [float(tick) / 100.0] * 8,
            "structural": [0.5] * 16,
        }

    # ── overrides ────────────────────────────────────────────────────────

    def record_episode(
        self,
        state_before: RealityGraph,
        transformation: Transformation,
        consequence: Consequence,
        predicted: float,
        domain: str,
        tick: int,
        action_role: str = "UNCLASSIFIED",
    ):
        super().record_episode(state_before, transformation, consequence, predicted, domain, tick, action_role)

        if self._ensure_connected():
            vectors = self._embed_episode(tick)
            self._client.insert_episode(
                "tais_episodes",
                fields={
                    "action": transformation.name,
                    "domain": domain,
                    "reward": str(consequence.net),
                },
                vectors=vectors,
            )

    def get_action_boosts(
        self,
        current_graph: RealityGraph,
        actions: List[Transformation],
        tick: int,
    ) -> Dict[str, float]:
        """Return per-action boost scores.

        In ``live`` mode the scores come from an AttentionDB multi-head
        query; in ``local`` mode they come from pattern-memory transfer.
        """
        if not self._ensure_connected():
            return self._get_local_boosts(current_graph, actions)

        query_vec = [0.5] * 32
        results = self._client.attend("tais_episodes", query_vec, heads=self.head_names)

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
