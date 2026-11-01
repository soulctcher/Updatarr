# M5 independent acceptance review

**Initial review:** 2026-10-29  
**Re-review:** 2026-10-29  
**Reviewer role:** independent acceptance review; no implementation files changed  
**Result:** **pass** — no unresolved critical, high or medium findings

## Review scope

The current M5 tree was reviewed against `AGENTS.md`, `PLAN.md`,
`MILESTONES.md`, `SECURITY.md`, `OPERATIONS.md`, `TEST_PLAN.md`, the M5
acceptance record, the packaging/network research and the M5 runbooks. The
review covered the package boundary, user-service and tray lifetimes, network
startup validation, proxy trust, settings export, notifier migration,
reversibility and the separate live-action gates.

The package and service design follows the repository's principal boundaries:
installation does not start or enable a service; the core and tray are
unprivileged and separate; the tray consumes a minimal owner-only status file;
the settings export is authenticated and restricted; and installation,
service enablement, notifier changes and software removal remain separate
approval decisions.

## Initial findings and resolution

### Resolved — wildcard direct listener

The initial review found that a certificate-backed direct listener could use
`0.0.0.0` or `::` even though the network contract requires one specific bind
address. `DeploymentConfig` now rejects IPv4, IPv6 and bracketed IPv6 wildcard
forms before listener construction. Certificate-backed negative tests cover
all three forms (`src/updatarr/deployment.py:57-61` and
`tests/test_m5_deployment.py:108-123`).

### Resolved — enabled Octopi notifier

The initial one-notifier assessment considered only whether Octopi was active,
which allowed an enabled notifier to return at the next login. Readiness now
requires the Octopi startup owner to be both disabled and inactive while the
Updatarr tray is selected. The suite explicitly rejects the
enabled-but-currently-inactive case (`src/updatarr/deployment.py:168-180` and
`tests/test_m5_deployment.py:159-171`).

### Resolved — notifier rollback fixture

The initial suite did not exercise the documented notifier swap and restore.
A disposable startup-owner fixture now preserves the exact Octopi autostart
file, selects Updatarr, proves exactly one owner, restores Octopi byte-for-byte
with its mode, and reapplies Updatarr while again proving one owner
(`tests/test_m5_deployment.py:174-210`). This is appropriately fixture-backed;
actual login/reboot and notifier changes remain behind their explicit live
approval gates.

## Re-review evidence

During the independent re-review, the source archive and PKGBUILD agreed
exactly:

```text
d3ec28a2cbb75a06df68313b6a483158c00f0be4904f55fe28467fe863cd71fc
```

The focused deployment, provider, tray and capability-probe suite passed after
the fixes:

```text
92 passed, 1 third-party deprecation warning in 1.52s
```

The known warning is Starlette's transition notice for its current test-client
HTTP dependency; it does not represent an Updatarr test failure.

After the pass, an acceptance-status wording change in the packaged README
caused a documentation-only archive rebuild. The project-owner validation
records the final archive and package hashes and a subsequent 24-test
archive/package consistency pass; no reviewed implementation changed.

## Acceptance conclusion

The three initial medium findings are resolved. No new significant finding was
introduced by the fixes, and no critical, high or medium issue remains. M5
passes independent review. The project owner subsequently recorded the final
full suite and package checksum in the M5 validation record. None of the
separately gated host actions is authorized by this review.

## M5 interface refinement re-review — 2026-10-29

The five requested refinements were reviewed independently in the current
tree. The focused real-browser suite passed **7 tests in 58.45 seconds**. It
exercised desktop and mobile layouts, every included theme, pointer and keyboard
help, the pointer-to-panel hover path, Escape, 200% zoom, checklist status
activation and representative title/acronym casing. The complete suite was
separately reported by the implementer as **278 passed** with one known
third-party deprecation warning.

The help implementation uses a `document.body` portal with fixed positioning
and `z-index: 2147483647`; the browser checks prove panels open to the right of
each desktop help control, remain reachable across the pointer gap, stay in the
viewport at 200% zoom and close on Escape. Checklist statuses are real buttons
with `aria-controls`; activation opens sibling detail where present, focuses
the row's exact next step and scrolls it into view. The build stamp is correctly
derived from package metadata and appears below the Safe Preview Build box.

### Resolved — faint build-stamp contrast

The initial refinement review found that the 9 px build stamp at 52% opacity
provided only **3.66:1** contrast on the default rail and about **3.19:1** on
Gruvbox Light. The stamp remains visibly subdued but now uses 78% opacity
(`web/src/styles.css:267-273`). Its browser test composites the translucent
foreground over the actual rail color for every one of the 18 included themes
and requires at least 4.5:1 (`tests/test_m4_browser.py:144-185`).

### Resolved — notice-card title case

The initial refinement review found that notice-card titles bypassed the new
title policy. They now use the same acronym- and product-aware `titleCase`
helper as the other dynamic headings (`web/src/App.tsx:1164-1168`). The browser
suite asserts the rendered simulator heading **Example Notice Requiring
Review** before moving through the remaining representative acronym cases
(`tests/test_m4_browser.py:188-214`).

The two targeted re-review tests passed independently:

```text
2 passed in 2.35s
```

### Refinement conclusion

Both medium findings are resolved. No critical, high or medium interface issue
remains. Pointer placement, z-order, hover/focus and zoom behavior, checklist
navigation, subdued accessible build metadata, responsive/theme coverage and
the representative title/acronym forms pass independent re-review.

## M5 interface correction re-review — 2026-10-29

The latest interaction corrections pass independent review. The focused
Safety Checklist, help-panel and title/Settings browser checks passed:

```text
4 passed in 47.77s
```

Help positioning is now owned by the information button. Entering the portaled
panel only cancels its close timer, so the panel does not chase the pointer.
The Review Updates wide panel renders without internal scrolling at the desktop
test size, remains fixed while the pointer crosses into it and stays contained
at 200% zoom. An additional independent 390 x 844 check confirmed that the
same panel stays inside the mobile viewport and that its full content remains
reachable by scrolling at normal and 200% zoom.

Safety Checklist status semantics now match their destinations. Passed, Not
Checked and Not Supported render as non-interactive spans. The two simulated
Needs Attention cases render as buttons only because each has a real in-app
destination: firmware changes to Overview and focuses **Check software**;
system-owned global npm packages focus the native update-selection checkbox.
The desktop and 390 px browser cases prove both focus destinations and assert
that the informational status classes contain no status button.

The Settings Appearance section now contains only its explanation and theme
selector; the redundant Ultraviolet preview and its copy are absent. The
design and content rules record the stable-panel and destination-only status
patterns.

No critical, high or medium finding remains from this correction re-review.
