# ADR 0002: Native repository packages form one upgrade group

- **Status:** accepted
- **Date:** 2026-10-23

## Context

Arch Linux supports full system upgrades rather than arbitrary partial
repository upgrades. Pacman, yay and eos-update overlap around the same native
package database and cannot be modeled as independent owners.

## Decision

Represent configured repository packages as one native ownership domain and one
full-upgrade consistency group. Package selection can filter notifications or
defer the whole group, but cannot authorize an unsafe subset transaction.

AUR work is ordered after the compatible native state and uses a separate
review/build stage without creating a second repository upgrade.

## Consequences

- The planner, not the browser, enforces native grouping.
- Updatarr may refuse an apparently simple per-package request.
- UI language must explain the group and supported alternatives before install.
- Safety tests can assert the invariant at one deep planning seam.

## Alternatives rejected

- **Warnings plus “force anyway”:** still enables unsupported system state.
- **Independent pacman/yay/eos providers:** duplicates updates and risks
  concurrent or repeated transactions.
- **Persistent IgnorePkg as ordinary app policy:** changes system-wide behavior
  and is outside MVP.
