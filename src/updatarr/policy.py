"""Policy Module: saved choices and the system-update-group safety rule."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
import re
import secrets
from typing import Iterable

from .domain import (
    DetectedUpdate,
    PolicyKind,
    PolicyState,
    SelectionPolicy,
    SourceState,
    SYSTEM_UPDATE_GROUP_ID,
    utc_now,
)


IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+:/@-]{0,299}$")


class PolicyError(ValueError):
    """A saved choice is incomplete, ambiguous, or unsafe."""


@dataclass(frozen=True)
class SelectionDecision:
    allowed: bool
    message: str
    selected_count: int
    system_update_count: int
    blocked_reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "allowed": self.allowed,
            "message": self.message,
            "selected_count": self.selected_count,
            "system_update_count": self.system_update_count,
            "blocked_reason": self.blocked_reason,
        }


def _valid_identifier(value: str, label: str) -> str:
    if not IDENTIFIER.fullmatch(value):
        raise PolicyError(f"{label} is not valid.")
    return value


def _future_expiry(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise PolicyError("Choose a valid date and time.") from error
    if parsed.tzinfo is None:
        raise PolicyError("Choose a date and time with a time zone.")
    if parsed.astimezone(UTC) <= datetime.now(UTC):
        raise PolicyError("Choose a date and time in the future.")
    return parsed.astimezone(UTC).isoformat()


def new_policy(
    *,
    kind: PolicyKind,
    source_id: str,
    scope: str,
    software_id: str | None = None,
    target_stable_id: str | None = None,
    version: str | None = None,
    expires_at: str | None = None,
    reason: str | None = None,
    actor: str = "administrator",
) -> SelectionPolicy:
    """Validate and create one exact saved choice without provider side effects."""

    _valid_identifier(source_id, "The update source")
    _valid_identifier(scope, "The installation place")
    if software_id is not None:
        _valid_identifier(software_id, "The software identity")
    if target_stable_id is not None:
        _valid_identifier(target_stable_id, "The exact software identity")
    if version is not None:
        _valid_identifier(version, "The version")
    if reason is not None:
        reason = reason.strip()
        if not reason:
            reason = None
        elif len(reason) > 500 or any(ord(character) < 32 and character not in "\t\n" for character in reason):
            raise PolicyError("The reason is not valid.")

    if kind is PolicyKind.TURN_OFF_SOURCE:
        if software_id is not None or version is not None or expires_at is not None:
            raise PolicyError("Turning off an update source applies to the whole source.")
    elif kind is PolicyKind.SKIP_VERSION:
        if not software_id or not version:
            raise PolicyError("Choose the software and exact version to skip.")
    elif kind in {PolicyKind.POSTPONE, PolicyKind.PAUSE_SOFTWARE}:
        if not software_id or version is not None:
            raise PolicyError("Choose the software to postpone or pause.")
        if source_id == "native" and software_id != SYSTEM_UPDATE_GROUP_ID:
            raise PolicyError("System packages must be postponed or paused together.")
    else:  # pragma: no cover - exhaustive guard for future enum members
        raise PolicyError("That saved choice is not supported.")

    if (
        kind is not PolicyKind.TURN_OFF_SOURCE
        and not (source_id == "native" and software_id == SYSTEM_UPDATE_GROUP_ID)
        and target_stable_id is None
    ):
        raise PolicyError("Choose the exact recorded software item.")

    expiry = _future_expiry(expires_at)
    return SelectionPolicy(
        policy_id=f"choice-{secrets.token_urlsafe(12)}",
        kind=kind,
        state=PolicyState.ACTIVE,
        source_id=source_id,
        scope=scope,
        software_id=software_id,
        target_stable_id=target_stable_id,
        version=version,
        expires_at=expiry,
        reason=reason,
        created_by=actor,
        created_at=utc_now(),
    )


def is_active(policy: SelectionPolicy, now: datetime | None = None) -> bool:
    if policy.state is not PolicyState.ACTIVE:
        return False
    if policy.expires_at is None:
        return True
    current = now or datetime.now(UTC)
    expiry = datetime.fromisoformat(policy.expires_at.replace("Z", "+00:00"))
    return expiry > current


def apply_policies(
    updates: Iterable[DetectedUpdate], policies: Iterable[SelectionPolicy]
) -> tuple[DetectedUpdate, ...]:
    """Return a presentation view; immutable detected-update evidence is untouched."""

    active = [policy for policy in policies if is_active(policy)]
    result: list[DetectedUpdate] = []
    for update in updates:
        matches = [
            policy
            for policy in active
            if policy.source_id == update.source_id
            and policy.scope == update.scope
            and (
                (policy.target_stable_id is not None and policy.target_stable_id == update.stable_id)
                or (update.source_id == "native" and policy.software_id == SYSTEM_UPDATE_GROUP_ID)
            )
        ]
        state = update.state
        if any(policy.kind is PolicyKind.PAUSE_SOFTWARE for policy in matches):
            state = SourceState.PAUSED
        elif any(policy.kind is PolicyKind.POSTPONE for policy in matches):
            state = SourceState.POSTPONED
        elif any(
            policy.kind is PolicyKind.SKIP_VERSION and policy.version == update.available_version
            for policy in matches
        ):
            state = SourceState.SKIPPED
        result.append(replace(update, state=state))
    return tuple(result)


def matching_policy_ids(
    updates: Iterable[DetectedUpdate], policies: Iterable[SelectionPolicy]
) -> set[str]:
    matched: set[str] = set()
    update_list = list(updates)
    for policy in policies:
        if not is_active(policy) or policy.kind is PolicyKind.TURN_OFF_SOURCE:
            continue
        for update in update_list:
            identity_matches = (
                (policy.target_stable_id is not None and policy.target_stable_id == update.stable_id)
                or (update.source_id == "native" and policy.software_id == SYSTEM_UPDATE_GROUP_ID)
            )
            version_matches = (
                policy.kind is not PolicyKind.SKIP_VERSION
                or policy.version == update.available_version
            )
            if (
                policy.source_id == update.source_id and policy.scope == update.scope
                and identity_matches and version_matches
            ):
                matched.add(policy.policy_id)
                break
    return matched


def check_update_selection(
    updates: Iterable[DetectedUpdate], selected_stable_ids: Iterable[str]
) -> SelectionDecision:
    """Reject a selected subset of the Arch/EndeavourOS system update group."""

    update_list = list(updates)
    available_ids = {update.stable_id for update in update_list}
    selected = set(selected_stable_ids)
    if not selected.issubset(available_ids):
        raise PolicyError("The selection contains software that is not in this update check.")
    native_ids = {update.stable_id for update in update_list if update.source_id == "native"}
    selected_native = selected & native_ids
    held_native = {
        update.stable_id
        for update in update_list
        if update.source_id == "native"
        and update.state in {SourceState.POSTPONED, SourceState.PAUSED, SourceState.SKIPPED}
    }
    if selected_native and held_native:
        return SelectionDecision(
            False,
            "The system update group has a saved choice. Remove that choice before reviewing system updates.",
            len(selected),
            len(native_ids),
            "A saved choice cannot create a partial system update on Arch Linux.",
        )
    if selected_native and selected_native != native_ids:
        return SelectionDecision(
            False,
            "System packages must update together. Select all system updates or postpone the whole group.",
            len(selected),
            len(native_ids),
            "A partial system update is not supported on Arch Linux.",
        )
    return SelectionDecision(
        True,
        "This selection keeps the system update group together.",
        len(selected),
        len(native_ids),
    )
