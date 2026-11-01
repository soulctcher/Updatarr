# Updatarr architecture

**Status:** M0 through M6 accepted; publication and live actions remain gated  
**Authority:** [PLAN.md](PLAN.md) remains the product specification

## Architectural drivers

Updatarr has to reconcile four unusually strong constraints:

1. The browser experience should feel at home beside Sonarr and Radarr.
2. The service must unify state without pretending heterogeneous package
   systems have identical semantics.
3. A network-facing process must never become a general-purpose root command
   runner.
4. Arch repository consistency, package ownership and provider trust rules must
   be enforced centrally, not reconstructed independently by each screen.

The resulting architecture is a local-first unprivileged service with deep
domain modules, provider adapters at explicit seams, a responsive web client,
a thin KDE tray client and a separate fixed-operation privileged executor.

## System context

```text
Desktop browser ─┐
Mobile browser ──┼── HTTP + authenticated event stream ── Updatarr service
KDE tray ────────┘                                          │
                                                            ├─ State store
                                                            ├─ Provider adapters
                                                            ├─ Planner/policy
                                                            └─ Audit/task engine
                                                                    │
                          local authorization + immutable plan ─────┤
                                                                    ▼
                                                        privileged executor
                                                                    │
                        pacman / Flatpak system / fwupd / host-owned operations
```

The Updatarr service is the only application authority. Browser and tray
clients display its state; they do not own schedules, compute safe plans or
invoke providers directly.

## Deep modules and seams

### Inventory module

**Interface:** request a scan and read a versioned inventory snapshot with
provider health.  
**Hides:** concurrent probes, timeouts, normalization, stale-state rules,
ownership resolution, deduplication and persistence.

### Planning module

**Interface:** produce an immutable plan from an intent plus a specific
inventory snapshot; validate that plan immediately before execution.  
**Hides:** dependency grouping, native full-upgrade invariants, provider
ordering, holds, advisories, permissions, size confidence and invalidation.

The planning interface accepts typed identities, never executable strings.

### Policy module

**Interface:** evaluate or record provider enablement, defer, skip-version,
pause and advisory acknowledgement rules.  
**Hides:** identity matching, expiration, audit events and the difference
between display suppression and an executable provider hold.

### Task module

**Interface:** start one approved plan, observe structured progress and request
cancellation.  
**Hides:** state transitions, coordinator locks, subprocess lifecycle,
reconnection, safe cancellation points, crash reconciliation and redaction.

### Provider seam

A provider adapter implements discovery, inventory, update checking, search,
description, planning evidence and history for one ownership domain. Execution
is exposed only when the provider and host support it safely. Unsupported
capabilities are data, not exceptions disguised as success.

The external provider interface should remain smaller than the method list in
the product plan if implementation experience shows operations can be grouped.
Internal parsing and subprocess seams stay private to each adapter.

### State store module

**Interface:** transactional reads/writes of domain records and append-only
audit events through schema-versioned repositories.  
**Hides:** SQLite WAL, migrations, retention, idempotent imports, backups and
recovery details.

### Privileged execution seam

**Interface:** execute one supported operation from a validated, immutable,
short-lived plan envelope.  
**Hides:** Polkit authorization, trusted executable resolution, exact argument
construction, environment control and result reconciliation.

The executor rejects free-form commands, shell syntax, unexpected paths,
unknown operation types, stale plans and mismatched caller identity.

### Local approval module

**Interface:** present one frozen plan on the managed host and record an explicit
local confirmation or rejection.  
**Hides:** graphical-session identity, prompt throttling, plan-detail retrieval,
expiry and handoff to Polkit when privilege is required.

Every software mutation crosses this module, including AUR builds and other
user-level provider actions. Polkit is a subsequent step only for root-required
plans. Until a tested isolation design exists, an AUR build is treated as
arbitrary code with the user's access and remains disabled for live execution.

## Web interface

The implemented stack is one FastAPI process plus a React/TypeScript SPA built
with Vite and served as packaged static assets from the same origin. Use
`/api/v1` JSON commands and authenticated reconnectable SSE for progress.
WebSockets remain excluded unless a concrete bidirectional need emerges.
Frontend and Python dependencies are locked by the M1 project manifests. The
application uses an explicit SQLite repository instead of an object-relational
mapper. See
[ADR 0004](docs/adr/0004-provisional-web-technology-stack.md) and the
[SQLite decision](docs/adr/0007-explicit-sqlite-state-store.md).

