"""Real-browser M4 safety-readiness and theme evidence."""

from __future__ import annotations

import pytest

from test_m2_browser import _open_update_details, _run_check, _server, _signed_in_page


THEMES = [
    "system", "light", "dark", "amoled", "solarized-light", "solarized-dark",
    "github-light", "github-dark", "norse", "nord", "gruvbox-light", "gruvbox-dark",
    "dracula", "catppuccin-latte", "catppuccin-mocha", "sepia", "midnight", "high-contrast",
]


def _open_visible_help(page) -> list[tuple[str, str]]:
    opened: list[tuple[str, str]] = []
    buttons = page.locator(".help-button")
    for index in range(buttons.count()):
        help_button = buttons.nth(index)
        if not help_button.is_visible():
            continue
        accessible_name = help_button.get_attribute("aria-label")
        assert accessible_name and accessible_name.startswith("Information: ")
        help_button.hover()
        help_id = help_button.get_attribute("aria-describedby")
        assert help_id
        help_content = page.locator(f'[id="{help_id}"]')
        assert help_content.is_visible()
        help_text = help_content.inner_text().strip()
        assert help_text
        opened.append((accessible_name, help_text))
        button_box = help_button.bounding_box()
        help_box = help_content.bounding_box()
        assert button_box is not None and help_box is not None
        assert help_box["x"] > button_box["x"] + button_box["width"]
        assert int(help_content.evaluate("node => getComputedStyle(node).zIndex")) >= 2_147_483_647
        page.mouse.move(
            help_box["x"] + min(10, help_box["width"] / 2),
            help_box["y"] + min(10, help_box["height"] / 2),
            steps=8,
        )
        assert help_content.is_visible()
        page.mouse.move(0, 0)
        help_content.wait_for(state="hidden")
    return opened


@pytest.mark.parametrize("viewport", [
    {"width": 1280, "height": 900}, {"width": 390, "height": 844},
])
def test_safety_readiness_explains_blocks_restart_and_no_mutation(viewport: dict[str, int]) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with _server() as base_url, playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = _signed_in_page(browser, base_url, viewport)
        _run_check(page)
        page.get_by_role("button", name="Updates", exact=True).click()
        _open_update_details(page)
        page.get_by_role("heading", name="Safety Checklist").wait_for()
        help_button = page.get_by_role("button", name="Information: About the Safety Checklist")
        help_button.focus()
        help_id = help_button.get_attribute("aria-describedby")
        assert help_id
        help = page.locator(f'[id="{help_id}"]')
        help_box = help.bounding_box()
        button_box = help_button.bounding_box()
        heading_box = page.get_by_role("heading", name="Safety Checklist").bounding_box()
        assert help_box is not None
        assert button_box is not None and heading_box is not None
        assert 16 <= button_box["width"] <= 19
        assert button_box["y"] < heading_box["y"] + 4
        assert help_box["x"] >= 0 and help_box["x"] + help_box["width"] <= viewport["width"]
        page.keyboard.press("Escape")
        help.wait_for(state="hidden")
        assert page.get_by_text("5 passed", exact=True).is_visible()
        assert page.get_by_text("2 need attention", exact=True).is_visible()
        assert page.get_by_text("2 not supported", exact=True).is_visible()
        assert page.get_by_role("heading", name="Example Firmware Device", exact=True).is_visible()
        firmware = page.locator(".checklist-item", has_text="Example Firmware Device")
        attention = firmware.get_by_role(
            "button",
            name="Needs attention: check software again from Overview for Example Firmware Device",
        )
        attention.click()
        page.get_by_role("heading", name="Software Overview").wait_for()
        page.wait_for_function(
            "() => document.activeElement?.id === 'check-software'"
        )
        page.get_by_role("button", name="Updates", exact=True).click()
        _open_update_details(page)
        page.get_by_role("heading", name="Safety Checklist").wait_for()
        firmware = page.locator(".checklist-item", has_text="Example Firmware Device")
        firmware.get_by_text("View details", exact=True).click()
        assert page.get_by_text("External power is not connected", exact=False).is_visible()
        assert page.get_by_text("Restart the computer to use the new version", exact=False).count() >= 1
        assert page.locator(".safety-readiness").get_by_text(
            "folder reserved for system packages", exact=False
        ).is_visible()
        assert page.get_by_text("does not know how uv was installed", exact=False).is_visible()
        npm = page.locator(".checklist-item", has_text="Global npm Packages")
        npm.get_by_role(
            "button",
            name="Needs attention: review system package updates for Global npm Packages",
        ).click()
        page.wait_for_function(
            "() => document.activeElement?.dataset.updateSource === 'native'"
        )
        assert page.locator(".checklist-ready button.checklist-status").count() == 0
        assert page.locator(".checklist-not_checked button.checklist-status").count() == 0
        assert page.locator(".checklist-not_supported button.checklist-status").count() == 0
        maintenance = page.locator(".checklist-item", has_text="Old Package Downloads")
        maintenance.get_by_text("View details", exact=True).click()
        assert maintenance.get_by_text("Nothing has been removed", exact=False).is_visible()
        assert maintenance.get_by_text("linux 6.16 package", exact=False).is_visible()
        assert maintenance.get_by_text("Keep the two newest versions", exact=False).is_visible()
        assert page.get_by_role("button", name="Clean", exact=False).count() == 0
        safety_box = page.locator(".safety-readiness").bounding_box()
        updates_box = page.locator(".detected-updates").bounding_box()
        assert safety_box is not None and updates_box is not None
        assert updates_box["y"] - (safety_box["y"] + safety_box["height"]) >= 17
        preservation = page.evaluate("() => fetch('./api/v1/safety-readiness').then(response => response.json()).then(body => body.preservation)")
        assert preservation == {"package_ownership_changed": False, "flatpak_origins_changed": False,
                                "host_changes_performed": False}
        width = page.evaluate("() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]")
        assert width[0] <= width[1]
        browser.close()


