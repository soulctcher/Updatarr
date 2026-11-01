"""M5 packaging, startup, network and migration safety checks."""

from __future__ import annotations

import os
from pathlib import Path
import stat
import subprocess
import sys
import shutil
import hashlib

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from updatarr.deployment import (  # noqa: E402
    DeploymentConfig,
    DeploymentError,
    StartupObservation,
    assess_migration,
)
from updatarr.app import AppConfig, create_app  # noqa: E402
from updatarr.tray import TrayInstanceLock, TrayStatus  # noqa: E402
from updatarr.tray_status import TrayStatusFile  # noqa: E402
from updatarr.open_web import configured_url  # noqa: E402


def environment(tmp_path: Path, **changes: str) -> dict[str, str]:
    values = {
        "HOME": str(tmp_path),
        "XDG_STATE_HOME": str(tmp_path / "state"),
        "XDG_RUNTIME_DIR": str(tmp_path / "runtime"),
        "UPDATARR_PASSWORD": "unique-password",
        "UPDATARR_STATIC_DIR": str(ROOT / "web" / "dist"),
    }
    values.update(changes)
    return values


def test_default_deployment_is_loopback_and_uses_xdg_paths(tmp_path: Path) -> None:
    config = DeploymentConfig.from_environment(environment(tmp_path))
    assert config.bind_host == "127.0.0.1"
    assert config.public_origin == "http://127.0.0.1:8788"
    assert config.state_path == tmp_path / "state" / "updatarr" / "updatarr.db"
    assert config.tray_status_path == tmp_path / "runtime" / "updatarr" / "tray-status.json"
    assert config.development_mode is False


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"UPDATARR_PASSWORD": ""}, "UPDATARR_PASSWORD"),
        ({"UPDATARR_BIND_HOST": "0.0.0.0"}, "specific address"),
        ({"UPDATARR_BIND_HOST": "192.0.2.10"}, "requires HTTPS"),
        ({"UPDATARR_ALLOWED_HOSTS": "*"}, "must include"),
        ({"UPDATARR_PUBLIC_ORIGIN": "http://127.0.0.1:8788/path"}, "without a path"),
        ({"UPDATARR_PORT": "70000"}, "65535"),
    ],
)
def test_unsafe_network_or_password_settings_fail_closed(
    tmp_path: Path, changes: dict[str, str], message: str
) -> None:
    with pytest.raises(DeploymentError, match=message):
        DeploymentConfig.from_environment(environment(tmp_path, **changes))


def test_reverse_proxy_origin_keeps_upstream_on_loopback(tmp_path: Path) -> None:
    config = DeploymentConfig.from_environment(environment(
        tmp_path,
        UPDATARR_PUBLIC_ORIGIN="https://updates.example.test",
        UPDATARR_ALLOWED_HOSTS="updates.example.test",
        UPDATARR_REVERSE_PROXY="1",
    ))
    assert config.bind_host == "127.0.0.1"
    assert config.public_origin.startswith("https://")
    assert config.tls_certfile is None
    assert config.trusted_proxy_peers == ("127.0.0.1", "::1")


def test_https_origin_without_explicit_proxy_mode_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(DeploymentError, match="UPDATARR_REVERSE_PROXY"):
        DeploymentConfig.from_environment(environment(
            tmp_path,
            UPDATARR_PUBLIC_ORIGIN="https://updates.example.test",
            UPDATARR_ALLOWED_HOSTS="updates.example.test",
        ))


def test_direct_lan_requires_certificate_pair(tmp_path: Path) -> None:
    (tmp_path / "cert.pem").write_text("test certificate", encoding="utf-8")
    (tmp_path / "key.pem").write_text("test key", encoding="utf-8")
    (tmp_path / "key.pem").chmod(0o600)
    config = DeploymentConfig.from_environment(environment(
        tmp_path,
        UPDATARR_BIND_HOST="192.0.2.10",
        UPDATARR_PUBLIC_ORIGIN="https://192.0.2.10:8788",
        UPDATARR_ALLOWED_HOSTS="192.0.2.10",
        UPDATARR_TLS_CERTFILE=str(tmp_path / "cert.pem"),
        UPDATARR_TLS_KEYFILE=str(tmp_path / "key.pem"),
    ))
    assert config.tls_certfile == tmp_path / "cert.pem"
    assert config.tls_keyfile == tmp_path / "key.pem"


@pytest.mark.parametrize("bind_host", ["0.0.0.0", "::", "[::]"])
def test_direct_https_rejects_wildcard_bind_addresses(
    tmp_path: Path, bind_host: str
) -> None:
    (tmp_path / "cert.pem").write_text("test certificate", encoding="utf-8")
    (tmp_path / "key.pem").write_text("test key", encoding="utf-8")
    (tmp_path / "key.pem").chmod(0o600)
    with pytest.raises(DeploymentError, match="specific address"):
        DeploymentConfig.from_environment(environment(
            tmp_path,
            UPDATARR_BIND_HOST=bind_host,
            UPDATARR_PUBLIC_ORIGIN="https://updates.example.test:8788",
            UPDATARR_ALLOWED_HOSTS="updates.example.test",
            UPDATARR_TLS_CERTFILE=str(tmp_path / "cert.pem"),
            UPDATARR_TLS_KEYFILE=str(tmp_path / "key.pem"),
        ))


