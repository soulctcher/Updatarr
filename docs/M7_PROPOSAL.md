# M7 Proposal: Release Candidate and Controlled Deployment

**Prepared:** 2026-10-30  
**Status:** scope accepted by the user on 2026-10-30; project-local M7 work authorized  
**Authorization:** project-local implementation only; retained gates below remain

M7 would turn the accepted M6 evaluation build into a traceable release
candidate and prove that it can be installed, started and removed safely. It
would not publish Updatarr, replace another updater or allow Updatarr to change
installed software.

## Why This Is the Next Milestone

M6 proved the application and its evaluation package, but deliberately left
three kinds of work unresolved:

- the owner has not selected a redistribution license or release-signing
  policy;
- the workspace has no authenticated revision and release-tag history; and
- live AUR builds do not yet have proven isolation from Updatarr secrets and
  unrelated user files.

Before live update trials, Updatarr also needs evidence from a clean package
build and a controlled installation that starts with every service disabled.
M7 addresses those gaps without combining them with a real software update.

## Proposed Work

### 1. Record Release Ownership and Provenance

- Prepare a plain-language license decision sheet and record the owner's
  selected redistribution license before producing a distributable artifact.
- Inventory dependency and bundled-asset licenses and stop if any selected
  license or asset use is incompatible.
- Record the generated logo and every other generated or modified visual asset
  in a provenance manifest, including its source, creation method and permitted
  use.
- Establish an owner-approved Git repository baseline for the accepted M6
  source, with a documented import point and reviewable release commits.
- Define the release-tag and artifact-signing policy. Signing keys and account
  credentials remain under the owner's control and are never placed in the
  repository or chat.

### 2. Produce a Verifiable Release Candidate

- Build the source archive and Arch package in a clean, disposable Arch build
  environment with all declared build dependencies present.
- Repeat the build and compare the source archive, installed-file manifest and
  normalized package contents. Any unavoidable metadata difference must be
  named and explained.
- Generate checksums, a dependency and license inventory, and a software bill
  of materials for the release candidate.
- Verify that the package contains only intended files, uses no workspace
  paths, ships no development password and enables no service or startup entry.
- Verify install, upgrade, downgrade recovery and uninstall in a disposable
  system before considering the managed computer.

The project-local `scripts/generate_m7_evidence.sh` tool may generate runtime
CycloneDX inventories and input hashes before the owner decisions. Its output
is evaluation evidence, not a release artifact or license determination.

The project-local `scripts/build_m7_arch_container.sh` drill uses a pinned Arch
base image, installs declared build tools only inside the builder image, then
runs the package build without network access under container memory, task and
CPU limits. It is preliminary clean-environment evidence; it does not replace
the final Arch clean-chroot gate.

### 3. Decide the Initial AUR Boundary

- Write and test a disposable AUR-build isolation prototype against hostile
  build scripts that attempt to read Updatarr state, credentials and unrelated
  user files or to escape their allowed workspace.
- Keep network access, writable paths, environment variables, process access
  and final package handoff explicit and minimal.
- Enable no live AUR build unless the isolation tests and independent security
  review pass.
- If adequate isolation is not ready, define the initial release boundary as
  read-only AUR discovery and review with build/install controls visibly
  unavailable. There is no override switch.

### 4. Prove Controlled Installation and Recovery

- First complete the full install/start/backup/restore/upgrade/uninstall drill
  in a disposable system.
- Prepare an exact managed-computer pilot plan showing files, package changes,
  service state, backup location, verification and rollback before requesting
  permission for any host action.
- Keep package installation, core service enablement, tray enablement, Octopi
  notifier changes and Octopi or Pamac removal as separate approvals.
- If a later host-pilot approval is granted, start loopback-only with live
  execution disabled and compare read-only inventory against the native tools.
- Prove that uninstall or rollback preserves the user's database, configuration
  and existing updater until the owner separately approves their removal.

### 5. Complete Release-Candidate Review

- Map every M7 requirement and risk to an exact test or an explicit retained
  blocker.
- Run the complete application, browser, packaging, recovery and security
  suites against the release candidate.
- Obtain an independent review of licensing records, provenance, package
  contents, AUR isolation status, installation behavior and rollback evidence.
- Publish a release-candidate acceptance packet with exact revision, artifact
  hashes, signatures, test results and remaining limitations.

## Owner Decisions Required During M7

M7 scope acceptance does not silently make these choices. Work must pause at
the relevant point for the owner to decide:

1. the redistribution license;
2. the Git repository and release-tag authority;
3. the artifact-signing method and key owner;
4. whether the first release keeps live AUR building disabled or waits for an
   accepted isolation design; and
5. whether to authorize a later read-only managed-computer installation pilot.

## Explicitly Outside M7

- Public release publication or upload.
- A live system-package, Flatpak, firmware, toolchain or portable-app change.
- Live AUR execution before isolation is accepted.
- Enabling a core or tray service on the managed computer without its separate
  approval.
- Disabling the Octopi notifier, removing Octopi or removing the stale Pamac
  launcher.
- Enabling LAN access, changing firewall or proxy settings, or handling owner
  signing credentials.

## M7 Acceptance Gate

M7 would be ready for acceptance only when:

- [x] the owner-selected license, Git provenance and signing policy are
      recorded and reflected in the package;
- [ ] two clean builds and a disposable install/upgrade/recovery/uninstall
      drill pass with exact evidence;
- [ ] checksums, the asset-provenance manifest, dependency/license inventory
      and software bill of materials match the reviewed revision;
- [x] AUR execution either passes the isolation/security gate or remains
      clearly disabled in the release candidate;
- [x] any approved read-only host pilot passes without enabling software
      mutation or changing the existing notifier;
- [ ] the complete suites and independent review have no unresolved critical,
      high or medium findings; and
- [ ] the user accepts the M7 release candidate.

No managed-computer pilot was approved during M7, so the conditional pilot
item required no host action. The exact plan remains available for a later,
separate approval.

M7 acceptance would establish a release candidate. Public publication, host
service changes and every first live software mutation would still require
their own explicit approvals.

## Scope Acceptance

- [x] User accepts this proposed M7 scope and authorizes project-local M7
      implementation. This does not authorize a host installation, service or
      notifier change, public release, signing-key use or live software
      mutation.
