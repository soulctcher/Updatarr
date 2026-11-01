# ADR 0007: explicit SQLite state store

**Status:** accepted; M1 milestone accepted by the user  
**Date:** 2026-10-24

## Context

M1 needs a small durable boundary for immutable inventory snapshots, background
tasks, audit history, appearance preferences and web sessions. The data shape is
known and narrow. Updatarr also needs exact transaction, retention, backup and
append-only behavior to remain visible during security review.

## Decision

Use Python's standard `sqlite3` interface behind one `StateStore` Module. Keep
SQL, transaction ownership, JSON encoding, WAL setup, migrations, file
permissions, event retention and backup inside that Module. Domain, provider,
HTTP and browser code do not issue SQL.

The first schema migration is one idempotent transaction. Audit rows reject
updates and deletion in SQLite. Session IDs are SHA-256 digested before storage;
password verifiers use Argon2id. Presentation preferences remain separate from
audit and inventory records.

## Consequences

- M1 has no object-relational mapping or migration-framework dependency.
- Schema changes require reviewed explicit migrations and restore tests.
- Repository methods stay task-oriented so a future storage change does not
  leak SQL concepts into the rest of the application.
- A migration framework may be reconsidered only when schema evolution becomes
  complex enough to justify another dependency and abstraction layer.
