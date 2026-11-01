# ADR 0001: Local service with a canonical web interface

- **Status:** accepted
- **Date:** 2026-10-23

## Context

Updatarr must be manageable like Sonarr and Radarr in a browser while retaining
KDE tray integration. Implementing independent desktop and web products would
duplicate policy, create inconsistent state and enlarge the security surface.

## Decision

Use one unprivileged long-lived Updatarr service as the application authority.
It serves one responsive browser client and a versioned interface consumed by a
thin KDE tray/launcher. A future desktop window may host the same web interface
but does not receive separate domain logic.

Default network binding is loopback-only. Non-loopback access is explicit,
authenticated and HTTPS-only, either directly or through a configured trusted
TLS-terminating proxy.

## Consequences

- Domain behavior and task state have one owner.
- Desktop and remote clients see consistent data.
- Browser security and service supervision become first-class requirements.
- The product is KDE-integrated rather than a wholly native Qt GUI.
- Offline desktop use depends on the local service, so startup and recovery must
  be reliable and well explained.

## Alternatives rejected

- **Separate Qt and web clients with duplicated logic:** too much drift and test
  surface.
- **Root web daemon:** unacceptable network-to-root exposure.
- **Desktop-only application:** does not satisfy remote browser management.
