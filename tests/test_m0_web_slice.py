"""Real-listener and browser evidence for the M0 production stack slice."""

from __future__ import annotations

from contextlib import contextmanager
import http.client
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

import pytest

from updatarr.domain import InventorySnapshot, SoftwareRecord, SourceResult, SourceState, utc_now
from updatarr.storage import StateStore

ROOT = Path(__file__).resolve().parents[1]
THEMES = (
    "system", "light", "dark", "amoled", "solarized-light", "solarized-dark",
    "github-light", "github-dark", "norse", "nord", "gruvbox-light",
    "gruvbox-dark", "dracula", "catppuccin-latte", "catppuccin-mocha",
    "sepia", "midnight", "high-contrast",
)


def _luminance(color: str) -> float:
    channels = [int(value) / 255 for value in re.findall(r"\d+", color)[:3]]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(first: str, second: str) -> float:
    lighter, darker = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def _free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


@contextmanager
def _server(url_base: str = "", event_history_limit: int = 100, seed=None):  # type: ignore[no-untyped-def]
    port = _free_port()
    state_directory = tempfile.TemporaryDirectory(prefix="updatarr-test-")
    env = os.environ.copy()
    state_path = Path(state_directory.name) / "state.db"
    if seed is not None:
        seed(state_path)
    env.update({
        "PYTHONPATH": str(ROOT / "src"), "UPDATARR_PORT": str(port), "UPDATARR_URL_BASE": url_base,
            "UPDATARR_PROVIDER_MODE": "simulator",
            "UPDATARR_DEVELOPMENT_MODE": "1",
        "UPDATARR_STATE_PATH": str(state_path),
        "UPDATARR_EVENT_HISTORY_LIMIT": str(event_history_limit),
    })
    process = subprocess.Popen(
        [sys.executable, "-m", "updatarr.main"], cwd=ROOT, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
    )
    base_url = f"http://127.0.0.1:{port}{url_base}"
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        try:
            with urlopen(f"{base_url}/healthz", timeout=0.4) as response:
                if response.status == 200:
                    break
        except OSError:
            time.sleep(0.05)
    else:
        process.terminate()
        pytest.fail(f"M0 server did not start: {process.stderr.read()}")
    try:
        yield base_url, port
    finally:
        process.terminate()
        process.wait(timeout=3)
        state_directory.cleanup()


@pytest.fixture(scope="module")
def server():
    with _server() as running:
        yield running


