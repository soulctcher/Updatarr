"""Validated, owner-only preferences for the unprivileged desktop tray."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
import json
import os
from pathlib import Path
import tempfile


class NotificationBehavior(StrEnum):
    """The limited times when the tray may show a desktop message."""

    WHEN_STATUS_CHANGES = "when_status_changes"
    WHEN_UPDATES_APPEAR = "when_updates_appear"
    NEVER = "never"


@dataclass(frozen=True)
class TrayPreferences:
    """The complete, deliberately small tray preference contract."""

    refresh_seconds: int = 5
    notification_behavior: NotificationBehavior = NotificationBehavior.WHEN_STATUS_CHANGES
    notification_duration_seconds: int = 8
    reminder_minutes: int = 0

    _ALLOWED_REFRESH_SECONDS = frozenset({5, 15, 30, 60})
    _ALLOWED_DURATION_SECONDS = frozenset({5, 8, 12})
    _ALLOWED_REMINDER_MINUTES = frozenset({0, 60, 240, 1440})

    @classmethod
    def from_payload(cls, payload: object) -> "TrayPreferences":
        if not isinstance(payload, dict):
            return cls()
        try:
            refresh = int(payload["refresh_seconds"])
            duration = int(payload["notification_duration_seconds"])
            behavior = NotificationBehavior(payload["notification_behavior"])
            reminder = int(payload.get("reminder_minutes", 0))
        except (KeyError, TypeError, ValueError):
            return cls()
        if refresh not in cls._ALLOWED_REFRESH_SECONDS:
            return cls()
        if duration not in cls._ALLOWED_DURATION_SECONDS:
            return cls()
        if reminder not in cls._ALLOWED_REMINDER_MINUTES:
            return cls()
        return cls(refresh, behavior, duration, reminder)

    def to_payload(self) -> dict[str, object]:
        payload = asdict(self)
        payload["notification_behavior"] = self.notification_behavior.value
        return payload


class TrayPreferencesFile:
    """Read and atomically replace one user's validated tray preferences."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> TrayPreferences:
        try:
            if self.path.is_symlink() or self.path.stat().st_mode & 0o077:
                return TrayPreferences()
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return TrayPreferences()
        return TrayPreferences.from_payload(payload)

    def write(self, preferences: TrayPreferences) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.path.parent, 0o700)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", dir=self.path.parent
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(preferences.to_payload(), stream, indent=2, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary_path, 0o600)
            os.replace(temporary_path, self.path)
        finally:
            temporary_path.unlink(missing_ok=True)


def default_tray_preferences_path() -> Path:
    config_root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return config_root / "updatarr" / "tray-settings.json"
