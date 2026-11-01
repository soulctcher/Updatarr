"""M1 tray model checks without creating a graphical session."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from updatarr.tray import TrayStatus, should_notify  # noqa: E402


def test_tray_uses_shared_overview_meaning() -> None:
    assert TrayStatus.from_overview({"snapshot": None, "summary": {}}).title.endswith("Not checked")
    blocked = TrayStatus.from_overview({"snapshot": {"snapshot_id": "one"}, "summary": {"updates_found": 5, "blocked": 1}})
    assert blocked.attention is True and "1 blocked" in blocked.title
    ready = TrayStatus.from_overview({"snapshot": {"snapshot_id": "one"}, "summary": {"updates_found": 5, "blocked": 0}})
    assert ready.attention is True and "5 ready to review" in ready.title
    current = TrayStatus.from_overview({"snapshot": {"snapshot_id": "one"}, "summary": {"updates_found": 0, "blocked": 0}})
    assert current.attention is False


def test_tray_count_uses_ready_updates_and_notifications_do_not_repeat() -> None:
    previous = TrayStatus.from_overview({"snapshot": None, "summary": {}})
    current = TrayStatus.from_overview({
        "snapshot": {"snapshot_id": "one"},
        "summary": {"updates_found": 7, "ready_to_review": 3, "blocked": 0},
    })
    assert current.title.endswith("3 ready to review")
    assert should_notify(previous, current) is True
    assert should_notify(current, current) is False
