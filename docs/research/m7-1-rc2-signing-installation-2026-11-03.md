# M7.1 RC2 Signing and Local Installation — 2026-11-03

## Scope

The owner authorized the M7.1 workflow correction to be versioned, packaged,
signed, installed locally and restarted. This work did not publish a release,
push a remote ref, enable the core service at login, change notifier ownership
or run a software update through Updatarr.

## Reviewed Source

- Feature commit: `6f7b5ecd0ea24ac4571c5eca36fdf5f9568d97c2`
- Lifecycle-evidence correction: `415d755d200821780396cde79a2ac9f6d4b3bf4b`
- Installed signed label: `v0.6.1-rc.2`
- Signing subkey: `5BD6 C0A8 D98B 655A EAF0 5EC2 E689 CC8D 9BBB 0AA4`
- Source archive SHA-256:
  `7cd201142b60253af6f6f4379d05d7727b67a6830749dd58285de2efb1fb044d`

The earlier immutable `v0.6.1-rc.1` label is retained for audit history. Its
lifecycle script used a pacman option unavailable on the managed computer, so
that candidate was not installed. Independent review also required exact-one
package selection and a current-version source-archive test. RC2 contains all
three corrections.

## Verification

- Complete Python suite: **347 passed, 2 skipped**, with the existing Starlette
  `httpx` deprecation warning.
- TypeScript check, production Vite build, Python bytecode compilation, shell
  parsing and `git diff --check`: passed.
- Independent focused review: **90 passed**, one existing warning; no workflow
  or AUR safety regression.
- Two isolated Arch builds used the same pinned builder image. Their installed
  payload hashes and builder package inventories match. Whole package archives
  differ only because makepkg records the build time in package metadata.
- Installed package SHA-256:
  `59c10d02f863f40d26224ac9ed7b57be8f425e89ee94d709a44408d2383475b4`
- Release checksum-list SHA-256:
  `a58f043ab1786e7ef894058d444a328655f2dc4ca56038cb79294511ec641cfd`
- Package, source archive and checksum-list signatures verified in a fresh
  public-key-only GnuPG home. Every checksum passed.
- The disposable lifecycle passed installation of `0.6.0-2`, service startup,
  database backup and restore, upgrade to `0.6.1-1`, downgrade, removal and
  preservation of user state.
- Package inspection found 260 paths, no install script, no automatic service
  enablement, no autostart entry and no private signing key.

## Managed-Computer Installation

Before installation, the live database and its new backup both passed SQLite
integrity checks. The backup is:

`~/.local/state/updatarr/backups/pre-m71-0.6.1-rc2-2026-11-03.db`

Its SHA-256 is
`86005f351525861d096619bd1cfd4c6f2b2729bca204797d9e65f47a39eb9bba`.
It is owned by the user with mode `0600`. No update run was active.

The simulated transaction contained only the Updatarr upgrade. A graphical
Polkit prompt authorized pacman to replace `updatarr 0.6.0-2` with
`updatarr 0.6.1-1`. Package verification reports 260 files and zero altered
files. The configuration hash remained
`ca6225f4dd953094455c9da2d9e4c8fe406f66dee3014dfc02c2c022f67aa91a`,
and the post-install database integrity check returned `ok`.

The original service policy was preserved:

- `updatarr.service`: active, disabled at login
- `updatarr-tray.service`: active, enabled at login

Both processes run from the packaged `/usr/bin` entry points. The core listens
only on `127.0.0.1:8788`; `/healthz` returned `{"status":"ok"}`. Neither unit
restarted or failed after launch.

## Live Interface Check

A fresh headless Chromium session signed in to the installed loopback service.
The `?view=updates` link opened **Ready Updates** after authentication. **Check
Again** and **Update Ready Software** were present. Settings showed **Version
0.6.1 · Build M7.1**. Desktop `1280×900` and mobile `390×844` checks passed
without horizontal overflow, page errors or failed post-login requests.

Local screenshots are retained under `build/` as:

- `m71-live-ready-updates-desktop.png`
- `m71-live-settings-desktop.png`
- `m71-live-ready-updates-mobile.png`

## Retained Gates

The live view correctly reports the six detected AUR updates as needing
attention. Production AUR building is still fail-closed because the approved
clean-root build service and host tooling do not yet exist. This installation
does not resolve or bypass that gate. Public release, remote push, core startup
enablement, notifier migration and every live software mutation remain
unauthorized.
