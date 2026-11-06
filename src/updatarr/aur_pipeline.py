"""Attested host prerequisites for exact AUR package review.

The public Module exposes one read-only assessment. It accepts no command,
path, URL, package name, environment or caller-selected argument surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import json
from pathlib import Path
import re
import stat
import subprocess
from typing import Callable, Protocol


AUR_POLICY_VERSION = "updatarr-aur-host-prerequisites-v2"
ATTESTATION_PATH = Path("/var/lib/updatarr/aur/readiness.json")
EXPECTED_CLEAN_ROOT = "/var/lib/updatarr/aur/arch/root"
MAX_ATTESTATION_BYTES = 64 * 1024
REQUIRED_CHECKS = frozenset(
    {
        "tools_verified",
        "clean_root_canary_verified",
        "user_namespace_boundary_verified",
        "secret_isolation_canary_verified",
        "local_source_verification_canary_verified",
        "repository_dependency_canary_verified",
        "artifact_handoff_canary_verified",
    }
)
REQUIRED_TOOL_PACKAGES = frozenset(
    {"bubblewrap", "coreutils", "devtools", "git", "libarchive", "pacman", "python", "systemd", "util-linux"}
)
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _visible_root_owner_ids(uid_map: str, overflow_uid: int) -> frozenset[int]:
    """Return the file-owner IDs that can represent host root here.

    A user service with ``PrivateTmp=true`` runs in a user namespace that may
    leave host UID 0 unmapped. Linux then reports root-owned files with the
    configured overflow UID. Accept that representation only when the current
    namespace's UID map proves that inside UID 0 is not mapped.
    """
    root_is_mapped = False
    valid_mapping_seen = False
    for line in uid_map.splitlines():
        fields = line.split()
        if len(fields) != 3:
            continue
        try:
            inside_start, _outside_start, length = (int(value) for value in fields)
        except ValueError:
            continue
        valid_mapping_seen = True
        if length > 0 and inside_start <= 0 < inside_start + length:
            root_is_mapped = True
            break
    if not valid_mapping_seen or root_is_mapped:
        return frozenset({0})
    return frozenset({0, overflow_uid})


def _current_visible_root_owner_ids() -> frozenset[int]:
    try:
        uid_map = Path("/proc/self/uid_map").read_text(encoding="ascii")
        overflow_uid = int(
            Path("/proc/sys/kernel/overflowuid").read_text(encoding="ascii").strip()
        )
    except (OSError, UnicodeError, ValueError):
        return frozenset({0})
    return _visible_root_owner_ids(uid_map, overflow_uid)


@dataclass(frozen=True)
class AurPipelineReadiness:
    ready: bool
    explanation: str
    policy_version: str
    checked_at: str
    evidence_digest: str


class AurReadinessProvider(Protocol):
    def assess(self) -> AurPipelineReadiness: ...


class StaticAurPipeline:
    """Deterministic adapter for the simulator and interface-level tests."""

    def __init__(self, readiness: AurPipelineReadiness) -> None:
        self._readiness = readiness

    def assess(self) -> AurPipelineReadiness:
        return self._readiness


def simulator_aur_pipeline() -> StaticAurPipeline:
    return StaticAurPipeline(AurPipelineReadiness(
        True,
        "The deterministic simulator AUR pipeline is ready.",
        "simulator",
        datetime.now(UTC).isoformat(),
        "simulator",
    ))


class AttestedAurPipeline:
    """Validate one short-lived root-owned readiness record."""

    def __init__(self) -> None:
        self._path = ATTESTATION_PATH
        self._expected_owners = _current_visible_root_owner_ids()
        self._now: Callable[[], datetime] = lambda: datetime.now(UTC)
        self._package_versions: Callable[[], dict[str, str]] = self._current_package_versions

    @staticmethod
    def _current_package_versions() -> dict[str, str]:
        completed = subprocess.run(
            ("/usr/bin/pacman", "-Q", *sorted(REQUIRED_TOOL_PACKAGES)),
            env={"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin"},
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
        if completed.returncode != 0:
            raise OSError("The installed AUR prerequisite versions could not be read.")
        versions: dict[str, str] = {}
        for line in completed.stdout.splitlines():
            name, separator, version = line.partition(" ")
            if not separator or name not in REQUIRED_TOOL_PACKAGES or not version:
                raise OSError("The installed AUR prerequisite versions were incomplete.")
            versions[name] = version
        if set(versions) != REQUIRED_TOOL_PACKAGES:
            raise OSError("The installed AUR prerequisite versions were incomplete.")
        return versions

    @classmethod
    def _testing(
        cls,
        path: Path,
        *,
        expected_owner: int,
        now: Callable[[], datetime],
        package_versions: Callable[[], dict[str, str]],
    ) -> "AttestedAurPipeline":
        subject = cls()
        subject._path = path
        subject._expected_owners = frozenset({expected_owner})
        subject._now = now
        subject._package_versions = package_versions
        return subject

    def assess(self) -> AurPipelineReadiness:
        checked_at = self._now().astimezone(UTC).isoformat()

        def blocked(message: str) -> AurPipelineReadiness:
            return AurPipelineReadiness(
                False, message, AUR_POLICY_VERSION, checked_at, ""
            )

        try:
            metadata = self._path.lstat()
            if not stat.S_ISREG(metadata.st_mode) or self._path.is_symlink():
                return blocked("The AUR readiness record is not an ordinary file.")
            if metadata.st_uid not in self._expected_owners or metadata.st_mode & 0o022:
                return blocked("The AUR readiness record has unsafe ownership or permissions.")
            if metadata.st_size <= 0 or metadata.st_size > MAX_ATTESTATION_BYTES:
                return blocked("The AUR readiness record has an invalid size.")
            raw = self._path.read_bytes()
            document = json.loads(raw)
        except FileNotFoundError:
            return blocked("The AUR host prerequisites have not been prepared on this computer.")
        except (OSError, UnicodeError, json.JSONDecodeError):
            return blocked("The AUR readiness record could not be verified.")

        if not isinstance(document, dict):
            return blocked("The AUR readiness record has an invalid format.")
        digest = document.get("evidence_digest")
        unsigned = {key: value for key, value in document.items() if key != "evidence_digest"}
        canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":"))
        expected_digest = hashlib.sha256(canonical.encode()).hexdigest()
        if not isinstance(digest, str) or not hmac.compare_digest(digest, expected_digest):
            return blocked("The AUR readiness record changed after it was prepared.")
        if document.get("schema_version") != 1 or document.get("policy_version") != AUR_POLICY_VERSION:
            return blocked("The AUR readiness record uses an unsupported policy version.")
        if document.get("clean_root") != EXPECTED_CLEAN_ROOT:
            return blocked("The AUR clean build root does not match Updatarr's fixed location.")
        checks = document.get("checks")
        if not isinstance(checks, dict) or set(checks) != REQUIRED_CHECKS:
            return blocked("The AUR readiness record is missing required checks.")
        if not all(checks.get(name) is True for name in REQUIRED_CHECKS):
            return blocked("The complete AUR host-prerequisite check has not passed.")
        try:
            prepared_at = datetime.fromisoformat(str(document["prepared_at"])).astimezone(UTC)
            expires_at = datetime.fromisoformat(str(document["expires_at"])).astimezone(UTC)
        except (KeyError, TypeError, ValueError):
            return blocked("The AUR readiness time is invalid.")
        now = self._now().astimezone(UTC)
        if prepared_at > now + timedelta(minutes=5):
            return blocked("The AUR readiness record is dated in the future.")
        if expires_at <= now or expires_at - prepared_at > timedelta(days=7):
            return blocked("The AUR host-prerequisite check has expired.")
        tool_packages = document.get("tool_packages")
        if (
            not isinstance(tool_packages, dict)
            or set(tool_packages) != REQUIRED_TOOL_PACKAGES
            or not all(isinstance(value, str) and value for value in tool_packages.values())
        ):
            return blocked("The verified AUR prerequisite versions are missing.")
        artifact_digest = document.get("canary_artifact_sha256")
        if not isinstance(artifact_digest, str) or not _SHA256.fullmatch(artifact_digest):
            return blocked("The clean-build canary digest is invalid.")
        try:
            if self._package_versions() != tool_packages:
                return blocked("The installed AUR prerequisite tools changed after preparation.")
        except (OSError, subprocess.SubprocessError):
            return blocked("The installed AUR prerequisite versions could not be verified.")
        return AurPipelineReadiness(
            True,
            "The fixed AUR host prerequisites and clean-build canary passed. Exact package source and dependencies still require review.",
            AUR_POLICY_VERSION,
            checked_at,
            digest,
        )
