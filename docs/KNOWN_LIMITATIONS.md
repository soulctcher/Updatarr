# Known limitations and release blockers

**Reviewed:** 2026-11-01
**Applies to:** Updatarr M7 work in progress

These limits are intentional and visible. A blocked capability must not be
treated as working merely because its update source can be read.

## Release blockers

1. **Public release remains unauthorized.** RC1's local signed label and files
   verify, but RC1 is rejected because its package contained a built-in
   demonstration password. Corrected RC2 evidence is pending, and there is no
   approved remote, push or public upload.
2. **Live AUR builds remain blocked.** PKGBUILDs are arbitrary user-level code.
   The bounded M7 prototype hides credentials, state and unrelated user files
   in fixture tests, but isolated source acquisition, a clean dependency root
   and dependency preparation are incomplete. There is no override.
3. **Every first live software-changing path remains unapproved.** Repository,
   Flatpak, firmware, startup-related, toolchain and portable-app changes have
   fixture or simulator coverage only. Each first live trial still needs the
   separate approval named in [MILESTONES.md](../MILESTONES.md).

RC1's clean-container builds, signatures and disposable package lifecycle drill
passed before package inspection rejected it. Corrected RC2 must repeat those
checks. None of this work installs or authorizes Updatarr on the managed
computer or enables live AUR.

## Unsupported or deliberately limited behavior

- Generated-browser-asset provenance is recorded, and the owner approved the
  logo's inclusion under `AGPL-3.0-or-later`. The exact image model/version was
  not retained, so bit-for-bit regeneration is unavailable. This is a
  reproducibility limitation, not a release blocker.
- Updatarr does not install unsigned local package bundles, add package-signing
  keys, weaken signature checks or enable untrusted repositories/remotes.
- Package rename and replacement relationships are shown only when the update
  source supplies trustworthy evidence. Otherwise the old and new identities
  remain separate; Updatarr does not guess.
- Foreign pacman packages are not automatically classified as AUR packages.
  Missing, orphaned, split and VCS AUR cases remain read-only or blocked until
  their exact identity and reviewed build path are known.
- Live Flatpak catalog search is not performed because it may refresh catalog
  metadata. Installed user and system scopes are read separately.
- Portable apps without supported embedded update information are reported as
  not supported. Pacman-owned files remain under pacman control.
- `uv` self-update is not enabled when Updatarr cannot prove how `uv` itself was
  installed. npm packages in a system-owned prefix are blocked.
- Firmware, startup-related software, toolchain and portable-app live execution
  remain disabled pending their individual first-live-trial gates.
- Direct public-Internet exposure and unattended remote software changes are
  unsupported. Remote review still requires confirmation on the managed
  computer; administrator work separately requires Polkit.
- The documented Caddy shape follows Updatarr's loopback-proxy contract: normal
  `X-Forwarded-*` values are accepted only from loopback and ignored for
  security decisions. Each actual deployment still needs the documented
  header-recording, TLS, Host, Origin, CSRF, cookie and event-stream checks
  before remote access is enabled.
- The tray is status-only and can lag the core by up to five seconds. It does
  not carry credentials or start software changes.
- Imported history can be incomplete because provider logs rotate or omit
  details. Updatarr labels the covered range and never uses imported history as
  proof that a current update succeeded.
- The initial product supports one administrator account and one managed Arch/
  EndeavourOS workstation. Multi-user roles and fleet management are outside
  this release.

## Recovery limits

After an interrupted update, Updatarr reports success only if a fresh result
check proves every expected version. A missing, failed or mismatched check
becomes **Needs Manual Recovery**. Updatarr never removes the pacman lock; a
lock with no visible owner remains blocking until an operator follows the
package manager's documented recovery procedure.

See [Upgrade and interrupted-run recovery](operations/UPGRADE_RECOVERY.md) for
the operator checklist.
