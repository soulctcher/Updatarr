"""Real-browser M3 plan review and local-confirmation boundary evidence."""

from __future__ import annotations

import pytest

from test_m2_browser import _open_update_details, _run_check, _server, _signed_in_page


@pytest.mark.parametrize("viewport", [
    {"width": 1280, "height": 900}, {"width": 390, "height": 844},
])
def test_exact_plan_can_be_reviewed_but_browser_cannot_confirm_locally(viewport: dict[str, int]) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with _server() as base_url, playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = _signed_in_page(browser, base_url, viewport)
        _run_check(page)
        page.get_by_role("button", name="Updates", exact=True).click()
        _open_update_details(page)
        page.get_by_role("checkbox", name="Include Linux in safety check").check()
        page.get_by_role("checkbox", name="Include Firefox in safety check").check()
        page.get_by_role("button", name="Check whether selection is safe").click()
        page.get_by_text("Selection can be planned", exact=True).wait_for()
        page.get_by_role("button", name="Prepare update plan").click()
        page.get_by_role("heading", name="Ready for your review").wait_for()
        assert page.get_by_text("native-full-upgrade", exact=False).count() == 0
        assert page.get_by_text("Update the complete system package group", exact=False).is_visible()
        assert page.get_by_text("Review code", exact=True).is_visible()
        page.get_by_role("button", name="Approve exact plan").click()
        page.get_by_role("heading", name="Waiting for confirmation on this computer").wait_for()
        assert page.get_by_text("The browser cannot replace", exact=False).is_visible()
        assert page.get_by_role("button", name="Confirm", exact=False).count() == 0
        dimensions = page.evaluate("() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth})")
        assert dimensions["scroll"] <= dimensions["client"]
        browser.close()


def test_simulated_aur_plan_reaches_review_without_claiming_a_live_build() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with _server() as base_url, playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = _signed_in_page(browser, base_url, {"width": 1280, "height": 900})
        _run_check(page)
        page.get_by_role("button", name="Updates", exact=True).click()
        _open_update_details(page)
        page.get_by_role("checkbox", name="Include Visual Studio Code in safety check").check()
        page.get_by_role("button", name="Check whether selection is safe").click()
        page.get_by_role("button", name="Prepare update plan").click()
        page.get_by_role("heading", name="Ready for Your Review", exact=True).wait_for()
        assert page.get_by_text("Review and build Visual Studio Code", exact=False).is_visible()
        assert page.get_by_role("button", name="Approve exact plan").is_visible()
        assert page.get_by_text("Safe Preview Build", exact=True).is_visible()
        browser.close()
