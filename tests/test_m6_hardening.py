"""M6 recovery, lock-owner and hostile-metadata hardening evidence."""

from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import sys
import tarfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from updatarr.app import AppConfig, create_app  # noqa: E402
from updatarr.catalog import plain_text, remove_format_controls  # noqa: E402
from updatarr.domain import (  # noqa: E402
    DetectedUpdate, InventorySnapshot, SoftwareRecord, SourceResult, SourceState,
    UpdateRun, UpdateRunState, stable_software_id, utc_now,
)
from updatarr.execution import (  # noqa: E402
    HostLockProbe, PackageManagerLockState, ProviderResultChecker,
)
from updatarr.planning import Planner  # noqa: E402
from updatarr.providers.adapters import AurUpdatesAdapter  # noqa: E402
from updatarr.providers.parsers import MAX_FIELD_LENGTH, clean  # noqa: E402
from updatarr.providers.probes import FixtureProbeClient  # noqa: E402
from updatarr.storage import StateStore  # noqa: E402


def _snapshot() -> InventorySnapshot:
    update = DetectedUpdate(
        stable_software_id("flatpak", "user", "org.example.App"),
        "flatpak", "user", "org.example.App", "Example", "1", "2",
    )
    return InventorySnapshot.create(utc_now(), [
        SourceResult(
            "flatpak", "Flatpak", "user", SourceState.READY_TO_REVIEW,
            "Ready", utc_now(), 1, (), (update,),
        ),
    ])


def _interrupted_store(path: Path, run_id: str = "interrupted") -> tuple[StateStore, str]:
    store = StateStore(path)
    store.initialize()
    snapshot = _snapshot()
    store.save_snapshot(snapshot)
    plan = Planner().prepare(snapshot, snapshot.updates, [snapshot.updates[0].stable_id], [])
    store.save_plan(plan)
    store.save_run(UpdateRun(
        run_id, plan.plan_id, plan.digest, UpdateRunState.RUNNING, 75,
        "Checking the result.", utc_now(),
    ), [{"state": "checking_result", "safe_to_cancel": False}])
    return store, plan.plan_id


def test_restart_marks_success_only_after_positive_result_evidence(tmp_path: Path) -> None:
    store, plan_id = _interrupted_store(tmp_path / "state.db")
    checked: list[str] = []

    assert store.recover_unfinished_runs(
        lambda plan: checked.append(plan.plan_id) is None or True
    ) == 1
    recovered = store.run_for_plan(plan_id)
    assert recovered is not None and recovered.state is UpdateRunState.SUCCEEDED
    assert checked == [plan_id]
    assert "verified" in recovered.message.lower()
    assert store.recover_unfinished_runs(lambda _plan: True) == 0


def test_restart_result_check_runs_without_holding_database_write_lock(tmp_path: Path) -> None:
    store, plan_id = _interrupted_store(tmp_path / "state.db")

    def verify(_plan):  # type: ignore[no-untyped-def]
        store.record_audit("recovery_check", "test", {"read_only": True})
        return True

    assert store.recover_unfinished_runs(verify) == 1
    assert store.run_for_plan(plan_id).state is UpdateRunState.SUCCEEDED  # type: ignore[union-attr]
    assert store.audit_page().items[0]["kind"] == "recovery_check"


@pytest.mark.parametrize("result", [False, None])
def test_restart_keeps_unverified_or_mismatched_result_out_of_success(
    tmp_path: Path, result: bool | None,
) -> None:
    store, plan_id = _interrupted_store(tmp_path / "state.db")
    assert store.recover_unfinished_runs(lambda _plan: result) == 1
    recovered = store.run_for_plan(plan_id)
    assert recovered is not None
    assert recovered.state is UpdateRunState.NEEDS_MANUAL_RECOVERY
    assert "manual recovery" in recovered.message.lower()


def test_restart_result_check_failure_is_fail_closed(tmp_path: Path) -> None:
    store, plan_id = _interrupted_store(tmp_path / "state.db")

    def unavailable(_plan):  # type: ignore[no-untyped-def]
        raise OSError("provider unavailable")

    assert store.recover_unfinished_runs(unavailable) == 1
    recovered = store.run_for_plan(plan_id)
    assert recovered is not None and recovered.state is UpdateRunState.NEEDS_MANUAL_RECOVERY