@pytest.mark.parametrize("viewport", [
    {"width": 1280, "height": 900}, {"width": 390, "height": 844},
])
def test_ready_updates_is_a_short_guided_workflow(viewport: dict[str, int]) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with _server() as base_url, playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = _signed_in_page(browser, base_url, viewport)
        _run_check(page)
        page.get_by_role("button", name="Updates", exact=True).click()

        page.get_by_role("heading", name="Ready Updates", exact=True).wait_for()
        assert page.get_by_role("button", name="Check Again", exact=True).is_visible()
        assert page.get_by_role("button", name="Update Ready Software", exact=True).is_visible()
        assert page.get_by_text("4 Ready", exact=True).is_visible()
        assert page.locator(".ready-update-list li", has_text="Example Firmware Device").get_by_text(
            "Needs Attention", exact=True
        ).is_visible()
        assert page.get_by_text("Safety Checklist", exact=True).is_hidden()
        assert page.get_by_text("Review code", exact=True).count() == 0

        page.get_by_role("button", name="Update Ready Software", exact=True).click()
        page.get_by_role("heading", name="Ready for Your Review", exact=True).wait_for()
        assert page.locator(".plan-review", has_text="Example Firmware Device").count() == 0

        details = page.get_by_text("Safety and technical details", exact=True)
        details.click()
        assert page.get_by_role("heading", name="Safety Checklist", exact=True).is_visible()
        browser.close()


def test_notification_link_lands_on_ready_updates_after_sign_in() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with _server() as base_url, playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(base_url + "/?view=updates")
        page.get_by_label("Password").fill("test-only-password")
        page.get_by_role("button", name="Sign in", exact=True).click()
        page.get_by_role("heading", name="Ready Updates", exact=True).wait_for()
        assert page.get_by_role("button", name="Updates", exact=True).get_attribute("aria-current") == "page"
        browser.close()


def test_primary_action_never_selects_part_of_the_system_package_group() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with _server() as base_url, playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = _signed_in_page(browser, base_url, {"width": 1280, "height": 900})
        _run_check(page)
        page.get_by_role("button", name="Updates", exact=True).click()
        page.get_by_label("Choice for Firefox", exact=True).select_option("skip_version")

        system_issue = page.locator(".ready-issues", has_text="System Packages")
        system_issue.wait_for()
        native_rows = page.locator(
            ".ready-update-list li", has_text="System packages"
        )
        assert native_rows.count() == 2
        assert native_rows.evaluate_all(
            "rows => rows.every(row => row.textContent.includes('Needs Attention') || row.textContent.includes('Remove Saved Choice'))"
        )

        page.get_by_role("button", name="Update Ready Software", exact=True).click()
        page.get_by_role("heading", name="Ready for Your Review", exact=True).wait_for()
        assert page.get_by_text("Update the complete system package group", exact=False).count() == 0
        browser.close()


