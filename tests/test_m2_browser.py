"""Real-browser evidence for M2 catalog, saved choices, safety and history flows."""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


@contextmanager
def _server():
    port = _free_port()
    state_directory = tempfile.TemporaryDirectory(prefix="updatarr-m2-browser-")
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": str(ROOT / "src"), "UPDATARR_PORT": str(port),
        "UPDATARR_PROVIDER_MODE": "simulator",
        "UPDATARR_DEVELOPMENT_MODE": "1",
        "UPDATARR_PASSWORD": "test-only-password",
        "UPDATARR_STATE_PATH": str(Path(state_directory.name) / "state.db"),
        "UPDATARR_STATIC_DIR": str(ROOT / "web" / "dist"),
    })
    process = subprocess.Popen(
        [sys.executable, "-m", "updatarr.main"], cwd=ROOT, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
    )
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        try:
            with urlopen(f"{base_url}/healthz", timeout=.4) as response:
                if response.status == 200:
                    break
        except OSError:
            time.sleep(.05)
    else:
        process.terminate()
        pytest.fail(process.stderr.read())
    try:
        yield base_url
    finally:
        process.terminate(); process.wait(timeout=3); state_directory.cleanup()


def _signed_in_page(browser, base_url: str, viewport: dict[str, int]):  # type: ignore[no-untyped-def]
    page = browser.new_page(viewport=viewport)
    page.goto(base_url)
    page.get_by_label("Password").fill("test-only-password")
    page.get_by_role("button", name="Sign in", exact=True).click()
    page.get_by_role("heading", name="Software Overview").wait_for()
    return page


def _run_check(page) -> None:  # type: ignore[no-untyped-def]
    page.get_by_role("button", name="Check software").click()
    page.locator(".metrics strong", has_text="5").first.wait_for(timeout=4000)


def _open_update_details(page) -> None:  # type: ignore[no-untyped-def]
    details = page.locator(".workflow-details")
    if not details.evaluate("node => node.open"):
        page.get_by_text("Safety and technical details", exact=True).click()


def _assert_update_header_geometry(page, viewport_width: int) -> None:  # type: ignore[no-untyped-def]
    panel_box = page.locator(".table-panel").bounding_box()
    group = page.locator(".group-title")
    group_box = group.bounding_box()
    count_box = group.locator(":scope > span").first.bounding_box()
    copy_box = group.locator(":scope > div").bounding_box()
    status_box = group.locator(".status").bounding_box()
    assert panel_box is not None and group_box is not None
    assert count_box is not None and copy_box is not None and status_box is not None
    assert abs(group_box["x"] - panel_box["x"]) <= 1
    assert abs(group_box["y"] - panel_box["y"]) <= 1
    expected_inline_padding = 15 if viewport_width <= 390 else 22
    expected_block_padding = 14 if viewport_width <= 390 else 17
    assert abs((count_box["x"] - group_box["x"]) - expected_inline_padding) <= 1
    assert min(count_box["y"], copy_box["y"], status_box["y"]) - group_box["y"] >= expected_block_padding - 1
    centers = [box["y"] + box["height"] / 2 for box in (count_box, copy_box, status_box)]
    assert max(centers) - min(centers) < 1


def test_catalog_results_are_explicit_source_choices() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with _server() as base_url, playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = _signed_in_page(browser, base_url, {"width": 1440, "height": 900})
        _run_check(page)
        page.get_by_role("button", name="Software", exact=True).click()
        installed_links = page.locator("a.software-link")
        installed_links.first.wait_for()
        assert installed_links.count() == 5
        assert all(link.startswith("https://") for link in installed_links.evaluate_all("links => links.map(link => link.href)"))
        page.get_by_role("button", name="Find new software").click()
        page.get_by_role("button", name="Search sources").click()
        page.wait_for_function("() => document.querySelectorAll('tbody tr').length === 4")
        assert page.get_by_role("cell", name="Arch repositories extra").is_visible()
        assert page.get_by_role("cell", name="AUR (user-submitted) aur").is_visible()
        assert page.get_by_role("cell", name="Flatpak flathub").first.is_visible()
        assert page.get_by_text("Kdenlive", exact=True).count() == 3
        assert page.get_by_text("Kdenlive development build", exact=True).count() == 1
        assert page.get_by_role("link", name="Read source documentation").count() == 4
        assert page.locator("a.software-link").count() == 4
        page.get_by_role("button", name="Preview build file").click()
        page.get_by_role("heading", name="kdenlive-git").wait_for()
        assert page.get_by_text("No earlier copy is recorded", exact=False).is_visible()
        assert page.locator(".aur-preview pre").get_by_text("build()", exact=False).is_visible()
        browser.close()


