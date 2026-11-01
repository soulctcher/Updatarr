"""Unit evidence for the M0 security, event and simulated-task modules."""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from updatarr.events import EventHistory  # noqa: E402
from updatarr.security import AuthenticationError, SessionStore  # noqa: E402
from updatarr.tasks import CheckTaskManager  # noqa: E402


def test_session_rotation_expiry_revocation_and_password_change() -> None:
    now = [10.0]
    store = SessionStore("first-password", ttl_seconds=5, clock=lambda: now[0])
    first = store.authenticate("first-password", "local")
    second = store.authenticate("first-password", "local")
    assert first.session_id != second.session_id
    assert first.csrf_token != second.csrf_token

    store.revoke(first.session_id)
    assert store.get(first.session_id) is None
    assert store.get(second.session_id) == second

    replacement = store.change_password("first-password", "second-password")
    assert store.get(second.session_id) is None
    assert store.get(replacement.session_id) == replacement
    with pytest.raises(AuthenticationError):
        store.authenticate("first-password", "local")

    now[0] = 16.0
    assert store.get(replacement.session_id) is None


def test_login_throttle_and_managed_host_recovery() -> None:
    now = [10.0]
    store = SessionStore("first-password", max_failures=2, throttle_seconds=4, clock=lambda: now[0])
    for _ in range(2):
        with pytest.raises(AuthenticationError, match="not accepted"):
            store.authenticate("wrong-password", "client")
    with pytest.raises(AuthenticationError, match="wait"):
        store.authenticate("first-password", "client")
    now[0] = 15.0
    assert store.authenticate("first-password", "client")

    with pytest.raises(AuthenticationError, match="managed computer"):
        store.recover_from_managed_host("recovered-password", host_local=False)
    store.recover_from_managed_host("recovered-password", host_local=True)
    assert store.authenticate("recovered-password", "client")


def test_event_history_replay_and_reset() -> None:
    history = EventHistory(limit=2)
    first = history.publish("progress", {"value": 1})
    second = history.publish("progress", {"value": 2})
    third = history.publish("progress", {"value": 3})
    assert first.id == 1 and third.id == 3
    reset, replay = history.after(0)
    assert reset is True
    assert [event.id for event in replay] == [2, 3]
    reset, replay = history.after(second.id)
    assert reset is False
    assert [event.id for event in replay] == [3]


def test_slow_event_subscriber_receives_reset_instead_of_silent_loss() -> None:
    history = EventHistory(limit=2)
    queue = history.subscribe()
    history.publish("progress", {"value": 1})
    history.publish("progress", {"value": 2})
    history.publish("progress", {"value": 3})
    queued = []
    while not queue.empty():
        queued.append(queue.get_nowait())
    assert queued[-1].kind == "reset"
    assert queued[-1].id == history.latest_id
    history.unsubscribe(queue)


def test_simulated_check_is_deduplicated() -> None:
    async def scenario() -> None:
        history = EventHistory()
        manager = CheckTaskManager(history)
        first, created = manager.start()
        duplicate, duplicate_created = manager.start()
        assert created is True
        assert duplicate_created is False
        assert duplicate.id == first.id
        assert manager.start_count == 1
        await asyncio.sleep(0.85)
        assert first.state == "complete"
        assert first.progress == 100

    asyncio.run(scenario())
