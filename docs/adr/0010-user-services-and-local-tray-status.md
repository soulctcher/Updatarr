# ADR 0010: User services and a restricted tray status file

- **Status:** accepted with M5 on 2026-10-29
- **Date:** 2026-10-29

## Context

The core must survive a tray restart, the tray must stop with the graphical
session, and neither process should run as an administrator. The tray needs the
same summary as the browser without storing a browser password or duplicating
update-source logic.

## Decision

Package two systemd user units but enable neither during installation. The core
uses `default.target`; the tray uses `graphical-session.target`. The service
writes only its current summary to a user-only file under `XDG_RUNTIME_DIR`.
The tray polls that file, opens the canonical browser interface and holds a
per-user lock so a second tray exits cleanly.

The tray may store its own display preferences in
`$XDG_CONFIG_HOME/updatarr/tray-settings.json`. That owner-only file controls
only how often the tray rereads recorded status, when it shows desktop
notifications and how long those notifications remain visible. It is not an
update-source setting, contains no credentials and cannot request or approve an
update.

Do not ship an XDG autostart entry. This avoids two startup owners for the tray.
Quitting or restarting the tray never stops the core.

## Consequences

- Package installation, service enablement and notifier migration remain
  separate operator decisions.
- The status file contains no credentials, software names, paths or plans and
  disappears with the user runtime directory.
- Tray status can briefly lag the service by the user's five-second to
  one-minute refresh interval.
- The icon uses muted red when recorded updates exist, muted green only after a
  recorded check finds none, and neutral gray before any check. Its tooltip
  carries the same meaning so status is not communicated by color alone.
- The tray menu can open a local settings dialog. Changing those settings does
  not contact an update source or change the core service.
- A future richer tray action needs an authenticated local channel and a new
  security review; it must not expand this file into a command channel.