def test_tray_status_is_minimal_private_and_readable(tmp_path: Path) -> None:
    path = tmp_path / "runtime" / "tray-status.json"
    status_file = TrayStatusFile(path)
    status_file.write({
        "snapshot": {"snapshot_id": "one"},
        "summary": {"updates_found": 5, "blocked": 1},
        "sources": [{"name": "must not be copied"}],
        "session": "must not be copied",
    })
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    document = status_file.read()
    assert document is not None and set(document) == {"version", "snapshot", "summary"}
    assert "1 blocked" in TrayStatus.from_overview(document).title


def test_tray_rejects_status_file_visible_to_other_users(tmp_path: Path) -> None:
    path = tmp_path / "tray-status.json"
    TrayStatusFile(path).write({"snapshot": None, "summary": {}})
    path.chmod(0o644)
    assert TrayStatusFile(path).read() is None


def test_only_one_tray_lock_can_be_held(tmp_path: Path) -> None:
    first = TrayInstanceLock(tmp_path / "tray.lock")
    second = TrayInstanceLock(tmp_path / "tray.lock")
    assert first.acquire() is True
    assert second.acquire() is False
    first.release()
    assert second.acquire() is True
    second.release()


def test_migration_requires_coverage_one_notifier_and_rollback() -> None:
    good = StartupObservation(True, True, True, 1, False, False)
    assert assess_migration(good, coverage_complete=True, rollback_tested=True).ready is True
    duplicate = StartupObservation(True, True, True, 1, True, True)
    result = assess_migration(duplicate, coverage_complete=True, rollback_tested=True)
    assert result.ready is False
    assert next(check for check in result.checks if check[0] == "One notifier")[1] is False
    returns_at_login = StartupObservation(True, True, True, 1, True, False)
    result = assess_migration(
        returns_at_login, coverage_complete=True, rollback_tested=True
    )
    assert result.ready is False
    assert next(check for check in result.checks if check[0] == "One notifier")[1] is False


def test_notifier_swap_rollback_and_reapply_preserve_one_owner(tmp_path: Path) -> None:
    """Exercise the documented swap using disposable startup-owner fixtures."""
    autostart = tmp_path / "config" / "autostart" / "octopi-notifier.desktop"
    saved = tmp_path / "migration" / "octopi-notifier.desktop.saved"
    tray_link = tmp_path / "config" / "systemd" / "user" / (
        "graphical-session.target.wants/updatarr-tray.service"
    )
    unit = tmp_path / "usr" / "lib" / "systemd" / "user" / "updatarr-tray.service"
    autostart.parent.mkdir(parents=True)
    saved.parent.mkdir(parents=True)
    tray_link.parent.mkdir(parents=True)
    unit.parent.mkdir(parents=True)
    original = b"[Desktop Entry]\nType=Application\nExec=/usr/bin/octopi-notifier\n"
    autostart.write_bytes(original)
    autostart.chmod(0o600)
    unit.write_text("[Install]\nWantedBy=graphical-session.target\n", encoding="utf-8")

    def enabled_notifiers() -> int:
        return int(autostart.exists()) + int(tray_link.exists())

    # Reviewed setup: save the exact old owner and select Updatarr.
    autostart.rename(saved)
    tray_link.symlink_to(unit)
    assert enabled_notifiers() == 1

    # Roll back: remove only Updatarr's owner and restore Octopi byte-for-byte.
    tray_link.unlink()
    saved.rename(autostart)
    assert enabled_notifiers() == 1
    assert autostart.read_bytes() == original
    assert stat.S_IMODE(autostart.stat().st_mode) == 0o600

    # Reapply the reviewed setup and prove there is still one startup owner.
    autostart.rename(saved)
    tray_link.symlink_to(unit)
    assert enabled_notifiers() == 1
    assert saved.read_bytes() == original


def test_package_has_one_startup_owner_and_does_not_enable_itself() -> None:
    core = (ROOT / "packaging/systemd/updatarr.service").read_text(encoding="utf-8")
    tray = (ROOT / "packaging/systemd/updatarr-tray.service").read_text(encoding="utf-8")
    package = (ROOT / "packaging/arch/PKGBUILD").read_text(encoding="utf-8")
    assert "WantedBy=default.target" in core
    assert "WantedBy=graphical-session.target" in tray
    assert "PartOf=graphical-session.target" in tray
    assert all(setting in core for setting in (
        "StateDirectory=updatarr", "CacheDirectory=updatarr", "RuntimeDirectory=updatarr"
    ))
    assert "NoNewPrivileges=true" in core and "NoNewPrivileges=true" in tray
    assert '--prefix=/usr' in package
    assert 'python-pydantic' in package
    assert '$startdir' not in package
    archive = ROOT / "packaging" / "arch" / "updatarr-0.6.0.tar.gz"
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert digest in package
    assert "systemctl" not in package
    assert not list((ROOT / "packaging").rglob("*autostart*"))


