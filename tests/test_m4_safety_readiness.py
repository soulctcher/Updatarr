"""M4 firmware, boot, portable-app, tool and maintenance safety evidence."""

from __future__ import annotations

from pathlib import Path
import json
import sys

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from updatarr.app import AppConfig, create_app  # noqa: E402
from updatarr.m4 import (  # noqa: E402
    Readiness, RestartAction, assess_appimage, assess_boot,
    firmware_follow_up_actions, firmware_restart_action, parse_firmware_releases, prepare_portable_replacement,
    simulate_portable_replacement, live_read_only_report, firmware_capability,
)
from updatarr.providers.adapters import (  # noqa: E402
    AppImageAdapter, CargoToolsAdapter, FnmAdapter, NpmGlobalsAdapter, UvToolsAdapter,
)
from updatarr.providers.probes import FixtureProbeClient  # noqa: E402
from updatarr.domain import DetectedUpdate, InventorySnapshot, OperationKind, SourceResult, SourceState, stable_software_id, utc_now  # noqa: E402
from updatarr.planning import Planner  # noqa: E402


@pytest.mark.parametrize(("flags", "expected"), [
    (["needs-shutdown"], RestartAction.SHUT_DOWN),
    (["needs-reboot"], RestartAction.RESTART),
    (["needs-replug"], RestartAction.REPLUG),
    (["needs-activation"], RestartAction.ACTIVATE),
    (["only-offline"], RestartAction.OFFLINE),
    (["will-disappear"], RestartAction.DISAPPEAR),
    (["needs-new-physical-step"], RestartAction.UNKNOWN),
    ([], RestartAction.NONE),
])
def test_firmware_requirements_stay_distinct(flags: list[str], expected: RestartAction) -> None:
    assert firmware_restart_action(flags) is expected


def test_firmware_json_is_bounded_and_fails_closed() -> None:
    payload = {"Devices": [{
        "DeviceId": "device-1", "Name": "System firmware", "Version": "1",
        "Flags": ["needs-reboot"], "Problems": ["requires-ac"],
        "Releases": [{"Version": "2", "Flags": [], "ReleaseId": "release-2",
                      "Checksum": ["sha256:abc"], "RemoteId": "lvfs",
                      "RemoteEnabled": True, "Trusted": True}],
    }]}
    release = parse_firmware_releases(json.dumps(payload))[0]
    assert release["device_id"] == "device-1"
    assert release["restart_action"] == "restart"
    assert release["follow_up_actions"] == ["restart"] and release["unknown_flags"] == []
    assert release["problems"] == ["requires-ac"]
    assert release["readiness"] == "blocked" and release["release_id"] == "release-2"
    with pytest.raises(ValueError, match="could not be read"):
        parse_firmware_releases("not-json")
    with pytest.raises(ValueError, match="recognizable device ID"):
        parse_firmware_releases(json.dumps({"Devices": [{"Releases": [{"Version": "2"}]}]}))


def test_firmware_combined_and_unknown_requirements_are_not_flattened() -> None:
    flags = ["needs-reboot", "needs-activation"]
    assert firmware_restart_action(flags) is RestartAction.UNKNOWN
    assert firmware_follow_up_actions(flags) == (RestartAction.RESTART, RestartAction.ACTIVATE)
    payload = {"Devices": [{"DeviceId": "device", "Flags": ["future-safety-requirement"],
                             "Releases": [{"Version": "2"}]}]}
    release = parse_firmware_releases(json.dumps(payload))[0]
    assert release["restart_action"] == "unknown"
    assert release["unknown_flags"] == ["future-safety-requirement"]


def test_firmware_below_battery_threshold_is_blocked_without_problem_string() -> None:
    payload = {"Devices": [{"DeviceId": "device", "BatteryLevel": 10, "BatteryThreshold": 50,
                             "Flags": [], "Problems": [], "Releases": [{"Version": "2",
                             "ReleaseId": "release-2", "Checksum": ["sha256:abc"],
                             "RemoteId": "lvfs", "RemoteEnabled": True, "Trusted": True}]}]}
    release = parse_firmware_releases(json.dumps(payload))[0]
    capability = firmware_capability(release)
    assert release["battery_blocked"] is True and release["readiness"] == "blocked"
    assert capability.state is Readiness.BLOCKED
    assert next(check for check in capability.checks if check.check_id == "battery").state is Readiness.BLOCKED
    release_without_trust = dict(release, battery_blocked=False, problems=[], readiness="not_checked",
                                 remote_enabled=None, trusted=None, battery_level=None, battery_threshold=None)
    unchecked = firmware_capability(release_without_trust)
    assert unchecked.state is Readiness.NOT_CHECKED


