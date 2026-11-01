"""End-to-end checks for the disposable Phase 0 Overview prototype."""

from __future__ import annotations

import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import re
from urllib.request import urlopen

import pytest


ROOT = Path(__file__).resolve().parents[1]
PROTOTYPE = ROOT / "prototypes" / "overview" / "app.py"
THEME_IDS = (
    "light",
    "dark",
    "amoled",
    "solarized-light",
    "solarized-dark",
    "github-light",
    "github-dark",
    "norse",
    "nord",
    "gruvbox-light",
    "gruvbox-dark",
    "dracula",
    "catppuccin-latte",
    "catppuccin-mocha",
    "sepia",
    "midnight",
    "high-contrast",
)


def _relative_luminance(rgb: str) -> float:
    channels = [int(value) / 255 for value in re.findall(r"\d+", rgb)[:3]]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(first: str, second: str) -> float:
    lighter, darker = sorted((_relative_luminance(first), _relative_luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def _free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


@pytest.fixture(scope="module")
def prototype_server():
    port = _free_port()
    env = os.environ.copy()
    env["UPDATARR_PROTOTYPE_PORT"] = str(port)
    process = subprocess.Popen(
        [sys.executable, str(PROTOTYPE)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        try:
            with urlopen(f"{base_url}/healthz", timeout=0.5) as response:
                if response.status == 200:
                    break
        except OSError:
            time.sleep(0.05)
    else:
        process.terminate()
        process.wait(timeout=2)
        pytest.fail("prototype server did not become healthy")

    yield base_url, port
    process.terminate()
    process.wait(timeout=3)


def test_loopback_json_and_security_headers(prototype_server):
    base_url, _ = prototype_server
    with urlopen(f"{base_url}/api/v1/status", timeout=2) as response:
        payload = json.load(response)
        assert response.status == 200
        assert payload["prototype"] is True
        assert payload["summary"]["updates_found"] == 12
        assert payload["summary"]["ready_to_review"] == 11
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_unknown_host_is_rejected(prototype_server):
    _, port = prototype_server
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    connection.putrequest("GET", "/healthz", skip_host=True)
    connection.putheader("Host", "attacker.invalid")
    connection.endheaders()
    response = connection.getresponse()
    assert response.status == 400
    connection.close()


def test_sse_emits_typed_progress(prototype_server):
    _, port = prototype_server
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=4)
    connection.request("GET", "/api/v1/events")
    response = connection.getresponse()
    assert response.status == 200
    assert response.headers["Content-Type"].startswith("text/event-stream")

    event = {}
    for _ in range(12):
        line = response.readline().decode().strip()
        if not line:
            if event:
                break
            continue
        key, value = line.split(":", 1)
        event[key] = value.strip()
    payload = json.loads(event["data"])
    assert event["event"] == "scan-progress"
    assert payload["schema_version"] == 1
    assert payload["task_id"] == "prototype-scan"
    assert payload["sequence"] == 1
    connection.close()


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize(
    ("variant", "heading", "active_nav"),
    [
        ("A", "Overview", "Overview"),
        ("B", "Update sources", "Overview"),
        ("C", "Review updates", "Updates"),
    ],
)
@pytest.mark.parametrize(
    "viewport",
    [
        {"width": 1440, "height": 900},
        {"width": 681, "height": 800},
        {"width": 680, "height": 800},
        {"width": 390, "height": 844},
        {"width": 320, "height": 720},
    ],
)
def test_variants_are_responsive_and_named(
    prototype_server, theme, variant, heading, active_nav, viewport
):
    playwright = pytest.importorskip("playwright.sync_api")
    base_url, _ = prototype_server
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = browser.new_page(viewport=viewport, color_scheme=theme)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(f"{base_url}/?variant={variant}", wait_until="networkidle")

        assert page.locator("h1").text_content() == heading
        assert page.locator(".mobile-nav [aria-current='page'] span").text_content() == active_nav
        assert page.locator(".prototype-switcher").get_attribute("aria-label") == (
            f"Prototype variant {variant} of 3"
        )
        assert page.evaluate(
            "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
        )
        assert errors == []
        browser.close()


def test_keyboard_switcher_updates_the_url(prototype_server):
    playwright = pytest.importorskip("playwright.sync_api")
    base_url, _ = prototype_server
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{base_url}/?variant=A", wait_until="networkidle")
        page.keyboard.press("ArrowRight")
        assert page.url.endswith("?variant=B")
        assert page.locator("h1").text_content() == "Update sources"
        browser.close()


@pytest.mark.parametrize("variant", ["A", "B", "C"])
def test_visible_copy_avoids_internal_jargon(prototype_server, variant):
    playwright = pytest.importorskip("playwright.sync_api")
    base_url, _ = prototype_server
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{base_url}/?variant={variant}", wait_until="networkidle")
        # text_content includes hidden text that can supply an accessible name
        # through aria-labelledby or aria-describedby.
        document_text = page.locator("body").text_content().lower()
        accessible_names = page.locator("[aria-label], [alt], [title]").evaluate_all(
            """elements => elements.map((element) =>
              element.getAttribute('aria-label') ||
              element.getAttribute('alt') ||
              element.getAttribute('title') || ''
            ).join(' ').toLowerCase()"""
        )
        interface_copy = f"{document_text} {accessible_names}"
        for internal_term in (
            "actionable",
            "artifact",
            "authorization",
            "atomic group",
            "backend",
            "consistency set",
            "defer",
            "disabled",
            "healthy",
            "intent",
            "job",
            "local confirmation",
            "native group",
            "offer",
            "ownership domain",
            "provider",
            "reconcile",
            "reconciliation",
            "stale",
            "transaction",
            "unmanaged",
            "unsupported",
        ):
            assert internal_term not in interface_copy
        browser.close()


@pytest.mark.parametrize("theme", THEME_IDS)
def test_explicit_theme_profiles_apply_without_overflow(prototype_server, theme):
    playwright = pytest.importorskip("playwright.sync_api")
    base_url, _ = prototype_server
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(f"{base_url}/?variant=B&theme={theme}", wait_until="networkidle")

        assert page.locator("html").get_attribute("data-theme") == theme
        assert page.locator(".prototype-theme select").input_value() == theme
        assert page.locator(".topbar select").count() == 0
        assert page.evaluate(
            "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
        )
        assert page.evaluate(
            "getComputedStyle(document.documentElement).getPropertyValue('--canvas').trim()"
        )
        colors = page.evaluate(
            """() => {
              const probe = document.createElement('span');
              document.body.appendChild(probe);
              const resolve = (token) => {
                probe.style.color = `var(${token})`;
                return getComputedStyle(probe).color;
              };
              const result = {
                ink: resolve('--ink'),
                canvas: resolve('--canvas'),
                surface: resolve('--surface'),
                focus: resolve('--focus'),
                muted: resolve('--muted'),
                brandAccent: resolve('--brand-accent'),
                glyphSurface: resolve('--glyph-surface'),
                groupSurface: resolve('--group-surface'),
                groupIndependent: resolve('--group-independent'),
                blockSurface: resolve('--block-surface'),
                successText: resolve('--success-text'),
                successSurface: resolve('--success-surface'),
                warningText: resolve('--warning-text'),
                warningSurface: resolve('--warning-pill'),
                dangerText: resolve('--danger-text'),
                dangerSurface: resolve('--danger-surface'),
              };
              probe.remove();
              return result;
            }"""
        )
        assert _contrast(colors["ink"], colors["canvas"]) >= 4.5
        assert _contrast(colors["ink"], colors["surface"]) >= 4.5
        for surface in (
            "canvas",
            "surface",
            "groupSurface",
            "groupIndependent",
            "blockSurface",
        ):
            assert _contrast(colors["muted"], colors[surface]) >= 4.5
        for surface in ("canvas", "surface", "glyphSurface"):
            assert _contrast(colors["brandAccent"], colors[surface]) >= 4.5
        assert _contrast(colors["successText"], colors["successSurface"]) >= 4.5
        assert _contrast(colors["warningText"], colors["warningSurface"]) >= 4.5
        assert _contrast(colors["dangerText"], colors["dangerSurface"]) >= 4.5
        assert _contrast(colors["focus"], colors["canvas"]) >= 3
        assert _contrast(colors["focus"], colors["surface"]) >= 3
        browser.close()


def test_system_theme_uses_no_explicit_override(prototype_server):
    playwright = pytest.importorskip("playwright.sync_api")
    base_url, _ = prototype_server
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = browser.new_page(color_scheme="dark")
        page.goto(f"{base_url}/?variant=A", wait_until="networkidle")
        assert page.locator("html").get_attribute("data-theme") is None
        assert page.locator(".prototype-theme select").input_value() == "system"
        assert page.evaluate("getComputedStyle(document.documentElement).colorScheme") == "dark"
        browser.close()
