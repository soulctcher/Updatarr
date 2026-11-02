# M7 Managed-Computer Pilot Evidence

**Run:** 2026-11-02  
**Authorization:** exact signed RC2 package, missing declared runtime
dependencies, owner-only configuration and manual loopback-only read-only test  
**Result:** package installation and transient read-only test passed; the
packaged user unit failed its live-provider check and must not be enabled

## Exact Installed Inputs

- Signed candidate: `v0.6.0-rc.2` at
  `660f4918ebc612e63953a0014199dfe481c100ef`.
- Package SHA-256:
  `59a95be67a26776da10a365e7088cb16c3f3dd09fbca0141308411a3cc2ad666`.
- Release-key fingerprint:
  `721E ED2D 67AD EE74 D26E 75C5 7DAF 7D14 02C8 082E`.
- The detached signature and complete release checksum list passed from the
  public-only verification keyring before installation.

Pacman added exactly these packages and removed none:

| Package | Version | Reason |
| --- | --- | --- |
| `updatarr` | `0.6.0-1` | Exact reviewed RC2 package |
| `python-argon2-cffi` | `25.1.0-2` | Missing declared runtime dependency |
| `python-argon2-cffi-bindings` | `26.1.0-1` | Dependency of Argon2 |

`pacman -Qkk updatarr` reported 251 package files and no altered files. The
package installed no privileged helper, Polkit rule, XDG autostart file or
enabled service link.

## Preserved State and Configuration

The existing database passed `PRAGMA integrity_check`. A mode-0600 SQLite
backup was created under the owner-only Updatarr state directory and its
independent integrity check passed before the installed application opened the
database.

The owner chose a new password through a local graphical dialog. It was never
printed or placed in project evidence. The mode-0600 configuration binds only
to `127.0.0.1:8788`, uses the exact loopback origin and hosts, and selects live
read-only provider mode.

The prior database contained an older Argon2 verifier, so changing the
environment file alone correctly did not replace the stored credential. The
built-in managed-host recovery seam replaced only that verifier, revoked three
old sessions and recorded a secret-free audit event while the service was
stopped. Database integrity remained `ok`; the exact authentication repro then
changed from HTTP 401 to HTTP 200. The temporary verification session was
revoked.

## Read-Only Baseline and After-State

- Before-state probe SHA-256:
  `3d5a820dbed8e17639c8b3793b9019fcf4d4d748f351824a5b76f0925e249095`.
- After-state probe SHA-256:
  `a672adaf8c6c80457b73ef3d59810acb2a5df8a8ab7561705a5f5b1eb2892af9`.
- All 18 fixed probes completed in both captures.

The Flatpak applications, remotes and masks; firmware device record;
Rust/Cargo/fnm/npm/uv records; Octopi package and process; Octopi notifier
autostart hash; and stale Pamac launcher hash were unchanged. Native package
inventory added only the three named packages. Foreign-package inventory added
only the locally installed Updatarr package.

## Packaged User-Unit Failure

The package correctly left `updatarr.service` and `updatarr-tray.service`
disabled. A manual start of `updatarr.service` was unprivileged and loopback
only, and its health and browser endpoints worked. Its live check incorrectly
reported every installed command-backed provider as **Not supported**.

The deterministic native-provider repro expected any state other than
`not_supported` but received `not_supported`. Direct execution of the installed
probe passed. Isolating the unit properties proved:

| Context | Trusted pacman probe |
| --- | --- |
| Direct installed runtime | Passed |
| Transient user unit without extra hardening | Passed |
| `NoNewPrivileges=true` only | Passed |
| `UMask=0077` only | Passed |
| `PrivateTmp=true` only | Failed |

Inside this user service's `PrivateTmp` mount namespace, host-root-owned
`/usr/bin/pacman` appears with UID 65534. The trusted-executable policy requires
UID 0, so it rejects the executable as unsafe before pacman ownership can be
used. This affects the other root-owned trusted executables in the same way.

No packaged file or persistent unit override was weakened. The packaged unit
was stopped and remains disabled and inactive.

## Working Local Test

A non-enabled transient `updatarr-pilot.service` runs the exact installed
binary with `NoNewPrivileges=true`, owner-only permissions and the same
loopback configuration, but without `PrivateTmp`. Its read-only check passed:

- 1,828 software records;
- four native updates, matching `checkupdates`;
- six AUR updates, matching `yay`;
- 22 user and one system Flatpak applications, matching Flatpak;
- firmware, Rust, Cargo, fnm, npm, uv and bounded portable-app states remained
  distinct and truthful; and
- npm system-prefix software remained blocked while uv remained not supported.

The transient unit is active for owner testing at
`http://127.0.0.1:8788`. It is not enabled and will not start at login or boot.

## Manual Tray Test

The user separately requested a tray test. `updatarr-tray.service` was started
manually and remains disabled at login. Verification found:

- one unprivileged `updatarr-tray` process;
- one owner-only mode-0600 instance lock containing that process identity;
- one registered Plasma StatusNotifier item with icon name `updatarr`;
- an active tooltip reporting **10 ready to review** from the shared core
  status file; and
- a second tray launch exited successfully without creating another process.

The existing Octopi notifier remains active. The tray can open the canonical
loopback page but owns no credentials, update policy or execution authority.

## Required Follow-Up

RC2 must not be published or enabled as the normal service. A corrected
candidate needs a narrow trusted-executable design that remains safe inside the
accepted user-service isolation, a regression test that reproduces the mapped
root ownership, complete package rebuild and lifecycle evidence, and an
independent review. Removing `PrivateTmp` from the permanent packaged unit is
not the accepted fix.

Enabling either service at login, notifier migration, Octopi/Pamac removal, LAN
access, live AUR execution and every software-changing action through Updatarr
remain unauthorized.
