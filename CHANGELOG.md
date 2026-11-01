# Changelog

## 0.6.0-m6 — accepted 2026-10-30

- M5 accepted by the user; repository work advanced to the separately gated M6
  hardening and release scope.
- Added evidence-based interrupted-run reconciliation: only a positive
  expected-version check can recover to success; unknown, failed and mismatched
  checks require manual recovery and never replay the plan.
- Added bounded package-manager lock observation that distinguishes an
  alternative owner, the current process and an owner-unknown lock without
  removing any lock.
- Removed Unicode direction and zero-width format controls from untrusted
  provider text and extended unavailable-source, schema-interruption and
  identity hardening tests.
- Added indexed server-side inventory paging and a visible 100-row Software
  pager, replacing the prior silent 500-record cutoff.
- Added explicit API version 1 compatibility checks, high-density/400% reflow
  accessibility coverage and a repeatable 10,000-record performance profile.
- Added the full security review, 22-scenario acceptance matrix, upgrade and
  interrupted-run recovery guide, and known limitations/release blockers.
- Release publication, package installation, service and notifier changes,
  software removal and every live software mutation remain unauthorized.
- M6 was accepted by the user, closing the currently defined milestone plan
  without resolving or bypassing the retained publication and live-action
  gates.

## 0.5.0-m5 — accepted 2026-10-29

- M4 accepted by the user; repository work advanced to the separately gated M5
  scope.
- Added a staged Arch package with unprivileged core and tray user units, a KDE
  launcher, icon, example configuration and built web application.
- Added a private service-to-tray status file, five-second refresh and a
  per-user single-tray lock without storing browser credentials in the tray.
- Added fail-closed production settings for passwords, loopback, direct HTTPS,
  specific non-wildcard binds, exact hosts and reverse-proxy public origins.
- Added a secret-free settings download plus install, recovery, trusted-network,
  Octopi comparison and rollback guidance.
- Added fixture-backed notifier disable, exact rollback and reapplication
  evidence that keeps exactly one startup owner throughout the migration drill.
- Added faint version/build information beneath the rail safety notice,
  stationary top-layer pointer-right help panels and destination-aware Safety
  Checklist status tags.
- Removed the redundant Ultraviolet preview from Appearance. Passed and
  informational checklist badges are no longer presented as actions.
- Standardized visible titles and table headings on title case while preserving
  official forms such as AUR, KDE, AMOLED, GitHub, Node.js, npm, fnm, fwupd and
  uv.
- No package, service, notifier or software removal was performed.

## 0.4.0-m4 — revised 2026-10-29

- M3 accepted by the user; repository work advanced to the separately gated M4
  scope.
- Added fail-closed firmware follow-up classification, startup-related safety
  checks and portable-app ownership/update-information rules.
- Added read-only Cargo, fnm, npm, uv and portable-app adapters plus closed
  typed simulator operations for firmware, portable apps, rustup and fnm.
- Replaced the dense safety-card grid with an issue-first Safety checklist that
  shows what passed and what needs attention before expandable detail.
- Replaced permanent instruction panels with small, raised circled information
  controls and click-free hover/focus help panels across every page.
- Completed a full plain-language pass over page copy, help, update plans,
  firmware/startup checks, portable apps, tools, maintenance and errors.
- Added clear spacing between the Safety checklist and Detected updates.
- Added preview-only maintenance;
  live mutation and cleanup remain unavailable.

All notable project changes will be recorded here once implementation begins.

## Unreleased

### Changed

- The user accepted the proposed M7 scope on 2026-10-30 and authorized
  project-local release-candidate work. Host installation, service/notifier
  changes, public release, signing-key use and live software mutation remain
  separately gated.
- Added the M7 owner decision sheet, primary-source release-foundations
  research, generated-asset provenance inventory and locked runtime SBOM/input
  hash generator. No license, repository authority, signing method or AUR
  release boundary was selected on the owner's behalf.
- The owner selected `AGPL-3.0-or-later`, a local Git baseline with no remote
  push, and an AUR-isolation requirement before producing the release
  candidate. Release proof and exact copyright-holder text remain pending.
- The owner selected one owner-controlled OpenPGP release key for both signed
  Git release labels and downloaded release files. No private key has been
  created, inspected or used.
- M0 decisions accepted by the user on 2026-10-24; project advanced to the M1
  safe-foundation and read-only-product scope without authorizing host mutation.
