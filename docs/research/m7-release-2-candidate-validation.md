# M7 Release-2 Candidate Validation

**Prepared:** 2026-11-02  
**Status:** project-local candidate validated; not signed, installed or accepted  
**Candidate package:** `updatarr 0.6.0-2`

## Scope

This candidate responds to the owner's RC2 pilot review and corrects RC2's
packaged user-service defect. It does not authorize installation, service
enablement, notifier changes, publication or any software-changing action
through Updatarr.

## Interface Results

- The Overview action remains **Check software** and now explains why many
  sources truthfully remain **Not checked**.
- Installed software no longer repeats an identifier that matches its name.
- The installed-software header remains visible while its long list scrolls.
- Detected Updates has a named Select all checkbox with selected, clear and
  mixed states.
- Safety Checklist text explains that Passed is a result, gives a direct
  next step only when one exists and exposes recorded update-source details.
- The tray checklist names `http://127.0.0.1:8788` and explains that it works
  only on the managed computer.

Focused browser tests exercised the changed interactions. The broader M2/M4
browser and safety suites passed across desktop, mobile and every included
theme. Desktop and 390-pixel visual captures were reviewed without a new
overflow or hierarchy problem.

## User-Service Correction

The package retains `PrivateTmp=true` and `NoNewPrivileges=true`. Fixed system
tools can use Linux's overflow user identity only after the namespace map,
non-writable `/usr` path and every symbolic-link target directory pass. Pacman
must still report the exact expected package owner. Missing or contradictory
evidence fails closed.

Short-lived real user-service checks with `PrivateTmp=true` completed:

- `/usr/bin/pacman` as package `pacman`;
- `/usr/bin/npm`, through its root-owned link, as package `npm`; and
- `/usr/bin/cargo`, through its root-owned link, as package `rustup`.

The independent review initially found that link ownership had not crossed the
new seam. That high finding was reproduced, fixed and covered by both a unit
regression and the npm/Cargo transient-service check. Re-review requested
negative cases for an outside-`/usr` target, writable target, writable target
directory and symbolic-link target directory. Those cases now fail closed.
Final standards and spec re-reviews found no remaining issues.

## Build and Lifecycle Evidence

Two sequential networkless, 2 GiB-limited clean builds produced the same
normalized payload and identical builder inventories. Archive bytes differ
only in Arch's generated build metadata.

| Evidence | SHA-256 |
| --- | --- |
| Source archive | `e8cfa64e48ef175ee901001fff7cdb241e647db3644bfcfb613e3c3ef644136e` |
| First package | `ec5813892254e5eeb588bbbaa4c8f33e38edca57677fcc1cf8f88e305d844276` |
| Repeated package | `2105be02f9edb4c0ac9d0af55eaa1562810d0e97e3c7ed8fb61bb88658b8dd05` |
| Normalized payload | `aa0e08e7401327ba40bf162fd8036d8b0c99bc62b0485cf4094ee850a2300571` |
| Builder inventory | `a2cb2bf8ca6db33e144040b4e3a6fc74219f2bad6e9d68671b34362e03b682d0` |
| Lifecycle log | `461dc22a72c613449525e52903d1687acdaf498a749f6a1ee842105a52959c8e` |
| Lifecycle package list | `80e55f0895462e0b06a8995a7fb9edf8aab49c8575c6a3c25c9700d269263668` |

The disposable lifecycle installed RC2 release 1, upgraded to this release 2,
restored saved state, downgraded, uninstalled and preserved the private user
database, configuration and backup. Neither candidate package contains the
known development passwords, an enabled-service link, an autostart entry, a
Polkit file or an install script.

## Final Checks

- Python suite: **333 passed in 195.28 seconds** with one known third-party
  Starlette test-client deprecation warning.
- TypeScript check and production browser build: passed.
- Locked browser dependency audit: no known vulnerabilities.
- Locked Python dependency resolution, Python compilation, shell parsing, Git
  whitespace and Arch source verification: passed.
- Runtime inventory: 18 Python and 3 browser components; declared license
  inventory unchanged.
- Independent standards and spec re-review: passed with no remaining findings.

## Remaining Gate

This package has not been signed or installed. The current live pilot still
uses rejected RC2 through its non-enabled transient core. Owner approval is
required before signing or replacing that installed package. Service enablement
at login, publication, notifier migration and every live software update remain
separate decisions.

