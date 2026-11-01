"""Open the configured Updatarr browser address without sourcing a shell file."""

from __future__ import annotations

import os
from pathlib import Path
import stat
from urllib.parse import urlparse
import webbrowser


def configured_url(config_path: Path | None = None) -> str:
    path = config_path or Path.home() / ".config" / "updatarr" / "updatarr.env"
    values: dict[str, str] = {}
    try:
        if stat.S_IMODE(path.stat().st_mode) & 0o077:
            raise ValueError("The Updatarr configuration must be readable only by its owner.")
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        lines = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in {"UPDATARR_PUBLIC_ORIGIN", "UPDATARR_URL_BASE"}:
            values[key] = value.strip()
    origin = values.get("UPDATARR_PUBLIC_ORIGIN", "http://127.0.0.1:8788").rstrip("/")
    parsed = urlparse(origin)
    if (
        parsed.scheme not in {"http", "https"} or not parsed.hostname
        or parsed.username or parsed.password or parsed.path not in {"", "/"}
        or parsed.query or parsed.fragment
    ):
        raise ValueError("The configured Updatarr browser address is not valid.")
    base = values.get("UPDATARR_URL_BASE", "").strip("/")
    if any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_/." for character in base):
        raise ValueError("The configured Updatarr URL prefix is not valid.")
    return origin + (f"/{base}/" if base else "/")


def main() -> None:
    if os.geteuid() == 0:
        raise SystemExit("Open Updatarr from the signed-in desktop user, not as root.")
    webbrowser.open(configured_url())
