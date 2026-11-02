# M7 Independent Review

**Reviewed:** 2026-11-01
**Result:** corrected RC2 passed final independent review with no critical,
high or medium findings
**Scope:** current M7 changes since baseline commit `373cb91`

## Initial Findings

The independent reviewer initially rejected the changes with three high and
four medium findings:

- unbounded child-process output could consume host memory;
- the writable AUR build tree lacked a proven aggregate storage boundary;
- the evidence generator could delete an arbitrary selected output directory;
- the documented Module interface was narrower than the real constructor;
- artifact prefixes and duplicates were not handled exactly;
- retention I/O failures escaped the structured result; and
- the clean-build status claimed final evidence before final hashes existed.

## Resolutions

The AUR Module now continuously drains process output into fixed-size tails,
uses a verified `/dev/shm` tmpfs under the cgroup memory ceiling, bounds input
and aggregate package bytes, removes production executable/limit overrides,
uses no-follow source copying with inode revalidation, selects the longest
expected package identity, rejects duplicates and converts retention I/O
failures to **Unavailable**.

The evidence generator resolves its output, refuses every existing target and
publishes staged results only to a new path. Milestone and clean-build records
remain open until exact final evidence is recorded.

Focused regression evidence passed 21 tests without resource-pressure
fixtures. The independent re-review found no remaining critical, high or
medium implementation issue in the reviewed fixes.

The corrected RC2 application suite passed **324 tests in 195.73 seconds** with
one known third-party deprecation warning. TypeScript checking, the Vite
production build, Python compilation, package-source verification and the exact
final disposable lifecycle also passed. Two extracted RC2 packages contain
neither known development-password string. The focused M7 AUR and release-
evidence suite passed 23 tests in 13.79 seconds after the evidence records were
updated.

## Final RC2 Review

The independent reviewer verified the signed `v0.6.0-rc.2` label and all three
detached signatures from the public-only keyring. The label points to commit
`660f4918ebc612e63953a0014199dfe481c100ef`; no secret or revocation material
is present. Every acceptance hash matched, the release package equals the first
clean build, the source checksum matches the frozen PKGBUILD and the reviewed-
input hashes match the candidate.

The reviewer independently confirmed identical 213-file normalized payloads
and 183-package builder inventories. Only build-time package metadata differs.
Neither extracted package nor either archive contains a known development
password. The lifecycle terminal result, SBOM manifests, retained AUR block and
all publication, host and live-mutation gates also matched the records.

No critical, high or medium finding remains. Two low documentation findings—an
awkward double negative and the stale word “proposed” in the M7 heading—were
corrected before presentation for owner acceptance.

## Retained Gates

The review treats these as intentional blockers, not implementation defects:

- no approved remote, push or public release exists;
- AUR source acquisition, clean dependency root and dependency preparation are
  not implemented;
- the managed-computer pilot remains unauthorized; and
- every first live software-changing path remains separately gated.

Rejected RC1's signed local label and detached release-file signatures verify
with the owner-controlled key, but valid signatures do not make the defective
package acceptable. Corrected RC2's label and detached signatures also verify
from a fresh public-only keyring. The accepted bounded AUR prototype satisfies
the owner's M7 candidate gate, but it does not enable live AUR. RC2 is now ready
for owner acceptance.
