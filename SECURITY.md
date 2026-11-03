# Updatarr security model

**Status:** M0 through M6 accepted; separate live-mutation and release gates remain  
**Security posture:** deny by default; preserve ownership and provider trust

## Assets

- Integrity and availability of the package database, boot stack and firmware.
- User files, application configuration, package cache and update history.
- Administrator credentials, sessions and approval decisions.
- Trust configuration: package signatures, repositories, Flatpak remotes and
  AUR review state.
- Accurate update status and audit evidence.

## Trust zones

| Zone | Trust level | Rule |
| --- | --- | --- |
| Browser or tray client | Authenticated but not intrinsically trusted | May express intent; cannot construct commands or declare a plan safe |
| Updatarr service | Unprivileged application authority | Owns domain state and validates intent; cannot perform arbitrary privileged work |
| Provider output | Untrusted input | Parse defensively; never render or execute as trusted content |
| AUR source/build | Untrusted executable build input | Review explicitly; require local confirmation; assume full user-account access until tested isolation exists |
| Privileged executor | Narrow trusted computing base | Accept fixed operations and immutable validated plans only |
| Package backends | Host authorities within their ownership domain | Preserve their locks, signatures, prompts and transaction semantics |

## Threats and required controls

### Network and browser threats

| Threat | Required control |
| --- | --- |
| Accidental or cleartext LAN exposure | Bind to loopback by default; require authenticated HTTPS for non-loopback; never modify firewall/router automatically |
| Password guessing | Modern password hashing, throttling/backoff, generic failures, audit events |
| Session theft/fixation | Rotating opaque session IDs, Secure/HttpOnly/SameSite cookies as deployment permits, expiry and revocation |
| CSRF | Same-origin design, anti-CSRF token on mutations, Origin validation and safe HTTP method discipline |
| Stored/reflected XSS | Treat names, logs, notes and URLs as untrusted; contextual escaping; sanitize any permitted rich text; restrictive CSP |
| DNS rebinding/Host abuse | Explicit allowed hosts and Origin checks |
| Proxy spoofing | Keep proxy-header interpretation off; accept and ignore those headers only from an explicitly configured loopback proxy peer |
| Sensitive diagnostics | Minimal unauthenticated health response; authenticate inventory, logs, paths and version detail |
| API replay/stale intent | Short-lived plan envelope, current-state revalidation, one-time execution semantics and audit correlation ID |

LAN reachability is not Internet readiness. Initial supported remote use is a
trusted LAN or VPN, optionally behind a deliberately configured reverse proxy.

M1 stores the single administrator verifier with Argon2id and keeps opaque
sessions server-side in SQLite. Only a SHA-256 digest of each session ID is
stored; the CSRF token remains server-side, and expiry, logout, password change
and restart behavior are tested. Login throttling, exact Origin and Host checks,
forwarded-header rejection from untrusted peers, bounded bodies and a
loopback-only default listener remain enforced. Explicit reverse-proxy mode
accepts but does not interpret forwarding headers from its loopback peer. The
visible demonstration password is development-only.

### Command and privilege threats

- Use trusted absolute executable paths discovered and recorded by capability
  probing; never shell-concatenate metadata.
- In an unprivileged systemd user namespace, host-root-owned files can appear
  under Linux's overflow user ID. Accept that identity only when the namespace
  map proves host root is absent, the fixed `/usr/bin` path and parents are not
  writable, and the read-only package-owner check matches the closed registry.
  Missing namespace evidence fails closed.
- Build argv from typed operation data and validate package/ref identifiers
  again in the privileged executor.
- Use a controlled environment and working directory. Remove secret-bearing
  variables that providers do not need.
- Never accept an executable path, environment map, arbitrary argv or shell
  fragment from the browser.
- Bind approval to plan hash, actor, operation type, snapshot, expiry and
  dependency/permission summary.
- Refuse execution after material plan drift.
- Keep AUR checkout, review and build unprivileged, but do not confuse
  unprivileged with isolated: arbitrary build scripts may access user files.
  Live AUR builds remain blocked until a tested isolation design protects
  Updatarr credentials/state and documents residual access. Only the final
  reviewed package installation crosses the privileged seam.
- Do not cache desktop authentication credentials or accept passwords through
  application logs/stdin plumbing.

### Package-management threats

- Native repository packages form one full-upgrade group.
- Honor the ALPM lock and an Updatarr coordinator lock; never delete a lock
  merely because its file exists.
- Preserve signature enforcement and disabled origins.
- Treat foreign packages as unresolved until ownership is established.
- Do not let npm, uv, AppImage or another adapter overwrite pacman-owned files.
- Firmware operations require device-specific constraints, explicit approval
  and truthful reboot/activation state.

### Filesystem and persistence threats

- Refuse symlink/path traversal for staged portable updates and exports.
- Use restrictive permissions for configuration, session and recovery data.
- Perform atomic database migrations and file replacement where supported.
- Keep logical audit events append-only and make imported external history
  visibly distinct.
- Redact credentials, secret query parameters, authorization headers, local
  usernames where unnecessary and control sequences from captured output.
