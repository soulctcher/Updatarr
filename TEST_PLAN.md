# Updatarr test plan

**Status:** executable strategy; M0 through M6 accepted

## Test strategy

Tests follow the risk order of the product:

1. prove unsafe work is rejected;
2. prove displayed state is truthful;
3. prove ownership and transaction grouping are correct;
4. prove recovery from interruption and stale state;
5. prove the interface remains usable and accessible at workstation scale.

Every production adapter has contract fixtures before live integration. Every
mutating executor is exercised against fakes or a disposable sandbox before a
tightly scoped live trial. Implementers do not perform the final acceptance
review of their own significant task.

## Test layers

| Layer | Scope | Required evidence |
| --- | --- | --- |
| Domain unit | Identity, policy, grouping, plan hash/state machine | Fast deterministic tests, property cases where useful |
| Provider contract | Parsed installed/update/search/history output | Versioned fixtures including empty, malformed, offline and hostile output |
| Storage integration | Migrations, transactions, imports, retention, backup | Fresh DB plus every supported upgrade path and interrupted migration |
| HTTP integration | Auth, CSRF, validation, pagination, errors, events | In-process client and real listener tests on loopback |
| Executor security | Allowlist, argv, paths, environment, stale/replayed plan | Negative corpus; no real host mutation |
| Browser component | Tables, filters, states, keyboard and responsive layout | Automated accessibility checks and deterministic stories/fixtures |
| Browser end-to-end | Login, scan, plan, approval state, progress/reconnect | Desktop and mobile viewport runs against simulator |
| Host read-only | Results versus installed provider tools | Captured commands, timestamps and discrepancy report |
| Live mutation | Small reversible provider-specific trial | Separate approval, exact impact/rollback and independent observer |

## Safety regression suite

The suite must fail if any implementation can:

- emit `pacman -Sy`, `pacman -Sy <package>` or an equivalent unsupported
  partial-upgrade flow;
- execute a subset of a required native full-upgrade group;
- build an AUR package as root;
- accept arbitrary argv, shell metacharacters or caller-chosen executables at
  the privileged seam;
- run concurrent native writes or ignore an active ALPM lock;
- re-enable disabled Flatpak origins or disable verification silently;
- mutate pacman-owned files through npm, uv or AppImage handling;
- report disabled, stale, errored or unqueried providers as current;
- mark an interrupted or unknown transaction successful;
- expose a non-loopback unauthenticated administrative interface.
- accept credentials or sessions over a cleartext non-loopback listener;
- begin any executable mutation from a remote session without managed-host
  local confirmation;
- expose Updatarr credentials/state to an AUR build process declared isolated.

## Provider fixture minimums

Each adapter needs fixtures for:

- supported with updates;
- supported with no updates;
- disabled;
- executable absent or unsupported version;
- source unavailable/offline/timeout;
- partial or malformed structured output;
- hostile package name, description, URL and terminal control sequences;
- stale installed state between planning and execution;
- cancellation before commit and interruption after commit begins.

Provider-specific fixtures add foreign/unresolved native packages, AUR split and
VCS packages, Flatpak user/system scopes and disabled origins, fwupd power and
reboot flags, AppImages without update metadata and toolchain ownership
collisions.

## Web security matrix

| Case | Expected result |
| --- | --- |
| Default startup | Listener reachable only on loopback |
| LAN bind without auth configuration | Startup/configuration rejected |
| LAN bind without effective HTTPS configuration | Startup/configuration rejected |
| Missing/invalid CSRF token | Mutation rejected without side effect |
| Foreign Origin or disallowed Host | Request rejected |
| Forged forwarded headers from untrusted peer | Ignored or rejected |
| Expired/revoked session | Reauthentication required |
| Replayed plan | Rejected after first terminal use |
| Provider HTML/script in notes or logs | Rendered inert; CSP remains effective |
| Unauthenticated health request | No inventory, paths, user data or detailed errors |
| Event reconnect | Resumes/reconciles observation without starting a second task |
| Remote request for user-level mutation | Waits in `awaiting-local-confirmation`; no provider process starts |
| Root-required plan after local confirmation | Enters `awaiting-authorization`; no root work starts before Polkit success |
| AUR isolation escape corpus | Cannot read protected Updatarr credentials/state or live execution remains blocked |

