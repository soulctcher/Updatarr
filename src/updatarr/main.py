"""Validated Updatarr service entry point."""

from __future__ import annotations

import uvicorn

from .app import AppConfig, create_app
from .deployment import DeploymentConfig


def main() -> None:
    deployment = DeploymentConfig.from_environment()
    deployment.state_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    app = create_app(
        AppConfig(
            password=deployment.password,
            public_origin=deployment.public_origin,
            allowed_hosts=deployment.allowed_hosts,
            secure_cookie=deployment.public_origin.startswith("https://"),
            url_base=deployment.url_base,
            static_dir=deployment.static_dir,
            storage_path=deployment.state_path,
            provider_mode=deployment.provider_mode,
            event_history_limit=deployment.event_history_limit,
            tray_status_path=deployment.tray_status_path,
            trusted_proxy_peers=deployment.trusted_proxy_peers,
        )
    )
    uvicorn.run(
        app,
        host=deployment.bind_host,
        port=deployment.port,
        access_log=False,
        proxy_headers=False,
        ssl_certfile=str(deployment.tls_certfile) if deployment.tls_certfile else None,
        ssl_keyfile=str(deployment.tls_keyfile) if deployment.tls_keyfile else None,
    )


if __name__ == "__main__":
    main()
