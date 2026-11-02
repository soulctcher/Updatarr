# Updatarr milestones

**Current phase:** M7 release candidate and controlled deployment  
**Current authorization:** project-local M7 implementation, clean disposable
build/test environments, simulators, fixtures, documentation and read-only
inspection. Package installation on the managed computer,
service/autostart changes, notifier changes, Octopi or Pamac removal, release
publication and every live software mutation remain separately gated and
unauthorized. Signing-key use is authorized only for the final local M7 release
label and release files; it does not authorize publication or a push.

## Gate rules

- A milestone closes only with recorded evidence, resolved critical findings
  and an independent review.
- A later milestone may prototype behind simulators, but may not bypass an open
  safety gate from an earlier milestone.
- Live update-source changes, dependency installation, autostart changes and
  Octopi migration each require the approval stated below.

## M0 — architecture, research and design

**Deliverables**

- [x] Product specification and host snapshot
- [x] *arr ecosystem and visual research
- [x] Architecture and initial deep-module seams
- [x] Conceptual domain/data schema
- [x] Threat model and web security baseline
- [x] Capability matrix template
- [x] Test strategy and negative safety suite
- [x] Ultraviolet visual direction selected with alternate palette record
- [x] Initial ADRs and operations model
- [x] Primary-source web stack, browser security, Polkit, systemd and KDE tray
      research
- [x] Initial read-only target-host runtime and capability snapshot
- [x] Update-source output fixtures, ownership classification and full read-only
      target-host capability probe results
- [x] Provisional FastAPI + React/TypeScript/Vite + SSE stack validated by an
      isolated project-local vertical slice and target-host dependency evidence
- [x] Three responsive Overview directions exercised in representative
      desktop/mobile frames without horizontal overflow
- [x] Tokenized multi-theme catalog documented and exercised in the throwaway
      shell
- [x] Plain-language product vocabulary applied to the glossary, mock API and
      prototype with a visible-copy regression check
- [x] Final Phase 0 decisions and user sign-off

**Read-only capability evidence (2026-10-24):** The closed probe, sanitized
fixtures, complete capability summary and primary-source command research are
recorded under `scripts/read_only_capability_probe.py`,
`tests/fixtures/read_only` and `docs/research`. Exact trusted executable paths
and owners gate execution; the suite covers PATH hijacking, redaction, timeout,
byte and AppImage-record limits. Independent review passed after its initial
security findings were fixed. Verification: `python -m pytest -q` — 103 passed.

**Web-stack evidence (2026-10-24):** The packaged same-origin React interface,
FastAPI API, server-side sessions, CSRF/Host/Origin boundary, bounded event
history and simulator-only task module are under `web`, `src/updatarr` and
`tests/test_m0_*`. Root and `/updatarr` URL bases, authenticated event replay,
task deduplication, all 18 themes and the 320/390/680/681/1440 responsive widths
are exercised. Dependency and limitation evidence is recorded in
`docs/research/m0-web-stack-validation.md`. Final sign-off remains a user
decision, not a checkbox the implementer can approve. Final verification:
TypeScript check and Vite build passed; `python -m pytest -q` — 119 passed.
Independent review passed after its bounded-request and accessibility findings
were fixed, with no critical, high or medium findings remaining.

**M0 closure (2026-10-24):** The user accepted the recorded decisions and
authorized work within the M1 scope and gate. This does not authorize privileged
executor work or any live software mutation; those later approvals remain
separate.

## M1 — safe foundation and read-only product

- [x] Software identity, source status, policy and update-run state models.
- [x] SQLite migrations and append-only audit foundation.
- [x] Update-source registry, simulator and adversarial fixtures.
- [x] Read-only native/foreign, Flatpak, fwupd and rustup adapters. Foreign
  packages remain unresolved rather than being mislabeled as AUR packages.
- [x] Versioned loopback API and authenticated event channel.
- [x] Authentication, server-side sessions, CSRF and Host/Origin enforcement before
  any persistent browser mutation is introduced.
- [x] Responsive Updatarr shell and KDE tray prototype.
- [x] Inventory deduplication and truthful update-source status.
- [x] User accepts M1 and authorizes the next milestone.

**Gate:** no writes; results match native tools; active pacman sync data
is untouched; responsive/accessibility smoke tests pass.

**M1 closure (2026-10-24):** The user accepted M1 and authorized work within
the M2 scope and gate. This does not authorize M3 installation work, live
software changes, system dependency installation, service or autostart changes,
or Octopi migration.

## M2 — catalog, policy and history

