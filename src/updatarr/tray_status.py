"""Restricted status handoff from the core service to the local tray."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any


class TrayStatusFile:
    def __init__(self, path: Path) -> None:
        self.path = path

    def write(self, payload: dict[str, Any]) -> None:
        document = {
            "version": 1,
            "snapshot": payload.get("snapshot"),
            "summary": payload.get("summary", {}),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.path.parent, 0o700)
        descriptor, temporary_name = tempfile.mkstemp(prefix=".tray-status-", dir=self.path.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(document, stream, separators=(",", ":"), sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, self.path)
        finally:
            temporary.unlink(missing_ok=True)

    def read(self) -> dict[str, Any] | None:
        try:
            if self.path.stat().st_mode & 0o077:
                return None
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(value, dict) or value.get("version") != 1:
            return None
        if not isinstance(value.get("summary"), dict):
            return None
        return value