- Back up before destructive migrations; test restoration rather than merely
  creating backup files.

The M1 state directory and database are restricted to the owning user. The
first schema migration is one SQLite transaction, audit rows reject update and
delete operations, bounded task events are separate from authoritative task
state, and the backup test restores a usable snapshot.

M2 catalog and history inputs remain untrusted. Fixed-source HTTPS requests
have response and time limits, catalog prose and notices become bounded plain
text, notices retain a content hash and parse state, and external links are kept
separate from rendered text. AUR results are explicitly user-submitted. Saved
choices accept the complete stable software identity rather than a name or a
command. Policy, imported-history and import-coverage events are append-only,
while imported activity never supplies approval evidence. Live Flatpak search
is blocked because its documented behavior may refresh metadata. Existing
disabled remotes and masks are read through fixed probes, but no remote, mask,
repository or package setting is changed in M2.

M4 treats firmware JSON, tool inventories, file paths and boot status as
untrusted observations. Firmware requirements and physical follow-up actions
remain separate; unknown or malformed values cannot become a ready update.
Portable-app support requires a regular non-symlink file, a negative
system-package ownership result and supported embedded update information.
Read-only tool adapters do not use self-update or force-overwrite behavior.
System npm roots are blocked, unresolved uv provenance remains not supported,
and a maintenance preview has no deletion interface. The simulator preserves
package ownership and disabled Flatpak origins and reports those facts in the
authenticated readiness response.

M6 removes Unicode direction and zero-width format controls from provider text,
distinguishes alternative, current-process and owner-unknown pacman locks, and
blocks on every present lock without removing it. Restart reconciliation can
record success only after a trusted check proves every expected version; a
negative, absent or failed check becomes Needs Manual Recovery and the plan is
never replayed. API version 1 is explicit at sign-in, and an incompatible
browser/service pair stops before loading the application. The complete control
review and residual blockers are in the
[M6 security review](docs/research/m6-security-review.md) and
[known limitations](docs/KNOWN_LIMITATIONS.md).

## Authentication and authorization baseline

- Loopback-only deployments may offer an explicit local convenience policy,
  but loopback proves neither human identity nor request intent. The decision
  must be visible, resist cross-origin/DNS-rebinding and other-local-process
  attacks, and never carry over when the bind address changes.
- Every non-loopback deployment requires authentication.
- Every non-loopback deployment requires HTTPS, terminated directly or by an
  explicitly trusted reverse proxy. Startup/configuration rejects cleartext
  non-loopback credential and session mode.
- Serve UI and API from one origin with CORS disabled by default. Keep safe HTTP
  methods side-effect free and reject disallowed Host/Origin values before
  application routing.
- Store opaque sessions server-side; use Secure/HttpOnly/SameSite cookies for
  every non-loopback deployment, rotate at authentication changes, and support
  expiry and revocation. Keep reusable credentials out of URLs and browser
  storage.
- Use Argon2id with target-host-benchmarked parameters for local password
  verifiers and throttle authentication attempts.
- Initial bootstrap and credential recovery must require access to the managed
  host or another separately designed recovery factor.
- Roles are deferred until a real multi-user requirement exists. The initial
  design can use one administrator role without inventing shallow permissions.
- All state-changing browser requests require an authenticated session, CSRF
  defense, server-side authorization, revalidation and an audit event.

## Local confirmation, authorization and remote intent

A remote administrator can inspect state, adjust application policy and prepare
a transaction. Every executable software mutation enters
`awaiting-local-confirmation` and must be confirmed through the managed host's
local approval surface; this covers user-level AUR builds, Flatpak/toolchain
changes and AppImage replacement as well as root work. A root-required plan then
enters `awaiting-authorization` for the approved Polkit/helper flow. The UI must
not imply that a remote click completed either step. A different unattended or
remote-execution policy would expand the threat model and needs explicit user
approval and an ADR.

## Security verification gate

Before any live mutation provider is enabled, an independent review must cover:

1. privileged executor operation allowlist and validation;
2. command argument and environment construction;
3. AUR review/build/install separation;
4. session, CSRF, XSS, Host/Origin and proxy behavior;
5. plan drift, replay and concurrent transaction handling;
6. logs, exports and error responses for secret leakage;
7. negative tests with adversarial names, paths, URLs and provider output.

Known limitations and deferred decisions must be published rather than hidden
behind a generic security claim.

M7 now has a project-local AUR isolation prototype with a closed typed
interface, hidden home/runtime/network, cleared environment, fixed system tools,
private cgroup limits and separately sandboxed package inspection. Its writable
tree is confined to a verified memory-backed filesystem and the cgroup memory
ceiling; process output is drained into fixed-size tails. A disk-backed,
unbounded build directory is not an acceptable fallback. It is not a live
provider. Source acquisition and a clean dependency root remain blocking, with
no override. Resource testing no longer uses
deliberate memory or process pressure after the initial cgroup check caused an
unacceptable desktop low-memory notification.

Primary-source basis and decisions still requiring prototypes are recorded in
[architecture-security-research.md](docs/research/architecture-security-research.md).
