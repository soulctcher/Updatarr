"""M2 catalog provenance, safe text and imported-history evidence."""

from __future__ import annotations

from pathlib import Path
import os
import sqlite3
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from updatarr.catalog import (  # noqa: E402
    BlockedFlatpakCatalogAdapter,
    CatalogService,
    SimulatorCatalogAdapter,
    aur_build_preview,
    plain_text,
    simulator_catalog_adapters,
)
from updatarr.advisories import (  # noqa: E402
    AdvisoryService, SimulatorAdvisoryAdapter, _parse_arch_news,
)
from updatarr.history import (  # noqa: E402
    HistoryImportBatch, parse_flatpak_history, parse_pacman_history,
    read_pacman_history_report,
)
from updatarr.storage import StateStore  # noqa: E402


def test_catalog_keeps_same_name_sources_and_scopes_separate() -> None:
    page = CatalogService(simulator_catalog_adapters()).search("kdenlive", limit=20)
    assert len(page.items) == 4
    assert len({item.catalog_id for item in page.items}) == 4
    assert {(item.source_id, item.scope) for item in page.items} == {
        ("native", "system"), ("aur", "user"),
        ("flatpak", "user"), ("flatpak", "system"),
    }
    assert all(item.note and item.note.source_url.startswith("https://") for item in page.items)


def test_catalog_source_filter_and_turned_off_state_are_truthful() -> None:
    service = CatalogService(simulator_catalog_adapters())
    page = service.search(
        "kdenlive", source_id="flatpak", scope="user", limit=20,
        turned_off={("flatpak", "user")},
    )
    assert page.items == ()
    assert page.source_states[0]["state"] == "turned_off"
    with pytest.raises(ValueError, match="available update source"):
        service.search("kdenlive", source_id="firmware")


def test_live_flatpak_catalog_is_not_checked_without_refreshing_metadata() -> None:
    page = CatalogService([BlockedFlatpakCatalogAdapter("user")]).search("kdenlive")
    assert page.items == ()
    assert page.source_states == ({
        "source_id": "flatpak",
        "scope": "user",
        "state": "not_checked",
        "message": "Live Flatpak search is not checked because the installed command may refresh catalog data.",
    },)


def test_catalog_cutoff_is_incomplete_not_a_false_total() -> None:
    adapter = SimulatorCatalogAdapter(
        "aur", "AUR (user-submitted)", "user", "aur",
        tuple((f"match-{index}", f"Match {index}", "1", "matching result", "User-submitted") for index in range(5)),
    )
    page = CatalogService([adapter]).search("match", limit=2)
    assert len(page.items) == 2
    assert page.complete is False
    assert page.source_states[0]["state"] == "incomplete"
    assert "more may exist" in str(page.source_states[0]["message"])


@pytest.mark.parametrize(
    "error, expected_state",
    [(TimeoutError("late"), "source_unavailable"), (ValueError("schema changed"), "error")],
)
def test_catalog_timeout_and_schema_drift_are_not_zero_results(
    error: Exception, expected_state: str
) -> None:
    class FailingAdapter:
        source_id = "aur"
        source_name = "AUR (user-submitted)"
        scope = "user"
        origin = "aur"

        def search(self, query: str, limit: int):  # type: ignore[no-untyped-def]
            raise error

    page = CatalogService([FailingAdapter()]).search("match")
    assert page.items == ()
    assert page.complete is False
    assert page.source_states[0]["state"] == expected_state


def test_untrusted_notes_become_bounded_plain_text() -> None:
    hostile = '<img src=x onerror=alert(1)>Useful <script>alert(2)</script><b>description</b>\x1b'
    cleaned = plain_text(hostile)
    assert cleaned == "Useful description"
    assert "alert" not in cleaned and "onerror" not in cleaned and "\x1b" not in cleaned
    assert plain_text("x" * 5000, limit=40) == "x" * 40


def test_aur_build_preview_is_bounded_inert_and_fixed_source() -> None:
    preview = aur_build_preview("kdenlive-git", simulated=True)
    assert preview["source_url"] == "https://aur.archlinux.org/cgit/aur.git/plain/PKGBUILD?h=kdenlive-git"
    assert preview["comparison_state"] == "no_earlier_copy"
    assert "build()" in str(preview["content"])
    assert len(str(preview["content_hash"])) == 64
    with pytest.raises(ValueError, match="valid AUR package"):
        aur_build_preview("../outside", simulated=True)


def test_advisories_keep_source_url_time_state_and_preview_label() -> None:
    result = AdvisoryService([SimulatorAdvisoryAdapter()]).read()
    item = result["items"][0]
    assert item["source_name"] == "Arch Linux news"
    assert item["source_url"].startswith("https://archlinux.org/")
    assert item["observed_at"]
    assert item["advisory_kind"] == "general_notice"
    assert item["simulated"] is True
    assert len(item["content_hash"]) == 64
    assert item["parse_status"] == "parsed"
    with pytest.raises(ValueError, match="unsafe or incomplete"):
        _parse_arch_news(
            b"<rss><channel><item><title>Unsafe</title><description>x</description><link>javascript:alert(1)</link></item></channel></rss>",
            10,
        )