def test_expired_plan_has_space_before_safety_details() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with _server() as base_url, playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = _signed_in_page(browser, base_url, {"width": 1280, "height": 900})
        _run_check(page)
        page.route(
            "**/api/v1/plans/latest",
            lambda route: route.fulfill(json={
                "plan": {
                    "plan_id": "plan-expired-example",
                    "digest": "a" * 64,
                    "state": "expired",
                    "created_at": "2026-11-03T12:00:00+00:00",
                    "expires_at": "2026-11-03T12:15:00+00:00",
                    "steps": [],
                    "warnings": [],
                    "blockers": [],
                    "unknowns": [],
                    "requires_administrator": False,
                },
                "run": None,
            }),
        )
        page.get_by_role("button", name="Updates", exact=True).click()
        page.get_by_role("heading", name="Plan Expired", exact=True).wait_for()
        plan_box = page.locator(".plan-review").bounding_box()
        details_box = page.locator(".workflow-details").bounding_box()
        assert plan_box is not None and details_box is not None
        assert details_box["y"] - (plan_box["y"] + plan_box["height"]) >= 18
        browser.close()


def test_live_inventory_safety_row_exposes_recorded_source_details() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with _server() as base_url, playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = _signed_in_page(browser, base_url, {"width": 1280, "height": 800})
        page.route(
            "**/api/v1/safety-readiness",
            lambda route: route.fulfill(
                json={
                    "mode": "Read-only",
                    "items": [{
                        "capability_id": "developer-tools",
                        "category": "Developer tools",
                        "name": "Developer tools",
                        "state": "blocked",
                        "summary": "Global npm packages need attention.",
                        "next_step": "No action is available in Updatarr for this source.",
                        "restart_action": "none",
                        "checks": [],
                        "simulated": False,
                        "details": {"observed_sources": [{
                            "source_id": "npm",
                            "name": "Global npm packages",
                            "scope": "system",
                            "state": "blocked",
                            "state_label": "Blocked",
                            "message": "This system folder must remain under system package management.",
                            "software_count": 8,
                            "update_count": 0,
                        }]},
                    }],
                    "preservation": {
                        "package_ownership_changed": False,
                        "flatpak_origins_changed": False,
                        "host_changes_performed": False,
                    },
                }
            ),
        )
        page.get_by_role("button", name="Updates", exact=True).click()
        _open_update_details(page)
        developer_tools = page.locator(".checklist-item", has_text="Developer Tools")
        developer_tools.get_by_text("View details", exact=True).click()
        assert developer_tools.get_by_text("Global npm packages", exact=True).is_visible()
        assert developer_tools.get_by_text("This system folder must remain", exact=False).is_visible()
        assert developer_tools.get_by_text("No action is available in Updatarr", exact=False).is_visible()
        browser.close()


def test_safety_readiness_uses_every_theme_profile() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with _server() as base_url, playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = _signed_in_page(browser, base_url, {"width": 1280, "height": 900})
        page.get_by_role("button", name="Updates", exact=True).click()
        _open_update_details(page)
        page.get_by_role("heading", name="Safety Checklist").wait_for()
        for theme in THEMES:
            page.evaluate("theme => theme === 'system' ? delete document.documentElement.dataset.theme : document.documentElement.dataset.theme = theme", theme)
            assert page.get_by_role("heading", name="Safety Checklist").is_visible()
            assert page.locator(".safety-checklist > .checklist-item").count() == 10
            colors = page.locator(".checklist-item").first.evaluate(
                "node => ({background: getComputedStyle(node).backgroundColor, color: getComputedStyle(node).color})"
            )
            assert colors["background"] != colors["color"]
            help_contrast = page.locator(".help-button").first.evaluate("""node => {
                const channel = value => {
                    value /= 255;
                    return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
                };
                const luminance = value => {
                    const rgb = value.match(/[\\d.]+/g).slice(0, 3).map(Number);
                    return 0.2126 * channel(rgb[0]) + 0.7152 * channel(rgb[1]) + 0.0722 * channel(rgb[2]);
                };
                const style = getComputedStyle(node);
                const light = Math.max(luminance(style.color), luminance(style.backgroundColor));
                const dark = Math.min(luminance(style.color), luminance(style.backgroundColor));
                return (light + 0.05) / (dark + 0.05);
            }""")
            assert help_contrast >= 4.5, f"{theme} information icon contrast was {help_contrast:.2f}:1"
        browser.close()


