"""Bounded event history with deterministic reconnect semantics."""

from __future__ import annotations

from collections import deque
import asyncio
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Event:
    id: int
    kind: str
    data: dict[str, Any]


class EventHistory:
    """Keep a bounded replay window and signal when a client must reset."""

    def __init__(self, limit: int = 100) -> None:
        if limit < 1:
            raise ValueError("event history limit must be positive")
        self._events: deque[Event] = deque(maxlen=limit)
        self._next_id = 1
        self._subscribers: set[asyncio.Queue[Event]] = set()

    @property
    def latest_id(self) -> int:
        return self._next_id - 1

    def publish(self, kind: str, data: dict[str, Any]) -> Event:
        event = Event(self._next_id, kind, data)
        self._next_id += 1
        self._events.append(event)
        for subscriber in tuple(self._subscribers):
            try:
                subscriber.put_nowait(event)
            except asyncio.QueueFull:
                while not subscriber.empty():
                    subscriber.get_nowait()
                subscriber.put_nowait(Event(
                    event.id, "reset",
                    {"reason": "Event history is no longer available. Refresh current state."},
                ))
        return event

    def subscribe(self) -> asyncio.Queue[Event]:
        queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=self._events.maxlen or 100)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[Event]) -> None:
        self._subscribers.discard(queue)

    def restore(self, events: list[tuple[int, str, dict[str, Any]]]) -> None:
        """Load a trusted persisted tail before accepting new publications."""
        for event_id, kind, data in events:
            if event_id < self._next_id:
                continue
            self._events.append(Event(event_id, kind, data))
            self._next_id = event_id + 1

    def after(self, last_id: int | None) -> tuple[bool, list[Event]]:
        if last_id is None:
            return False, list(self._events)
        if last_id < 0:
            return True, list(self._events)
        if self._events and last_id < self._events[0].id - 1:
            return True, list(self._events)
        return False, [event for event in self._events if event.id > last_id]