def test_pacman_history_import_is_exact_idempotent_and_keeps_duplicates(tmp_path: Path) -> None:
    text = "\n".join((
        "[2026-10-18T13:04:22-0400] [ALPM] upgraded firefox (1 -> 2)",
        "[2026-10-18T13:04:22-0400] [ALPM] upgraded firefox (1 -> 2)",
        "[2026-10-18T13:05:00-0400] [ALPM] reinstalled linux (6.17)",
        "[2026-10-18T13:06:00-0400] [PACMAN] Running 'pacman -Syu'",
        "malformed provider text",
    ))
    events = parse_pacman_history(text, source_name="fixture")
    assert len(events) == 3
    assert events[0].dedupe_key != events[1].dedupe_key
    assert events[2].version_before == events[2].version_after == "6.17"
    assert all(event.completeness == "partial" for event in events)
    old = parse_pacman_history("[2012-01-02 03:04] upgraded old-package (1 -> 2)")
    assert old[0].software_id == "old-package"
    rotated_a = parse_pacman_history(text, source_generation="device-1-inode-10")
    rotated_b = parse_pacman_history(text, source_generation="device-1-inode-11")
    assert rotated_a[0].dedupe_key != rotated_b[0].dedupe_key

    store = StateStore(tmp_path / "state.db"); store.initialize()
    assert store.import_history(events) == 3
    assert store.import_history(events) == 0
    page = store.external_history_page()
    assert page.total == 3 and all(item["history_kind"] == "imported" for item in page.items)
    assert store.history_summary()["download_bytes"] is None
    with sqlite3.connect(store.path) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("UPDATE external_history_events SET action = 'changed'")

    batch = HistoryImportBatch(
        "batch-test", "native", "system", "incomplete", "available log", "0", "99",
        3, 1, "Older rotated logs may be missing.", "2026-10-25T00:00:00+00:00",
    )
    assert store.record_history_batches((batch,)) == 1
    assert store.record_history_batches((batch,)) == 0
    assert store.history_import_batches()[0]["reason"] == "Older rotated logs may be missing."


def test_pacman_copy_truncate_advances_persisted_source_generation(tmp_path: Path) -> None:
    path = tmp_path / "pacman.log"
    line = "[2026-10-18T13:04:22-0400] [ALPM] upgraded firefox (1 -> 2)\n"
    path.write_text(line)
    first_events, _, first_state = read_pacman_history_report(path)
    inode = first_state.inode

    path.write_text(line)
    os.utime(path, ns=(first_state.mtime_ns + 1_000_000, first_state.mtime_ns + 1_000_000))
    second_events, _, second_state = read_pacman_history_report(path, previous=first_state)
    assert second_state.inode == inode
    assert second_state.generation == first_state.generation + 1
    assert second_events[0].dedupe_key != first_events[0].dedupe_key

    store = StateStore(tmp_path / "state.db"); store.initialize()
    store.save_history_source_state(second_state)
    assert store.history_source_state(str(path)) == second_state


def test_flatpak_history_keeps_scope_branch_and_ignores_download_steps() -> None:
    text = """[
      {"time":"Oct 24 14:19:51","change":"pull","application":"org.example.App","branch":"stable","installation":"user","remote":"flathub"},
      {"time":"Oct 24 14:19:52","change":"deploy update","application":"org.example.App","arch":"x86_64","branch":"stable","installation":"user","remote":"flathub","old-commit":"aaa","new-commit":"bbb"},
      {"time":"Oct 24 14:19:53","change":"uninstall","application":"org.example.Old","branch":"stable","installation":"user","remote":""}
    ]"""
    events = parse_flatpak_history(text, scope="user")
    assert [event.action for event in events] == ["updated", "removed"]
    assert all(event.scope == "user" and event.completeness == "partial" for event in events)
    assert events[0].software_id == "org.example.App/x86_64/stable"
    assert events[0].details["old_commit"] == "aaa"
    assert events[0].details["new_commit"] == "bbb"
    assert events[0].details["remote"] == "flathub"
    with pytest.raises(ValueError, match="different installation scope"):
        parse_flatpak_history(text, scope="system")


def test_target_scale_catalog_filter_is_bounded_and_fast() -> None:
    adapter = simulator_catalog_adapters()[0]
    large = type(adapter)(
        adapter.source_id, adapter.source_name, adapter.scope, adapter.origin,
        tuple((f"package-{index}", f"Package {index}", "1", "Useful software", "Official repository") for index in range(10_000)),
    )
    started = time.perf_counter()
    page = CatalogService([large]).search("package-99", limit=40)
    elapsed = time.perf_counter() - started
    assert len(page.items) == 40
    assert elapsed < 1.0