def test_rail_shows_faint_version_and_build_below_preview_box() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with _server() as base_url, playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = _signed_in_page(browser, base_url, {"width": 1280, "height": 900})
        safe_box = page.locator(".safe-mode").bounding_box()
        stamp = page.get_by_text("Version 0.6.1 · Build M7.1", exact=True)
        stamp_box = stamp.bounding_box()
        assert safe_box is not None and stamp_box is not None
        assert stamp_box["y"] >= safe_box["y"] + safe_box["height"]
        style = stamp.evaluate(
            "node => ({color: getComputedStyle(node).color, fontSize: getComputedStyle(node).fontSize})"
        )
        assert style["color"].startswith("rgba(")
        assert float(style["fontSize"].removesuffix("px")) <= 10
        for theme in THEMES:
            page.evaluate(
                "theme => theme === 'system' ? delete document.documentElement.dataset.theme : document.documentElement.dataset.theme = theme",
                theme,
            )
            contrast = stamp.evaluate("""node => {
                const channels = value => value.match(/[\\d.]+/g).map(Number);
                const foreground = channels(getComputedStyle(node).color);
                const background = channels(getComputedStyle(node.closest('.rail')).backgroundColor);
                const alpha = foreground[3] ?? 1;
                const composite = foreground.slice(0, 3).map(
                    (channel, index) => channel * alpha + background[index] * (1 - alpha)
                );
                const linear = value => {
                    value /= 255;
                    return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
                };
                const luminance = values =>
                    0.2126 * linear(values[0]) +
                    0.7152 * linear(values[1]) +
                    0.0722 * linear(values[2]);
                const first = luminance(composite);
                const second = luminance(background);
                return (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05);
            }""")
            assert contrast >= 4.5, f"{theme} build stamp contrast was {contrast:.2f}:1"
        browser.close()


def test_settings_ends_with_version_contact_and_license_information() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with _server() as base_url, playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = _signed_in_page(browser, base_url, {"width": 1280, "height": 900})
        page.get_by_role("button", name="Settings", exact=True).click()
        about = page.locator(".about-settings")
        assert about.get_by_role("heading", name="About Updatarr", exact=True).is_visible()
        assert about.get_by_text("Version 0.6.1 · Build M7.1", exact=True).is_visible()
        assert about.get_by_text("© 2026 ✦ ERIK WINBLAD ✦", exact=True).is_visible()
        contact = about.get_by_role("link", name="soulctcher@soulctcher.net", exact=True)
        assert contact.get_attribute("href") == "mailto:soulctcher@soulctcher.net"
        license_link = about.get_by_role("link", name="AGPL-3.0-or-later", exact=True)
        assert license_link.get_attribute("href") == "https://www.gnu.org/licenses/agpl-3.0.html"
        assert about.evaluate("node => node === node.parentElement.lastElementChild") is True
        browser.close()


def test_titles_use_title_case_and_preserve_product_casing() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with _server() as base_url, playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = _signed_in_page(browser, base_url, {"width": 1280, "height": 900})
        assert page.get_by_role("heading", name="Software Overview").is_visible()
        _run_check(page)
        assert page.get_by_role(
            "heading", name="Example Notice Requiring Review", exact=True
        ).is_visible()
        page.get_by_role("button", name="Updates", exact=True).click()
        _open_update_details(page)
        page.get_by_role("heading", name="Safety Checklist").wait_for()
        for heading in (
            "Safety Checklist",
            "Example Firmware Device",
            "Global npm Packages",
            "Node.js from fnm",
            "uv Tools",
            "Detected Updates",
        ):
            assert page.get_by_role("heading", name=heading, exact=True).is_visible()
        assert page.get_by_role("columnheader", name="Update Source").is_visible()
        assert page.get_by_role("columnheader", name="Saved Choice").is_visible()
        page.get_by_role("button", name="Settings", exact=True).click()
        theme = page.locator("#theme")
        assert theme.locator("option", has_text="AMOLED").count() == 1
        assert theme.locator("option", has_text="GitHub Light").count() == 1
        assert theme.locator("option", has_text="High Contrast").count() == 1
        assert page.get_by_text("Ultraviolet stays recognizable").count() == 0
        browser.close()


