"""Typed inventory, catalog, policy, and history domain model.

The types in this module contain no command, HTTP or SQLite details. Stable
identity always includes the update source and installation scope.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
import hashlib
import json
from typing import Any
from urllib.parse import quote, urlencode


class SourceState(StrEnum):
    READY_TO_REVIEW = "ready_to_review"
    UP_TO_DATE = "up_to_date"
    NOT_CHECKED = "not_checked"
    NEEDS_REFRESH = "needs_refresh"
    TURNED_OFF = "turned_off"
    SOURCE_UNAVAILABLE = "source_unavailable"
    BLOCKED = "blocked"
    ERROR = "error"
    NOT_SUPPORTED = "not_supported"
    POSTPONED = "postponed"
    SKIPPED = "skipped"
    PAUSED = "paused"


class PolicyKind(StrEnum):
    TURN_OFF_SOURCE = "turn_off_source"
    POSTPONE = "postpone"
    SKIP_VERSION = "skip_version"
    PAUSE_SOFTWARE = "pause_software"


class PolicyState(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REMOVED = "removed"


SYSTEM_UPDATE_GROUP_ID = "system-update-group"


class UpdateRunState(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIALLY_SUCCEEDED = "partially_succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    NEEDS_REBOOT = "needs_reboot"
    NEEDS_MANUAL_RECOVERY = "needs_manual_recovery"


class PlanState(StrEnum):
    AWAITING_REVIEW = "awaiting_review"
    AWAITING_LOCAL_CONFIRMATION = "awaiting_local_confirmation"
    AWAITING_AUTHORIZATION = "awaiting_authorization"
    READY_FOR_EXECUTION = "ready_for_execution"
    CONSUMED = "consumed"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"


class OperationKind(StrEnum):
    NATIVE_FULL_UPGRADE = "native_full_upgrade"
    FLATPAK_UPDATE = "flatpak_update"
    AUR_BUILD_INSTALL = "aur_build_install"
    FIRMWARE_UPDATE = "firmware_update"
    APPIMAGE_REPLACE = "appimage_replace"
    RUSTUP_UPDATE = "rustup_update"
    FNM_INSTALL_VERSION = "fnm_install_version"


class PermissionKind(StrEnum):
    CURRENT_USER = "current_user"
    ADMINISTRATOR = "administrator"


PLAN_TRANSITIONS: dict[PlanState, frozenset[PlanState]] = {
    PlanState.AWAITING_REVIEW: frozenset({PlanState.AWAITING_LOCAL_CONFIRMATION, PlanState.EXPIRED, PlanState.INVALIDATED}),
    PlanState.AWAITING_LOCAL_CONFIRMATION: frozenset({PlanState.AWAITING_AUTHORIZATION, PlanState.READY_FOR_EXECUTION, PlanState.EXPIRED, PlanState.INVALIDATED}),
    PlanState.AWAITING_AUTHORIZATION: frozenset({PlanState.READY_FOR_EXECUTION, PlanState.EXPIRED, PlanState.INVALIDATED}),
    PlanState.READY_FOR_EXECUTION: frozenset({PlanState.CONSUMED, PlanState.EXPIRED, PlanState.INVALIDATED}),
}


def can_transition_plan(current: PlanState, requested: PlanState) -> bool:
    return requested in PLAN_TRANSITIONS.get(current, frozenset())


UPDATE_RUN_TRANSITIONS: dict[UpdateRunState, frozenset[UpdateRunState]] = {
    UpdateRunState.CREATED: frozenset({
        UpdateRunState.RUNNING, UpdateRunState.CANCELLED,
        UpdateRunState.NEEDS_MANUAL_RECOVERY,
    }),
    UpdateRunState.RUNNING: frozenset({
        UpdateRunState.SUCCEEDED, UpdateRunState.PARTIALLY_SUCCEEDED,
        UpdateRunState.FAILED, UpdateRunState.CANCELLED, UpdateRunState.NEEDS_REBOOT,
        UpdateRunState.NEEDS_MANUAL_RECOVERY,
    }),
}


def can_transition_update_run(current: UpdateRunState, requested: UpdateRunState) -> bool:
    """Return whether a later milestone may record the requested run state."""
    return requested in UPDATE_RUN_TRANSITIONS.get(current, frozenset())


@dataclass(frozen=True)
class UpdatePlanStep:
    step_id: str
    operation: OperationKind
    source_id: str
    scope: str
    target_stable_ids: tuple[str, ...]
    package_ids: tuple[str, ...]
    permission: PermissionKind
    summary: str
    expected_changes: tuple[tuple[str, str | None, str], ...] = ()
    safe_cancellation: str = "Before this step starts"
    live_enabled: bool = False
    blocker: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["operation"] = self.operation.value
        value["permission"] = self.permission.value
        return value


@dataclass(frozen=True)
class UpdatePlan:
    plan_id: str
    digest: str
    snapshot_id: str
    snapshot_generation: str
    created_by: str
    created_at: str
    expires_at: str
    steps: tuple[UpdatePlanStep, ...]
    warnings: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    policy_ids: tuple[str, ...] = ()
    policy_digest: str = ""
    tool_versions: tuple[tuple[str, str, str | None], ...] = ()
    unknowns: tuple[str, ...] = ()

    @property
    def requires_administrator(self) -> bool:
        return any(step.permission is PermissionKind.ADMINISTRATOR for step in self.steps)

    def canonical_content(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "snapshot_generation": self.snapshot_generation,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "steps": [step.to_dict() for step in self.steps],
            "warnings": list(self.warnings),
            "blockers": list(self.blockers),
            "policy_ids": list(self.policy_ids),
            "policy_digest": self.policy_digest,
            "tool_versions": [list(value) for value in self.tool_versions],
            "unknowns": list(self.unknowns),
        }

    def to_dict(self, state: PlanState | None = None) -> dict[str, Any]:
        value = {**self.canonical_content(), "plan_id": self.plan_id, "digest": self.digest,
                 "requires_administrator": self.requires_administrator}
        if state is not None:
            value["state"] = state.value
        return value


@dataclass(frozen=True)
class UpdateRun:
    run_id: str
    plan_id: str
    plan_digest: str
    state: UpdateRunState
    progress: int
    message: str
    started_at: str
    finished_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["state"] = self.state.value
        return value


@dataclass(frozen=True)
class SelectionPolicy:
    policy_id: str
    kind: PolicyKind
    state: PolicyState
    source_id: str
    scope: str
    software_id: str | None = None
    target_stable_id: str | None = None
    version: str | None = None
    expires_at: str | None = None
    reason: str | None = None
    created_by: str = "administrator"
    created_at: str = field(default_factory=lambda: utc_now())
    removed_at: str | None = None
    last_applied_at: str | None = None
    last_applied_snapshot: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["kind"] = self.kind.value
        value["state"] = self.state.value
        return value


@dataclass(frozen=True)
class ProvenancedNote:
    """Plain-text information whose origin and observation time remain visible."""

    text: str
    source_name: str
    source_url: str
    observed_at: str
    kind: str = "description"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class CatalogRecord:
    catalog_id: str
    source_id: str
    source_name: str
    scope: str
    origin: str
    software_id: str
    name: str
    version: str | None
    summary: str | None
    trust: str
    note: ProvenancedNote | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    architecture: str | None = None
    branch: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["note"] = self.note.to_dict() if self.note else None
        return value


@dataclass(frozen=True)
class Advisory:
    advisory_id: str
    source_id: str
    source_name: str
    title: str
    summary: str
    source_url: str
    published_at: str | None
    observed_at: str
    advisory_kind: str
    simulated: bool = False
    content_hash: str = ""
    parse_status: str = "parsed"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExternalHistoryEvent:
    event_id: str
    dedupe_key: str
    source_id: str
    scope: str
    occurred_at: str
    action: str
    software_id: str
    name: str
    version_before: str | None
    version_after: str | None
    result: str
    completeness: str
    provenance: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


STATE_LABELS: dict[SourceState, str] = {
    SourceState.READY_TO_REVIEW: "Ready to review",
    SourceState.UP_TO_DATE: "Up to date",
    SourceState.NOT_CHECKED: "Not checked",
    SourceState.NEEDS_REFRESH: "Needs refresh",
    SourceState.TURNED_OFF: "Turned off",
    SourceState.SOURCE_UNAVAILABLE: "Source unavailable",
    SourceState.BLOCKED: "Blocked",
    SourceState.ERROR: "Error",
    SourceState.NOT_SUPPORTED: "Not supported",
    SourceState.POSTPONED: "Postponed",
    SourceState.SKIPPED: "Skipped this version",
    SourceState.PAUSED: "Paused",
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def stable_software_id(
    source_id: str,
    scope: str,
    software_id: str,
    origin: str | None = None,
    architecture: str | None = None,
    branch: str | None = None,
) -> str:
    canonical = json.dumps(
        [source_id, scope, origin, software_id, architecture, branch],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass(frozen=True)
class SoftwareRecord:
    source_id: str
    scope: str
    software_id: str
    name: str
    installed_version: str | None
    origin: str | None = None
    architecture: str | None = None
    branch: str | None = None
    ownership: str = "confirmed"
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def stable_id(self) -> str:
        return stable_software_id(
            self.source_id, self.scope, self.software_id,
            self.origin, self.architecture, self.branch,
        )

    @property
    def source_documentation_url(self) -> str:
        """Return a safe, human-readable page for this software's source."""

        if self.source_id == "aur":
            return f"https://aur.archlinux.org/packages/{quote(self.software_id, safe='')}"
        if self.source_id == "native":
            if self.origin and self.origin != "preview" and self.architecture:
                return (
                    "https://archlinux.org/packages/"
                    f"{quote(self.origin, safe='')}/{quote(self.architecture, safe='')}/"
                    f"{quote(self.software_id, safe='')}/"
                )
            return "https://archlinux.org/packages/?" + urlencode({"q": self.software_id})
        if self.source_id == "flatpak":
            app_id = self.software_id.split("/", 1)[0]
            if self.origin == "flathub":
                return f"https://flathub.org/apps/{quote(app_id, safe='.')}"
            return "https://docs.flatpak.org/en/latest/using-flatpak.html"
        if self.source_id == "firmware":
            return "https://fwupd.github.io/libfwupdplugin/"
        if self.source_id == "rustup":
            return "https://rust-lang.github.io/rustup/concepts/toolchains.html"
        if self.source_id == "appimage":
            return "https://docs.appimage.org/packaging-guide/optional/updates.html"
        if self.source_id == "fnm":
            return "https://github.com/Schniz/fnm"
        if self.source_id == "cargo":
            return "https://doc.rust-lang.org/cargo/commands/cargo-install.html"
        if self.source_id == "npm":
            return "https://docs.npmjs.com/cli/commands/npm-update"
        if self.source_id == "uv":
            return "https://docs.astral.sh/uv/guides/tools/"
        return "https://wiki.archlinux.org/title/System_maintenance"

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "stable_id": self.stable_id,
            "source_documentation_url": self.source_documentation_url,
        }


