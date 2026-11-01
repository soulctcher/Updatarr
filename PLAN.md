# Updatarr — Product and Technical Plan

**Product name:** Updatarr  
**Target platform:** EndeavourOS (Arch Linux), KDE Plasma 6, Wayland, x86_64; responsive browser clients on a trusted local network or VPN  
**Status:** Implementation specification; no host modifications authorized by this document  
**Baseline date:** 2026-10-23  
**Primary objective:** One polished *arr-style web application and one KDE tray
notifier for finding, reviewing, installing and postponing software updates and
new installations across different update sources.

**Language rule:** User-facing text uses the plain terms in
[GLOSSARY.md](GLOSSARY.md). Internal identifiers may be more technical when
precision requires it, but those names do not leak into labels without a plain
explanation.

> **Foundational rule:** Consolidate *experience and orchestration*, not underlying package databases. Keep trusted native backends; avoid unsupported partial upgrades, unreviewed AUR builds, silent privileged operations, and false claims of universal coverage.

---

## 1. Desired product

Deliver **Updatarr**, a full-featured KDE-integrated, local-first update-and-software manager that:

1. Provides one GUI and system-tray status item for **all detected, supported
   update sources**; clearly lists software that Updatarr cannot manage.
2. Discovers and installs updates for Arch/EndeavourOS repository packages, AUR packages, Flatpak applications and runtimes (system/user), eligible AppImages, device firmware, kernel/boot-related packages, and other separately managed toolchains such as Rust and Node.js.
3. Searches configured package catalogs and installs new software with explicit source/ownership selection; includes official repositories, EndeavourOS configured repositories, AUR, Flathub/configured Flatpak remotes, and separately labeled source-specific search where supported.
4. Supports update-source on/off controls; individual updates can be selected,
   postponed, skipped for a particular version, or paused **only when the
   update source allows it safely**. Unsafe Arch package selections must be
   blocked, not merely warned and installed.
5. Displays source-specific changelogs/release notes, version changes, size, dependencies, reviews/PKGBUILD diffs where available; labels unavailable information rather than inventing it.
6. Requests graphical authentication for privileged actions; does not run the entire GUI as root or cache credentials.
7. Reports accurate statistics, logs, history, update-plan steps, outcomes,
   update-source status and pending actions such as reboots in a modern
   KDE-friendly interface.
8. Fully replaces **Octopi GUI and Octopi Notifier** only after feature parity, supervised testing, successful autostart/tray handover, and a reversible migration.
9. Respects the host's real update workflows; never double-applies a native package update by treating pacman, yay, and eos-update as independent owners of the same package.
10. Runs an unprivileged long-lived local service that serves a responsive web interface and versioned API, allowing Updatarr to be managed in a browser like Sonarr and Radarr while keeping all privileged execution behind the separately reviewed authorization boundary.
11. Uses an original Updatarr identity within the recognizable *arr interaction language; it must not copy another project's logo, trademark, source assets, or exact screen design.

### Not guaranteed

A single app cannot promise update support for *literally every piece of
installed software*. Software with no declared update mechanism, proprietary
in-app updaters, offline Flatpak bundles, manually copied binaries, vendor-only
firmware and untracked builds may be discoverable but not safely updateable.
Report them as **Not managed**, **Not supported** or **Source unavailable**,
optionally with a link or manual steps. Do not claim to have checked them.

---

## 2. Verified host baseline (from four user-run read-only inventories)

| Observation | Host-specific finding |
|---|---|
| OS / desktop | EndeavourOS / Arch, KDE Plasma; user runs Wayland |
| Official packages | 1,680 native repository packages |
| Foreign pacman packages | 38 (includes AUR and possibly locally built packages; **not** proof every one is AUR) |
| Overlapping native frontends | `pacman`, `yay 13.0.1`, `eos-update 26.9.2`, `octopi 0.19.0` |
| Existing active notifier | `octopi-notifier`, autostarted from `~/.config/autostart/octopi-notifier.desktop` |
| Stale launcher | `~/.local/share/applications/org.manjaro.pamac.manager.desktop` exists; `pamac-manager` absent from PATH |
| PackageKit | Installed with `packagekit-qt6`; no active updater service at inventory moment; dependencies must be rechecked before considering removal |
| Flatpak | 23 apps: **2 Flathub** (one system, one user) and **21 `com.retro_exo.*`** user-installed versioned bundles |
| Flatpak remotes | Flathub system + user; 21 local `*-origin` remotes are disabled, non-enumerable, and do not provide normal live package listings |
| Firmware | `fwupd 2.1.9`, `fwupdmgr` installed; device eligibility/available updates not yet verified |
| Rust | `rustup 1.29.2`, one stable toolchain; no `cargo install --list` tools |
| Python | `uv` at `~/.local/bin/uv`, not owned by pacman; `uv tool list`: none; interpreter listings point at system-owned paths (do not call these uv-managed downloads) |
| Node | `fnm` installed with Node v23.6.0; `npm` global list includes six packages under `/usr/lib` (must check ownership before any mutation) |
| AppImages | Expanded bounded discovery found one unowned LM Studio AppImage under `$HOME/bin`; update support is unverified. `86box-appimage` is a **pacman-owned foreign package**, not an independently managed AppImage. |
| Background schedules | `paccache.timer`; no update timer in earlier filtered scan. `plocate-updatedb` is not software updating |
| Kernel/initramfs | `dracut` present. Exact installed kernels, bootloader, initramfs hooks, DKMS state, and snapshot capability still require runtime detection |

**Baseline inventory caveat:** these are inventory-time observations, not live counts. Always scan on the user's actual host before acting. Do not automatically uninstall or reconfigure anything based solely on this table.

---

## 3. Capability review of existing tools and required behavior

