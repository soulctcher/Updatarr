"""Managed-computer review surface for one frozen plan.

This provisional terminal surface is intentionally separate from the browser.
It records the local Unix identity and session. M5 may replace its presentation
with the KDE companion while preserving this boundary.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from .domain import PlanState
from .planning import Planner
from .storage import StateStore


class LocalApprovalError(ValueError):
    pass


class LocalApprovalService:
    def __init__(self, store: StateStore, *, uid: int, session_id: str) -> None:
        self.store = store
        self.uid = uid
        self.session_id = session_id

    def decide(self, plan_id: str, *, approve: bool) -> PlanState:
        stored = self.store.plan(plan_id)
        if stored is None:
            raise LocalApprovalError("That update plan was not found.")
        plan, state = stored
        if state is not PlanState.AWAITING_LOCAL_CONFIRMATION:
            raise LocalApprovalError("That plan is not waiting for a decision on this computer.")
        if approve:
            validation = Planner().validate(plan, self.store.latest_snapshot(), self.store.policies())
            if not validation.valid:
                self.store.transition_plan(plan_id, state, validation.state, "plan_validation_failed",
                                           "local-approval", {"reason": validation.message})
                raise LocalApprovalError(validation.message)
            requested = PlanState.AWAITING_AUTHORIZATION if plan.requires_administrator else PlanState.READY_FOR_EXECUTION
            kind = "confirmed_on_managed_computer"
        else:
            requested = PlanState.INVALIDATED
            kind = "rejected_on_managed_computer"
        return self.store.transition_plan(
            plan_id, state, requested, kind, "local-approval",
            {"digest": plan.digest, "uid": self.uid, "session_id": self.session_id},
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Review one Updatarr plan on the managed computer")
    parser.add_argument("--state", type=Path, required=True, help="Path to the Updatarr state database")
    parser.add_argument("--plan", required=True, help="Exact plan ID shown by Updatarr")
    args = parser.parse_args()
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise SystemExit("Local approval requires an interactive terminal on the managed computer.")
    store = StateStore(args.state)
    stored = store.plan(args.plan)
    if stored is None:
        raise SystemExit("That update plan was not found.")
    plan, state = stored
    if state is not PlanState.AWAITING_LOCAL_CONFIRMATION:
        raise SystemExit("That plan is not waiting for confirmation on this computer.")
    print(f"Plan: {plan.plan_id}\nReview code: {plan.digest}\nExpires: {plan.expires_at}")
    for index, step in enumerate(plan.steps, 1):
        permission = "Administrator permission" if step.permission.value == "administrator" else "Current user"
        print(f"{index}. {step.summary}\n   {', '.join(step.package_ids)}\n   Permission: {permission}")
    answer = input("Confirm this exact plan on this computer? Type CONFIRM or REJECT: ").strip()
    if answer not in {"CONFIRM", "REJECT"}:
        raise SystemExit("No decision recorded.")
    session_id = Path("/proc/self/sessionid").read_text(encoding="utf-8").strip()
    result = LocalApprovalService(store, uid=os.getuid(), session_id=session_id).decide(
        plan.plan_id, approve=answer == "CONFIRM",
    )
    result_label = {
        PlanState.AWAITING_AUTHORIZATION: "Waiting for administrator permission",
        PlanState.READY_FOR_EXECUTION: "Ready to start",
        PlanState.INVALIDATED: "Plan rejected",
    }.get(result, "Decision recorded")
    print(f"Result: {result_label}")


if __name__ == "__main__":
    main()
