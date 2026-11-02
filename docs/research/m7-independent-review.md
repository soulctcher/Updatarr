# M7 Independent Review

**Reviewed:** 2026-11-01
**Result:** implementation re-review passed; RC1 candidate review aborted after
package inspection found a built-in demonstration password; RC2 review pending
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

The RC1 application suite subsequently passed **322 tests in
194.85 seconds** with one known third-party deprecation warning. TypeScript
checking, the Vite production build, Python compilation, package-source
verification and the exact final disposable lifecycle also passed.

## Retained Gates

The review treats these as intentional blockers, not implementation defects:

- no approved remote, push or public release exists;
- AUR source acquisition, clean dependency root and dependency preparation are
  not implemented;
- the managed-computer pilot remains unauthorized; and
- every first live software-changing path remains separately gated.

Rejected RC1's signed local label and detached release-file signatures verify
with the owner-controlled key, but valid signatures do not make the defective
package acceptable. The accepted bounded AUR prototype satisfies the owner's
M7 candidate gate, but it does not enable live AUR. Corrected RC2 requires a
complete new candidate review before owner acceptance.
