"""Inventory Module behavior through its public Interface."""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from updatarr.domain import SoftwareRecord, SourceResult, SourceState, utc_now  # noqa: E402
from updatarr.events import EventHistory  # noqa: E402
from updatarr.inventory import InventoryCoordinator  # noqa: E402
from updatarr.storage import StateStore  # noqa: E402


class Adapter:
    def __init__(self, source_id: str, delay: float = 0, fail: bool = False) -> None:
        self.source_id = source_id; self.name = source_id.title(); self.scope = "user"; self.delay = delay; self.fail = fail

    def check(self) -> SourceResult:
        time.sleep(self.delay)
        if self.fail: raise RuntimeError("hostile adapter detail must not escape")
        software = SoftwareRecord(self.source_id, self.scope, f"{self.source_id}.app", f"{self.name} app", "1.0")
        return SourceResult(self.source_id, self.name, self.scope, SourceState.NOT_CHECKED, "Inventory recorded.", utc_now(), 1, (software,))


def test_coordinator_deduplicates_persists_partial_results_and_events(tmp_path: Path) -> None:
    async def scenario() -> None:
        store = StateStore(tmp_path / "state.db"); store.initialize()
        events = EventHistory(20)
        coordinator = InventoryCoordinator([Adapter("good", .05), Adapter("failed", fail=True)], store, events)
        first, created = coordinator.start(); duplicate, duplicate_created = coordinator.start()
        assert created is True and duplicate_created is False and duplicate.id == first.id
        await coordinator.wait()
        assert first.state == "complete"
        snapshot = store.latest_snapshot(); assert snapshot is not None
        assert {source.state for source in snapshot.sources} == {SourceState.NOT_CHECKED, SourceState.ERROR}
        assert store.audit_page().total == 2
        reset, replay = events.after(0)
        assert reset is False and replay[-1].kind == "check-complete"
    asyncio.run(scenario())


def test_cancellation_is_recorded(tmp_path: Path) -> None:
    async def scenario() -> None:
        store = StateStore(tmp_path / "state.db"); store.initialize()
        coordinator = InventoryCoordinator([Adapter("slow", .15)], store, EventHistory())
        task, _ = coordinator.start()
        cancellation = asyncio.create_task(coordinator.cancel())
        await asyncio.sleep(.02)
        duplicate, created = coordinator.start()
        assert created is False and duplicate.id == task.id
        assert task.state == "cancelling"
        assert await cancellation is True
        assert task.state == "cancelled"
        assert store.audit_page().items[0]["kind"] == "inventory_check_cancelled"
        replacement, created = coordinator.start()
        assert created is True and replacement.id != task.id
        await coordinator.wait()
    asyncio.run(scenario())
