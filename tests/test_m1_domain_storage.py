"""M1 domain identity and SQLite state-store evidence."""

from __future__ import annotations

import json
import stat
from pathlib import Path
import sqlite3
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from updatarr.domain import (  # noqa: E402
    DetectedUpdate, InventorySnapshot, PolicyKind, PolicyState, SelectionPolicy,
    SoftwareRecord, SourceResult, SourceState, UpdateRunState,
    can_transition_update_run, stable_software_id, utc_now,
)
from updatarr.storage import StateStore  # noqa: E402
from updatarr.security import SessionStore  # noqa: E402


def _snapshot() -> InventorySnapshot:
    native = SoftwareRecord("native", "system", "same-name", "Same name", "1.0", ownership="native_repository")
    flatpak = SoftwareRecord("flatpak", "user", "same-name/x86_64/stable", "Same name", "2.0", origin="flathub")
    update = DetectedUpdate(native.stable_id, "native", "system", "same-name", "Same name", "1.0", "1.1", restart_needed=True)
    return InventorySnapshot.create(utc_now(), [
        SourceResult("native", "System packages", "system", SourceState.READY_TO_REVIEW, "Recorded.", utc_now(), 2, (native,), (update,)),
        SourceResult("flatpak", "Flatpak (user)", "user", SourceState.NOT_CHECKED, "Inventory only.", utc_now(), 3, (flatpak,), ()),
    ])


def test_identity_includes_source_and_scope() -> None:
    assert stable_software_id("native", "system", "same") != stable_software_id("flatpak", "user", "same")
    assert stable_software_id("flatpak", "user", "same") != stable_software_id("flatpak", "system", "same")
    assert stable_software_id("flatpak", "user", "same", "flathub") != stable_software_id("flatpak", "user", "same", "private")


def test_software_records_link_to_source_documentation() -> None:
    records = (
        SoftwareRecord("native", "system", "firefox", "Firefox", "1", ownership="native_repository"),
        SoftwareRecord("aur", "user", "visual-studio-code-bin", "Visual Studio Code", "1"),
        SoftwareRecord("flatpak", "user", "org.kde.kdenlive/x86_64/stable", "Kdenlive", "1", origin="flathub"),
        SoftwareRecord("firmware", "system", "device", "Device", "1"),
        SoftwareRecord("rustup", "user", "stable-x86_64-unknown-linux-gnu", "Rust", None),
    )
    urls = [record.to_dict()["source_documentation_url"] for record in records]
    assert urls == [
        "https://archlinux.org/packages/?q=firefox",
        "https://aur.archlinux.org/packages/visual-studio-code-bin",
        "https://flathub.org/apps/org.kde.kdenlive",
        "https://fwupd.github.io/libfwupdplugin/",
        "https://rust-lang.github.io/rustup/concepts/toolchains.html",
    ]


def test_future_policy_and_update_run_states_are_typed_and_terminal() -> None:
    policy = SelectionPolicy(
        "policy-1", PolicyKind.SKIP_VERSION, PolicyState.ACTIVE,
        "flatpak", "user", "org.example.App/x86_64/stable", "2.0",
    )
    assert policy.kind is PolicyKind.SKIP_VERSION
    assert can_transition_update_run(UpdateRunState.CREATED, UpdateRunState.RUNNING)
    assert can_transition_update_run(UpdateRunState.RUNNING, UpdateRunState.NEEDS_MANUAL_RECOVERY)
    assert not can_transition_update_run(UpdateRunState.SUCCEEDED, UpdateRunState.RUNNING)


