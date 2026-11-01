# M6 acceptance

**Prepared:** 2026-10-30  
**Status:** accepted by the user on 2026-10-30

M6 hardens recovery, lock handling, untrusted metadata, large inventories,
browser compatibility and release operations. It prepares a versioned local
evaluation artifact but does not publish a release, install a package, enable a
service, change a notifier or run a live software update.

## Delivered

- Restart reconciliation that never replays a plan and reports success only
  after every expected version is positively verified.
- Typed read-only pacman lock observation for no lock, alternative owner,
  current-process owner and owner not visible; every present lock blocks and is
  left untouched.
- Additional hostile/unavailable input coverage, including Unicode direction
  and zero-width controls, AUR timeout, literal wildcard search and unknown
  package-renaming relationships.
- SQLite schema 6 with indexed server-side inventory paging and rollback proof
  for an interrupted transaction.
- A Software pager that shows the full recorded count and keeps only 100 rows
  in the browser at a time instead of silently hiding records after 500.
- API version 1 negotiation that stops an incompatible page/service pair with a
  plain explanation.
- High-density and 400% reflow-equivalent browser checks in addition to all 18
  themes, documented responsive widths, 200% zoom, reduced motion, keyboard,
  accessible-name and plain-language checks.
- A repeatable 10,000-record performance profile, full security control review,
  22-scenario acceptance matrix, upgrade/recovery runbook and published known
  limitations.
- A deterministic 0.6.0 M6 source archive and staged evaluation package inputs.

## What to review in the browser

The main visible M6 change is **Software → Installed**. After a software check,
the page now shows a quiet range such as **1–5 of 5 recorded** above the table,
with Previous and Next controls when more than 100 results exist. The lower-left
build stamp reads **Version 0.6.0 · Build M6**. Other M6 work is primarily
failure handling, security, performance and operator evidence.

## Release blockers retained on purpose

- The owner has not selected a redistribution license.
- This workspace is not a Git checkout and has no authenticated commit/tag or
  approved release signing/generated-asset provenance policy.
- Live AUR builds remain blocked until build isolation protects Updatarr state,
  credentials and unrelated user data.
- Every first live software-changing path, helper install, service/notifier
  change and Octopi/Pamac removal still requires its separate approval.

These blockers prevent publication or unsupported live claims; they do not
hide a failed M6 evaluation check. Full detail is in
[Known limitations](KNOWN_LIMITATIONS.md).

## Acceptance gate

- [x] Interrupted-run, database rollback and alternative lock-holder drills pass.
- [x] Hostile metadata, unavailable source and ownership/identity checks pass.
- [x] Accessibility, responsive, theme and target-scale performance checks pass.
- [x] Security review, operator recovery guide and known-limitations list exist.
- [x] Complete automated suite, package drill and independent end-to-end review
      are recorded without unresolved significant findings.
- [x] User accepts M6. Release publication remains blocked until the named
      publication decisions are resolved.

The package includes the [acceptance matrix](research/m6-acceptance-matrix.md)
and security review. Exact artifact hashes, final command output and the
independent closure report are build-time evidence retained outside the
evaluation archive so those records do not change the artifact they describe.