def test_database_interruption_rolls_back_the_whole_change(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.db")
    store.initialize()
    with pytest.raises(RuntimeError, match="simulated interruption"):
        with store.transaction() as connection:
            connection.execute(
                "INSERT INTO preferences VALUES (?, ?, ?, ?)",
                ("administrator", "interrupted", '"unsafe"', utc_now()),
            )
            raise RuntimeError("simulated interruption")
    with sqlite3.connect(store.path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM preferences WHERE preference_key = 'interrupted'"
        ).fetchone()[0] == 0


def _fake_lock_owner(root: Path, lock: Path, process_id: int) -> None:
    descriptors = root / str(process_id) / "fd"
    descriptors.mkdir(parents=True)
    os.link(lock, descriptors / "7")


def test_native_lock_distinguishes_alternative_holder_from_available(tmp_path: Path) -> None:
    process_root = tmp_path / "proc"
    process_root.mkdir()
    lock = tmp_path / "db.lck"
    probe = HostLockProbe(
        lock_path=lock, process_root=process_root, current_process_id=99,
    )
    assert probe.package_manager_lock().state is PackageManagerLockState.AVAILABLE

    lock.touch()
    _fake_lock_owner(process_root, lock, 4242)
    observation = probe.package_manager_lock()
    assert observation.state is PackageManagerLockState.HELD_BY_ANOTHER_PROCESS
    assert observation.owner_process_ids == (4242,)
    assert observation.blocks_updates and probe.package_manager_locked()
    assert lock.exists(), "The observation must never remove the package-manager lock."


def test_native_lock_without_visible_owner_still_blocks(tmp_path: Path) -> None:
    process_root = tmp_path / "proc"
    process_root.mkdir()
    lock = tmp_path / "db.lck"
    lock.touch()
    observation = HostLockProbe(lock_path=lock, process_root=process_root).package_manager_lock()
    assert observation.state is PackageManagerLockState.OWNER_NOT_FOUND
    assert observation.blocks_updates


def test_native_lock_records_current_process_without_treating_it_as_free(tmp_path: Path) -> None:
    process_root = tmp_path / "proc"
    process_root.mkdir()
    lock = tmp_path / "db.lck"
    lock.touch()
    _fake_lock_owner(process_root, lock, 99)
    observation = HostLockProbe(
        lock_path=lock, process_root=process_root, current_process_id=99,
    ).package_manager_lock()
    assert observation.state is PackageManagerLockState.HELD_BY_THIS_PROCESS
    assert observation.blocks_updates


def test_hostile_unicode_formatting_cannot_spoof_displayed_metadata() -> None:
    hostile = "trusted\u202eexe.example\u202c\u200b"
    cleaned = clean(hostile)
    assert cleaned == "trustedexe.example"
    assert all(not (0x202A <= ord(character) <= 0x202E) for character in cleaned)
    assert len(clean("x" * (MAX_FIELD_LENGTH * 2))) == MAX_FIELD_LENGTH
    assert plain_text("Safe\u202eevil.example\u200b") == "Safeevil.example"
    assert remove_format_controls("pkgbuild\u2066spoof\u2069") == "pkgbuildspoof"


def test_large_inventory_is_paged_and_search_wildcards_are_literal(tmp_path: Path) -> None:
    records = tuple(
        SoftwareRecord(
            "native", "system", f"package-{index:04d}", f"Package {index:04d}",
            "1", ownership="native_repository",
        )
        for index in range(1_001)
    ) + (SoftwareRecord(
        "native", "system", "literal%name", "Literal % Name", "1",
        ownership="native_repository",
    ),)
    snapshot = InventorySnapshot.create(utc_now(), [SourceResult(
        "native", "System packages", "system", SourceState.UP_TO_DATE,
        "Current", utc_now(), 1, records, (),
    )])
    store = StateStore(tmp_path / "state.db")
    store.initialize()
    store.save_snapshot(snapshot)
    first = store.inventory_page(limit=100, offset=0)
    last = store.inventory_page(limit=100, offset=1_000)
    literal = store.inventory_page(limit=100, query="%")
    assert first.total == 1_002 and len(first.items) == 100
    assert last.total == 1_002 and len(last.items) == 2
    assert literal.total == 1 and literal.items[0]["software_id"] == "literal%name"


def test_unavailable_aur_source_is_not_reported_up_to_date() -> None:
    result = AurUpdatesAdapter(FixtureProbeClient({
        "aur-updates": {"state": "timed_out", "stdout": "", "exit_code": None},
        "yay-version": {"stdout": "yay v13"},
    })).check()
    assert result.state is SourceState.ERROR
    assert result.updates == ()
    assert result.state is not SourceState.UP_TO_DATE


def test_renamed_packages_remain_distinct_without_source_evidence() -> None:
    old = SoftwareRecord("native", "system", "old-name", "Old Name", "1")
    new = SoftwareRecord("native", "system", "new-name", "New Name", "1")
    assert old.stable_id != new.stable_id


def test_m6_schema_and_paging_indexes_are_present(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.db")
    store.initialize()
    with sqlite3.connect(store.path) as connection:
        assert connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] == 6
        indexes = {
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            )
        }
    assert {"software_records_page", "software_records_identity_search"} <= indexes