def test_help_is_available_on_hover_and_focus_on_every_page() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with _server() as base_url, playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        sign_in = browser.new_page(viewport={"width": 1280, "height": 900})
        sign_in.goto(base_url)
        opened_help = dict(_open_visible_help(sign_in))
        sign_in.close()

        page = _signed_in_page(browser, base_url, {"width": 1280, "height": 900})
        _run_check(page)
        page.get_by_role("button", name="Overview", exact=True).click()
        opened_help.update(_open_visible_help(page))

        page.get_by_role("button", name="Software", exact=True).click()
        opened_help.update(_open_visible_help(page))
        page.get_by_role("button", name="Find new software").click()
        opened_help.update(_open_visible_help(page))
        page.get_by_role("button", name="Search sources").click()
        page.get_by_text("Kdenlive development build", exact=True).wait_for()
        page.get_by_role("button", name="Preview build file").click()
        page.get_by_role("heading", name="kdenlive-git").wait_for()
        opened_help.update(_open_visible_help(page))

        page.get_by_role("button", name="Updates", exact=True).click()
        _open_update_details(page)
        opened_help.update(_open_visible_help(page))
        page.get_by_role("checkbox", name="Include Visual Studio Code in safety check").check()
        page.get_by_role("button", name="Check whether selection is safe").click()
        page.get_by_role("button", name="Prepare update plan").click()
        page.get_by_role("heading", name="Ready for Your Review", exact=True).wait_for()
        opened_help.update(_open_visible_help(page))

        page.get_by_role("button", name="History", exact=True).click()
        opened_help.update(_open_visible_help(page))
        page.get_by_role("button", name="Import earlier activity").click()
        page.get_by_text("Earlier History Limits", exact=True).wait_for()
        opened_help.update(_open_visible_help(page))

        page.get_by_role("button", name="Settings", exact=True).click()
        opened_help.update(_open_visible_help(page))
        assert len(opened_help) == 20
        for expected_name in (
            "Information: About Sign In",
            "Information: About Search Results",
            "Information: About This Preview",
            "Information: About This Update Plan",
            "Information: About Earlier History Limits",
        ):
            assert expected_name in opened_help

        for view in ("Overview", "Software", "Updates", "History", "Settings"):
            page.get_by_role("button", name=view, exact=True).click()
        page.get_by_role("button", name="Updates", exact=True).click()
        page_help_button = page.get_by_role("button", name="Information: How Ready Updates Work")
        page_help_button.hover()
        page_help_id = page_help_button.get_attribute("aria-describedby")
        assert page_help_id
        page_help = page.locator(f'[id="{page_help_id}"]')
        assert page_help.is_visible()
        assert page_help.get_by_text("checks completed so far", exact=False).is_visible()
        assert page_help.bounding_box()["width"] <= 380
        button_box = page_help_button.bounding_box()
        panel_box = page_help.bounding_box()
        assert button_box is not None and panel_box is not None
        panel_size = page_help.evaluate(
            "node => ({scrollHeight: node.scrollHeight, clientHeight: node.clientHeight})"
        )
        assert panel_size["scrollHeight"] <= panel_size["clientHeight"]
        start_x = button_box["x"] + button_box["width"] / 2
        start_y = button_box["y"] + button_box["height"] / 2
        target_x = panel_box["x"] + 20
        target_y = panel_box["y"] + 20
        for step in range(1, 13):
            fraction = step / 12
            page.mouse.move(
                start_x + (target_x - start_x) * fraction,
                start_y + (target_y - start_y) * fraction,
            )
            page.wait_for_timeout(50)
            assert page_help.is_visible(), f"Help closed during pointer step {step}"
            current_box = page_help.bounding_box()
            assert current_box is not None
            assert abs(current_box["x"] - panel_box["x"]) < 0.5
            assert abs(current_box["y"] - panel_box["y"]) < 0.5
        page.mouse.move(0, 0)
        page_help.wait_for(state="hidden")
        _open_update_details(page)
        checklist_button = page.get_by_role("button", name="Information: About the Safety Checklist")
        checklist_button.hover()
        checklist_button.focus()
        checklist_help_id = checklist_button.get_attribute("aria-describedby")
        assert checklist_help_id
        checklist_help = page.locator(f'[id="{checklist_help_id}"]')
        assert checklist_help.is_visible()
        page.keyboard.press("Escape")
        page.wait_for_timeout(250)
        checklist_help.wait_for(state="hidden")

        page.evaluate("document.body.style.zoom = '2'")
        page_help_button.scroll_into_view_if_needed()
        page_help_button.hover()
        zoomed_box = page_help.bounding_box()
        assert zoomed_box is not None
        viewport = page.viewport_size
        assert viewport is not None
        assert zoomed_box["x"] >= 0
        assert zoomed_box["y"] >= 0
        assert zoomed_box["x"] + zoomed_box["width"] <= viewport["width"]
        assert zoomed_box["y"] + zoomed_box["height"] <= viewport["height"]
        page.evaluate("document.body.style.zoom = ''")
        browser.close()