def _request(port: int, method: str, path: str, *, headers: dict[str, str] | None = None, body: dict[str, object] | None = None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    final_headers = {"Host": f"127.0.0.1:{port}", **(headers or {})}
    payload = json.dumps(body).encode() if body is not None else None
    if payload is not None:
        final_headers["Content-Type"] = "application/json"
    connection.request(method, path, body=payload, headers=final_headers)
    response = connection.getresponse()
    data = response.read()
    result = response.status, {name.lower(): value for name, value in response.getheaders()}, data
    connection.close()
    return result


def _chunked_request(port: int, path: str, chunks: list[bytes]) -> int:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    connection.putrequest("POST", path, skip_host=True)
    connection.putheader("Host", f"127.0.0.1:{port}")
    connection.putheader("Origin", f"http://127.0.0.1:{port}")
    connection.putheader("Content-Type", "application/json")
    connection.putheader("Transfer-Encoding", "chunked")
    connection.endheaders()
    for chunk in chunks:
        connection.send(f"{len(chunk):X}\r\n".encode() + chunk + b"\r\n")
    connection.send(b"0\r\n\r\n")
    response = connection.getresponse()
    response.read()
    status = response.status
    connection.close()
    return status


def _open_sse(port: int, cookie: str, last_event_id: str = "0"):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    connection.request(
        "GET", "/api/v1/events",
        headers={"Host": f"127.0.0.1:{port}", "Cookie": cookie, "Last-Event-ID": last_event_id},
    )
    response = connection.getresponse()
    assert response.status == 200
    return connection, response


def _read_sse_until(response: http.client.HTTPResponse, expected: bytes) -> bytes:
    captured = bytearray()
    while expected not in captured:
        line = response.readline()
        if not line:
            break
        captured.extend(line)
    return bytes(captured)


def _login(port: int, base: str = "") -> tuple[str, str]:
    status, headers, body = _request(
        port, "POST", f"{base}/api/v1/session",
        headers={"Origin": f"http://127.0.0.1:{port}"},
        body={"password": "updatarr-demo"},
    )
    assert status == 200
    cookie = headers["set-cookie"].split(";", 1)[0]
    assert "HttpOnly" in headers["set-cookie"] and "SameSite=strict" in headers["set-cookie"]
    document = json.loads(body)
    assert document["api_version"] == 1
    return cookie, document["csrf_token"]


def test_health_is_minimal_and_static_spa_is_same_origin(server) -> None:
    base_url, port = server
    with urlopen(f"{base_url}/healthz") as response:
        assert json.load(response) == {"status": "ok"}
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    status, _, body = _request(port, "GET", "/")
    assert status == 200
    assert b'<div id="root"></div>' in body


def test_auth_host_origin_csrf_and_duplicate_task_boundaries(server) -> None:
    _, port = server
    status, _, _ = _request(port, "GET", "/api/v1/overview")
    assert status == 401
    assert _request(port, "POST", "/api/v1/session", body={"password": "updatarr-demo"})[0] == 403
    assert _request(port, "POST", "/api/v1/session", headers={"Origin": "https://attacker.invalid"}, body={"password": "updatarr-demo"})[0] == 403
    assert _request(port, "POST", "/api/v1/session", headers={"Origin": f"http://127.0.0.1:{port}"}, body={"password": "x" * 9000})[0] == 413
    assert _chunked_request(port, "/api/v1/session", [b'{"password":"', b"x" * 5000, b"x" * 5000, b'"}']) == 413
    assert _request(port, "GET", "/api/v1/not-a-route")[0] == 404
    cookie, csrf = _login(port)
    origin = f"http://127.0.0.1:{port}"

    assert _request(port, "POST", "/api/v1/checks", headers={"Cookie": cookie})[0] == 403
    assert _request(port, "POST", "/api/v1/checks", headers={"Cookie": cookie, "Origin": "null", "X-CSRF-Token": csrf})[0] == 403
    assert _request(port, "POST", "/api/v1/checks", headers={"Cookie": cookie, "Origin": "https://attacker.invalid", "X-CSRF-Token": csrf})[0] == 403
    first = _request(port, "POST", "/api/v1/checks", headers={"Cookie": cookie, "Origin": origin, "X-CSRF-Token": csrf})
    second = _request(port, "POST", "/api/v1/checks", headers={"Cookie": cookie, "Origin": origin, "X-CSRF-Token": csrf})
    assert first[0] == 202 and json.loads(first[2])["created"] is True
    assert second[0] == 200 and json.loads(second[2])["created"] is False
    assert json.loads(first[2])["task"]["id"] == json.loads(second[2])["task"]["id"]

    assert _request(port, "GET", "/healthz", headers={"Host": "attacker.invalid"})[0] == 400
    assert _request(port, "GET", "/healthz", headers={"Forwarded": "host=attacker.invalid"})[0] == 400


def test_authenticated_sse_has_event_ids_and_reconnects(server) -> None:
    _, port = server
    cookie, csrf = _login(port)
    connection, response = _open_sse(port, cookie, "0")
    replay = _read_sse_until(response, b"retry: 1500")
    assert b"retry: 1500" in replay
    origin = f"http://127.0.0.1:{port}"
    assert _request(port, "POST", "/api/v1/checks", headers={"Cookie": cookie, "Origin": origin, "X-CSRF-Token": csrf})[0] in {200, 202}
    live = _read_sse_until(response, b"event: check-complete")
    assert b"event: check-progress" in live or b"event: check-complete" in live
    assert re.search(rb"id: [1-9]", live)
    response.close()
    connection.close()


def test_non_root_url_base_serves_spa_and_api() -> None:
    with _server("/updatarr") as (base_url, port):
        with urlopen(f"{base_url}/") as response:
            html = response.read().decode()
            assert response.status == 200
            assert "./assets/" in html
        cookie, _ = _login(port, "/updatarr")
        status, _, body = _request(port, "GET", "/updatarr/api/v1/overview", headers={"Cookie": cookie})
        assert status == 200
        assert json.loads(body)["mode"] == "Read-only"


@pytest.mark.parametrize("viewport", [{"width": 1440, "height": 900}, {"width": 681, "height": 800}, {"width": 680, "height": 800}, {"width": 390, "height": 844}, {"width": 320, "height": 700}])
def test_browser_layout_has_no_horizontal_overflow(server, viewport) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    base_url, _ = server
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = browser.new_page(viewport=viewport)
        page.goto(base_url)
        page.get_by_role("button", name="Sign in").click()
        page.get_by_role("heading", name="Software Overview").wait_for()
        assert page.get_by_role("button", name="Check software").is_visible()
        page.get_by_role("button", name="Check software").click()
        page.locator(".metrics strong", has_text="5").first.wait_for(timeout=4000)
        for view in ("Overview", "Software", "Updates", "History", "Settings"):
            page.get_by_role("button", name=view, exact=True).click()
            dimensions = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
            assert dimensions["scroll"] <= dimensions["client"], view
        browser.close()


def test_m1_browser_flow_filters_software_and_persists_theme(server) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    base_url, _ = server
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(base_url)
        page.get_by_role("button", name="Sign in").click()
        page.get_by_role("button", name="Check software").click()
        page.locator(".metrics strong", has_text="5").first.wait_for(timeout=4000)
        page.get_by_role("button", name="Software", exact=True).click()
        page.get_by_label("Find software").fill("firefox")
        page.get_by_role("button", name="Search").click()
        page.wait_for_function("() => document.querySelectorAll('tbody tr').length === 1")
        page.get_by_text("Firefox", exact=True).wait_for()
        assert page.locator("tbody tr").count() == 1
        page.get_by_role("button", name="Settings", exact=True).click()
        page.get_by_label("Theme").select_option("norse")
        page.reload()
        page.get_by_role("button", name="Settings", exact=True).click()
        assert page.get_by_label("Theme").input_value() == "norse"
        assert page.locator("html").get_attribute("data-theme") == "norse"
        browser.close()


def test_sse_history_reset_preserves_active_software_filter() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with _server(event_history_limit=2) as (base_url, port):
        with playwright.sync_playwright() as runtime:
            browser = runtime.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page(); page.goto(base_url)
            page.get_by_role("button", name="Sign in").click()
            page.get_by_role("button", name="Check software").click()
            page.get_by_text("Read-only inventory check complete").wait_for(timeout=8000)
            page.get_by_role("button", name="Software", exact=True).click()
            page.get_by_label("Find software").fill("firefox")
            page.get_by_role("button", name="Search").click()
            page.wait_for_function("() => document.querySelectorAll('tbody tr').length === 1")

            context.set_offline(True)
            cookie, csrf = _login(port)
            assert _request(port, "POST", "/api/v1/checks", headers={
                "Cookie": cookie, "Origin": f"http://127.0.0.1:{port}", "X-CSRF-Token": csrf,
            })[0] == 202
            deadline = time.monotonic() + 4
            while time.monotonic() < deadline:
                overview = json.loads(_request(port, "GET", "/api/v1/overview", headers={"Cookie": cookie})[2])
                if overview.get("task", {}).get("state") == "complete":
                    break
                time.sleep(.05)
            else:
                pytest.fail("simulated check did not complete")
            context.set_offline(False)
            page.wait_for_timeout(2200)
            assert page.locator("tbody tr").count() == 1
            assert page.get_by_text("Firefox", exact=True).is_visible()
            browser.close()


def test_all_themes_are_in_settings_and_not_the_top_bar(server) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    base_url, _ = server
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(base_url)
        page.get_by_role("button", name="Sign in").click()
        assert page.locator(".topbar select").count() == 0
        page.get_by_role("button", name="Settings", exact=True).click()
        selector = page.get_by_label("Theme")
        assert selector.is_visible()
        assert selector.locator("option").count() == len(THEMES)
        for theme in THEMES:
            page.get_by_role("button", name="Settings", exact=True).click()
            selector.select_option(theme)
            expected = "" if theme == "system" else theme
            assert page.locator("html").get_attribute("data-theme") in (expected, None)
            for view in ("Overview", "Software", "Updates", "History", "Settings"):
                page.get_by_role("button", name=view, exact=True).click()
                dimensions = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
                assert dimensions["scroll"] <= dimensions["client"], (theme, view)
            colors = page.evaluate("""() => {
              const buttonProbe = document.createElement('button');
              buttonProbe.className = 'primary';
              document.body.appendChild(buttonProbe);
              const button = getComputedStyle(buttonProbe);
              const resolve = token => {
                const probe = document.createElement('i');
                probe.style.color = `var(${token})`;
                document.body.appendChild(probe);
                const value = getComputedStyle(probe).color;
                probe.remove();
                return value;
              };
              const result = {
                buttonText: button.color, buttonBackground: button.backgroundColor,
                muted: resolve('--muted'), focus: resolve('--focus'),
                canvas: resolve('--canvas'), surface: resolve('--surface'),
              };
              buttonProbe.remove();
              return result;
            }""")
            assert _contrast(colors["buttonText"], colors["buttonBackground"]) >= 4.5
            assert _contrast(colors["muted"], colors["canvas"]) >= 4.5
            assert _contrast(colors["muted"], colors["surface"]) >= 4.5
            assert _contrast(colors["focus"], colors["canvas"]) >= 3
            assert _contrast(colors["focus"], colors["surface"]) >= 3
        browser.close()


def test_system_theme_keyboard_reduced_motion_and_200_percent_zoom(server) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    base_url, _ = server
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
        page.goto(base_url)
        page.get_by_role("button", name="Sign in").click()
        page.get_by_role("button", name="Settings", exact=True).click()
        selector = page.get_by_label("Theme")
        selector.focus(); selector.press("Home"); selector.press("ArrowDown")
        assert selector.input_value() == "light"
        selector.select_option("system")
        page.emulate_media(color_scheme="light", reduced_motion="reduce")
        light_canvas = page.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--canvas')")
        page.emulate_media(color_scheme="dark", reduced_motion="reduce")
        dark_canvas = page.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--canvas')")
        assert light_canvas != dark_canvas
        transition = page.evaluate("""() => {
          const bar = document.createElement('div'); bar.className = 'progress';
          const fill = document.createElement('span'); bar.appendChild(fill); document.body.appendChild(bar);
          const value = getComputedStyle(fill).transitionDuration; bar.remove(); return value;
        }""")
        assert transition == "0s"
        page.evaluate("document.body.style.zoom = '2'")
        for view in ("Overview", "Software", "Updates", "History", "Settings"):
            page.get_by_role("button", name=view, exact=True).click()
            dimensions = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
            assert dimensions["scroll"] <= dimensions["client"], view
        browser.close()


def test_m6_high_density_400_percent_zoom_and_accessible_controls(server) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    base_url, _ = server
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,
            reduced_motion="reduce",
        )
        page = context.new_page()
        page.goto(base_url)
        page.get_by_role("button", name="Sign in").click()
        page.get_by_role("button", name="Check software").click()
        page.locator(".metrics strong", has_text="5").first.wait_for(timeout=4000)
        # A 360 CSS-pixel viewport represents a 1440-pixel desktop at 400%
        # reflow zoom. DPR 2 separately exercises high-density rendering.
        page.set_viewport_size({"width": 360, "height": 800})
        for view in ("Overview", "Software", "Updates", "History", "Settings"):
            page.get_by_role("button", name=view, exact=True).click()
            if view == "Software":
                page.get_by_role("navigation", name="Installed software pages").get_by_text(
                    "1–5 of 5 recorded", exact=True
                ).wait_for()
            audit = page.evaluate("""() => ({
              overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
              duplicateIds: [...document.querySelectorAll('[id]')]
                .map(node => node.id).filter((id, index, ids) => ids.indexOf(id) !== index),
              unnamedButtons: [...document.querySelectorAll('button')]
                .filter(node => !(node.getAttribute('aria-label') || node.textContent?.trim())).length,
              unlabeledInputs: [...document.querySelectorAll('input, select, textarea')]
                .filter(node => node.labels?.length === 0 && !node.getAttribute('aria-label')).length,
            })""")
            assert audit == {
                "overflow": False,
                "duplicateIds": [],
                "unnamedButtons": 0,
                "unlabeledInputs": 0,
            }, view
        browser.close()