| Tool / ecosystem | Capabilities to preserve / build upon | Overlap or limitation | Approach |
|---|---|---|---|
| `pacman` + libalpm | Official/EOS configured repositories; install, remove, full system upgrade, dependencies, package metadata, native hooks, local pacman history/cache | Arch does **not** support partial upgrades or unconstrained per-package holds | Sole authoritative owner of native repo transactions; discovery via `checkupdates` / safe ALPM read paths; full-upgrade planner |
| `yay` | Pacman-compatible repo+AUR search/install/update; AUR metadata, PKGBUILDs, source builds, VCS/devel support, dependency resolution | Also upgrades repository packages; must not cause second native upgrade | Preferred AUR adapter, with auditable build/diff/review stages, non-root builds, PTY for truly interactive steps |
| `eos-update` | Safe-ish EndeavourOS orchestration around pacman and yay/paru; mirror, NVIDIA/kernel driver checks; checks/repair suggestions; cache and `pacnew` support | Wrapper, not an independent repository; command options need detection from installed version | Preserve useful preflight checks; optionally use whole `eos-update --aur` for a supported full-system flow if it satisfies review/progress requirements; do **not** combine it blindly with another full upgrade |
| Octopi | Installed/searchable package GUI, repo/AUR info, update actions, cache cleaner, PKGBUILD review/diff integrations | Overlaps native stack | Replace end-user GUI only after parity |
| Octopi Notifier | KDE tray notifications, update checks, optional AUR checks | Duplicate background checker; currently running | Replace with single-instance KDE tray service, after rollback-ready cutover |
| PackageKit | Backend framework for graphical app stores | Potentially overlaps native pacman/Flatpak updates and package locking | Do not use as a competing pacman transaction engine; retain while other software requires it |
| Flatpak | User/system installation scopes, configured remotes, search, install/update, refs/runtimes, per-ref masking, permissions, transaction review | App revisions/branches and remote scopes differ; 21 installed retro_exo bundles have disabled local origins | Separate user/system provider instances; scoped identity and accurate remote/permission reporting; never silently enable local bundle origins |
| `fwupd` / LVFS | Device enumeration, metadata refresh, available releases, updates, history, reboot/activation requirements | Only hardware/vendors supported by fwupd/remotes; firmware operations may have major prerequisites | Prefer fwupd D-Bus/client JSON; device-specific consent, power/reboot warnings, serialization and historical reconciliation |
| AppImage / AppImageUpdate | Portable apps can optionally embed zsync/update information; some update in-app | No universal AppImage catalog; many files have no embedded update mechanism | Register/scan bounded directories and user-provided files; verify embedded mechanism, checksum/signature where feasible; staged atomic replacement/rollback; report unupdateable otherwise |
| Linux kernels / drivers / boot | Kernels, DKMS, firmware packages, microcode and bootloader components generally installed by pacman; dracut builds initramfs via hooks | Not a separate distribution-release transaction on rolling Arch; boot risks need checks | Classify native packages as kernel/boot changes, preserve hooks, detect installed vs running kernel, DKMS/boot implications, and reboot; no bespoke kernel installer |
| EndeavourOS distribution | Rolling-release package updates, EOS packages/mirrors/news | No Ubuntu-style release-upgrade button to implement | Show distribution news/manual intervention feed; native full upgrade applies distribution changes |
| `rustup` / Cargo | Rust toolchains and separately `cargo install`ed binaries | Cargo tools count 0 now; pacman owns `rustup` binary itself | Toolchain vs pacman ownership separation; optional tool updates only when present |
| `fnm` / npm | Per-user Node runtime versions; global npm packages | System npm binaries may be pacman-owned; updating via npm could corrupt ownership | Check package-manager ownership; update user-managed tools only; never npm-upgrade system-owned global packages blindly |
| `uv` | User-installed `uv` can manage Python downloads/tools | No registered uv tools; `uv` executable is unowned, provenance unknown | Optional provider; no upgrading binary until installation method known; avoid projects' virtualenv dependency upgrades |
| `paccache` | Cache cleaning, retaining a configurable number of old package versions | Maintenance, not updating | Separate maintenance pane/metric, opt-in |

### Important source-specific facts