- M1 accepted by the user on 2026-10-24; project advanced to the M2 catalog,
  policy and history scope without authorizing installation or host mutation.
- M2 accepted by the user on 2026-10-26; project advanced to M3 planning and
  simulated execution without authorizing a helper installation or live update.

### Added

- Content-addressed, immutable, 15-minute update plans with exact typed steps,
  permission needs, blockers, expiry, constrained state transitions and
  one-time consumption.
- Separate browser review, managed-computer confirmation and administrator
  permission states; browser approval cannot stand in for local consent.
- Typed privileged-boundary prototype with caller, fingerprint, inventory,
  identifier and package-manager-lock checks and no caller-provided command,
  path, environment or argument surface.
- Deterministic update-run simulation with explicit safe cancellation points,
  result checks and restart reconciliation to Needs manual recovery.
- An explicit live AUR blocker pending tested build isolation and separation
  from Updatarr credentials and state.
- Responsive exact-plan review in the Updates screen with desktop and mobile
  visual evidence.

- M2 source-qualified Arch/AUR/Flatpak catalog with complete
  repository/remote, scope, architecture and branch identity, truthful cutoff
  and failure states, bounded plain-text source information, and hashed notice
  provenance. Live Flatpak search remains Not checked because it may refresh
  catalog metadata.
- Fixed-host, bounded, plain-text AUR build-file previews that explicitly say
  when an earlier copy is unavailable for comparison.
- Durable postpone, skip-version, pause and turned-off-source choices with
  append-only events, expiry, last-application evidence and central rejection
  of partial system update selections.
- Idempotent bounded pacman and scoped Flatpak history import, separately
  labeled partial history, append-only coverage batches, truthful summaries and
  target-scale measurements.
- Read-only detection of existing Flatpak disabled remotes and update masks,
  with no provider setting changes.
- Responsive M2 catalog, saved-choice, source-setting, selection-safety and
  imported-history flows across the complete theme system.
- M1 typed inventory, source, policy and update-run state models with
  deterministic source-and-scope-qualified software identities.
- Explicit SQLite WAL state store for immutable inventory snapshots, bounded
  task events, append-only audit history, preferences, Argon2id credentials and
  hashed durable sessions.
- Defensive live read-only adapters for native packages, Flatpak user/system,
  firmware and Rust toolchains, plus truthful unresolved foreign-package
  classification and hostile/malformed fixtures.
- Software, Updates and History screens, persistent Settings → Appearance,
  responsive five-view navigation and optional KDE tray prototype.
- M1 API, coordinator, persistence, provider, browser and live-count evidence.

- Updatarr product name and *arr-style responsive web-management direction.
- Initial product plan, architecture, capability matrix, security model, test
  plan, milestones, operations runbook and architecture decisions.
- Source-backed *arr ecosystem/color and web architecture/security research.
- User-selected Ultraviolet brand direction plus documented alternate palettes.
- Loopback-only throwaway Overview prototype with update-progress,
  update-source and review variants, mocked JSON/SSE state and responsive
  layouts.
- Plain-language product vocabulary, including “detected update,” “ready to
  review,” “update source,” “update plan” and “update run.”
- Initial read-only target-host capability snapshot.
- Tokenized appearance system with System, Light, Dark, AMOLED, Solarized,
  GitHub, Norse and nine additional theme profiles.
- Closed, read-only capability probe with local-identity redaction, executable
  ownership reporting and expiry metadata.
- Sanitized native, Flatpak, firmware, npm and toolchain output fixtures.
- Expanded Phase 0 local ownership, disabled-origin, firmware-shape, toolchain,
  DKMS, boot and rollback findings captured without changing the host.
- Project-local React/TypeScript/Vite production interface with all 18 themes
  under Settings → Appearance, responsive navigation and the Ultraviolet
  controlled-change workflow.
- Loopback-only FastAPI architecture proof, advanced in M1 with durable server-side sessions,
  CSRF/Host/Origin checks, bounded requests, reconnectable event IDs and one
  simulator-only update-check task.
- M0 web-stack validation evidence and final decision/sign-off packet.

### Security

- Defined loopback-only defaults, authenticated LAN/VPN access, browser threat
  controls, mandatory HTTPS beyond loopback, local confirmation for every
  software mutation and a separate fixed-operation privileged execution seam.

The production entry point cannot run package-manager commands. Only locked
project-local dependencies, simulators and disposable state were used; no
system package, Flatpak, service, autostart, update-source or host configuration
was changed.
