"""State setup and offline recovery checks for the disposable M7 package drill."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import sqlite3
import sys

from updatarr.storage import StateStore


STATE = Path("/home/updatarr-test/.local/state/updatarr/updatarr.db")
BACKUP = Path("/home/updatarr-test/backups/updatarr.db")
EXPECTED = {"value": "preserved"}


def create() -> None:
    store = StateStore(STATE)
    store.initialize()
    store.set_preference("admin", "lifecycle-proof", EXPECTED)
    store.backup(BACKUP)
    assert store.preference("admin", "lifecycle-proof") == EXPECTED
    assert BACKUP.stat().st_mode & 0o077 == 0


def restore() -> None:
    store = StateStore(STATE)
    assert store.preference("admin", "lifecycle-proof") == EXPECTED
    store.set_preference(
        "admin", "lifecycle-proof", {"value": "changed-after-backup"}
    )
    with sqlite3.connect(STATE) as current:
        current.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    for suffix in ("-wal", "-shm"):
        STATE.with_name(STATE.name + suffix).unlink(missing_ok=True)
    restored = STATE.with_name(STATE.name + ".restored")
    shutil.copyfile(BACKUP, restored)
    restored.chmod(0o600)
    os.replace(restored, STATE)
    assert StateStore(STATE).preference("admin", "lifecycle-proof") == EXPECTED


def verify() -> None:
    assert StateStore(STATE).preference("admin", "lifecycle-proof") == EXPECTED


if __name__ == "__main__":
    actions = {"create": create, "restore": restore, "verify": verify}
    if len(sys.argv) != 2 or sys.argv[1] not in actions:
        raise SystemExit("Use create, restore or verify.")
    actions[sys.argv[1]]()
