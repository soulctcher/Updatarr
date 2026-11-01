# Updatarr capability matrix

**Status:** M4 safety classification and detected tool adapters implemented  
**Snapshot date:** 2026-10-27

The initial host probe is recorded in
[Target-host capability snapshot](docs/research/host-capability-snapshot.md).
It includes high-level availability, ownership classification and sanitized
output shapes. M1 adds defensive parsers, hostile/malformed fixtures and a
live inventory comparison without querying update availability.

## Status vocabulary

- **Planned:** required by the product but not implemented.
- **Conditional:** exposed only after a runtime capability probe succeeds.
- **Unsupported:** provider cannot safely perform the action.
- **Blocked:** capability exists in principle but a current safety condition
  prevents use.
- **Unknown:** not yet verified on the target host.

## Provider matrix

| Provider / scope | Inventory | Check | Search | Plan | Execute | Hold/defer | Principal constraints |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Arch/EOS repositories | Implemented read-only | M5 fixed `checkupdates` probe uses a separate temporary database | Official Arch HTTPS search implemented; configured-host availability remains unconfirmed | Selection and planning preserve one full-upgrade group | Simulator only; first live trial gated | Saved postpone/pause applies to whole native group | Never partial-upgrade; one native owner/lock |
| AUR / foreign packages | Foreign records identified but ownership unresolved | M5 fixed `yay -Qua --aur` query reports helper-confirmed updates | AUR RPC v5 search implemented with user-submitted label | Exact AUR update can be reviewed; build/install stays blocked | M7 isolation prototype only; live use blocked pending isolated source acquisition, clean dependency root and independent review | Exact saved choice only | Foreign is not automatically AUR; the update query does not rewrite original ownership |
| Flatpak user | Implemented read-only | Not checked in M2 | Fixture-backed; live search blocked because it may refresh AppStream | Planned with refs, runtimes and permission delta | Gated Phase 3 | Updatarr saved choice only; masks are read-only until approved later | Never elevate unnecessarily or re-enable disabled origins |
| Flatpak system | Implemented read-only | Not checked in M2 | Fixture-backed; live search blocked because it may refresh AppStream | Planned with auth and scope | Gated Phase 3 | Updatarr saved choice only; masks are read-only until approved later | Preserve system/user identity and remote/branch |
| fwupd | Implemented read-only without refresh | Read-only release parser and simulator requirement states | Device release catalog only | Typed simulator plan with separate restart/shutdown/replug/activation | First live trial gated | Usually postpone rather than pause | Use signed provider flow; no universal device support/rollback |
| AppImage | Bounded-path adapter; ownership unresolved until checked | Conditional on verified update metadata | Unsupported as universal catalog | Typed staged-replacement simulator; unsafe files disabled | First live trial gated | App postpone | Regular non-symlink, no pacman owner, supported embedded update information, colocated staging and recovery copy |
| rustup toolchains | Implemented read-only | Simulator plan; live versions not checked | Source-specific only | Typed toolchain simulator; suppress self-update | First live trial gated | App postpone | Pacman may own rustup binary; toolchains are separate |
| Cargo-installed tools | Implemented read-only | Not checked; no stable update-all preview assumed | Source-specific only | Disabled until exact reproducible source/root exists | First live trial gated | App postpone | Git/local/untracked/unknown-root entries stay disabled |
| fnm Node runtimes | Implemented read-only | Simulator exact-version plan | Version catalog only | Typed version install; default switch remains separate | First live trial gated | App postpone | Preserve project selections; no silent default switch |
| npm globals | Implemented read-only with root ownership class | System-root entries visibly blocked | Source-specific only | User-owned scope only | First live trial gated | App postpone | Never overwrite pacman-owned `/usr/lib` globals |
| uv tools/Pythons | Implemented read-only tool inventory | Not checked; self-update disabled when provenance unresolved | Source-specific only | uv-managed tools only after provenance and collision checks | First live trial gated | App postpone | Do not claim system Python or project environments |
| Cache maintenance | Simulator preview implemented | Usage/status only | Not applicable | Preview is not a cleanup plan | First cleanup trial gated | Not applicable | Maintenance is separate and M4 exposes no delete action |

