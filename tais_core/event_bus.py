"""Typed event bus for TAIS — enables observable mote behavior."""

from __future__ import annotations

import json
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set


class EventType(Enum):
    MOTE_STEP = auto()
    ACTION_TAKEN = auto()
    TASK_SUCCESS = auto()
    TASK_FAILURE = auto()
    PATTERN_STORED = auto()
    TRANSFER_USED = auto()
    TEACHING = auto()
    PREDICTION = auto()
    ENERGY_CHANGE = auto()
    PLAN_CREATED = auto()
    PLAN_ADVANCED = auto()
    CULTURAL_QUERY = auto()


@dataclass
class Event:
    type: EventType
    tick: int
    mote_id: Optional[int]
    data: Dict[str, Any]
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.name,
            "tick": self.tick,
            "mote_id": self.mote_id,
            "data": self.data,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


class EventBus:
    def __init__(self, history_size: int = 10000):
        self._subscribers: Dict[EventType, List[Callable[[Event], None]]] = {}
        self._global_subscribers: List[Callable[[Event], None]] = []
        self._history: deque = deque(maxlen=history_size)
        self._filters: Dict[EventType, Callable[[Event], bool]] = {}
        self._event_counts: Dict[EventType, int] = {}
        self._muted_types: Set[EventType] = set()

    def subscribe(self, event_type: EventType, handler: Callable[[Event], None]):
        self._subscribers.setdefault(event_type, []).append(handler)

    def subscribe_all(self, handler: Callable[[Event], None]):
        self._global_subscribers.append(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable[[Event], None]):
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h != handler
            ]

    def set_filter(self, event_type: EventType, filter_fn: Callable[[Event], bool]):
        self._filters[event_type] = filter_fn

    def mute(self, event_type: EventType):
        self._muted_types.add(event_type)

    def unmute(self, event_type: EventType):
        self._muted_types.discard(event_type)

    def emit(self, event: Event):
        if event.type in self._muted_types:
            return
        if event.type in self._filters and not self._filters[event.type](event):
            return
        self._history.append(event)
        self._event_counts[event.type] = self._event_counts.get(event.type, 0) + 1
        for handler in self._subscribers.get(event.type, []):
            try:
                handler(event)
            except Exception as e:
                print(f"[EventBus] Handler error for {event.type}: {e}")
        for handler in self._global_subscribers:
            try:
                handler(event)
            except Exception as e:
                print(f"[EventBus] Global handler error: {e}")

    def get_history(
        self,
        event_types: Optional[List[EventType]] = None,
        tick_start: Optional[int] = None,
        tick_end: Optional[int] = None,
        mote_id: Optional[int] = None,
        limit: int = 1000,
    ) -> List[Event]:
        results = []
        for event in reversed(self._history):
            if len(results) >= limit:
                break
            if event_types and event.type not in event_types:
                continue
            if tick_start is not None and event.tick < tick_start:
                continue
            if tick_end is not None and event.tick > tick_end:
                continue
            if mote_id is not None and event.mote_id != mote_id:
                continue
            results.append(event)
        return list(reversed(results))

    def get_stats(self) -> Dict[str, int]:
        return {k.name: v for k, v in self._event_counts.items()}

    def clear_history(self):
        self._history.clear()
