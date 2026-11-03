"""Thin KDE tray for the shared overview contract.

The tray owns no update policy. Its model consumes the same overview document
as the browser, and the Qt shell only opens the canonical loopback interface.
It reads a restricted status document written by the service and is never
started automatically by package installation.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import fcntl
import os
from pathlib import Path
import time
import webbrowser

from .tray_status import TrayStatusFile
from .tray_settings import (
    NotificationBehavior,
    TrayPreferences,
    TrayPreferencesFile,
    default_tray_preferences_path,
)


TRAY_ICON_COLORS = {
    "not_checked": "#6B7280",
    "clear": "#4F806B",
    "updates": "#A45D64",
}


def build_status_icon(icon_state: str, base_icon=None):
    """Render the Updatarr mark over a truthful, muted status circle."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap

    if icon_state not in TRAY_ICON_COLORS:
        raise ValueError(f"Unknown tray icon state: {icon_state}")
    source_icon = base_icon if base_icon is not None else QIcon.fromTheme("updatarr")
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(TRAY_ICON_COLORS[icon_state]))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(1, 1, 30, 30)
    if source_icon.isNull():
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "↻")
    else:
        painter.drawPixmap(4, 4, source_icon.pixmap(24, 24))
    painter.end()
    return QIcon(pixmap)


@dataclass(frozen=True)
class TrayStatus:
    title: str
    detail: str
    attention: bool
    icon_state: str

    @classmethod
    def from_overview(cls, payload: dict) -> "TrayStatus":
        summary = payload.get("summary", {})
        updates = int(summary.get("updates_found", 0))
        ready = int(summary.get("ready_to_review", updates))
        blocked = int(summary.get("blocked", 0))
        snapshot = payload.get("snapshot")
        if snapshot is None:
            return cls(
                "Updatarr — Not checked",
                "Open Updatarr to check software.",
                False,
                "not_checked",
            )
        if blocked:
            return cls(
                f"Updatarr — {blocked} blocked",
                f"{ready} ready to review; open Updatarr to review what is blocked.",
                True,
                "updates",
            )
        if ready:
            return cls(
                f"Updatarr — {ready} ready to review",
                "Open Updatarr to review them.",
                True,
                "updates",
            )
        if updates:
            return cls(
                f"Updatarr — {updates} updates recorded",
                "Open Updatarr to review their current status.",
                True,
                "updates",
            )
        return cls(
            "Updatarr — No updates recorded",
            "The latest recorded check found no updates.",
            False,
            "clear",
        )


def should_notify(
    previous: TrayStatus,
    current: TrayStatus,
    preferences: TrayPreferences | None = None,
    *,
    seconds_since_last_notification: float | None = None,
) -> bool:
    """Apply the user's notification choice without changing update policy."""
    behavior = (preferences or TrayPreferences()).notification_behavior
    if behavior is NotificationBehavior.NEVER or not current.attention:
        return False
    reminder_due = (
        preferences is not None
        and preferences.reminder_minutes > 0
        and seconds_since_last_notification is not None
        and seconds_since_last_notification >= preferences.reminder_minutes * 60
    )
    if behavior is NotificationBehavior.WHEN_UPDATES_APPEAR:
        return not previous.attention or reminder_due
    return current != previous or reminder_due


def edit_tray_preferences(current: TrayPreferences) -> TrayPreferences | None:
    """Show the local tray settings window and return a saved choice."""
    from PySide6.QtWidgets import (
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFormLayout,
        QLabel,
        QVBoxLayout,
    )

    dialog = QDialog()
    dialog.setObjectName("updatarrTraySettings")
    dialog.setWindowTitle("Updatarr Tray Settings")
    dialog.setMinimumWidth(420)
    layout = QVBoxLayout(dialog)
    explanation = QLabel(
        "Choose how often the tray refreshes its recorded status and when it shows desktop notifications."
    )
    explanation.setWordWrap(True)
    layout.addWidget(explanation)
    form = QFormLayout()

    refresh_choice = QComboBox()
    refresh_choice.setObjectName("refreshSeconds")
    for seconds, label in (
        (5, "5 seconds"),
        (15, "15 seconds"),
        (30, "30 seconds"),
        (60, "1 minute"),
    ):
        refresh_choice.addItem(label, seconds)
    refresh_choice.setCurrentIndex(refresh_choice.findData(current.refresh_seconds))
    form.addRow("Refresh tray status:", refresh_choice)

    behavior_choice = QComboBox()
    behavior_choice.setObjectName("notificationBehavior")
    for behavior, label in (
        (
            NotificationBehavior.WHEN_STATUS_CHANGES,
            "When updates appear or their count changes",
        ),
        (NotificationBehavior.WHEN_UPDATES_APPEAR, "When updates first appear"),
        (NotificationBehavior.NEVER, "Never"),
    ):
        behavior_choice.addItem(label, behavior.value)
    behavior_choice.setCurrentIndex(
        behavior_choice.findData(current.notification_behavior.value)
    )
    form.addRow("Show notifications:", behavior_choice)

    reminder_choice = QComboBox()
    reminder_choice.setObjectName("reminderMinutes")
    for minutes, label in (
        (0, "Do not repeat"),
        (60, "Every hour"),
        (240, "Every 4 hours"),
        (1440, "Once a day"),
    ):
        reminder_choice.addItem(label, minutes)
    reminder_choice.setCurrentIndex(reminder_choice.findData(current.reminder_minutes))
    form.addRow("Repeat while updates are waiting:", reminder_choice)

    duration_choice = QComboBox()
    duration_choice.setObjectName("notificationDurationSeconds")
    for seconds in (5, 8, 12):
        duration_choice.addItem(f"{seconds} seconds", seconds)
    duration_choice.setCurrentIndex(
        duration_choice.findData(current.notification_duration_seconds)
    )
    form.addRow("Keep notifications visible for:", duration_choice)
    layout.addLayout(form)
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return TrayPreferences(
        refresh_seconds=int(refresh_choice.currentData()),
        notification_behavior=NotificationBehavior(behavior_choice.currentData()),
        notification_duration_seconds=int(duration_choice.currentData()),
        reminder_minutes=int(reminder_choice.currentData()),
    )


