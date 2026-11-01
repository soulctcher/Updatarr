"""M2 saved-choice and native-group safety evidence."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sqlite3
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from updatarr.domain import (  # noqa: E402
    DetectedUpdate, PolicyKind, PolicyState, SourceState,
    SYSTEM_UPDATE_GROUP_ID, stable_software_id,
)
from updatarr.policy import (  # noqa: E402
    PolicyError, apply_policies, check_update_selection, new_policy,
)
from updatarr.storage import StateStore  # noqa: E402


def _update(source: str, scope: str, software: str, version: str = "2") -> DetectedUpdate:
    return DetectedUpdate(
        stable_software_id(source, scope, software), source, scope, software,
        software, "1", version,
    )


def test_policy_validation_keeps_choices_distinct_and_exact() -> None:
    target = stable_software_id("flatpak", "user", "org.example.App/x86_64/stable")
    skip = new_policy(
        kind=PolicyKind.SKIP_VERSION, source_id="flatpak", scope="user",
        software_id="org.example.App/x86_64/stable", target_stable_id=target, version="2.0",
    )
    assert skip.kind is PolicyKind.SKIP_VERSION
    with pytest.raises(PolicyError, match="exact recorded software"):
        new_policy(
            kind=PolicyKind.PAUSE_SOFTWARE, source_id="flatpak", scope="user",
            software_id="org.example.App/x86_64/stable",
        )
    with pytest.raises(PolicyError, match="exact version"):
        new_policy(
            kind=PolicyKind.SKIP_VERSION, source_id="flatpak", scope="user",
            software_id="org.example.App/x86_64/stable", target_stable_id=target,
        )
    with pytest.raises(PolicyError, match="must be postponed or paused together"):
        new_policy(
            kind=PolicyKind.POSTPONE, source_id="native", scope="system",
            software_id="firefox",
        )
    grouped = new_policy(
        kind=PolicyKind.POSTPONE, source_id="native", scope="system",
        software_id=SYSTEM_UPDATE_GROUP_ID,
    )
    assert grouped.software_id == SYSTEM_UPDATE_GROUP_ID
    with pytest.raises(PolicyError, match="exact recorded software"):
        new_policy(
            kind=PolicyKind.POSTPONE, source_id="flatpak", scope="user",
            software_id=SYSTEM_UPDATE_GROUP_ID,
        )


def test_policy_expiry_must_be_future_and_scope_does_not_leak() -> None:
    expired = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    with pytest.raises(PolicyError, match="future"):
        new_policy(
            kind=PolicyKind.PAUSE_SOFTWARE, source_id="flatpak", scope="user",
            software_id="org.example.App/x86_64/stable",
            target_stable_id=stable_software_id("flatpak", "user", "org.example.App/x86_64/stable"),
            expires_at=expired,
        )
    update = _update("flatpak", "system", "org.example.App/x86_64/stable")
    wrong_scope = new_policy(
        kind=PolicyKind.PAUSE_SOFTWARE, source_id="flatpak", scope="user",
        software_id="org.example.App/x86_64/stable",
        target_stable_id=stable_software_id("flatpak", "user", "org.example.App/x86_64/stable"),
    )
    assert apply_policies([update], [wrong_scope])[0].state is SourceState.READY_TO_REVIEW


def test_policy_precedence_and_changed_version_reappears() -> None:
    update = _update("flatpak", "user", "org.example.App/x86_64/stable", "2.0")
    skip = new_policy(
        kind=PolicyKind.SKIP_VERSION, source_id="flatpak", scope="user",
        software_id=update.software_id, target_stable_id=update.stable_id, version="2.0",
    )
    assert apply_policies([update], [skip])[0].state is SourceState.SKIPPED
    assert apply_policies([replace(update, available_version="2.1")], [skip])[0].state is SourceState.READY_TO_REVIEW
    pause = new_policy(
        kind=PolicyKind.PAUSE_SOFTWARE, source_id="flatpak", scope="user",
        software_id=update.software_id, target_stable_id=update.stable_id,
    )
    assert apply_policies([update], [skip, pause])[0].state is SourceState.PAUSED


def test_policy_exact_identity_does_not_follow_same_ref_to_another_remote() -> None:
    flathub = replace(
        _update("flatpak", "user", "org.example.App/x86_64/stable", "2.0"),
        stable_id=stable_software_id(
            "flatpak", "user", "org.example.App/x86_64/stable", "flathub", "x86_64", "stable"
        ),
    )
    private = replace(
        flathub,
        stable_id=stable_software_id(
            "flatpak", "user", "org.example.App/x86_64/stable", "private", "x86_64", "stable"
        ),
    )
    pause = new_policy(
        kind=PolicyKind.PAUSE_SOFTWARE, source_id="flatpak", scope="user",
        software_id=flathub.software_id, target_stable_id=flathub.stable_id,
    )
    assert apply_policies([flathub], [pause])[0].state is SourceState.PAUSED
    assert apply_policies([private], [pause])[0].state is SourceState.READY_TO_REVIEW


def test_partial_native_selection_is_rejected_but_all_or_none_is_safe() -> None:
    native = [_update("native", "system", "linux"), _update("native", "system", "firefox")]
    flatpak = _update("flatpak", "user", "org.example.App/x86_64/stable")
    blocked = check_update_selection([*native, flatpak], [native[0].stable_id])
    assert not blocked.allowed
    assert "must update together" in blocked.message
    assert check_update_selection([*native, flatpak], [item.stable_id for item in native]).allowed
    assert check_update_selection([*native, flatpak], [flatpak.stable_id]).allowed
    with pytest.raises(PolicyError, match="not in this update check"):
        check_update_selection(native, ["forged"])


@pytest.mark.parametrize("state", [SourceState.POSTPONED, SourceState.PAUSED, SourceState.SKIPPED])
def test_saved_native_choice_blocks_the_system_update_group(state: SourceState) -> None:
    native = [
        replace(_update("native", "system", "linux"), state=state),
        _update("native", "system", "firefox"),
    ]
    flatpak = _update("flatpak", "user", "org.example.App/x86_64/stable")
    blocked = check_update_selection([*native, flatpak], [item.stable_id for item in native])
    assert not blocked.allowed
    assert blocked.blocked_reason == "A saved choice cannot create a partial system update on Arch Linux."
    assert check_update_selection([*native, flatpak], [flatpak.stable_id]).allowed


def test_policy_storage_is_durable_append_only_and_expires(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.db"); store.initialize()
    policy = new_policy(
        kind=PolicyKind.TURN_OFF_SOURCE, source_id="flatpak", scope="system",
    )
    store.create_policy(policy)
    assert store.turned_off_sources() == {("flatpak", "system")}
    assert StateStore(store.path).policies()[0].policy_id == policy.policy_id
    removed = store.remove_policy(policy.policy_id)
    assert removed is not None and removed.state is PolicyState.REMOVED
    assert store.turned_off_sources() == set()
    with sqlite3.connect(store.path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM policy_events").fetchone()[0] == 2
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("DELETE FROM policy_events")


def test_policy_application_time_is_recorded_once_per_snapshot(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.db"); store.initialize()
    policy = store.create_policy(new_policy(
        kind=PolicyKind.PAUSE_SOFTWARE, source_id="flatpak", scope="user",
        software_id="org.example.App",
        target_stable_id=stable_software_id("flatpak", "user", "org.example.App"),
    ))
    store.mark_policies_applied({policy.policy_id}, "snapshot-one")
    store.mark_policies_applied({policy.policy_id}, "snapshot-one")
    loaded = store.policies()[0]
    assert loaded.last_applied_at is not None
    assert loaded.last_applied_snapshot == "snapshot-one"
    with sqlite3.connect(store.path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM policy_events WHERE kind = 'applied'"
        ).fetchone()[0] == 1


def test_schema_migrates_existing_m1_database(tmp_path: Path) -> None:
    path = tmp_path / "state.db"
    store = StateStore(path); store.initialize()
    with sqlite3.connect(path) as connection:
        connection.execute("DELETE FROM schema_migrations WHERE version = 2")
        connection.execute("DROP TABLE policy_events")
        connection.execute("DROP TABLE selection_policies")
        connection.execute("DROP TABLE external_history_events")
    store.initialize()
    with sqlite3.connect(path) as connection:
        versions = {row[0] for row in connection.execute("SELECT version FROM schema_migrations")}
    assert versions == {1, 2, 3, 4, 5, 6}


def test_target_scale_policy_evaluation_is_bounded() -> None:
    updates = [_update("flatpak", "user", f"org.example.App{index}") for index in range(10_000)]
    pause = new_policy(
        kind=PolicyKind.PAUSE_SOFTWARE, source_id="flatpak", scope="user",
        software_id="org.example.App9999", target_stable_id=updates[-1].stable_id,
    )
    started = time.perf_counter()
    result = apply_policies(updates, [pause])
    elapsed = time.perf_counter() - started
    assert result[-1].state is SourceState.PAUSED
    assert elapsed < 1.0
