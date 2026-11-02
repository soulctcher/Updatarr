"""Fail-closed deployment settings and read-only migration checks for M5."""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import os
from pathlib import Path
import stat
from urllib.parse import urlparse


class DeploymentError(ValueError):
    """Deployment settings would weaken the supported security posture."""


def _is_loopback(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


@dataclass(frozen=True)
class DeploymentConfig:
    bind_host: str
    port: int
    public_origin: str
    allowed_hosts: tuple[str, ...]
    password: str
    url_base: str
    state_path: Path
    static_dir: Path
    tray_status_path: Path
    provider_mode: str
    event_history_limit: int
    trusted_proxy_peers: tuple[str, ...] = ()
    tls_certfile: Path | None = None
    tls_keyfile: Path | None = None
    development_mode: bool = False

    @classmethod
    def from_environment(cls, environ: dict[str, str] | None = None) -> "DeploymentConfig":
        env = os.environ if environ is None else environ
        development = env.get("UPDATARR_DEVELOPMENT_MODE", "").lower() in {"1", "true", "yes"}
        password = env.get("UPDATARR_PASSWORD", "")
        if len(password) < 8:
            raise DeploymentError("Set UPDATARR_PASSWORD to at least 8 characters.")

        bind_host = env.get("UPDATARR_BIND_HOST", "127.0.0.1").strip()
        if bind_host.lower() in {"0.0.0.0", "::", "[::]"}:
            raise DeploymentError(
                "UPDATARR_BIND_HOST must be one specific address, not a wildcard."
            )
        try:
            port = int(env.get("UPDATARR_PORT", "8788"))
        except ValueError as error:
            raise DeploymentError("UPDATARR_PORT must be a number from 1 through 65535.") from error
        if not 1 <= port <= 65535:
            raise DeploymentError("UPDATARR_PORT must be a number from 1 through 65535.")

        cert = Path(env["UPDATARR_TLS_CERTFILE"]).expanduser() if env.get("UPDATARR_TLS_CERTFILE") else None
        key = Path(env["UPDATARR_TLS_KEYFILE"]).expanduser() if env.get("UPDATARR_TLS_KEYFILE") else None
        if (cert is None) != (key is None):
            raise DeploymentError("Set both UPDATARR_TLS_CERTFILE and UPDATARR_TLS_KEYFILE, or neither.")
        if cert is not None and key is not None:
            if not cert.is_file() or not key.is_file():
                raise DeploymentError("The configured HTTPS certificate and key must be readable files.")
            if stat.S_IMODE(key.stat().st_mode) & 0o077:
                raise DeploymentError("The HTTPS private key must be readable only by its owner.")

        scheme = "https" if cert else "http"
        public_origin = env.get("UPDATARR_PUBLIC_ORIGIN", f"{scheme}://{bind_host}:{port}").rstrip("/")
        parsed = urlparse(public_origin)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.path not in {"", "/"}:
            raise DeploymentError("UPDATARR_PUBLIC_ORIGIN must be one http or https origin without a path.")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise DeploymentError("UPDATARR_PUBLIC_ORIGIN must not contain credentials, a query or a fragment.")

        loopback = _is_loopback(bind_host)
        reverse_proxy = env.get("UPDATARR_REVERSE_PROXY", "").lower() in {"1", "true", "yes"}
        if reverse_proxy and (not loopback or parsed.scheme != "https" or cert is not None):
            raise DeploymentError(
                "Reverse-proxy mode requires a loopback listener, an https public origin and proxy-managed TLS."
            )
        if parsed.scheme == "https" and loopback and cert is None and not reverse_proxy:
            raise DeploymentError("Set UPDATARR_REVERSE_PROXY=1 when HTTPS is provided by a loopback proxy.")
        if not loopback and (parsed.scheme != "https" or cert is None):
            raise DeploymentError("A direct non-loopback listener requires HTTPS certificate and key files.")
        if parsed.scheme == "https" and not loopback and development:
            raise DeploymentError("Development mode cannot be used for a non-loopback listener.")
        if parsed.scheme == "http" and not loopback:
            raise DeploymentError("Cleartext non-loopback access is not supported.")

        allowed = tuple(
            dict.fromkeys(
                host.strip().lower()
                for host in env.get("UPDATARR_ALLOWED_HOSTS", parsed.hostname).split(",")
                if host.strip()
            )
        )
        if not allowed or parsed.hostname.lower() not in allowed:
            raise DeploymentError("UPDATARR_ALLOWED_HOSTS must include the host in UPDATARR_PUBLIC_ORIGIN.")
        if any(value in {"*", "0.0.0.0", "::"} for value in allowed):
            raise DeploymentError("Allowed hosts must be exact host names or addresses, not wildcards.")

        state_home = Path(env.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state")))
        runtime_dir = Path(env.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
        state_path = Path(env.get("UPDATARR_STATE_PATH", str(state_home / "updatarr" / "updatarr.db"))).expanduser()
        static_dir = _static_dir(env)
        try:
            event_history_limit = int(env.get("UPDATARR_EVENT_HISTORY_LIMIT", "100"))
        except ValueError as error:
            raise DeploymentError("UPDATARR_EVENT_HISTORY_LIMIT must be a positive number.") from error
        if event_history_limit < 1:
            raise DeploymentError("UPDATARR_EVENT_HISTORY_LIMIT must be a positive number.")
        return cls(
            bind_host=bind_host,
            port=port,
            public_origin=public_origin,
            allowed_hosts=allowed,
            password=password,
            url_base=env.get("UPDATARR_URL_BASE", ""),
            state_path=state_path,
            static_dir=static_dir,
            tray_status_path=Path(env.get("UPDATARR_TRAY_STATUS_PATH", str(runtime_dir / "updatarr" / "tray-status.json"))),
            provider_mode=env.get("UPDATARR_PROVIDER_MODE", "live"),
            event_history_limit=event_history_limit,
            trusted_proxy_peers=("127.0.0.1", "::1") if reverse_proxy else (),
            tls_certfile=cert,
            tls_keyfile=key,
            development_mode=development,
        )


def _static_dir(env: dict[str, str] | os._Environ[str]) -> Path:
    if env.get("UPDATARR_STATIC_DIR"):
        return Path(env["UPDATARR_STATIC_DIR"]).expanduser()
    installed = Path("/usr/share/updatarr/web")
    if installed.is_dir():
        return installed
    return Path(__file__).resolve().parents[2] / "web" / "dist"


@dataclass(frozen=True)
class StartupObservation:
    core_enabled: bool
    core_active: bool
    tray_enabled: bool
    tray_active_instances: int
    octopi_notifier_enabled: bool
    octopi_notifier_active: bool


@dataclass(frozen=True)
class MigrationAssessment:
    ready: bool
    checks: tuple[tuple[str, bool, str], ...]


def assess_migration(observation: StartupObservation, *, coverage_complete: bool, rollback_tested: bool) -> MigrationAssessment:
    """Assess evidence only. This function never changes services or software."""
    checks = (
        ("Update coverage", coverage_complete, "Every approved update source is accounted for."),
        ("Core service", observation.core_enabled and observation.core_active, "Updatarr starts under one user service."),
        ("One tray", observation.tray_enabled and observation.tray_active_instances == 1, "Exactly one Updatarr tray is running."),
        (
            "One notifier",
            not observation.octopi_notifier_enabled and not observation.octopi_notifier_active,
            "The Octopi notifier is disabled and inactive while the Updatarr tray is selected.",
        ),
        ("Rollback", rollback_tested, "The prior notifier setup can be restored."),
    )
    return MigrationAssessment(ready=all(item[1] for item in checks), checks=checks)
