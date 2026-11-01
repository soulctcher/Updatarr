# Known limitations and release blockers

**Reviewed:** 2026-11-01
**Applies to:** Updatarr M7 work in progress

These limits are intentional and visible. A blocked capability must not be
treated as working merely because its update source can be read.

## Release blockers

1. **Copyright-holder text is pending.** The owner selected
   `AGPL-3.0-or-later` and the package now records it, but public release remains
   blocked until the exact copyright-holder record is supplied and checked.
2. **Authenticated release provenance is incomplete.** A local Git baseline
   now exists, but there is no approved remote, signed release label or signed
   artifact. Generated-browser-asset provenance is recorded with its remaining
   limitation.
3. **Generated-logo terms are not confirmed.** The asset, prompt description
   and digest are recorded, but the exact image model/version and applicable
   generated-output terms were not retained. Do not infer redistribution
   permission from the image-generation documentation.
4. **Live AUR builds remain blocked.** PKGBUILDs are arbitrary user-level code.
   The bounded M7 prototype hides credentials, state and unrelated user files
   in fixture tests, but isolated source acquisition, a clean dependency root
   and independent review are incomplete. There is no override.
5. **Every first live software-changing path remains unapproved.** Repository,
   Flatpak, firmware, startup-related, toolchain and portable-app changes have
   fixture or simulator coverage only. Each first live trial still needs the
   separate approval named in [MILESTONES.md](../MILESTONES.md).

The clean-container package build and disposable package lifecycle drill have
passed. Those results do not install or authorize Updatarr on the managed
computer and do not resolve the live AUR isolation blocker.

## Unsupported or deliberately limited behavior

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