def test_appimage_requires_regular_unowned_file_and_update_information() -> None:
    ready = assess_appimage("/home/demo/Applications/Example.AppImage", package_owner=None,
                            update_information="gh-releases-zsync|example|app|latest|Example.zsync",
                            ownership_checked=True)
    assert ready.state is Readiness.READY
    unchecked_owner = assess_appimage("/home/demo/Applications/Example.AppImage", package_owner=None,
                                      update_information="zsync|https://example.invalid/update.zsync")
    assert unchecked_owner.state is Readiness.NOT_CHECKED
    package_owned = assess_appimage("/usr/bin/example.AppImage", package_owner="example-package",
                                    update_information="zsync|https://example.invalid/update.zsync",
                                    ownership_checked=True)
    assert package_owned.state is Readiness.BLOCKED
    assert "belongs to example-package" in package_owned.checks[1].explanation
    unsupported = assess_appimage("/home/demo/Example.AppImage", package_owner=None,
                                  update_information=None, ownership_checked=True)
    assert unsupported.state is Readiness.NOT_SUPPORTED
    unknown_transport = assess_appimage("/home/demo/Example.AppImage", package_owner=None,
                                        update_information="ftp|example.invalid", ownership_checked=True)
    assert unknown_transport.state is Readiness.NOT_SUPPORTED
    malformed_github = assess_appimage("/home/demo/Example.AppImage", package_owner=None,
                                       update_information="gh-releases-zsync|", ownership_checked=True)
    assert malformed_github.state is Readiness.NOT_SUPPORTED
    symlink = assess_appimage("/home/demo/Example.AppImage", package_owner=None,
                              update_information="zsync|https://example.invalid/update.zsync", symlink=True,
                              ownership_checked=True)
    assert symlink.state is Readiness.BLOCKED


def test_portable_replacement_simulator_binds_file_identity_digests_and_recovery() -> None:
    plan = prepare_portable_replacement(
        canonical_path="/home/demo/Applications/Example.AppImage",
        installed_bytes=b"old-app", candidate_bytes=b"new-app", device=41, inode=99,
        owner_uid=1000, mode=0o755, package_owner=None,
        update_information="gh-releases-zsync|example|app|latest|Example.AppImage.zsync",
        parent_writable=True, trust_policy="publisher digest", trust_verified=True,
        ownership_checked=True,
    )
    result = simulate_portable_replacement(plan, observed_installed=b"old-app",
                                           staged_candidate=b"new-app", observed_device=41,
                                           observed_inode=99, staged_device=41, observed_mode=0o755,
                                           replacement_path="/home/demo/Applications/Example.AppImage",
                                           replacement_bytes=b"new-app", replacement_mode=0o755,
                                           replacement_executable=True)
    assert result.backup_retained
    assert result.steps == ("stage beside current file", "verify staged digest", "retain recovery copy",
                            "replace atomically", "verify installed digest and mode")
    with pytest.raises(ValueError, match="changed after review"):
        simulate_portable_replacement(plan, observed_installed=b"tampered",
                                      staged_candidate=b"new-app", observed_device=41,
                                      observed_inode=99, staged_device=41, observed_mode=0o755,
                                      replacement_path="/home/demo/Applications/Example.AppImage",
                                      replacement_bytes=b"new-app", replacement_mode=0o755,
                                      replacement_executable=True)


