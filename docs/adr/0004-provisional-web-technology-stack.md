# ADR 0004: Provisional web technology stack

- **Status:** accepted
- **Date:** 2026-10-23
- **Accepted:** 2026-10-24 after vertical-slice validation and user sign-off

Use one FastAPI process with typed transport models, a React/TypeScript SPA
built by Vite and served from the same origin, ordinary `/api/v1` HTTP commands,
and reconnectable server-sent events for progress. This fits Updatarr's
predominantly server-to-browser event flow, keeps one application authority for
SQLite and native transaction coordination, and avoids shipping a Node
production server. SQLAlchemy/Alembic versus a smaller explicit SQLite
repository remains an M1 implementation decision.

## Consequences

- The Arch package builds static frontend assets and Python application code.
- Browser and server types must be checked against the versioned OpenAPI/event
  contracts.
- The service starts as one process; bounded provider subprocesses do the
  external work.
- WebSockets are added only if a concrete bidirectional requirement cannot be
  expressed as authenticated HTTP commands plus SSE.
- Frontend dependencies are locked in `web/package-lock.json`; Python runtime
  versions remain host-provided in the proof and need packaging constraints before
  release.

## Considered options

- A separate Node production server adds deployment and trust surface without a
  current need.
- A Qt-only UI fails the remote browser requirement.
- Multiple web workers complicate SQLite writes, task ownership and event
  delivery before scale requires them.

Research basis: [architecture-security-research.md](../research/architecture-security-research.md).