- [x] Official/AUR/Flatpak search and explicit source selection.
- [x] Notes/advisory provenance and safe rendering.
- [x] Postpone, skip-version, pause and update-source settings.
- [x] Native partial-upgrade rejection.
- [x] Imported history, analytics and accurate empty/unknown states.
- [x] User accepts M2 and authorizes the next milestone.

**Gate:** persistent policy semantics, source disambiguation, no invented data,
and acceptable performance with target-scale inventory.

**M2 technical evidence (2026-10-26):** Complete source identities, truthful
catalog cutoffs/failures, inert AUR build-file previews, native-group safety,
durable saved choices, direct removal back to the source-reported state, source
documentation links, plain-language update-choice guidance, existing
Flatpak-setting detection and partial external history with rotation-aware
source generations are implemented. Live checks
used fixed HTTPS reads, trusted local read-only probes and disposable SQLite
state; no software or provider setting changed. TypeScript check, Vite build,
lockfile check and Python compilation passed. Final suite: **197 passed** with
one third-party deprecation warning. Independent re-review found no remaining
critical, high or medium issues. Details: [M2 acceptance](docs/M2_ACCEPTANCE.md).

**M2 closure (2026-10-26):** The user accepted M2 and authorized work within
the M3 scope and gate. This authorizes repository implementation with
simulators and fixtures; it does not authorize installing a privileged helper
or performing any live software mutation.

## M3 — reviewed update installation

- [x] Unchangeable update plans and last-minute safety checks.
- [x] Store-backed typed privileged boundary and fixed-action Polkit prototype;
      installation and live use remain separately gated.
- [x] Native full-upgrade and Flatpak simulator execution paths; reviewed AUR
      steps remain visibly blocked before execution.
- [x] Durable progress, safe cancellation, result checks and honest restart
      recovery.
- [x] Remote review, interactive managed-computer confirmation and separate
      administrator-permission flow.
- [x] Explicit tested blocker keeps live AUR execution disabled until build
      isolation and service-secret separation are proven.

**Approvals required:** install privileged helper; run each first live update-source
trial; make any system package or Flatpak change.

**Gate:** independent security review and all command/privilege/local-consent
negative tests.

**M3 technical evidence (2026-10-27):** Canonical 15-minute plans, atomic
single-use claims, typed operation envelopes, fixed-action Polkit arguments,
Unix identity/session binding, native-group safety, simulator execution,
durable progress, safe-point cancellation, expected-version result checks and
restart recovery are implemented. AUR remains blocked with no override. The
TypeScript check, Vite build and Python compilation passed; the complete suite
passed **221 tests in 88.22 seconds** with one known third-party deprecation
warning. Independent review found no remaining critical, high or medium
findings. No helper, policy, package, Flatpak, service or autostart change was
installed or performed. Details: [M3 acceptance](docs/M3_ACCEPTANCE.md).

**M3 closure (2026-10-27):** The user accepted M3 and authorized repository
work within the M4 scope and gate. This does not authorize any of M4's first
live mutation trials.

## M4 — firmware, boot, tools and portable apps

- [x] fwupd flow and activation/reboot state.
- [x] Kernel, DKMS, dracut and boot classification/preflights.
- [x] Supported AppImage staged replacement.
- [x] Detected rustup/Cargo/fnm/npm/uv adapters.
- [x] Previewed maintenance operations.

**Approvals required:** first live firmware, boot-affecting, toolchain, AppImage
replacement and cleanup trials.

**Gate:** unsupported cases remain accurately disabled; package ownership and
disabled Flatpak origins are unchanged except by an explicitly approved plan.

**M4 technical evidence (revised 2026-10-28):** Firmware requirements and follow-up
actions, complete startup-related preflights, staged portable-app replacement,
truthful developer-tool ownership, and exact non-destructive maintenance
previews are implemented behind typed simulator and read-only boundaries. All
M4 live execution paths remain disabled pending their separate first-trial
approvals. TypeScript checking, the Vite build and Python compilation passed;
the complete suite passed **247 tests in 163.35 seconds** with one known
third-party deprecation warning. Desktop, mobile and all 18 included themes
passed browser checks. The final interface revision adds an issue-first safety
checklist, all-page contextual help, consistent section spacing and a complete
plain-language audit. Independent re-review found no remaining critical, high
or medium findings. No firmware, package, tool, portable file, cleanup,
service or host-setting mutation occurred. Details: [M4 acceptance](docs/M4_ACCEPTANCE.md).

**M4 closure (2026-10-29):** The user accepted M4 and authorized repository
work within the M5 scope and gate. This does not authorize any package
installation, service enablement, notifier change or software removal.

## M5 — packaging and Octopi migration

