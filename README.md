# Updatarr

Updatarr is a planned local-first software update manager for EndeavourOS and
Arch Linux. It combines package and update visibility in one responsive
*arr-style web interface while preserving the real ownership and safety rules
of pacman, AUR helpers, Flatpak, fwupd and supported user toolchains.

The user has accepted **M0 through M6** and authorized project-local work on
**M7: release candidate and controlled deployment**. Release publication and
live actions remain under their separate gates.
The current loopback-only application can use a safe simulator or live
read-only inventory. Live execution remains disabled until each separate
privileged-helper and first-live-mutation approval gate is explicitly granted.

## Run the development application

Python and frontend dependencies are locked in `uv.lock` and
`web/package-lock.json`; `pyproject.toml` declares the supported direct
dependencies.

```bash
cd web
npm install
npm run build
cd ..
uv sync --extra test
UPDATARR_DEVELOPMENT_MODE=1 UPDATARR_PROVIDER_MODE=simulator \
  .venv/bin/python -m updatarr.main
```

Open `http://127.0.0.1:8788` and use the clearly labeled development password
`updatarr-demo`. To exercise a URL base, set `UPDATARR_URL_BASE=/updatarr` and
open `http://127.0.0.1:8788/updatarr/`. The server defaults to loopback unless
a validated HTTPS deployment explicitly selects a specific
non-loopback address. The theme selector is under **Settings → Appearance**.

When a reviewed simulator plan is waiting for confirmation, its exact plan ID
can be reviewed from an interactive terminal on the managed computer:

```bash
.venv/bin/python -m updatarr.local_approval \
  --state .state/updatarr.db --plan PLAN_ID_SHOWN_IN_UPDATARR
```

This separate surface records the local Unix identity and session. It does not
install software. Administrator plans remain waiting for the separately gated
Polkit/helper flow.

Run the evidence suite with:

```bash
npm --prefix web run check
npm --prefix web run build
.venv/bin/python -m pytest -q
```

## Product shape

- One unprivileged background service owns inventory, plans, policy, history
  and live task state.
- One responsive browser interface works locally and, when explicitly enabled,
  across authenticated HTTPS on a trusted LAN or VPN.
- One KDE tray companion reports status and opens the canonical web interface.
- One narrowly scoped privileged executor may eventually perform approved
  system mutations; it will not accept arbitrary commands.
- Native repository updates remain one Arch full-upgrade consistency group.

## Current safety posture

The default future listener is loopback-only. Authenticated HTTPS LAN access,
live update sources, Octopi migration, autostart changes and all privileged
operations remain gated work. Direct public-Internet exposure is outside the
supported initial model.

## Documentation map

- [Product and technical plan](PLAN.md)
- [Architecture](ARCHITECTURE.md)
- [Domain glossary](GLOSSARY.md)
- [Conceptual data model](DATA_MODEL.md)
- [Capability matrix](CAPABILITY_MATRIX.md)
- [Security model](SECURITY.md)
- [Test plan](TEST_PLAN.md)
- [Milestones](MILESTONES.md)
- [Operations and recovery](OPERATIONS.md)
- [Visual direction and palette choices](docs/design/VISUAL_DIRECTION.md)
- [Theme catalog and token contract](docs/design/THEMES.md)
- [Interface language rules](docs/design/CONTENT_STYLE.md)
- [Phase 0 prototype visual review](docs/design/PROTOTYPE_REVIEW.md)
- [Read-only capability evidence](docs/research/host-capability-snapshot.md)
- [M0 web-stack validation](docs/research/m0-web-stack-validation.md)
- [M0 decision and sign-off packet](docs/M0_DECISIONS.md)
- [M1 read-only validation](docs/research/m1-read-only-validation.md)
- [M1 acceptance packet](docs/M1_ACCEPTANCE.md)
- [M2 catalog, saved-choice and history research](docs/research/m2-catalog-policy-history-research.md)
- [M2 validation](docs/research/m2-validation.md)
- [M2 acceptance packet](docs/M2_ACCEPTANCE.md)
- [M3 validation](docs/research/m3-validation.md)
- [M3 acceptance packet](docs/M3_ACCEPTANCE.md)
- [M4 provider safety research](docs/research/m4-provider-safety-research.md)
- [M4 validation](docs/research/m4-validation.md)
- [M4 acceptance packet](docs/M4_ACCEPTANCE.md)
- [M5 acceptance packet](docs/M5_ACCEPTANCE.md)
- [M6 acceptance packet](docs/M6_ACCEPTANCE.md)
- [Proposed M7 scope and acceptance gate](docs/M7_PROPOSAL.md)
- [M7 owner decisions](docs/M7_OWNER_DECISIONS.md)
- [M7 release-foundations research](docs/research/m7-release-foundations-research.md)
- [Release asset provenance](docs/release/ASSET_PROVENANCE.md)
- [M6 acceptance matrix](docs/research/m6-acceptance-matrix.md)
- [M6 security review](docs/research/m6-security-review.md)
- [Known limitations and release blockers](docs/KNOWN_LIMITATIONS.md)
- [Arch installation and recovery](docs/operations/ARCH_INSTALL.md)
- [Upgrade and interrupted-run recovery](docs/operations/UPGRADE_RECOVERY.md)
- [Trusted network access](docs/operations/NETWORK_ACCESS.md)
- [Octopi migration and rollback](docs/operations/OCTOPI_MIGRATION.md)
- [Architecture decisions](docs/adr/)
- [Research notes](docs/research/)
- [Throwaway Overview prototype](prototypes/overview/README.md)
- [Changelog](CHANGELOG.md)

## Development status

M0 through M6 are accepted, and project-local M7 implementation is authorized.
Its scope and retained publication and live-action gates are listed in
[MILESTONES.md](MILESTONES.md). Commands shown in research sources remain
evidence, not setup instructions. System
dependencies outside the project environment, services, autostart, package
installation, software changes and Octopi migration remain unauthorized.

The repeatable host probe has a closed list of local, read-only commands. List
them without running anything:

```bash
python scripts/read_only_capability_probe.py --list
```

Run only a named probe and review its sanitized JSON on standard output:

```bash
python scripts/read_only_capability_probe.py --probe flatpak-user-remotes
```

The probe does not check for available updates, refresh metadata or write a
fixture automatically. Captured evidence must be reviewed before it is added to
the reduced fixtures under `tests/fixtures/read_only`.
