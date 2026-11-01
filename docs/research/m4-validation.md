# M4 validation

**Date:** 2026-10-29  
**Scope:** firmware, startup-related checks, portable apps, detected developer
tools and maintenance previews  
**Safe boundary:** practice data and read-only observations of this computer only

## Result

M4's review checks passed. Higher-risk update sources now have explicit,
plain-language safety states and practice actions limited to known fields. Live mode
does not claim these operations are ready and exposes no cleanup action. No
software, firmware, package ownership, Flatpak origin or host setting changed.

## Requirement and risk evidence

| Requirement or risk | Evidence |
| --- | --- |
| Firmware requirements must not collapse into one reboot flag | Tests cover restart, full shutdown, reconnect, activation and no follow-up; incomplete firmware data is refused. |
| Startup-related packages must stay in the complete system update group | M4 adds safety information without creating another update path; planning keeps the existing complete system update. Kernel files, driver builds, dracut and boot-loader checks remain separate facts. |
| Portable apps must not overwrite system-owned or unsafe paths | The safety check blocks a file owned by a system package or a file that links to another file, marks missing built-in update information Not supported and allows only a practice plan that cannot change the computer. |
| Tool sources must preserve ownership and selection | Read-only checks detect Cargo, fnm, npm and uv state without guessing ownership. Unknown Cargo sources and folders remain unresolved, an npm folder reserved for system packages is blocked until its owner is known, uv cannot update itself when Updatarr does not know how it was installed, and installing an fnm version does not change the default. |
| Maintenance preview must not imply deletion | The browser shows the exact simulated file names, sizes and rule for how many newer versions to keep, says “Nothing has been removed,” provides no cleanup control and creates no update run. |
| No place for an arbitrary command | M4 plan tests confirm that firmware, portable-app, rustup and fnm actions have no command or extra-option fields. The restricted system tool was not given any new permitted administrator action. |
| M4 preservation check | The signed-in safety result reports that package ownership, Flatpak sources and the computer remain unchanged; browser and direct application tests confirm all three. |
| Safety results must be quick to review | One issue-first checklist shows summary counts and orders needs-attention, not-checked and not-supported results before passed results. Blockers and next steps remain visible with details closed. |
| Instructional panels must not crowd the work | Every page has a small, raised and specifically named circled information control. Every help panel appears on hover or keyboard focus without a click; longer guidance uses a wider, scrollable panel. |
| All interface language must be familiar | A rendered-copy check covers every page, opens every help control, checks the spoken names used by screen readers, search results, an update plan, imported history, every expanded safety detail and sample error messages sent by Updatarr. It rejects internal and unnecessarily technical terms. |

## Automated verification

Environment: project virtual environment on Python 3.14, Chromium through
Playwright, TypeScript 7 and Vite 8 on the target EndeavourOS workstation.

```text
.venv/bin/pytest -q
247 passed, 1 warning in 163.35s

.venv/bin/python -m compileall -q src tests
passed

cd web && npm run check && npm run build
TypeScript check passed
Vite production build passed: 17 modules transformed
```

The one warning is the previously known third-party Starlette TestClient/httpx
deprecation. It does not indicate an application failure.

M4-specific browser evidence passed five tests: desktop at 1280×900, mobile at
390×844, no document overflow, checklist summary and ordering, visible blockers
and next steps, section spacing, hover/focus help panels, rendered plain language,
no cleanup control and all 18 included theme profiles. The complete suite also
reran all earlier milestone tests.

## Read-only host comparison

The limited safety check ran only existing read-only entries. Cargo and
uv reported no managed tools. fnm, npm, DKMS, the running kernel and installed
kernel-module tree returned results within the recorded limits. The npm folder and package output
were recorded without running an update check. One AppImage file
was observed under the existing user `bin` scan; update information and package
ownership remain unverified, so live replacement remains disabled.

`bootctl status` identified systemd-boot and Secure Boot but returned failure
because a check without administrator access could not read protected files on
the startup partition. The live
M4 response therefore remains **Not checked** rather than calling the boot
layout safe. The rollback prerequisite probe found `btrfs-progs` but not
snapper or Timeshift; an installed tool alone would not prove recoverability in
any case.

No probe refreshed update information, checked newer online versions, enabled a source,
installed software, rewrote a file or removed data.

## Visual review

- [Desktop, Ultraviolet light](../design/screenshots/m4-safety-ultraviolet-desktop.png)
- [Mobile, Norse](../design/screenshots/m4-safety-norse-mobile.png)

The desktop view keeps the issue-first checklist above detected updates with a
clear panel gap, summary counts and compact passed rows. The mobile view keeps
the same order in one column, retains the fixed navigation and keeps each next
step adjacent to its state. Both use the accepted token system; status meaning
is carried by symbols and text as well as color. Page instructions are now
available from circled information controls rather than permanent help panels.

## Known gaps and gates

- Live fwupd release discovery, refresh and execution remain separately gated.
- The protected startup partition prevents a complete safety check without
  administrator access on this host; a narrowly reviewed restricted-system-tool
  operation is still required before live
  startup-related work can be enabled.
- The observed AppImage has not passed ownership, embedded update-information,
  trust checks or checks for preparing the replacement file.
- Cargo has no stable generic update-all preview; unknown source/root entries
  remain disabled.
- No live toolchain update or maintenance cleanup was attempted.
- Packaging, service startup, tray integration and Octopi migration belong to
  M5 and remain unauthorized.

## Independent review

Independent re-review covered the complete current tree because this workspace
does not contain Git metadata. The reviewer reran the complete Python suite,
TypeScript check, Vite production build and Python compilation, and inspected
the desktop and mobile evidence. Earlier findings about firmware follow-up and
trust data, startup-check completeness, portable-app replacement safety, tool
ownership, the exact maintenance file list and live-readiness evidence were
resolved. No critical, high or medium findings remain.
