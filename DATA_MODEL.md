# Updatarr conceptual data model

**Status:** M3 accepted; M4 safety facts and typed simulator operations implemented  
**Language:** [GLOSSARY.md](GLOSSARY.md) is canonical

## Design rules

- Identity always includes update source and installation scope; display names never
  deduplicate records.
- Observed facts are tied to an immutable inventory snapshot and provenance.
- Plans are immutable and content-addressed after review begins.
- Review approval, confirmation on this computer and administrator permission
  are separate facts.
- Update runs append actual outcomes; they do not rewrite the approved plan.
- Imported history is visibly incomplete and never masquerades as an Updatarr
  update run.
- Secrets and sessions are excluded from ordinary settings/history exports.

## Relationship overview

```text
UpdateSource ──< InstallationScope ──< Software ──< DetectedUpdate
                    │                    │               │
                    └────< InventorySnapshot ┘
                                  │
UpdateRequest + PolicySnapshot ───┤
                                  ▼
                            UpdatePlan ──< UpdatePlanStep
                                  │
               ReviewApproval ────┤
          OnDeviceConfirmation ───┤
        AdministratorPermission ──┤ (administrator access only)
                                  ▼
                              UpdateRun ──< UpdateRunStep
                                  │
                                  └──< ProgressEvent / AuditEvent
```

## Catalog and inventory records

### UpdateSource

Stable update-source identity, display metadata, enabled settings and capability
schema version. Source status is not one yes/no value; it comes from the latest
applicable check.

### InstallationScope

Update-source installation context, permission model and configuration
identity. Examples include Flatpak user and Flatpak system.

### Software

Stable update-source-qualified identity, installed state, origin, architecture,
branch/channel and ownership confidence. Descriptive metadata may change
without changing identity.

### InventorySnapshot

Immutable results of one coordinated check: start/end time, per-source status,
input/tool versions, software versions and a generation/hash used for plan drift
checks. Partial snapshots explicitly identify missing update sources.

### DetectedUpdate

Detected version or revision, originating snapshot, evidence timestamp,
metadata confidence, size, notes, reboot facts or explicit unknowns. Detected
updates expire or are replaced; they are not presented as timeless facts.

## Policy records

### SelectionPolicy

Update-source setting, postpone, skip-version or pause rule with exact target
identity, reason, actor, creation/expiry and last application. App-level policy
is distinct from a hold or mask applied by the update source itself.

### PolicyEvent

Append-only creation, expiration, resumption and override record. The current
policy view is derived without losing provenance.

### AdvisoryAcknowledgement

Actor, advisory identity/version, decision and expiry. An acknowledgement can
remove a review prompt but cannot bypass a safety invariant.

## Planning and execution records

### UpdateRequest

Requested action, exact targets, person and creation time before safety and
dependency evaluation.

### UpdatePlan

Immutable once frozen. Contains the update request, inventory generation, policy
snapshot, update-source/tool versions, exact actions, unknowns, warnings,
blockers, expiry and canonical digest.

Update-plan lifecycle:

```text
draft -> checking -> frozen -> awaiting-review -> awaiting-local-confirmation
                                             -> awaiting-authorization?
                                             -> ready-for-execution -> consumed
                                             -> expired
                                             -> invalidated
```

A plan needing administrator access proceeds from confirmation on this computer to
`awaiting-authorization`; an unprivileged plan proceeds to
`ready-for-execution`. Creating its one update run consumes the plan. Any
relevant drift invalidates the plan before execution.

### UpdatePlanStep

Ordered proposed update-source operation, expected permission, dependencies, safe
cancellation phase and user-visible consequences. It contains typed values, not
shell commands.

### ReviewApproval

Signed-in person's acceptance of one plan digest after review. Review approval
does not grant operating-system permission.

### OnDeviceConfirmation

Decision made on the computer being updated that allows one plan digest to
begin changing software. It is required whether or not administrator access is
needed.

### AdministratorPermission

Result of the operating system's permission decision for one root-required plan: local Unix
identity/session, Polkit action, decision time and helper validation result.
Never store credentials.

### UpdateRun

One attempt to carry out one ready plan. Canonical states:

```text
created -> running -> succeeded | partially-succeeded | failed | cancelled
                   -> needs-reboot | needs-manual-recovery
```

Confirmation and administrator permission belong to the plan before an update
run begins. The final state is established by checking actual results, not
merely by observing that a child process exited.

### UpdateRunStep

Actual start/end, update-source result, redacted exit/log references, before/after
state and recovery evidence for one planned step.

## Tasks, history and audit

