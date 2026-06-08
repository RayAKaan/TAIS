"""
Persistence layer for TAIS Swarm V6.

SQLite with WAL mode for high-throughput event logging.
"""

from __future__ import annotations

import sqlite3
import json
import time
import threading
from typing import Dict, List, Optional, Any, Iterator
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TickRecord:
    tick: int
    timestamp: float
    population: int
    avg_energy: float
    avg_hydration: float
    avg_toxicity: float
    season: str
    utterance_count: int
    comprehension_success: int
    comprehension_trials: int
    semantic_rate: float
    utility_rate: float
    common_tokens_json: str


@dataclass
class EventRecord:
    tick: int
    event_type: str
    mote_id: Optional[int]
    data_json: str
    timestamp: float


@dataclass
class MoteSnapshot:
    tick: int
    mote_id: int
    x: float
    y: float
    energy: float
    hydration: float
    toxicity: float
    heat: float
    age: int
    intent: str
    lexicon_json: str
    memory_json: str
    genome_json: str


class PersistenceLayer:
    """SQLite-based persistence with WAL mode and batch inserts."""

    def __init__(self, db_path: str = "./tais_v6_data.db"):
        self.db_path = db_path
        self._local = threading.local()
        self._batch_size = 100
        self._event_buffer: List[EventRecord] = []
        self._mote_buffer: List[MoteSnapshot] = []
        self._lock = threading.Lock()

        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn.execute("PRAGMA cache_size=-64000")
            self._local.conn.execute("PRAGMA temp_store=MEMORY")
        return self._local.conn

    def _init_schema(self):
        conn = self._connection()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS ticks (
                tick INTEGER PRIMARY KEY, timestamp REAL NOT NULL, population INTEGER,
                avg_energy REAL, avg_hydration REAL, avg_toxicity REAL, season TEXT,
                utterance_count INTEGER, comprehension_success INTEGER, comprehension_trials INTEGER,
                semantic_rate REAL, utility_rate REAL, common_tokens_json TEXT
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, tick INTEGER NOT NULL,
                event_type TEXT NOT NULL, mote_id INTEGER, data_json TEXT NOT NULL, timestamp REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_events_tick ON events(tick);
            CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
            CREATE INDEX IF NOT EXISTS idx_events_mote ON events(mote_id);
            CREATE TABLE IF NOT EXISTS mote_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT, tick INTEGER NOT NULL, mote_id INTEGER NOT NULL,
                x REAL, y REAL, energy REAL, hydration REAL, toxicity REAL, heat REAL, age INTEGER,
                intent TEXT, lexicon_json TEXT, memory_json TEXT, genome_json TEXT, timestamp REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_snapshots_tick ON mote_snapshots(tick);
            CREATE INDEX IF NOT EXISTS idx_snapshots_mote ON mote_snapshots(mote_id);
            CREATE TABLE IF NOT EXISTS colonies (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL,
                tick INTEGER, data_json TEXT NOT NULL, created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS metrics (
                tick INTEGER PRIMARY KEY, metric_json TEXT NOT NULL
            );
        """)
        conn.commit()

    def log_tick(self, record: TickRecord):
        conn = self._connection()
        conn.execute("""
            INSERT OR REPLACE INTO ticks (tick, timestamp, population, avg_energy, avg_hydration, avg_toxicity,
             season, utterance_count, comprehension_success, comprehension_trials,
             semantic_rate, utility_rate, common_tokens_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (record.tick, record.timestamp, record.population, record.avg_energy, record.avg_hydration,
              record.avg_toxicity, record.season, record.utterance_count, record.comprehension_success,
              record.comprehension_trials, record.semantic_rate, record.utility_rate, record.common_tokens_json))
        conn.commit()

    def buffer_event(self, record: EventRecord):
        with self._lock:
            self._event_buffer.append(record)
            if len(self._event_buffer) >= self._batch_size:
                self._flush_events()

    def _flush_events(self):
        if not self._event_buffer:
            return
        conn = self._connection()
        conn.executemany(
            "INSERT INTO events (tick, event_type, mote_id, data_json, timestamp) VALUES (?, ?, ?, ?, ?)",
            [(e.tick, e.event_type, e.mote_id, e.data_json, e.timestamp) for e in self._event_buffer]
        )
        conn.commit()
        self._event_buffer = []

    def buffer_mote_snapshot(self, snapshot: MoteSnapshot):
        with self._lock:
            self._mote_buffer.append(snapshot)
            if len(self._mote_buffer) >= self._batch_size // 2:
                self._flush_mote_snapshots()

    def _flush_mote_snapshots(self):
        if not self._mote_buffer:
            return
        conn = self._connection()
        conn.executemany("""
            INSERT INTO mote_snapshots (tick, mote_id, x, y, energy, hydration, toxicity, heat, age, intent,
             lexicon_json, memory_json, genome_json, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [(s.tick, s.mote_id, s.x, s.y, s.energy, s.hydration, s.toxicity, s.heat, s.age, s.intent,
               s.lexicon_json, s.memory_json, s.genome_json, time.time()) for s in self._mote_buffer])
        conn.commit()
        self._mote_buffer = []

    def save_colony(self, name: str, tick: int, data: dict):
        conn = self._connection()
        conn.execute("INSERT OR REPLACE INTO colonies (name, tick, data_json, created_at) VALUES (?, ?, ?, ?)",
                     (name, tick, json.dumps(data), time.time()))
        conn.commit()

    def load_colony(self, name: str) -> Optional[dict]:
        conn = self._connection()
        cursor = conn.execute("SELECT data_json FROM colonies WHERE name = ?", (name,))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None

    def list_colonies(self) -> List[dict]:
        conn = self._connection()
        cursor = conn.execute("SELECT name, tick, created_at FROM colonies ORDER BY created_at DESC")
        return [{"name": row[0], "tick": row[1], "created_at": row[2]} for row in cursor.fetchall()]

    def query_events(self, tick_start=None, tick_end=None, event_types=None, mote_id=None, limit=1000) -> Iterator[dict]:
        conn = self._connection()
        conditions = []
        params = []
        if tick_start is not None:
            conditions.append("tick >= ?")
            params.append(tick_start)
        if tick_end is not None:
            conditions.append("tick <= ?")
            params.append(tick_end)
        if event_types:
            conditions.append(f"event_type IN ({','.join('?' * len(event_types))})")
            params.extend(event_types)
        if mote_id is not None:
            conditions.append("mote_id = ?")
            params.append(mote_id)
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        cursor = conn.execute(
            f"SELECT tick, event_type, mote_id, data_json FROM events {where_clause} ORDER BY tick DESC LIMIT ?",
            params + [limit]
        )
        for row in cursor:
            data = json.loads(row[3])
            yield {"tick": row[0], "type": row[1], "mote_id": row[2], **data}

    def close(self):
        self._flush_events()
        self._flush_mote_snapshots()
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