## Host snapshot and remaining revalidation

| Observation | Prior snapshot | Phase 0 verification |
| --- | --- | --- |
| Native packages | 1,743 total installed; 42 foreign | 41 have a current AUR name match; `kgamma` is a signed former/locally absent repository package; original provenance remains unproven |
| Native tools | pacman, yay 13.0.1, eos-update 26.9.2, Octopi 0.19.0 | Executable paths and pacman owners verified; supported help captured without invoking default update behavior |
| Existing notifier | Octopi notifier autostart | M5 reconfirmed Octopi 0.19.0-3, one active notifier process and an unowned private user autostart copy; no setting changed |
| Flatpak | 22 user apps; 1 system app; Flathub in both scopes | Branch, origin and scope captured; 21 disabled one-off origins found with `--show-disabled` |
| Firmware | fwupd 2.1.9 present | JSON device discovery works without refresh; 29 heterogeneous records observed; update availability not queried |
| Rust/Cargo | rustup 1.29.2; no Cargo-installed tools | Toolchain and ownership verified; Cargo launcher belongs to pacman `rustup` package |
| Node/npm | Node v24.22.1 and npm 12.2.1; global root `/usr/lib/node_modules` | fnm state confirmed; all six listed npm globals resolve to pacman-owned directories |
| uv | Unowned `$HOME/.local/bin/uv`, uv 0.13.1 | No registered tools; provenance unresolved and self-update remains disabled |
| AppImage | Initial two-path scan was empty; expanded `$HOME/bin` scan found one LM Studio AppImage | Candidate is unowned but updater support is unverified; package-owned `86box-appimage` stays native-managed |
| Boot stack | dracut, systemd-boot, one Linux kernel and matching NVIDIA DKMS build | Root is ext4; no configured Btrfs/snapper/Timeshift rollback path was found |

The 2026-10-24 M1 live run matched direct local-tool counts: 1,743 native
packages, 22 user Flatpaks, 1 system Flatpak, 29 firmware records and 1 Rust
toolchain. All 1,796 software identities were unique. See
[M1 read-only validation](docs/research/m1-read-only-validation.md).

## Capability probe record

Each probe result must include:

- provider and adapter schema version;
- executable/API identity, version and resolved ownership;
- supported structured-output mode and observed contract version;
- installation scopes and privilege model;
- check/search/plan/execute/history/hold support separately;
- degraded or blocked reason with remediation;
- timestamp and expiration/staleness policy;
- fixture captured after sensitive-data review.

An absent optional provider remains visible as unavailable only when useful; it
must not trigger dependency installation automatically.

## M4 safety evidence

- Firmware requirements preserve restart, full shutdown, reconnect and
  activation as distinct follow-up actions; malformed or identity-less JSON is
  refused.
- Startup checks keep kernel files, driver builds, dracut and boot-loader facts
  separate while leaving every package in the complete system update group.
- Portable-app classification blocks symlinks and system-package-owned paths
  and marks missing embedded update information **Not supported**.
- Cargo, fnm, npm, uv and bounded portable-app adapters inventory only through
  the closed read-only probe registry. No version check, metadata refresh,
  self-update or overwrite is implied.
- The authenticated M4 response records that package ownership, disabled
  Flatpak origins and host state were unchanged. Live execution and cleanup
  remain unavailable pending their individual trial approvals.

## M2 history and notice evidence

- AUR search can open a bounded plain-text PKGBUILD preview from the fixed
  official AUR host. It never executes the file and does not invent a change
  comparison when no earlier copy is recorded.

- Pacman history import reads a bounded tail of the configured default log and
  recognizes install, reinstall, upgrade, downgrade and removal facts.
- Flatpak history import uses the fixed user and system `history --json` probes;
  journal retention means the result is always labeled partial, with one import
  batch per scope explaining the limitation.
- Existing Flatpak disabled remotes and masks are read through fixed user/system
  probes. M2 records and displays them but cannot create, remove or enable them.
- Arch news uses the official HTTPS feed with a bounded response and plain-text
  rendering, parse state and content hash. Security and EndeavourOS notice
  sources remain Not checked until their exact stable parsers are implemented.
