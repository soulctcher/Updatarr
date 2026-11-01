# M4 provider safety research

**Research date:** 2026-10-27  
**Scope:** Firmware, boot-affecting native updates, AppImages, developer
toolchains and preview-only maintenance  
**Source policy:** Primary project documentation, specifications, source and
first-party Arch/systemd manuals only

## Result

M4 can safely add detection, safety results, simulation and plans that cannot
change after review for these update sources. It must not treat them as
variations of one generic updater. Each source has a different owner, trust
rules, group of items that must update together and sign that work is complete.

The safe M4 boundary is:

- firmware is identified by fwupd device and release identities and retains
  fwupd's power, activation, shutdown, reboot and replug requirements;
- kernels, DKMS, initramfs and bootloaders stay in the native full-upgrade
  transaction, with a boot-risk view and read-only safety check;
- an AppImage is replaceable only when it is a registered, user-owned regular
  file with supported embedded update information and no pacman owner;
- rustup, Cargo, fnm, npm and uv are separate scopes whose executable owner,
  data folder and installation source must be established independently;
- maintenance stays separate from update discovery and shows proposed files only
  when the underlying tool has a genuinely read-only check or dry run.

This research authorizes no live update, metadata refresh, cleanup, helper
installation or change to the computer. The first real firmware,
startup-related, toolchain, AppImage-replacement and cleanup runs remain
separate approvals.

## 1. Firmware through fwupd

### Verified behavior

