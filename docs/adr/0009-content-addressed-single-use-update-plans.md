# ADR 0009: Content-addressed single-use update plans

- **Status:** accepted for M3 implementation
- **Date:** 2026-10-26

## Context

The browser, managed-computer approval surface and privileged mechanism act at
different times and trust levels. A person must be able to review one exact set
of software changes without a later request silently changing its targets,
permissions or order. Old approval must not authorize a changed or replayed
request.

## Decision

Serialize the security-relevant plan content in one canonical form and identify
it with a SHA-256 fingerprint. The sealed content includes the inventory
generation, active saved-choice identities, exact typed steps, targets,
permission requirements, blockers, creation time and 15-minute expiry.

Store sealed content in an append-only record. Store lifecycle state and audit
events separately. Browser review, confirmation on the managed computer,
administrator permission and execution all bind to the same plan ID and
fingerprint. Recheck the fingerprint, expiry, inventory generation and saved
choices immediately before each boundary. A plan can be consumed once.

The plan contains operation types and software identities, never a command,
executable path, environment or caller-provided argument list.

## Consequences

- Any relevant software or saved-choice change requires a new review.
- A captured request cannot be replayed after the plan is consumed.
- The local approval surface can show exactly what the browser reviewed.
- Fifteen minutes may be inconvenient during a long review, but bounds stale
  authority and makes preparing a replacement plan inexpensive.
- A future schema change that alters canonical content needs a versioned plan
  format rather than silently changing existing fingerprints.

## Alternatives rejected

- **Mutable plan rows:** approval could outlive changes to targets or steps.
- **Sign only selected IDs:** omits permission, ordering, policy and expiry
  assumptions.
- **Browser sends command arguments:** crosses the execution boundary and turns
  a web compromise into a command-construction surface.
- **Reusable approval:** permits replay after the intended update has finished.

