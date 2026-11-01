"""Explicit SQLite state-store Module for durable Updatarr state.

The Interface is intentionally small: initialize, store/read snapshots, record
tasks/events/audit, and persist presentation preferences. WAL, migrations,
transactions, JSON encoding and append-only enforcement stay inside.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import time
from typing import Any, Callable, Iterator

from .domain import (
    DetectedUpdate,
    ExternalHistoryEvent,
    InventorySnapshot,
    PolicyKind,
    PolicyState,
    SelectionPolicy,
    SoftwareRecord,
    SourceResult,
    SourceState,
    OperationKind,
    PermissionKind,
    PlanState,
    UpdatePlan,
    UpdatePlanStep,
    UpdateRun,
    UpdateRunState,
    can_transition_plan,
    can_transition_update_run,
    utc_now,
)
from .history import HistoryImportBatch, HistorySourceState
from .planning import policy_digest


SCHEMA_VERSION = 6


@dataclass(frozen=True)
class Page:
    items: list[dict[str, Any]]
    total: int
    limit: int
    offset: int

    def to_dict(self) -> dict[str, Any]:
        return {"items": self.items, "total": self.total, "limit": self.limit, "offset": self.offset}


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        parent_existed = self.path.parent.exists()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not parent_existed or self.path.parent.name == ".state":
            os.chmod(self.path.parent, 0o700)
        else:
            directory = self.path.parent.stat()
            if stat.S_IMODE(directory.st_mode) & 0o077:
                raise PermissionError(
                    "The Updatarr state directory must be accessible only to its owner."
                )
        connection = sqlite3.connect(self.path, timeout=5, autocommit=True)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            connection.execute("PRAGMA journal_mode = WAL")
            migration_table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_migrations'"
            ).fetchone()
            if migration_table is not None:
                newest = connection.execute(
                    "SELECT MAX(version) FROM schema_migrations"
                ).fetchone()[0]
                if newest is not None and int(newest) > SCHEMA_VERSION:
                    raise RuntimeError(
                        "This database was created by a newer Updatarr version. "
                        "Install that version or restore a compatible backup."
                    )
            connection.executescript(
                """
                BEGIN IMMEDIATE;
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS inventory_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    generation TEXT NOT NULL UNIQUE,
                    started_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS snapshot_sources (
                    snapshot_id TEXT NOT NULL REFERENCES inventory_snapshots(snapshot_id) ON DELETE CASCADE,
                    source_id TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    name TEXT NOT NULL,
                    state TEXT NOT NULL,
                    message TEXT NOT NULL,
                    checked_at TEXT NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    tool_version TEXT,
                    evidence_json TEXT NOT NULL,
                    PRIMARY KEY (snapshot_id, source_id, scope)
                );
                CREATE TABLE IF NOT EXISTS software_records (
                    snapshot_id TEXT NOT NULL REFERENCES inventory_snapshots(snapshot_id) ON DELETE CASCADE,
                    stable_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    software_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    installed_version TEXT,
                    origin TEXT,
                    architecture TEXT,
                    branch TEXT,
                    ownership TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    PRIMARY KEY (snapshot_id, stable_id)
                );
                CREATE INDEX IF NOT EXISTS software_snapshot_source ON software_records(snapshot_id, source_id, scope);
                CREATE TABLE IF NOT EXISTS detected_updates (
                    snapshot_id TEXT NOT NULL REFERENCES inventory_snapshots(snapshot_id) ON DELETE CASCADE,
                    stable_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    software_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    installed_version TEXT,
                    available_version TEXT NOT NULL,
                    state TEXT NOT NULL,
                    restart_needed INTEGER,
                    size_bytes INTEGER,
                    summary TEXT,
                    PRIMARY KEY (snapshot_id, stable_id, available_version)
                );
                CREATE TABLE IF NOT EXISTS background_tasks (
                    task_id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    state TEXT NOT NULL,
                    progress INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT
                );
                CREATE TABLE IF NOT EXISTS task_events (
                    event_id INTEGER PRIMARY KEY,
                    task_id TEXT,
                    kind TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    occurred_at TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    correlation_id TEXT,
                    details_json TEXT NOT NULL
                );
                CREATE TRIGGER IF NOT EXISTS audit_events_no_update
                BEFORE UPDATE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit events are append-only'); END;
                CREATE TRIGGER IF NOT EXISTS audit_events_no_delete
                BEFORE DELETE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit events are append-only'); END;
                CREATE TABLE IF NOT EXISTS preferences (
                    account_id TEXT NOT NULL,
                    preference_key TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    modified_at TEXT NOT NULL,
                    PRIMARY KEY (account_id, preference_key)
                );
                CREATE TABLE IF NOT EXISTS accounts (
                    account_id TEXT PRIMARY KEY,
                    password_verifier TEXT NOT NULL,
                    changed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS web_sessions (
                    session_hash TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL REFERENCES accounts(account_id) ON DELETE CASCADE,
                    csrf_token TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS web_sessions_expiry ON web_sessions(expires_at);
                INSERT OR IGNORE INTO schema_migrations(version, applied_at)
                VALUES (1, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'));
                """
            )
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS selection_policies (
                    policy_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    state TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    software_id TEXT,
                    version TEXT,
                    expires_at TEXT,
                    reason TEXT,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    removed_at TEXT,
                    last_applied_at TEXT,
                    last_applied_snapshot TEXT
                );
                CREATE INDEX IF NOT EXISTS selection_policy_active
                    ON selection_policies(state, source_id, scope, kind);
                CREATE TABLE IF NOT EXISTS policy_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    policy_id TEXT NOT NULL REFERENCES selection_policies(policy_id),
                    occurred_at TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    details_json TEXT NOT NULL
                );
                CREATE TRIGGER IF NOT EXISTS policy_events_no_update
                BEFORE UPDATE ON policy_events BEGIN SELECT RAISE(ABORT, 'policy events are append-only'); END;
                CREATE TRIGGER IF NOT EXISTS policy_events_no_delete
                BEFORE DELETE ON policy_events BEGIN SELECT RAISE(ABORT, 'policy events are append-only'); END;
                CREATE TABLE IF NOT EXISTS external_history_events (
                    event_id TEXT PRIMARY KEY,
                    dedupe_key TEXT NOT NULL UNIQUE,
                    source_id TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    action TEXT NOT NULL,
                    software_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    version_before TEXT,
                    version_after TEXT,
                    result TEXT NOT NULL,
                    completeness TEXT NOT NULL,
                    provenance TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    imported_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS external_history_time
                    ON external_history_events(occurred_at DESC);
                CREATE TRIGGER IF NOT EXISTS external_history_no_update
                BEFORE UPDATE ON external_history_events BEGIN SELECT RAISE(ABORT, 'imported history is append-only'); END;
                CREATE TRIGGER IF NOT EXISTS external_history_no_delete
                BEFORE DELETE ON external_history_events BEGIN SELECT RAISE(ABORT, 'imported history is append-only'); END;
                INSERT OR IGNORE INTO schema_migrations(version, applied_at)
                VALUES (2, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'));
                """
            )
            policy_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(selection_policies)")
            }
            if "target_stable_id" not in policy_columns:
                connection.execute(
                    "ALTER TABLE selection_policies ADD COLUMN target_stable_id TEXT"
                )
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS history_import_batches (
                    batch_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requested_range TEXT NOT NULL,
                    first_position TEXT,
                    last_position TEXT,
                    record_count INTEGER NOT NULL,
                    skipped_count INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    imported_at TEXT NOT NULL
                );
                CREATE TRIGGER IF NOT EXISTS history_import_batches_no_update
                BEFORE UPDATE ON history_import_batches BEGIN SELECT RAISE(ABORT, 'history import batches are append-only'); END;
                CREATE TRIGGER IF NOT EXISTS history_import_batches_no_delete
                BEFORE DELETE ON history_import_batches BEGIN SELECT RAISE(ABORT, 'history import batches are append-only'); END;
                CREATE TABLE IF NOT EXISTS history_source_state (
                    source_key TEXT PRIMARY KEY,
                    device INTEGER NOT NULL,
                    inode INTEGER NOT NULL,
                    size INTEGER NOT NULL,
                    mtime_ns INTEGER NOT NULL,
                    generation INTEGER NOT NULL,
                    tail_hash TEXT NOT NULL,
                    checked_at TEXT NOT NULL
                );
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (3, utc_now()),
            )
            connection.execute(
                "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (4, utc_now()),
            )
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS update_plans (
                    plan_id TEXT PRIMARY KEY,
                    digest TEXT NOT NULL UNIQUE,
                    content_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );
                CREATE TRIGGER IF NOT EXISTS update_plans_no_update
                BEFORE UPDATE ON update_plans BEGIN SELECT RAISE(ABORT, 'update plans are immutable'); END;
                CREATE TRIGGER IF NOT EXISTS update_plans_no_delete
                BEFORE DELETE ON update_plans BEGIN SELECT RAISE(ABORT, 'update plans are immutable'); END;
                CREATE TABLE IF NOT EXISTS update_plan_states (
                    plan_id TEXT PRIMARY KEY REFERENCES update_plans(plan_id),
                    state TEXT NOT NULL,
                    changed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS update_plan_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id TEXT NOT NULL REFERENCES update_plans(plan_id),
                    occurred_at TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    details_json TEXT NOT NULL
                );
                CREATE TRIGGER IF NOT EXISTS update_plan_events_no_update
                BEFORE UPDATE ON update_plan_events BEGIN SELECT RAISE(ABORT, 'plan events are append-only'); END;
                CREATE TRIGGER IF NOT EXISTS update_plan_events_no_delete
                BEFORE DELETE ON update_plan_events BEGIN SELECT RAISE(ABORT, 'plan events are append-only'); END;
                CREATE TABLE IF NOT EXISTS update_runs (
                    run_id TEXT PRIMARY KEY,
                    plan_id TEXT NOT NULL REFERENCES update_plans(plan_id),
                    plan_digest TEXT NOT NULL,
                    state TEXT NOT NULL,
                    progress INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT
                );
                CREATE TABLE IF NOT EXISTS update_run_steps (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL REFERENCES update_runs(run_id),
                    occurred_at TEXT NOT NULL,
                    details_json TEXT NOT NULL
                );
                CREATE TRIGGER IF NOT EXISTS update_run_steps_no_update
                BEFORE UPDATE ON update_run_steps BEGIN SELECT RAISE(ABORT, 'run steps are append-only'); END;
                CREATE TRIGGER IF NOT EXISTS update_run_steps_no_delete
                BEFORE DELETE ON update_run_steps BEGIN SELECT RAISE(ABORT, 'run steps are append-only'); END;
                INSERT OR IGNORE INTO schema_migrations(version, applied_at)
                VALUES (5, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'));
                CREATE INDEX IF NOT EXISTS software_records_page
                ON software_records(snapshot_id, name COLLATE NOCASE, stable_id);
                CREATE INDEX IF NOT EXISTS software_records_identity_search
                ON software_records(snapshot_id, source_id, software_id);
                INSERT OR IGNORE INTO schema_migrations(version, applied_at)
                VALUES (6, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'));
                """
            )
            connection.execute("COMMIT")
            os.chmod(self.path, 0o600)
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def save_snapshot(self, snapshot: InventorySnapshot) -> None:
        with self.transaction() as connection:
            existing = connection.execute(
                "SELECT snapshot_id, generation FROM inventory_snapshots WHERE snapshot_id = ? OR generation = ?",
                (snapshot.snapshot_id, snapshot.generation),
            ).fetchone()
            if existing is not None:
                if existing["snapshot_id"] != snapshot.snapshot_id or existing["generation"] != snapshot.generation:
                    raise ValueError("inventory snapshot identity collision")
                return
            connection.execute(
                "INSERT INTO inventory_snapshots VALUES (?, ?, ?, ?)",
                (snapshot.snapshot_id, snapshot.generation, snapshot.started_at, snapshot.completed_at),
            )
            for source in snapshot.sources:
                connection.execute(
                    """INSERT INTO snapshot_sources
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        snapshot.snapshot_id, source.source_id, source.scope, source.name,
                        source.state.value, source.message, source.checked_at, source.duration_ms,
                        source.tool_version, json.dumps(source.evidence, sort_keys=True),
                    ),
                )
                for software in source.software:
                    connection.execute(
                        """INSERT INTO software_records
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            snapshot.snapshot_id, software.stable_id, software.source_id,
                            software.scope, software.software_id, software.name,
                            software.installed_version, software.origin, software.architecture,
                            software.branch, software.ownership,
                            json.dumps(software.details, sort_keys=True),
                        ),
                    )
                for update in source.updates:
                    connection.execute(
                        """INSERT INTO detected_updates
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            snapshot.snapshot_id, update.stable_id, update.source_id,
                            update.scope, update.software_id, update.name,
                            update.installed_version, update.available_version,
                            update.state.value,
                            None if update.restart_needed is None else int(update.restart_needed),
                            update.size_bytes, update.summary,
                        ),
                    )

    def latest_snapshot(self) -> InventorySnapshot | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM inventory_snapshots ORDER BY completed_at DESC LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            sources: list[SourceResult] = []
            for source_row in connection.execute(
                "SELECT * FROM snapshot_sources WHERE snapshot_id = ? ORDER BY name, scope",
                (row["snapshot_id"],),
            ):
                software = tuple(
                    SoftwareRecord(
                        source_id=item["source_id"], scope=item["scope"], software_id=item["software_id"],
                        name=item["name"], installed_version=item["installed_version"],
                        origin=item["origin"], architecture=item["architecture"], branch=item["branch"],
                        ownership=item["ownership"], details=json.loads(item["details_json"]),
                    )
                    for item in connection.execute(
                        "SELECT * FROM software_records WHERE snapshot_id = ? AND source_id = ? AND scope = ? ORDER BY name",
                        (row["snapshot_id"], source_row["source_id"], source_row["scope"]),
                    )
                )
                updates = tuple(
                    DetectedUpdate(
                        stable_id=item["stable_id"], source_id=item["source_id"], scope=item["scope"],
                        software_id=item["software_id"], name=item["name"],
                        installed_version=item["installed_version"], available_version=item["available_version"],
                        state=SourceState(item["state"]),
                        restart_needed=None if item["restart_needed"] is None else bool(item["restart_needed"]),
                        size_bytes=item["size_bytes"], summary=item["summary"],
                    )
                    for item in connection.execute(
                        "SELECT * FROM detected_updates WHERE snapshot_id = ? AND source_id = ? AND scope = ? ORDER BY name",
                        (row["snapshot_id"], source_row["source_id"], source_row["scope"]),
                    )
                )
                sources.append(SourceResult(
                    source_id=source_row["source_id"], name=source_row["name"], scope=source_row["scope"],
                    state=SourceState(source_row["state"]), message=source_row["message"],
                    checked_at=source_row["checked_at"], duration_ms=source_row["duration_ms"],
                    software=software, updates=updates, tool_version=source_row["tool_version"],
                    evidence=json.loads(source_row["evidence_json"]),
                ))
            return InventorySnapshot(
                snapshot_id=row["snapshot_id"], generation=row["generation"],
                started_at=row["started_at"], completed_at=row["completed_at"], sources=tuple(sources),
            )

    def inventory_page(self, *, limit: int = 100, offset: int = 0, query: str = "") -> Page:
        with self._connect() as connection:
            snapshot = connection.execute(
                "SELECT snapshot_id FROM inventory_snapshots ORDER BY completed_at DESC LIMIT 1"
            ).fetchone()
            if snapshot is None:
                return Page([], 0, limit, offset)
            where = "snapshot_id = ?"
            parameters: list[object] = [snapshot["snapshot_id"]]
            if query:
                escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                where += (
                    " AND (name LIKE ? ESCAPE '\\' COLLATE NOCASE"
                    " OR software_id LIKE ? ESCAPE '\\' COLLATE NOCASE"
                    " OR source_id LIKE ? ESCAPE '\\' COLLATE NOCASE)"
                )
                pattern = f"%{escaped}%"
                parameters.extend((pattern, pattern, pattern))
            total = int(connection.execute(
                f"SELECT COUNT(*) FROM software_records WHERE {where}", parameters
            ).fetchone()[0])
            rows = connection.execute(
                f"""SELECT * FROM software_records WHERE {where}
                    ORDER BY name COLLATE NOCASE, stable_id LIMIT ? OFFSET ?""",
                (*parameters, limit, offset),
            ).fetchall()
        values = [SoftwareRecord(
            source_id=row["source_id"], scope=row["scope"], software_id=row["software_id"],
            name=row["name"], installed_version=row["installed_version"], origin=row["origin"],
            architecture=row["architecture"], branch=row["branch"], ownership=row["ownership"],
            details=json.loads(row["details_json"]),
        ).to_dict() for row in rows]
        return Page(values, total, limit, offset)

    def record_audit(self, kind: str, actor: str, details: dict[str, Any], correlation_id: str | None = None) -> int:
        with self.transaction() as connection:
            cursor = connection.execute(
                "INSERT INTO audit_events(occurred_at, kind, actor, correlation_id, details_json) VALUES (?, ?, ?, ?, ?)",
                (utc_now(), kind, actor, correlation_id, json.dumps(details, sort_keys=True)),
            )
            return int(cursor.lastrowid)

    def audit_page(self, *, limit: int = 50, offset: int = 0) -> Page:
        with self._connect() as connection:
            total = int(connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0])
            rows = connection.execute(
                "SELECT * FROM audit_events ORDER BY audit_id DESC LIMIT ? OFFSET ?", (limit, offset)
            ).fetchall()
        return Page([
            {"audit_id": row["audit_id"], "occurred_at": row["occurred_at"], "kind": row["kind"],
             "actor": row["actor"], "correlation_id": row["correlation_id"],
             "details": json.loads(row["details_json"])} for row in rows
        ], total, limit, offset)

    @staticmethod
    def _policy_from_row(row: sqlite3.Row) -> SelectionPolicy:
        return SelectionPolicy(
            policy_id=row["policy_id"],
            kind=PolicyKind(row["kind"]),
            state=PolicyState(row["state"]),
            source_id=row["source_id"],
            scope=row["scope"],
            software_id=row["software_id"],
            target_stable_id=row["target_stable_id"],
            version=row["version"],
            expires_at=row["expires_at"],
            reason=row["reason"],
            created_by=row["created_by"],
            created_at=row["created_at"],
            removed_at=row["removed_at"],
            last_applied_at=row["last_applied_at"],
            last_applied_snapshot=row["last_applied_snapshot"],
        )

    def create_policy(self, policy: SelectionPolicy) -> SelectionPolicy:
        with self.transaction() as connection:
            duplicate = connection.execute(
                """SELECT policy_id FROM selection_policies
                   WHERE state = 'active' AND kind = ? AND source_id = ? AND scope = ?
                     AND COALESCE(software_id, '') = COALESCE(?, '')
                     AND COALESCE(target_stable_id, '') = COALESCE(?, '')
                     AND COALESCE(version, '') = COALESCE(?, '')""",
                (
                    policy.kind.value, policy.source_id, policy.scope,
                    policy.software_id, policy.target_stable_id, policy.version,
                ),
            ).fetchone()
            if duplicate is not None:
                raise ValueError("That choice is already saved.")
            connection.execute(
                """INSERT INTO selection_policies(
                       policy_id, kind, state, source_id, scope, software_id,
                       version, expires_at, reason, created_by, created_at,
                       removed_at, last_applied_at, last_applied_snapshot,
                       target_stable_id
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    policy.policy_id, policy.kind.value, policy.state.value,
                    policy.source_id, policy.scope, policy.software_id, policy.version,
                    policy.expires_at, policy.reason, policy.created_by,
                    policy.created_at, policy.removed_at,
                    policy.last_applied_at, policy.last_applied_snapshot,
                    policy.target_stable_id,
                ),
            )
            connection.execute(
                """INSERT INTO policy_events(policy_id, occurred_at, kind, actor, details_json)
                   VALUES (?, ?, 'created', ?, ?)""",
                (policy.policy_id, policy.created_at, policy.created_by,
                 json.dumps({"kind": policy.kind.value}, sort_keys=True)),
            )
        return policy

    def policies(self, *, include_inactive: bool = False) -> list[SelectionPolicy]:
        now = utc_now()
        with self.transaction() as connection:
            expired = connection.execute(
                """SELECT policy_id, created_by FROM selection_policies
                   WHERE state = 'active' AND expires_at IS NOT NULL AND expires_at <= ?""",
                (now,),
            ).fetchall()
            for row in expired:
                connection.execute(
                    "UPDATE selection_policies SET state = 'expired', removed_at = ? WHERE policy_id = ?",
                    (now, row["policy_id"]),
                )
                connection.execute(
                    """INSERT INTO policy_events(policy_id, occurred_at, kind, actor, details_json)
                       VALUES (?, ?, 'expired', ?, '{}')""",
                    (row["policy_id"], now, row["created_by"]),
                )
            sql = "SELECT * FROM selection_policies"
            parameters: tuple[object, ...] = ()
            if not include_inactive:
                sql += " WHERE state = ?"
                parameters = (PolicyState.ACTIVE.value,)
            sql += " ORDER BY created_at DESC, policy_id"
            rows = connection.execute(sql, parameters).fetchall()
        return [self._policy_from_row(row) for row in rows]

    def remove_policy(self, policy_id: str, actor: str = "administrator") -> SelectionPolicy | None:
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM selection_policies WHERE policy_id = ?", (policy_id,)
            ).fetchone()
            if row is None:
                return None
            policy = self._policy_from_row(row)
            if policy.state is not PolicyState.ACTIVE:
                return policy
            removed_at = utc_now()
            connection.execute(
                "UPDATE selection_policies SET state = 'removed', removed_at = ? WHERE policy_id = ?",
                (removed_at, policy_id),
            )
            connection.execute(
                """INSERT INTO policy_events(policy_id, occurred_at, kind, actor, details_json)
                   VALUES (?, ?, 'removed', ?, '{}')""",
                (policy_id, removed_at, actor),
            )
            row = connection.execute(
                "SELECT * FROM selection_policies WHERE policy_id = ?", (policy_id,)
            ).fetchone()
        return self._policy_from_row(row)

    def turned_off_sources(self) -> set[tuple[str, str]]:
        return {
            (policy.source_id, policy.scope)
            for policy in self.policies()
            if policy.kind is PolicyKind.TURN_OFF_SOURCE
        }

    def source_is_enabled(self, source_id: str, scope: str) -> bool:
        return (source_id, scope) not in self.turned_off_sources()

    def mark_policies_applied(self, policy_ids: set[str], snapshot_id: str) -> None:
        if not policy_ids:
            return
        applied_at = utc_now()
        with self.transaction() as connection:
            for policy_id in sorted(policy_ids):
                row = connection.execute(
                    "SELECT created_by, last_applied_snapshot FROM selection_policies WHERE policy_id = ?",
                    (policy_id,),
                ).fetchone()
                if row is None or row["last_applied_snapshot"] == snapshot_id:
                    continue
                connection.execute(
                    """UPDATE selection_policies
                       SET last_applied_at = ?, last_applied_snapshot = ? WHERE policy_id = ?""",
                    (applied_at, snapshot_id, policy_id),
                )
                connection.execute(
                    """INSERT INTO policy_events(policy_id, occurred_at, kind, actor, details_json)
                       VALUES (?, ?, 'applied', ?, ?)""",
                    (policy_id, applied_at, row["created_by"],
                     json.dumps({"snapshot_id": snapshot_id}, sort_keys=True)),
                )

    def import_history(self, events: list[ExternalHistoryEvent] | tuple[ExternalHistoryEvent, ...]) -> int:
        imported = 0
        with self.transaction() as connection:
            for event in events:
                cursor = connection.execute(
                    """INSERT OR IGNORE INTO external_history_events
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        event.event_id, event.dedupe_key, event.source_id, event.scope,
                        event.occurred_at, event.action, event.software_id, event.name,
                        event.version_before, event.version_after, event.result,
                        event.completeness, event.provenance,
                        json.dumps(event.details, sort_keys=True), utc_now(),
                    ),
                )
                imported += int(cursor.rowcount == 1)
        return imported

    def record_history_batches(self, batches: list[HistoryImportBatch] | tuple[HistoryImportBatch, ...]) -> int:
        added = 0
        with self.transaction() as connection:
            for batch in batches:
                cursor = connection.execute(
                    """INSERT OR IGNORE INTO history_import_batches
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        batch.batch_id, batch.source_id, batch.scope, batch.status,
                        batch.requested_range, batch.first_position, batch.last_position,
                        batch.record_count, batch.skipped_count, batch.reason,
                        batch.observed_at, utc_now(),
                    ),
                )
                added += int(cursor.rowcount == 1)
        return added

    def history_import_batches(self, *, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT * FROM history_import_batches
                   ORDER BY imported_at DESC, batch_id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def history_source_state(self, source_key: str) -> HistorySourceState | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM history_source_state WHERE source_key = ?", (source_key,)
            ).fetchone()
        if row is None:
            return None
        return HistorySourceState(
            source_key=row["source_key"], device=row["device"], inode=row["inode"],
            size=row["size"], mtime_ns=row["mtime_ns"], generation=row["generation"],
            tail_hash=row["tail_hash"],
        )

    def save_history_source_state(self, state: HistorySourceState) -> None:
        with self.transaction() as connection:
            connection.execute(
                """INSERT INTO history_source_state
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(source_key) DO UPDATE SET
                     device=excluded.device, inode=excluded.inode, size=excluded.size,
                     mtime_ns=excluded.mtime_ns, generation=excluded.generation,
                     tail_hash=excluded.tail_hash, checked_at=excluded.checked_at""",
                (
                    state.source_key, state.device, state.inode, state.size,
                    state.mtime_ns, state.generation, state.tail_hash, utc_now(),
                ),
            )

    def external_history_page(self, *, limit: int = 100, offset: int = 0) -> Page:
        with self._connect() as connection:
            total = int(connection.execute("SELECT COUNT(*) FROM external_history_events").fetchone()[0])
            rows = connection.execute(
                """SELECT * FROM external_history_events
                   ORDER BY occurred_at DESC, event_id DESC LIMIT ? OFFSET ?""",
                (limit, offset),
            ).fetchall()
        return Page([
            {
                "event_id": row["event_id"], "source_id": row["source_id"],
                "scope": row["scope"], "occurred_at": row["occurred_at"],
                "action": row["action"], "software_id": row["software_id"],
                "name": row["name"], "version_before": row["version_before"],
                "version_after": row["version_after"], "result": row["result"],
                "completeness": row["completeness"], "provenance": row["provenance"],
                "details": json.loads(row["details_json"]), "history_kind": "imported",
            }
            for row in rows
        ], total, limit, offset)

    def history_summary(self) -> dict[str, Any]:
        with self._connect() as connection:
            imported = int(connection.execute("SELECT COUNT(*) FROM external_history_events").fetchone()[0])
            app_events = int(connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0])
            by_source = [
                {"source_id": row["source_id"], "count": int(row["count"])}
                for row in connection.execute(
                    """SELECT source_id, COUNT(*) AS count FROM external_history_events
                       GROUP BY source_id ORDER BY source_id"""
                )
            ]
        return {
            "imported_events": imported,
            "updatarr_events": app_events,
            "recorded_changes": imported,
            "by_source": by_source,
            "download_bytes": None,
            "download_data_label": "No download data recorded",
        }

    def save_task(self, task: dict[str, Any]) -> None:
        with self.transaction() as connection:
            connection.execute(
                """INSERT INTO background_tasks VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(task_id) DO UPDATE SET state=excluded.state, progress=excluded.progress,
                   message=excluded.message, finished_at=excluded.finished_at""",
                (task["id"], task.get("type", "inventory_check"), task["state"], task["progress"],
                 task["message"], task["started_at"], task.get("finished_at")),
            )

    def save_event(self, event_id: int, task_id: str | None, kind: str, payload: dict[str, Any]) -> None:
        with self.transaction() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO task_events VALUES (?, ?, ?, ?, ?)",
                (event_id, task_id, kind, utc_now(), json.dumps(payload, sort_keys=True)),
            )
            connection.execute(
                "DELETE FROM task_events WHERE event_id NOT IN (SELECT event_id FROM task_events ORDER BY event_id DESC LIMIT 200)"
            )

    def recent_events(self, limit: int = 100) -> list[tuple[int, str, dict[str, Any]]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT event_id, kind, payload_json FROM task_events ORDER BY event_id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [(row["event_id"], row["kind"], json.loads(row["payload_json"])) for row in reversed(rows)]

    def preference(self, account_id: str, key: str, default: Any = None) -> Any:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value_json FROM preferences WHERE account_id = ? AND preference_key = ?", (account_id, key)
            ).fetchone()
        return default if row is None else json.loads(row["value_json"])

    def set_preference(self, account_id: str, key: str, value: Any) -> None:
        with self.transaction() as connection:
            connection.execute(
                """INSERT INTO preferences VALUES (?, ?, ?, ?)
                   ON CONFLICT(account_id, preference_key) DO UPDATE SET value_json=excluded.value_json,
                   modified_at=excluded.modified_at""",
                (account_id, key, json.dumps(value), utc_now()),
            )

    def password_verifier(self, account_id: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT password_verifier FROM accounts WHERE account_id = ?", (account_id,)
            ).fetchone()
        return None if row is None else str(row["password_verifier"])

    def save_password_verifier(self, account_id: str, verifier: str) -> None:
        with self.transaction() as connection:
            connection.execute(
                """INSERT INTO accounts VALUES (?, ?, ?)
                   ON CONFLICT(account_id) DO UPDATE SET
                   password_verifier=excluded.password_verifier, changed_at=excluded.changed_at""",
                (account_id, verifier, utc_now()),
            )

    @staticmethod
    def _session_hash(session_id: str) -> str:
        import hashlib
        return hashlib.sha256(session_id.encode("utf-8")).hexdigest()

    def save_session(self, account_id: str, session_id: str, csrf_token: str, expires_at: float) -> None:
        with self.transaction() as connection:
            connection.execute("DELETE FROM web_sessions WHERE expires_at <= ?", (time.time(),))
            connection.execute(
                "INSERT INTO web_sessions VALUES (?, ?, ?, ?, ?)",
                (self._session_hash(session_id), account_id, csrf_token, expires_at, utc_now()),
            )

    def load_session(self, session_id: str) -> tuple[str, float] | None:
        session_hash = self._session_hash(session_id)
        with self.transaction() as connection:
            connection.execute("DELETE FROM web_sessions WHERE expires_at <= ?", (time.time(),))
            row = connection.execute(
                "SELECT csrf_token, expires_at FROM web_sessions WHERE session_hash = ?",
                (session_hash,),
            ).fetchone()
        if row is None:
            return None
        return str(row["csrf_token"]), float(row["expires_at"])

    def delete_session(self, session_id: str) -> None:
        with self.transaction() as connection:
            connection.execute(
                "DELETE FROM web_sessions WHERE session_hash = ?", (self._session_hash(session_id),)
            )

    def clear_sessions(self, account_id: str) -> None:
        with self.transaction() as connection:
            connection.execute("DELETE FROM web_sessions WHERE account_id = ?", (account_id,))

    def backup(self, destination: Path) -> None:
        parent_existed = destination.parent.exists()
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not parent_existed:
            os.chmod(destination.parent, 0o700)
        with self._connect() as source, sqlite3.connect(destination) as target:
            source.backup(target)
        os.chmod(destination, 0o600)

    @staticmethod
    def _plan_from_row(row: sqlite3.Row) -> UpdatePlan:
        value = json.loads(row["content_json"])
        steps = tuple(UpdatePlanStep(
            step_id=step["step_id"], operation=OperationKind(step["operation"]),
            source_id=step["source_id"], scope=step["scope"],
            target_stable_ids=tuple(step["target_stable_ids"]), package_ids=tuple(step["package_ids"]),
            permission=PermissionKind(step["permission"]), summary=step["summary"],
            expected_changes=tuple(tuple(change) for change in step.get("expected_changes", [])),
            safe_cancellation=step.get("safe_cancellation", "Before this step starts"),
            live_enabled=bool(step.get("live_enabled", False)), blocker=step.get("blocker"),
        ) for step in value["steps"])
        return UpdatePlan(
            plan_id=row["plan_id"], digest=row["digest"], snapshot_id=value["snapshot_id"],
            snapshot_generation=value["snapshot_generation"], created_by=value["created_by"],
            created_at=value["created_at"], expires_at=value["expires_at"], steps=steps,
            warnings=tuple(value.get("warnings", [])), blockers=tuple(value.get("blockers", [])),
            policy_ids=tuple(value.get("policy_ids", [])),
            policy_digest=value.get("policy_digest", ""),
            tool_versions=tuple(tuple(item) for item in value.get("tool_versions", [])),
            unknowns=tuple(value.get("unknowns", [])),
        )

    def save_plan(self, plan: UpdatePlan) -> None:
        content = json.dumps(
            plan.canonical_content(), sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        )
        with self.transaction() as connection:
            existing = connection.execute("SELECT digest, content_json FROM update_plans WHERE plan_id = ?", (plan.plan_id,)).fetchone()
            if existing is not None:
                if existing["digest"] != plan.digest or existing["content_json"] != content:
                    raise ValueError("A plan cannot be changed after it is prepared.")
                return
            connection.execute("INSERT INTO update_plans VALUES (?, ?, ?, ?, ?)",
                               (plan.plan_id, plan.digest, content, plan.created_at, plan.expires_at))
            connection.execute("INSERT INTO update_plan_states VALUES (?, ?, ?)",
                               (plan.plan_id, PlanState.AWAITING_REVIEW.value, plan.created_at))
            connection.execute("INSERT INTO update_plan_events(plan_id, occurred_at, kind, actor, details_json) VALUES (?, ?, ?, ?, ?)",
                               (plan.plan_id, plan.created_at, "prepared", plan.created_by, "{}"))

    def plan(self, plan_id: str) -> tuple[UpdatePlan, PlanState] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT p.*, s.state FROM update_plans p JOIN update_plan_states s USING(plan_id) WHERE plan_id = ?", (plan_id,)).fetchone()
        return None if row is None else (self._plan_from_row(row), PlanState(row["state"]))

    def latest_plan(self) -> tuple[UpdatePlan, PlanState] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT p.*, s.state FROM update_plans p JOIN update_plan_states s USING(plan_id) ORDER BY p.created_at DESC LIMIT 1").fetchone()
        return None if row is None else (self._plan_from_row(row), PlanState(row["state"]))

    def plan_events(self, plan_id: str) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT occurred_at, kind, actor, details_json FROM update_plan_events WHERE plan_id = ? ORDER BY event_id",
                (plan_id,),
            ).fetchall()
        return [{"occurred_at": row["occurred_at"], "kind": row["kind"], "actor": row["actor"],
                 "details": json.loads(row["details_json"])} for row in rows]

    def transition_plan(self, plan_id: str, expected: PlanState, requested: PlanState,
                        kind: str, actor: str, details: dict[str, Any] | None = None) -> PlanState:
        with self.transaction() as connection:
            row = connection.execute("SELECT state FROM update_plan_states WHERE plan_id = ?", (plan_id,)).fetchone()
            if row is None:
                raise ValueError("Plan not found.")
            current = PlanState(row["state"])
            if current is not expected:
                raise ValueError("The plan is no longer at the expected step.")
            if not can_transition_plan(current, requested):
                raise ValueError("That plan state change is not allowed.")
            changed = utc_now()
            connection.execute("UPDATE update_plan_states SET state = ?, changed_at = ? WHERE plan_id = ?",
                               (requested.value, changed, plan_id))
            connection.execute("INSERT INTO update_plan_events(plan_id, occurred_at, kind, actor, details_json) VALUES (?, ?, ?, ?, ?)",
                               (plan_id, changed, kind, actor, json.dumps(details or {}, sort_keys=True)))
        return requested

    def claim_plan_for_run(self, run: UpdateRun) -> None:
        """Atomically consume one ready plan and create its sole durable run."""
        if run.state is not UpdateRunState.CREATED:
            raise ValueError("A claimed run must start in the created state.")
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT p.*, s.state FROM update_plans p JOIN update_plan_states s USING(plan_id) WHERE plan_id = ?",
                (run.plan_id,),
            ).fetchone()
            if row is None or PlanState(row["state"]) is not PlanState.READY_FOR_EXECUTION:
                raise ValueError("The plan is not ready or has already been claimed.")
            plan = self._plan_from_row(row)
            if run.plan_digest != plan.digest:
                raise ValueError("The update run does not match the reviewed plan. Prepare and review it again.")
            if hashlib.sha256(row["content_json"].encode("utf-8")).hexdigest() != plan.digest:
                raise ValueError("The update plan changed after it was reviewed. Prepare and review it again.")
            now = utc_now()
            if plan.expires_at <= now:
                raise ValueError("The reviewed plan expired before it could be claimed.")
            snapshot = connection.execute(
                "SELECT snapshot_id, generation FROM inventory_snapshots ORDER BY completed_at DESC LIMIT 1"
            ).fetchone()
            if (snapshot is None or snapshot["snapshot_id"] != plan.snapshot_id
                    or snapshot["generation"] != plan.snapshot_generation):
                raise ValueError("The recorded software changed before the plan could be claimed.")
            policy_rows = connection.execute(
                "SELECT * FROM selection_policies WHERE state = 'active' AND (expires_at IS NULL OR expires_at > ?) ORDER BY created_at DESC, policy_id",
                (now,),
            ).fetchall()
            policies = [self._policy_from_row(policy_row) for policy_row in policy_rows]
            if (tuple(sorted(policy.policy_id for policy in policies)) != plan.policy_ids
                    or policy_digest(policies) != plan.policy_digest):
                raise ValueError("A saved choice changed before the plan could be claimed.")
            if plan.blockers:
                raise ValueError(plan.blockers[0])
            changed = utc_now()
            connection.execute(
                "UPDATE update_plan_states SET state = ?, changed_at = ? WHERE plan_id = ?",
                (PlanState.CONSUMED.value, changed, run.plan_id),
            )
            connection.execute(
                "INSERT INTO update_plan_events(plan_id, occurred_at, kind, actor, details_json) VALUES (?, ?, ?, ?, ?)",
                (run.plan_id, changed, "plan_claimed", "local-agent",
                 json.dumps({"run_id": run.run_id}, sort_keys=True)),
            )
            connection.execute("INSERT INTO update_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                               (run.run_id, run.plan_id, run.plan_digest, run.state.value, run.progress,
                                run.message, run.started_at, run.finished_at))

    def append_run_steps(self, run_id: str, steps: list[dict[str, Any]]) -> None:
        with self.transaction() as connection:
            for step in steps:
                connection.execute("INSERT INTO update_run_steps(run_id, occurred_at, details_json) VALUES (?, ?, ?)",
                                   (run_id, utc_now(), json.dumps(step, sort_keys=True)))

    def record_run_progress(self, run_id: str, event: dict[str, Any]) -> None:
        with self.transaction() as connection:
            row = connection.execute("SELECT state FROM update_runs WHERE run_id = ?", (run_id,)).fetchone()
            if row is None or UpdateRunState(row["state"]) is not UpdateRunState.RUNNING:
                raise ValueError("Progress can only be recorded for a running update.")
            connection.execute(
                "INSERT INTO update_run_steps(run_id, occurred_at, details_json) VALUES (?, ?, ?)",
                (run_id, utc_now(), json.dumps(event, sort_keys=True)),
            )
            connection.execute(
                "UPDATE update_runs SET progress = ?, message = ? WHERE run_id = ?",
                (int(event["progress"]), str(event["message"]), run_id),
            )

    def transition_run(self, run_id: str, expected: UpdateRunState, requested: UpdateRunState,
                       *, progress: int, message: str, finished_at: str | None = None) -> UpdateRun:
        with self.transaction() as connection:
            row = connection.execute("SELECT * FROM update_runs WHERE run_id = ?", (run_id,)).fetchone()
            if row is None:
                raise ValueError("Update run not found.")
            current = UpdateRunState(row["state"])
            if current is not expected or not can_transition_update_run(current, requested):
                raise ValueError("That update-run state change is not allowed.")
            connection.execute(
                "UPDATE update_runs SET state = ?, progress = ?, message = ?, finished_at = ? WHERE run_id = ?",
                (requested.value, progress, message, finished_at, run_id),
            )
        return UpdateRun(run_id, row["plan_id"], row["plan_digest"], requested, progress,
                         message, row["started_at"], finished_at)

    def save_run(self, run: UpdateRun, steps: list[dict[str, Any]]) -> None:
        """Compatibility helper for fixtures; production uses claim and transitions."""
        with self.transaction() as connection:
            connection.execute("INSERT INTO update_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                               (run.run_id, run.plan_id, run.plan_digest, run.state.value, run.progress,
                                run.message, run.started_at, run.finished_at))
            for step in steps:
                connection.execute("INSERT INTO update_run_steps(run_id, occurred_at, details_json) VALUES (?, ?, ?)",
                                   (run.run_id, utc_now(), json.dumps(step, sort_keys=True)))

    def latest_run(self) -> UpdateRun | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM update_runs ORDER BY started_at DESC LIMIT 1").fetchone()
        if row is None:
            return None
        return UpdateRun(row["run_id"], row["plan_id"], row["plan_digest"], UpdateRunState(row["state"]),
                         row["progress"], row["message"], row["started_at"], row["finished_at"])

    def run_for_plan(self, plan_id: str) -> UpdateRun | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM update_runs WHERE plan_id = ? ORDER BY started_at DESC LIMIT 1", (plan_id,)).fetchone()
        if row is None:
            return None
        return UpdateRun(row["run_id"], row["plan_id"], row["plan_digest"], UpdateRunState(row["state"]),
                         row["progress"], row["message"], row["started_at"], row["finished_at"])

    def recover_unfinished_runs(
        self,
        verify_result: Callable[[UpdatePlan], bool | None] | None = None,
    ) -> int:
        """Reconcile interrupted runs, succeeding only with positive evidence.

        A missing, failed or negative result check remains a manual-recovery
        case. The lock and plan are never replayed during reconciliation.
        """
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT r.run_id, r.state, p.*
                   FROM update_runs r JOIN update_plans p USING(plan_id)
                   WHERE r.state IN ('created', 'running')"""
            ).fetchall()
        observations: list[tuple[sqlite3.Row, UpdateRunState, bool | None, str | None]] = []
        for row in rows:
            current = UpdateRunState(row["state"])
            check_result: bool | None = None
            check_problem: str | None = None
            if current is UpdateRunState.RUNNING and verify_result is not None:
                try:
                    check_result = verify_result(self._plan_from_row(row))
                except Exception:
                    check_problem = "result_check_failed"
            observations.append((row, current, check_result, check_problem))

        recovered = 0
        for row, current, check_result, check_problem in observations:
            requested = (
                UpdateRunState.SUCCEEDED
                if current is UpdateRunState.RUNNING and check_result is True
                else UpdateRunState.NEEDS_MANUAL_RECOVERY
            )
            if not can_transition_update_run(current, requested):
                continue
            message = (
                "Updatarr restarted and verified every expected software version."
                if requested is UpdateRunState.SUCCEEDED
                else "Updatarr restarted before it could verify the result. Manual recovery is needed."
            )
            reason = (
                "expected_versions_verified"
                if requested is UpdateRunState.SUCCEEDED
                else check_problem or (
                    "expected_versions_not_observed" if check_result is False
                    else "restart_before_result_check"
                )
            )
            with self.transaction() as connection:
                changed = connection.execute(
                    """UPDATE update_runs SET state = ?, progress = 100, message = ?, finished_at = ?
                       WHERE run_id = ? AND state = ?""",
                    (requested.value, message, utc_now(), row["run_id"], current.value),
                )
                if changed.rowcount != 1:
                    continue
                connection.execute(
                    "INSERT INTO update_run_steps(run_id, occurred_at, details_json) VALUES (?, ?, ?)",
                    (row["run_id"], utc_now(), json.dumps({
                        "state": requested.value,
                        "reason": reason,
                        "result_check": check_result,
                        "replayed": False,
                    }, sort_keys=True)),
                )
                recovered += 1
        return recovered
