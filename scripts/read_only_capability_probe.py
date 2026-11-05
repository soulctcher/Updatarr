#!/usr/bin/env python3
"""Collect local capability evidence without refreshing or changing update state.

The command surface is deliberately closed: callers select a named probe and
cannot supply executable names or arguments. Output is written to stdout so a
person can review it before deciding whether it is suitable as a fixture.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import re
import selectors
import socket
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final


SCHEMA_VERSION: Final = 1
DEFAULT_TIMEOUT_SECONDS: Final = 15
MAX_OUTPUT_BYTES: Final = 1_000_000
UID_MAP_PATH: Final = Path("/proc/self/uid_map")
OVERFLOW_UID_PATH: Final = Path("/proc/sys/kernel/overflowuid")
UUID_PATTERN: Final = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
LOCAL_ID_PATTERN: Final = re.compile(r"\b[0-9a-fA-F]{32}\b")
URL_CREDENTIAL_PATTERN: Final = re.compile(r"([a-z][a-z0-9+.-]*://)[^/@\s]+@", re.IGNORECASE)
SECRET_QUERY_PATTERN: Final = re.compile(
    r"([?&](?:access_?token|api_?key|key|password|secret|token)=)[^&\s]+",
    re.IGNORECASE,
)
SENSITIVE_JSON_KEYS: Final = {
    "checksum",
    "checksums",
    "compositeid",
    "deviceid",
    "guid",
    "instanceids",
    "parentdeviceid",
    "serial",
}
PASSTHROUGH_ENVIRONMENT: Final = {
    "CARGO_HOME",
    "DBUS_SESSION_BUS_ADDRESS",
    "FNM_DIR",
    "HOME",
    "RUSTUP_HOME",
    "UV_TOOL_BIN_DIR",
    "UV_TOOL_DIR",
    "XDG_CACHE_HOME",
    "XDG_CONFIG_HOME",
    "XDG_DATA_HOME",
    "XDG_RUNTIME_DIR",
    "XDG_STATE_HOME",
}


@dataclass(frozen=True)
class Probe:
    probe_id: str
    argv: tuple[str, ...]
    purpose: str
    expires_after_hours: int
    required_path: str | None = None
    max_records: int | None = None
    accepted_exit_codes: tuple[int, ...] = (0,)


@dataclass(frozen=True)
class TrustedExecutable:
    path: Path
    pacman_owner: str | None
    allow_unowned_user_file: bool = False


TRUSTED_EXECUTABLES: Final = {
    "bootctl": TrustedExecutable(Path("/usr/bin/bootctl"), "systemd"),
    "checkupdates": TrustedExecutable(Path("/usr/bin/checkupdates"), "pacman-contrib"),
    "cargo": TrustedExecutable(Path("/usr/bin/cargo"), "rustup"),
    "dkms": TrustedExecutable(Path("/usr/bin/dkms"), "dkms"),
    "eos-update": TrustedExecutable(Path("/usr/bin/eos-update"), "eos-update"),
    "find": TrustedExecutable(Path("/usr/bin/find"), "findutils"),
    "findmnt": TrustedExecutable(Path("/usr/bin/findmnt"), "util-linux"),
    "flatpak": TrustedExecutable(Path("/usr/bin/flatpak"), "flatpak"),
    "fnm": TrustedExecutable(Path("/usr/bin/fnm"), "fnm-bin"),
    "fwupdmgr": TrustedExecutable(Path("/usr/bin/fwupdmgr"), "fwupd"),
    "npm": TrustedExecutable(Path("/usr/bin/npm"), "npm"),
    "pacman": TrustedExecutable(Path("/usr/bin/pacman"), "pacman"),
    "rustup": TrustedExecutable(Path("/usr/bin/rustup"), "rustup"),
    "systemd-run": TrustedExecutable(Path("/usr/bin/systemd-run"), "systemd"),
    "env": TrustedExecutable(Path("/usr/bin/env"), "coreutils"),
    "uname": TrustedExecutable(Path("/usr/bin/uname"), "coreutils"),
    "uv": TrustedExecutable(Path.home() / ".local" / "bin" / "uv", None, True),
    "yay": TrustedExecutable(Path("/usr/bin/yay"), "yay"),
}


PROBES: Final[tuple[Probe, ...]] = (
    Probe("pacman-version", ("pacman", "--version"), "Native package tool version", 168),
    Probe("pacman-installed", ("pacman", "-Q"), "Installed native packages", 24),
    Probe("pacman-foreign", ("pacman", "-Qm"), "Packages absent from configured sync databases", 24),
    Probe(
        "native-updates",
        ("checkupdates", "--nocolor"),
        "Available native updates using a separate temporary package database",
        1,
        accepted_exit_codes=(0, 2),
    ),
    Probe("yay-version", ("yay", "--version"), "AUR helper version", 168),
    Probe(
        "aur-updates",
        ("yay", "-Qua", "--aur", "--color", "never"),
        "Available AUR updates without starting an upgrade",
        1,
    ),
    Probe("eos-update-help", ("eos-update", "--help"), "Installed updater capabilities", 168),
    Probe("flatpak-version", ("flatpak", "--version"), "Flatpak version", 168),
    Probe(
        "flatpak-user-apps",
        ("flatpak", "list", "--user", "--app", "--columns=ref,origin,installation,active,size,options"),
        "User Flatpak application identities",
        24,
    ),
    Probe(
        "flatpak-system-apps",
        ("flatpak", "list", "--system", "--app", "--columns=ref,origin,installation,active,size,options"),
        "System Flatpak application identities",
        24,
    ),
    Probe(
        "flatpak-user-remotes",
        ("flatpak", "remotes", "--user", "--show-disabled", "--columns=name,url,collection,filter,priority,options"),
        "Configured user Flatpak remotes and enabled state",
        24,
    ),
    Probe(
        "flatpak-system-remotes",
        ("flatpak", "remotes", "--system", "--show-disabled", "--columns=name,url,collection,filter,priority,options"),
        "Configured system Flatpak remotes and enabled state",
        24,
    ),
    Probe(
        "flatpak-user-masks",
        ("flatpak", "mask", "--user"),
        "Existing user Flatpak update masks",
        24,
    ),
    Probe(
        "flatpak-system-masks",
        ("flatpak", "mask", "--system"),
        "Existing system Flatpak update masks",
        24,
    ),
    Probe(
        "flatpak-user-history",
        ("flatpak", "history", "--user", "--json"),
        "Recorded user Flatpak activity from the local journal",
        24,
    ),
    Probe(
        "flatpak-system-history",
        ("flatpak", "history", "--system", "--json"),
        "Recorded system Flatpak activity from the local journal",
        24,
    ),
    Probe("fwupd-version", ("fwupdmgr", "--version"), "Firmware tool and daemon versions", 168),
    Probe(
        "fwupd-devices",
        ("fwupdmgr", "get-devices", "--json", "--no-metadata-check", "--no-remote-check", "--no-unreported-check"),
        "Locally known firmware-capable devices without refreshing metadata",
        24,
    ),
    Probe("rustup-toolchains", ("rustup", "toolchain", "list"), "Installed Rust toolchains", 24),
    Probe("cargo-tools", ("cargo", "install", "--list"), "Cargo-installed tools", 24),
    Probe("fnm-versions", ("fnm", "list"), "Installed fnm Node versions", 24),
    Probe("npm-root", ("npm", "root", "--global"), "Global npm installation root", 24),
    Probe("npm-globals", ("npm", "ls", "--global", "--depth=0", "--json"), "Global npm packages", 24),
    Probe(
        "uv-tools",
        ("uv", "--offline", "--no-python-downloads", "--no-config", "tool", "list"),
        "Tools registered with uv, without network, downloads or project configuration",
        24,
    ),
    Probe("dkms-status", ("dkms", "status"), "Installed DKMS module state", 24),
    Probe("kernel-release", ("uname", "--kernel-release"), "Running kernel release", 24),
    Probe(
        "kernel-modules",
        ("find", "/usr/lib/modules", "-mindepth", "1", "-maxdepth", "1", "-type", "d", "-printf", "%f\\n"),
        "Installed kernel module trees",
        24,
    ),
    Probe("boot-status", ("bootctl", "status", "--no-pager"), "Boot loader and current boot entry", 24),
    Probe("root-filesystem", ("findmnt", "--json", "--output", "TARGET,FSTYPE,OPTIONS", "/"), "Root filesystem type", 24),
    Probe(
        "rollback-tools",
        ("pacman", "-Q", "btrfs-progs", "snapper", "timeshift"),
        "Installed snapshot prerequisites; a tool is not proof of working rollback",
        24,
    ),
    Probe(
        "appimages-applications",
        ("find", str(Path.home() / "Applications"), "-xdev", "-maxdepth", "3", "-type", "f", "-iname", "*.AppImage", "-print0"),
        "Standalone AppImage candidates in the configured Applications path",
        24,
        str(Path.home() / "Applications"),
        100,
    ),
    Probe(
        "appimages-local-bin",
        ("find", str(Path.home() / ".local" / "bin"), "-xdev", "-maxdepth", "2", "-type", "f", "-iname", "*.AppImage", "-print0"),
        "Standalone AppImage candidates in the configured local binary path",
        24,
        str(Path.home() / ".local" / "bin"),
        100,
    ),
    Probe(
        "appimages-bin",
        ("find", str(Path.home() / "bin"), "-xdev", "-maxdepth", "2", "-type", "f", "-iname", "*.AppImage", "-print0"),
        "Standalone AppImage candidates in the configured user binary path",
        24,
        str(Path.home() / "bin"),
        100,
    ),
)

PROBES_BY_ID: Final = {probe.probe_id: probe for probe in PROBES}

# These fragments must never appear in an allowlisted command. The check is an
# additional tripwire; the closed registry above remains the primary control.
FORBIDDEN_ARGUMENTS: Final = {
    "-S",
    "-R",
    "-U",
    "--clean",
    "--delete",
    "--disable-remote",
    "--enable-remote",
    "--install",
    "--refresh",
    "--remove",
    "--save",
    "--self-update",
    "--sync",
    "--update",
    "--upgrade",
    "clean",
    "delete",
    "disable-remote",
    "enable-remote",
    "install",
    "refresh",
    "remove",
    "self-update",
    "sync",
    "update",
    "upgrade",
}


def validate_registry() -> None:
    """Reject duplicate, shell-driven, privileged or mutating probe entries."""

    if len(PROBES_BY_ID) != len(PROBES):
        raise ValueError("probe identifiers must be unique")
    for probe in PROBES:
        if not probe.argv or not probe.probe_id:
            raise ValueError("every probe needs an identifier and command")
        if probe.argv[0] in {"bash", "sh", "sudo", "doas", "pkexec"}:
            raise ValueError(f"unsafe executable in {probe.probe_id}")
        if probe.argv[0] not in TRUSTED_EXECUTABLES:
            raise ValueError(f"untrusted executable in {probe.probe_id}")
        blocked = FORBIDDEN_ARGUMENTS.intersection(probe.argv[1:])
        if probe.argv == ("cargo", "install", "--list"):
            blocked = blocked.difference({"install"})
        if blocked:
            raise ValueError(f"mutating argument in {probe.probe_id}: {sorted(blocked)}")


def _sanitize_plain(text: str) -> str:
    sanitized = text.replace(str(Path.home()), "$HOME")
    for value, replacement in (
        (getpass.getuser(), "$USER"),
        (socket.gethostname(), "$HOST"),
    ):
        if value:
            sanitized = re.sub(
                rf"(?<![A-Za-z0-9_.-]){re.escape(value)}(?![A-Za-z0-9_.-])",
                replacement,
                sanitized,
            )
    sanitized = URL_CREDENTIAL_PATTERN.sub(r"\1$CREDENTIALS@", sanitized)
    sanitized = SECRET_QUERY_PATTERN.sub(r"\1$REDACTED", sanitized)
    sanitized = UUID_PATTERN.sub("$UUID", sanitized)
    return LOCAL_ID_PATTERN.sub("$LOCAL_ID", sanitized)


def _redact_json(value):
    if isinstance(value, dict):
        return {
            key: "$REDACTED" if key.lower() in SENSITIVE_JSON_KEYS else _redact_json(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_json(item) for item in value]
    if isinstance(value, str):
        return _sanitize_plain(value)
    return value


def sanitize(text: str) -> str:
    """Remove local identity, credentials and stable device identifiers."""

    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return _sanitize_plain(text)
    suffix = "\n" if text.endswith("\n") else ""
    return json.dumps(_redact_json(parsed), indent=2, sort_keys=True) + suffix


def _pseudonym(value) -> str:
    canonical = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "$ID_" + hashlib.sha256(canonical.encode()).hexdigest()[:20]


def _application_safe_json(value, *, sensitive: bool = False):
    """Keep stable one-way identity while removing raw host identifiers."""
    if sensitive:
        return _pseudonym(value)
    if isinstance(value, dict):
        return {
            key: _application_safe_json(item, sensitive=key.lower() in SENSITIVE_JSON_KEYS)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_application_safe_json(item) for item in value]
    if isinstance(value, str):
        return _sanitize_plain(value)
    return value


def sanitize_for_application(text: str) -> str:
    """Sanitize output while retaining pseudonymous inventory identity."""
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return _sanitize_plain(text)
    suffix = "\n" if text.endswith("\n") else ""
    return json.dumps(_application_safe_json(parsed), indent=2, sort_keys=True) + suffix


def probe_environment() -> dict[str, str]:
    """Pass only local-state paths required by the inspected tools."""

    environment = {
        key: value for key, value in os.environ.items() if key in PASSTHROUGH_ENVIRONMENT
    }
    environment.update(
        {
            "LANG": "C",
            "LC_ALL": "C",
            "NO_COLOR": "1",
            "PAGER": "cat",
            "SYSTEMD_PAGER": "cat",
            "PATH": "/usr/bin",
        }
    )
    return environment


def root_owner_is_safe(metadata: os.stat_result) -> bool:
    """Recognize host root after a per-user service maps it to overflow UID."""

    if metadata.st_uid == 0:
        return True
    try:
        overflow_uid = int(OVERFLOW_UID_PATH.read_text(encoding="ascii").strip())
        mappings = [
            tuple(int(value) for value in line.split())
            for line in UID_MAP_PATH.read_text(encoding="ascii").splitlines()
            if line.strip()
        ]
    except (FileNotFoundError, OSError, UnicodeError, ValueError):
        return False
    if metadata.st_uid != overflow_uid or not mappings:
        return False
    # If host UID 0 is mapped, stat() must report that mapped value rather than
    # the overflow UID. Accept overflow only when root is demonstrably absent.
    return not any(outside <= 0 < outside + length for _inside, outside, length in mappings)


def system_executable_is_safe(path: Path, metadata: os.stat_result) -> bool:
    """Validate fixed /usr/bin files without weakening the user namespace."""

    if path.parent != Path("/usr/bin") or metadata.st_mode & 0o022:
        return False
    if not root_owner_is_safe(metadata):
        return False
    try:
        resolved = path.resolve(strict=True)
        system_root = Path("/usr")
        if not resolved.is_relative_to(system_root):
            return False
        parents = {system_root, Path("/usr/bin")}
        parent = resolved.parent
        while parent != system_root:
            parents.add(parent)
            parent = parent.parent
        for parent in parents:
            parent_metadata = parent.stat()
            if (not parent.is_dir() or parent.is_symlink()
                    or parent_metadata.st_mode & 0o022
                    or not root_owner_is_safe(parent_metadata)):
                return False
    except OSError:
        return False
    return not os.access(path, os.W_OK, effective_ids=True)


def pacman_owner(executable: str) -> str | None:
    """Return the package owning an executable, without changing pacman state."""

    pacman = TRUSTED_EXECUTABLES["pacman"].path
    try:
        metadata = pacman.stat()
    except FileNotFoundError:
        return None
    if not system_executable_is_safe(pacman, metadata):
        return None
    try:
        result = subprocess.run(
            (str(pacman), "-Qqo", executable),
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
            env=probe_environment(),
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def trusted_executable(name: str) -> tuple[Path | None, str | None, str | None]:
    """Resolve one exact executable and reject unexpected owner or permissions."""

    policy = TRUSTED_EXECUTABLES[name]
    path = policy.path
    try:
        link_metadata = path.lstat()
        metadata = path.stat()
    except FileNotFoundError:
        return None, None, "expected executable is absent"
    if path.is_symlink():
        if policy.allow_unowned_user_file:
            return None, None, "unowned executable may not be a symbolic link"
        if not root_owner_is_safe(link_metadata):
            return None, None, "executable link owner is unsafe"
    owner_is_safe = (
        metadata.st_uid == os.getuid() and not metadata.st_mode & 0o022
        if policy.allow_unowned_user_file
        else system_executable_is_safe(path, metadata)
    )
    if not owner_is_safe:
        return None, None, "executable ownership or write permissions are unsafe"
    if not path.is_symlink() and link_metadata.st_mode & 0o022:
        return None, None, "executable link is group- or world-writable"
    owner = pacman_owner(str(path))
    if owner != policy.pacman_owner:
        return None, owner, "executable package owner does not match policy"
    return path, owner, None


@dataclass(frozen=True)
class BoundedResult:
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool
    output_truncated: bool


def run_bounded(
    argv: tuple[str, ...],
    timeout_seconds: int,
    *,
    max_records: int | None = None,
) -> BoundedResult:
    """Run a trusted command while bounding time, bytes and optional NUL records."""

    process = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=probe_environment(),
        shell=False,
    )
    assert process.stdout is not None and process.stderr is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    deadline = time.monotonic() + timeout_seconds
    timed_out = False
    output_truncated = False
    stdout_records = 0

    while selector.get_map():
        remaining_time = deadline - time.monotonic()
        if remaining_time <= 0:
            timed_out = True
            process.kill()
            break
        events = selector.select(min(0.2, remaining_time))
        for key, _mask in events:
            chunk = os.read(key.fileobj.fileno(), 65_536)
            if not chunk:
                selector.unregister(key.fileobj)
                continue
            remaining_bytes = MAX_OUTPUT_BYTES - sum(len(value) for value in buffers.values())
            if remaining_bytes <= 0:
                output_truncated = True
                process.kill()
                break
            accepted = chunk[:remaining_bytes]
            if key.data == "stdout" and max_records is not None:
                allowed_records = max_records - stdout_records
                positions = [index for index, byte in enumerate(accepted) if byte == 0]
                if len(positions) > allowed_records:
                    accepted = accepted[: positions[allowed_records - 1] + 1] if allowed_records else b""
                    output_truncated = True
                    process.kill()
                stdout_records += accepted.count(b"\0")
                if stdout_records >= max_records:
                    output_truncated = True
                    process.kill()
            buffers[key.data].extend(accepted)
            if len(chunk) > len(accepted):
                output_truncated = True
                process.kill()
            if output_truncated:
                break
        if timed_out or output_truncated:
            break

    if process.poll() is None:
        process.kill()
    process.wait(timeout=2)
    selector.close()
    return BoundedResult(
        exit_code=None if timed_out else process.returncode,
        stdout=bytes(buffers["stdout"]).decode("utf-8", errors="replace"),
        stderr=bytes(buffers["stderr"]).decode("utf-8", errors="replace"),
        timed_out=timed_out,
        output_truncated=output_truncated,
    )


def run_probe(
    probe: Probe,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    *,
    application_safe: bool = False,
) -> dict:
    executable, executable_owner, trust_error = trusted_executable(probe.argv[0])
    base = {
        "probe_id": probe.probe_id,
        "purpose": probe.purpose,
        "expires_after_hours": probe.expires_after_hours,
        "argv": [sanitize(part) for part in probe.argv],
        "output_format": (
            "json"
            if "--json" in probe.argv
            else "tsv"
            if any(argument.startswith("--columns=") for argument in probe.argv)
            else "text"
        ),
        "requires_privilege": False,
    }
    if executable is None:
        return {
            **base,
            "state": "not_available",
            "executable_path": None,
            "executable_owner": None,
            "trust_error": trust_error,
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "output_truncated": False,
        }

    if probe.required_path is not None and not Path(probe.required_path).is_dir():
        return {
            **base,
            "state": "not_available",
            "executable_path": sanitize(str(executable)),
            "executable_owner": executable_owner,
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "output_truncated": False,
        }

    base.update(
        {
            "executable_path": sanitize(str(executable)),
            "executable_owner": executable_owner,
            "trust_exception": "known unowned user tool" if probe.argv[0] == "uv" else None,
        }
    )

    argv = (str(executable), *probe.argv[1:])
    if probe.probe_id == "native-updates":
        systemd_run, _systemd_owner, systemd_error = trusted_executable("systemd-run")
        env_tool, _env_owner, env_error = trusted_executable("env")
        if systemd_run is None or env_tool is None:
            return {
                **base,
                "state": "not_available",
                "exit_code": None,
                "stdout": "",
                "stderr": "",
                "output_truncated": False,
                "trust_error": systemd_error or env_error,
            }
        home = Path.home()
        argv = (
            str(systemd_run),
            "--user",
            "--wait",
            "--pipe",
            "--collect",
            "--quiet",
            "--property=PrivateTmp=false",
            "--property=NoNewPrivileges=true",
            "--property=UMask=0077",
            "--",
            str(env_tool),
            "-i",
            f"HOME={home}",
            "PATH=/usr/bin",
            "LANG=C",
            "LC_ALL=C",
            "NO_COLOR=1",
            f"CHECKUPDATES_DB=/tmp/updatarr-checkup-db-{os.getuid()}",
            str(executable),
            *probe.argv[1:],
        )

    result = run_bounded(
        argv,
        timeout_seconds,
        max_records=probe.max_records,
    )
    sanitizer = sanitize_for_application if application_safe else sanitize
    stdout = sanitizer(result.stdout)
    stderr = sanitizer(result.stderr)
    if result.timed_out:
        return {
            **base,
            "state": "timed_out",
            "exit_code": None,
            "stdout": stdout,
            "stderr": stderr,
            "output_truncated": result.output_truncated,
        }

    return {
        **base,
        "state": "completed" if result.exit_code in probe.accepted_exit_codes else "error",
        "exit_code": result.exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "output_truncated": result.output_truncated,
    }


def build_report(probe_ids: list[str], timeout_seconds: int) -> dict:
    validate_registry()
    selected = [PROBES_BY_ID[probe_id] for probe_id in probe_ids]
    return {
        "schema_version": SCHEMA_VERSION,
        "captured_at": datetime.now(UTC).isoformat(),
        "read_only": True,
        "results": [run_probe(probe, timeout_seconds) for probe in selected],
    }


def build_application_report(probe_ids: list[str], timeout_seconds: int) -> dict:
    """Build an internal report with pseudonymous, non-exportable identities."""
    validate_registry()
    selected = [PROBES_BY_ID[probe_id] for probe_id in probe_ids]
    return {
        "schema_version": SCHEMA_VERSION,
        "captured_at": datetime.now(UTC).isoformat(),
        "read_only": True,
        "application_safe": True,
        "results": [run_probe(probe, timeout_seconds, application_safe=True) for probe in selected],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--probe",
        action="append",
        choices=sorted(PROBES_BY_ID),
        dest="probe_ids",
        help="Named allowlisted probe; repeat to select more than one",
    )
    parser.add_argument("--list", action="store_true", help="List probes without running them")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    return parser.parse_args()


def public_probe_list() -> list[dict]:
    return [
        {
            "probe_id": probe.probe_id,
            "argv": [sanitize(part) for part in probe.argv],
            "purpose": probe.purpose,
            "expires_after_hours": probe.expires_after_hours,
            "required_path": sanitize(probe.required_path) if probe.required_path else None,
            "max_records": probe.max_records,
        }
        for probe in PROBES
    ]


def main() -> int:
    args = parse_args()
    validate_registry()
    if args.list:
        print(json.dumps(public_probe_list(), indent=2))
        return 0
    if args.timeout < 1 or args.timeout > 60:
        raise SystemExit("--timeout must be between 1 and 60 seconds")
    report = build_report(args.probe_ids or [probe.probe_id for probe in PROBES], args.timeout)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
