# Read-only capability probe research

**Status:** M0 research; no commands in this document authorize software,
service, repository, firmware, boot, or snapshot changes  
**Researched:** 2026-10-24  
**Scope:** local capability and ownership discovery for the target
EndeavourOS/Arch workstation

## Decision

Updatarr should have a deliberately narrow **local inspection** probe. It may
read installed-package databases, configured scopes, cached metadata, mounted
filesystem information, and tool-owned inventory. It must not turn capability
detection into an update check.

The commands under **Safe local probe set** are suitable for the currently
authorized M0 read-only host probe when run as the logged-in user, without
`sudo`. They do not request an update, refresh remote metadata, install or
remove software, change a configuration, or deliberately acquire an update
transaction lock. A non-zero result such as “not installed,” “not owned,” or
“permission denied” is evidence to record, not a reason to elevate.

Commands under **Excluded from the local probe** are not safe substitutes.
Some are valid future update-source operations, but they require a separately
declared network, privilege, or mutation phase.

## Probe-wide rules

1. Locate a program and resolve its path before invoking it. Query that path
   with `pacman -Qqo -- PATH`. A missing owner means **unowned or unresolved**,
   not “user-managed.” `pacman -Qm` likewise means “not found in configured
   sync databases,” not “confirmed AUR.” Pacman's query operation and its
   `--owns`, `--foreign`, and `--native` filters are documented in the
   [pacman manual](https://man.archlinux.org/man/pacman.8.en).
2. Do not execute an arbitrary discovered file merely to obtain its version.
   `--version` and `--help` still execute the target program. Invoke only a
   known, expected tool after recording its resolved path and ownership.
3. Run every scope explicitly. In particular, keep Flatpak user and system
   installations separate and retain the full ref, origin, branch,
   architecture, commit, and installation scope.
4. Put timeouts and output-size limits around external programs. Preserve the
   exit code and standard error separately. A supported JSON flag does not
   guarantee that every installed historical version has the same schema.
5. Record tool version, resolved executable, pacman owner, command arguments,
   exit status, capture time, and whether cached information may be stale.
   Sanitize usernames, home paths, remote URLs containing credentials, device
   serials, and other host identifiers before committing fixtures.
6. Never retry a failed unprivileged probe with `sudo`. Report the capability
   as unavailable to the service account or requiring later administrator
   review.

## Safe local probe set

### Pacman and Arch ownership

| Question | Read-only command or method | Interpretation |
| --- | --- | --- |
| Installed package inventory | `pacman -Q` | Reads the local installed-package database. |
| Native/foreign classification | `pacman -Qn`; `pacman -Qm` | “Foreign” only means absent from configured sync databases. It does not prove AUR origin. |
| File or executable owner | `pacman -Qqo -- /absolute/path` | Returns the installed package that owns that exact path; a non-zero result is an unowned/unresolved path. |
| Package metadata | `pacman -Qi -- package-name` | Reads installed package metadata such as install reason and dates. |
| Configured repositories | `pacman-conf --repo-list`; selected `pacman-conf` directives | Parses pacman's effective configuration, including `Include` processing, without changing it. |
| Program versions | `pacman --version`; `pacman-conf --version` | Capability/version evidence only. |

`pacman-conf` is specifically a script-friendly query tool and guarantees that
its resolved values match pacman's configuration interpretation; see the
[pacman-conf manual](https://man.archlinux.org/man/pacman-conf.8).

Do not use the sync (`-S`), upgrade (`-U`), remove (`-R`), database mutation
(`-D --asdeps`/`--asexplicit`), or files refresh (`-Fy`) operations in this
probe. Even `pacman -Qu` only compares against the current live sync database
and can be stale. `checkupdates` safely isolates its sync database from the
live pacman database, but normally contacts mirrors and writes a temporary
database, so it belongs to a later declared **update check**, not capability
discovery. Its behavior and `--nosync` limitation are documented in the
[checkupdates manual](https://man.archlinux.org/man/extra/pacman-contrib/checkupdates.8.en).

### yay and eos-update

After resolving each executable and pacman owner:

- `yay --version` and `yay --help` are safe capability probes.
- `yay -P --currentconfig` is a local configuration display, but its output may
  include paths and must be sanitized before becoming a fixture.
- `eos-update --help` is the installed build's authoritative option probe.
  Obtain its installed version and owner with `pacman -Qi eos-update` rather
  than assuming that every release implements the same version flag.

The official [yay manual](https://github.com/Jguer/yay/blob/next/doc/yay.8)
states that bare `yay` performs `yay -Syu` and that yay extends pacman update
operations. Therefore never use bare `yay`, `yay -S*`, `yay -Qu`, `yay -G`,
`yay -P --stats`, or remote/development checks during local capability
discovery: those can refresh data, contact AUR/Git servers, download files, or
prepare changes. The official
[eos-update tips](https://gitlab.com/endeavouros-filemirror/PKGBUILDS/-/blob/master/eos-update/eos-update-tips.md)
identify `eos-update --help` as the most current option documentation and make
clear that normal operation updates through pacman and optionally yay/paru.
Only `--help` is admitted here; options such as `--fast`, `--aur`,
`--other-updates`, `--cache-limit`, and bare `eos-update` are excluded because
they update, save state, call user-defined commands, or remove cached files.

### Flatpak user and system inventory

Run the following separately for `--user` and `--system`:

```text
flatpak --version
flatpak --user list --columns=ref,origin,installation,active,size,options
flatpak --system list --columns=ref,origin,installation,active,size,options
flatpak remotes --user --show-disabled --columns=name,url,options
flatpak remotes --system --show-disabled --columns=name,url,options
```

These commands inspect installed deployments and local remote configuration.
The [flatpak-list manual](https://man.archlinux.org/man/flatpak-list.1.en)
documents the explicit user/system scopes and stable selectable fields,
including ref, origin, installation, active commit, size, and options. The
[flatpak-remotes manual](https://man.archlinux.org/man/flatpak-remotes.1.en)
documents `--show-disabled`; omitting it would incorrectly hide disabled local
origins.

Do not use `flatpak update`, `repair`, `remote-add`, `remote-delete`,
`remote-modify`, `mask`, or `unmask`. Do not use `remote-ls` for a local probe.
`flatpak remote-info --cached` only *prefers* cached information and explicitly
warns it can be stale and incomplete; it is not a guaranteed offline
capability probe according to the
[flatpak-remote-info manual](https://man.archlinux.org/man/flatpak-remote-info.1.en).

### fwupd

After confirming that `fwupdmgr` is the expected package-owned executable:

```text
fwupdmgr --version
fwupdmgr get-devices --json
fwupdmgr get-remotes --json
fwupdmgr get-updates --json
fwupdmgr get-history --json
fwupdmgr check-reboot-needed
```

These are read operations against the daemon's current device state and local
metadata. They may D-Bus-activate the already installed fwupd daemon, but do
not request firmware installation or metadata refresh. Record that
`get-updates` is based on the metadata already present and may be stale. Treat
unsupported JSON or an unavailable daemon as a capability result rather than
falling back to unstable terminal-text parsing.

The official [fwupdmgr reference](https://fwupd.github.io/libfwupdplugin/fwupdmgr.html)
says terminal output is not stable for parsing, recommends `--json`, lists the
read-only `get-*` operations, and separately defines `refresh` as downloading
metadata. Exclude `refresh`, `update`, `install`, `downgrade`, `reinstall`,
`enable-remote`, `disable-remote`, `modify-remote`, `clean-remote`, reporting
uploads, BIOS setters, security fixes, `unlock`, and verification state
changes.

### Rustup and Cargo

After resolving and classifying the `rustup`, `cargo`, and `rustc` paths:

```text
rustup --version
rustup show
rustup toolchain list
cargo --version
cargo install --list
```

`rustup show` identifies the selected toolchain and directory override; the
[rustup override documentation](https://rust-lang.github.io/rustup/overrides.html)
explains why the current directory must be recorded with its output.
`cargo install --list` reads Cargo's installed-binary metadata and is the
documented inventory command in the
[Cargo install reference](https://doc.rust-lang.org/cargo/commands/cargo-install.html).
It is not evidence about distribution-owned Rust executables, so retain pacman
ownership separately.

Exclude `rustup update`, `self update`, toolchain/component/target add or
remove operations, `cargo install` without `--list`, `cargo uninstall`, and
registry searches. Do not use `rustup check` for local discovery because its
purpose is to check remote update availability.

### fnm, Node.js, and global npm packages

After resolving the paths and ownership of `fnm`, `node`, and `npm`:

```text
fnm --version
fnm list
fnm current
node --version
npm --version
npm prefix --global
npm root --global
npm ls --global --depth=0 --json
```

The official [fnm command reference](https://github.com/Schniz/fnm/blob/master/docs/commands.md)
distinguishes local `list`/`current` state from `list-remote`, which queries the
configured Node distribution mirror. The npm
[list reference](https://docs.npmjs.com/cli/v11/commands/npm-ls/) documents
global mode and depth-zero inventory; npm's
[folder model](https://docs.npmjs.com/cli/v11/configuring-npm/folders/)
places global packages below the active prefix.

The prefix is not ownership proof. For every top-level global package, resolve
its package directory and exposed executable paths, then query each with
`pacman -Qqo`. A package below `/usr/lib/node_modules` may be distribution
owned even when npm can display it. Preserve the active Node path/version with
the inventory because changing fnm selection changes which npm installation is
being queried.

Some recent fnm releases also use `fnm default` with no argument as a getter.
Do not assume that behavior: first inspect the installed build's help and run
the no-argument form only when that help explicitly documents it as read-only.

Exclude `fnm list-remote`, install/uninstall/use/default setters, and the npm
commands `outdated`, `view`, `search`, `update`, `install`, `uninstall`, and
`audit`; they contact a registry, mutate selected runtime state, or change
packages.

### uv

First classify the resolved `uv` executable with pacman ownership. For an
expected executable, force the inventory offline and prevent interpreter
downloads:

```text
uv --version
uv --offline --no-python-downloads --no-config tool list
uv --offline --no-python-downloads --no-config python list --only-installed
uv --offline --no-python-downloads --no-config tool dir
```

The official [uv CLI reference](https://docs.astral.sh/uv/reference/cli/)
defines `--offline`, `--no-python-downloads`, `--no-config`, and `uv tool
list`. The [uv Python documentation](https://docs.astral.sh/uv/concepts/python-versions/)
documents `--only-installed`. This combination avoids network access,
automatic Python downloads, and project/parent configuration discovery.
System Python entries displayed by uv are not thereby uv-owned; classify each
interpreter path separately.

Exclude `uv self update`, tool install/upgrade/uninstall, Python install or
uninstall, cache clean/prune, `uvx`/`uv tool run`, project sync/lock/add/remove,
and any inventory command without offline/download guards when its behavior is
not already proven local.

### AppImage bounded discovery

There is no authoritative system-wide AppImage database. The AppImage project
says files may be stored anywhere and identifies `~/Applications` only as a
common convention; see the official
[AppImage FAQ](https://docs.appimage.org/user-guide/faq.html). Therefore:

1. Search only explicit user-configured roots plus a short, documented initial
   set such as `~/Applications`, `~/.local/bin`, and `~/bin` when those
   directories exist. Use `find` with `-xdev`, a maximum depth, a regular-file
   filter, NUL-delimited output, a result limit, and a timeout. Do not scan all
   of `$HOME`, mounted network filesystems, or `/`.
2. Include candidates referenced by user desktop entries, but parse the
   desktop file and resolve its `Exec` path without launching it.
3. Inspect candidates with data-reading tools such as `file` and ELF readers,
   record size/hash/path, and query `pacman -Qqo` for ownership. A `.AppImage`
   suffix alone is a hint; a pacman-owned AppImage remains pacman-managed.
4. Do not execute a discovered AppImage to call `--appimage-mount`,
   `--appimage-extract`, or an embedded updater. The official
   [AppImage inspection documentation](https://docs.appimage.org/user-guide/run-appimages.html)
   warns that the self-mount method calls the target AppImage and may be
   inappropriate for an untrusted file.

Update support remains conditional. The official
[AppImage update documentation](https://docs.appimage.org/packaging-guide/optional/updates.html)
requires author-embedded update information or another explicit updater; file
discovery alone must never produce an “update available” claim. Exclude
AppImageUpdate/appimageupdatetool checks from local discovery because they may
contact the embedded remote, download data, or replace a file.

### Kernel, boot, DKMS, and snapshot discovery

The unprivileged local probe may use:

```text
uname --kernel-release
find /usr/lib/modules -mindepth 1 -maxdepth 1 -type d -printf '%f\n'
dkms status
lsmod
findmnt --json --output TARGET,SOURCE,FSTYPE,OPTIONS --target /
findmnt --json --output TARGET,SOURCE,FSTYPE,OPTIONS --target /boot
findmnt --json --output TARGET,SOURCE,FSTYPE,OPTIONS --target /efi
lsblk --json --output NAME,PATH,TYPE,FSTYPE,FSVER,MOUNTPOINTS
bootctl status --no-pager
bootctl list --json=short --no-pager
```

Apply existence checks to optional paths and tools. For each directory under
`/usr/lib/modules`, inspect its `pkgbase` file when present and use `pacman
-Qqo` on package-owned files to map installed kernel artifacts to native
packages. Compare those installed versions with `uname --kernel-release`; do
not infer reboot need from package names alone. Query likely boot/initramfs and
snapshot packages with `pacman -Q`, and inventory relevant configuration and
hook filenames without editing them.

Boot-loader discovery must also be bounded and plural: record whether the host
booted through EFI (`/sys/firmware/efi`), inspect only known configuration
roots such as `/boot/loader`, `/efi/loader`, and `/boot/grub` when accessible,
and resolve package ownership for discovered loader files. `bootctl` output is
useful evidence even when systemd-boot is not the installed loader, but it is
not by itself a universal GRUB/rEFInd/firmware inventory. Do not recursively
scan the entire EFI system partition.

`dkms status` is the documented read-only action that reports module, version,
kernel, and build/install state; see the
[DKMS manual](https://man.archlinux.org/man/extra/dkms/dkms.8.en). `findmnt`
supports explicit fields and JSON, whereas its default output may change; see
the [findmnt manual](https://man.archlinux.org/man/findmnt.8.en). The
[bootctl manual](https://man.archlinux.org/man/bootctl.1.en) documents `status`
and JSON-capable `list`, but those results cover the boot-loader interfaces
bootctl understands and do not prove recovery or rollback.

For snapshot capability:

- use `findmnt` to establish the root filesystem type and mount options;
- record whether package-owned `snapper`, `timeshift`, `btrfs`, or related
  tools and configurations exist;
- `snapper list-configs` and `snapper list --disable-used-space` are read-only
  only for configurations already accessible to the current user;
- `btrfs subvolume list` is a read operation but may require permissions the
  unprivileged service lacks. Record that failure and do not elevate.

The [snapper manual](https://man.archlinux.org/man/extra/snapper/snapper.8.en)
documents its list operations and access controls. The
[Btrfs subvolume manual](https://man.archlinux.org/man/btrfs-subvolume.8)
also cautions that a snapshot is not a backup. Merely detecting Btrfs,
Snapper, Timeshift, or snapshot-like subvolumes does not prove that a usable,
bootable, space-sufficient rollback path exists.

Exclude `bootctl install`, `update`, `remove`, default/oneshot setters, kernel
installation/removal, `dkms add/build/install/remove/autoinstall`, initramfs
generation, bootloader generation, snapshot creation/deletion/rollback,
subvolume mutation, filesystem checks/repair, mounting, and anything retried
with administrator permission.

## Excluded command classes at a glance

| Exclusion reason | Examples | Why excluded from capability discovery |
| --- | --- | --- |
| Refreshes or writes metadata | `pacman -Sy`, `pacman -Fy`, normal `checkupdates`, `fwupdmgr refresh`, Flatpak AppStream updates | Contacts remote services and writes databases/caches; belongs to an explicit update check. |
| Opens or plans a package transaction | bare `yay`, bare `eos-update`, `pacman -S/-U/-R`, `flatpak update/install/uninstall` | Can lock databases, resolve changes, prompt, download, or mutate. |
| Unnecessary network access | `yay -Qu`, `fnm list-remote`, `npm outdated/view/search/audit`, `rustup check`, remote Flatpak listings | Capability detection needs installed/local state, not latest remote state. |
| Privileged or hardware mutation | firmware install/unlock/settings, boot changes, DKMS builds, initramfs generation | Requires separate review, local confirmation, and often administrator permission. |
| User/tool state mutation | fnm default/use/install, rustup update/add/remove, uv install/upgrade, npm install/update | Changes runtimes, packages, defaults, caches, or configuration. |
| Executes untrusted discovered content | AppImage self-mount/extract/updater, arbitrary `--version` | A supposedly read-only flag still runs code from the target file. |

## Adapter consequences and remaining gaps

- Capability discovery and update checking need separate interfaces, audit
  events, timeouts, and freshness labels. Cached `get-updates` output is not a
  successful refresh.
- Command output is not a stable contract unless the installed tool documents
  structured fields. Capture sanitized target-host fixtures for each installed
  version before finalizing parsers.
- Pacman ownership must be applied to tool binaries and the things they list.
  Prefix, path, filename extension, or a tool's ability to display an item is
  not proof that the tool owns it.
- Target-host checks confirmed fwupd's top-level `Devices` JSON shape, the
  selected Flatpak columns, unprivileged DKMS status, and systemd-boot status.
  A future parser still needs hostile/malformed fixtures and bootctl list JSON
  before treating those formats as stable contracts.
- A read-only AUR RPC name lookup matched 41 of 42 foreign package names, while
  installed metadata identifies the remaining `kgamma` as a signed Arch build.
  Original provenance remains unresolved; do not equate either observation
  with proof of installation source.
- AppImage coverage remains explicitly bounded and user-configurable. The
  expanded target-host roots found one unowned LM Studio AppImage under
  `$HOME/bin`; discovery alone does not establish update support.
- Snapshot detection can establish prerequisites only. A rollback capability
  remains **not verified** until a separately approved restore/boot test proves
  it end to end.
