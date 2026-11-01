"""Simulator-only check-task module used to prove M0 task ownership."""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import secrets

from .events import EventHistory


@dataclass
class CheckTask:
    id: str
    state: str
    progress: int
    started_at: str
    message: str


class CheckTaskManager:
    """Own a single simulated check and deduplicate concurrent requests."""

    def __init__(self, events: EventHistory) -> None:
        self._events = events
        self._active: CheckTask | None = None
        self._runner: asyncio.Task[None] | None = None
        self.start_count = 0

    @property
    def active(self) -> CheckTask | None:
        return self._active

    def start(self) -> tuple[CheckTask, bool]:
        if self._active and self._active.state == "checking":
            return self._active, False
        task = CheckTask(
            id=secrets.token_urlsafe(9),
            state="checking",
            progress=0,
            started_at=datetime.now(timezone.utc).isoformat(),
            message="Starting a simulated update check",
        )
        self._active = task
        self.start_count += 1
        self._events.publish("check-progress", asdict(task))
        self._runner = asyncio.create_task(self._run(task))
        return task, True

    async def _run(self, task: CheckTask) -> None:
        for progress, message in (
            (30, "Checking system packages"),
            (60, "Checking separately managed software"),
            (100, "Simulated check complete"),
        ):
            await asyncio.sleep(0.25)
            if self._active is not task:
                return
            task.progress = progress
            task.message = message
            if progress == 100:
                task.state = "complete"
            self._events.publish("check-progress", asdict(task))
