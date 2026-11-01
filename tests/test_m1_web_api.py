"""End-to-end M1 persistence, inventory and preference checks."""

from __future__ import annotations

from contextlib import contextmanager
import http.client
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import time
from urllib.request import urlopen

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


@contextmanager
def _server(state_path: Path):
    port = _free_port()
    env = os.environ.copy()
    env.update({"PYTHONPATH": str(ROOT / "src"), "UPDATARR_PORT": str(port),
                "UPDATARR_PROVIDER_MODE": "simulator", "UPDATARR_DEVELOPMENT_MODE": "1",
                "UPDATARR_STATE_PATH": str(state_path)})
    process = subprocess.Popen([sys.executable, "-m", "updatarr.main"], cwd=ROOT, env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        try:
            with urlopen(f"{base_url}/healthz", timeout=.4) as response:
                if response.status == 200: break
        except OSError: time.sleep(.05)
    else:
        process.terminate(); pytest.fail(process.stderr.read())
    try: yield base_url, port
    finally: process.terminate(); process.wait(timeout=3)


def _request(port: int, method: str, path: str, headers: dict[str, str] | None = None, body: dict | None = None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=4)
    final = {"Host": f"127.0.0.1:{port}", **(headers or {})}
    payload = json.dumps(body).encode() if body is not None else None
    if payload is not None: final["Content-Type"] = "application/json"
    connection.request(method, path, body=payload, headers=final)
    response = connection.getresponse(); data = response.read(); status = response.status
    response_headers = {key.lower(): value for key, value in response.getheaders()}
    connection.close(); return status, response_headers, data


def _login(port: int) -> tuple[str, str, dict]:
    status, headers, data = _request(port, "POST", "/api/v1/session",
        {"Origin": f"http://127.0.0.1:{port}"}, {"password": "updatarr-demo"})
    assert status == 200
    body = json.loads(data)
    return headers["set-cookie"].split(";", 1)[0], body["csrf_token"], body


def _auth(cookie: str) -> dict[str, str]: return {"Cookie": cookie}
def _mutation(port: int, cookie: str, csrf: str) -> dict[str, str]: return {"Cookie": cookie, "Origin": f"http://127.0.0.1:{port}", "X-CSRF-Token": csrf}


def _sse_until(port: int, cookie: str, expected: bytes) -> bytes:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=4)
    connection.request("GET", "/api/v1/events", headers={"Host": f"127.0.0.1:{port}", "Cookie": cookie, "Last-Event-ID": "0"})
    response = connection.getresponse(); captured = bytearray()
    while expected not in captured:
        line = response.readline()
        if not line: break
        captured.extend(line)
    response.close()
    connection.close()
    return bytes(captured)


def test_m1_read_only_flow_and_restart_persistence(tmp_path: Path) -> None:
    state = tmp_path / "state.db"
    with _server(state) as (_, port):
        cookie, csrf, session = _login(port)
        assert session["theme"] == "system"
        initial = json.loads(_request(port, "GET", "/api/v1/overview", _auth(cookie))[2])
        assert initial["snapshot"] is None and initial["summary"]["software_recorded"] == 0
        assert _request(port, "POST", "/api/v1/checks", _mutation(port, cookie, csrf))[0] == 202
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            overview = json.loads(_request(port, "GET", "/api/v1/overview", _auth(cookie))[2])
            if overview["snapshot"] is not None: break
            time.sleep(.05)
        assert overview["summary"] == {"updates_found": 5, "ready_to_review": 4, "blocked": 1, "restart_needed": 2, "software_recorded": 5}
        inventory = json.loads(_request(port, "GET", "/api/v1/inventory?limit=500", _auth(cookie))[2])
        assert inventory["total"] == 5 and len({item["stable_id"] for item in inventory["items"]}) == 5
        updates = json.loads(_request(port, "GET", "/api/v1/updates", _auth(cookie))[2])
        assert len(updates["items"]) == 5
        history = json.loads(_request(port, "GET", "/api/v1/history", _auth(cookie))[2])
        assert {item["kind"] for item in history["items"]}.issuperset({"signed_in", "inventory_check_started", "inventory_check_completed"})
        assert _request(port, "PUT", "/api/v1/settings/appearance", _mutation(port, cookie, csrf), {"theme": "norse"})[0] == 200
        assert _request(port, "PUT", "/api/v1/settings/appearance", _mutation(port, cookie, csrf), {"theme": "unknown"})[0] == 400

    with _server(state) as (_, port):
        status, _, restored_session = _request(port, "GET", "/api/v1/session", _auth(cookie))
        assert status == 200 and restored_session
        assert json.loads(restored_session)["csrf_token"] == csrf
        cookie, _, session = _login(port)
        assert session["theme"] == "norse"
        overview = json.loads(_request(port, "GET", "/api/v1/overview", _auth(cookie))[2])
        assert overview["summary"]["software_recorded"] == 5
        stream = _sse_until(port, cookie, b"event: check-complete")
        assert b"event: check-complete" in stream


@pytest.mark.parametrize("path", ["/api/v1/inventory", "/api/v1/updates", "/api/v1/history", "/api/v1/settings/appearance"])
def test_m1_read_endpoints_require_sign_in(tmp_path: Path, path: str) -> None:
    with _server(tmp_path / "state.db") as (_, port):
        assert _request(port, "GET", path)[0] == 401


def test_retired_stored_theme_falls_back_to_system(tmp_path: Path) -> None:
    state = tmp_path / "state.db"
    with _server(state) as (_, port):
        cookie, csrf, _ = _login(port)
        assert _request(port, "PUT", "/api/v1/settings/appearance", _mutation(port, cookie, csrf), {"theme": "norse"})[0] == 200
    with sqlite3.connect(state) as connection:
        connection.execute(
            "UPDATE preferences SET value_json = ? WHERE preference_key = 'theme'",
            ('"retired-theme"',),
        )
    with _server(state) as (_, port):
        _, _, session = _login(port)
        assert session["theme"] == "system"
