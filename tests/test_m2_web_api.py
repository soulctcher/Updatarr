"""Authenticated M2 catalog, saved-choice, safety and history API evidence."""

from __future__ import annotations

from pathlib import Path
import sys
import time

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from updatarr.app import AppConfig, create_app  # noqa: E402
from updatarr.domain import SYSTEM_UPDATE_GROUP_ID  # noqa: E402


def _client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(AppConfig(
        password="test-only-password",
        public_origin="http://testserver",
        storage_path=tmp_path / "state.db",
        provider_mode="simulator",
    )))


def _login(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/session", headers={"Origin": "http://testserver"},
        json={"password": "test-only-password"},
    )
    assert response.status_code == 200
    return {"Origin": "http://testserver", "X-CSRF-Token": response.json()["csrf_token"]}


def _check_and_wait(client: TestClient, headers: dict[str, str]) -> dict:
    prior = client.get("/api/v1/overview").json().get("snapshot")
    prior_id = prior.get("snapshot_id") if prior else None
    assert client.post("/api/v1/checks", headers=headers).status_code == 202
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        overview = client.get("/api/v1/overview").json()
        if overview["snapshot"] and overview["snapshot"]["snapshot_id"] != prior_id:
            return overview
        time.sleep(.02)
    raise AssertionError("simulated check did not complete")


