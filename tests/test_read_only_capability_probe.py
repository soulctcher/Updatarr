from __future__ import annotations

import importlib.util
import json
import os
import stat
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "read_only_capability_probe.py"
FIXTURES = ROOT / "tests" / "fixtures" / "read_only"
SUMMARY = ROOT / "docs" / "research" / "host-capability-probe-summary.json"
SPEC = importlib.util.spec_from_file_location("read_only_capability_probe", MODULE_PATH)
assert SPEC and SPEC.loader
probe_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = probe_module
SPEC.loader.exec_module(probe_module)


def test_registry_is_closed_and_read_only():
    probe_module.validate_registry()
    assert len(probe_module.PROBES) == len(probe_module.PROBES_BY_ID)
    assert all(probe.argv[0] not in {"bash", "sh", "sudo", "doas", "pkexec"} for probe in probe_module.PROBES)


@pytest.mark.parametrize("probe", probe_module.PROBES, ids=lambda probe: probe.probe_id)
def test_registered_commands_have_no_forbidden_argument(probe):
    blocked = probe_module.FORBIDDEN_ARGUMENTS.intersection(probe.argv[1:])
    if probe.argv == ("cargo", "install", "--list"):
        blocked = blocked.difference({"install"})
    assert not blocked


def test_sanitizer_removes_local_identifiers(monkeypatch):
    monkeypatch.setattr(probe_module.Path, "home", lambda: Path("/home/example"))
    monkeypatch.setattr(probe_module.getpass, "getuser", lambda: "example")
    monkeypatch.setattr(probe_module.socket, "gethostname", lambda: "workstation")
    source = "/home/example file by example on workstation 123e4567-e89b-12d3-a456-426614174000"
    sanitized = probe_module.sanitize(source)
    assert "/home/example" not in sanitized
    assert "workstation" not in sanitized
    assert "123e4567" not in sanitized
    assert sanitized == "$HOME file by $USER on $HOST $UUID"


def test_sanitizer_does_not_replace_username_inside_another_word(monkeypatch):
    monkeypatch.setattr(probe_module.Path, "home", lambda: Path("/home/ann"))
    monkeypatch.setattr(probe_module.getpass, "getuser", lambda: "ann")
    monkeypatch.setattr(probe_module.socket, "gethostname", lambda: "host")
    assert probe_module.sanitize("ann cannot /home/ann") == "$USER cannot $HOME"


def test_sanitizer_redacts_structured_device_ids_and_url_credentials():
    source = json.dumps(
        {
            "DeviceId": "stable-device-id",
            "Guid": ["123e4567-e89b-12d3-a456-426614174000"],
            "Serial": "private-serial",
            "url": "https://person:password@example.test/path?token=secret",
        }
    )
    sanitized = probe_module.sanitize(source)
    assert "stable-device-id" not in sanitized
    assert "private-serial" not in sanitized
    assert "person:password" not in sanitized
    assert "token=secret" not in sanitized
    assert json.loads(sanitized)["DeviceId"] == "$REDACTED"


def test_application_sanitizer_uses_stable_one_way_identifiers():
    source = json.dumps(
        {"Devices": [
            {"DeviceId": "device-one", "Serial": "private-one"},
            {"DeviceId": "device-two", "Serial": "private-two"},
        ]}
    )
    first = probe_module.sanitize_for_application(source)
    second = probe_module.sanitize_for_application(source)
    assert first == second
    assert "device-one" not in first and "private-one" not in first
    assert len({device["DeviceId"] for device in json.loads(first)["Devices"]}) == 2
    assert all(
        device["DeviceId"].startswith("$ID_")
        for device in json.loads(first)["Devices"]
    )


def test_sanitizer_redacts_systemd_machine_and_boot_entry_ids():
    local_id = "a0ab5d68a75849b1940d443e196fb5f9"
    assert probe_module.sanitize(f"Current Entry: {local_id}-linux.conf") == (
        "Current Entry: $LOCAL_ID-linux.conf"
    )


