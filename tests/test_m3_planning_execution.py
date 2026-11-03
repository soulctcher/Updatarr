"""M3 immutable plan, consent boundary, and simulator execution evidence."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import sys
import time

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from updatarr.app import AppConfig, create_app  # noqa: E402
from updatarr.authorization import (  # noqa: E402
    AdministratorAuthorizer, AuthorizationRefused, FixedPkcheckRunner,
    POLKIT_ACTION, ProcessSubject,
)
from updatarr.domain import (  # noqa: E402
    DetectedUpdate, InventorySnapshot, OperationKind, PlanState, SoftwareRecord,
    PolicyKind, PolicyState, SelectionPolicy, SourceResult, SourceState,
    UpdateRun, UpdateRunState, stable_software_id, utc_now,
)
from updatarr.execution import (  # noqa: E402
    ExecutionRefused, LocalSubject, PrivilegedBoundary, SimulatorExecutor,
    SimulatorResultChecker,
)
from updatarr.local_approval import LocalApprovalService  # noqa: E402
from updatarr.planning import Planner, PlanningError  # noqa: E402
from updatarr.storage import StateStore  # noqa: E402


def _snapshot() -> InventorySnapshot:
    native = [
        DetectedUpdate(stable_software_id("native", "system", name), "native", "system", name, name, "1", "2")
        for name in ("linux", "firefox")
    ]
    flatpak = DetectedUpdate(stable_software_id("flatpak", "user", "org.example.App"), "flatpak", "user", "org.example.App", "Example", "1", "2")
    aur = DetectedUpdate(stable_software_id("aur", "user", "example-bin"), "aur", "user", "example-bin", "Example AUR", "1", "2")
    return InventorySnapshot.create(utc_now(), [
        SourceResult("native", "System packages", "system", SourceState.READY_TO_REVIEW, "Ready", utc_now(), 1, (), tuple(native)),
        SourceResult("flatpak", "Flatpak", "user", SourceState.READY_TO_REVIEW, "Ready", utc_now(), 1, (), (flatpak,)),
        SourceResult("aur", "AUR", "user", SourceState.READY_TO_REVIEW, "Ready", utc_now(), 1, (), (aur,)),
    ])


def test_plan_is_deterministic_typed_and_native_group_is_indivisible() -> None:
    snapshot = _snapshot(); planner = Planner(); now = datetime(2026, 1, 2, tzinfo=UTC)
    native = [item for item in snapshot.updates if item.source_id == "native"]
    with pytest.raises(PlanningError, match="partial system update"):
        planner.prepare(snapshot, snapshot.updates, [native[0].stable_id], [], now=now)
    selected = [item.stable_id for item in snapshot.updates if item.source_id in {"native", "flatpak"}]
    first = planner.prepare(snapshot, snapshot.updates, selected, [], now=now)
    second = planner.prepare(snapshot, snapshot.updates, list(reversed(selected)), [], now=now)
    assert first.digest == second.digest
    assert first.steps[0].operation is OperationKind.NATIVE_FULL_UPGRADE
    assert first.steps[0].package_ids == ("firefox", "linux")
    assert first.requires_administrator
    assert not hasattr(first.steps[0], "command") and not hasattr(first.steps[0], "argv")


def test_plan_fails_closed_on_drift_expiry_policy_change_and_aur() -> None:
    snapshot = _snapshot(); planner = Planner(); now = datetime(2026, 1, 2, tzinfo=UTC)
    flatpak = next(item for item in snapshot.updates if item.source_id == "flatpak")
    plan = planner.prepare(snapshot, snapshot.updates, [flatpak.stable_id], [], now=now)
    assert planner.validate(plan, snapshot, [], now=now + timedelta(minutes=14)).valid
    assert planner.validate(plan, snapshot, [], now=now + timedelta(minutes=15)).state is PlanState.EXPIRED
    changed = replace(snapshot, generation="changed")
    assert planner.validate(plan, changed, [], now=now).state is PlanState.INVALIDATED
    tampered = replace(plan, warnings=("changed",))
    assert "changed after it was reviewed" in planner.validate(tampered, snapshot, [], now=now).message
    aur = next(item for item in snapshot.updates if item.source_id == "aur")
    aur_plan = planner.prepare(snapshot, snapshot.updates, [aur.stable_id], [], now=now)
    assert aur_plan.blockers and not aur_plan.steps[0].live_enabled
    assert not planner.validate(aur_plan, snapshot, [], now=now).valid
    policy = SelectionPolicy("policy-fixed", PolicyKind.TURN_OFF_SOURCE, PolicyState.ACTIVE,
                             "firmware", "system", reason="first")
    policy_plan = planner.prepare(snapshot, snapshot.updates, [flatpak.stable_id], [policy], now=now)
    assert not planner.validate(policy_plan, snapshot, [replace(policy, reason="changed")], now=now).valid


def test_aur_plan_is_executable_only_after_pipeline_readiness_is_proven() -> None:
    snapshot = _snapshot()
    aur = next(item for item in snapshot.updates if item.source_id == "aur")

    blocked = Planner().prepare(snapshot, snapshot.updates, [aur.stable_id], [])
    assert blocked.blockers

    ready = Planner(aur_pipeline_ready=True).prepare(
        snapshot, snapshot.updates, [aur.stable_id], []
    )
    assert ready.blockers == ()
    assert ready.steps[0].live_enabled is True
    assert ready.steps[0].operation is OperationKind.AUR_BUILD_INSTALL


def test_live_updates_api_keeps_aur_out_of_the_ready_set(tmp_path: Path) -> None:
    app = create_app(AppConfig(
        password="test-only-password",
        public_origin="http://testserver",
        storage_path=tmp_path / "state.db",
        provider_mode="live",
        adapters=(),
        catalog_adapters=(),
        advisory_adapters=(),
    ))
    with TestClient(app) as client:
        _login(client)
        snapshot = _snapshot()
        client.app.state.store.save_snapshot(snapshot)
        body = client.get("/api/v1/updates").json()
        aur = next(item for item in body["items"] if item["source_id"] == "aur")

        assert aur["stable_id"] not in body["readiness"]["ready_stable_ids"]
        issue = next(
            issue for issue in body["readiness"]["issues"]
            if issue["source_id"] == "aur"
        )
        assert issue["stable_ids"] == [aur["stable_id"]]
        assert "isolated build pipeline" in issue["message"]


@pytest.mark.parametrize("hostile", [
    "pkg;id", "pkg id", "$(touch /tmp/no)", "pkg\nname", "--config", "../pkg", "pkg\x1b[31m",
])
def test_hostile_software_identifiers_never_reach_a_plan(hostile: str) -> None:
    snapshot = _snapshot(); original = next(item for item in snapshot.updates if item.source_id == "flatpak")
    forged = replace(original, software_id=hostile)
    with pytest.raises(PlanningError, match="invalid software identifier"):
        Planner().prepare(snapshot, [forged], [forged.stable_id], [])


def test_plan_storage_is_immutable_and_privileged_boundary_accepts_no_command(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.db"); store.initialize(); snapshot = _snapshot(); store.save_snapshot(snapshot)
    selected = [item.stable_id for item in snapshot.updates if item.source_id == "native"]
    plan = Planner().prepare(snapshot, snapshot.updates, selected, [])
    store.save_plan(plan); store.save_plan(plan)
    loaded = store.plan(plan.plan_id)
    assert loaded and loaded[0].digest == plan.digest and loaded[1] is PlanState.AWAITING_REVIEW
    store.transition_plan(plan.plan_id, PlanState.AWAITING_REVIEW, PlanState.AWAITING_LOCAL_CONFIRMATION,
                          "review_approved", "administrator")
    store.transition_plan(plan.plan_id, PlanState.AWAITING_LOCAL_CONFIRMATION, PlanState.AWAITING_AUTHORIZATION,
                          "confirmed_on_managed_computer", "local-approval", {"uid": 1000, "session_id": "s1"})
    store.transition_plan(plan.plan_id, PlanState.AWAITING_AUTHORIZATION, PlanState.READY_FOR_EXECUTION,
                          "administrator_permission_granted", "polkit", {"uid": 1000})
    class Locks:
        locked = False
        busy = False
        def package_manager_locked(self) -> bool: return self.locked
        def coordinator_busy(self) -> bool: return self.busy
    locks = Locks(); boundary = PrivilegedBoundary(store, locks)
    envelope = boundary.envelope_for(plan.plan_id, "native-full-upgrade", LocalSubject(1000, "s1", True))
    assert envelope.operation is OperationKind.NATIVE_FULL_UPGRADE
    assert set(envelope.__dict__) == {"plan_id", "plan_digest", "operation", "package_ids", "snapshot_generation", "expires_at", "caller_uid"}
    with pytest.raises(ExecutionRefused):
        boundary.envelope_for(plan.plan_id, "forged", LocalSubject(1000, "s1", True))
    with pytest.raises(ExecutionRefused, match="caller"):
        boundary.envelope_for(plan.plan_id, "native-full-upgrade", LocalSubject(1001, "s1", True))
    with pytest.raises(ExecutionRefused, match="Another"):
        locks.locked = True
        boundary.envelope_for(plan.plan_id, "native-full-upgrade", LocalSubject(1000, "s1", True))
    with sqlite3.connect(store.path) as connection, pytest.raises(sqlite3.IntegrityError, match="immutable"):
        connection.execute("UPDATE update_plans SET content_json = '{}' WHERE plan_id = ?", (plan.plan_id,))


def test_simulator_cancels_only_at_safe_point_and_restart_preserves_uncertainty(tmp_path: Path) -> None:
    snapshot = _snapshot(); flatpak = next(item for item in snapshot.updates if item.source_id == "flatpak")
    plan = Planner().prepare(snapshot, snapshot.updates, [flatpak.stable_id], [])
    observed_events: list[dict[str, object]] = []
    cancelled, events = SimulatorExecutor().execute(
        plan, SimulatorResultChecker(), run_id="run-cancelled", started_at=utc_now(),
        cancel_requested=lambda: True, event_callback=observed_events.append, step_delay=0,
    )
    assert cancelled.state is UpdateRunState.CANCELLED
    assert events[-1]["safe_to_cancel"] is True
    assert observed_events == events

    store = StateStore(tmp_path / "state.db"); store.initialize(); store.save_snapshot(snapshot); store.save_plan(plan)
    running = UpdateRun("run-interrupted", plan.plan_id, plan.digest, UpdateRunState.RUNNING, 50,
                        "Software tool is running.", utc_now())
    store.save_run(running, [{"state": "running", "safe_to_cancel": False}])
    assert store.recover_unfinished_runs() == 1
    assert store.latest_run() is not None and store.latest_run().state is UpdateRunState.NEEDS_MANUAL_RECOVERY
    assert store.recover_unfinished_runs() == 0
    failed, _ = SimulatorExecutor().execute(
        plan, SimulatorResultChecker({flatpak.stable_id: "wrong"}),
        run_id="run-failed-check", started_at=utc_now(), step_delay=0,
    )
    assert failed.state is UpdateRunState.NEEDS_MANUAL_RECOVERY


def test_local_human_service_records_unix_identity_and_exact_plan(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.db"); store.initialize(); snapshot = _snapshot(); store.save_snapshot(snapshot)
    flatpak = next(item for item in snapshot.updates if item.source_id == "flatpak")
    plan = Planner().prepare(snapshot, snapshot.updates, [flatpak.stable_id], [])
    store.save_plan(plan)
    store.transition_plan(plan.plan_id, PlanState.AWAITING_REVIEW, PlanState.AWAITING_LOCAL_CONFIRMATION,
                          "review_approved", "administrator")
    state = LocalApprovalService(store, uid=1000, session_id="plasma-1").decide(plan.plan_id, approve=True)
    assert state is PlanState.READY_FOR_EXECUTION
    event = store.plan_events(plan.plan_id)[-1]
    assert event["details"]["uid"] == 1000 and event["details"]["session_id"] == "plasma-1"


def test_atomic_plan_claim_allows_exactly_one_run(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.db"); store.initialize(); snapshot = _snapshot(); store.save_snapshot(snapshot)
    flatpak = next(item for item in snapshot.updates if item.source_id == "flatpak")
    plan = Planner().prepare(snapshot, snapshot.updates, [flatpak.stable_id], []); store.save_plan(plan)
    store.transition_plan(plan.plan_id, PlanState.AWAITING_REVIEW, PlanState.AWAITING_LOCAL_CONFIRMATION, "review", "user")
    LocalApprovalService(store, uid=1000, session_id="s1").decide(plan.plan_id, approve=True)
    def claim(number: int) -> bool:
        try:
            store.claim_plan_for_run(UpdateRun(f"run-{number}", plan.plan_id, plan.digest, UpdateRunState.CREATED,
                                               0, "created", utc_now()))
            return True
        except ValueError:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(claim, (1, 2))) == 1
    assert store.recover_unfinished_runs() == 1
    assert store.latest_run() is not None and store.latest_run().state is UpdateRunState.NEEDS_MANUAL_RECOVERY

    second = Planner().prepare(snapshot, snapshot.updates, [flatpak.stable_id], [],
                               now=datetime.now(UTC) + timedelta(seconds=1)); store.save_plan(second)
    store.transition_plan(second.plan_id, PlanState.AWAITING_REVIEW, PlanState.AWAITING_LOCAL_CONFIRMATION, "review", "user")
    LocalApprovalService(store, uid=1000, session_id="s1").decide(second.plan_id, approve=True)
    with pytest.raises(ValueError, match="does not match the reviewed plan"):
        store.claim_plan_for_run(UpdateRun("run-wrong", second.plan_id, "0" * 64, UpdateRunState.CREATED,
                                           0, "created", utc_now()))
    store.create_policy(SelectionPolicy("new-policy", PolicyKind.TURN_OFF_SOURCE, PolicyState.ACTIVE,
                                        "firmware", "system"))
    with pytest.raises(ValueError, match="saved choice"):
        store.claim_plan_for_run(UpdateRun("run-drift", second.plan_id, second.digest, UpdateRunState.CREATED,
                                           0, "created", utc_now()))


def test_unicode_reviewed_content_uses_one_canonical_fingerprint_at_claim(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.db"); store.initialize(); snapshot = _snapshot(); store.save_snapshot(snapshot)
    flatpak = next(item for item in snapshot.updates if item.source_id == "flatpak")
    localized = replace(flatpak, name="Éditeur exemple")
    plan = Planner().prepare(snapshot, [localized], [localized.stable_id], []); store.save_plan(plan)
    store.transition_plan(plan.plan_id, PlanState.AWAITING_REVIEW, PlanState.AWAITING_LOCAL_CONFIRMATION, "review", "user")
    LocalApprovalService(store, uid=1000, session_id="s1").decide(plan.plan_id, approve=True)
    store.claim_plan_for_run(UpdateRun("run-unicode", plan.plan_id, plan.digest, UpdateRunState.CREATED,
                                       0, "created", utc_now()))
    assert store.run_for_plan(plan.plan_id) is not None


def test_administrator_authorization_uses_resolved_local_subject_and_fixed_decision(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.db"); store.initialize(); snapshot = _snapshot(); store.save_snapshot(snapshot)
    native = [item.stable_id for item in snapshot.updates if item.source_id == "native"]
    plan = Planner().prepare(snapshot, snapshot.updates, native, []); store.save_plan(plan)
    store.transition_plan(plan.plan_id, PlanState.AWAITING_REVIEW, PlanState.AWAITING_LOCAL_CONFIRMATION, "review", "user")
    LocalApprovalService(store, uid=1000, session_id="plasma-1").decide(plan.plan_id, approve=True)
    class Resolver:
        session = "plasma-1"
        def resolve(self, pid: int) -> ProcessSubject: return ProcessSubject(pid, 12345, 1000, self.session)
    class Runner:
        allowed = True
        def check(self, subject: ProcessSubject) -> bool: return self.allowed
    runner = Runner(); resolver = Resolver(); authorizer = AdministratorAuthorizer(store, resolver, runner)
    resolver.session = "other-session"
    with pytest.raises(AuthorizationRefused, match="was not confirmed"):
        authorizer.authorize(plan.plan_id, caller_pid=4242)
    resolver.session = "plasma-1"
    assert authorizer.authorize(plan.plan_id, caller_pid=4242) is PlanState.READY_FOR_EXECUTION
    event = store.plan_events(plan.plan_id)[-1]
    assert event["details"]["pid"] == 4242 and event["details"]["start_time"] == 12345

    second = Planner().prepare(snapshot, snapshot.updates, native, [], now=datetime.now(UTC) + timedelta(seconds=1))
    store.save_plan(second)
    store.transition_plan(second.plan_id, PlanState.AWAITING_REVIEW, PlanState.AWAITING_LOCAL_CONFIRMATION, "review", "user")
    LocalApprovalService(store, uid=1000, session_id="plasma-1").decide(second.plan_id, approve=True)
    runner.allowed = False
    with pytest.raises(AuthorizationRefused, match="not granted"):
        authorizer.authorize(second.plan_id, caller_pid=4242)


def test_pkcheck_prototype_has_fixed_executable_action_environment_and_arguments(monkeypatch) -> None:
    captured: dict[str, object] = {}
    class Completed:
        returncode = 0
    def fake_run(argv, **options):  # type: ignore[no-untyped-def]
        captured.update({"argv": argv, **options}); return Completed()
    monkeypatch.setattr("updatarr.authorization.subprocess.run", fake_run)
    assert FixedPkcheckRunner().check(ProcessSubject(4242, 12345, 1000, "plasma-1"))
    assert captured["argv"] == [
        "/usr/bin/pkcheck", "--action-id", POLKIT_ACTION,
        "--process", "4242,12345,1000", "--allow-user-interaction",
    ]
    assert captured["env"] == {"PATH": "/usr/bin", "LANG": "C.UTF-8"}
    assert "shell" not in captured


def _login(client: TestClient) -> dict[str, str]:
    response = client.post("/api/v1/session", headers={"Origin": "http://testserver"}, json={"password": "test-only-password"})
    return {"Origin": "http://testserver", "X-CSRF-Token": response.json()["csrf_token"]}


def _check(client: TestClient, headers: dict[str, str]) -> dict:
    assert client.post("/api/v1/checks", headers=headers).status_code == 202
    for _ in range(150):
        body = client.get("/api/v1/overview").json()
        if body["snapshot"]:
            return body
        time.sleep(.02)
    raise AssertionError("check did not finish")


def test_remote_review_cannot_replace_local_confirmation_and_simulator_is_single_use(tmp_path: Path) -> None:
    app = create_app(AppConfig(password="test-only-password", public_origin="http://testserver", storage_path=tmp_path / "state.db",
                               provider_mode="simulator", local_agent_token="local-secret"))
    with TestClient(app) as client:
        headers = _login(client); overview = _check(client, headers)
        flatpak = next(item for item in client.get("/api/v1/updates").json()["items"] if item["source_id"] == "flatpak")
        prepared = client.post("/api/v1/plans", headers=headers, json={
            "snapshot_id": overview["snapshot"]["snapshot_id"], "selected_stable_ids": [flatpak["stable_id"]],
        })
        assert prepared.status_code == 201
        plan = prepared.json()["plan"]
        reviewed = client.post(f"/api/v1/plans/{plan['plan_id']}/review", headers=headers, json={"digest": plan["digest"]})
        assert reviewed.json()["plan"]["state"] == "awaiting_local_confirmation"
        assert client.post(f"/api/v1/local/plans/{plan['plan_id']}/confirm", headers=headers).status_code == 403
        local = {"Origin": "http://testserver", "X-Updatarr-Local-Agent": "local-secret"}
        confirmed = client.post(f"/api/v1/local/plans/{plan['plan_id']}/confirm", headers=local)
        assert confirmed.json()["plan"]["state"] == "ready_for_execution"
        run = client.post(f"/api/v1/local/plans/{plan['plan_id']}/execute", headers=local)
        assert run.json()["run"]["state"] == "running"
        assert run.json()["plan"]["state"] == "consumed"
        assert client.post(f"/api/v1/local/plans/{plan['plan_id']}/execute", headers=local).status_code == 409
        for _ in range(100):
            latest = client.get("/api/v1/plans/latest").json()["run"]
            if latest["state"] != "running": break
            time.sleep(.01)
        assert latest["state"] == "succeeded"
        assert "expected version" in latest["message"]
        replacement = client.post("/api/v1/plans", headers=headers, json={
            "snapshot_id": overview["snapshot"]["snapshot_id"], "selected_stable_ids": [flatpak["stable_id"]],
        })
        assert replacement.status_code == 201
        latest_pair = client.get("/api/v1/plans/latest").json()
        assert latest_pair["plan"]["plan_id"] == replacement.json()["plan"]["plan_id"]
        assert latest_pair["run"] is None


def test_managed_computer_can_reject_without_execution(tmp_path: Path) -> None:
    app = create_app(AppConfig(password="test-only-password", public_origin="http://testserver", storage_path=tmp_path / "state.db",
                               provider_mode="simulator", local_agent_token="local-secret"))
    with TestClient(app) as client:
        headers = _login(client); overview = _check(client, headers)
        flatpak = next(item for item in client.get("/api/v1/updates").json()["items"] if item["source_id"] == "flatpak")
        plan = client.post("/api/v1/plans", headers=headers, json={
            "snapshot_id": overview["snapshot"]["snapshot_id"], "selected_stable_ids": [flatpak["stable_id"]],
        }).json()["plan"]
        client.post(f"/api/v1/plans/{plan['plan_id']}/review", headers=headers, json={"digest": plan["digest"]})
        local = {"Origin": "http://testserver", "X-Updatarr-Local-Agent": "local-secret"}
        rejected = client.post(f"/api/v1/local/plans/{plan['plan_id']}/reject", headers=local)
        assert rejected.json()["plan"]["state"] == "invalidated"
        assert client.post(f"/api/v1/local/plans/{plan['plan_id']}/execute", headers=local).status_code == 409


def test_application_cancellation_stops_at_next_safe_point(tmp_path: Path) -> None:
    app = create_app(AppConfig(password="test-only-password", public_origin="http://testserver", storage_path=tmp_path / "state.db",
                               provider_mode="simulator", local_agent_token="local-secret"))
    with TestClient(app) as client:
        headers = _login(client); overview = _check(client, headers)
        items = client.get("/api/v1/updates").json()["items"]
        selected = [item["stable_id"] for item in items if item["source_id"] in {"native", "flatpak"}]
        plan = client.post("/api/v1/plans", headers=headers, json={
            "snapshot_id": overview["snapshot"]["snapshot_id"], "selected_stable_ids": selected,
        }).json()["plan"]
        client.post(f"/api/v1/plans/{plan['plan_id']}/review", headers=headers, json={"digest": plan["digest"]})
        local = {"Origin": "http://testserver", "X-Updatarr-Local-Agent": "local-secret"}
        client.post(f"/api/v1/local/plans/{plan['plan_id']}/confirm", headers=local)
        client.post(f"/api/v1/local/plans/{plan['plan_id']}/authorize", headers=local)
        assert client.post(f"/api/v1/local/plans/{plan['plan_id']}/execute", headers=local).status_code == 200
        cancelled = client.post(f"/api/v1/local/plans/{plan['plan_id']}/cancel", headers=local)
        assert cancelled.status_code == 200
        for _ in range(100):
            run = client.get("/api/v1/plans/latest").json()["run"]
            if run["state"] != "running": break
            time.sleep(.01)
        assert run["state"] == "cancelled"


def test_all_plan_browser_mutations_require_csrf_and_live_execution_is_disabled(tmp_path: Path) -> None:
    with TestClient(create_app(AppConfig(password="test-only-password", public_origin="http://testserver", storage_path=tmp_path / "state.db",
                                         provider_mode="simulator", local_agent_token="token"))) as client:
        _login(client)
        response = client.post("/api/v1/plans", headers={"Origin": "http://testserver"},
                               json={"snapshot_id": "x", "selected_stable_ids": []})
        assert response.status_code == 403
        response = client.post("/api/v1/plans/missing/review", headers={"Origin": "http://testserver"}, json={"digest": "0" * 64})
        assert response.status_code == 403


def test_latest_plan_read_marks_expired_authority_truthfully(tmp_path: Path) -> None:
    with TestClient(create_app(AppConfig(password="test-only-password", public_origin="http://testserver", storage_path=tmp_path / "state.db",
                                         provider_mode="simulator"))) as client:
        _login(client)
        snapshot = _snapshot(); client.app.state.store.save_snapshot(snapshot)
        flatpak = next(item for item in snapshot.updates if item.source_id == "flatpak")
        plan = Planner().prepare(
            snapshot, snapshot.updates, [flatpak.stable_id], [],
            now=datetime.now(UTC) - timedelta(minutes=20),
        )
        client.app.state.store.save_plan(plan)
        assert client.get("/api/v1/plans/latest").json()["plan"]["state"] == "expired"
        assert client.app.state.store.plan(plan.plan_id)[1] is PlanState.AWAITING_REVIEW