def test_launcher_reads_public_address_without_sourcing_configuration(tmp_path: Path) -> None:
    config = tmp_path / "updatarr.env"
    config.write_text(
        "UPDATARR_PASSWORD=must-not-be-used\n"
        "UPDATARR_PUBLIC_ORIGIN=https://updates.example.test\n"
        "UPDATARR_URL_BASE=/updatarr\n",
        encoding="utf-8",
    )
    config.chmod(0o600)
    assert configured_url(config) == "https://updates.example.test/updatarr/"
    config.chmod(0o644)
    with pytest.raises(ValueError, match="only by its owner"):
        configured_url(config)


def test_packaging_metadata_parses_with_host_tools() -> None:
    subprocess.run(["bash", "-n", str(ROOT / "packaging/arch/PKGBUILD")], check=True)
    validator = Path("/usr/bin/desktop-file-validate")
    if validator.exists():
        subprocess.run([
            str(validator), str(ROOT / "packaging/desktop/io.github.updatarr.Updatarr.desktop")
        ], check=True)


def test_user_unit_enable_and_rollback_are_reversible_in_staged_root(tmp_path: Path) -> None:
    systemctl = shutil.which("systemctl")
    if systemctl is None:
        pytest.skip("systemctl is not available")
    unit_dir = tmp_path / "usr" / "lib" / "systemd" / "user"
    unit_dir.mkdir(parents=True)
    for name in ("updatarr.service", "updatarr-tray.service"):
        shutil.copy2(ROOT / "packaging" / "systemd" / name, unit_dir / name)
    subprocess.run([
        systemctl, f"--root={tmp_path}", "--global", "enable",
        "updatarr.service", "updatarr-tray.service",
    ], check=True, capture_output=True, text=True)
    assert (tmp_path / "etc/systemd/user/default.target.wants/updatarr.service").is_symlink()
    assert (tmp_path / "etc/systemd/user/graphical-session.target.wants/updatarr-tray.service").is_symlink()
    assert not list(tmp_path.rglob("*autostart*"))
    subprocess.run([
        systemctl, f"--root={tmp_path}", "--global", "disable",
        "updatarr.service", "updatarr-tray.service",
    ], check=True, capture_output=True, text=True)
    assert not (tmp_path / "etc/systemd/user/default.target.wants/updatarr.service").exists()
    assert not (tmp_path / "etc/systemd/user/graphical-session.target.wants/updatarr-tray.service").exists()


def test_settings_export_excludes_credentials_inventory_and_plans(tmp_path: Path) -> None:
    app = create_app(AppConfig(
        password="export-password",
        public_origin="http://testserver",
        storage_path=tmp_path / "state" / "updatarr.db",
        provider_mode="simulator",
    ))
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/session",
            headers={"Origin": "http://testserver"},
            json={"password": "export-password"},
        )
        assert login.status_code == 200
        response = client.get("/api/v1/settings/export")
    assert response.status_code == 200
    assert response.headers["content-disposition"].endswith('"updatarr-settings.json"')
    document = response.json()
    assert set(document) == {
        "format", "version", "exported_at", "appearance", "update_sources", "saved_choices"
    }
    serialized = response.text.lower()
    for forbidden in ("password", "session", "inventory", "update_plan", "csrf"):
        assert forbidden not in serialized


def test_forwarding_headers_are_ignored_only_for_configured_proxy_peer(tmp_path: Path) -> None:
    trusted = create_app(AppConfig(
        public_origin="https://updates.example.test",
        allowed_hosts=("updates.example.test",),
        secure_cookie=True,
        trusted_proxy_peers=("testclient",),
        storage_path=tmp_path / "trusted" / "state.db",
    ))
    with TestClient(trusted, base_url="https://updates.example.test") as client:
        response = client.get("/healthz", headers={
            "Forwarded": "for=198.51.100.10;proto=http",
            "X-Forwarded-Host": "attacker.invalid",
            "X-Forwarded-Proto": "http",
        })
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    untrusted = create_app(AppConfig(
        public_origin="https://updates.example.test",
        allowed_hosts=("updates.example.test",),
        secure_cookie=True,
        storage_path=tmp_path / "untrusted" / "state.db",
    ))
    with TestClient(untrusted, base_url="https://updates.example.test") as client:
        assert client.get("/healthz", headers={"X-Forwarded-Proto": "https"}).status_code == 400
