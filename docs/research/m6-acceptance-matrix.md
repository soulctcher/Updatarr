# M6 end-to-end acceptance matrix

**Prepared:** 2026-10-30  
**Source:** the 22 minimum scenarios in [PLAN.md](../../PLAN.md)  
**Rule:** a scenario is either demonstrated or names an explicit release
blocker; simulator/read-only evidence does not authorize live mutation

| ID | Acceptance outcome | Evidence and disposition |
| --- | --- | --- |
| E2E-01 | Pass | Source states keep Up to Date, Not Checked, Needs Refresh, Turned Off, Source Unavailable, Blocked and Error distinct; source timestamps remain visible. Provider/API/browser tests cover empty and failed checks. |
| E2E-02 | Pass | The read-only host snapshot recorded 1,743 native packages and 42 foreign packages, exceeding the target scale. Foreign packages remain unresolved unless separately evidenced; native/AUR queries stay separate. |
| E2E-03 | Pass | User/system Flatpak scopes have distinct identities. The read-only check retained 21 disabled user remotes and did not change them. |
| E2E-04 | Pass | The native adapter uses the accepted `checkupdates` temporary-database probe; the forbidden-command suite rejects `pacman -Sy` and no active sync database is written. |
| E2E-05 | Pass | Domain, API and browser tests reject a native subset and explain that all system packages must update together. |
| E2E-06 | Pass | Postpone, skip-version, pause, removal and turned-off-source behavior persist and retain truthful status across restart and version change. |
| E2E-07 | **Release blocker** | AUR search, metadata, build-file preview, plan blocking and current-native-state rules are tested. Live AUR build/install remains disabled until user-data and service-secret isolation is proven. |
| E2E-08 | Pass | Same-name Arch, AUR and Flatpak catalog results retain source/scope identity and documentation links; no automatic source switch exists. |
| E2E-09 | Pass in simulator; live gate remains | Plans distinguish user and administrator permission, and system Flatpak cannot bypass managed-host confirmation/Polkit. First live user/system Flatpak mutation remains separately approval-gated. |
| E2E-10 | Pass in fixtures; live gate remains | Unsupported, AC-power, battery, activation and restart/shutdown firmware states remain distinct and cannot claim false success. First live firmware trial remains separately approval-gated. |
| E2E-11 | Pass | npm system-prefix ownership blocks mutation; unresolved uv installation provenance is Not Supported and self-update remains disabled. |
| E2E-12 | Pass | Portable apps require a regular unowned file and supported update information; missing metadata is Not Supported and pacman ownership blocks independent handling. |
| E2E-13 | Pass in fixtures; live gate remains | Kernel, driver-build, early-startup-image and boot checks preserve the native group and report restart or manual recovery truthfully. First live startup-related trial remains separately approval-gated. |
| E2E-14 | Pass | Hostile identifiers, paths and caller mismatch are rejected; the browser/service/helper seam accepts no arbitrary command; captured data strips control characters. |
| E2E-15 | Pass | M6 restart drills prove success only with positive expected-version evidence. Missing, false or failed checks become Needs Manual Recovery and no plan is replayed. |
| E2E-16 | Pass | Provider checks run concurrently behind one deduplicated read-only task. Enforced SQL profiles passed at 2,000 rows (1.042 ms median first page; 1.509 ms populated filter) and 10,000 rows (1.288 ms; 2.882 ms). The browser pages rather than rendering or hiding the inventory. Native writes remain single-claim and lock-gated. |
| E2E-17 | Pass in fixtures; live gate remains | Tray counts use the same Overview summary; paused/blocked states remain separate; staged migration and rollback keep exactly one notifier. Live notifier cutover remains separately approval-gated. |
| E2E-18 | Pass | Imported history is labeled partial, failed steps and timestamps remain recorded, analytics never invent missing download data, and settings export excludes secrets and runtime state. |
| E2E-19 | Pass | No Octopi, notifier, Pamac or PackageKit removal/change occurred. Each remains a separate approval decision. |
| E2E-20 | Pass | TypeScript, production build, lockfile, Python compilation, dependency audits, 300 automated tests, package drills and independent review passed; no significant finding remains. |
| E2E-21 | Pass | Loopback default, authenticated HTTPS rules, Host/Origin/CSRF/session/proxy-spoofing tests and minimal unauthenticated health response pass. API version mismatch stops the browser. |
| E2E-22 | Pass in simulator; live gate remains | Browser/tray state comes from one service; SSE reconnect does not duplicate work; every simulated mutation waits for managed-host confirmation and root work waits separately for authorization. Live execution remains separately gated. |

## Additional M6 hardening cases

- Alternative live pacman lock holder, current-process holder and owner-unknown
  lock all block without deleting the lock.
- AUR timeout is Error, not Up to Date.
- Malformed, truncated, HTML/script, terminal-control and Unicode-direction
  metadata fail closed or remain inert bounded text.
- Unknown package rename relationships stay separate rather than being guessed.
- Schema 6 adds indexed server-side inventory paging; an interrupted database
  migration rolls back every new object, and a future schema is rejected.
- All included themes, documented responsive boundaries, reduced motion, 200%
  zoom and 400% reflow/high-density checks remain in the browser suite.

The publication blockers are consolidated in
[Known limitations](../KNOWN_LIMITATIONS.md). They prevent a release tag and
publication but do not conceal a failed acceptance scenario.