def test_boot_check_keeps_dkms_initramfs_loader_and_restart_facts_separate() -> None:
    ready = assess_boot(running_kernel="6.17.2", installed_kernels=("6.17.2", "6.17.4"),
                        dkms_failures=(), initramfs_tool=True, boot_loader_known=True,
                        headers_match=True, effective_hooks_known=True, dracut_config_known=True,
                        boot_artifacts_present=True, boot_space_sufficient=True, recovery_available=False)
    assert ready.state is Readiness.READY
    assert ready.restart_action is RestartAction.NONE
    blocked = assess_boot(running_kernel="6.17.2", installed_kernels=("6.17.4",),
                          dkms_failures=("nvidia/580",), initramfs_tool=True, boot_loader_known=True,
                          headers_match=True, effective_hooks_known=True, dracut_config_known=True,
                          boot_artifacts_present=True, boot_space_sufficient=True)
    assert blocked.state is Readiness.BLOCKED
    assert blocked.restart_action is RestartAction.NONE
    assert any(check.check_id == "dkms" and check.state is Readiness.BLOCKED for check in blocked.checks)
    incomplete = assess_boot(running_kernel="6.17.2", installed_kernels=("6.17.2",),
                             dkms_failures=(), initramfs_tool=True, boot_loader_known=True)
    assert incomplete.state is Readiness.NOT_CHECKED
    multiple_kernels = assess_boot(running_kernel="6.17.2", installed_kernels=("6.17.2", "6.12.50-lts"),
                                   dkms_failures=(), initramfs_tool=True, boot_loader_known=True,
                                   headers_match=True, effective_hooks_known=True, dracut_config_known=True,
                                   boot_artifacts_present=True, boot_space_sufficient=True)
    assert multiple_kernels.restart_action is RestartAction.NONE
    applied = assess_boot(running_kernel="6.17.2", installed_kernels=("6.17.2", "6.17.4"),
                          dkms_failures=(), initramfs_tool=True, boot_loader_known=True,
                          headers_match=True, effective_hooks_known=True, dracut_config_known=True,
                          boot_artifacts_present=True, boot_space_sufficient=True,
                          target_kernel="6.17.4", update_applied=True)
    assert applied.restart_action is RestartAction.RESTART


def test_detected_tool_and_portable_adapters_are_read_only_and_ownership_aware() -> None:
    client = FixtureProbeClient({
        "cargo-tools": {"stdout": "ripgrep v14.1.1:\n    rg\n"},
        "fnm-versions": {"stdout": "* v24.11.0 default\n  v22.1.0\n"},
        "npm-root": {"stdout": "/usr/lib/node_modules\n"},
        "npm-globals": {"stdout": json.dumps({"dependencies": {"typescript": {"version": "7.0.2"}}})},
        "uv-tools": {"stdout": "ruff v0.14.0\n- ruff\n"},
        "appimages-applications": {"stdout": "/home/demo/Applications/Example.AppImage\x00"},
        "appimages-local-bin": {"stdout": ""}, "appimages-bin": {"stdout": ""},
    })
    cargo = CargoToolsAdapter(client).check(); fnm = FnmAdapter(client).check()
    npm = NpmGlobalsAdapter(client).check(); uv = UvToolsAdapter(client).check()
    appimage = AppImageAdapter(client).check()
    assert [item.software_id for item in cargo.software] == ["ripgrep"]
    assert cargo.software[0].ownership == "unresolved" and not cargo.software[0].details["source_checked"]
    assert len(fnm.software) == 2 and fnm.software[0].details["default"]
    assert npm.state.value == "blocked" and npm.software[0].ownership == "system_prefix"
    assert npm.evidence["package_owner_checked"] is False
    assert [item.software_id for item in uv.software] == ["ruff"]
    assert uv.state.value == "not_supported" and uv.software[0].ownership == "uv_registered"
    assert appimage.software[0].ownership == "unresolved"
    assert appimage.evidence["read_only"] is True