- **Arch safety:** full repository upgrades are supported; `pacman -Sy foo`, `pacman -Sy` alone, and unconstrained IgnorePkg / `--ignore` usage violate the full-upgrade model. Detect via `checkupdates` rather than synchronizing the live local sync DB simply to count updates. See [Arch System Maintenance](https://wiki.archlinux.org/title/System_maintenance) and [Pacman](https://wiki.archlinux.org/title/Pacman).
- **AUR:** yay wraps pacman and can interactively review PKGBUILDs and diff files; building arbitrary AUR scripts as root is unsafe. See [yay manual](https://github.com/Jguer/yay/blob/next/doc/yay.8) and [Arch makepkg guidance](https://wiki.archlinux.org/title/Makepkg).
- **EndeavourOS:** `eos-update` has `--aur`, `--check-mirrors`, `--nvidia`, `--cache-limit`, various diagnostics; verify installed version's `--help` prior to integration. See [eos-update tips](https://gitlab.com/endeavouros-filemirror/PKGBUILDS/-/blob/master/eos-update/eos-update-tips.md). `eos-update-notifier` was removed by the distribution in September 2026, which is separate from the user's Octopi notifier. See [EOS important news](https://github.com/endeavouros-team/Important-news).
- **Flatpak:** per-user vs system scopes are distinct; `flatpak mask` allows scoped individual refs to be held. See [Flatpak mask](https://docs.flatpak.org/en/latest/tips-and-tricks.html#masking) and [Flathub system vs user](https://docs.flathub.org/docs/for-users/user-vs-system-install).
- **fwupd:** use firmware metadata, release/device IDs, consent and reboot flags; stable JSON is preferable to parsing terminal messages. See [fwupdmgr docs](https://github.com/fwupd/fwupd/blob/main/src/fwupdmgr.md).
- **AppImage:** automatic updates require embedded update information or another verifiable vendor updater; no universal mechanism. See [AppImage update documentation](https://docs.appimage.org/packaging-guide/optional/updates.html).
- **Search:** official Arch package index supports JSON search; AUR supports JSON RPC search and info, though local package-management tools govern installation. See [Arch package search JSON](https://wiki.archlinux.org/title/Official_repositories_web_interface) and [AUR RPC](https://wiki.archlinux.org/title/Aurweb_RPC_interface).

---

## 4. Update choices: exact meanings for off, postpone, skip and pause

This is a central product requirement and must be defined before execution code.

### Distinct controls

| UI action | Meaning | Retained update visibility | Persistence | Arch repo behavior |
|---|---|---|---|---|
| Turn off an update source | Stop its checks and installs through this app | Show “Turned off”; mark last information “Needs refresh” | Until turned on | Turning off system update checks must not imply the system is up to date |
| Remove from this update | Leave software out of the proposed update plan | Still listed as an update | Current plan only | If this would create a partial system upgrade, block or postpone the whole system update group |
| Postpone update | Leave a selected update out until a date, version or manual resumption | Listed under Postponed and still visible in risk summaries | Saved rule with optional expiry | Postpone the whole system update group when one package cannot safely wait alone |
| Skip this version | Hide one exact detected version and show the software again when the version changes | Available under Skipped; counted separately | Keyed on update source + software + version/commit | Hiding is a notification choice, not permission for a partial system upgrade |
| Pause updates | Keep this software from changing until resumed, possibly with an expiry | Shown as paused, with warnings | Saved rule | Blocks system updates if it cannot safely be maintained; do not silently apply `IgnorePkg` |
| Ignore advisory | Dismiss warning only | Warning accessible in log | Versioned/time-limited | Cannot bypass invariant safety gates |

All policies use exact identity: `{update_source, installation_scope,
repository_or_remote, package_or_ref, architecture, channel_or_branch,
detected_version_or_commit}` as appropriate. Store the reason, creation/expiry,
owner and last applied time; explain where the rule came from and how to remove
it. Never modify `/etc/pacman.conf` merely to save an Updatarr preference.

### Native upgrade safety behavior

**Example:** A user selects only 5 of 20 available system-package updates. The
GUI can install none or postpone the whole system update group, but cannot
promise to install those 5 alone safely. It must explain why and offer:

- **Install all system updates** (supported path).
- **Postpone all system updates**, while still allowing separate Flatpak, Rust
  and firmware updates when their own rules permit.
- **Review exclusions and unpause**, then replan.

AUR package selection may be granular **after** a current, compatible native system state is achieved, with dependency/build review. If the AUR action would require an unsafe native partial upgrade, block and require full native upgrade. No option labeled “force anyway” in normal UI.

A display checkbox can influence notifications, but installation still follows
dependency, update-source permission and integrity checks.

### Grouping and collision avoidance

- Repository packages reported by pacman, yay, eos-update or another frontend map to **one owned native package record** and **one native upgrade plan**, not duplicate updates.
- Foreign/AUR packages use owner metadata; orphaned foreign packages are labeled `foreign / source unresolved`, not promised AUR upgrades.
- An AppImage delivered via pacman is *pacman-managed* even though its file format is AppImage.
- Flathub names colliding with pacman package names are **alternatives**, not duplicate installation records. Show source/sandbox/privacy/permissions differences at selection time.
- Kernel/dracut/microcode are native packages; show a **category overlay** rather than a duplicate updater.

---

## 5. Functional requirements and interface design

### 5.1 Home / Overview

Responsive, information-dense, readable, and visually related to the *arr family without being a clone. Use a persistent desktop side rail, a compact mobile navigation treatment, a slim global search/action area, and a wide operational content canvas. Display:

- Updates ready to review, grouped by update source and by which updates must be
  installed together.
- Postponed, paused and skipped counts separate from updates ready to review;
  update-source labels use `working`, `turned off`, `up to date`, `source
  unavailable`, `error`, `not supported` and `needs refresh`.
- Last successful check for each update source, including time, duration and
  “Needs refresh” or offline labels.
- Estimated downloads and disk impact **only when backend supplies credible numbers**; unknown otherwise.
- Kernel/driver/firmware/reboot readiness messages and blockers; distro Arch/EOS advisories requiring manual intervention.
- Action buttons: Check for Updates, Review Updates, Install Approved Updates,
  Search Software and View History; progress banner for an update in progress.

### 5.2 Updates

- Filter and sort by name, installed version, new version, source, size, type,
  risk, notes, date, selected, postponed or paused.
- Bulk selection and preference editing; clearly distinguish updates that can
  run separately from the system update group.
- Detail drawer: description, changelog, package web links, dependency plan, related conflicts, permission changes, cached download state, exact action, ownership; AUR review includes PKGBUILD/source/diff and explicit trust acknowledgment.
- Per-software actions: Skip This Version, Postpone Until, Pause Updates,
  Resume Updates, Show Notes and Show Requirements. All actions enter history.
- Prevent installation for software marked Not supported, Needs refresh or
  Blocked, and explain the safe next step.

### 5.3 Software Catalog / Install New

- Unified search filters for configured Arch/EOS repositories, AUR, user
  Flatpak remotes and system Flatpak remotes, plus supported additional catalogs.
- Show source, package ID, version, popularity/trust hints only if verifiable, description, screenshots when properly sourced, source trust, installation scope, dependency and permission delta.
- Install/Uninstall/Repair where supported; no automatic source switching. Request explicit selection when same app exists in multiple ecosystems.
- Support searching, paginating, filtering and installing via proper native/AUR/Flatpak backends, including elevation and full-upgrade safety on native installs.
- AUR search results must not be presented as audited or official. Show PKGBUILD and git diffs before builds when changed.
- Firmware is a separate device catalog, not a general software-install repository; AppImages have no universal safe central catalog.

### 5.4 Activity / History

- Update history showing start/end, requested and actual steps, update source,
  user decision, before/after versions, bytes downloaded when known, result,
  reboot requirements and recovery notes.
- Import existing `/var/log/pacman.log` as clearly marked **partial history**,
  plus fwupd and Flatpak history where available.
- Logs with search, filters, copy/export; stdout/stderr captured with ANSI sanitization; redact passwords, tokens, usernames/URLs containing secrets, and other sensitive command arguments.
- SQLite local store (WAL, migrations, idempotent import, retention, safe backups). Do not store privileged credentials. Keep original unmodified system logs.
- Graphs with truthful axes and data: updates completed by week, failures,
  update-source shares, update duration, version age, download volume when
  recorded and time postponed. Empty-data states are clearly labeled.

### 5.5 System Health / Maintenance

- Update-source diagnostics and program versions, last successful checks,
  errors, offline states and timeouts.
- Active pacman database lock owner if determinable; **never remove a lock just because a file exists**. Only offer safe guided recovery after confirming no transaction is active and respecting eos-update behavior.
- Arch and EndeavourOS official news/manual-intervention items with read/acknowledged state and pre-upgrade review.
- Kernel version running vs installed, detected DKMS modules, dracut/hook results, bootloader type, pending reboot; don't claim rollback or snapshot support unless the actual host has a verified usable mechanism.
- `.pacnew`/`.pacsave` inventory, view/diff and manual merge assistance; never automatic overwrite.
- Package cache usage and paccache cleanup with preview; optional snapshots if an actual tested snapper/Timeshift/Btrfs scheme exists.
- Unsupported Node/Rust/Python runtimes and other known end-of-life versions when reliable upstream release/EOL data is available; distinguish advisory from actual update.

### 5.6 Settings

- Update-source controls: check enabled, show updates, allow installation and
  notifications; separate system/user Flatpak controls.
- Check intervals, startup behavior, metered connection options, quiet hours, tray menu, privacy and notification settings.
- Optional background checks, **not** unattended privileged install by default. AUR and firmware installs always demand active user interaction.
- Lists of paused, postponed and skipped software with clear expiry, reset and
  restore actions.
- Data export and retention controls, settings migration, logs diagnostics, environment/compatibility report.
- Appearance settings, including the theme catalog and System default. Theme
  selection belongs here rather than in the persistent top bar.
- Web host controls: listen address, port, URL base, allowed hosts, authentication/session policy, trusted proxy networks, TLS/reverse-proxy status and an explicit LAN-access switch. Do not expose Updatarr beyond loopback merely because the service starts, and reject non-loopback operation unless the configured external origin uses HTTPS directly or through an explicitly trusted TLS-terminating proxy.

### 5.7 Tray / notifications

- Single-instance tray application integrated with Plasma's StatusNotifierItem support (`QSystemTrayIcon` can be used and validated in target Plasma).
- Tray icon states: unknown/checking, up to date, updates available,
  postponed-only, blocked/action required and error; the tooltip shows the
  latest successful check and counts for each update source.
- Left-click opens the canonical local Updatarr web interface in the configured browser (or a future thin webview shell that displays the same UI); menu for Check Now, Review Updates, Pause Checks, Settings, Quit UI; background service may remain if configured; notification throttling/deduplication, no duplicate startup entries.
- Start minimized and on login by standard XDG autostart or a **single** user-systemd service (not both). Handle multiple user sessions reasonably.
- Distinguish app exit from background monitoring; avoid zombie processes or duplicate notification workers.

### 5.8 Visual quality requirements

- **Updatarr identity:** accepted Ultraviolet direction with brand bright `#A78BFA` for marks/highlights on dark surfaces and brand strong `#6D28D9` for accessible controls on light surfaces. Brand violet is not a semantic status color. Secondary tokens require validation in representative light and dark screens.
- **Family resemblance:** inherit Sonarr/Radarr's operational rhythm—persistent responsive side navigation, compact page actions, dense sortable tables, filters, status marks, progress, detail drawers/pages and explicit settings save state—without copying their logos, trademarks, source assets or exact layouts. See [`docs/research/arr-ecosystem-visual-research.md`](docs/research/arr-ecosystem-visual-research.md).
- Tokenized browser themes with System as the default: Light, Dark, AMOLED,
  Solarized light/dark, GitHub light/dark, Norse, Nord, Gruvbox light/dark,
  Dracula, Catppuccin Latte/Mocha, Sepia, Midnight and High contrast. Theme
  choice never changes semantic status meaning or the Ultraviolet identity. See
  [`docs/design/THEMES.md`](docs/design/THEMES.md).
- Deliberate readable typography and icons, responsive desktop/tablet/mobile
  behavior, keyboard navigation, visible focus, reduced-motion support and
  accessible contrast/tooltips.
- Contextual detail panels, searchable virtualized tables for 1,700+ packages, charts/meters with legends and accessible tabular equivalents, progressive disclosure of expert functions.
- Consistent layout hierarchy and status language. Avoid decorative analytics that imply unsupported telemetry or precise timings/sizes not actually measured.
- Replace permanent instructional panels with a small, raised circled
  information control. Every explanation appears in an anchored panel on hover
  or keyboard focus; none requires a click. Longer help may use a wider,
  scrollable panel. Current status, consequences, blockers and required next
  steps must never be hidden as optional help.
- Safety results use an issue-first checklist that Updatarr completes
  automatically. It summarizes passed, needs-attention, not-checked and
  unavailable results before expandable detail; it is not a form the user must
  tick manually.
- Every fabricated or changed screen must pass a full plain-language reading
  review, including help, dialogs, empty/error states, server-provided text and
  accessible names. Technical terms appear only when necessary and with a
  familiar explanation.

---

## 6. Proposed architecture

### 6.1 Runtime / technology

**Provisional starting stack:** one unprivileged Python 3/FastAPI process with a typed domain layer, SQLite, versioned `/api/v1` HTTP commands and reconnectable server-sent events; a React/TypeScript single-page client built with Vite and served as static assets from the same origin; and a small Qt 6/KDE tray and local-approval companion. Phase 0 must validate this stack against the actual host and pin/test supported versions before it becomes accepted. The web service, browser UI and tray never run as root. Use D-Bus, KDE Frameworks and StatusNotifierItem integration where installed and justified. See [ADR 0004](docs/adr/0004-provisional-web-technology-stack.md) and the [primary-source research](docs/research/architecture-security-research.md).

The service is the single source of truth for inventory, policy, plans, history, scheduling and task state. The browser client and KDE tray consume the same API rather than maintaining parallel business logic. A desktop window, if later desired, is only a thin host for the canonical web interface.

```
Browser SPA ───────────────┐
KDE tray / launcher ───────┼── Versioned API + authenticated event stream
                           │                 │
                    Updatarr service (unprivileged, single authority)
                           ├── Planner / Policy / Audit / Scheduler
                           ├── SQLite state and update history
                           └── Update-source registry and capability descriptions
                                  ┌───────────────┼──────────────────────────────┐
                            Native repo/AUR   Flatpak scopes    fwupd    Tools/AppImage
                            pacman/yay/eos    commands/API      D-Bus    rustup, fnm,...
                                  └───────────────┼──────────────────────────────┘
                                          Scoped execution adapters
                                          ├── normal user actions
                                          └── minimal authenticated helper / Polkit
```

### 6.2 Web hosting and remote management

- Serve the SPA and API from one origin. The default listener is loopback-only; enabling a LAN listener is an explicit administrator choice and must never silently open a firewall port or configure a router.
- Require authentication and HTTPS for every non-loopback deployment, either terminated by Updatarr or an explicitly trusted reverse proxy. Refuse cleartext non-loopback credential/session mode. Use Secure, HttpOnly, SameSite session cookies, CSRF protection for state changes, login throttling, session revocation and auditable authentication events. Do not place reusable API credentials in browser storage.
- Validate `Host` and `Origin`; trust forwarded client, scheme and host headers only from explicitly configured proxy networks. Support a URL base and SSE proxying, adding WebSocket support only if later adopted. Document trusted-LAN/VPN and reverse-proxy deployment; direct public-Internet exposure is unsupported until separately threat-modeled and tested.
- Apply authorization server-side to every command. API requests carry typed identifiers and immutable plan hashes, never shell fragments or arbitrary argv. Release notes, logs and update-source metadata are untrusted content and must be escaped/sanitized in the browser.
- Remote browsing, preference changes and update-plan preparation do not weaken the execution boundary. Every software change—including AUR builds, user Flatpak/toolchain changes and AppImage replacement—requires explicit confirmation on the computer being updated. Root-required work then separately requires the approved Polkit/helper permission. Show “Waiting for confirmation on this computer” and “Waiting for administrator permission” distinctly; any future unattended or remotely executable policy requires a separate security design and user approval.
- Provide live reconnectable progress, cancellation only at safe points, API/schema compatibility signaling and a health endpoint that reveals no sensitive inventory before authentication.

### 6.3 Update-source adapter contract

Every update source reports its **capabilities**; unavailable actions are
disabled with an explanation and never report false success:

- `probe()` — discovery, version, ownership, privilege model, scopes, applicable checks.
- `list_installed()` — package and provenance inventory.
- `check_updates()` — detected updates with a timestamp and update-source status;
  no side effects on the active pacman sync database.
- `search(query, scopes, cursor)` — configured catalogs with pagination.
- `describe(target)` — release notes metadata, trust/permissions, links.
- `plan(action, targets, policy)` — exact proposed update plan with requirements,
  safety-check information, warnings and reasons it cannot proceed.
- `execute(approved_plan)` — explicit permission, controlled progress,
  structured log events, safe cancellation and result verification.
- `history()` — past update runs, with origin and completeness markings.
- `set_hold_or_mask()` — **only when an update source safely supports it**;
  otherwise save an Updatarr postponement that blocks unsafe installation.

Include schema version, update-source identifier, installation scope, package
identity, installed/new versions, repository/origin, owner, metadata confidence,
capabilities, reboot requirement, notes source and actual timestamps.

### 6.4 Execution constraints

- UI thread never blocks on downloads/installations; async worker process or subprocess orchestration, bounded concurrency, progress events, cancellation and crash recovery.
- System native/AUR actions acquire a single **app-side coordinator lock** and additionally honor external pacman/ALPM lock; no concurrent or double native upgrades.
- AUR build steps remain unprivileged, locally confirmed and interactive; avoid env-variable credential leakage and never execute unreviewed generated shell commands as root. Treat PKGBUILDs as arbitrary code with user-account access unless a separately tested build isolation design proves otherwise; do not enable live AUR builds before that risk is resolved and service credentials/state are isolated from the build process.
- Prefer native APIs and structured outputs (JSON/D-Bus) where documented; otherwise robust subprocess invocations with **argument arrays**, known executable paths, controlled environment, version-tested exit codes; never arbitrary string shell concatenation.
- For authorized privileged operations, use a narrowly scoped polkit-authorized helper or proven system service. The helper validates fixed operation types and exact sanitized package IDs, works from an immutable approved plan, and rejects arbitrary commands and unsafe paths. Polkit agent supplies desktop password prompt. Avoid root GUI, password handling, `sudo -S`, permissive sudoers entries and password storage.
- AUR, pacman, Flatpak and fwupd operations may ask questions; design safe
  approval windows for update-source prompts and preserve review, stop paths and
  permission boundaries.
- Native package install/search operations must be planned to avoid partial upgrades, including installation of newly searched packages on out-of-date local package databases.
- Never promise cancellation/rollback of irreversible steps. Allow cancellation precommit, request interrupt only at supported safe points, and show 'finishing / cannot safely cancel' when appropriate.
- Downloads and cache reuse follow update-source rules. Never delete package
  database locks blindly. Cleanup must use the update source's supported flow.
- The HTTP listener and web worker remain unprivileged and may not invoke arbitrary commands. All mutating API endpoints require authentication, authorization, current-state revalidation, an anti-CSRF mechanism and an audit event.

### 6.5 Data model / persistence

Suggested normalized tables (IDs and schemas finalized in Phase 1):

- `update_sources`, `installation_scopes`, `software`, `detected_updates`,
  `check_runs`;
- `selection_policies`, `policy_events`, `reviewed_advisories`;
- `update_plans`, `update_runs`, `update_run_steps`, `update_run_logs`;
- `external_history_events` (imported, provenance + dedupe key), `notification_events`, `auth_events`, `web_sessions`, `settings`, `schema_migrations`.

Stable IDs include update source and installation scope; never merge software
solely by display name. Store input snapshots and the plan hash; invalidate a
plan if installed versions, repository information, package locks or other
assumptions change before installation. Internal state identifiers remain in
[DATA_MODEL.md](DATA_MODEL.md); the interface translates them into the plain
language in [GLOSSARY.md](GLOSSARY.md).

---

## 7. Detailed update-source behavior and edge cases

### 7.1 Arch and EndeavourOS

- Read actual `pacman.conf`/configured repos, architecture, IgnorePkg/IgnoreGroup (display existing system holds), package ownership, `/var/log/pacman.log`, mirrors, and installed `checkupdates`/pacman/yay/eos-update versions.
- Safe scan: `checkupdates` (pacman-contrib) uses a separate temporary database; AUR availability via yay's version-tested query or AUR RPC + VCS detection. Do not treat a `checkupdates` nonzero status as necessarily a fatal process failure without consulting its documented conventions.
- Single full native upgrade group, with AUR rebuilds ordered after appropriate native system state; preserve documented eos-update safety preflights. Native packages classified `kernel`, `driver`, `system`, `application`, `library` for UI categorization only.
- Check EOS/Arch important news; show user acknowledgment workflow and manual-intervention guidance, never parse advisory pages as install scripts.
- Pacman hooks (dracut, bootloader, DKMS, etc.) execute unmodified; surface their errors and reboot requirements.
- When pause or postpone choices would require an unsupported partial upgrade,
  mark the plan blocked and explain the safe alternatives.

### 7.2 AUR

- Resolve repo/AUR ownership safely; foreign does not necessarily mean AUR. Disclose maintainer, last-updated, out-of-date flag where available. Allow AUR package installation with code/diff review.
- Handle `-git` VCS rebuilds, pinned versions, split package outputs, repo dependencies, missing/orphaned AUR packages, git clone failures, key/signature errors.
- Never auto-accept changed PKGBUILDs or disable verification; preserve best-practice build/test behavior; show logs and failure recovery.

### 7.3 Flatpak

- Separate `--system` and `--user`, remote and branch, app and runtime, permission deltas, Flatpak ref IDs.
- Native masking/hold support per scope; app-level 'skip this commit' as display policy, not a no-op purported to mask by exact version if unsupported.
- Exactly 21 `com.retro_exo` user apps have disabled local `-origin` remotes. Treat as source-unavailable, preserve versions and disabled trust settings, not ordinary Flathub candidates. No auto remote reenable or GPG bypass.
- On install or update, show scope, remote, branch, permissions and runtime dependencies. Respect official interaction/authorization, avoid root for user scope.

### 7.4 fwupd

- Device-specific checking, supported releases, vendor warnings, required AC power/battery/physical presence and reboot/staging flags; do not assume every device is fwupd-capable.
- Explicit per-device approval; use fwupd's own policy, signature and verification pathway. Show backend history and pending install/activation states.
- Never suppress firmware confirmation, falsely guarantee rollback, or force shutdown/reboot without user approval.

### 7.5 AppImages and self-updaters

- Inventory registered user directories, user-added paths, `.desktop` targets and package ownership. Avoid unbounded filesystem search.
- If file owned by pacman/AUR, ignore as independent AppImage target.
- If embedded update metadata exists and trusted updater available, download to staging, validate, atomic replace with backup/recovery and permission preservation. Otherwise show unsupported/upstream link/manual update status.
- Never infer update availability solely from name-versus-upstream version without matching identity and trusted download artifact.

### 7.6 Other update sources

- `rustup`: user-managed toolchains separately from a pacman-owned rustup
  executable; pause/postpone behavior follows actual command support.
- `cargo`: user-installed binaries only (`cargo install --list`, none at baseline); update support based on installed plugin/helper, not assume built-in `cargo install-update`.
- `fnm`: list managed Node versions; install newer supported LTS release only with explicit version migration/default switching choice; do not overwrite project-specific runtime selection.
- `npm`: examine `pacman -Qo`/prefix/scope of each global package; skip pacman-owned. Avoid modifying project node_modules.
- `uv`: check provenance of `~/.local/bin/uv` and uv-managed tools/Python downloads; skip system interpreters and project venvs.
- Other sources can be future plugins (pipx, snap, Nix, Homebrew, Distrobox, container images, IDE extension managers) **only if detected**; don't preinstall or assume.

---

## 8. Security, trust, reliability and recovery

**Threat model:** malicious AUR PKGBUILDs, spoofed download/notes URLs, command injection in package names, symlink/path manipulation for portable updates, privilege boundary errors, malicious log content, untrusted release notes (HTML), stale repository snapshots, package database corruption, offline and interrupted upgrade, reboot mid-transaction, unauthenticated LAN access, credential/session theft, CSRF, cross-site scripting, DNS rebinding/host-header abuse, malicious reverse-proxy headers and unauthorized remote triggering of privileged work.

Required mitigations:

1. No arbitrary shell execution from package metadata, release notes, or user-selected URL; sanitize rich content and render notes as plain text or trusted browser link.
2. Clear hierarchy: unprivileged web service/UI and KDE tray, regular user-build adapters, fixed-operation polkit helper only for approved privileged operations.
3. No silent permanent trust changes (disable signatures, enable unsigned Flatpak remotes, bypass AUR code review, unsafe package options).
4. Revalidate exactly what will execute after review; immutable approval record includes package/repo/commit/dependency differences; prompt again if materially changed.
5. Reliable update history: append-only event trail, safe SQLite migrations,
   bounded retention, no credentials or secret tokens and clear failures.
6. Respect filesystem permissions, atomic file replacement, collision/symlink defenses, mounted-volume limitations; backup-before-change where feasible.
7. Accept partial failures and report them without claiming the system is up to
   date; verify actual results on the next startup.
8. Never promise universal system rollback; snapshots only when installed and verified, otherwise logs/cached package availability and manual guidance.
9. No unapproved automatic reboot; reboot banner respects fwupd/kernel real state.
10. Security review must independently inspect privilege helper, package parsers, AUR workflow, and command argument validation.
11. Loopback is the default network boundary. Non-loopback access requires authentication and explicit configuration; direct public exposure remains unsupported until a dedicated Internet-facing security gate passes.
12. Browser security tests must cover CSRF, stored/reflected XSS through
    update-source metadata and logs, session fixation/revocation, brute-force
    throttling, origin/host validation, trusted-proxy spoofing, unauthorized API
    calls and leakage from health/error endpoints.
13. Every executable software mutation requires explicit confirmation on the managed host before work starts, even when no root privilege is needed. Root-required work additionally crosses Polkit. AUR builds remain blocked until their user-account access and service-secret isolation are explicitly designed and tested.

---

## 9. Phased delivery (Codex should refine and execute sequentially)

### Phase 0 — Reconnaissance and executable specification

**Goal:** no modifications beyond new project directory. 

Tasks: inspect actual host versions/help/man pages, boot stack, KDE/Polkit
session, update-source ownership, file/layout requirements, Flatpak origins and
external autostart; write architecture decisions, capability matrix, schema,
threat model, executable acceptance tests and responsive *arr-style prototype
wireframes. Use fixed simulated update and failure examples before live tools.

**Gate:** confirmed runtime matrix, list of dangerous actions + safe alternatives, branded responsive mock demo of key flows, approved web/security architecture and user review before any privileged executor.

### Phase 1 — Safe foundation and read-only dashboard

Typed domain models, update-source registry, modular adapters, SQLite migrations,
read-only checks with timeouts and source status, mock drivers, unified results,
versioned API, responsive web UI shell, authentication/session/CSRF foundation,
authenticated event stream and tray mock. Real read-only inventory; no installs.

**Gate:** test counts, source/state accuracy vs native tools, no duplicate repo records, never modifies live pacman db, responsive desktop/mobile UI, dark/light theme, loopback-only default, clean first-run state.

### Phase 2 — Catalog, notes, policies, analytics

Unified official/AUR/Flatpak search, notes and AUR change previews,
postponed/paused/skipped rules, partial-system-update blocking, history import,
initial accurate charts and source-unavailable diagnostics.

**Gate:** skip/postpone/pause persistence; blocked partial system updates;
Flatpak scoped holds; clearly distinguished search results; no invented release
notes; good performance with 1,700+ installed packages.

### Phase 3 — Update planning and permission

Exact update plans, requirements/permissions/size review, full system updates,
safe reviewed AUR builds, user/system Flatpak installation, minimal Polkit
boundary, progress, cancellation rules and result verification. Use simulations
first, then tightly scoped live trials with explicit user approval.

**Gate:** security review; no root web/tray process or AUR builds; no unsafe pacman command, no double native transaction, cancellation/failure handled, web authentication is hardened and privileged authorization works in KDE Wayland.

### Phase 4 — Firmware, kernels, developer tools, AppImages

fwupd device updates/consent and reboot state; kernel/dracut/DKMS/boot classification and preflights; EOL warnings; registered AppImage updateable-file flow and fallback; Rust/fnm/npm/uv/Cargo optional adapters; maintenance.

**Gate:** supported cases work with fixtures and verified live-safe tests, missing/unsupported cases clearly identified, no damage to system-managed runtimes or disabled Flatpak bundle remotes.

### Phase 5 — KDE polish, packaging, replacement and migration

Native KDE tray/launcher and service startup, robust notifications, web UI polish/accessibility/charts, responsive browser validation, app package and install/uninstall scripts, compatibility checklist, operator guide, settings export and supported reverse-proxy examples. Pilot side-by-side with Octopi but only one notifier active at a time; swap notifier after proving correct monitoring. **Only then**, with explicit confirmation, remove Octopi package and Octopi notifier autostart entry safely, and optionally stale Pamac launcher. Do **not** automatically remove PackageKit, pacman, yay, eos-update, fwupd or other backends.

**Gate:** reboot/login persistence, single instance and tray, feature-parity checklist signed off, rollback plan verified, no lost update coverage.

### Phase 6 — hardening and ongoing maintenance

Reboot/interrupted transactions, alternative pacman lock holders, unavailable repos, malformed/hostile metadata, unsigned/local bundles, renamed packages, AUR failures, versioned runtime conflicts, API changes, high-DPI, dark/light UX, long-running operations; independent code/security/UI testing, performance profiling, documentation.

**Gate:** acceptance suite and recovery drill passed, release tagged, upgrade procedure documented, known unsupported features called out.

---

## 10. Minimum end-to-end acceptance scenarios

1. An update source with no updates is not confused with offline, errored or
   turned off; the last check and “Needs refresh” time are visible.
2. 1,680+ repo packages and 38 foreign packages are inventoried without confusing foreign with AUR; native updates are not duplicated.
3. At least two real Flatpak scopes work; 21 disabled local-origin bundles remain unchanged and show correct source-unavailable state.
4. Arch `checkupdates` scan leaves active sync databases untouched; no `pacman -Sy` partial-sync scenario.
5. Selecting one repository package from a larger system update does **not**
   launch an unsafe partial update; the UI offers all system updates or postpones
   them.
6. A postponed update remains visible; a skipped version reappears when a newer
   version is found; pauses survive restart/expiry; a turned-off source is not
   reported up to date.
7. AUR update requires current-safe native state, PKGBUILD diff review, user-mode build, explicit accept, and correct install privileges.
8. Searching a package present in official repos/AUR/Flatpak shows distinct source IDs, metadata and installation choices; no automatic source switch.
9. System Flatpak requests native auth as needed; user Flatpak does not unnecessarily elevate; masks/unmasks only intended scope.
10. fwupd device unsupported/AC-power-required/staged-for-reboot flows are handled without false success.
11. Node/npm package owned by pacman is not overwritten by npm; unowned uv executable is not automatically self-updated.
12. AppImage path registered from local file with no embedded update metadata shows unsupported, not updateable; pacman-owned AppImage is managed only as native package.
13. Kernel/dracut package transaction preserves hooks and surfaces reboot/failed hook status; never claims snapshot rollback that wasn't configured.
14. Policy-checked privileged operation rejects arbitrary argv/path injection; GUI has no superuser privileges; process logs redact sensitive strings.
15. After a simulated crash during an update, Updatarr verifies actual results
    on restart and does not report an interrupted or unknown update as complete.
16. UI remains responsive with thousands of rows and multiple simultaneous *read-only* checks; no concurrent native *write* transactions.
17. Tray count exactly matches updates ready to review; postponed, paused and
    errored groups are separately explained; no duplicate notifier.
18. Logs, charts and history show real or properly labeled imported data, including failed steps and timestamps; export works.
19. No Octopi removal, autostart reconfiguration, or PackageKit removal before Phase 5 explicit approval.
20. Clean build/run, format/type/static analysis, unit/integration tests, end-to-end mocked safety checks, independent review; provide results/evidence.
21. Updatarr binds only to loopback by default. Enabling LAN access requires authentication; CSRF, origin/host, session, proxy-spoofing and unauthorized-action tests pass, while unauthenticated health/error responses expose no sensitive inventory.
22. The same update and source status appears in desktop/mobile browsers and the
    KDE tray; live progress reconnects without duplicating work, every remote
    change waits for confirmation on the computer being updated, and
    administrator work separately waits for Polkit permission.

---

## 11. Required project files and development discipline

Codex must maintain:

```
README.md                     User-facing overview, safe local run, install, uninstall, status
PLAN.md                       This product and engineering specification (preserve requirements)
ARCHITECTURE.md               Diagrams, components, provider contracts, auth boundary, ADR links
DATA_MODEL.md                 Canonical conceptual entities, relationships and state transitions
CAPABILITY_MATRIX.md          Verified per-provider features/version limitations
SECURITY.md                   Threat model, policies, redaction, authorization, AUR trust
TEST_PLAN.md                  Tests, risk matrix, fixture inventory, acceptance gates
MILESTONES.md                 Phases, task status, scope, evidence, blockers
CHANGELOG.md                  Human-readable release notes
OPERATIONS.md                 Health, logs, recovery, rollback, migration procedures
AGENTS.md                     Project-local, project-agnostic-friendly agent workflow (if needed)
docs/adr/                     Dated architecture decisions
docs/research/                Source-backed product and technical research
src/                          Service/domain/providers/auth/storage and KDE tray source
web/                          Responsive browser client, design tokens and frontend tests
scripts/                      Read-only probes/dev tools/packaging (no side-effect auto execution)
tests/                        Mocks, contract/unit/integration/UI/safety/e2e tests
```

- Scope work into explicit milestones and narrow tasks. An orchestration agent assigns **single-task** implementation subagents with only relevant comprehensive context, while **independent testing/review subagents** verify and attempt to break the work. Obey user-existing global OpenCode/Codex instructions where applicable; do not overwrite them.
- First build a no-root runnable service/web UI with fixtures, then read-only integration, only then allow authenticated execution. Each milestone closes with code review, tests, regression, docs and a user-readable summary.
- If an external feature cannot be verified on this machine, keep adapter disabled with a capability-status message and targeted tests; do not speculate, auto-install dependencies, or hide failure.
- Never remove Octopi or alter boot/network/system configuration as a side effect of starting this project.

---

## 12. Research and authoritative references

Consult current installed `--help`/man pages, then these stable provider sources (links included to guide Codex; versions may change):

- [ArchWiki — System maintenance](https://wiki.archlinux.org/title/System_maintenance)
- [ArchWiki — Pacman](https://wiki.archlinux.org/title/Pacman)
- [ArchWiki — Official repositories JSON search](https://wiki.archlinux.org/title/Official_repositories_web_interface)
- [ArchWiki — AUR RPC API](https://wiki.archlinux.org/title/Aurweb_RPC_interface)
- [ArchWiki — Makepkg](https://wiki.archlinux.org/title/Makepkg)
- [Arch Linux news / RSS feeds](https://archlinux.org/feeds/)
- [EndeavourOS — eos-update tips](https://gitlab.com/endeavouros-filemirror/PKGBUILDS/-/blob/master/eos-update/eos-update-tips.md)
- [EndeavourOS — important news](https://github.com/endeavouros-team/Important-news)
- [yay manual](https://github.com/Jguer/yay/blob/next/doc/yay.8)
- [Octopi releases/feature history](https://github.com/aarnt/octopi/releases)
- [Flatpak — Usage](https://docs.flatpak.org/en/latest/using-flatpak.html)
- [Flatpak — Masking](https://docs.flatpak.org/en/latest/tips-and-tricks.html#masking)
- [Flathub — User vs system](https://docs.flathub.org/docs/for-users/user-vs-system-install)
- [fwupd — fwupdmgr](https://github.com/fwupd/fwupd/blob/main/src/fwupdmgr.md)
- [AppImage — Updating](https://docs.appimage.org/packaging-guide/optional/updates.html)
- [Qt 6 — System tray](https://doc.qt.io/qt-6/qsystemtrayicon.html)
- [Servarr — official application family](https://wiki.servarr.com/)
- [Sonarr — product site and web-interface examples](https://sonarr.tv/)
- [Radarr — product site and web-interface examples](https://radarr.video/)
- [`docs/research/arr-ecosystem-visual-research.md`](docs/research/arr-ecosystem-visual-research.md) — bounded ecosystem, interface and official-asset color research for Updatarr

**Source freshness and changes:** treat these as design references, not a license to assume exact installed CLI options, return codes, JSON fields, or capabilities. Version-check on the target machine and feature-detect at runtime.