`fwupdmgr` documents `get-devices`, `get-updates`, `get-releases`,
`get-remotes`, `get-history` and `get-results` as inspection commands. It also
warns that human-readable terminal output is not stable and recommends `--json`
for parsing. `refresh`, `update`, `install`, `activate` and remote-management
commands change state; `activate` can make a device temporarily unavailable.
`check-reboot-needed` is the explicit reboot-state check. A successful command
with nothing to do can return exit code 2, which is not a generic failure.
[fwupdmgr reference](https://github.com/fwupd/fwupd/blob/main/src/fwupdmgr.md)

Firmware updates do not all finish the same way. fwupd's public flags distinguish
updates that work only in an offline environment, require external power, need
a reboot, need a shutdown, need separate activation, wait for a replug, disappear
after updating, or load only after activation or power cycling. Those states
must not be collapsed into one “restart needed” value.
[fwupd device flags](https://github.com/fwupd/fwupd/blob/main/libfwupd/fwupd-enums.h)

fwupd can inhibit an otherwise known device when a prerequisite is not met.
Power and battery thresholds are device-level requirements, and a device below
its threshold is prevented from starting an update.
[fwupd plugin tutorial](https://fwupd.github.io/libfwupdplugin/tutorial.html)

Firmware releases expose a stable release ID as well as version, remote,
checksums, size, urgency, locations and install duration. Updatarr should retain
these fields rather than identifying an update only by its display name and
version.
[Fwupd release API](https://fwupd.github.io/libfwupd/class.Release.html)

Firmware trust is also provider-owned. In the normal LVFS flow, LVFS signs the
firmware and metadata carried in the cabinet, and fwupd's per-system keys answer
whether the update came from a configured trusted source; that is separate from
any signature that the device itself validates on the payload.
[fwupd trust model](https://github.com/fwupd/fwupd/blob/main/docs/only-trusted.md)

### Updatarr contract

Read-only discovery should use JSON and preserve unknown fields so a newer fwupd
does not silently lose safety information. Each discovered update should
include at least:

- device ID and GUIDs;
- current device version, release ID, target version and cabinet checksums;
- remote ID and whether that remote is currently enabled;
- updatable/inhibited state, problems, battery level and threshold;
- offline, power, reboot, shutdown, activation, replug and disappearance flags;
- user requests or consent text supplied by fwupd.

The plan must lock those values after review and read them again immediately before
execution. An unknown flag, changed current version, changed checksum, changed
remote state, newly inhibited device or unmet power requirement invalidates the
plan rather than being ignored.

Updatarr must never enable a disabled remote, weaken a fwupd requirement, use
force/ignore-requirements flags or turn a branch switch, downgrade or reinstall
into an ordinary update. fwupd explicitly exposes flags that bypass requirements
or force an operation, so absence of those flags is part of Updatarr's closed
operation shape.
[fwupd install flags](https://fwupd.github.io/libfwupd/flags.InstallFlags.html)

A firmware run is not complete merely because preparing the update succeeded. Updatarr must
record one of the following plain-language follow-up states and reconcile it
through fwupd history/results and fresh device discovery:

| Provider result | Updatarr meaning |
| --- | --- |
| Applied live and verified | Finished |
| Staged for the offline environment | Restart to continue |
| `NEEDS_REBOOT` | Restart to finish |
| `NEEDS_SHUTDOWN` | Shut down to finish |
| `NEEDS_ACTIVATION` | Activation still required |
| Waiting for replug or power cycle | Follow the device instruction |
| Device will disappear | Result cannot be verified immediately |
| Inhibited or unmet requirement | Blocked, with the exact requirement |

No firmware execution belongs in an all-devices shortcut. The plan and local
confirmation must show the exact device/release pair, required physical action,
power warning and completion state. Root-required work still passes through the
restricted system tool, which accepts only listed actions, after confirmation
on the managed computer.

## 2. Kernel, DKMS, dracut and startup safety checks

### Verified behavior

Arch supports full upgrades, not partial upgrades. Arch's maintenance guidance
also recommends checking Arch News before fundamental updates and states that a
kernel update normally needs a reboot before the new kernel is running.
[Arch system maintenance](https://wiki.archlinux.org/title/System_maintenance)

DKMS modules are normally rebuilt by pacman hooks during a kernel upgrade, but
the matching headers are required for each target kernel and builds can fail.
Arch calls out higher risk when a DKMS module is needed for boot or essential
hardware.
[Arch DKMS guidance](https://wiki.archlinux.org/title/Dynamic_Kernel_Module_Support)

Pacman hooks can run before or after a transaction. Local hooks override
packaged hooks, and a same-named link to `/dev/null` disables a hook. Therefore
the installed package list alone does not prove that the expected DKMS or
initramfs hook will run.
[alpm-hooks(5)](https://man.archlinux.org/man/alpm-hooks.5)

dracut creates the initramfs used for early userspace and supports read-only
configuration reports such as `--printconfig`, `--print-cmdline` and
`--list-modules`; generation commands such as `--regenerate-all` write startup
files and are not read-only safety checks.
[dracut(8)](https://man.archlinux.org/man/dracut.8)

Boot layouts vary. `bootctl status` reports firmware and the bootloader used,
while `bootctl list --json=` can report Boot Loader Specification entries.
systemd-boot may coexist with other loaders, so `bootctl is-installed` alone
does not prove it is the active or default loader.
[bootctl(1)](https://www.freedesktop.org/software/systemd/man/latest/bootctl.html)

`dkms status` reports each module/version/kernel state and explicitly identifies
broken entries whose source is missing. Its build, install and autoinstall
operations change the computer; they are not harmless checks.
[dkms(8)](https://man.archlinux.org/man/dkms.8)

### Updatarr contract

Kernel, header, DKMS, initramfs, microcode and bootloader packages remain members
of the one native full-upgrade group. M4 adds a risk classification to that
group; it does not create a second kernel updater or detach selected packages.

Before a startup-related system plan can become executable, its read-only
safety check should record:

1. the running kernel release and installed/target kernel package versions;
2. all installed DKMS module states and matching target-kernel headers;
3. the active initramfs generator and effective pacman hooks, including local
   overrides and disabled packaged hooks;
4. computed dracut configuration when dracut is active;
5. bootloader type, boot entries, boot/ESP/XBOOTLDR mount paths, free space and
   whether referenced kernel/initramfs files are present;
6. whether a tested recovery or snapshot path actually exists; absence is
   reported honestly and never rewritten as “rollback available.”

The plan is blocked when the boot layout cannot be established, required headers
are missing, an effective generation hook is disabled or unknown, a critical
DKMS entry is broken, a required startup file is missing, or the target startup
filesystem lacks the required space. Non-critical uncertainty remains a visible
risk requiring review; it is not silently treated as safe.

Pacman's normal hooks make the change. Updatarr must record their exact
output, treat hook failure as transaction failure or manual recovery, and only
set “restart recommended” after the transaction outcome is known. It must not
claim the new kernel is active until the running kernel observed after a reboot
matches the installed target.

## 3. AppImage staged replacement

### Verified behavior

Update information is optional in the AppImage specification and an AppImage can
describe exactly one transport. Defined forms include direct zsync and GitHub
release zsync. An AppImage may also carry a signature, but the mere presence of
that section does not prove that a trusted signature was validated.
[AppImage update-information specification](https://github.com/AppImage/AppImageSpec/blob/master/draft.md#update-information)

Official AppImage documentation says that the update location and method travel
inside the AppImage and that not every AppImage is updateable. Its documented
update path verifies file integrity before replacement, while the same document
describes signature validation in that path as not yet implemented.
[AppImage update documentation](https://docs.appimage.org/packaging-guide/optional/updates.html)

Displaying an embedded signature is not validation. The official signature
guide requires an external verifier; Updatarr must also have a configured trusted
key relationship before “signed” can mean “trusted.”
[AppImage signature documentation](https://docs.appimage.org/packaging-guide/optional/signatures.html)

`appimageupdatetool -j` is an update check: exit 0 means no update, 1 means an
update is available and other non-zero values mean error. This check does not
replace the file.
[AppImageUpdate check interface](https://github.com/AppImageCommunity/AppImageUpdate/wiki/Self-updating-AppImages)

Pacman can identify the package that owns a path with `-Qo`; that ownership check
is the authoritative boundary between a portable file and a native-managed file.
[pacman query options](https://man.archlinux.org/man/pacman.8.en)

### Updatarr contract

Automatic AppImage work is enabled only when all of these are true:

- the path was explicitly registered or found inside an approved folder with a
  fixed search limit;
- it is a regular file, not a symlink, owned and writable by the managed user;
- `pacman -Qo` reports no package owner;
- the file is a supported AppImage type with one recognized update-information
  transport;
- the configured updater can perform a check without replacement;
- the applicable integrity and trust policy can be stated truthfully.

A missing update-information section, unsupported transport, ambiguous owner,
package-owned path, symlink, inaccessible file or unverifiable required trust
policy produces “Not supported” with the reason. It never produces a working
update button.

The frozen replacement plan should bind canonical path, parent directory,
device/inode, owner, mode, size, digest and exact update-information value. The
download goes to a new regular file in the same directory/filesystem. Updatarr
then checks the new file's type, expected integrity and configured trust,
rechecks the original identity/digest, and retains a recoverable previous copy
before replacement. A successful `os.replace()` on one filesystem completes the
replacement as one step. It can fail across filesystems, which is why the new
copy must be prepared in the same folder as the current file.
[Python `os.replace`](https://docs.python.org/3/library/os.html#os.replace)

Post-replacement verification must confirm the path digest/mode and that the new
AppImage remains executable. Cleanup of the previous copy is a separate
maintenance action, not an automatic part of replacement acceptance.

## 4. rustup and Cargo

### Verified behavior

`rustup update` changes installed toolchains and can also self-update rustup.
`--no-self-update` prevents that extra change, and distributor builds
may disable self-update entirely.
[rustup basic usage](https://rust-lang.github.io/rustup/basics.html)

The active Rust toolchain can depend on a command-line selector, environment
variable, directory override, nearby `rust-toolchain.toml`, or the default.
`rustup show` reports the active result, so service-directory output must not be
assumed to match an interactive project directory.
[rustup overrides](https://rust-lang.github.io/rustup/overrides.html)

`cargo install --list` inventories Cargo-managed binary crates. Install roots
can come from a command option, environment, Cargo configuration, `CARGO_HOME`
or the normal home directory, and installed sources may be crates.io, another
registry, Git or a local path. Cargo has no stable update-all/dry-run contract;
its documented dry run is unstable.
[cargo install](https://doc.rust-lang.org/cargo/commands/cargo-install.html)

### Updatarr contract

The rustup executable and rustup-managed toolchains are separate ownership
questions. If pacman owns the rustup executable, Updatarr may still describe
user toolchains, but it must suppress rustup self-update and leave the executable
to the native package transaction. Toolchain discovery records rustup home,
installed toolchain, default/active selection and overrides; an update must not
silently change the default or a project's pinned selection.

Cargo entries retain install root, source, version and known installation
settings. Only a registry-sourced, tracked, user-owned entry that Updatarr can
reproduce exactly may become updateable. Git, local path, untracked, unknown-root
or ownership-conflicting entries remain disabled. Updatarr never uses Cargo's
force-overwrite path.

## 5. fnm and npm

### Verified behavior

fnm can itself be installed by a script, Homebrew, Cargo, another package
manager or a manually downloaded binary. Its official upgrade instructions are
installation-method specific, so the fnm binary has no universal self-update
operation.
[fnm README](https://github.com/Schniz/fnm/blob/master/README.md)

fnm separates listing installed versions, listing newer online versions, installing,
selecting the current version and changing the persistent default. Installing a
version does not inherently authorize changing the default.
[fnm command reference](https://github.com/Schniz/fnm/blob/master/docs/commands.md)

npm documents `npm outdated -g --depth=0` as the global update check and
`npm update -g NAME` as a named global update. In global mode, packages live
under its configured package folder. A folder reserved for system packages and
a user-owned folder therefore have different owners.
[npm global update guidance](https://docs.npmjs.com/updating-packages-downloaded-from-the-registry/) ·
[npm folders](https://docs.npmjs.com/cli/v11/configuring-npm/folders/)

### Updatarr contract

fnm discovery runs as the managed user with an explicit fnm data directory and
configured Node distribution mirror. It records installed versions, current
version, persistent default and project version files separately. A new Node
version may be installed only as an explicit version; switching the current or
default version is a separate choice. Updatarr updates fnm itself only when it
knows how fnm was installed and supports that method.

For each Node installation, Updatarr records the npm executable, prefix, global
root and package list as a distinct scope. It checks the npm binary, global
package directories and linked executables with `pacman -Qo`. A system or
package-owned prefix is read-only to npm: those packages are reported as
native-managed or unsupported, never overwritten with `npm update -g`. Project
`node_modules` are outside the global-provider scope.

## 6. uv

### Verified behavior

`uv self update` is supported for the standalone installer. When uv was
installed another way, self-update is disabled and the owning package manager
must perform the upgrade. Even the supported self-update reruns the installer
and can modify shell profiles unless explicitly prevented.
[uv installation and upgrades](https://docs.astral.sh/uv/getting-started/installation/)

uv-installed tools use dedicated environments. `uv tool upgrade` retains the
original constraints and installation settings, reinstalls executables even
when unchanged, and refuses to overwrite an executable it did not install unless
forced. uv warns against mutating tool environments directly with pip.
[uv tools](https://docs.astral.sh/uv/concepts/tools/)

uv can use existing system Python installations as well as uv-managed Python
downloads; `uv python list --only-installed` narrows discovery to installed
interpreters but does not by itself say who owns each interpreter.
[uv Python versions](https://docs.astral.sh/uv/concepts/python-versions/)

### Updatarr contract

Updatarr records the uv executable owner and how uv was installed separately
from `uv tool dir`, its executable directory, uv-managed tool environments and
uv-managed Python downloads. `uv self update` is enabled only for confirmed
standalone installations and uses the option that prevents shell-profile
changes. Package-manager, pip, Cargo or unresolved installations remain owned
by their original installer.

Only tools managed by uv may use `uv tool upgrade`; system Python,
project virtual environments and ordinary project dependency locks are outside
this update-source check. An executable collision is blocked, and Updatarr never enables
uv's force behavior to cross an ownership boundary.

## 7. Preview-only maintenance

Maintenance is not an update source. It gets a separate preview and, later, a
separate cleanup plan that cannot change after review, with its own confirmation
on this computer.

### Operations with a safe preview

- `paccache --dryrun` only finds package files that could be removed. Keep count, cache
  directories, installed/uninstalled filters and age filters affect that set and
  belong in the preview and eventual plan.
  [paccache(8)](https://man.archlinux.org/man/paccache.8)
- `pacman -Qdt`/`-Qdtt` query unrequired packages without removing them. These
  describe dependency state at one moment, so every proposed package and dependency relation
  needs revalidation before any eventual removal.
  [pacman(8)](https://man.archlinux.org/man/pacman.8.en)
- `journalctl --disk-usage` is a read-only usage measurement. Vacuum operations
  delete archived journals and have no documented dry run; current total usage
  is not an exact reclaim estimate because it includes active files that vacuum
  does not remove.
  [journalctl(1)](https://www.freedesktop.org/software/systemd/man/latest/journalctl.html)

### Operations that are not previews

`flatpak uninstall --unused` removes unused runtimes and extensions. Flatpak's
documented uninstall interface has no dry-run mode, and user and system
installations are separate scopes. Updatarr must not invoke uninstall to
“preview”; it should either build a conservative read-only inventory through a
tested API or mark exact Flatpak cleanup preview unsupported.
[Flatpak command reference](https://docs.flatpak.org/en/latest/flatpak-command-reference.html#flatpak-uninstall)

Similarly, metadata refreshes, store repairs, cache pruning, journal vacuuming,
unused-package removal and old-AppImage deletion change the computer. A preview may inspect
and calculate, but it may not perform one of those actions and then call the
result a dry run.

## 8. Cross-provider rules for M4

Every M4 update-source check should follow the same outer rules even though the
source-specific details differ:

1. **Detect the owner first.** Use pacman ownership for paths and retain the
   provider's data root, scope and installation method.
2. **Keep checking and changing separate.** A network lookup may produce
   “Not checked” or “Error”; it must not silently refresh local trust or source
   configuration.
3. **Lock the source's own identity after review.** Device/release/checksum,
   package/version/full-upgrade group, path/digest/update information, or
   tool/root/source must be frozen in the plan.
4. **Disable uncertainty accurately.** Missing information, unknown installation source,
   unsupported transport, ownership collision or unknown boot state is shown as
   “Not supported” or “Blocked,” with a plain-language reason.
5. **Revalidate at the final boundary.** Ownership, current version, digest,
   provider configuration and prerequisites must still match immediately before
   execution.
6. **Require confirmation on this computer for every change.** Firmware,
   user toolchains, AppImage replacement and cleanup are included even when no
   root privilege is needed. Polkit remains a separate step for root work.
7. **Verify the observed result.** Process exit alone is insufficient; use
   a fresh update-source list, running-kernel state, path digest or a fresh
   maintenance preview as applicable.

These rules keep M4's unsupported cases disabled and preserve pacman ownership,
disabled fwupd/Flatpak origins and provider trust settings unless an exact,
separately approved plan says otherwise.