def test_probe_environment_excludes_unrelated_secrets(monkeypatch):
    monkeypatch.setenv("UPDATARR_TEST_SECRET", "do-not-pass")
    monkeypatch.setenv("HOME", "/home/example")
    environment = probe_module.probe_environment()
    assert environment["HOME"] == "/home/example"
    assert "UPDATARR_TEST_SECRET" not in environment
    assert environment["PAGER"] == "cat"


def test_native_update_probe_uses_fixed_secret_free_host_tmp_worker(monkeypatch):
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        probe_module,
        "trusted_executable",
        lambda name: (Path(f"/usr/bin/{name}"), "expected-owner", None),
    )

    def bounded(argv, timeout_seconds, *, max_records=None):
        captured.update(
            argv=argv,
            timeout_seconds=timeout_seconds,
            max_records=max_records,
        )
        return probe_module.BoundedResult(0, "rsync 1 -> 2\n", "", False, False)

    monkeypatch.setattr(probe_module, "run_bounded", bounded)
    monkeypatch.setenv("UPDATARR_PASSWORD", "must-not-cross")

    result = probe_module.run_probe(probe_module.PROBES_BY_ID["native-updates"])

    argv = captured["argv"]
    assert isinstance(argv, tuple)
    assert argv[0] == "/usr/bin/systemd-run"
    assert "--property=PrivateTmp=false" in argv
    assert "--property=NoNewPrivileges=true" in argv
    assert "/usr/bin/env" in argv and "-i" in argv
    assert argv[-2:] == ("/usr/bin/checkupdates", "--nocolor")
    assert not any("must-not-cross" in argument for argument in argv)
    assert result["state"] == "completed"


def test_missing_executable_is_a_truthful_state(monkeypatch):
    missing = Path("/definitely/not/an/executable")
    monkeypatch.setitem(
        probe_module.TRUSTED_EXECUTABLES,
        "pacman",
        probe_module.TrustedExecutable(missing, "pacman"),
    )
    result = probe_module.run_probe(probe_module.PROBES_BY_ID["pacman-version"])
    assert result["state"] == "not_available"
    assert result["exit_code"] is None
    assert result["stdout"] == ""


def test_path_hijack_cannot_replace_trusted_executable(monkeypatch, tmp_path):
    marker = tmp_path / "marker"
    fake = tmp_path / "pacman"
    fake.write_text(f"#!/bin/sh\ntouch '{marker}'\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}:/usr/bin")
    result = probe_module.run_probe(probe_module.PROBES_BY_ID["pacman-version"])
    assert result["state"] == "completed"
    assert result["executable_path"] == "/usr/bin/pacman"
    assert not marker.exists()


def test_unexpected_executable_owner_is_rejected(monkeypatch, tmp_path):
    candidate = tmp_path / "tool"
    candidate.write_text("not executed")
    candidate.chmod(0o755)
    monkeypatch.setitem(
        probe_module.TRUSTED_EXECUTABLES,
        "pacman",
        probe_module.TrustedExecutable(candidate, "expected-package", True),
    )
    monkeypatch.setattr(probe_module, "pacman_owner", lambda _path: None)
    path, owner, error = probe_module.trusted_executable("pacman")
    assert path is None
    assert owner is None
    assert "owner" in error


def test_root_owner_is_recognized_inside_a_verified_user_namespace(monkeypatch, tmp_path):
    uid_map = tmp_path / "uid_map"
    overflow_uid = tmp_path / "overflowuid"
    uid_map.write_text("       1000       1000          1\n", encoding="utf-8")
    overflow_uid.write_text("65534\n", encoding="utf-8")
    monkeypatch.setattr(probe_module, "UID_MAP_PATH", uid_map)
    monkeypatch.setattr(probe_module, "OVERFLOW_UID_PATH", overflow_uid)
    metadata = SimpleNamespace(st_uid=65534, st_mode=stat.S_IFREG | 0o755)
    assert probe_module.root_owner_is_safe(metadata) is True

    uid_map.write_text("          0          0 4294967295\n", encoding="utf-8")
    assert probe_module.root_owner_is_safe(metadata) is False
    metadata.st_uid = 12345
    assert probe_module.root_owner_is_safe(metadata) is False


