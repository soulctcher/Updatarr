"""Immutable update planning with no command or subprocess surface."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
import re

from .aur_pipeline import AUR_POLICY_VERSION, AurPipelineReadiness
from .domain import (
    DetectedUpdate, InventorySnapshot, OperationKind, PermissionKind,
    PlanState, SelectionPolicy, SourceState, UpdatePlan, UpdatePlanStep,
)
from .policy import PolicyError, check_update_selection


PLAN_TTL = timedelta(minutes=15)
SAFE_PACKAGE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9@+._:/-]{0,299}$")


class PlanningError(ValueError):
    pass


@dataclass(frozen=True)
class PlanValidation:
    valid: bool
    state: PlanState
    message: str

    def to_dict(self) -> dict[str, str | bool]:
        return {"valid": self.valid, "state": self.state.value, "message": self.message}


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _digest(content: dict[str, object]) -> str:
    encoded = json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def policy_digest(policies: list[SelectionPolicy]) -> str:
    return _digest({"policies": [policy.to_dict() for policy in sorted(policies, key=lambda value: value.policy_id)]})


class Planner:
    """Turns a specific inventory generation into a sealed, typed plan."""

    def __init__(self, *, aur_readiness: AurPipelineReadiness | None = None) -> None:
        self._aur_readiness = aur_readiness or AurPipelineReadiness(
            False,
            "The AUR host prerequisites have not been prepared on this computer.",
            AUR_POLICY_VERSION,
            datetime.now(UTC).isoformat(),
            "",
        )

    def prepare(
        self,
        snapshot: InventorySnapshot,
        updates: tuple[DetectedUpdate, ...] | list[DetectedUpdate],
        selected_stable_ids: list[str],
        policies: list[SelectionPolicy],
        *,
        actor: str = "administrator",
        now: datetime | None = None,
    ) -> UpdatePlan:
        decision = check_update_selection(updates, selected_stable_ids)
        if not decision.allowed:
            raise PlanningError(decision.blocked_reason or decision.message)
        selected = [item for item in updates if item.stable_id in set(selected_stable_ids)]
        if not selected:
            raise PlanningError("Choose at least one update before preparing a plan.")
        for item in selected:
            if item.state is not SourceState.READY_TO_REVIEW:
                raise PlanningError(f"{item.name} is not ready to include in a plan.")
            if not SAFE_PACKAGE_ID.fullmatch(item.software_id):
                raise PlanningError("An update has an invalid software identifier.")

        steps: list[UpdatePlanStep] = []
        blockers: list[str] = []
        warnings: list[str] = []
        native = sorted((item for item in selected if item.source_id == "native"), key=lambda x: x.software_id)
        if native:
            steps.append(UpdatePlanStep(
                step_id="native-full-upgrade", operation=OperationKind.NATIVE_FULL_UPGRADE,
                source_id="native", scope="system",
                target_stable_ids=tuple(item.stable_id for item in native),
                package_ids=tuple(item.software_id for item in native),
                permission=PermissionKind.ADMINISTRATOR,
                summary=f"Update the complete system package group ({len(native)} packages).",
                expected_changes=tuple((item.stable_id, item.installed_version, item.available_version) for item in native),
                live_enabled=True,
            ))
        for item in sorted((item for item in selected if item.source_id == "flatpak"), key=lambda x: (x.scope, x.software_id)):
            permission = PermissionKind.ADMINISTRATOR if item.scope == "system" else PermissionKind.CURRENT_USER
            steps.append(UpdatePlanStep(
                step_id=f"flatpak-{len(steps) + 1}", operation=OperationKind.FLATPAK_UPDATE,
                source_id=item.source_id, scope=item.scope,
                target_stable_ids=(item.stable_id,), package_ids=(item.software_id,),
                permission=permission,
                summary=f"Update {item.name} for {'the whole system' if item.scope == 'system' else 'the current user'}.",
                live_enabled=True,
                expected_changes=((item.stable_id, item.installed_version, item.available_version),),
            ))
        for item in sorted((item for item in selected if item.source_id == "aur"), key=lambda x: x.software_id):
            simulated = self._aur_readiness.policy_version == "simulator"
            blocker = None if simulated else (
                f"The AUR host prerequisites passed, but {item.name} still needs its exact source changes and dependencies reviewed before installation."
                if self._aur_readiness.ready
                else self._aur_readiness.explanation
            )
            if blocker:
                blockers.append(blocker)
            steps.append(UpdatePlanStep(
                step_id=f"aur-{len(steps) + 1}", operation=OperationKind.AUR_BUILD_INSTALL,
                source_id=item.source_id, scope=item.scope,
                target_stable_ids=(item.stable_id,), package_ids=(item.software_id,),
                permission=PermissionKind.CURRENT_USER,
                summary=(
                    f"Review and build {item.name} in the safe simulator."
                    if simulated
                    else f"Review the exact source and dependencies for {item.name}."
                ),
                expected_changes=((item.stable_id, item.installed_version, item.available_version),),
                # Only the deterministic simulator executes this operation.
                # Live host prerequisites do not replace a package-specific
                # reviewed tree and dependency plan.
                live_enabled=simulated,
                blocker=blocker,
            ))
        operation_details = {
            "firmware": (OperationKind.FIRMWARE_UPDATE, PermissionKind.ADMINISTRATOR,
                         "Install the signed firmware version", "Before the device starts changing"),
            "appimage": (OperationKind.APPIMAGE_REPLACE, PermissionKind.CURRENT_USER,
                         "Download, check and replace", "Before the checked file replaces the current file"),
            "rustup": (OperationKind.RUSTUP_UPDATE, PermissionKind.CURRENT_USER,
                       "Update the Rust toolchain", "Before the toolchain installer begins"),
            "fnm": (OperationKind.FNM_INSTALL_VERSION, PermissionKind.CURRENT_USER,
                    "Install the selected Node.js version", "Before the version download begins"),
        }
        operation_labels = {"firmware": "firmware", "appimage": "portable-app replacement",
                            "rustup": "Rust toolchain", "fnm": "Node.js"}
        for item in sorted((item for item in selected if item.source_id in operation_details),
                           key=lambda x: (x.source_id, x.software_id)):
            operation, permission, verb, safe_cancellation = operation_details[item.source_id]
            blocker = (f"Live {operation_labels[item.source_id]} work is not available yet. Its first real change "
                       "and the restricted system helper must be reviewed and approved separately.")
            blockers.append(blocker)
            steps.append(UpdatePlanStep(
                step_id=f"{item.source_id}-{len(steps) + 1}", operation=operation,
                source_id=item.source_id, scope=item.scope,
                target_stable_ids=(item.stable_id,), package_ids=(item.software_id,),
                permission=permission, summary=f"{verb}: {item.name}.",
                expected_changes=((item.stable_id, item.installed_version, item.available_version),),
                safe_cancellation=safe_cancellation, live_enabled=False, blocker=blocker,
            ))
        unsupported = sorted({item.source_id for item in selected} - {"native", "flatpak", "aur", *operation_details})
        if unsupported:
            raise PlanningError("Installation is not supported for: " + ", ".join(unsupported))

        instant = (now or datetime.now(UTC)).astimezone(UTC)
        created = instant.isoformat()
        expires = (instant + PLAN_TTL).isoformat()
        active_policy_ids = tuple(sorted(policy.policy_id for policy in policies))
        active_policy_digest = policy_digest(policies)
        recorded_tools = [
            (source.source_id, source.scope, source.tool_version)
            for source in snapshot.sources
        ]
        if any(step.operation is OperationKind.AUR_BUILD_INSTALL for step in steps):
            recorded_tools.append(
                ("aur-pipeline", "system", self._aur_readiness.evidence_digest)
            )
        tool_versions = tuple(sorted(recorded_tools))
        unknown_values = [
            f"{item.name}: download size is not known" for item in selected if item.size_bytes is None
        ]
        source_names = {"native": "System packages", "flatpak": "Flatpak", "aur": "AUR",
                        "firmware": "Firmware", "appimage": "Portable apps", "rustup": "Rust toolchains",
                        "fnm": "Node.js from fnm"}
        unknown_values.extend(
            f"{source_names.get(step.source_id, step.source_id)}: other software needed by this update was not reported by the simulator."
            for step in steps
        )
        unknowns = tuple(sorted(unknown_values))
        unsigned: dict[str, object] = {
            "snapshot_id": snapshot.snapshot_id,
            "snapshot_generation": snapshot.generation,
            "created_by": actor,
            "created_at": created,
            "expires_at": expires,
            "steps": [step.to_dict() for step in steps],
            "warnings": warnings,
            "blockers": sorted(set(blockers)),
            "policy_ids": list(active_policy_ids),
            "policy_digest": active_policy_digest,
            "tool_versions": [list(value) for value in tool_versions],
            "unknowns": list(unknowns),
        }
        digest = _digest(unsigned)
        return UpdatePlan(
            plan_id=f"plan-{digest[:24]}", digest=digest,
            snapshot_id=snapshot.snapshot_id, snapshot_generation=snapshot.generation,
            created_by=actor, created_at=created, expires_at=expires,
            steps=tuple(steps), warnings=tuple(warnings), blockers=tuple(sorted(set(blockers))),
            policy_ids=active_policy_ids, policy_digest=active_policy_digest,
            tool_versions=tool_versions, unknowns=unknowns,
        )

    def validate(
        self,
        plan: UpdatePlan,
        snapshot: InventorySnapshot | None,
        policies: list[SelectionPolicy],
        *,
        now: datetime | None = None,
        require_executable: bool = True,
    ) -> PlanValidation:
        if _digest(plan.canonical_content()) != plan.digest:
            return PlanValidation(False, PlanState.INVALIDATED, "The update plan changed after it was reviewed. Prepare and review it again.")
        if (now or datetime.now(UTC)).astimezone(UTC) >= _parse_time(plan.expires_at):
            return PlanValidation(False, PlanState.EXPIRED, "This plan expired. Prepare and review a new plan.")
        if snapshot is None or snapshot.snapshot_id != plan.snapshot_id or snapshot.generation != plan.snapshot_generation:
            return PlanValidation(False, PlanState.INVALIDATED, "The recorded software changed. Prepare and review a new plan.")
        if (tuple(sorted(policy.policy_id for policy in policies)) != plan.policy_ids
                or policy_digest(policies) != plan.policy_digest):
            return PlanValidation(False, PlanState.INVALIDATED, "A saved choice changed. Prepare and review a new plan.")
        if any(step.operation is OperationKind.AUR_BUILD_INSTALL for step in plan.steps):
            recorded_evidence = next(
                (
                    version
                    for source_id, scope, version in plan.tool_versions
                    if source_id == "aur-pipeline" and scope == "system"
                ),
                None,
            )
            if (
                not self._aur_readiness.ready
                or not recorded_evidence
                or not __import__("hmac").compare_digest(
                    recorded_evidence, self._aur_readiness.evidence_digest
                )
            ):
                return PlanValidation(
                    False,
                    PlanState.INVALIDATED,
                    "The AUR build readiness check changed or expired. Prepare and review a new plan.",
                )
        if require_executable and plan.blockers:
            return PlanValidation(False, PlanState.INVALIDATED, plan.blockers[0])
        return PlanValidation(True, PlanState.READY_FOR_EXECUTION, "The plan still matches the reviewed software information.")
