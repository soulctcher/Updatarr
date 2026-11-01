# ADR 0008: Evented saved choices and separate outside history

- **Status:** accepted for M2 implementation
- **Date:** 2026-10-25

## Context

Updatarr needs a current view of postponed, skipped, paused and turned-off
choices without losing who changed a choice or when it expired. It also needs
to show pacman and Flatpak activity that happened outside Updatarr without
misrepresenting those records as reviewed Updatarr update runs.

## Decision

Store each current saved choice with its exact update-source-qualified target,
and append a separate event whenever that choice is created, expires or is
removed. A native postpone or pause targets the whole system update group.

Store imported activity in a separate append-only table with its outside
source, deterministic import key and completeness label. Imported activity
does not create an Updatarr plan, approval or update run.

## Consequences

- Current settings are inexpensive to read while decision history remains
  inspectable.
- Re-importing an unchanged history source is idempotent.
- Journal rotation and incomplete system logs remain visible limitations rather
  than being treated as complete history.
- Future provider-level holds or masks remain separate typed mutations; an M2
  saved choice changes only Updatarr state.

## Alternatives rejected

- **Overwrite one settings document:** loses expiry and removal provenance.
- **Treat imported records as update runs:** invents review, approval and
  completion evidence that the outside logs do not contain.
- **Write pacman holds or Flatpak masks immediately:** crosses a provider-state
  mutation gate that M2 does not authorize.
