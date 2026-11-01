# Updatarr architecture and security research

**Research date:** 2026-10-23  
**Scope:** Pre-implementation research for the Python service, TypeScript SPA, browser security boundary, Polkit integration, Arch packaging, systemd user service, and KDE tray companion.  
**Source policy:** Official specifications, project documentation, and first-party platform documentation only.

## Executive recommendation

Use a **single-process FastAPI service** as Updatarr's unprivileged authority, backed by SQLite with explicit migrations. Build a **React + TypeScript SPA with Vite** and package its static production output with the Python application so the UI and `/api/v1` share one origin. Use normal versioned HTTP requests for commands and **reconnectable server-sent events (SSE)** for task progress; retain WebSockets only if a genuinely bidirectional use case emerges.

Run the service as a user unit and use a separate graphical-session companion for Plasma notifications, StatusNotifierItem integration, and confirmation on the managed computer. A remote browser may inspect, configure, search, and create a frozen update plan, but every software change should enter `awaiting-local-confirmation` until a person at the managed KDE session confirms it. Root-required plans then enter `awaiting-authorization` and initiate Polkit. This follows from Polkit's process/session subject model; Polkit does not authenticate the human operating a remote browser, and unprivileged package/build operations can still execute hostile code with user-account access.

No exact dependency versions, authentication bootstrap flow, or unattended-update policy should be frozen from research alone. Phase 0 must prototype and threat-model those decisions against the actual EndeavourOS host.

---

## 1. Verified facts

This section records what the cited platforms and specifications provide. It is not itself a final Updatarr design decision.

### 1.1 Python service foundation

