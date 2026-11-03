# Arch installation and recovery

These instructions describe the M7 local candidates. The user authorized the
reviewed RC3 follow-up (`updatarr 0.6.0-2`) for signing, local installation and
bounded manual read-only testing on 2026-11-03. Service enablement remains a
separate approval decision in
[MILESTONES.md](../../MILESTONES.md).

> **RC2 is rejected:** Do not reinstall or enable RC2. The reviewed RC3
> follow-up preserves `PrivateTmp=true` and corrects its trusted executable
> check. The manual packaged service and tray checks passed on 2026-11-03.
> Keep both RC3 user units disabled at login until the owner separately approves
> enablement.

## Before installation

1. Build the browser with the locked npm inputs, run
   `scripts/build_source_archive.sh`, and confirm its checksum matches the
   PKGBUILD. The archive is the only application source consumed by makepkg.
2. Build and inspect the package in a clean Arch build environment.
3. Review the file list with `pacman -Qlp updatarr-0.6.0-2-any.pkg.tar.zst`.
4. Confirm that it contains two user units and no enabled-service links, XDG
   autostart entry, privileged helper or Polkit rule.
5. Copy `/usr/share/doc/updatarr/updatarr.env.example` to
   `~/.config/updatarr/updatarr.env`, set a unique password and make the file
   readable only by your user.

The local M7 PKGBUILD builds from a deterministic, checksummed source archive.
The archive contains the browser files produced by the already-verified locked
frontend build. A published release still needs an authenticated release source
and a selected redistribution license.

The user-unit directory and state-directory behavior require systemd 254 or
newer; current Arch satisfies that requirement.

## Separate approval: install the package

After that approval, install the reviewed package with the normal Arch package
tool. Installation places files under `/usr`; it must not start Updatarr,
enable either user unit, change Octopi or edit the user's configuration.

## Separate approval: enable startup

After configuration and a successful manual start, the approved action is:

```text
systemctl --user enable --now updatarr.service
systemctl --user enable --now updatarr-tray.service
```

The core belongs to the user service manager. The tray belongs to the graphical
session. Do not also create an XDG autostart file. Quitting the tray does not
stop the core.

Check the actual result rather than assuming enablement worked:

```text
systemctl --user is-enabled updatarr.service updatarr-tray.service
systemctl --user is-active updatarr.service updatarr-tray.service
systemctl --user status updatarr.service updatarr-tray.service
```

Sign out and back in before recording persistence as passed. Reboot and repeat
the checks before recording reboot persistence as passed. Verify that one tray
icon appears and that its count matches the signed-in Overview.

## Stop or disable without uninstalling

This is another service-setting change and needs its own approval:

```text
systemctl --user disable --now updatarr-tray.service
systemctl --user disable --now updatarr.service
```

Disabling the tray first preserves access to any core work already in progress.
Do not kill the core during an update run.

## Backup and restore

Stop new work, then use SQLite's backup operation rather than copying a live
database file. The packaged service keeps its database in
`$XDG_STATE_HOME/updatarr`, which defaults to `~/.local/state/updatarr`; use the
actual XDG state path rather than assuming the default. Preserve
`~/.config/updatarr/updatarr.env` with mode `0600` and record the package version
and checksum. A backup counts only after it opens and passes an integrity check
in a disposable directory.

To recover a bad upgrade, stop the user units, preserve logs and the current
database, reinstall the last compatible package, restore the tested database
and configuration, and start the core manually. Confirm the Overview and update
source states before re-enabling automatic startup.

## Uninstall

Disable the user units before uninstalling the package. Package removal must
remove only package-owned files under `/usr`; it must leave the user's database,
configuration, logs and backups for an explicit later cleanup decision.

Uninstalling Updatarr does not reinstall or re-enable Octopi. Restore the prior
notifier first if Updatarr had replaced it, using the recorded migration state
and [rollback procedure](OCTOPI_MIGRATION.md).