### BackgroundTask

Durable asynchronous operation with type, actor, state, progress summary and
correlation ID. Read-only checks and planning tasks do not create update runs.

### ProgressEvent

Monotonic sequence within a task with event ID, schema version, timestamp, kind
and typed payload. A bounded durable tail supports SSE reconnection; clients
reload the authoritative task when the requested tail is unavailable.

### AuditEvent

Append-only security and decision record referencing actors, sessions, plan
digests and outcomes without secrets.

### ExternalHistoryEvent

Imported pacman/Flatpak/fwupd history with source, completeness marker and
idempotent deduplication key. It never implies an Updatarr approval or plan.

M2 imports bounded pacman package actions and scoped Flatpak journal history.
Every record remains append-only, carries its outside source, and is marked
partial because neither source proves a complete Updatarr update run.

## Web identity records

### Account

Initial single administrator identity, password-verifier metadata, status and
credential-change time. Additional roles are not modeled until required.

### WebSession

Server-side opaque-session record with hashed/random identifier material, actor,
creation, rotation, idle/absolute expiry, revocation and authentication context.

### AuthenticationEvent

Rate-limit and audit evidence for login, failure, logout, recovery and session
revocation without submitted secrets.

### AppearancePreference

Presentation-only preference associated with an account: stable theme ID,
schema version and modification time. `system` is the default; missing, unknown
or retired theme IDs resolve safely to `system`. Appearance never participates
in inventory, planning, authorization or audit decisions.

## Implemented physical schema

The explicit SQLite state-store Module owns these tables:

- `schema_migrations`;
- immutable `inventory_snapshots` with `snapshot_sources`, `software_records`
  and `detected_updates` children;
- `background_tasks` plus a bounded `task_events` tail;
- trigger-protected `audit_events`;
- presentation-only `preferences`;
- `accounts` and independently revocable `web_sessions`.

The first migration is atomic and idempotent, the database uses WAL mode and
foreign keys, state files are owner-only, and backup evidence restores a
readable snapshot. Full update-source-qualified identities and snapshot
generations are deterministic. Raw session IDs are never stored.

M1 demonstrates:

- uniqueness for full update-source-qualified identities;
- referential integrity within immutable inventory snapshots;
- append-only audit semantics at the repository interface;
- bounded task-event retention without breaking authoritative task state;
- session deletion/revocation independent of update history;
- migration backup and restore.

M2 adds:

- current `selection_policies` with append-only `policy_events` for creation,
  expiry and removal;
- append-only `external_history_events` with deterministic import keys,
  provenance and completeness labels;
- append-only `history_import_batches` with requested range, observed positions,
  skipped-row count and the plain-language reason evidence is incomplete;
- a mutable `history_source_state` cursor that advances the pacman log
  generation after replacement or copy-truncate rotation so new evidence does
  not collide with an older file at the same byte position;
- exact saved-choice matching by the complete stable software identity, including
  origin/repository, architecture and branch where applicable, plus version
  where required;
- derived summaries that return unknown download information as `null` rather
  than inventing a zero; and
- source-qualified catalog and notice responses that are not stored as
  installed-software facts.

M3 adds:

- trigger-protected immutable `update_plans` containing canonical reviewed
  content and a unique SHA-256 fingerprint;
- separately mutable `update_plan_states` with append-only
  `update_plan_events`, so lifecycle progress cannot rewrite reviewed content;
- `update_runs` and append-only `update_run_steps` tied to one plan fingerprint;
- typed, constrained transitions for review, local confirmation,
  administrator permission, readiness, one-time consumption, expiry and
  invalidation; and
- restart reconciliation that marks unfinished work **Needs manual recovery**
  rather than inferring success from a missing process.

The installed schema is version 5. Only simulator runs are enabled in the M3
repository; live records require the separate helper and provider approvals.

M4 adds domain values without a schema migration:

- `M4Capability` records one source-specific safety classification as **Ready
  to review**, **Blocked**, **Not supported** or **Not checked**;
- `SafetyCheck` keeps each requirement and explanation separate;
- `RestartAction` distinguishes restart, full shutdown, reconnect and firmware
  activation instead of reducing them to one Boolean;
- typed plan operations represent one firmware release, staged portable-app
  replacement, Rust toolchain update or exact fnm Node.js version without a
  command or argument field; and
- maintenance previews remain read-only presentation records and do not create
  a detected update or update run.

Live M4 classifications are deliberately **Not checked** until their matching
read-only observations complete. Package ownership and disabled Flatpak origins
remain provider facts and are not rewritten by these records.
