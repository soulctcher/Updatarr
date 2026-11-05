# M7.2 Production Readiness Validation

**Prepared:** 2026-11-04  
**Status:** reviewed candidate ready for signing and authorized local installation  
**Authorized boundary:** official Arch build-tool installation, fixed local
canary, signed Git publication, Updatarr package installation and web/tray
restart; no actual AUR update build or installation

## Defects Being Corrected

The installed 0.6.1 build had two separate failures:

1. live AUR planning was constructed with a permanent false readiness value,
   so every AUR update remained blocked regardless of host preparation; and
2. `checkupdates` inherited the web service's `PrivateTmp=true` namespace,
   where pacman's `DownloadUser=alpm` could not own its temporary download
   directory. That made native update availability appear **Not Checked** even
   when Octopi reported current repository updates.

## Production Boundary

The M7.2 preparation command accepts no package, path, URL, executable,
environment or caller-selected argument. It checks fixed package-owned tools
and their current versions, maintains one fixed `devtools` clean root, verifies
a harmless root-owned local canary, proves a secret-free networkless user
namespace, builds the canary in a clean working copy, and transfers the
user-written artifact through one no-follow descriptor before writing a
short-lived root-owned prerequisite record. Missing, incomplete, expired,
tampered, changed-tool or permission-unsafe evidence fails closed.

An attempted AUR plan records the current evidence digest and stays blocked
from executable states. If the record changes or expires, Updatarr invalidates
that evidence. The record proves host prerequisites and a canary, not the
safety of a specific AUR recipe. Exact Git source, changes, dependencies and
output identities still require package-specific review, so AUR remains
outside **Update Ready Software** in this release. This path does not install
an AUR package or add an arbitrary command surface.

## Native Update Worker

The web service keeps `PrivateTmp=true`. Only the fixed package-owned
`checkupdates --nocolor` probe moves to a collected user transient unit with
`PrivateTmp=false`, `NoNewPrivileges=true`, owner-only temporary files and an
empty, rebuilt environment. Updatarr credentials and unrelated service
variables do not cross that seam.

Before the host's supported full upgrade installed the two pending repository
updates, the corrected workspace probe reported both:

- `python-opentelemetry-api 1.45.1-3 -> 1.45.2-1`
- `rsync 3.5.1-3 -> 3.5.2-1`

After that upgrade, the same adapter truthfully reported **Up to Date** rather
than **Not Checked**.

## Evidence To Complete

Completed before signing:

- frontend type checking and the production Vite build passed;
- the locked browser audit reported no known vulnerabilities;
- the complete suite passed **358 tests** with two environment-dependent skips
  and one existing Starlette deprecation warning;
- Python compilation, shell parsing and Git whitespace checks passed;
- independent review's two high and one medium AUR findings were reproduced,
  corrected and re-reviewed; no critical, high or medium findings remain;
- two isolated Arch builds produced the same normalized payload digest,
  `71001036284eb706c590b611bdfe27796fab81a9246a02138608ef2385263034`,
  and the same builder inventory digest,
  `a2cb2bf8ca6db33e144040b4e3a6fc74219f2bad6e9d68671b34362e03b682d0`;
- source archive SHA-256:
  `cc5f686dad505f11e586b07fd57ca9e337b0702d7d3a9bb1d56a211c170c9960`;
- selected package SHA-256:
  `f5d447a64135b02dc1ffc19cc549206fe9b3a20bb2c74364503bcd4434497d5a`;
  and
- the disposable lifecycle passed install, startup, backup, restore, upgrade,
  downgrade, removal and user-state preservation for the exact 0.7.0 package.

Still to record after the reviewed source is frozen:

- signed Git label, package, source and checksum verification;
- managed-host clean-build canary and prerequisite-record verification;
- local package replacement with database/configuration preservation;
- live browser, tray, native-source and AUR-message checks; and
- publication of the reviewed branch and signed label.