def test_schema_migration_failure_rolls_back_every_new_object(tmp_path: Path) -> None:
    path = tmp_path / "state.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        # This name collides with the late schema-6 index and forces a late failure.
        connection.execute("CREATE TABLE software_records_page(value TEXT)")
    with pytest.raises(sqlite3.OperationalError):
        StateStore(path).initialize()
    with sqlite3.connect(path) as connection:
        objects = {
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        versions = connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
    assert objects == {"schema_migrations", "software_records_page"}
    assert versions == 0


def test_database_from_newer_schema_is_rejected_without_changes(tmp_path: Path) -> None:
    path = tmp_path / "state.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        connection.execute("INSERT INTO schema_migrations VALUES (999, 'future')")
    with pytest.raises(RuntimeError, match="newer Updatarr version"):
        StateStore(path).initialize()
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT version FROM schema_migrations").fetchone()[0] == 999
        assert connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE name = 'inventory_snapshots'"
        ).fetchone()[0] == 0


class _RecoveryAdapter:
    source_id = "flatpak"
    scope = "user"

    def __init__(self, installed_version: str | None, state: SourceState = SourceState.NOT_CHECKED) -> None:
        self.installed_version = installed_version
        self.state = state

    @property
    def name(self) -> str:
        return "Flatpak"

    def check(self) -> SourceResult:
        software = () if self.installed_version is None else (SoftwareRecord(
            "flatpak", "user", "org.example.App", "Example",
            self.installed_version, ownership="flatpak",
        ),)
        return SourceResult(
            self.source_id, self.name, self.scope, self.state, "Fresh result",
            utc_now(), 1, software, (),
        )


def test_production_result_checker_matches_mismatch_and_unavailable() -> None:
    snapshot = _snapshot()
    plan = Planner().prepare(snapshot, snapshot.updates, [snapshot.updates[0].stable_id], [])
    assert ProviderResultChecker([_RecoveryAdapter("2")]).matches(plan) is True
    assert ProviderResultChecker([_RecoveryAdapter("1")]).matches(plan) is False
    assert ProviderResultChecker([
        _RecoveryAdapter(None, SourceState.ERROR)
    ]).matches(plan) is None


def test_application_startup_uses_fresh_provider_result_for_recovery(tmp_path: Path) -> None:
    store, plan_id = _interrupted_store(tmp_path / "state.db")
    create_app(AppConfig(
        password="test-only-password",
        storage_path=store.path,
        adapters=(_RecoveryAdapter("2"),),
        provider_mode="simulator",
        static_dir=ROOT / "web" / "dist",
    ))
    recovered = store.run_for_plan(plan_id)
    assert recovered is not None and recovered.state is UpdateRunState.SUCCEEDED


def test_m6_source_archive_is_clean_and_contains_operator_evidence() -> None:
    archive = ROOT / "packaging" / "arch" / "updatarr-0.6.0.tar.gz"
    workspace_marker = b"/home/soul" + b"/codex/Updatarr"
    with tarfile.open(archive, "r:gz") as source:
        names = set(source.getnames())
        prefix = "updatarr-0.6.0/"
        assert prefix + "docs/KNOWN_LIMITATIONS.md" in names
        assert prefix + "docs/operations/UPGRADE_RECOVERY.md" in names
        assert prefix + "scripts/read_only_capability_probe.py" in names
        assert prefix + "tests/test_m6_hardening.py" in names
        assert not any(
            "__pycache__" in name or name.endswith(".pyc")
            or ".egg-info" in name or "/build/" in name
            for name in names
        )
        for member in source.getmembers():
            if not member.isfile() or Path(member.name).suffix not in {
                ".py", ".md", ".json", ".toml", ".sh", ".ts", ".tsx", ".css"
            }:
                continue
            stream = source.extractfile(member)
            assert stream is not None
            assert workspace_marker not in stream.read(), member.name
