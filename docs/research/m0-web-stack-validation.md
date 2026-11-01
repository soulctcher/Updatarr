# M0 web-stack validation

**Date:** 2026-10-24  
**Scope:** local architecture proof only; no package-manager or host mutation

## Outcome

The provisional FastAPI + React/TypeScript/Vite + server-sent events stack has
passed its M0 vertical-slice validation and is ready for the user's final M0
decision. The proof serves the built single-page interface and `/api/v1`
from one process and one origin at both `/` and `/updatarr`. It uses no Node
production server.

The design uses three deliberately deep modules:

- the session-security **Module** exposes authentication, opaque session lookup,
  revocation and password change while hiding verifier and throttle details;
- the event-history **Module** exposes bounded replay after an event ID and
  hides sequence and eviction bookkeeping;
- the simulated check-task **Module** exposes start/observe behavior and hides
  ownership, progress publication and duplicate suppression.

FastAPI is the **Adapter** that maps those interfaces to same-origin HTTP and
SSE. The package-manager **Seam** is absent: M0 update results and activity are
fixed simulation data, and no executable or arbitrary command crosses the web
boundary.

## Target-host evidence

| Runtime or dependency | Version exercised |
| --- | --- |
| Node.js | 24.22.1 |
| npm | 12.2.1 |
| Python | 3.14.8 |
| FastAPI | 0.161.1 |
| Uvicorn | 0.54.0 |
| React / React DOM | 19.3.1 |
| TypeScript | 7.0.2 |
| Vite | 8.3.5 |
| React Vite plugin | 6.1.2 |

The frontend versions are exact project-local dependencies and are captured in
`web/package-lock.json`. `npm install` reported 25 packages audited and zero
known vulnerabilities. Existing host Python packages were used without a
system install. Reproducible Python packaging constraints remain required in
M1.

## Behavior proven

- minimal unauthenticated health response;
- loopback-only demonstration entry point;
- exact allowed Host and same-origin mutation checks;
- forwarded-header rejection because M0 configures no trusted proxy;
- HttpOnly, SameSite Strict opaque session cookie;
- session rotation, expiry, revocation, password-change invalidation, login
  throttling and managed-host-only recovery interface;
- CSRF token required independently of the session cookie;
- bounded event history, numeric IDs, reconnect replay and explicit reset when
  requested history has expired;
- one active simulated update check, including duplicate-start suppression;
- built assets and API under root and non-root URL bases;
- Settings-only theme selection with System plus 17 explicit profiles;
- no document-level horizontal overflow at 320, 390, 680, 681 and 1440 pixels.

## Visual critique

The production shell keeps the accepted *arr-family structure—persistent rail,
compact status bar, dense operational panels and tables—without copying a
specific product. Ultraviolet identifies selection and primary action, while
green, amber and red remain status-only. The five-step update path is the visual
signature. Desktop density is calm and scannable; the narrow layout converts
the rail to a fixed bottom navigation and the five-step path to a vertical
sequence. Theme selection appears only in Settings → Appearance.

Retained screenshots:

- `docs/design/screenshots/m0-overview-ultraviolet-desktop.png`
- `docs/design/screenshots/m0-settings-norse-desktop.png`
- `docs/design/screenshots/m0-overview-amoled-mobile.png`

## Boundaries and deferred work

This is proof, not a deployable release. Authentication is intentionally
in-memory, the visible password is demonstration-only, and scrypt avoids adding
a Python dependency during the M0 proof. M1 must add durable storage and a
target-host-benchmarked Argon2id verifier before any non-loopback use. HTTPS,
trusted-proxy configuration, persistent preferences, live update-source
adapters, local approval, Polkit, tray lifecycle and Arch package lifecycle are
not implemented here. Those later milestone gates remain closed.

## Exact verification commands

```text
npm --prefix web run check
npm --prefix web run build
python -m pytest -q tests/test_m0_modules.py tests/test_m0_web_slice.py
python -m pytest -q
```

Final result: the focused M0 module/web suite passed 16 tests and the complete
suite passed 119 tests. TypeScript checking, the Vite production build and
Python compilation also passed. Independent review initially found two medium
issues—request bodies were limited after buffering, and production theme/accessibility
coverage was insufficient. Both were fixed and regression-tested; the second
review passed with no critical, high or medium findings.
