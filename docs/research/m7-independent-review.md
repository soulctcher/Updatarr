# M7 Independent Review

**Reviewed:** 2026-11-01
**Result:** implementation re-review passed; retained release gates remain
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

The final complete application suite subsequently passed **321 tests in
193.39 seconds** with one known third-party deprecation warning. TypeScript
checking, the Vite production build, Python compilation, package-source
verification and the exact final disposable lifecycle also passed.

## Retained Gates

The review treats these as intentional blockers, not implementation defects:

- exact copyright-holder text is pending;
- generated-logo redistribution terms remain unconfirmed;
- no approved remote, signed release label or signed artifact exists;
- AUR source acquisition, clean dependency root and dependency preparation are
  not implemented;
- the managed-computer pilot remains unauthorized; and
- a release candidate cannot be declared while the owner-selected 4B AUR gate
  remains open.
