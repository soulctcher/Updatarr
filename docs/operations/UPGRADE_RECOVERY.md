# Upgrade and interrupted-run recovery

**Applies to:** Updatarr 0.6.0 M6 evaluation build  
**Authorization:** this runbook explains operator work; it does not authorize a
package, service, notifier or software change

## Before an Updatarr package upgrade

1. Confirm no Updatarr update run or provider write is active.
2. Record the installed Updatarr version, package checksum, configured public
   address and actual XDG configuration/state paths.
3. Use SQLite's backup operation to create a consistent database backup. Copy
   the `0600` configuration separately and preserve its permissions.
4. Open the backup in a disposable directory, run `PRAGMA integrity_check`, and
   confirm the latest inventory and update-run record can be read.
5. Review the new package file list, source checksum, schema version and known
   limitations before separately approving installation.

Do not copy a live SQLite database file as the only backup. Its WAL may contain
committed data that is not present in the main file.

## After an approved package upgrade

1. Start the core manually before enabling startup.
2. Sign in through the loopback address and confirm the page and service both
   report API version 1. A version mismatch stops the browser from entering the
   application.
3. Confirm the database opened, the prior settings remain, and each update
   source shows its own current state rather than an invented all-clear.
4. Run a read-only check and compare source counts with the native tools.
5. If the tray is enabled, confirm one tray instance and that its count matches
   Overview.
6. Only after those checks, separately approve any service enablement or
   notifier migration.

## Interrupted update reconciliation

On startup, Updatarr finds update runs left in **Created** or **Running**.

- It never replays the plan automatically.
- It never treats process disappearance as success.
- When a trusted result check is available, success requires every expected
  version to match the immutable plan.
- A negative, unavailable or failed check becomes **Needs Manual Recovery**.
- The reconciliation event records whether a check ran and that no replay
  occurred.

For **Needs Manual Recovery**:

1. Leave the database, provider logs and package-manager lock unchanged.
2. Record the plan ID, run ID, expected versions, last durable step and provider
   state.
3. Use the owning update source's read-only status/history commands to establish
   what actually changed.
4. Repair through that provider's documented recovery procedure, not by editing
   Updatarr history.
5. Run a fresh read-only inventory before preparing another plan.

## Package-manager lock checklist

Updatarr distinguishes no lock, a lock held by another process, a lock held by
its own process and a lock whose owner cannot be observed. Every present lock
blocks a new native transaction.

1. Do not delete `/var/lib/pacman/db.lck` merely because it exists.
2. Establish whether a live package-manager process owns it and whether a
   transaction was interrupted.
3. Preserve relevant journal and pacman log evidence.
4. Follow the installed package manager's documented recovery procedure.
5. Confirm database integrity and run a safe read-only update check before
   allowing another native plan.

## Rollback

If the upgraded service cannot read prior state, stop it without starting any
software work. Preserve the failed database and logs, reinstall the last
reviewed compatible package, restore the tested backup and configuration, then
start manually on loopback. Confirm API compatibility, Overview, source states
and the latest run before restoring automatic startup.

Rollback does not change Octopi or notifier ownership. If a separately approved
notifier migration occurred, use the exact saved-owner procedure in
[Octopi migration and rollback](OCTOPI_MIGRATION.md).
