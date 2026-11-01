"""Defensive parsers for untrusted update-source output."""

from __future__ import annotations

import json
import re
from typing import Any
import unicodedata

from ..domain import DetectedUpdate, SoftwareRecord, SourceState, stable_software_id


CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
MAX_FIELD_LENGTH = 1024


class ProviderOutputError(ValueError):
    pass


def clean(value: Any) -> str:
    text = CONTROL_CHARACTERS.sub("", str(value))
    # Remove format controls too, including bidirectional overrides and
    # zero-width characters that can make hostile metadata look trustworthy.
    text = "".join(character for character in text if unicodedata.category(character) != "Cf").strip()
    return text[:MAX_FIELD_LENGTH]


def parse_pacman_packages(text: str, foreign_names: set[str] | None = None) -> tuple[SoftwareRecord, ...]:
    foreign_names = foreign_names or set()
    records: list[SoftwareRecord] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = clean(raw)
        if not line:
            continue
        try:
            name, version = line.rsplit(maxsplit=1)
        except ValueError as error:
            raise ProviderOutputError(f"invalid native package row {number}") from error
        if not name or not version:
            raise ProviderOutputError(f"invalid native package row {number}")
        records.append(SoftwareRecord(
            source_id="native", scope="system", software_id=name, name=name,
            installed_version=version, origin=None,
            ownership="foreign_unresolved" if name in foreign_names else "native_repository",
        ))
    return tuple(records)


def parse_package_updates(text: str, source_id: str, scope: str) -> tuple[DetectedUpdate, ...]:
    """Parse pacman/yay `name installed -> available` output as inert data."""
    updates: list[DetectedUpdate] = []
    seen: set[str] = set()
    for number, raw in enumerate(text.splitlines(), start=1):
        line = clean(raw)
        if not line:
            continue
        parts = line.split()
        valid_age = (
            source_id == "aur"
            and len(parts) == 5
            and re.fullmatch(r"\[(?:[0-9]+[smhdw])+\]", parts[4]) is not None
        )
        if (len(parts) != 4 and not valid_age) or parts[2] != "->":
            raise ProviderOutputError(f"invalid {source_id} update row {number}")
        name, installed, _, available = parts[:4]
        if not name or not installed or not available or name in seen:
            raise ProviderOutputError(f"invalid {source_id} update row {number}")
        seen.add(name)
        updates.append(DetectedUpdate(
            stable_id=stable_software_id(source_id, scope, name, "aur" if source_id == "aur" else None),
            source_id=source_id,
            scope=scope,
            software_id=name,
            name=name,
            installed_version=installed,
            available_version=available,
            state=SourceState.READY_TO_REVIEW,
            summary=(
                "AUR reports a newer version. Review its build files before planning this update."
                if source_id == "aur"
                else "A newer system package version is available."
            ),
        ))
    return tuple(updates)


def parse_flatpak_apps(text: str, scope: str) -> tuple[SoftwareRecord, ...]:
    records: list[SoftwareRecord] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip():
            continue
        columns = [clean(value) for value in raw.split("\t")]
        if len(columns) < 6:
            raise ProviderOutputError(f"invalid Flatpak row {number}")
        ref, origin, reported_scope, commit, size, options = columns[:6]
        parts = ref.split("/")
        if len(parts) != 3 or reported_scope not in {scope, ""}:
            raise ProviderOutputError(f"invalid Flatpak identity on row {number}")
        app_id, architecture, branch = parts
        records.append(SoftwareRecord(
            source_id="flatpak", scope=scope, software_id=ref, name=app_id,
            installed_version=commit or None, origin=origin or None,
            architecture=architecture, branch=branch,
            details={"size": size, "options": options},
        ))
    return tuple(records)


def parse_flatpak_settings(remotes_text: str, masks_text: str) -> dict[str, list[str]]:
    """Read existing provider settings without treating them as Updatarr choices."""

    disabled_remotes: list[str] = []
    for number, raw in enumerate(remotes_text.splitlines(), start=1):
        if not raw.strip():
            continue
        columns = [clean(value) for value in raw.split("\t")]
        if len(columns) < 2 or not columns[0]:
            raise ProviderOutputError(f"invalid Flatpak remote row {number}")
        if any("disabled" in value.split(",") for value in columns[1:]):
            disabled_remotes.append(columns[0])
    masks = [clean(line) for line in masks_text.splitlines() if clean(line)]
    return {"disabled_remotes": disabled_remotes, "masks": masks}