def test_m4_simulator_plans_use_typed_operations_without_command_surface() -> None:
    definitions = [
        ("firmware", "system", "device-1", OperationKind.FIRMWARE_UPDATE),
        ("appimage", "user", "Example.AppImage", OperationKind.APPIMAGE_REPLACE),
        ("rustup", "user", "stable", OperationKind.RUSTUP_UPDATE),
        ("fnm", "user", "node-24", OperationKind.FNM_INSTALL_VERSION),
    ]
    updates = tuple(DetectedUpdate(stable_software_id(source, scope, software), source, scope,
                                   software, software, "1", "2")
                    for source, scope, software, _operation in definitions)
    snapshot = InventorySnapshot.create(utc_now(), [
        SourceResult(source, source, scope, SourceState.READY_TO_REVIEW, "Ready", utc_now(), 1,
                     updates=(next(item for item in updates if item.source_id == source),))
        for source, scope, _software, _operation in definitions
    ])
    plan = Planner().prepare(snapshot, updates, [item.stable_id for item in updates], [])
    assert {step.operation for step in plan.steps} == {item[3] for item in definitions}
    assert all(not hasattr(step, "command") and not hasattr(step, "argv") for step in plan.steps)
    assert all(not step.live_enabled and step.blocker for step in plan.steps)
    assert len(plan.blockers) == 4
    assert next(step for step in plan.steps if step.source_id == "firmware").permission.value == "administrator"


def _login(client: TestClient) -> None:
    response = client.post("/api/v1/session", headers={"Origin": "http://testserver"},
                           json={"password": "updatarr-demo"})
    assert response.status_code == 200


def test_m4_api_is_authenticated_truthful_and_reports_no_mutation(tmp_path: Path) -> None:
    simulator = create_app(AppConfig(public_origin="http://testserver", storage_path=tmp_path / "sim.db"))
    with TestClient(simulator) as client:
        assert client.get("/api/v1/safety-readiness").status_code == 401
        _login(client)
        body = client.get("/api/v1/safety-readiness").json()
        states = {item["capability_id"]: item["state"] for item in body["items"]}
        assert states["firmware:demo-device"] == "blocked"
        assert states["npm:system"] == "blocked"
        assert states["uv:unknown"] == "not_supported"
        assert body["preservation"] == {
            "package_ownership_changed": False,
            "flatpak_origins_changed": False,
            "host_changes_performed": False,
        }
        preview = next(item for item in body["items"] if item["capability_id"] == "maintenance:package-cache")
        assert len(preview["details"]["preview"]["candidates"]) == 3
        assert preview["details"]["preview"]["removal_performed"] is False

    live = create_app(AppConfig(public_origin="http://testserver", storage_path=tmp_path / "live.db",
                                provider_mode="live"))
    with TestClient(live) as client:
        _login(client)
        body = client.get("/api/v1/safety-readiness").json()
        assert body["mode"] == "Read-only"
        assert {item["state"] for item in body["items"]} == {"not_checked"}
        assert all(item["state"] != "ready" for item in body["items"])


def test_live_readiness_uses_recorded_inventory_without_claiming_update_safety() -> None:
    software = (next(iter(FnmAdapter(FixtureProbeClient({
        "fnm-versions": {"stdout": "* v24.11.0 default\n"},
    })).check().software)),)
    snapshot = InventorySnapshot.create(utc_now(), [
        SourceResult("fnm", "Node.js from fnm", "user", SourceState.NOT_CHECKED,
                     "Installed versions were recorded.", utc_now(), 1, software=software),
        SourceResult("npm", "Global npm packages", "system", SourceState.BLOCKED,
                     "System prefix cannot be changed through npm.", utc_now(), 1),
    ])
    report = live_read_only_report(snapshot)
    tools = next(item for item in report["items"] if item["capability_id"] == "developer-tools")
    assert tools["state"] == "blocked"
    assert "1 software records from 2 matching update sources" in tools["summary"]
    assert len(tools["details"]["observed_sources"]) == 2
    assert report["preservation"]["host_changes_performed"] is False


@pytest.mark.parametrize("relative_path", [
    "docs/M4_ACCEPTANCE.md",
    "docs/research/m4-provider-safety-research.md",
    "docs/research/m4-validation.md",
])
def test_m4_review_documents_use_plain_language(relative_path: str) -> None:
    text = (Path(__file__).parents[1] / relative_path).read_text(encoding="utf-8").lower()
    for unclear_term in (
        "atomic replacement", "colocated staging", "installer provenance",
        "maintenance candidate", "boot preflight", "boot artifact",
        "system prefix", "remote versions", "retention setting",
        "cleanup trials", "typed privileged", "bounded scan",
        "additional mutation", "typed simulator", "privileged live allowlist",
        "host mutation", "mutation posture", "readiness module is an overlay",
        "bounded results",
    ):
        assert unclear_term not in text