def test_every_rendered_page_and_safety_detail_uses_plain_language() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with _server() as base_url, playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(base_url)
        sign_in_help = _open_visible_help(page)
        collected: list[str] = [text.lower() for name, text in sign_in_help]
        collected.extend(name.lower() for name, text in sign_in_help)
        page.close()
        page = _signed_in_page(browser, base_url, {"width": 1280, "height": 900})
        _run_check(page)
        page.get_by_role("button", name="Overview", exact=True).click()
        collected.append(page.locator("body").text_content().lower())
        collected.extend(value.lower() for pair in _open_visible_help(page) for value in pair)
        page.get_by_role("button", name="Software", exact=True).click()
        page.get_by_role("button", name="Find new software").click()
        collected.extend(value.lower() for pair in _open_visible_help(page) for value in pair)
        page.get_by_role("button", name="Search sources").click()
        page.get_by_text("Kdenlive development build", exact=True).wait_for()
        page.get_by_role("button", name="Preview build file").click()
        page.get_by_role("heading", name="kdenlive-git").wait_for()
        collected.extend(value.lower() for pair in _open_visible_help(page) for value in pair)
        collected.append(page.locator("body").text_content().lower())
        page.get_by_role("button", name="Updates", exact=True).click()
        _open_update_details(page)
        page.get_by_role("heading", name="Safety Checklist").wait_for()
        page.locator("details").evaluate_all("items => items.forEach(item => item.open = true)")
        page.get_by_role("checkbox", name="Include Visual Studio Code in safety check").check()
        page.get_by_role("button", name="Check whether selection is safe").click()
        page.get_by_role("button", name="Prepare update plan").click()
        page.get_by_role("heading", name="Ready for Your Review", exact=True).wait_for()
        collected.extend(value.lower() for pair in _open_visible_help(page) for value in pair)
        collected.append(page.locator("body").text_content().lower())
        page.get_by_role("button", name="History", exact=True).click()
        page.get_by_role("button", name="Import earlier activity").click()
        page.get_by_text("Updated firefox", exact=True).wait_for()
        collected.extend(value.lower() for pair in _open_visible_help(page) for value in pair)
        collected.append(page.locator("body").text_content().lower())
        page.get_by_role("button", name="Settings", exact=True).click()
        collected.extend(value.lower() for pair in _open_visible_help(page) for value in pair)
        collected.append(page.locator("body").text_content().lower())
        server_errors = page.evaluate("""async () => {
            const responses = await Promise.all([
                fetch('./api/v1/catalog?limit=101'),
                fetch('./api/v1/history?limit=201'),
            ]);
            return Promise.all(responses.map(async response => (await response.json()).detail));
        }""")
        assert server_errors == [
            "Choose between 1 and 100 search results.",
            "The history page request is not valid.",
        ]
        collected.extend(message.lower() for message in server_errors)
        interface_copy = " ".join(collected)
        for unclear_term in (
            "fingerprint", "preflight", "artifact", "atomic", "mutation safety",
            "retention", "candidate", "provenance", "executor review", "early boot image",
            "package hooks", "symbolic link", "staged file", "system-owned location",
            "install method", "cleanup trial", "build isolation", "service-secret",
            "system prefix", "remote versions", "ordinary software inventory",
        ):
            assert unclear_term not in interface_copy
        browser.close()
