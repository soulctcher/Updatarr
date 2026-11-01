"""Inventory Module: provider coordination, truthfulness and persistence."""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
import secrets
from typing import Any, Callable

from .domain import InventorySnapshot, SourceResult, SourceState, utc_now
from .events import EventHistory
from .providers.base import ProviderAdapter
from .policy import matching_policy_ids
from .storage import StateStore


@dataclass
class InventoryTask:
    id: str
    state: str
    progress: int
    started_at: str
    message: str
    type: str = "inventory_check"
    finished_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class InventoryCoordinator:
    """Own exactly one coordinated read-only inventory check at a time."""

    def __init__(
        self,
        adapters: list[ProviderAdapter],
        store: StateStore,
        events: EventHistory,
        snapshot_listener: Callable[[InventorySnapshot], None] | None = None,
    ) -> None:
        self._adapters = adapters
        self._store = store
        self._events = events
        self._active: InventoryTask | None = None
        self._runner: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        self._cancel_requested = False
        self._snapshot_listener = snapshot_listener
        self.start_count = 0

    @property
    def active(self) -> InventoryTask | None:
        return self._active

    def start(self) -> tuple[InventoryTask, bool]:
        if self._active and self._active.state in {"checking", "cancelling"}:
            return self._active, False
        task = InventoryTask(
            id=secrets.token_urlsafe(9), state="checking", progress=0,
            started_at=utc_now(), message="Starting a read-only inventory check",
        )
        self._active = task
        self._cancel_requested = False
        self.start_count += 1
        self._store.save_task(task.to_dict())
        self._publish(task, "check-progress")
        self._store.record_audit("inventory_check_started", "administrator", {"read_only": True}, task.id)
        self._runner = asyncio.create_task(self._run(task))
        return task, True

    async def wait(self) -> None:
        if self._runner:
            await self._runner

    async def cancel(self) -> bool:
        async with self._lock:
            if not self._active or self._active.state != "checking" or not self._runner:
                return False
            self._cancel_requested = True
            self._active.state = "cancelling"
            self._active.message = "Finishing the current read-only command before cancelling"
            self._store.save_task(self._active.to_dict())
            self._publish(self._active, "check-progress")
            runner = self._runner
        await runner
        return True

    async def _run(self, task: InventoryTask) -> None:
        started_at = task.started_at
        results: list[SourceResult] = []
        try:
            total = max(1, len(self._adapters))
            previous = self._store.latest_snapshot()

            def turned_off_result(adapter: ProviderAdapter) -> SourceResult:
                prior = next(
                    (
                        source for source in (previous.sources if previous else ())
                        if source.source_id == adapter.source_id and source.scope == adapter.scope
                    ),
                    None,
                )
                updates = tuple(
                    replace(update, state=SourceState.NEEDS_REFRESH)
                    for update in (prior.updates if prior else ())
                )
                return SourceResult(
                    source_id=adapter.source_id,
                    name=adapter.name,
                    scope=adapter.scope,
                    state=SourceState.TURNED_OFF,
                    message="This update source is turned off. Its last information needs refresh.",
                    checked_at=utc_now(),
                    duration_ms=0,
                    software=prior.software if prior else (),
                    updates=updates,
                    tool_version=prior.tool_version if prior else None,
                    evidence={"read_only": True, "check_skipped": "turned_off"},
                )

            async def checked(adapter: ProviderAdapter) -> tuple[ProviderAdapter, SourceResult | Exception]:
                if not self._store.source_is_enabled(adapter.source_id, adapter.scope):
                    return adapter, turned_off_result(adapter)
                try:
                    return adapter, await asyncio.to_thread(adapter.check)
                except Exception as error:
                    return adapter, error

            pending = [asyncio.create_task(checked(adapter)) for adapter in self._adapters]
            completed = 0
            for future in asyncio.as_completed(pending):
                adapter, outcome = await future
                if isinstance(outcome, Exception):
                    result = SourceResult(
                        source_id=adapter.source_id,
                        name=adapter.name,
                        scope=adapter.scope,
                        state=SourceState.ERROR,
                        message="This update source could not be read. Try again or view technical details.",
                        checked_at=utc_now(), duration_ms=0,
                        evidence={"error_type": type(outcome).__name__},
                    )
                else:
                    result = outcome
                results.append(result)
                completed += 1
                if self._cancel_requested:
                    continue
                task.progress = min(90, int(completed / total * 90))
                task.message = f"Recorded {result.name}"
                self._store.save_task(task.to_dict())
                self._publish(task, "check-progress", {"source": result.to_dict(include_software=False)})
            if self._cancel_requested:
                task.state = "cancelled"
                task.message = "Read-only inventory check cancelled"
                task.finished_at = utc_now()
                self._store.save_task(task.to_dict())
                self._store.record_audit("inventory_check_cancelled", "administrator", {}, task.id)
                self._publish(task, "check-cancelled")
                return
            snapshot = InventorySnapshot.create(started_at, results)
            self._store.save_snapshot(snapshot)
            if self._snapshot_listener is not None:
                self._snapshot_listener(snapshot)
            policies = self._store.policies()
            self._store.mark_policies_applied(
                matching_policy_ids(snapshot.updates, policies), snapshot.snapshot_id
            )
            task.state = "complete"
            task.progress = 100
            task.message = "Read-only inventory check complete"
            task.finished_at = utc_now()
            self._store.save_task(task.to_dict())
            self._store.record_audit(
                "inventory_check_completed", "administrator",
                {"snapshot_id": snapshot.snapshot_id, "source_count": len(results), **snapshot.summary()}, task.id,
            )
            self._publish(task, "check-complete", {"snapshot": snapshot.to_dict(include_software=False)})
        except asyncio.CancelledError:
            if task.state != "cancelled":
                task.state = "cancelled"
                task.message = "Read-only inventory check cancelled"
                task.finished_at = utc_now()
                self._store.save_task(task.to_dict())
                self._store.record_audit("inventory_check_cancelled", "administrator", {}, task.id)
                self._publish(task, "check-cancelled")
            raise
        except Exception as error:
            task.state = "error"
            task.message = "The inventory check could not finish. Try again."
            task.finished_at = utc_now()
            self._store.save_task(task.to_dict())
            self._store.record_audit(
                "inventory_check_failed", "administrator", {"error_type": type(error).__name__}, task.id
            )
            self._publish(task, "check-error")

    def _publish(self, task: InventoryTask, kind: str, extra: dict[str, Any] | None = None) -> None:
        payload = {**task.to_dict(), **(extra or {})}
        event = self._events.publish(kind, payload)
        self._store.save_event(event.id, task.id, kind, payload)