Required server behaviors:

- loopback-only default binding;
- explicit LAN listener with authentication and HTTPS, direct or through a
  configured trusted TLS-terminating proxy;
- Host and Origin validation;
- server-side authorization and CSRF protection for mutations;
- bounded request bodies, pagination and stable error envelopes;
- URL-base and trusted reverse-proxy support;
- no sensitive inventory in unauthenticated health responses;
- compatibility version surfaced to browser and tray clients.

The current browser and service declare API version 1 during session creation
and restoration. The browser stops with a plain mismatch message rather than
continuing against an unknown contract.

## Deployment processes

The expected eventual process model is:

```text
updatarr service       one unprivileged user process; web/domain/provider work
updatarr tray          graphical session; notification, launcher, local approval
privileged executor    separately installed fixed-operation system facility
```

Use separate systemd user units provisionally: the core follows the user-manager
lifecycle; the tray is bound to `graphical-session.target`. Lingering is an
explicit opt-in, never silently enabled. Phase 0 must test login, logout,
lingering, Polkit agent availability and remote-use expectations before this
becomes accepted.

## Data and state

SQLite is the implemented local database. Stable identities include update source,
scope, origin/repository, item ID, architecture and branch/channel as
applicable. Inventory snapshots and transaction plans receive content hashes.
A plan becomes invalid when its relevant input state changes.

The browser never receives secrets it does not need. Password verifiers,
session records and recovery material are stored separately from provider logs
and are excluded from ordinary exports.

Schema 6 adds indexed, server-side inventory paging. The browser requests 100
records at a time and displays the complete recorded count, so a target-scale
inventory is neither rendered all at once nor silently cut off. Interrupted
runs retain immutable plan identity and reconcile without replay; only a
positive expected-version check can turn an interrupted run into success.

## Architectural invariants

- No native repository partial upgrade.
- No duplicate native transaction.
- No root web service, GUI, tray or AUR build.
- No arbitrary command interface across any seam.
- No state-changing action without current-state validation and an audit event.
- No executable software mutation without managed-host local confirmation.
- No assumption that a provider is healthy because it returned an empty list.
- No remote reachability by default.
- No second implementation of domain policy in the browser or tray.

## M1 implemented boundaries

- `InventoryCoordinator` owns one concurrent, cancellable read-only check and
  creates one immutable snapshot from partial per-source results.
- Provider adapters call only names in the closed trusted-probe registry. The
  browser cannot submit a command, path or argument.
- `StateStore` owns SQLite WAL mode, the atomic first migration, snapshots,
  task/event retention, audit history, preferences, Argon2id verifiers and
  hashed session identifiers.
- The FastAPI service owns authentication, authorization and the `/api/v1`
  interface. React and the optional tray consume that interface and contain no
  update rules.
- Live M1 adapters inventory local state only. They do not refresh metadata or
  claim that update availability was checked.

## M2 implemented boundaries

- The Catalog Module preserves update source, origin and installation scope;
  repository/remote, architecture and branch remain part of identity, and
  same-name results are alternatives rather than merged identities. Cutoffs,
  invalid responses and unavailable sources are not reported as zero results.
- Live Arch and AUR search use fixed HTTPS authorities, bounded responses and
  version checks. AUR results say user-submitted and never receive a safety
  verdict. A bounded fixed-host AUR build-file preview remains inert text and
  says when no earlier copy exists for comparison.
- Live Flatpak search stays unavailable because the installed search command
  may refresh AppStream data. Simulator results exercise the full interface
  without changing host metadata.
- The Policy Module validates exact saved choices and centrally rejects a
  selected subset of the system update group. Any active native exclusion also
  blocks that group until the saved choice is removed. It never writes
  `pacman.conf` or changes Flatpak masks.
- The History Module imports bounded pacman and scoped Flatpak records through
  fixed read-only paths. Append-only import batches record source positions,
  skipped rows and why coverage is incomplete. A persisted source cursor
  distinguishes pacman log replacement and same-inode truncation. Imported
  activity stays separate from Updatarr audit events.