def test_installed_software_hides_repeated_names_and_pins_the_table_header() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with _server() as base_url, playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = _signed_in_page(browser, base_url, {"width": 1280, "height": 620})
        assert page.get_by_text("Not checked means installed software was recorded", exact=False).is_visible()
        _run_check(page)
        page.get_by_role("button", name="Software", exact=True).click()
        rows = page.locator(".software-table-wrap tbody tr")
        rows.first.wait_for()
        repeated_identifiers = rows.evaluate_all("""rows => rows.filter(row => {
            const name = row.querySelector('td b')?.textContent?.trim().toLocaleLowerCase();
            const identifier = row.querySelector('td small')?.textContent?.trim().toLocaleLowerCase();
            return name && identifier && name === identifier;
        }).length""")
        assert repeated_identifiers == 0
        header = page.locator(".software-table-wrap thead th").first
        assert header.evaluate("node => getComputedStyle(node).position") == "sticky"
        assert header.evaluate("node => getComputedStyle(node).top") == "0px"
        page.locator(".software-table-wrap tbody").evaluate("""body => {
            const row = body.querySelector('tr');
            for (let index = 0; index < 30; index += 1) body.append(row.cloneNode(true));
        }""")
        header_top = header.bounding_box()["y"]
        page.locator(".software-table-wrap").evaluate("node => node.scrollTop = 600")
        assert abs(header.bounding_box()["y"] - header_top) <= 1
        browser.close()


def test_detected_updates_header_selects_and_clears_every_update() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with _server() as base_url, playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = _signed_in_page(browser, base_url, {"width": 1280, "height": 800})
        _run_check(page)
        page.get_by_role("button", name="Updates", exact=True).click()
        _open_update_details(page)
        select_all = page.get_by_role("checkbox", name="Select all detected updates")
        update_boxes = page.locator('.detected-updates tbody input[type="checkbox"]')
        select_all.check()
        assert update_boxes.count() > 1
        assert update_boxes.evaluate_all("boxes => boxes.every(box => box.checked)")
        update_boxes.first.uncheck()
        assert select_all.evaluate("box => box.indeterminate") is True
        select_all.click()
        assert update_boxes.evaluate_all("boxes => boxes.every(box => box.checked)")
        select_all.uncheck()
        assert update_boxes.evaluate_all("boxes => boxes.every(box => !box.checked)")
        browser.close()


def test_partial_system_selection_is_blocked_and_group_choice_persists() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with _server() as base_url, playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = _signed_in_page(browser, base_url, {"width": 1280, "height": 800})
        _run_check(page)
        page.get_by_role("button", name="Updates", exact=True).click()
        _open_update_details(page)
        _assert_update_header_geometry(page, 1280)
        help_button = page.get_by_role("button", name="Information: How Ready Updates Work")
        help_button.hover()
        help_id = help_button.get_attribute("aria-describedby")
        assert help_id
        help_panel = page.locator(f'[id="{help_id}"]')
        assert help_panel.get_by_text("Wait one day", exact=False).is_visible()
        assert help_panel.get_by_text("A newer version will appear", exact=False).is_visible()
        assert help_panel.get_by_text("future versions waiting", exact=False).is_visible()
        page.mouse.move(0, 0)
        help_panel.wait_for(state="hidden")
        page.get_by_role("checkbox", name="Include Firefox in safety check").check()
        page.get_by_role("button", name="Check whether selection is safe").click()
        page.get_by_text("Selection blocked", exact=True).wait_for()
        assert page.locator(".decision", has_text="System packages must update together").is_visible()

        page.get_by_label("Saved choice for Firefox").select_option("postpone")
        page.get_by_text("Postponed", exact=True).first.wait_for()
        assert page.get_by_text("Postponed", exact=True).count() >= 2
        saved = page.evaluate("() => fetch('./api/v1/policies').then(response => response.json())")
        assert saved["items"][0]["expires_at"] is not None
        page.get_by_role("button", name="Settings", exact=True).click()
        assert page.get_by_text("Postponed until", exact=False).is_visible()
        page.get_by_role("button", name="Updates", exact=True).click()
        csrf = page.evaluate("() => fetch('./api/v1/session').then(response => response.json()).then(body => body.csrf_token)")
        second = page.evaluate("""async ({csrf}) => {
            const response = await fetch('./api/v1/policies', {
              method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf},
              body: JSON.stringify({kind: 'pause_software', source_id: 'native', scope: 'system', software_id: 'system-update-group'})
            });
            return response.status;
        }""", {"csrf": csrf})
        assert second == 201
        page.reload()
        page.get_by_role("button", name="Updates", exact=True).click()
        _open_update_details(page)
        page.get_by_text("Paused", exact=True).first.wait_for()
        page.get_by_role("button", name="Remove saved choice").first.click()
        page.get_by_label("Saved choice for Firefox").wait_for()
        assert page.get_by_text("Ready to review", exact=True).count() >= 2
        assert page.evaluate("() => fetch('./api/v1/policies').then(response => response.json()).then(body => body.total)") == 0
        page.get_by_label("Saved choice for Firefox").select_option("pause_software")
        page.get_by_text("Paused", exact=True).first.wait_for()
        page.get_by_role("button", name="Settings", exact=True).click()
        assert page.get_by_text("All system packages", exact=True).is_visible()
        page.reload()
        page.get_by_role("button", name="Settings", exact=True).click()
        page.get_by_text("All system packages", exact=True).wait_for()
        browser.close()