@dataclass(frozen=True)
class DetectedUpdate:
    stable_id: str
    source_id: str
    scope: str
    software_id: str
    name: str
    installed_version: str | None
    available_version: str
    state: SourceState = SourceState.READY_TO_REVIEW
    restart_needed: bool | None = None
    size_bytes: int | None = None
    summary: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["state"] = self.state.value
        value["state_label"] = STATE_LABELS[self.state]
        return value


@dataclass(frozen=True)
class SourceResult:
    source_id: str
    name: str
    scope: str
    state: SourceState
    message: str
    checked_at: str
    duration_ms: int
    software: tuple[SoftwareRecord, ...] = ()
    updates: tuple[DetectedUpdate, ...] = ()
    tool_version: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, *, include_software: bool = True) -> dict[str, Any]:
        value: dict[str, Any] = {
            "source_id": self.source_id,
            "name": self.name,
            "scope": self.scope,
            "state": self.state.value,
            "state_label": STATE_LABELS[self.state],
            "message": self.message,
            "checked_at": self.checked_at,
            "duration_ms": self.duration_ms,
            "software_count": len(self.software),
            "update_count": len(self.updates),
            "tool_version": self.tool_version,
            "evidence": self.evidence,
        }
        if include_software:
            value["software"] = [item.to_dict() for item in self.software]
            value["updates"] = [item.to_dict() for item in self.updates]
        return value


