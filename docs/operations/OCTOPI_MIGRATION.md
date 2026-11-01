# Octopi side-by-side migration and rollback

Updatarr does not remove Octopi or PackageKit. Each change below has a separate
approval gate. The safe default is to stop and leave the current setup intact.

## Evidence to record first

- installed Octopi package name and version;
- the exact Octopi notifier startup owner and whether it is active;
- every update source Octopi currently covers;
- Updatarr source states and counts after a fresh check;
- the commands or settings needed to restore the Octopi notifier;
- a tested copy of the current Octopi configuration or a record that it has no
  configuration to preserve.

## Side-by-side check

Run Updatarr and Octopi together only long enough to compare coverage. Do not
enable both notifiers for normal use. For each approved source, record whether
both tools report it, whether a failure stays visible and why any counts differ.
Package names alone are not enough: native packages remain one complete system
update group, and Flatpak scopes and turned-off sources remain distinct.

The migration assessment passes only when:

1. every approved update source is accounted for;
2. the Updatarr core and tray persist through a new login and reboot;
3. exactly one Updatarr tray is active;
4. Updatarr and the Octopi notifier are not active together; and
5. the prior notifier setup has been restored successfully in a rollback drill.

## Separate approval: stop the old notifier

After the side-by-side evidence passes, record the exact existing startup entry
and then disable only that notifier. Do not remove Octopi, PackageKit, pacman,
yay, eos-update, fwupd or any update-source backend. Sign out and back in, then
verify one active notifier and a current Updatarr check.

## Rollback drill

1. Stop or disable the Updatarr tray without stopping an active core update run.
2. Restore the recorded Octopi notifier startup setting.
3. Start a new graphical session.
4. Confirm exactly one Octopi notifier, confirm it performs its normal check and
   confirm Updatarr has not changed any update-source setting.
5. Reapply the reviewed Updatarr notifier setup only after recording the drill
   as passed.

A failed or incomplete rollback blocks migration.

## Separate approval: remove Octopi

Removing the Octopi package is optional and later than the notifier swap. First
repeat the coverage, persistence, one-notifier and rollback checks. Review the
package transaction before accepting it so update backends and unrelated tools
are not removed. Keep the exact reinstall package name and notifier restoration
steps in the migration record.

Removing a stale Pamac launcher is yet another separate decision. Its presence
does not authorize removal.
