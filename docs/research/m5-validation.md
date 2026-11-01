# M5 validation

**Date:** 2026-10-29  
**Scope:** packaging, supervised startup, tray/launcher, trusted network access,
settings export and reversible Octopi notifier migration  
**Safe boundary:** repository files, project-local tools, disposable package
roots, fixed read-only host checks and no service or software changes

## Result

The M5 implementation is ready for user review under its separate live-action
gates. The package, service and tray are unprivileged; installation does not
enable either service; the tray has one startup owner and one-instance locking;
the production listener fails closed; settings export excludes secrets; and the
migration assessment refuses a coverage gap, two notifiers or an untested
rollback.

No package was installed on the host. No user service, autostart entry, user
lingering, notifier or firewall setting changed. Octopi, PackageKit and all
update-source tools remain installed and unchanged.

## Requirement and risk evidence

| Requirement or risk | Evidence |
| --- | --- |
| Package must not start or enable itself | The package contains two unit files but no `.wants` link, XDG autostart entry, `/etc` payload, Polkit rule or install script. Offline enable/disable tests create exactly one core and one tray link in a disposable root and remove both on rollback. |
| Package inputs and paths must be reviewable | The PKGBUILD consumes the deterministic `updatarr-0.5.0.tar.gz` source, whose SHA-256 is recorded in the PKGBUILD. The build produced 131 entries with `/usr/bin/python` launchers and no workspace, home or temporary path. |
| Install and uninstall must preserve user state | A fakeroot pacman drill installed the package into an empty disposable root, added a sample user database, removed the package and proved the user database remained unchanged. |
| Core and tray must have separate lifetimes | The core is wanted by `default.target`; the tray is wanted by and part of `graphical-session.target`. Quitting the tray has no core stop action. The tray lock refuses a second instance. |
| Tray and browser must agree | The core writes only snapshot identity and summary to a mode-0600 runtime file in a mode-0700 directory. The tray counts **Ready to review**, reports blocked work separately, polls every five seconds and suppresses repeated notifications. |
| Production credentials must not fall back to the demo password | Startup requires an eight-character password unless development mode is explicitly enabled. Development mode is rejected on a direct non-loopback listener. |
| Remote access must remain authenticated HTTPS | Direct non-loopback startup requires a specific bind address, HTTPS origin, exact allowed host, readable certificate pair and an owner-only private key. Reverse-proxy mode requires loopback, an HTTPS public origin and proxy-managed TLS. |
| Proxy headers must not grant trust | Uvicorn proxy interpretation is disabled. Updatarr accepts forwarding headers only from its configured loopback proxy peer and ignores their values; other peers are rejected. Host, Origin, CSRF and local-confirmation rules still use configured/direct request facts. |
| Settings backup must exclude secrets | The authenticated download contains only format/version/time, appearance, update-source choices and saved review choices. Tests reject password, session, CSRF, inventory and update-plan fields. |
| Octopi replacement must not lose monitoring | Fixed trusted probes now use `checkupdates --nocolor` with its separate temporary database and `yay -Qua --aur` without starting an upgrade. Native and AUR results remain separate, and the AUR query does not reclassify every foreign package. |
| Migration must be reversible | The assessment requires complete source coverage, active supervised core, exactly one tray, the Octopi notifier both disabled and inactive, and a passed rollback. A disposable startup-owner drill saves the exact Octopi entry, selects Updatarr, restores Octopi byte-for-byte and reapplies Updatarr while keeping exactly one owner. |

## Read-only host comparison

The installed Octopi package is `0.19.0-3`. One `/usr/bin/octopi-notifier`
process was active. Its user autostart file was mode `0600`, was not owned by a
package and differed from the packaged application launcher. A stale
`org.manjaro.pamac.manager.desktop` user launcher was also observed. These are
inventory facts only: nothing was disabled, edited or removed.

