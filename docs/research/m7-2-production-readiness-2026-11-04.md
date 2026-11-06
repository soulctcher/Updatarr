# M7.2 Production Readiness Validation

**Prepared:** 2026-11-04  
**Status:** RC4 candidate verified and ready for signing and authorized local installation
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
  `43ebcb3c8c706b16b78c7c3a9636b833fbe0ac5fc9ada1ac35da87830fcb6add`,
  and the same builder inventory digest,
  `a2cb2bf8ca6db33e144040b4e3a6fc74219f2bad6e9d68671b34362e03b682d0`;
- source archive SHA-256:
  `4425a184db5d73e425dfbf9d1404644cf7a12f0273cb854749072a26726c7135`;
- selected package SHA-256:
  `8ca6ac85df2f871e6b64b87de673502a097882d24e113275ada010d51cdb2d0c`;
  and
- the disposable lifecycle passed install, startup, backup, restore, upgrade,
  downgrade, removal and user-state preservation for the exact 0.7.0 package.

Still to record after the reviewed source is frozen:

- signed Git label, package, source and checksum verification;
- managed-host clean-build canary and prerequisite-record verification;
- local package replacement with database/configuration preservation;
- live browser, tray, native-source and AUR-message checks; and
- publication of the reviewed branch and signed label.

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
