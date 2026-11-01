"""Fixed-action Polkit authorization prototype for administrator plans."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Protocol

from .domain import PlanState
from .planning import Planner
from .storage import StateStore


POLKIT_ACTION = "org.updatarr.execute-system-plan"
PKCHECK = Path("/usr/bin/pkcheck")


class AuthorizationRefused(ValueError):
    pass


@dataclass(frozen=True)
class ProcessSubject:
    pid: int
    start_time: int
    uid: int
    session_id: str


class SubjectResolver(Protocol):
    def resolve(self, pid: int) -> ProcessSubject: ...


class ProcSubjectResolver:
    """Resolve identity from procfs; a caller cannot supply UID/start time."""
    def resolve(self, pid: int) -> ProcessSubject:
        if pid <= 0:
            raise AuthorizationRefused("The confirmation request from this computer is not valid.")
        status = Path(f"/proc/{pid}/status").read_text(encoding="utf-8")
        uid_line = next((line for line in status.splitlines() if line.startswith("Uid:")), None)
        if uid_line is None:
            raise AuthorizationRefused("The identity used to confirm on this computer could not be read.")
        uid = int(uid_line.split()[1])
        stat_value = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        closing_parenthesis = stat_value.rfind(")")
        if closing_parenthesis < 0:
            raise AuthorizationRefused("The confirmation tool information on this computer is invalid.")
        fields_after_name = stat_value[closing_parenthesis + 2:].split()
        start_time = int(fields_after_name[19])
        session_id = Path(f"/proc/{pid}/sessionid").read_text(encoding="utf-8").strip()
        return ProcessSubject(pid, start_time, uid, session_id)


class PolkitRunner(Protocol):
    def check(self, subject: ProcessSubject) -> bool: ...


class FixedPkcheckRunner:
    """Invoke only the fixed Updatarr action for one resolved local process."""
    def check(self, subject: ProcessSubject) -> bool:
        completed = subprocess.run(
            [str(PKCHECK), "--action-id", POLKIT_ACTION,
             "--process", f"{subject.pid},{subject.start_time},{subject.uid}",
             "--allow-user-interaction"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env={"PATH": "/usr/bin", "LANG": "C.UTF-8"}, timeout=120, check=False,
        )
        return completed.returncode == 0


class AdministratorAuthorizer:
    def __init__(self, store: StateStore, resolver: SubjectResolver, runner: PolkitRunner) -> None:
        self.store = store
        self.resolver = resolver
        self.runner = runner

    def authorize(self, plan_id: str, *, caller_pid: int) -> PlanState:
        stored = self.store.plan(plan_id)
        if stored is None or stored[1] is not PlanState.AWAITING_AUTHORIZATION:
            raise AuthorizationRefused("That plan is not waiting for administrator permission.")
        plan, state = stored
        validation = Planner().validate(plan, self.store.latest_snapshot(), self.store.policies())
        if not validation.valid:
            self.store.transition_plan(plan_id, state, validation.state, "plan_validation_failed",
                                       "polkit", {"reason": validation.message})
            raise AuthorizationRefused(validation.message)
        subject = self.resolver.resolve(caller_pid)
        confirmations = [event for event in self.store.plan_events(plan_id)
                         if event["kind"] == "confirmed_on_managed_computer"]
        if (not confirmations
                or confirmations[-1]["details"].get("uid") != subject.uid
                or confirmations[-1]["details"].get("session_id") != subject.session_id):
            raise AuthorizationRefused("This exact plan was not confirmed on the computer being updated.")
        if not self.runner.check(subject):
            raise AuthorizationRefused("Administrator permission was not granted.")
        validation = Planner().validate(plan, self.store.latest_snapshot(), self.store.policies())
        if not validation.valid:
            self.store.transition_plan(plan_id, state, validation.state, "plan_validation_failed",
                                       "polkit", {"reason": validation.message})
            raise AuthorizationRefused(validation.message)
        return self.store.transition_plan(
            plan_id, state, PlanState.READY_FOR_EXECUTION,
            "administrator_permission_granted", "polkit",
            {"action": POLKIT_ACTION, "uid": subject.uid, "session_id": subject.session_id,
             "pid": subject.pid, "start_time": subject.start_time, "digest": plan.digest},
        )
