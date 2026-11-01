# M7 Managed-Computer Pilot Plan

**Prepared:** 2026-11-01
**Status:** plan only; the pilot is not authorized
**Purpose:** prove the reviewed package can run read-only on the managed
computer without replacing, disabling or changing an existing updater

## Separate Approvals

The pilot must not begin until the owner separately approves all actions that
are actually needed. Approval of this document alone does not authorize them.

1. Install the exact reviewed Updatarr package and any missing declared
   dependencies through pacman.
2. Create the owner-only Updatarr configuration and pilot state directories.
3. Start the core manually for this pilot, bound only to loopback.

The pilot does not request permission to enable either user service, start the
tray at login, change the Octopi notifier, remove Octopi or Pamac, enable LAN
access, publish a release or perform any software update.

## Exact Inputs

Before requesting approval, fill in and verify:

- Git revision and clean-worktree result;
- source archive, package and detached-signature SHA-256 values;
- trusted release-key fingerprint and signature-verification result;
- package file inventory and dependency check from `pacman -T`;
- current Updatarr/Octopi package, process, user-service and autostart state;
- actual XDG configuration, state, cache and runtime paths; and
- free disk space plus the package-manager lock state.

Stop if any recorded artifact differs, a dependency would remove or replace
unrelated software, pacman is busy, or an existing Updatarr installation is
not covered by the backup plan.

## Backups and Baseline

Record file hashes and permissions for any existing Updatarr configuration and
state. If an Updatarr database exists, create a consistent SQLite backup and
verify `PRAGMA integrity_check` in a disposable path. Record—not change—the
Octopi notifier autostart file, Octopi process, PackageKit state and both
Updatarr user-unit enablement states.

Collect a fresh read-only native, foreign-package, Flatpak, firmware and
toolchain inventory using the fixed trusted probes. This becomes the comparison
baseline; it is not permission to refresh metadata or install anything.

## Approved Pilot Sequence

1. Verify the package signature, hash, package identity, file list, declared
   dependencies and AGPL license before pacman sees the file.
2. Install only the reviewed package after the separate package-install
   approval. Confirm installation did not enable or start either Updatarr user
   service and created no XDG autostart entry.
3. Create an owner-only configuration with a unique local password,
   `127.0.0.1` binding, exact loopback origin/host and live read-only provider
   mode. Keep every execution adapter disabled.
4. Start the core manually, not through an enabled startup owner. Confirm one
   unprivileged process, the expected executable and loopback-only listener.
5. Sign in locally. Confirm API version 1, the packaged browser application,
   honest source states and no available install/update control.
6. Run one read-only check. Compare exact source identities, counts, versions,
   disabled origins and ownership with the fresh native-tool results. Unknown,
   unavailable and unsupported states must remain distinct.
7. Confirm the package database, Flatpak remotes/masks, firmware settings,
   trust configuration, Octopi notifier, user services and autostart files are
   unchanged. Confirm no privileged helper or Polkit rule was installed.
8. Stop the manual core and prove no Updatarr process or listener remains.

Any mismatch, write attempt, duplicate notifier, unexpected listener or stale
success claim ends the pilot and starts rollback.

## Rollback

Stop only the manually started Updatarr process. Remove the reviewed Updatarr
package through pacman after separate approval; do not remove dependencies that
are used elsewhere. Preserve the pilot database, logs and configuration for
diagnosis unless the owner explicitly approves their removal.

Verify packaged files are gone, no Updatarr process/listener/unit link exists,
and the Octopi notifier and all other updater state still match the recorded
baseline. If pre-existing Updatarr state was moved, restore it from the tested
backup and recheck permissions and SQLite integrity.

## Evidence Required to Pass

- exact approvals and timestamps;
- artifact identity, hash and signature verification;
- before/after package, process, listener, service and autostart records;
- native-tool and Updatarr inventory comparison;
- proof that execution controls remained disabled;
- state/config permissions and database integrity; and
- completed stop and rollback checks.

A passed read-only pilot would not authorize service enablement, tray
migration, notifier replacement or the first live software mutation.