class TrayInstanceLock:
    """Hold a per-user advisory lock for the lifetime of the tray."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._stream = None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.path.parent, 0o700)
        self._stream = self.path.open("a+", encoding="utf-8")
        os.chmod(self.path, 0o600)
        try:
            fcntl.flock(self._stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self._stream.close()
            self._stream = None
            return False
        self._stream.seek(0)
        self._stream.truncate()
        self._stream.write(str(os.getpid()))
        self._stream.flush()
        return True

    def release(self) -> None:
        if self._stream is not None:
            fcntl.flock(self._stream, fcntl.LOCK_UN)
            self._stream.close()
            self._stream = None


def save_tray_preferences(
    settings_file: TrayPreferencesFile,
    candidate: TrayPreferences,
    apply_saved: Callable[[TrayPreferences], None],
) -> str | None:
    """Persist first, then apply; return a plain-language error on failure."""
    try:
        settings_file.write(candidate)
    except OSError:
        return (
            "Updatarr could not save the tray settings. "
            "Your previous settings are still in use. Check that your personal "
            "configuration folder is writable, then try again."
        )
    apply_saved(candidate)
    return None


def run_tray(
    status: TrayStatus | None = None,
    url: str = "http://127.0.0.1:8788",
    *,
    status_path: Path | None = None,
    lock_path: Path | None = None,
    preferences_path: Path | None = None,
) -> int:
    """Run the opt-in tray; refuse root and a second tray instance."""
    if os.geteuid() == 0:
        raise RuntimeError("The Updatarr tray must not run as root.")
    runtime_dir = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "updatarr"
    instance = TrayInstanceLock(lock_path or runtime_dir / "tray.lock")
    if not instance.acquire():
        return 0
    source = TrayStatusFile(status_path or runtime_dir / "tray-status.json")

    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QAction, QIcon
    from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

    app = QApplication.instance() or QApplication(["updatarr-tray"])
    app.setQuitOnLastWindowClosed(False)
    base_icon = QIcon.fromTheme("updatarr")

    current = status or TrayStatus.from_overview(source.read() or {"snapshot": None, "summary": {}})
    previous = current
    settings_file = TrayPreferencesFile(preferences_path or default_tray_preferences_path())
    preferences = settings_file.read()
    last_notification_at = time.monotonic()
    tray = QSystemTrayIcon(build_status_icon(current.icon_state, base_icon))
    menu = QMenu()
    heading = QAction(current.title)
    heading.setEnabled(False)
    menu.addAction(heading)
    menu.addSeparator()
    open_action = QAction("Open Updatarr")
    open_action.triggered.connect(lambda: webbrowser.open(url))
    menu.addAction(open_action)
    settings_action = QAction("Settings…")
    menu.addAction(settings_action)
    menu.addSeparator()
    quit_action = QAction("Quit tray")
    quit_action.triggered.connect(app.quit)
    menu.addAction(quit_action)
    tray.setContextMenu(menu)
    tray.activated.connect(lambda reason: webbrowser.open(url) if reason == QSystemTrayIcon.ActivationReason.Trigger else None)

    def refresh() -> None:
        nonlocal last_notification_at, previous
        latest = TrayStatus.from_overview(source.read() or {"snapshot": None, "summary": {}})
        tray.setIcon(build_status_icon(latest.icon_state, base_icon))
        tray.setToolTip(f"{latest.title}\n{latest.detail}")
        heading.setText(latest.title)
        now = time.monotonic()
        if should_notify(
            previous,
            latest,
            preferences,
            seconds_since_last_notification=now - last_notification_at,
        ):
            tray.showMessage(
                "Updatarr",
                latest.detail,
                QSystemTrayIcon.MessageIcon.Warning,
                preferences.notification_duration_seconds * 1000,
            )
            last_notification_at = now
        previous = latest

    refresh()
    timer = QTimer()
    timer.setInterval(preferences.refresh_seconds * 1000)
    timer.timeout.connect(refresh)
    timer.start()

    def open_settings() -> None:
        nonlocal preferences
        candidate = edit_tray_preferences(preferences)
        if candidate is None:
            return

        def apply_saved(saved: TrayPreferences) -> None:
            nonlocal preferences
            preferences = saved
            timer.setInterval(saved.refresh_seconds * 1000)

        error = save_tray_preferences(settings_file, candidate, apply_saved)
        if error:
            QMessageBox.warning(None, "Tray Settings Were Not Saved", error)

    settings_action.triggered.connect(open_settings)
    app.aboutToQuit.connect(instance.release)
    tray.show()
    return app.exec()


def main() -> None:
    base = os.environ.get("UPDATARR_URL_BASE", "").strip("/")
    suffix = f"/{base}/" if base else "/"
    url = os.environ.get("UPDATARR_PUBLIC_ORIGIN", "http://127.0.0.1:8788").rstrip("/") + suffix
    raise SystemExit(run_tray(url=url))


if __name__ == "__main__":
    main()