- [x] KDE tray/launcher and supervised service startup.
- [x] Arch packaging, install/uninstall and recovery documentation.
- [x] Authenticated LAN/VPN and reverse-proxy documentation.
- [x] Fixture-backed reboot/login persistence and single-notifier verification;
      live enablement remains separately gated.
- [x] Side-by-side feature-parity and rollback drill.
- [x] Secret-free settings export.

**Approvals required:** install package, enable service/autostart, disable the
old notifier, remove Octopi or remove the stale Pamac launcher. These are
separate decisions, not one blanket approval.

**Gate:** no coverage gap, duplicate notifier or failed rollback.

**M5 technical evidence (2026-10-29):** The deterministic Arch source and
package build, staged runtime, disposable install/remove, user-unit
enable/disable, exact notifier rollback/reapplication, network fail-closed and
secret-free export checks passed. The independent review's three medium
findings were resolved with wildcard-bind rejection, enabled-notifier gating
and an actual startup-owner rollback fixture. No package, service, notifier,
autostart entry or software on the host was changed. Details:
[M5 acceptance](docs/M5_ACCEPTANCE.md) and
[M5 validation](docs/research/m5-validation.md).

**M5 interface refinement evidence (2026-10-29):** The acceptance build adds a
faint version/build rail stamp, stationary viewport-top pointer-right help
panels, destination-aware Safety Checklist statuses and consistent
title/acronym casing, and removes the redundant Appearance preview. The
complete suite passed 278 tests, and the focused browser matrix passed across
the complete theme set and documented responsive boundaries.

**M5 closure (2026-10-29):** The user accepted M5 and authorized repository
work within the M6 scope and gate. This does not authorize package
installation, service enablement, notifier changes, software removal, release
publication or any live software mutation.

## M6 — hardening and release

- [x] Interrupted update and recovery drills.
- [x] Hostile metadata, unavailable update-source and alternative lock-holder tests.
- [x] Accessibility, responsive layout and performance closure.
- [x] Full security review, operator documentation and known-limitations list.

**Gate:** all acceptance scenarios pass or carry an explicit release blocker;
release is tagged only after independent end-to-end review.

**M6 technical evidence (2026-10-30):** Restart reconciliation now uses fresh
read-only provider evidence and never replays a plan; alternative and
owner-unknown pacman locks remain blocking and untouched; schema 6 migrations
are atomic and reject future databases; hostile Unicode format controls are
removed across provider, catalog, advisory and build-preview text. Indexed
server paging passed enforced 2,000- and 10,000-record profiles, while the
browser passed high-density, 400% reflow, API-compatibility and 205-row paging
checks. TypeScript, production build, lockfile, Python compilation and both
dependency audits passed. The complete suite passed **300 tests in 176.72
seconds** with one known third-party deprecation warning. Independent re-review
found no remaining critical, high, medium or low findings. Publication remains
explicitly blocked by the missing redistribution license, release provenance/
tag/signing decision and live AUR isolation; every first live mutation remains
separately gated. Details: [M6 acceptance](docs/M6_ACCEPTANCE.md).

**M6 closure (2026-10-30):** The user accepted M6. This closes the currently
defined milestone plan. Acceptance does not resolve the redistribution-license,
release provenance/tag/signing or live AUR isolation blockers, and does not
authorize release publication, package installation, service or notifier
changes, software removal or any live software mutation.

## M7 — release candidate and controlled deployment

- [x] Record the owner-selected redistribution license, authenticated source
      provenance, release-tag policy, signing policy and generated-asset
      provenance.
- [x] Produce and compare clean, disposable Arch builds with checksums, a
      dependency/license inventory and a software bill of materials.
- [x] Test AUR build isolation against hostile inputs, or keep live AUR
      execution visibly disabled with no override.
- [x] Prove package install, startup, backup, restore, upgrade and uninstall in
      a disposable system before requesting any managed-computer pilot.
- [x] Prepare the separately gated, loopback-only, read-only host pilot plan
      that preserves existing services, notifier and user state. Execution is
      not authorized.
- [x] Complete the release-candidate test matrix and independent review.

**Proposed gate:** M7 acceptance creates a reviewed release candidate only.
Public release publication, managed-computer package or service changes,
notifier migration and every first live software mutation remain separate
approvals. Full scope and decision points:
[M7 proposal](docs/M7_PROPOSAL.md).

**M7 scope authorization (2026-10-30):** The user accepted the proposed scope
and authorized project-local implementation. Owner license, repository/tag,
signing, initial AUR boundary and managed-computer pilot decisions remain
explicit decision points; no host installation or public release is implied.