def test_generated_logo_is_loaded_and_centered() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with _server() as base_url, playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = _signed_in_page(browser, base_url, {"width": 1280, "height": 800})
        def assert_centered(selector: str) -> None:
            mark = page.locator(selector)
            glyph = mark.locator("img")
            assert glyph.evaluate("image => image.complete && image.naturalWidth === 128 && image.naturalHeight === 128")
            boxes = {"mark": mark.bounding_box(), "glyph": glyph.bounding_box()}
            assert boxes["mark"] is not None and boxes["glyph"] is not None
            assert boxes["glyph"]["width"] == 36 and boxes["glyph"]["height"] == 36
            assert abs((boxes["mark"]["x"] + boxes["mark"]["width"] / 2) - (boxes["glyph"]["x"] + boxes["glyph"]["width"] / 2)) < .5
            assert abs((boxes["mark"]["y"] + boxes["mark"]["height"] / 2) - (boxes["glyph"]["y"] + boxes["glyph"]["height"] / 2)) < .5

        assert_centered(".rail .mark")
        browser.close()


def test_history_import_is_labeled_partial_and_idempotent() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with _server() as base_url, playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = _signed_in_page(browser, base_url, {"width": 1280, "height": 800})
        page.get_by_role("button", name="History", exact=True).click()
        page.get_by_role("button", name="Import earlier activity").click()
        page.get_by_text("Updated firefox", exact=True).wait_for()
        assert page.get_by_text("Incomplete history", exact=False).count() == 3
        assert page.get_by_text("No download data recorded", exact=True).is_visible()
        page.get_by_role("button", name="Import earlier activity").click()
        page.get_by_text("History is already current", exact=True).wait_for()
        assert page.get_by_text("Updated firefox", exact=True).count() == 1
        browser.close()


@pytest.mark.parametrize("viewport", [
    {"width": 1440, "height": 900}, {"width": 681, "height": 800},
    {"width": 680, "height": 800}, {"width": 390, "height": 844},
    {"width": 320, "height": 700},
])
def test_m2_flows_have_no_document_overflow(viewport: dict[str, int]) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with _server() as base_url, playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = _signed_in_page(browser, base_url, viewport)
        _run_check(page)
        page.get_by_role("button", name="Software", exact=True).click()
        page.get_by_role("button", name="Find new software").click()
        page.get_by_role("button", name="Search sources").click()
        page.get_by_text("Kdenlive development build", exact=True).wait_for()
        for destination in ("Software", "Updates", "History", "Settings"):
            page.get_by_role("button", name=destination, exact=True).click()
            if destination == "Updates":
                page.get_by_role("heading", name="Ready Updates").wait_for()
                _open_update_details(page)
                _assert_update_header_geometry(page, viewport["width"])
            dimensions = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
            assert dimensions["scroll"] <= dimensions["client"], (viewport, destination)
        browser.close()