- FastAPI is based on OpenAPI and JSON Schema, supports typed request/response validation through Pydantic, integrates security schemes into the API definition, and supports WebSocket endpoints with normal dependency, cookie, header, and security handling. [FastAPI features](https://fastapi.tiangolo.com/features/) · [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- Current FastAPI provides first-party `EventSourceResponse` and `ServerSentEvent` support. Events can carry `event`, `id`, and `retry`; a reconnecting client can send `Last-Event-ID`; the implementation emits keep-alive comments and anti-buffering/no-cache headers. [FastAPI SSE guide](https://fastapi.tiangolo.com/tutorial/server-sent-events/) · [FastAPI SSE API](https://fastapi.tiangolo.com/reference/sse/)
- The HTML standard defines `EventSource` as a one-way HTTP event channel and defines event IDs and reconnection behavior. [WHATWG Server-sent events](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- FastAPI/Uvicorn do not trust forwarded host, scheme, or client information merely because those headers are present. Trusted proxy addresses must be configured before interpreting `X-Forwarded-*`; a proxy path prefix can be represented with `root_path`. [FastAPI behind a proxy](https://fastapi.tiangolo.com/advanced/behind-a-proxy/)
- Python's subprocess API recommends argument sequences and does not invoke a shell by default. `asyncio.create_subprocess_exec()` supports asynchronous process I/O; shell invocation makes the application responsible for safe quoting. [Python subprocess security](https://docs.python.org/3/library/subprocess.html#security-considerations) · [Python asyncio subprocesses](https://docs.python.org/3/library/asyncio-subprocess.html)
- Alembic is the migration tool associated with SQLAlchemy, and SQLAlchemy supports both Core/ORM and asyncio. An `AsyncSession` is mutable and must not be shared across concurrent tasks. [SQLAlchemy documentation](https://docs.sqlalchemy.org/en/20/) · [SQLAlchemy session concurrency](https://docs.sqlalchemy.org/en/20/orm/session_basics.html#is-the-session-thread-safe-is-asyncsession-safe-to-share-in-concurrent-tasks) · [Alembic documentation](https://alembic.sqlalchemy.org/en/latest/)
- SQLite WAL permits concurrent readers and a writer, but only one writer at a time and all users of the database must be on the same host. SQLite also documents a WAL-reset corruption bug fixed in SQLite 3.51.3 and selected backports, which makes the deployed SQLite version relevant if WAL is enabled. [SQLite WAL](https://www.sqlite.org/wal.html)

### 1.2 TypeScript SPA foundation

- React has documented TypeScript support, including typed component props and state. [React with TypeScript](https://react.dev/learn/typescript)
- Vite's production build emits deployable static assets; `vite preview` is explicitly a local preview tool, not a production server. [Vite production build](https://vite.dev/guide/build) · [Vite static deployment](https://vite.dev/guide/static-deploy.html)
- React Router's Data mode provides routing, data loading, actions, pending states, and error boundaries while retaining control of the bundler and server boundary. [React Router modes](https://reactrouter.com/start/modes) · [React Router custom integration](https://reactrouter.com/start/data/custom)
- TanStack Table is headless: it supplies typed sorting, filtering, pagination, selection, and related table state while leaving markup and visual design to the application. Its documentation distinguishes server-side data processing from rendering virtualization. [TanStack Table](https://tanstack.com/table/latest) · [client/server processing](https://tanstack.com/table/latest/docs/guide/client-side-vs-server-side) · [virtualization](https://tanstack.com/table/latest/docs/framework/react/guide/virtualization)
- TanStack Query manages asynchronous server-state fetching, caching, invalidation, and mutations. [TanStack Query overview](https://tanstack.com/query/latest)

### 1.3 Browser authentication, sessions, and request integrity

- A web origin is the scheme/host/port tuple. Serving SPA and API from one origin lets the browser's same-origin policy operate without a permissive CORS configuration. [Same-origin policy](https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Same-origin_policy)
- Starlette's `TrustedHostMiddleware` rejects requests whose `Host` is not in the configured allowlist. [Starlette middleware](https://www.starlette.io/middleware/#trustedhostmiddleware)
- RFC 9110 requires an origin server to reject a misdirected request when the target URI does not match the connection context; the RFC specifically notes routing around security filters and cache poisoning as risks. [RFC 9110 section 7.4](https://www.rfc-editor.org/rfc/rfc9110.html#section-7.4)
- Forwarding headers are not intrinsically trustworthy because clients and intermediaries can add or modify them. [RFC 7239 section 8.1](https://www.rfc-editor.org/rfc/rfc7239.html#section-8.1)
- OWASP recommends opaque session identifiers in cookies with `Secure`, `HttpOnly`, and explicit `SameSite`; server-side expiry and invalidation remain necessary. It warns against storing authentication tokens or session IDs in `localStorage` or `sessionStorage`. `SameSite` is defense in depth rather than a replacement for CSRF protection. [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- OWASP's CSRF guidance recommends protecting every state-changing request, using non-safe HTTP methods for mutations, checking source and target origins, and trusting an original host supplied by a proxy only when that proxy is trusted. Fetch Metadata such as `Sec-Fetch-Site` can add defense in depth but needs a fallback policy. [OWASP CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html) · [W3C Fetch Metadata](https://www.w3.org/TR/fetch-metadata/)
- RFC 6455 requires a WebSocket server to decide whether the request's `Origin` is acceptable; servers that do not validate it will accept cross-origin connections. [RFC 6455 section 4.2.2](https://www.rfc-editor.org/rfc/rfc6455.html#section-4.2.2)
- OWASP recommends Argon2id for password storage and recommends login throttling. [OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) · [OWASP Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html#login-throttling)

### 1.4 Polkit boundary

- Polkit is designed for a privileged **mechanism** to authorize an untrusted **subject**, normally through the system bus. The subject is a local process, Unix session, or system-bus name; `pkcheck` identifies it by PID plus process start time or by system-bus name. [polkit overview](https://polkit.pages.freedesktop.org/polkit/polkit.8.html) · [pkcheck](https://polkit.pages.freedesktop.org/polkit/pkcheck.1.html)
- Authentication agents are registered by local user sessions and are normally supplied by the desktop environment. A process outside a desktop session may have no graphical authentication agent. [polkit authentication agents](https://polkit.pages.freedesktop.org/polkit/polkit-agents.html)
- Policy distinguishes `allow_any`, `allow_inactive`, and `allow_active`. `auth_admin` requires an administrator; `auth_self` is documented as insufficient for most multi-user uses. [polkit action policy](https://polkit.pages.freedesktop.org/polkit/polkit.8.html)
- `ALLOW_USER_INTERACTION` should be used only when the check originates from a user action and may block for a long time while authentication occurs. [PolkitAuthority](https://polkit.pages.freedesktop.org/polkit/PolkitAuthority.html)
- A retained `AUTH_SELF_KEEP` or `AUTH_ADMIN_KEEP` authorization applies to the same action and subject for a brief period even if detail values supplied to a later check differ. Polkit warns against retained authorization when rules depend on those per-request values. [polkit retained authorization](https://polkit.pages.freedesktop.org/polkit/polkit.8.html)
- `pkexec` does not validate arguments passed to its target program and warns that a program with retained or implicit authorization must never trust user input. [pkexec](https://polkit.pages.freedesktop.org/polkit/pkexec.1.html)

**Necessary inference:** a browser operator on another computer does not become the Polkit subject. If the long-running Updatarr service asks for authorization, Polkit sees that service process/session, not the remote human. A remote click can also create an unexpected prompt on the managed desktop. Therefore browser authentication and Polkit authorization solve different identity problems and must not be treated as interchangeable.

### 1.5 Arch packaging, user services, and Plasma integration

- Arch packages are built through `PKGBUILD`/makepkg, should use normal filesystem locations, and should list direct dependencies instead of relying on transitive ones. Application data belongs under `/usr/share/<package>`; packaged Python projects with `pyproject.toml` normally build a wheel with `python-build` and install it into the package root with `python-installer`. [Arch package guidelines](https://wiki.archlinux.org/title/Arch_package_guidelines) · [Arch Python package guidelines](https://wiki.archlinux.org/title/Python_package_guidelines)
- Packaged systemd user units belong in the distribution user-unit directory reported by `pkg-config systemd --variable=systemduserunitdir`; per-user configuration has precedence. [systemd unit locations](https://www.freedesktop.org/software/systemd/man/latest/systemd.html#Directories)
- `default.target` is the general user-manager target. `graphical-session.target` is active while a graphical session runs, and graphical-only services should use `PartOf=graphical-session.target` so they stop with it. [systemd special user units](https://www.freedesktop.org/software/systemd/man/latest/systemd.special.html#Units%20managed%20by%20the%20user%20service%20manager)
- Without lingering, a user's manager normally exists while the user has a login session. Enabling lingering starts it at boot and keeps it after logout, allowing long-running user services. [loginctl lingering](https://www.freedesktop.org/software/systemd/man/latest/loginctl.html#enable-linger%20USER%E2%80%A6)
- The XDG autostart specification starts `.desktop` entries after desktop login and lets a user suppress a system-wide entry with a same-named personal entry containing `Hidden=true`. systemd can generate user units for XDG autostart entries, but documents limits to that generator and recommends `X-systemd-skip=true` when an application provides its own unit. [XDG Autostart](https://specifications.freedesktop.org/autostart/latest/) · [systemd desktop integration](https://systemd.io/DESKTOP_ENVIRONMENTS/)
- KDE Frameworks 6 provides `KStatusNotifierItem`, implementing the D-Bus StatusNotifierItem protocol with `Passive`, `Active`, and `NeedsAttention` states, activation, menus, overlays, and tooltips. KDE recommends icon-theme names over pixmaps. [KStatusNotifierItem API](https://api.kde.org/kstatusnotifieritem.html) · [StatusNotifierItem specification](https://specifications.freedesktop.org/status-notifier-item/latest-single/)
- KDE's HIG advises that tray icons should be opt-in, normally visible only for abnormal status, and supplemented with notifications or deeper desktop integration where useful. [KDE status-change guidance](https://develop.kde.org/hig/status_changes/)

---

## 2. Recommendations for Updatarr

These are design recommendations derived from the verified facts. They should guide Phase 0 prototypes but are not yet irreversible implementation commitments.

### 2.1 Recommended runtime split

| Component | Responsibility | Privilege/lifecycle |
| --- | --- | --- |
| `updatarr.service` | Same-origin SPA/API hosting, inventory, provider coordination, scheduling, policy, immutable plans, audit history, event stream | Unprivileged systemd user service; one process; normal user-manager lifecycle |
| `updatarr-tray.service` | Plasma StatusNotifierItem, notifications, open-browser action, and review/approval handoff for pending privileged plans | Unprivileged; bound to `graphical-session.target`; never the source of business truth |
| `updatarr-helper` | Minimal system-bus mechanism for a closed set of root-required operations | Privileged only while servicing typed requests; independently authorizes and validates every request |

The service should remain a **single process** initially. SQLite has a single-writer model, native transactions need one coordinator, and multiple web workers would introduce avoidable ownership and event-broadcast complexity. Provider commands may run in bounded child processes without multiplying the web authority.

### 2.2 Recommended Python foundation

- FastAPI + Uvicorn/its supported server path for HTTP, OpenAPI, typed schemas, authentication dependencies, and SSE.
- Pydantic models at the transport boundary, mapped explicitly to domain objects; do not let HTTP models become the domain model by accident.
- SQLAlchemy 2 + Alembic for persistence and migrations, with one database session per request/task. Direct `sqlite3` remains a viable smaller alternative to compare in Phase 0.
- SQLite stored on a local filesystem in the user's state-data location. Do not place it on NFS or another network filesystem. Enable WAL only after verifying the host carries a fixed SQLite build and after crash/recovery tests; one-process Updatarr may not need WAL initially.
- `asyncio.create_subprocess_exec()` with fixed executable paths and argument arrays. Do not accept shell strings, arbitrary environment maps, or client-supplied executable paths.
- A bounded job supervisor that records state transitions before launching external work and reconciles unfinished jobs after restart.

### 2.3 Recommended SPA foundation

- React + TypeScript, built by Vite into static files included in the Arch package.
- React Router in Data mode: this is a client-rendered authenticated admin UI, so server-side rendering adds little value and another runtime is unnecessary.
- TanStack Query for API server-state and mutation invalidation.
- TanStack Table for Updatarr's dense, sortable, filterable package views; add TanStack Virtual only where realistic package inventories show a rendering bottleneck.
- A small, original token/component layer using semantic HTML and CSS custom properties. Do not adopt another *arr application's source assets or a visual framework that prevents the Updatarr identity.

The production service should serve the Vite build itself. Do not ship a Node production server, and never use `vite preview` in the installed application.

### 2.4 HTTP and progress contract

Use `/api/v1/...` from the first prototype. Version the JSON and event payloads independently from the desktop package version, publish an OpenAPI document, and generate or validate TypeScript request/response types from that contract in CI.

Prefer this command/event pattern:

1. Browser submits a state-changing `POST` with its session and CSRF proof.
2. Server validates the requested typed operation and returns `202 Accepted` plus a `task_id` or returns a completed result.
3. Browser observes `/api/v1/events` over authenticated SSE.
4. Every durable event includes `event_id`, `schema_version`, `task_id`, `sequence`, `kind`, server timestamp, and a typed payload.
5. Server keeps a bounded durable event tail. On reconnect, `Last-Event-ID` resumes when available; otherwise the server emits a reset marker and the client reloads an authoritative task snapshot.
6. Cancellation is a separate authenticated command and succeeds only at a provider-declared safe point.

SSE matches Updatarr because progress is predominantly server-to-browser, works over ordinary HTTP, and has standardized reconnection. Use WebSockets only if Phase 0 identifies required full-duplex behavior that POST + SSE cannot express. If WebSockets are added, apply the same session, host, and exact-origin checks as HTTP.

### 2.5 Authentication and exposure modes

Treat loopback as reduced exposure, **not as proof of user identity**: other same-user processes and browser-origin attacks can still reach a loopback TCP listener.

Recommended modes:

| Mode | Listener | Authentication and transport |
| --- | --- | --- |
| Local default | `127.0.0.1` and/or `::1` only | Phase 0 must choose between mandatory login and a secure local bootstrap/session scheme; all mutation endpoints still require CSRF/origin protection |
| Trusted LAN/VPN | Explicit configured address | Mandatory login; HTTPS either in Updatarr or through a configured trusted reverse proxy |
| Public Internet | None in MVP | Unsupported until separately threat-modeled, penetration-tested, and documented |

Required controls regardless of mode:

- Serve UI and API from one origin; disable CORS by default.
- Maintain an explicit allowed-host list including configured port behavior. Reject unknown hosts before routing.
- Accept forwarded client, host, scheme, and URL-base information only from exact configured proxy addresses. The edge proxy must replace, not append to or pass through, untrusted inbound forwarding headers.
- Store opaque session records server-side. Put only the random session identifier in an `HttpOnly`, explicit `SameSite` cookie; use `Secure` whenever the effective origin is HTTPS; omit `Domain`; scope `Path` to the configured URL base. Rotate at login and credential change; apply idle and absolute expiry; revoke server-side on logout and when authentication settings change.
- Never place session IDs, bearer credentials, password-reset material, or reusable API keys in URLs or Web Storage.
- Hash a locally stored password with Argon2id and a unique salt, using parameters benchmarked on the target machine. Rate-limit by account and source, log failures without logging submitted secrets, and provide recovery that requires local filesystem/console control.
- Use a framework-backed synchronizer CSRF token for all mutations. Also require an exact allowed `Origin` when present, reject `Origin: null` for mutations, reject `Sec-Fetch-Site: cross-site`, and have a documented safe fallback for clients without Fetch Metadata.
- Keep `GET`, `HEAD`, and `OPTIONS` side-effect free.
- Send a restrictive Content Security Policy and other standard security headers. Render provider output, logs, package descriptions, release notes, and SVG/images as untrusted content; do not inject raw HTML.
- Authenticate SSE before streaming and ensure task events are authorized for the current Updatarr account/session.

### 2.6 Reverse proxy and URL base

Support a configured external origin and URL base, for example `https://host.example/updatarr`, without deriving security decisions from arbitrary request headers. Generate links and cookie paths from this canonical configuration. Document one tested reverse-proxy configuration during implementation that covers:

- HTTPS termination;
- exact `Host` preservation/rewriting;
- replacement of forwarding headers;
- SSE buffering disabled and connection timeouts suitable for keep-alives;
- request/body/time limits;
- the configured Updatarr listener remaining unreachable from untrusted interfaces.

Proxy support is an operational feature, not an excuse to make `--forwarded-allow-ips=*` or an allow-all host list the default.

### 2.7 Confirmation on this computer and administrator-permission flow

Use this state model for every executable plan:

```text
draft -> checking -> frozen -> awaiting-review -> awaiting-local-confirmation
                                             |-> awaiting-authorization? -> ready-for-execution -> consumed
                                             |-> expired
                                             `-> invalidated
```

Execution creates an update run whose verified final state is `succeeded`,
`partially-succeeded`, `failed`, `cancelled`, `needs-reboot`, or
`needs-manual-recovery`.

Recommended security properties:

- The browser may build and freeze a plan, but a remote request must not start any software mutation or directly produce a surprise Polkit prompt.
- The tray/local approval UI fetches the exact frozen plan, displays packages, versions, source, dependencies, size/unknowns, risk flags, and irreversible effects, and requires an explicit local action.
- The helper authorizes the **local caller** and then independently checks the action ID, caller UID, plan digest, short expiry, system-state generation, allowed package identifiers, and permitted operation shape.
- The helper accepts typed data, never arbitrary commands, shell fragments, unrestricted paths, environment injection, or a client-chosen executable.
- Use narrow action IDs by capability, such as native package update, firmware update, and boot maintenance. Default policy should be `allow_any=no`, `allow_inactive=no`, `allow_active=auth_admin`.
- Do not use `auth_admin_keep` for update-sensitive actions: retained permission can cover later requests with different details. If a future action is proven safe to cache, give it a separate action ID and threat model.
- Keep AUR acquisition, diff/review, and build unprivileged, but treat build scripts as arbitrary code with user-account access until a tested isolation design proves otherwise. Require local confirmation before build, separate the build process from Updatarr credentials/state, and elevate only the final validated installation where required.
- Record the HTTP user/session, plan digest, local approving Unix identity/session, Polkit action, helper validation result, process exit status, and result check in the audit trail without recording credentials.

An unattended-update feature would be a different authorization model. It would need a tightly bounded administrator-installed policy, explicit package/source constraints, independent audit/recovery design, and separate user approval; it must not be implemented by weakening the interactive action.

### 2.8 systemd and Plasma behavior

- Install packaged user units into systemd's distribution user-unit directory and let users override them in their own configuration.
- Start the core service under the normal user-manager lifecycle. Do **not** silently enable lingering. Without lingering, LAN availability ends with the user's login lifecycle; with an explicit lingering opt-in, read-only and planning functions may remain available after logout but privileged plans remain pending until an eligible local session/agent exists.
- Start/stop the tray with `graphical-session.target`; do not duplicate it in both a user unit and XDG autostart. Use XDG autostart only if the Phase 0 Plasma test proves the native user-unit integration insufficient.
- Implement the tray with the StatusNotifierItem protocol. Prefer theme icon names and a `SystemServices` category.
- Proposed state mapping:

  | Updatarr state | StatusNotifierItem state |
  | --- | --- |
  | Healthy, no updates ready to review | `Passive` |
  | Updates available or task running | `Active` |
  | Failure, update source unavailable or needing refresh, reboot required, or confirmation on this computer pending | `NeedsAttention` |

- Primary activation opens the canonical web URL. The menu may contain Open Updatarr, Check Now, Review Updates, and Quit Tray. Quitting the tray must not stop the service or an update run.
- Follow KDE's guidance by making always-visible tray presence configurable and relying on restrained notifications for updates that need attention. Phase 0 should resolve this with the product requirement for a persistent notifier.

### 2.9 Arch package layout

Build one Arch package initially, with an optional later split only if dependency weight justifies it:

- build the Vite SPA during `build()` and include immutable assets under `/usr/share/updatarr/web` or inside the Python package;
- build the Python wheel with the declared PEP 517 backend and install it using Arch's standard Python packaging flow;
- install launchers/icons under the normal `/usr/share` locations;
- install user units through systemd's discovered user-unit directory;
- install the Polkit action and privileged mechanism as package-owned system files;
- keep mutable config, state, cache, and logs out of `/usr/share` and follow XDG locations for the unprivileged user;
- list Python, Qt/KF6, Polkit, package-manager, and build dependencies directly in the `PKGBUILD` as applicable;
- test clean build, install, upgrade, downgrade/migration refusal, and uninstall in an isolated Arch environment before host deployment.

Do not vendor a private Python environment into the installed package without a documented reason. Pin application dependencies for development/CI reproducibility, but package against compatible Arch system libraries where feasible and verify them continuously because Arch is rolling release.

---

## 3. Decisions deferred to Phase 0

The following questions require prototypes, host inspection, benchmarks, or a fuller threat model. Research does not settle them:

1. **Exact supported versions:** Record current Arch versions of Python, FastAPI, Uvicorn, Pydantic, SQLAlchemy/Alembic, SQLite, Node, TypeScript, React, Vite, Qt 6, KDE Frameworks, and Polkit; then pin tested compatibility ranges. In particular, verify SQLite contains the documented WAL-reset fix before considering WAL.
2. **Persistence layer:** Compare SQLAlchemy 2 + Alembic with a smaller explicit SQL repository. Choose based on migration safety, typed-domain isolation, testability, and package availability—not familiarity alone.
3. **Local authentication bootstrap:** Decide whether loopback requires the same password login as LAN, a one-time locally displayed setup secret, or another mechanism. Prove resistance to cross-origin loopback requests, DNS rebinding, another local Unix user, session theft, and lost-password recovery.
4. **TLS ownership:** Decide whether MVP terminates TLS itself or formally supports HTTPS only through a trusted reverse proxy for LAN/VPN use. Test certificate renewal and effective-origin/cookie behavior.
5. **SSE through target proxies:** Test reconnect, `Last-Event-ID`, proxy buffering, idle timeouts, service restart, event loss, and long-running native updates. Adopt WebSockets only if a measured requirement remains.
6. **API compatibility policy:** Define deprecation windows, event-schema compatibility, OpenAPI client generation, and behavior when tray/service package versions temporarily differ during an upgrade.
7. **Polkit mechanism transport:** Prototype a root-owned D-Bus mechanism versus a small fixed-purpose `pkexec` helper. Prefer D-Bus if it gives stronger caller identity, typed methods, lifecycle, and cancellation; reject any design that accepts arbitrary argv.
8. **Plan sealing:** Define canonical serialization, digest algorithm, expiry, state-generation inputs, replay prevention, and helper-side revalidation. Test TOCTOU cases involving pacman databases, mirror metadata, package files, and simultaneous external package-manager activity.
9. **Local approval UX:** Determine whether the tray can safely present the full plan or should open a local-only approval page/native dialog. Ensure a remote actor cannot prompt-spam the desktop and a local user cannot approve a changed plan.
10. **Unattended operations:** Keep out of MVP unless separately specified. If requested later, design a non-interactive policy model rather than reusing interactive Polkit grants.
11. **Service lifecycle:** Decide whether normal operation starts at login, on first browser/launcher activation, or continuously via an explicit linger option. Verify actual Plasma/systemd target behavior on the host.
12. **Tray implementation language:** Spike Python Qt/KDE bindings against a minimal C++/Qt 6 KF6 companion. Choose the smallest reliably packaged implementation that supports StatusNotifierItem, KNotifications, single-instance behavior, and Wayland without private APIs.
13. **KDE presence policy:** Reconcile the requested single tray notifier with KDE's recommendation that tray icons be opt-in and abnormal-state-oriented. Validate discoverability when `Passive` items are hidden by Plasma.
14. **Packaging split:** Measure whether Qt/KF6 tray dependencies justify `updatarr` plus `updatarr-kde`, while preserving one supported installation path for this KDE-first product.
15. **Sandbox/hardening properties:** Test candidate systemd hardening settings against provider tools, user config, package databases, D-Bus, notifications, and subprocesses. Add only restrictions whose required access is understood and covered by tests.

## 4. Phase 0 acceptance evidence

Before implementation stack choices become committed decisions, capture at least:

- a same-origin FastAPI + built SPA slice under both `/` and a non-root URL base;
- authenticated HTTP and SSE reconnection tests through the chosen reverse proxy;
- rejected unknown `Host`, disallowed `Origin`, cross-site mutation, missing/invalid CSRF token, and spoofed forwarded-header tests;
- session rotation, expiry, logout revocation, password change, brute-force throttling, and recovery tests;
- a frozen-plan demo that remains read-only remotely, becomes executable only after an explicit local action, and is rejected after expiry or relevant host-state change;
- Polkit tests for active local, inactive local, logged-out/linger, SSH, and no-agent cases;
- helper fuzz/property tests proving arbitrary executable, argument, path, environment, and plan mutation input cannot escape the typed operation set;
- systemd login/logout/restart/crash tests and proof that quitting the tray does not stop the service;
- Plasma/Wayland tray, notification, theme-icon, browser-open, and duplicate-instance tests;
- clean Arch package build/install/upgrade/uninstall validation with every installed path owned by the package or intentionally created as user state.

Passing these checks should be the gate for replacing the provisional architecture language in `PLAN.md` with pinned implementation decisions.
