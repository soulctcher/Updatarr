"""Thin KDE tray for the shared overview contract.

The tray owns no update policy. Its model consumes the same overview document
as the browser, and the Qt shell only opens the canonical loopback interface.
It reads a restricted status document written by the service and is never
started automatically by package installation.
"""

from __future__ import annotations

from dataclasses import dataclass
import fcntl
import os
from pathlib import Path
import webbrowser

from .tray_status import TrayStatusFile


@dataclass(frozen=True)
class TrayStatus:
    title: str
    detail: str
    attention: bool

    @classmethod
    def from_overview(cls, payload: dict) -> "TrayStatus":
        summary = payload.get("summary", {})
        updates = int(summary.get("updates_found", 0))
        ready = int(summary.get("ready_to_review", updates))
        blocked = int(summary.get("blocked", 0))
        snapshot = payload.get("snapshot")
        if snapshot is None:
            return cls("Updatarr — Not checked", "Open Updatarr to check software.", False)
        if blocked:
            return cls(
                f"Updatarr — {blocked} blocked",
                f"{ready} ready to review; open Updatarr to review what is blocked.",
                True,
            )
        if ready:
            return cls(f"Updatarr — {ready} ready to review", "Open Updatarr to review them.", True)
        return cls("Updatarr — No updates recorded", "The latest recorded check found no updates.", False)


def should_notify(previous: TrayStatus, current: TrayStatus) -> bool:
    """Notify only when a new attention state appears or materially changes."""
    return current.attention and current != previous


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


def run_tray(
    status: TrayStatus | None = None,
    url: str = "http://127.0.0.1:8788",
    *,
    status_path: Path | None = None,
    lock_path: Path | None = None,
) -> int:
    """Run the opt-in tray; refuse root and a second tray instance."""
    if os.geteuid() == 0:
        raise RuntimeError("The Updatarr tray must not run as root.")
    runtime_dir = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "updatarr"
    instance = TrayInstanceLock(lock_path or runtime_dir / "tray.lock")
    if not instance.acquire():
        return 0
    source = TrayStatusFile(status_path or runtime_dir / "tray-status.json")

    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
    from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

    app = QApplication.instance() or QApplication(["updatarr-tray"])
    app.setQuitOnLastWindowClosed(False)
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#6D28D9"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(2, 2, 28, 28, 7, 7)
    painter.setPen(QColor("#FFFFFF"))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "U")
    painter.end()

    icon = QIcon.fromTheme("updatarr")
    tray = QSystemTrayIcon(icon if not icon.isNull() else QIcon(pixmap))
    current = status or TrayStatus.from_overview(source.read() or {"snapshot": None, "summary": {}})
    previous = current
    menu = QMenu()
    heading = QAction(current.title)
    heading.setEnabled(False)
    menu.addAction(heading)
    menu.addSeparator()
    open_action = QAction("Open Updatarr")
    open_action.triggered.connect(lambda: webbrowser.open(url))
    menu.addAction(open_action)
    quit_action = QAction("Quit tray")
    quit_action.triggered.connect(app.quit)
    menu.addAction(quit_action)
    tray.setContextMenu(menu)
    tray.activated.connect(lambda reason: webbrowser.open(url) if reason == QSystemTrayIcon.ActivationReason.Trigger else None)

    def refresh() -> None:
        nonlocal previous
        latest = TrayStatus.from_overview(source.read() or {"snapshot": None, "summary": {}})
        tray.setToolTip(f"{latest.title}\n{latest.detail}")
        heading.setText(latest.title)
        if should_notify(previous, latest):
            tray.showMessage(
                "Updatarr",
                latest.detail,
                QSystemTrayIcon.MessageIcon.Warning,
                8000,
            )
        previous = latest

    refresh()
    timer = QTimer()
    timer.setInterval(5000)
    timer.timeout.connect(refresh)
    timer.start()
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