@dataclass(frozen=True)
class InventorySnapshot:
    snapshot_id: str
    generation: str
    started_at: str
    completed_at: str
    sources: tuple[SourceResult, ...]

    @classmethod
    def create(cls, started_at: str, sources: list[SourceResult]) -> "InventorySnapshot":
        completed_at = utc_now()
        canonical = json.dumps(
            [source.to_dict() for source in sorted(sources, key=lambda item: (item.source_id, item.scope))],
            sort_keys=True,
            separators=(",", ":"),
        )
        generation = hashlib.sha256(canonical.encode()).hexdigest()
        return cls(
            snapshot_id=f"snapshot-{generation[:20]}",
            generation=generation,
            started_at=started_at,
            completed_at=completed_at,
            sources=tuple(sources),
        )

    @property
    def software(self) -> tuple[SoftwareRecord, ...]:
        return tuple(item for source in self.sources for item in source.software)

    @property
    def updates(self) -> tuple[DetectedUpdate, ...]:
        return tuple(item for source in self.sources for item in source.updates)

    def summary(self) -> dict[str, int]:
        updates = self.updates
        return {
            "updates_found": len(updates),
            "ready_to_review": sum(item.state is SourceState.READY_TO_REVIEW for item in updates),
            "blocked": sum(item.state is SourceState.BLOCKED for item in updates),
            "restart_needed": sum(item.restart_needed is True for item in updates),
            "software_recorded": len(self.software),
        }

    def to_dict(self, *, include_software: bool = True) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "generation": self.generation,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "summary": self.summary(),
            "sources": [source.to_dict(include_software=include_software) for source in self.sources],
        }