def test_catalog_requires_sign_in_and_preserves_source_choices(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        assert client.get("/api/v1/catalog?q=kdenlive").status_code == 401
        assert client.get("/api/v1/catalog/aur/kdenlive-git/build-preview").status_code == 401
        assert client.get("/api/v1/advisories").status_code == 401
        _login(client)
        response = client.get("/api/v1/catalog?q=kdenlive")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 4
        assert len({item["catalog_id"] for item in body["items"]}) == 4
        assert all("<" not in (item["summary"] or "") for item in body["items"])
        preview = client.get("/api/v1/catalog/aur/kdenlive-git/build-preview")
        assert preview.status_code == 200
        assert preview.json()["comparison_state"] == "no_earlier_copy"
        assert preview.json()["simulated"] is True
        assert client.get("/api/v1/catalog?q=x").status_code == 400
        advisory = client.get("/api/v1/advisories").json()["items"][0]
        assert advisory["source_name"] == "Arch Linux news"
        assert advisory["simulated"] is True


def test_saved_choices_persist_apply_and_are_audited(tmp_path: Path) -> None:
    state_path = tmp_path / "state.db"
    with _client(tmp_path) as client:
        headers = _login(client)
        overview = _check_and_wait(client, headers)
        policy = client.post("/api/v1/policies", headers=headers, json={
            "kind": "postpone", "source_id": "native", "scope": "system",
            "software_id": SYSTEM_UPDATE_GROUP_ID, "reason": "Wait for the weekend",
        })
        assert policy.status_code == 201
        updates = client.get("/api/v1/updates").json()
        assert updates["saved_choices"]["postponed"] == 2
        assert {item["state"] for item in updates["items"] if item["source_id"] == "native"} == {"postponed"}
        assert overview["snapshot"] is not None
        policy_id = policy.json()["policy"]["policy_id"]

    with TestClient(create_app(AppConfig(
        password="test-only-password",
        public_origin="http://testserver", storage_path=state_path, provider_mode="simulator",
    ))) as client:
        headers = _login(client)
        assert client.get("/api/v1/policies").json()["total"] == 1
        assert client.delete(f"/api/v1/policies/{policy_id}", headers=headers).status_code == 200
        kinds = {item["kind"] for item in client.get("/api/v1/history").json()["items"]}
        assert {"saved_choice_added", "saved_choice_removed"}.issubset(kinds)


def test_native_subset_is_blocked_without_execution_surface(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        headers = _login(client)
        overview = _check_and_wait(client, headers)
        updates = client.get("/api/v1/updates").json()["items"]
        native = [item for item in updates if item["source_id"] == "native"]
        blocked = client.post("/api/v1/update-selection/check", headers=headers, json={
            "snapshot_id": overview["snapshot"]["snapshot_id"],
            "selected_stable_ids": [native[0]["stable_id"]],
        })
        assert blocked.status_code == 200
        assert blocked.json()["allowed"] is False
        allowed = client.post("/api/v1/update-selection/check", headers=headers, json={
            "snapshot_id": overview["snapshot"]["snapshot_id"],
            "selected_stable_ids": [item["stable_id"] for item in native],
        })
        assert allowed.json()["allowed"] is True
        saved_skip = client.post("/api/v1/policies", headers=headers, json={
            "kind": "skip_version", "source_id": "native", "scope": "system",
            "software_id": native[0]["software_id"], "version": native[0]["available_version"],
            "target_stable_id": native[0]["stable_id"],
        })
        assert saved_skip.status_code == 201
        held = client.post("/api/v1/update-selection/check", headers=headers, json={
            "snapshot_id": overview["snapshot"]["snapshot_id"],
            "selected_stable_ids": [item["stable_id"] for item in native],
        })
        assert held.json()["allowed"] is False
        assert "saved choice" in held.json()["message"].lower()
        assert client.post("/api/v1/update-selection/check", headers=headers, json={
            "snapshot_id": "old", "selected_stable_ids": [],
        }).status_code == 409
        routes = {route.path for route in client.app.routes}
        execution_routes = {path for path in routes if "execute" in path or "install" in path}
        assert execution_routes == {"/api/v1/local/plans/{plan_id}/execute"}


def test_turning_off_source_skips_check_and_keeps_last_information(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        headers = _login(client)
        _check_and_wait(client, headers)
        response = client.put(
            "/api/v1/settings/update-sources/flatpak/user",
            headers=headers, json={"enabled": False},
        )
        assert response.status_code == 200
        prior = client.get("/api/v1/inventory?limit=500").json()["total"]
        _check_and_wait(client, headers)
        overview = client.get("/api/v1/overview").json()
        flatpak = next(
            source for source in overview["sources"]
            if source["source_id"] == "flatpak" and source["scope"] == "user"
        )
        assert flatpak["state"] == "turned_off"
        assert flatpak["software_count"] == 1
        assert client.get("/api/v1/inventory?limit=500").json()["total"] == prior
        catalog = client.get("/api/v1/catalog?q=kdenlive&source_id=flatpak&scope=user").json()
        assert catalog["total"] == 0 and catalog["sources"][0]["state"] == "turned_off"


def test_history_import_is_idempotent_and_does_not_claim_completeness(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        headers = _login(client)
        first = client.post("/api/v1/history/import", headers=headers)
        second = client.post("/api/v1/history/import", headers=headers)
        assert first.json() == {"found": 3, "added": 3, "batches_added": 1}
        assert second.json() == {"found": 3, "added": 0, "batches_added": 0}
        history = client.get("/api/v1/history?limit=100").json()
        assert history["imported_total"] == 3
        assert history["import_batches"][0]["status"] == "incomplete"
        assert history["import_batches"][0]["reason"]
        assert all(item["completeness"] == "partial" for item in history["imported_items"])
        assert history["summary"]["download_bytes"] is None
        assert history["summary"]["download_data_label"] == "No download data recorded"


def test_all_m2_mutations_require_csrf(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        _login(client)
        for method, path, body in (
            ("post", "/api/v1/policies", {"kind": "turn_off_source", "source_id": "native", "scope": "system"}),
            ("put", "/api/v1/settings/update-sources/native/system", {"enabled": False}),
            ("post", "/api/v1/history/import", None),
            ("post", "/api/v1/update-selection/check", {"snapshot_id": "x", "selected_stable_ids": []}),
        ):
            response = getattr(client, method)(path, headers={"Origin": "http://testserver"}, json=body)
            assert response.status_code == 403, path