def test_m6_browser_rejects_an_incompatible_service_version(server) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    base_url, _ = server
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = browser.new_page()

        def change_version(route):  # type: ignore[no-untyped-def]
            if route.request.method != "POST":
                route.continue_()
                return
            response = route.fetch()
            body = response.json()
            body["api_version"] = 2
            route.fulfill(response=response, json=body)

        page.route("**/api/v1/session", change_version)
        page.goto(base_url)
        page.get_by_role("button", name="Sign in").click()
        page.get_by_role("alert").get_by_text(
            "This page and the Updatarr service use different versions.", exact=False
        ).wait_for()
        assert page.get_by_role("heading", name="Software Overview").count() == 0
        browser.close()


def test_m6_large_inventory_pager_keeps_unsubmitted_search_separate() -> None:
    playwright = pytest.importorskip("playwright.sync_api")

    def seed(path: Path) -> None:
        records = tuple(
            SoftwareRecord(
                "native", "system", f"package-{index:04d}", f"Package {index:04d}",
                "1", ownership="native_repository",
            )
            for index in range(205)
        )
        snapshot = InventorySnapshot.create(utc_now(), [SourceResult(
            "native", "System packages", "system", SourceState.UP_TO_DATE,
            "Current", utc_now(), 1, records, (),
        )])
        store = StateStore(path)
        store.initialize()
        store.save_snapshot(snapshot)

    with _server(seed=seed) as (base_url, _port), playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(base_url)
        page.get_by_role("button", name="Sign in").click()
        page.get_by_role("button", name="Software", exact=True).click()
        pager = page.get_by_role("navigation", name="Installed software pages")
        pager.get_by_text("1–100 of 205 recorded", exact=True).wait_for()

        page.get_by_label("Find software").fill("package-020")
        pager.get_by_role("button", name="Next").click()
        pager.get_by_text("101–200 of 205 recorded", exact=True).wait_for()
        pager.get_by_role("button", name="Previous").click()
        pager.get_by_text("1–100 of 205 recorded", exact=True).wait_for()

        page.get_by_role("button", name="Search", exact=True).click()
        pager.get_by_text("1–5 of 5 recorded", exact=True).wait_for()
        assert page.locator("tbody tr").count() == 5
        browser.close()


