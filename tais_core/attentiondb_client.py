"""Thin REST client for AttentionDB (Rust vector engine)."""

from __future__ import annotations

import socket
from typing import Any, Dict, List, Optional

import requests


class AttentionDBClient:
    """Stateless HTTP client for the AttentionDB REST API.

    AttentionDB is a separate Rust binary (``attentiondb-server``).
    This client knows nothing about TAIS — it speaks generic
    ``collection``, ``insert``, ``attend`` over JSON.
    """

    def __init__(self, host: str = "localhost", port: int = 8080, api_key: Optional[str] = None):
        self.base_url = f"http://{host}:{port}/v1"
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
        self._session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=1, pool_maxsize=1,
            max_retries=0,
        )
        self._session.mount("http://", adapter)

    def create_collection(self, name: str, dimension: int) -> requests.Response:
        payload = {
            "collection": name,
            "dimension": dimension,
            "fields": [
                {"name": "action", "type": "text"},
                {"name": "domain", "type": "text"},
                {"name": "reward", "type": "float"},
            ],
        }
        return self._session.post(f"{self.base_url}/collections", headers=self.headers, json=payload, timeout=2.0)

    def insert_episode(
        self,
        collection: str,
        fields: Dict[str, str],
        vectors: Dict[str, List[float]],
    ) -> requests.Response:
        payload = {
            "collection": collection,
            "fields": fields,
            "vectors": {head: vec for head, vec in vectors.items()},
        }
        return self._session.post(f"{self.base_url}/insert", headers=self.headers, json=payload, timeout=2.0)

    def attend(
        self,
        collection: str,
        query_vec: List[float],
        heads: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        payload = {
            "collection": collection,
            "query": query_vec,
            "heads": heads or [],
            "top_k": top_k,
        }
        resp = self._session.post(f"{self.base_url}/attend", headers=self.headers, json=payload, timeout=2.0)
        if resp.status_code == 200:
            return resp.json().get("results", [])
        return []

    def health(self) -> bool:
        """Check server health via raw IPv4 socket with guaranteed timeout.

        Uses explicit ``AF_INET`` to avoid Windows IPv6 fallback issues where
        ``create_connection`` can hang during ``sock.connect()`` despite an
        explicit timeout parameter (observed on Python 3.14 / Windows).
        """
        host = "localhost"
        port = 8080
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            try:
                sock.connect((host, port))
                sock.sendall(b"GET /v1/health HTTP/1.0\r\nHost: localhost\r\n\r\n")
                resp = sock.recv(1024)
                return b"200" in resp[:64]
            finally:
                sock.close()
        except (socket.timeout, ConnectionRefusedError, OSError, TimeoutError):
            return False
