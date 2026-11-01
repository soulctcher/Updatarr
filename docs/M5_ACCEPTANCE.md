# M5 acceptance

**Prepared:** 2026-10-29  
**Status:** accepted by the user on 2026-10-29

M5 packages the unprivileged application, gives the core and KDE tray one
supervised startup owner each, validates safe network settings and makes the
Octopi migration reversible. It does not install the package, enable a service,
change a notifier or remove software.

## Delivered

- Arch package metadata for the Python service, built browser files, icon,
  launcher, example configuration, user units and operator documentation.
- One core user unit and one graphical-session tray unit. The package enables
  neither and ships no competing XDG autostart entry.
- A tray that shows the core service's minimal user-only summary, opens the
  canonical web interface, exits cleanly if another tray holds the per-user
  lock and never stops the core when the tray exits.
- Production startup validation that requires a unique password, keeps the
  default listener on loopback, requires HTTPS for direct non-loopback use and
  rejects wildcard bind addresses, wildcard hosts and incomplete certificate
  settings.
- Reverse-proxy guidance that keeps the upstream on loopback and rejects rather
  than trusts forwarding headers.
- Separate install, startup, backup, restore, uninstall, Octopi comparison,
  notifier swap, rollback and optional removal procedures.
- A fail-closed migration assessment: coverage, persistence, one tray, one
  notifier and rollback must all pass.
- A subdued rail footer showing the application version and milestone build
  directly below the Safe Preview Build notice.
- Viewport-level hover/focus information panels that open to the right of the
  pointer, remain stationary while entered, show their complete content when
  space permits and stay above every other interface layer.
- Safety Checklist badges that are interactive only when Updatarr has a real
  action destination. Passed and informational states remain plain badges;
  actionable Needs Attention badges lead to the relevant Updatarr control.
- Title-case interface headings with official acronym and product casing;
  actions, statuses and explanatory copy remain in sentence case.
- A simpler Appearance section without the redundant Ultraviolet preview card.

## Safety result

The review package was built only in disposable directories and was not
installed into the host system. No service, graphical startup entry or user
lingering was enabled. Octopi and its notifier were not changed or removed.
PackageKit and every update-source backend remain outside the removal scope.
The staged drill uses disposable directories and fixtures.

## Separate approvals still required

- install the reviewed Updatarr package;
- enable or disable the core and tray user units;
- disable or restore the Octopi notifier;
- remove Octopi;
- remove a stale Pamac launcher.

One approval does not imply any other item.

## Acceptance gate

- [x] Staged package build, file inventory and uninstall preservation passed.
- [x] Login/reboot unit behavior and single-notifier rollback drill passed with
      fixtures; live host verification remains gated.
- [x] Complete automated checks and independent review passed.
- [x] User accepts M5 and authorizes the next milestone.

Exact package, runtime, test and review evidence is recorded in
[M5 validation](research/m5-validation.md) and the
[independent acceptance review](research/m5-independent-review.md).
