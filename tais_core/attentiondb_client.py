"""Dual-protocol client for AttentionDB: gRPC primary, REST fallback."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

ATTENTIONDB_GRPC_PORT = int(os.environ.get("ATTENTIONDB_GRPC_PORT", "7400"))
ATTENTIONDB_REST_PORT = int(os.environ.get("ATTENTIONDB_REST_PORT", "8080"))
ATTENTIONDB_HOST = os.environ.get("ATTENTIONDB_HOST", "localhost")


class AttentionDBClient:
    """Stateless dual-protocol client.

    Tries gRPC first (port 7400), falls back to REST (port 8080).
    Gracefully degrades to no-op if neither is available.
    """

    def __init__(self, host: str = ATTENTIONDB_HOST,
                 grpc_port: int = ATTENTIONDB_GRPC_PORT,
                 rest_port: int = ATTENTIONDB_REST_PORT,
                 api_key: Optional[str] = None):
        self.host = host
        self.grpc_port = grpc_port
        self.rest_port = rest_port
        self.api_key = api_key
        self._grpc_stub: Any = None
        self._grpc_channel: Any = None
        self._rest_session = requests.Session()
        self._rest_session.mount("http://", requests.adapters.HTTPAdapter(
            pool_connections=1, pool_maxsize=1, max_retries=0))
        self._available: Optional[str] = None  # "grpc", "rest", or None

    # ── connection ──────────────────────────────────────────────────────

    def ensure_connected(self) -> bool:
        if self._available:
            return True
        if self._try_grpc():
            self._available = "grpc"
            logger.info("AttentionDB: connected via gRPC on %s:%s",
                        self.host, self.grpc_port)
            return True
        if self._try_rest_health():
            self._available = "rest"
            logger.info("AttentionDB: connected via REST on %s:%s",
                        self.host, self.rest_port)
            return True
        logger.info("AttentionDB: not available (tried gRPC:%s, REST:%s)",
                    self.grpc_port, self.rest_port)
        return False

    def _try_grpc(self) -> bool:
        try:
            import grpc
            from tais_core.attentiondb_pb2 import HealthRequest
            from tais_core.attentiondb_pb2_grpc import AttentionDBStub
            channel = grpc.insecure_channel(f"{self.host}:{self.grpc_port}")
            stub = AttentionDBStub(channel)
            resp = stub.HealthCheck(HealthRequest(), timeout=2.0)
            if resp.status == "ok":
                self._grpc_channel = channel
                self._grpc_stub = stub
                return True
        except Exception:
            pass
        return False

    def _try_rest_health(self) -> bool:
        try:
            resp = self._rest_session.get(
                f"{self._rest_base}/health", timeout=2.0)
            return resp.ok
        except Exception:
            return False

    # ── API methods ─────────────────────────────────────────────────────

    def create_collection(self, name: str, dimension: int) -> bool:
        if self._available == "grpc":
            return self._grpc_create_collection(name, dimension)
        if self._available == "rest":
            return self._rest_create_collection(name, dimension)
        return False

    def insert_episode(self, collection: str, fields: Dict[str, str],
                       vectors: Optional[Dict[str, List[float]]] = None) -> bool:
        if self._available == "grpc":
            return self._grpc_insert(collection, fields)
        if self._available == "rest":
            return self._rest_insert(collection, fields, vectors or {})
        return False

    def attend(self, collection: str, query: str,
               heads: Optional[List[str]] = None,
               top_k: int = 5) -> List[Dict[str, Any]]:
        if self._available == "grpc":
            return self._grpc_attend(collection, query, heads, top_k)
        if self._available == "rest":
            return self._rest_attend(collection, query, heads, top_k)
        return []

    def health(self) -> bool:
        return self._available is not None

    # ── gRPC implementations ────────────────────────────────────────────

    def _grpc_create_collection(self, name: str, dimension: int) -> bool:
        try:
            from tais_core.attentiondb_pb2 import (
                CreateCollectionRequest, FieldDefinition,
            )
            req = CreateCollectionRequest(
                collection=name,
                dimension=dimension,
                fields=[
                    FieldDefinition(name="action", type="text"),
                    FieldDefinition(name="domain", type="text"),
                    FieldDefinition(name="reward", type="float"),
                ],
            )
            resp = self._grpc_stub.CreateCollection(req, timeout=5.0)
            return resp.success
        except Exception as e:
            logger.warning("AttentionDB gRPC create_collection failed: %s", e)
            return False

    def _grpc_insert(self, collection: str, fields: Dict[str, str]) -> bool:
        try:
            from tais_core.attentiondb_pb2 import InsertRequest
            req = InsertRequest(collection=collection, fields=fields)
            resp = self._grpc_stub.Insert(req, timeout=5.0)
            return resp.success
        except Exception as e:
            logger.warning("AttentionDB gRPC insert failed: %s", e)
            return False

    def _grpc_attend(self, collection: str, query: str,
                     heads: Optional[List[str]], top_k: int) -> List[Dict[str, Any]]:
        try:
            from tais_core.attentiondb_pb2 import AttendRequest
            req = AttendRequest(
                collection=collection,
                query=query,
                heads=heads or [],
                top_k=top_k,
            )
            resp = self._grpc_stub.Attend(req, timeout=5.0)
            results = []
            for r in resp.results:
                results.append({
                    "id": r.id,
                    "score": r.score,
                    "fields": dict(r.fields),
                })
            return results
        except Exception as e:
            logger.warning("AttentionDB gRPC attend failed: %s", e)
            return []

    # ── REST implementations ────────────────────────────────────────────

    @property
    def _rest_base(self) -> str:
        return f"http://{self.host}:{self.rest_port}/v1"

    def _rest_create_collection(self, name: str, dimension: int) -> bool:
        try:
            payload = {
                "collection": name,
                "dimension": dimension,
                "fields": [
                    {"name": "action", "type": "text"},
                    {"name": "domain", "type": "text"},
                    {"name": "reward", "type": "float"},
                ],
            }
            resp = self._rest_session.post(
                f"{self._rest_base}/collections", json=payload, timeout=3.0)
            return resp.ok
        except Exception as e:
            logger.warning("AttentionDB REST create_collection failed: %s", e)
            return False

    def _rest_insert(self, collection: str, fields: Dict[str, str],
                     vectors: Dict[str, List[float]]) -> bool:
        try:
            payload = {"collection": collection, "fields": fields}
            if vectors:
                payload["vectors"] = vectors
            resp = self._rest_session.post(
                f"{self._rest_base}/insert", json=payload, timeout=3.0)
            return resp.ok
        except Exception as e:
            logger.warning("AttentionDB REST insert failed: %s", e)
            return False

    def _rest_attend(self, collection: str, query: str,
                     heads: Optional[List[str]], top_k: int) -> List[Dict[str, Any]]:
        try:
            payload = {
                "collection": collection,
                "query": query,
                "heads": heads or [],
                "top_k": top_k,
            }
            resp = self._rest_session.post(
                f"{self._rest_base}/attend", json=payload, timeout=3.0)
            if resp.status_code == 200:
                return resp.json().get("results", [])
        except Exception as e:
            logger.warning("AttentionDB REST attend failed: %s", e)
        return []