Octopi's existing configuration uses the ALPM backend and `yay`, so native and
AUR notification coverage are migration requirements. The fixed M5 read-only
probes completed with trusted package owners. At 2026-10-29 11:46 UTC, the
separate-database native check reported three updates and the AUR-only helper
query reported four. Neither command installed, upgraded or removed software.
The exact results expire after one hour and are not claimed as current later.

## Package and recovery drill

The deterministic source archive passed makepkg checksum verification with
SHA-256 `4589f232dce11e4a544b9df1b14dbd8958f1d22005664dcbc3700a5e89dc2b5a`.
A disposable source build produced:

```text
updatarr-0.5.0-1-any.pkg.tar.zst
131 archive entries
SHA-256 2ab9340249ac0c89a1d5a9a348af3d346cb4038e45ef0ed34e7ad7cbd27c873e
portable launchers: /usr/bin/python
forbidden package paths: none
```

The package started from an extracted root with an isolated XDG state, runtime
and cache tree; `/healthz` returned only `{"status":"ok"}`, the packaged SPA
returned the Updatarr page, the state directory was `0700` and the database was
`0600`. The package-manager drill then installed and removed the package in a
fakeroot and preserved the sample user state.

The target lacks Arch `devtools`, `namcap` and Caddy. No dependency was installed
to fill that gap. This evidence is therefore a checksum-verified clean-source
build and staged package-manager/runtime drill, not a clean-chroot, namcap or
live-proxy claim. The primary-source review and remaining release distinction
are recorded in [M5 packaging and network research](m5-packaging-network-research.md).

## Automated verification

The final verification set completed with these results:

```text
.venv/bin/python -m pytest -q
npm --prefix web run check
npm --prefix web run build
.venv/bin/python -m compileall -q src tests
desktop-file-validate packaging/desktop/io.github.updatarr.Updatarr.desktop
bash -n packaging/arch/PKGBUILD
makepkg --verifysource
```

- Complete Python suite: **278 passed** in **167.66 seconds**, with one known
  Starlette test-client deprecation warning.
- Focused deployment, provider, tray and capability-probe suite after the
  review fixes: **92 passed**.
- Final archive/package consistency check: **24 passed**.
- All **7 interface-refinement browser tests** passed in the final complete
  suite. They cover desktop/mobile, all 18 themes, the 681/680/390/320
  responsive boundaries, pointer and keyboard help, 200% zoom,
  stationary top-layer/right-side help placement, destination-aware checklist
  statuses, build stamp contrast, title or acronym casing and removal of the
  redundant Appearance preview.
- TypeScript checking, Vite production build, Python compilation, desktop-file
  validation, PKGBUILD shell parsing and makepkg source verification passed.
- The final package contains 131 entries. Its extracted runtime returned
  `{"status":"ok"}`, served the Updatarr SPA, created its state directory as
  `0700` and its database as `0600`. Disposable removal preserved user state.

## Known gaps and separate gates

- Actual package installation is not approved.
- Actual core/tray enablement, login persistence, reboot persistence and KDE
  notification appearance require the separate service/autostart approval.
- Disabling/restoring the Octopi notifier is a separate approval. Removing
  Octopi and removing the stale Pamac launcher are two further separate
  decisions.
- Direct HTTPS and Caddy configurations have deterministic validation and
  primary-source review but no live listener/proxy trial on this host.
- The package is for local M5 evaluation. Publishing remains blocked until the
  owner selects a redistribution license and release-source signing policy.
- The existing M3 AUR build isolation blocker remains; M5 adds monitoring, not
  live AUR build execution.

## Independent review

The independent review initially found three medium issues: wildcard direct
binds, an enabled-but-inactive Octopi notifier and missing notifier rollback
fixture evidence. All three were fixed and re-reviewed. The final result is
**pass**. Its interface-refinement re-review found two further medium issues—
build-stamp contrast and one notice title—which were also fixed and re-reviewed.
The final correction review then verified stationary, reachable help panels,
status links only for real Updatarr destinations and the simplified Appearance
section. No critical, high or medium finding remains. See
[M5 independent acceptance review](m5-independent-review.md).
