# Target-host capability snapshot

**Captured:** 2026-10-23 (America/Indiana/Indianapolis)  
**Method:** read-only local commands; no refresh, install, update, service change
or provider mutation was performed  
**Purpose:** constrain the Phase 0 runtime decision and later adapter probes

This is a point-in-time observation of the intended development host, not an
application support promise. Provider adapters still need fixtures and explicit
output-contract tests before their results can be trusted by Updatarr.

## Runtime and UI toolchain

| Capability | Observed state | Phase 0 implication |
| --- | --- | --- |
| OS/session | EndeavourOS, Linux 7.2.11-arch1-1 x86_64, KDE Plasma on Wayland | Primary host matches the proposed Linux/KDE scope. |
| Python | CPython 3.14.8 | Suitable for the service prototype. |
| Web service | FastAPI 0.161.1, Uvicorn 0.54.0, Pydantic 2.14.1 | A no-install loopback JSON/SSE slice is possible. |
| Persistence packages | SQLite 3.54.0 present; SQLAlchemy and Alembic absent | SQLite is viable, but the proposed migration/ORM layer is not yet locally validated. |
| Test packages | pytest 9.1.1; Playwright available with Chromium | API and responsive browser checks can run without installation. |
| JavaScript | Node 24.22.1, npm 12.2.1 | Modern JavaScript execution is present. |
| Production web stack | React and Vite were not installed locally or globally at capture time | This established the original dependency gap. The later user-approved, project-local validation is recorded in `m0-web-stack-validation.md`; no system package was installed. |
| KDE tray build | Qt 6.12.0 and `kstatusnotifieritem` 6.31.0-1 present; CMake and a pkg-config entry for KStatusNotifierItem absent | Do not commit to a native tray implementation until its real build dependencies and packaging route are proven. |

## Provider and ownership observations

| Area | Observation | Safety consequence |
| --- | --- | --- |
| Native packages | pacman 7.1.0.r9.g54d9411-3 owns `/usr/bin/pacman`; 1,743 installed packages, including 42 foreign packages | Native inventory and foreign-package classification must remain separate; counts are expected to drift. |
| AUR helper | yay 13.0.1 | Availability does not prove safe noninteractive output or execution semantics. |
| EndeavourOS updater | eos-update 26.9.2-1 | Treat as an observed native tool, not an additional package ownership domain. |
| Existing updater | Octopi 0.19.0-3; `octopi-notifier` was running from the user's autostart entry | Side-by-side development only. No process or autostart change is authorized. |
| Flatpak | Flatpak 1.18.4; 22 user apps, one system app; user and system Flathub remotes | Preserve scope, ref, branch, origin and remote enabled state. The older two-app inventory is obsolete. |
| Firmware | fwupd 2.1.9; `fwupdmgr get-devices --json` succeeded | Structured discovery is available, but device eligibility and release operations need sanitized fixtures. |
| Rust | rustup 1.29.2; `cargo install --list` exposed no installed tools | Keep rustup toolchains distinct from pacman ownership; do not manufacture an empty Cargo provider result. |
| Node globals | npm root is `/usr/lib/node_modules`; Node 24.22.1 and npm 12.2.1 | Resolve pacman ownership for every global before offering an npm mutation. |
| uv | uv 0.13.1 at unowned `~/.local/bin/uv` | Provenance remains unknown; self-update must stay disabled by default. |
| AppImage | No `.AppImage` files found in `~/Applications` or `~/.local/bin` during the initial two-path scan | Coverage was incomplete; bounded registration paths needed expansion. |
| Boot | dracut 112; booted Linux 7.2.11; `btrfs` tool present | A tool's presence is not proof of a configured rollback path. Kernel, DKMS, bootloader and snapshots require deeper read-only probes. |

## Local service feasibility

- The per-user default and graphical-session targets were active, and lingering
  was already enabled for the user. This supports later user-service
  experiments but does not authorize creating or enabling a unit.
- polkit 128, `polkitd` and the KDE authentication agent were active. That
  supports the planned local authorization UX; it does not validate any
  privileged action definition.
- The Phase 0 prototype successfully served loopback-only static HTML, JSON and
  FastAPI's native server-sent events. Host-header rejection and baseline
  browser security headers were exercised.

## Remaining probe work

The expanded 2026-10-24 pass below closes the local output-shape, ownership and
boot-discovery items. The chosen production frontend was subsequently validated
with user-approved, project-local dependencies. The tray build path remains a
later prototype, and M1 owns the full parser corpus, including malformed,
hostile, timeout and unavailable results.

## Expanded read-only evidence — 2026-10-24

All commands in this pass were local queries except the explicitly identified
AUR name lookup. No package database refresh, install, update, configuration
write, service change or authentication prompt was performed.