def test_namespaced_root_exception_does_not_allow_writable_system_paths(monkeypatch):
    metadata = SimpleNamespace(st_uid=65534, st_mode=stat.S_IFREG | 0o775)
    monkeypatch.setattr(probe_module, "root_owner_is_safe", lambda _metadata: True)
    assert probe_module.system_executable_is_safe(Path("/usr/bin/pacman"), metadata) is False
    assert probe_module.system_executable_is_safe(Path("/opt/bin/pacman"), metadata) is False


def test_namespaced_root_owned_system_symlink_uses_the_same_owner_check(monkeypatch, tmp_path):
    npm = Path("/usr/bin/npm")
    original_lstat = Path.lstat
    real_link = original_lstat(npm)
    values = list(real_link)
    values[4] = 65534
    namespaced_link = os.stat_result(values)
    uid_map = tmp_path / "uid_map"
    overflow_uid = tmp_path / "overflowuid"
    uid_map.write_text("       1000       1000          1\n", encoding="utf-8")
    overflow_uid.write_text("65534\n", encoding="utf-8")
    monkeypatch.setattr(probe_module, "UID_MAP_PATH", uid_map)
    monkeypatch.setattr(probe_module, "OVERFLOW_UID_PATH", overflow_uid)
    monkeypatch.setattr(
        Path,
        "lstat",
        lambda path: namespaced_link if path == npm else original_lstat(path),
    )
    path, owner, error = probe_module.trusted_executable("npm")
    assert path == npm
    assert owner == "npm"
    assert error is None


def test_system_link_target_outside_usr_is_rejected(monkeypatch):
    candidate = Path("/usr/bin/example-tool")
    metadata = SimpleNamespace(st_uid=0, st_mode=stat.S_IFREG | 0o755)
    monkeypatch.setattr(
        Path,
        "resolve",
        lambda path, strict=False: Path("/tmp/example-tool") if path == candidate else path,
    )
    assert probe_module.system_executable_is_safe(candidate, metadata) is False


@pytest.mark.parametrize("bad_parent_kind", ["writable", "symbolic-link"])
def test_unsafe_system_link_target_parent_is_rejected(monkeypatch, bad_parent_kind):
    candidate = Path("/usr/bin/example-tool")
    resolved = Path("/usr/lib/example/tool")
    bad_parent = Path("/usr/lib/example")
    metadata = SimpleNamespace(st_uid=0, st_mode=stat.S_IFREG | 0o755)
    monkeypatch.setattr(
        Path,
        "resolve",
        lambda path, strict=False: resolved if path == candidate else path,
    )
    monkeypatch.setattr(
        Path,
        "stat",
        lambda path: SimpleNamespace(
            st_uid=0,
            st_mode=stat.S_IFDIR | (0o775 if path == bad_parent and bad_parent_kind == "writable" else 0o755),
        ),
    )
    monkeypatch.setattr(Path, "is_dir", lambda _path: True)
    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda path: path == bad_parent and bad_parent_kind == "symbolic-link",
    )
    monkeypatch.setattr(probe_module.os, "access", lambda *_args, **_kwargs: False)
    assert probe_module.system_executable_is_safe(candidate, metadata) is False


def test_public_probe_list_redacts_home_paths():
    payload = json.dumps(probe_module.public_probe_list())
    assert str(Path.home()) not in payload
    assert "$HOME" in payload


