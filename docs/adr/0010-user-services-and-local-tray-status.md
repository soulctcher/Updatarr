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

Do not ship an XDG autostart entry. This avoids two startup owners for the tray.
Quitting or restarting the tray never stops the core.

## Consequences

- Package installation, service enablement and notifier migration remain
  separate operator decisions.
- The status file contains no credentials, software names, paths or plans and
  disappears with the user runtime directory.
- Tray status can briefly lag the service by its five-second polling interval.
- A future richer tray action needs an authenticated local channel and a new
  security review; it must not expand this file into a command channel.