def parse_firmware_devices(text: str) -> tuple[SoftwareRecord, ...]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise ProviderOutputError("firmware output is not valid JSON") from error
    devices = payload.get("Devices") if isinstance(payload, dict) else None
    if not isinstance(devices, list):
        raise ProviderOutputError("firmware output has no device list")
    records: list[SoftwareRecord] = []
    for index, device in enumerate(devices):
        if not isinstance(device, dict):
            raise ProviderOutputError("firmware device is not an object")
        name = clean(device.get("Name", "Unnamed firmware device"))
        identity = clean(device.get("DeviceId") or f"redacted-device-{index}")
        records.append(SoftwareRecord(
            source_id="firmware", scope="system", software_id=identity, name=name,
            installed_version=clean(device.get("Version")) or None,
            origin=clean(device.get("Plugin")) or None,
            details={
                "updatable": "updatable" in device.get("Flags", []),
                "problems": [clean(value) for value in device.get("Problems", []) if value],
                "version_format": clean(device.get("VersionFormat")) or None,
            },
        ))
    return tuple(records)


def parse_rustup_toolchains(text: str) -> tuple[SoftwareRecord, ...]:
    records: list[SoftwareRecord] = []
    for raw in text.splitlines():
        line = clean(raw)
        if not line:
            continue
        toolchain = line.split(maxsplit=1)[0]
        records.append(SoftwareRecord(
            source_id="rustup", scope="user", software_id=toolchain, name=toolchain,
            installed_version=None, origin="rustup",
            details={"active": "active" in line, "default": "default" in line},
        ))
    return tuple(records)


def parse_cargo_tools(text: str) -> tuple[SoftwareRecord, ...]:
    records: list[SoftwareRecord] = []
    for raw in text.splitlines():
        line = clean(raw)
        if not line or raw[:1].isspace():
            continue
        match = re.fullmatch(r"([^\s]+) v([^:]+):", line)
        if match:
            name, version = match.groups()
            records.append(SoftwareRecord("cargo", "user", name, name, version, origin="cargo",
                                          ownership="unresolved",
                                          details={"install_root_checked": False, "source_checked": False}))
    return tuple(records)


def parse_fnm_versions(text: str) -> tuple[SoftwareRecord, ...]:
    records: list[SoftwareRecord] = []
    for raw in text.splitlines():
        line = clean(raw)
        if not line:
            continue
        version_match = re.search(r"v?(\d+(?:\.\d+){1,3})", line)
        if version_match:
            version = version_match.group(1)
            records.append(SoftwareRecord("fnm", "user", f"node-{version}", f"Node.js {version}",
                                          version, origin="fnm", ownership="user_tool",
                                          details={"default": "default" in line.lower(),
                                                   "active": "*" in line or "current" in line.lower()}))
    return tuple(records)


def parse_npm_globals(text: str, root: str) -> tuple[SoftwareRecord, ...]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise ProviderOutputError("global npm output is not valid JSON") from error
    dependencies = payload.get("dependencies") if isinstance(payload, dict) else None
    if not isinstance(dependencies, dict):
        raise ProviderOutputError("global npm output has no package list")
    records: list[SoftwareRecord] = []
    for name, value in sorted(dependencies.items())[:1000]:
        if not isinstance(value, dict):
            raise ProviderOutputError("a global npm package record is incomplete")
        clean_name = clean(name)
        if not clean_name:
            raise ProviderOutputError("a global npm package has no name")
        records.append(SoftwareRecord("npm", "system" if root.startswith("/usr/") else "user",
                                      clean_name, clean_name, clean(value.get("version")) or None,
                                      origin="npm", ownership="system_prefix" if root.startswith("/usr/") else "unresolved",
                                      details={"global_root": clean(root), "package_owner_checked": False}))
    return tuple(records)


def parse_uv_tools(text: str) -> tuple[SoftwareRecord, ...]:
    records: list[SoftwareRecord] = []
    for raw in text.splitlines():
        line = clean(raw)
        if not line or line.startswith("-") or raw[:1].isspace():
            continue
        match = re.match(r"([^\s]+)\s+v?([^\s]+)", line)
        if match:
            name, version = match.groups()
            records.append(SoftwareRecord("uv", "user", name, name, version, origin="uv",
                                          ownership="uv_registered",
                                          details={"uv_executable_provenance_checked": False}))
    return tuple(records)


def parse_appimage_paths(*texts: str) -> tuple[SoftwareRecord, ...]:
    records: list[SoftwareRecord] = []
    for text in texts:
        for raw in text.replace("\x00", "\n").splitlines():
            path = clean(raw)
            if not path:
                continue
            name = path.rsplit("/", 1)[-1]
            records.append(SoftwareRecord("appimage", "user", path, name, None, origin="local-file",
                                          ownership="unresolved",
                                          details={"path_recorded": True, "update_information_checked": False}))
    return tuple(records)