def test_required_path_absence_is_not_reported_as_a_command_failure(tmp_path):
    probe = probe_module.Probe(
        "missing-path",
        ("find", str(tmp_path / "absent"), "-print0"),
        "test",
        1,
        str(tmp_path / "absent"),
        10,
    )
    result = probe_module.run_probe(probe)
    assert result["state"] == "not_available"
    assert result["exit_code"] is None


def test_bounded_runner_stops_at_byte_limit(monkeypatch):
    monkeypatch.setattr(probe_module, "MAX_OUTPUT_BYTES", 128)
    result = probe_module.run_bounded(
        (sys.executable, "-c", "import sys; sys.stdout.write('x' * 10000)"),
        5,
    )
    assert result.output_truncated is True
    assert len(result.stdout.encode()) <= 128


def test_bounded_runner_preserves_timeout_output():
    result = probe_module.run_bounded(
        (
            sys.executable,
            "-c",
            "import time; print('started', flush=True); time.sleep(2)",
        ),
        1,
    )
    assert result.timed_out is True
    assert result.exit_code is None
    assert "started" in result.stdout


def test_bounded_runner_limits_nul_delimited_records():
    result = probe_module.run_bounded(
        (sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'a\\0b\\0c\\0')"),
        5,
        max_records=2,
    )
    assert result.output_truncated is True
    assert result.stdout.count("\0") == 2


def test_report_is_versioned_and_serializable(monkeypatch):
    monkeypatch.setattr(
        probe_module,
        "run_probe",
        lambda probe, _timeout: {"probe_id": probe.probe_id, "state": "completed"},
    )
    report = probe_module.build_report(["pacman-version"], 1)
    assert report["schema_version"] == 1
    assert report["read_only"] is True
    assert json.loads(json.dumps(report))["results"][0]["probe_id"] == "pacman-version"


def test_json_fixtures_are_valid_and_sanitized():
    for fixture_name in ("fwupd-devices-shape.json", "npm-globals.json"):
        text = (FIXTURES / fixture_name).read_text()
        assert "/home/" not in text
        assert "Serial" not in text
        assert json.loads(text)


@pytest.mark.parametrize(
    ("fixture_name", "columns"),
    (("flatpak-apps.tsv", 6), ("flatpak-remotes.tsv", 6)),
)
def test_flatpak_fixtures_have_stable_columns(fixture_name, columns):
    rows = (FIXTURES / fixture_name).read_text().splitlines()
    assert rows
    assert all(len(row.split("\t")) == columns for row in rows)


def test_foreign_fixture_does_not_claim_aur_ownership():
    fixture = (FIXTURES / "pacman-foreign.txt").read_text()
    assert "AUR" not in fixture
    assert all(len(line.split()) == 2 for line in fixture.splitlines())


def test_appimage_fixture_is_bounded_and_does_not_claim_update_support():
    fixture = (FIXTURES / "appimage-candidates.tsv").read_text()
    assert "/home/" not in fixture
    assert "update available" not in fixture.lower()
    assert all(len(line.split("\t")) == 4 for line in fixture.splitlines())


def test_committed_capability_summary_is_complete_and_sanitized():
    text = SUMMARY.read_text()
    document = json.loads(text)
    assert document["schema_version"] == 1
    assert document["read_only"] is True
    assert document["host_changes"] == []
    assert str(Path.home()) not in text
    assert len(document["sources"]) >= 10
    for source in document["sources"]:
        assert source["tool"]["path"]
        assert source["observed_contract"]
        assert source["scopes"]
        assert source["privilege"]
        assert set(source["capabilities"]) == {
            "inventory",
            "check",
            "search",
            "plan",
            "execute",
            "history",
            "postpone",
        }
        assert source["state"]
        assert source["limitation"]
        assert source["safe_next_step"]
        assert source["fixtures"]
        assert all((SUMMARY.parent / fixture).resolve().is_file() for fixture in source["fixtures"])
