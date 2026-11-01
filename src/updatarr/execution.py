"""Typed execution boundary and deterministic simulator.

No public interface accepts a command, executable path, environment, or
caller-provided argument array.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import os
from pathlib import Path
import time
from typing import Callable, Protocol

from .domain import (
    OperationKind, PermissionKind, PlanState, UpdatePlan, UpdateRun,
    UpdateRunState, utc_now,
)
from .planning import Planner, SAFE_PACKAGE_ID


class ExecutionRefused(ValueError):
    pass


@dataclass(frozen=True)
class LocalSubject:
    """Identity derived by the future local D-Bus/Polkit transport."""
    uid: int
    session_id: str
    active: bool


@dataclass(frozen=True)
class PrivilegedEnvelope:
    plan_id: str
    plan_digest: str
    operation: OperationKind
    package_ids: tuple[str, ...]
    snapshot_generation: str
    expires_at: str
    caller_uid: int


class BoundaryRepository(Protocol):
    def plan(self, plan_id: str) -> tuple[UpdatePlan, PlanState] | None: ...
    def latest_snapshot(self): ...  # type: ignore[no-untyped-def]
    def policies(self, *, include_inactive: bool = False): ...  # type: ignore[no-untyped-def]
    def plan_events(self, plan_id: str) -> list[dict[str, object]]: ...


class LockProbe(Protocol):
    def package_manager_locked(self) -> bool: ...
    def coordinator_busy(self) -> bool: ...


class PackageManagerLockState(StrEnum):
    AVAILABLE = "available"
    HELD_BY_ANOTHER_PROCESS = "held_by_another_process"
    HELD_BY_THIS_PROCESS = "held_by_this_process"
    OWNER_NOT_FOUND = "owner_not_found"


@dataclass(frozen=True)
class PackageManagerLockObservation:
    state: PackageManagerLockState
    owner_process_ids: tuple[int, ...] = ()

    @property
    def blocks_updates(self) -> bool:
        return self.state is not PackageManagerLockState.AVAILABLE


class HostLockProbe:
    """Observe the native package lock without changing or removing it."""

    def __init__(
        self,
        coordinator_busy: Callable[[], bool] = lambda: False,
        *,
        lock_path: Path = Path("/var/lib/pacman/db.lck"),
        process_root: Path = Path("/proc"),
        current_process_id: int | None = None,
        scan_limit: int = 32_768,
    ) -> None:
        self._coordinator_busy = coordinator_busy
        self._lock_path = lock_path
        self._process_root = process_root
        self._current_process_id = os.getpid() if current_process_id is None else current_process_id
        self._scan_limit = scan_limit

    def package_manager_lock(self) -> PackageManagerLockObservation:
        try:
            lock_stat = self._lock_path.stat(follow_symlinks=False)
        except FileNotFoundError:
            return PackageManagerLockObservation(PackageManagerLockState.AVAILABLE)
        except OSError:
            return PackageManagerLockObservation(PackageManagerLockState.OWNER_NOT_FOUND)

        owners: set[int] = set()
        inspected = 0
        try:
            processes = sorted(
                (entry for entry in self._process_root.iterdir() if entry.name.isdigit()),
                key=lambda entry: int(entry.name),
            )
        except OSError:
            processes = []
        for process in processes:
            try:
                descriptors = list(process.joinpath("fd").iterdir())
            except OSError:
                continue
            for descriptor in descriptors:
                inspected += 1
                if inspected > self._scan_limit:
                    return PackageManagerLockObservation(
                        PackageManagerLockState.OWNER_NOT_FOUND, tuple(sorted(owners))
                    )
                try:
                    descriptor_stat = descriptor.stat()
                except OSError:
                    continue
                if (descriptor_stat.st_dev, descriptor_stat.st_ino) == (lock_stat.st_dev, lock_stat.st_ino):
                    owners.add(int(process.name))

        if not owners:
            return PackageManagerLockObservation(PackageManagerLockState.OWNER_NOT_FOUND)
        state = (
            PackageManagerLockState.HELD_BY_THIS_PROCESS
            if owners == {self._current_process_id}
            else PackageManagerLockState.HELD_BY_ANOTHER_PROCESS
        )
        return PackageManagerLockObservation(state, tuple(sorted(owners)))

    def package_manager_locked(self) -> bool:
        return self.package_manager_lock().blocks_updates

    def coordinator_busy(self) -> bool:
        return self._coordinator_busy()


class PrivilegedBoundary:
    """Store-backed, fail-closed validator for the future Polkit mechanism."""
    ALLOWED = frozenset({OperationKind.NATIVE_FULL_UPGRADE, OperationKind.FLATPAK_UPDATE})

    def __init__(self, repository: BoundaryRepository, lock_probe: LockProbe) -> None:
        self.repository = repository
        self.lock_probe = lock_probe
        self.planner = Planner()

    def envelope_for(self, plan_id: str, step_id: str, subject: LocalSubject) -> PrivilegedEnvelope:
        stored = self.repository.plan(plan_id)
        if stored is None:
            raise ExecutionRefused("The reviewed plan was not found.")
        plan, state = stored
        if state is not PlanState.READY_FOR_EXECUTION:
            raise ExecutionRefused("The reviewed plan is not ready for execution.")
        validation = self.planner.validate(plan, self.repository.latest_snapshot(), self.repository.policies())
        if not validation.valid:
            raise ExecutionRefused(validation.message)
        confirmations = [event for event in self.repository.plan_events(plan_id)
                         if event["kind"] == "confirmed_on_managed_computer"]
        if not confirmations:
            raise ExecutionRefused("Confirmation on the managed computer is missing.")
        confirmed = confirmations[-1]["details"]
        if (not subject.active or subject.uid < 0 or confirmed.get("uid") != subject.uid
                or confirmed.get("session_id") != subject.session_id):
            raise ExecutionRefused("The active caller does not match the person who confirmed this plan.")
        step = next((value for value in plan.steps if value.step_id == step_id), None)
        if step is None or step.permission is not PermissionKind.ADMINISTRATOR:
            raise ExecutionRefused("The requested administrator operation is not in this plan.")
        permissions = [event for event in self.repository.plan_events(plan_id)
                       if event["kind"] == "administrator_permission_granted"]
        if not permissions or permissions[-1]["details"].get("uid") != subject.uid:
            raise ExecutionRefused("Administrator permission from the computer being updated is missing.")
        if step.operation not in self.ALLOWED or not step.live_enabled:
            raise ExecutionRefused("That administrator operation is not enabled.")
        if not step.package_ids or any(not SAFE_PACKAGE_ID.fullmatch(value) for value in step.package_ids):
            raise ExecutionRefused("The plan contains an invalid software identifier.")
        if step.operation is OperationKind.NATIVE_FULL_UPGRADE and (
            self.lock_probe.package_manager_locked() or self.lock_probe.coordinator_busy()
        ):
            raise ExecutionRefused("Another system package operation is active.")
        return PrivilegedEnvelope(
            plan_id=plan.plan_id, plan_digest=plan.digest, operation=step.operation,
            package_ids=step.package_ids, snapshot_generation=plan.snapshot_generation,
            expires_at=plan.expires_at, caller_uid=subject.uid,
        )


class ResultChecker(Protocol):
    def matches(self, plan: UpdatePlan) -> bool: ...


class RecoveryAdapter(Protocol):
    source_id: str
    scope: str

    def check(self): ...  # type: ignore[no-untyped-def]


class ProviderResultChecker:
    """Verify plan targets from fresh read-only provider observations."""

    def __init__(self, adapters: list[RecoveryAdapter]) -> None:
        self.adapters = adapters

    def matches(self, plan: UpdatePlan) -> bool | None:
        expected = {
            stable_id: available
            for step in plan.steps
            for stable_id, _installed, available in step.expected_changes
        }
        if not expected:
            return False
        needed = {(step.source_id, step.scope) for step in plan.steps}
        selected = [
            adapter for adapter in self.adapters
            if (adapter.source_id, adapter.scope) in needed
        ]
        if len({(adapter.source_id, adapter.scope) for adapter in selected}) != len(needed):
            return None
        observed: dict[str, str | None] = {}
        for adapter in selected:
            result = adapter.check()
            if result.state.value in {"error", "source_unavailable", "not_supported"}:
                return None
            observed.update(
                (software.stable_id, software.installed_version)
                for software in result.software
            )
        return all(observed.get(stable_id) == version for stable_id, version in expected.items())


class SimulatorResultChecker:
    """Apply expected versions to an isolated ledger, then compare every target."""
    def __init__(self, observed_versions: dict[str, str] | None = None) -> None:
        self.observed_versions = observed_versions

    def matches(self, plan: UpdatePlan) -> bool:
        expected = {stable_id: available for step in plan.steps
                    for stable_id, _installed, available in step.expected_changes}
        observed = dict(expected) if self.observed_versions is None else self.observed_versions
        return bool(expected) and all(observed.get(stable_id) == version for stable_id, version in expected.items())


class SimulatorExecutor:
    """Deterministic M3 executor; never invokes host software tools."""
    def execute(self, plan: UpdatePlan, checker: ResultChecker, *, run_id: str,
                started_at: str, cancel_requested: Callable[[], bool] = lambda: False,
                event_callback: Callable[[dict[str, object]], None] = lambda _event: None,
                step_delay: float = 0.03) -> tuple[UpdateRun, list[dict[str, object]]]:
        events: list[dict[str, object]] = []
        def record(event: dict[str, object]) -> None:
            events.append(event)
            event_callback(event)
        for index, step in enumerate(plan.steps, start=1):
            if cancel_requested():
                progress = int((index - 1) / len(plan.steps) * 100)
                message = "Stopped before the next software change began."
                record({"step_id": step.step_id, "state": "cancelled", "safe_to_cancel": True,
                        "message": message, "progress": progress})
                return UpdateRun(run_id, plan.plan_id, plan.digest, UpdateRunState.CANCELLED,
                                 progress, message, started_at, utc_now()), events
            record({"step_id": step.step_id, "state": "starting", "safe_to_cancel": True,
                    "message": "Safe to cancel before this step starts.",
                    "progress": int((index - 1) / len(plan.steps) * 100)})
            time.sleep(step_delay)
            record({"step_id": step.step_id, "state": "running", "safe_to_cancel": False,
                    "message": step.summary, "progress": int((index - 1) / len(plan.steps) * 100)})
            time.sleep(step_delay)
            record({"step_id": step.step_id, "state": "checking_result", "safe_to_cancel": False,
                    "message": "Checking the recorded result.", "progress": int(index / len(plan.steps) * 100)})
        success = checker.matches(plan)
        state = UpdateRunState.SUCCEEDED if success else UpdateRunState.NEEDS_MANUAL_RECOVERY
        message = ("Simulation completed and every expected version was observed." if success
                   else "The expected software versions were not all observed. Manual recovery is needed.")
        return UpdateRun(run_id, plan.plan_id, plan.digest, state, 100, message, started_at, utc_now()), events