def test_navigation_and_live_progress_have_accessible_state(server) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    base_url, _ = server
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(base_url)
        page.get_by_role("button", name="Sign in").click()
        page.get_by_role("heading", name="Software Overview").wait_for()
        assert page.locator('[aria-current="page"]').count() == 2
        assert page.get_by_role("status").count() == 1
        page.get_by_role("button", name="Check software").click()
        progress = page.get_by_role("progressbar", name="Software check progress")
        progress.wait_for(state="visible", timeout=1000)
        assert progress.get_attribute("aria-valuenow") is not None
        browser.close()


def test_production_copy_avoids_internal_jargon(server) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    base_url, _ = server
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(base_url)
        page.get_by_role("button", name="Sign in").click()
        collected = []
        for view in ("Overview", "Software", "Updates", "History", "Settings"):
            page.get_by_role("button", name=view, exact=True).click()
            collected.append(page.locator("body").text_content().lower())
        interface_copy = " ".join(collected)
        for internal_term in (
            "actionable", "artifact", "authorization", "atomic group", "backend",
            "consistency set", "defer", "disabled", "healthy", "intent", "job",
            "local confirmation", "native group", "offer", "ownership domain",
            "provider", "reconcile", "reconciliation", "stale", "transaction",
            "unmanaged", "unsupported",
        ):
            assert internal_term not in interface_copy
        browser.close()