| Area | Result | Product consequence |
| --- | --- | --- |
| Executable ownership | pacman, yay, eos-update, Octopi, Flatpak, fwupd, rustup/Cargo, fnm, npm, DKMS, bootctl and findmnt resolve to pacman-owned executables. `uv` remains unowned at `$HOME/.local/bin/uv`. | Record executable path, owner and version independently; never let an unowned tool self-update automatically. |
| Native inventory | 1,743 installed packages; 42 are absent from the configured sync databases. Four dependency orphans were observed but no cleanup was attempted. | “Foreign” remains an inventory fact, not an AUR ownership claim or a cleanup instruction. |
| Foreign-package classification | A read-only AUR RPC v5 `info` lookup found a current name match for 41 of 42 foreign packages. `kgamma` had no current AUR or sync-database match, but its installed metadata names an Arch packager and a valid package signature. | Classify 41 as “current AUR name match, original provenance unproven”; classify `kgamma` as a signed former/locally absent repository package pending repository-history evidence. |
| Flatpak apps | 22 user apps and one system app. Each captured row includes application ID, branch, origin and installation scope. | These fields form identity; user and system entries must never collapse together. |
| Flatpak remotes | System and user Flathub are enabled. Twenty-one one-off user origins are `disabled,no-enumerate,no-gpg-verify`. | The adapter must query with `--show-disabled`; it must preserve these origins exactly and never silently enable them. |
| Firmware | `fwupdmgr get-devices --json` completed without refresh and returned 29 device records. Records have different optional field sets and may include stable IDs or serials. | Structured device discovery is supported. Persist only required identifiers and sanitize fixtures; do not infer that updates exist from the device count. |
| Rust/Cargo | One active default stable Rust toolchain; no Cargo-installed tools. `/usr/bin/cargo` is owned by the `rustup` package. | Treat the rustup-managed toolchain separately from the pacman-owned launcher. |
| Node/npm | fnm lists Node v23.6.0 plus the system runtime. npm lists six global packages under `/usr/lib/node_modules`; all six corresponding directories are pacman-owned. | Updatarr must not update those six packages through npm. |
| DKMS and kernel | One installed kernel (`linux` 7.2.11) and one installed NVIDIA DKMS build for that kernel were observed; dracut is installed. | Kernel planning must show the DKMS relationship and verify the post-update build result. |
| Boot and rollback | systemd-boot is active, UEFI Secure Boot is enabled, and the root filesystem is ext4. `btrfs-progs` is installed, but neither a Btrfs root nor snapper/Timeshift was found. | Do not advertise snapshot rollback. Tool presence alone is not a configured recovery path. |
| AppImage | Expanding the bounded paths found `$HOME/bin/LM-Studio-0.4.26-4-x64.AppImage`: an unowned, executable, 64-bit x86 ELF file of 1,021,758,187 bytes. No matching desktop entry was found. `86box-appimage` remains a pacman-owned foreign package. | Record LM Studio as a discovered candidate only. Do not execute it during discovery or claim update support until embedded update information or another trusted vendor method is safely verified. Package-owned files stay with the native package source. |
| Existing updater | `octopi-notifier` remains running from its existing XDG autostart entry. | Side-by-side development remains mandatory; no notifier or autostart change is authorized. |
| Production frontend | React, React DOM, Vite and TypeScript were absent locally and globally during this read-only capture. | This historical observation remains valid. A later M0 step installed exact project-local versions after explicit user approval and validated the provisional stack. |

### Repeatable evidence

- [`scripts/read_only_capability_probe.py`](../../scripts/read_only_capability_probe.py)
  exposes only named, argument-closed queries; it executes exact trusted paths
  only after verifying file permissions and expected pacman ownership. The
  single unowned `uv` exception is pinned to the expected user-owned path and
  called only with offline/download-disabled flags. The runner rejects shell,
  privilege and known mutating arguments, bounds time/output/record counts,
  passes only required local-state environment variables and redacts local
  identity, credentials and stable firmware/boot identifiers from output.
- [`tests/fixtures/read_only`](../../tests/fixtures/read_only) contains reduced,
  sanitized output shapes for native, Flatpak, firmware, npm and toolchain
  results.
- [`host-capability-probe-summary.json`](host-capability-probe-summary.json)
  records the complete sanitized M0 capability result, including scope,
  privilege, per-action support, limitations and safe next steps.
- `python -m pytest -q tests/test_read_only_capability_probe.py` verifies the
  closed command registry, redaction behavior, truthful missing-tool state and
  fixture structure.

### Known limits

- A current AUR name match does not prove where an installed package originally
  came from; Updatarr must retain that uncertainty.
- Firmware update availability was not requested. Device discovery used cached
  local daemon state and explicitly disabled metadata and remote checks.
- The probe intentionally does not call `checkupdates`, `yay` update checks,
  `flatpak update`, `fwupdmgr refresh/get-updates`, or any eos-update action.