- Official notices are bounded, converted to plain text and retain fixed HTTPS
  provenance, parse state and a content hash. The browser uses text rendering
  and separately validated links.
- Flatpak inventory reads existing disabled remotes and update masks through
  fixed read-only probes and shows their counts without changing them.

## M3 implemented boundaries

- The Planning Module converts one recorded inventory generation and one exact
  selection into a canonical SHA-256 plan fingerprint. Sealed plan content is
  immutable, expires after 15 minutes and contains typed operations rather
  than commands, executable paths, environments or argument lists.
- Native repository updates become one full-system step. User and system
  Flatpak items remain separate typed steps with explicit permission needs.
  AUR steps carry a visible blocker and cannot pass validation until build
  isolation and service-secret separation are independently proven.
- Browser review advances only to **Waiting for confirmation on this
  computer**. A separate interactive managed-computer surface displays the
  exact plan and records the Unix identity and kernel session. A loopback-only
  credential supports simulator automation but cannot enable live execution.
  Administrator work then waits in a separate permission state.
- The privileged-boundary prototype accepts only supported typed operations,
  checks the confirming Unix identity/session, inventory generation, exact
  plan fingerprint, identifier grammar and native coordinator/ALPM lock state.
  The fixed-action Polkit prototype resolves process identity from procfs and
  revalidates after interaction. It does not accept caller-selected commands
  or paths.
- Only the deterministic simulator can execute. It records safe cancellation
  points and durable progress, compares expected and observed versions before
  success, atomically claims the plan once and converts an unfinished run found
  after restart to **Needs manual recovery**.
- Live helper installation and provider execution remain disabled because
  their separate approvals have not been granted.

## M4 implemented boundaries

- The safety-readiness Module has one small interface that returns
  presentation-ready capability facts. It hides firmware flag mapping, startup
  checks, portable-file ownership rules and tool-specific ownership decisions;
  it cannot execute a command.
- Firmware follow-up state distinguishes restart, full shutdown, reconnect and
  separate activation. Malformed JSON, missing stable device identity and
  unknown readiness fail closed.
- Kernel, driver-build, dracut and boot-loader checks are one overlay on the
  complete system update group, never a second package owner.
- A portable-app replacement becomes supportable only for an ordinary,
  non-symlink, user-owned file with no system-package owner and recognized
  embedded update information. The simulator models colocated staging,
  verification, atomic replacement and a retained recovery copy; no live file
  operation exists.
- Read-only adapters detect Cargo-installed tools, fnm Node.js versions, global
  npm packages, uv tools and bounded portable-app paths. A system npm root is
  blocked, unresolved uv provenance is not supported and installing a Node.js
  version does not imply switching the default.
- Maintenance is not an update source. The browser can show preview facts, but
  M4 exposes no cleanup action.
- Firmware, portable-app, rustup and fnm simulator plans use closed typed
  operations. They contain identities and expected versions, not commands,
  executable paths, environments or caller-supplied arguments. The privileged
  boundary allowlist was not widened for live use.

## Deferred deployment decisions

- SSE reconnection and buffering through the selected reverse proxy.
- User-service lifecycle and optional linger behavior on the target host.
- Local account bootstrap and credential recovery workflow.
- Final system-bus Polkit/helper packaging and deployment.
- AUR build isolation and separation from Updatarr secrets/state; live use is
  explicitly blocked in M3.
- Packaging format and dependency strategy for Arch.

These decisions do not grant permission for system dependency installation or
host mutation.

## M7 AUR Isolation Prototype

The AUR isolation Module exposes one small interface: build one reviewed source
tree for an exact tuple of expected package identities. It hides all command,
mount, environment, namespace, resource and package-inspection details. There
is no caller-provided command surface.

The implementation uses a fixed root-owned Bubblewrap/`makepkg` toolchain in a
networkless empty-root namespace, wrapped in a collected transient user cgroup.
It copies input into one private writable tree, clears the environment and
parses output in a second sandbox before retaining private hashed artifacts.
Live AUR execution remains disabled because isolated source acquisition and a
clean dependency/tool root are not implemented and independent review is
pending. See the
[M7 isolation validation](docs/research/m7-aur-isolation-validation.md).