**M7 decision-gate evidence (2026-11-01):** Primary-source research now
separates license, tag, signature, checksum, clean-build, SBOM and AUR-isolation
claims. At that initial decision gate, the owner decision sheet and generated-
asset provenance record were ready, and a project-local tool had generated
locked CycloneDX runtime inventories for 18 Python and 3 browser components.
No Git repository, key, release artifact, package installation or host change
had been created at that point.

**M7 partial owner decisions (2026-11-01):** The owner selected
`AGPL-3.0-or-later`, authorized a local Git baseline with no remote push, and
chose to withhold the release candidate until AUR isolation passes. The exact
copyright-holder text and release-proof method were still undecided at that
point. No signing-key use or live AUR build occurred.

**M7 release-proof decision (2026-11-01):** The owner selected one
owner-controlled OpenPGP release key to prove both signed Git release labels
and downloaded release files. The owner later authorized creating the dedicated
key through a local password prompt. Its primary fingerprint is
`721E ED2D 67AD EE74 D26E 75C5 7DAF 7D14 02C8 082E`; only the public key is in
the project. On 2026-11-01, the owner authorized using this key through a local
password prompt to sign the final local M7 release label and files. The label
and detached file signatures now verify; publication remains separately gated.
Candidate labels use signed annotated
`v<version>-rc.<number>` names and are never moved or reused; the first is
`v0.6.0-rc.1`.

**M7 copyright decision (2026-11-01):** The owner supplied the exact public
record `Copyright © 2026 Erik Winblad`. It is recorded separately from the
unaltered official AGPL text and will ship in `NOTICE`.

**M7 generated-asset decision (2026-11-01):** The owner approved the recorded
AI-generated loop logo as an official Updatarr asset distributed under
`AGPL-3.0-or-later`. The missing exact image model/version remains a
reproducibility limitation, not a release blocker.

**M7 implementation progress (2026-11-01):** Local Git provenance begins at
commit `373cb91`; no remote or push exists. Project/package metadata now records
the selected `AGPL-3.0-or-later` license. The closed AUR isolation Module hides
commands, mounts and environments behind one reviewed-tree interface and passes
bounded safe, hostile and split-package fixture checks under a 512 MiB test
ceiling. Live AUR remains blocked by isolated source acquisition, a clean
dependency root and dependency preparation. Deliberate memory/process pressure
tests were removed after the first cgroup check caused an unacceptable desktop
notification; no such test may be run again.

The digest-pinned disposable Arch builder completed two initial networkless
package builds under a 2 GiB ceiling. Their 208-file normalized payload
manifests and builder-package inventories match; only generated package
build-time metadata differs. A separate networkless disposable system passed
package install,
disabled-by-default startup checks, loopback startup, SQLite backup and offline
restore, package upgrade, downgrade recovery, uninstall and user-state
preservation. The drill corrected the Arch runtime dependency name to
`uvicorn`. The managed computer was not changed. Final evidence generation and
independent review later completed as recorded below.

**M7 security and build evidence (2026-11-01):** The reviewed-tree AUR
isolation seam now uses bounded streaming logs, a verified memory-backed build
tree under cgroup limits, no-follow input copying, aggregate artifact limits
and exact package identity checks. Its final 23 focused tests and independent
re-review passed with no remaining critical, high or medium implementation
findings. This accepts the isolation boundary selected in owner choice 4B; it
does not enable live AUR. Source acquisition, a clean dependency root and
dependency preparation remain unavailable with no override. The corrected RC2
clean builds have identical 213-file normalized payload manifests, the
disposable package lifecycle passed, and the complete suite passed 324 tests. Exact
evidence is recorded in the M7 validation documents.

**M7 RC1 rejection (2026-11-01):** The signed local label `v0.6.0-rc.1` remains
immutable at commit `ee18e9a7f789404ece81488f150fd02e33837a42`, but that candidate
is rejected and must not be published. Final package inspection found the old
demonstration password in the installed runtime, browser and packaged README.
The replacement removes every built-in development password, requires an
explicit password even in development mode and is protected by shipped-input
and package-level regression checks.

**M7 RC2 evidence (2026-11-01):** The corrected signed local label
`v0.6.0-rc.2` identifies commit `660f4918ebc612e63953a0014199dfe481c100ef`.
Two networkless clean builds have identical 213-file normalized payloads and
183-package builder inventories. Neither extracted package contains either
known development-password string. The disposable lifecycle, fresh SBOM/license
evidence, detached file signatures and signed-label verification all pass.
The full suite passed 324 tests. Final independent candidate review found no
critical, high or medium findings; publication and every host/live-action gate
remain unchanged.