## Visual and accessibility matrix

- Desktop: 1280×720, 1440×900 and high-density wide display.
- Mobile: narrow portrait and landscape widths with touch targets.
- System preference transitions plus every shipped explicit theme in the
  [theme catalog](docs/design/THEMES.md), including AMOLED, Solarized, GitHub
  and Norse profiles.
- 200% zoom, long package names, localization expansion and thousands of rows.
- Keyboard-only navigation, visible focus, screen-reader names and logical
  heading/table structure.
- Reduced-motion preference and non-color status indicators.
- Brand and semantic color contrast tested independently.
- Empty, loading, Needs refresh, Source unavailable, Blocked, partial failure
  and recovery states.
- Visible text and accessible names follow the
  [plain-language rules](docs/design/CONTENT_STYLE.md); known internal jargon is
  rejected automatically.
- Every page exposes named keyboard-accessible information controls. All help
  opens on pointer hover or keyboard focus without requiring a click. Longer
  guidance uses a wider, scrollable anchored panel that remains available while
  the pointer or focus is inside it.
- Automated safety results use text and symbols, place needs-attention results
  before passed results and preserve visible blockers and next steps when
  details are closed.

## Performance budgets to establish in Phase 0

Concrete thresholds require a prototype and target-host measurement. The test
harness must nevertheless record:

- initial route and authenticated shell load;
- scan-to-first-provider-result and complete-scan time;
- table filter/sort latency at 2,000 and 10,000 rows;
- event delivery lag and reconnection time;
- service idle memory, scan peak memory and database growth;
- cancellation acknowledgement at each provider-safe point.

Budgets become gates only after baseline measurement; they must not be invented
after implementation to excuse regressions.

## Phase 0 architecture proof

Before the provisional web stack becomes accepted, demonstrate:

- the packaged SPA and `/api/v1` from one FastAPI origin at `/` and a non-root
  URL base;
- authenticated SSE reconnect with event IDs, reset behavior and no duplicate
  task through the chosen proxy path;
- rejection of unknown Host, foreign/null Origin mutations, missing CSRF proof
  and spoofed forwarding headers;
- session rotation, expiry, logout revocation, password change, throttling and
  host-local recovery;
- a frozen remote plan that remains non-executable until explicit local review
  for both user-level and privileged mutations, and that expires or invalidates
  on relevant host drift;
- Polkit behavior with active, inactive, logged-out/linger, SSH and missing-agent
  cases;
- tray/service separation across login, logout, restart and crash;
- an isolated clean Arch package build/install/upgrade/uninstall inventory.

## Milestone evidence format

Each closed task records:

- requirement or risk addressed;
- exact test commands and environment;
- pass/fail/skip counts;
- fixture or live-data provenance;
- screenshots for changed visual flows;
- independent reviewer and findings;
- known gaps and the milestone that owns them.

The 22 minimum end-to-end scenarios in [PLAN.md](PLAN.md) remain binding and
will be assigned stable test IDs when the test harness is scaffolded.

## M1 evidence

The M1 suite covers deterministic source-qualified identity, typed policy and
update-run states, atomic SQLite initialization, WAL/backup, append-only audit,
bounded events, Argon2id credentials, hashed durable sessions, provider failure
isolation, cancellation/deduplication, defensive hostile/malformed parsing,
API authentication and persistent preferences. Real-browser tests exercise all
five views at 1440, 681, 680, 390 and 320 CSS pixels; all 18 themes across all
five views; contrast, system light/dark, keyboard theme selection, reduced
motion, 200% zoom and retired-theme fallback; progress and document-level
overflow. Live evidence compares local tool counts while leaving update
availability explicitly Not checked.

## M2 evidence

