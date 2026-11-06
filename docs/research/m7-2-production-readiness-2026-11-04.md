# M7.2 Production Readiness Validation

**Prepared:** 2026-11-04  
**Status:** RC4 signed, published, installed and verified on the managed host
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

## Verification Evidence

Completed before signing:

- frontend type checking and the production Vite build passed;
- the locked browser audit reported no known vulnerabilities;
- the final complete suite passed **360 tests** with two environment-dependent skips
  and one existing Starlette deprecation warning;
- Python compilation, shell parsing and Git whitespace checks passed;
- independent review's two high and one medium AUR findings were reproduced,
  corrected and re-reviewed; no critical, high or medium findings remain;
- two isolated Arch builds produced the same 230-file normalized payload digest,
  `a05f4c45e82e3acff5044a78c4f7cc1260f7a3434951dcaa398a32e1a5bf342d`,
  and the same builder inventory digest,
  `a2cb2bf8ca6db33e144040b4e3a6fc74219f2bad6e9d68671b34362e03b682d0`;
- source archive SHA-256:
  `c604de0a33d54b03cc59f331a1f07de0864d322f08dbb0fcdf084c0b00866c8c`;
- selected package SHA-256:
  `e8a7ba0d7601bcef1b7ff3b019b377fbea9397c9c21254444f6fca9eaaad151e`;
  and
- the disposable lifecycle passed install, startup, backup, restore, upgrade,
  downgrade, removal and user-state preservation for the exact 0.7.0 package.

Completed after the reviewed source was frozen:

- signed label `v0.7.0-rc.4`, source, package and checksum signatures all
  verified from a fresh public-key-only keyring;
- the managed-host clean-build canary wrote a current root-owned prerequisite
  record and retained artifact, both mode `0444`;
- package `0.7.0-4` installed with **268 files and zero altered files**;
- the database and pre-install backup passed SQLite integrity checks, while the
  configuration SHA-256 remained
  `ca6225f4dd953094455c9da2d9e4c8fe406f66dee3014dfc02c2c022f67aa91a`;
- core and tray are active, with core still disabled and tray still enabled at
  login; `PrivateTmp=true`, `NoNewPrivileges=true` and `UMask=0077` remain;
- a fresh live check reported native packages **Up to Date** and five AUR
  updates needing exact source/dependency review, with zero AUR items in the
  install-ready set;
- the installed browser showed Version 0.7.0 / Build M7.2 without horizontal
  overflow or page errors; and
- public branch `main` plus signed label `v0.7.0-rc.4` were published at
  <https://github.com/soulctcher/Updatarr>.

The retained pre-install backup is
`~/.local/state/updatarr/backups/pre-m72-0.7.0-rc4-2026-11-06.db`, SHA-256
`ceb0e194643861a5139df677d74649473c868c7c9ebe048f36382a91f17353b9`.
No actual AUR package was fetched, built or installed by Updatarr.

## RC1 Host Rejection

The signed `v0.7.0-rc.1` package installed cleanly, but the first managed-host
canary failed closed before source verification because `makepkg` requires a
writable build directory even for `--verifysource`. The root-owned canary input
must remain read-only, so RC2 supplies a separate private user-owned `BUILDDIR`
alongside the already separate source, log and package destinations. RC1 did
not write a readiness record and must not be published as the current build.

## RC2 Host Rejection

The signed `v0.7.0-rc.2` package corrected the writable output boundary and
installed cleanly. Its managed-host canary reached the Bubblewrap isolation
check and failed closed because Python adds fixed `PWD=/` and
`LC_CTYPE=C.UTF-8` bootstrap variables inside Bubblewrap's otherwise cleared
environment. A direct networkless namespace observation confirmed the home was
absent, network access returned `ENETUNREACH`, and the complete environment was
exactly `PATH`, `PWD` and `LC_CTYPE`. RC3 checks those exact names and values;
it does not permit arbitrary inherited variables. RC2 issued no readiness
record and must not be published as the current build.

## RC3 Service Rejection

The signed `v0.7.0-rc.3` package completed the managed-host canary and wrote a
valid root-owned readiness record. Direct assessment passed, but the packaged
web service rejected the same record. Its retained `PrivateTmp=true` boundary
uses a restricted user namespace in which host UID 0 is unmapped and therefore
appears as Linux's overflow UID. RC4 accepts that visible owner only when the
current UID map proves root is unmapped. A normal namespace still requires UID
0, and missing or malformed mapping evidence fails closed. A transient unit
with the packaged service's `PrivateTmp`, `NoNewPrivileges` and umask settings
successfully assessed the corrected rule before RC4 was frozen.
