"""M1 tray model checks without creating a graphical session."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from updatarr.tray import (  # noqa: E402
    TRAY_ICON_COLORS,
    TrayStatus,
    build_status_icon,
    edit_tray_preferences,
    save_tray_preferences,
    should_notify,
)
from updatarr.tray_settings import (  # noqa: E402
    NotificationBehavior,
    TrayPreferences,
    TrayPreferencesFile,
)


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


def test_tray_status_distinguishes_not_checked_clear_and_updates() -> None:
    not_checked = TrayStatus.from_overview({"snapshot": None, "summary": {}})
    clear = TrayStatus.from_overview({
        "snapshot": {"snapshot_id": "one"},
        "summary": {"updates_found": 0, "blocked": 0},
    })
    updates = TrayStatus.from_overview({
        "snapshot": {"snapshot_id": "two"},
        "summary": {"updates_found": 2, "ready_to_review": 1, "blocked": 1},
    })
    assert not_checked.icon_state == "not_checked"
    assert clear.icon_state == "clear"
    assert updates.icon_state == "updates"


def test_notification_preferences_control_when_a_message_appears() -> None:
    clear = TrayStatus.from_overview({
        "snapshot": {"snapshot_id": "one"},
        "summary": {"updates_found": 0, "blocked": 0},
    })
    one_update = TrayStatus.from_overview({
        "snapshot": {"snapshot_id": "two"},
        "summary": {"updates_found": 1, "ready_to_review": 1, "blocked": 0},
    })
    two_updates = TrayStatus.from_overview({
        "snapshot": {"snapshot_id": "three"},
        "summary": {"updates_found": 2, "ready_to_review": 2, "blocked": 0},
    })
    never = TrayPreferences(notification_behavior=NotificationBehavior.NEVER)
    first_only = TrayPreferences(notification_behavior=NotificationBehavior.WHEN_UPDATES_APPEAR)
    changes = TrayPreferences(notification_behavior=NotificationBehavior.WHEN_STATUS_CHANGES)
    assert should_notify(clear, one_update, never) is False
    assert should_notify(clear, one_update, first_only) is True
    assert should_notify(one_update, two_updates, first_only) is False
    assert should_notify(one_update, two_updates, changes) is True


def test_tray_preferences_are_private_validated_and_recover_from_bad_data(tmp_path: Path) -> None:
    path = tmp_path / "config" / "updatarr" / "tray-settings.json"
    store = TrayPreferencesFile(path)
    expected = TrayPreferences(
        refresh_seconds=30,
        notification_behavior=NotificationBehavior.WHEN_UPDATES_APPEAR,
        notification_duration_seconds=12,
        reminder_minutes=240,
    )
    store.write(expected)
    assert store.read() == expected
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700

    path.write_text('{"refresh_seconds": 999, "notification_behavior": "loud"}', encoding="utf-8")
    assert store.read() == TrayPreferences()


def test_tray_icons_render_muted_status_circles(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(["tray-icon-test"])
    assert app is not None
    for state in ("not_checked", "clear", "updates"):
        image = build_status_icon(state, QIcon()).pixmap(32, 32).toImage()
        assert image.pixelColor(16, 3).name().upper() == TRAY_ICON_COLORS[state]

    packaged_loop = QIcon(str(ROOT / "web/src/assets/updatarr-loop.png"))
    assert packaged_loop.isNull() is False
    composed = build_status_icon("clear", packaged_loop).pixmap(32, 32).toImage()
    metallic_pixels = sum(
        composed.pixelColor(x, y).lightness() >= 180
        for x in range(6, 26)
        for y in range(6, 26)
    )
    assert metallic_pixels >= 20


def test_notification_reminder_frequency_and_clear_transition() -> None:
    update = TrayStatus.from_overview({
        "snapshot": {"snapshot_id": "one"},
        "summary": {"updates_found": 1, "ready_to_review": 1, "blocked": 0},
    })
    clear = TrayStatus.from_overview({
        "snapshot": {"snapshot_id": "two"},
        "summary": {"updates_found": 0, "blocked": 0},
    })
    preferences = TrayPreferences(reminder_minutes=60)
    assert should_notify(
        update,
        update,
        preferences,
        seconds_since_last_notification=3599,
    ) is False
    assert should_notify(
        update,
        update,
        preferences,
        seconds_since_last_notification=3600,
    ) is True
    assert should_notify(
        update,
        clear,
        preferences,
        seconds_since_last_notification=7200,
    ) is False


def test_tray_settings_dialog_returns_saved_controls(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QComboBox, QDialog

    app = QApplication.instance() or QApplication(["tray-settings-test"])

    def save_dialog() -> None:
        dialog = next(
            widget
            for widget in app.topLevelWidgets()
            if isinstance(widget, QDialog)
            and widget.objectName() == "updatarrTraySettings"
        )
        for name, value in (
            ("refreshSeconds", 30),
            (
                "notificationBehavior",
                NotificationBehavior.WHEN_UPDATES_APPEAR.value,
            ),
            ("reminderMinutes", 240),
            ("notificationDurationSeconds", 12),
        ):
            choice = dialog.findChild(QComboBox, name)
            choice.setCurrentIndex(choice.findData(value))
        dialog.accept()

    QTimer.singleShot(0, save_dialog)
    saved = edit_tray_preferences(TrayPreferences())
    assert saved == TrayPreferences(
        refresh_seconds=30,
        notification_behavior=NotificationBehavior.WHEN_UPDATES_APPEAR,
        notification_duration_seconds=12,
        reminder_minutes=240,
    )


def test_failed_tray_settings_write_keeps_previous_live_settings(tmp_path: Path) -> None:
    class FailingStore(TrayPreferencesFile):
        def write(self, preferences: TrayPreferences) -> None:
            raise OSError("simulated full disk")

    applied: list[TrayPreferences] = []
    error = save_tray_preferences(
        FailingStore(tmp_path / "tray-settings.json"),
        TrayPreferences(refresh_seconds=30),
        applied.append,
    )
    assert error is not None
    assert "previous settings are still in use" in error
    assert "try again" in error
    assert applied == []
