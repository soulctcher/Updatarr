# M1 read-only validation

**Captured:** 2026-10-24  
**Scope:** project implementation and read-only local inventory only  
**Host changes:** none

## What was validated

The application ran its live inventory coordinator against the closed M0 probe
registry. Those probes resolve trusted absolute executables and allow only local
installed-state commands. The run did not refresh pacman or firmware metadata,
contact an update catalog, install software, change an origin or write outside a
temporary test database.

| Update source | Direct local-tool count | Updatarr count | Reported state |
| --- | ---: | ---: | --- |
| System packages | 1,743 | 1,743 | Not checked |
| Flatpak, current user | 22 | 22 | Not checked |
| Flatpak, whole system | 1 | 1 | Not checked |
| Firmware devices | 29 | 29 | Not checked |
| Rust toolchains | 1 | 1 | Not checked |

Updatarr stored 1,796 records and 1,796 unique stable identities. It reported
zero detected updates because update availability was deliberately not queried.
The native result also recorded 42 packages absent from configured sync
databases as source-not-confirmed; it did not claim that they came from AUR.

Firmware identifiers are converted to stable one-way pseudonyms before the
provider parser receives them. Public probe reports retain full redaction.

## Commands represented by the evidence

- Updatarr coordinator using `live_adapters()` and a temporary SQLite database.
- Direct counts from `pacman -Q`, `pacman -Qm`, scoped `flatpak list --app`, and
  `rustup toolchain list`.
- Firmware count from the accepted `fwupdmgr get-devices --json` read-only
  probe; no refresh or update query.

## Result

The source/count accuracy portion of the M1 gate passed. The active pacman sync
database was not touched, and all update-availability states remained truthful.

## Automated evidence

Run from the repository root in the locked project environment:

```bash
uv sync --extra test
npm --prefix web run check
npm --prefix web run build
.venv/bin/python -m compileall -q src tests scripts
.venv/bin/python -m pytest -q
```

The final counts and independent-review disposition are recorded in the
[M1 acceptance packet](../M1_ACCEPTANCE.md). The suite includes negative cases
for mismatched Flatpak scopes, truncated output, snapshot rewrites, overlapping
cancellation, insecure backup modes, retired themes and live post-connection
events.

## Scale observation

A synthetic 10,000-record snapshot was saved to a temporary database in 57.41
ms, then filtered to 100 matching rows in 70.69 ms on this host. These are
observations, not retroactively invented pass/fail budgets. The browser API
limits one response to 500 rows.

## Visual evidence

- [Overview, Ultraviolet desktop](../design/screenshots/m1-overview-ultraviolet-desktop.png)
- [Software, Ultraviolet desktop](../design/screenshots/m1-software-ultraviolet-desktop.png)
- [History, Norse desktop](../design/screenshots/m1-history-norse-desktop.png)
- [Updates, Norse mobile](../design/screenshots/m1-updates-norse-mobile.png)
