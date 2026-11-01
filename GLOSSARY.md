# Updatarr language

Updatarr uses familiar update-manager words. Labels should explain themselves;
help text may add detail, but must not be required to decode a label.

## Software and update sources

**Update source**:  
A program or service that checks or manages one kind of software, such as
pacman, Flatpak or fwupd.
_Avoid_: Provider, backend, ownership domain

**Installation scope**:  
The place in which an update source manages software, such as Flatpak for the
current user or Flatpak for the whole system.
_Avoid_: Provider scope, instance

**Software**:  
An installed or discoverable app, package, runtime, library, firmware release
or toolchain identified by its update source and installation scope.
_Avoid_: Item, artifact

**Origin**:  
The repository, remote or catalog from which an update source obtains software.
_Avoid_: Update source when the exact repository or remote matters

**Software catalog**:  
Searchable software information from one or more update sources. A catalog
result does not mean the software is installed or ready to install on this
computer.
_Avoid_: Store, marketplace

**Catalog result**:  
One source-specific software search result. Results with the same name remain
separate when their update source, origin or installation scope differs.
_Avoid_: Universal package, merged result

**Source information**:  
A description, notice or other text shown with the organization, link and time
it came from. It is not renamed as release notes when the source did not call it
release notes.
_Avoid_: Trusted content, verified notes

**Detected update**:  
A newer version or revision reported by an update source at a recorded time. It
may be ready, blocked or postponed.
_Avoid_: Offer, update offer

**Software check**:  
A read-only request that records installed software and reports separately
whether each update source also checked for newer versions.
_Avoid_: Scan when no broad search occurs, refresh when metadata is not refreshed

**Safety check**:  
A read-only check of requirements that must be true before a particular update
can be reviewed or started. A passed safety check is not permission to update.
_Avoid_: Preflight in ordinary interface text, validation when nothing is approved

**Safety checklist**:  
A compact summary of safety checks that Updatarr performs automatically. It
shows what passed, what needs attention, what was not checked and what Updatarr
cannot check. A person reviews the list but does not tick boxes manually.
_Avoid_: User checklist, preflight dashboard, readiness matrix

**Startup-related update**:  
A system-package update that can affect the kernel, hardware drivers, early
startup files or boot loader. It stays in the complete system update group.
_Avoid_: Boot transaction, kernel provider

**Portable app**:  
An app kept as a standalone file, such as an AppImage, rather than installed by
a system package source. Updatarr manages it only when file ownership and its
declared update method are supported.
_Avoid_: Artifact, binary blob

**Maintenance preview**:  
A read-only list and size estimate of files that could be removed later. A
preview does not remove anything and is separate from software updates.
_Avoid_: Cleanup when only a preview has occurred, dry run in ordinary text

**System update group**:  
All configured Arch and EndeavourOS repository updates that must be installed
together to keep the system supported.
_Avoid_: Native group, atomic group, consistency set

## Review and installation

**Update request**:  
What a person asks Updatarr to change before safety and dependency checks.
_Avoid_: Intent, command

**Update plan**:  
The exact updates, order, requirements, warnings and blockers shown for review
before anything changes.
_Avoid_: Transaction, job

**Review approval**:  
A signed-in person's acceptance of one exact update plan.
_Avoid_: Authorization

**Confirmation on this computer**:  
Approval made from the computer being updated before an update plan may run.
_Avoid_: Local confirmation, remote approval

**Administrator permission**:  
The operating system's decision to allow an update that needs administrator
access.
_Avoid_: Authorization, review approval, login

**Background task**:  
Work that Updatarr performs over time, such as checking for updates or preparing
an update plan.
_Avoid_: Job, transaction when nothing is installed

**Update run**:  
One attempt to carry out an approved update plan, including what actually
happened and whether recovery is needed.
_Avoid_: Transaction, plan

**Result check**:  
The check of actual software and system state after an update, interruption or
restart.
_Avoid_: Reconciliation, retry, rollback

**Follow-up action**:  
Something still required after an update, such as restarting, shutting down,
reconnecting a device or activating firmware. Each action remains distinct.
_Avoid_: Reboot required when a different action is needed, pending state

## Choices

**Turn off an update source**:  
Stop checks and changes for one update source while keeping its last known
information visibly out of date.
_Avoid_: Disable provider, ignore

**Postpone**:  
Keep a detected update visible but leave it out until a chosen time, condition
or manual resumption.
_Avoid_: Defer

**Skip this version**:  
Hide one exact detected version until a different version is found.
_Avoid_: Ignore update, hold

**Pause updates for software**:  
Prevent one piece of software from changing until the pause is removed or
expires. If it cannot safely be held alone, the whole system update group waits.
_Avoid_: Pause item

**Saved choice**:  
A lasting decision to postpone, skip a version, pause software or turn off an
update source. Its exact target, reason and expiry remain visible.
_Avoid_: Policy, rule in ordinary interface text

**Remove from this update**:  
Leave separately updateable software out of the current plan without saving a
lasting rule.
_Avoid_: Deselect, postpone

## Status

**Ready to review**:  
A detected update is current and safe to include in an update plan, subject to
review and any required permission.
_Avoid_: Actionable, available when readiness matters

**Blocked**:  
A known update cannot proceed until the stated problem or dependency is fixed.
_Avoid_: Error

**Error**:  
An update source or Updatarr operation failed. Show the specific cause and a
safe next step when known.
_Avoid_: Blocked, unavailable

**Turned off**:  
Checks and changes for an update source were intentionally stopped in settings.
_Avoid_: Disabled in ordinary interface text

**Source unavailable**:  
The configured origin cannot currently provide update information.
_Avoid_: Not supported, up to date

**Not supported**:  
Updatarr cannot safely perform the requested operation for this software or
update source.
_Avoid_: Unsupported in ordinary interface text, error

**Not managed**:  
Updatarr can identify the software but no configured update source controls it.
_Avoid_: Unmanaged in ordinary interface text, not supported

**Needs refresh**:  
The last known information is too old or follows a failed or turned-off check.
_Avoid_: Stale in ordinary interface text, current

**Not checked**:  
No applicable check has completed for the current settings.
_Avoid_: No updates

**Up to date**:  
A current successful check found no applicable updates.
_Avoid_: Healthy when only update availability is known

**Source working**:  
An update source completed its expected check and the result remains current;
updates may still be available.
_Avoid_: Healthy in ordinary interface text, up to date

## History

**Imported activity**:  
Earlier software changes read from another program's history. It is labeled
partial when the source cannot prove the whole history and never implies that
Updatarr reviewed or performed the change.
_Avoid_: Update run, complete history