def test_snapshot_is_deterministic_and_round_trips(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.db")
    store.initialize()
    snapshot = _snapshot()
    duplicate = InventorySnapshot.create(snapshot.started_at, list(snapshot.sources))
    assert duplicate.generation == snapshot.generation
    store.save_snapshot(snapshot)
    store.save_snapshot(snapshot)
    loaded = store.latest_snapshot()
    assert loaded is not None
    assert loaded.generation == snapshot.generation
    assert len(loaded.software) == 2
    assert loaded.summary() == {"updates_found": 1, "ready_to_review": 1, "blocked": 0, "restart_needed": 1, "software_recorded": 2}


def test_existing_snapshot_children_cannot_be_rewritten(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.db"); store.initialize()
    original = _snapshot(); store.save_snapshot(original)
    changed_source = SourceResult(
        "native", "Changed", "system", SourceState.ERROR, "Changed.", utc_now(), 1,
        (SoftwareRecord("native", "system", "changed", "Changed", "9"),), (),
    )
    forged = InventorySnapshot(
        original.snapshot_id, original.generation, original.started_at,
        original.completed_at, (changed_source,),
    )
    store.save_snapshot(forged)
    loaded = store.latest_snapshot(); assert loaded is not None
    assert loaded.sources[0].name != "Changed"
    assert {item.software_id for item in loaded.software} == {"same-name", "same-name/x86_64/stable"}


def test_schema_is_idempotent_wal_and_backup_restores(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.db")
    store.initialize(); store.initialize(); store.save_snapshot(_snapshot())
    backup = tmp_path / "backup.db"
    store.backup(backup)
    restored = StateStore(backup)
    assert restored.latest_snapshot() is not None
    with sqlite3.connect(store.path) as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert connection.execute("SELECT COUNT(*) FROM schema_migrations WHERE version = 1").fetchone()[0] == 1
    assert stat.S_IMODE(store.path.stat().st_mode) == 0o600
    assert stat.S_IMODE(backup.stat().st_mode) == 0o600


def test_app_state_and_new_backup_directories_are_private(tmp_path: Path) -> None:
    state_directory = tmp_path / ".state"
    state_directory.mkdir(mode=0o755)
    store = StateStore(state_directory / "state.db"); store.initialize()
    assert stat.S_IMODE(state_directory.stat().st_mode) == 0o700
    backup = tmp_path / "new-backups" / "state.db"
    store.backup(backup)
    assert stat.S_IMODE(backup.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(backup.stat().st_mode) == 0o600


def test_insecure_custom_state_directory_is_rejected(tmp_path: Path) -> None:
    insecure = tmp_path / "shared-state"
    insecure.mkdir(mode=0o755)
    insecure.chmod(0o755)
    with pytest.raises(PermissionError, match="only to its owner"):
        StateStore(insecure / "state.db").initialize()


def test_audit_is_append_only_and_preferences_are_separate(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.db"); store.initialize()
    audit_id = store.record_audit("inventory_check_started", "administrator", {"read_only": True})
    store.set_preference("administrator", "theme", "norse")
    assert store.preference("administrator", "theme") == "norse"
    assert store.audit_page().items[0]["details"] == {"read_only": True}
    with sqlite3.connect(store.path) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("UPDATE audit_events SET kind = 'changed' WHERE audit_id = ?", (audit_id,))
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("DELETE FROM audit_events WHERE audit_id = ?", (audit_id,))


def test_inventory_pagination_and_filtering(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.db"); store.initialize(); store.save_snapshot(_snapshot())
    assert store.inventory_page(limit=1).total == 2
    result = store.inventory_page(query="flatpak")
    assert result.total == 1
    assert result.items[0]["source_id"] == "flatpak"


def test_credentials_and_hashed_sessions_survive_restart_and_revoke(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.db"); store.initialize()
    sessions = SessionStore("first-password", repository=store)
    session = sessions.authenticate("first-password", "local")
    with sqlite3.connect(store.path) as connection:
        verifier = connection.execute("SELECT password_verifier FROM accounts").fetchone()[0]
        session_hash = connection.execute("SELECT session_hash FROM web_sessions").fetchone()[0]
    assert verifier.startswith("$argon2id$")
    assert session.session_id not in session_hash

    restarted = SessionStore("ignored-password", repository=store)
    restored = restarted.get(session.session_id)
    assert restored is not None and restored.csrf_token == session.csrf_token
    restarted.revoke(session.session_id)
    assert SessionStore("ignored-password", repository=store).get(session.session_id) is None