M2 adds deterministic tests for exact saved-choice identity, expiry,
last-application records, changed-version behavior, same-ref/different-remote
isolation and native system-update-group rejection. Catalog contracts keep
same-name Arch, AUR and Flatpak results separate, report cutoffs, timeouts and
invalid formats distinctly, bound remote input, label AUR as user-submitted and
render descriptions/notices and bounded AUR build files as inert text. History tests cover current and
older pacman formats, Flatpak scopes and commit fields, duplicate source events,
idempotent import, replacement/copy-truncate generations, append-only events and coverage batches, incomplete reasons
and unknown analytics. Existing Flatpak disabled remotes and masks are detected
through fixed read-only probes. Authenticated API and browser tests cover CSRF,
changed snapshots, turned-off sources, desktop/mobile catalog choices, blocked
native selections, restart persistence and all shared theme/layout regressions.
Exact commands, counts, live read-only evidence and screenshots are recorded in the
[M2 validation note](docs/research/m2-validation.md).

## M3 evidence

M3 adds deterministic plan-fingerprint, expiry, inventory-drift, saved-choice,
native-group and constrained-transition tests. The privileged-boundary negative
corpus rejects caller mismatches, stale generations, active coordinator/ALPM
locks, hostile identifiers, unknown steps and disabled operations without
accepting commands, executable paths, environments or caller argument arrays.
API tests keep browser review, managed-computer confirmation and simulated
administrator permission separate; plans are single-use and all browser
mutations retain session, Origin and CSRF enforcement. Run tests cover safe
pre-step cancellation, result-check failure and restart reconciliation to
Needs manual recovery. AUR plans are visibly blocked before execution.

Real-browser tests exercise exact plan review and the local-confirmation wait
state at desktop and mobile widths. The full suite and visual evidence are
recorded in the [M3 validation note](docs/research/m3-validation.md). Final M3
verification passed **221 tests**; independent review found no remaining
critical, high or medium findings.

## M4 evidence

M4 adds deterministic tests for each firmware follow-up action, malformed and
identity-less firmware JSON, portable-app system-package ownership, symlinks
and missing update information, and separate kernel/driver-build/dracut/boot
checks. Adapter contracts cover empty Cargo and uv inventories, fnm active and
default versions, a system npm root and bounded portable-app paths. Typed
simulator plans prove that firmware, portable-app, rustup and fnm operations
contain no command or caller argument surface.

Authenticated interface tests distinguish **Ready to review**, **Blocked**,
**Not supported** and **Not checked**, show plain-language restart or physical
follow-up instructions, expose no cleanup control and assert that package
ownership, disabled Flatpak origins and host state remain unchanged. The
changed flow is exercised at desktop and mobile widths and with all 18 theme
profiles. Exact final commands and counts are recorded in the
[M4 validation note](docs/research/m4-validation.md).

The final M4 interface revision also tests the issue-first safety checklist,
summary counts, spacing between major sections, information controls on every
page, modal and pop-up behavior, keyboard dismissal, and a rendered-copy audit
that includes opened help and server-provided explanations.

## M6 evidence

M6 adds restart reconciliation drills that require positive expected-version
evidence for success and keep false, missing or failed checks in Needs Manual
Recovery without replaying the plan. Package-manager lock tests distinguish an
alternative process, the current process, no owner visible and no lock; every
present lock blocks and remains untouched. Provider tests add AUR unavailability,
Unicode direction/zero-width controls, literal search wildcards and unknown
package-renaming behavior.

Schema 6 provides indexed server-side inventory paging. The repeatable M6
profile enforces storage, sorted first-page, populated filtered-page and
database-size budgets at both 2,000 and 10,000 rows. Browser tests cover the visible full count and pager, API-version
mismatch, high-density output, 400% reflow equivalence, accessible control
names, duplicate IDs and all existing responsive/theme/plain-language gates.
The 22 scenarios and explicit release blockers are mapped in the
[M6 acceptance matrix](docs/research/m6-acceptance-matrix.md).
Final M6 verification passed **300 tests**; the independent re-review found no
remaining critical, high, medium or low findings.
