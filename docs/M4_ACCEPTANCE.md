# M4 acceptance

**Prepared:** 2026-10-27  
**Revised:** 2026-10-29  
**Status:** accepted by the user on 2026-10-29; M5 authorized

M4 makes higher-risk update sources understandable before they can change the
computer. It adds detection, safety results, practice plans limited to known
actions and plain-language follow-up states. It does not enable live firmware, startup,
toolchain, portable-app or cleanup work.

## Delivered

- Firmware-data handling that keeps restart, full shutdown, reconnect
  and separate activation distinct and blocks unmet power requirements.
- One startup-safety view for kernel files, driver builds, dracut and the boot
  loader while preserving the complete system update group.
- Portable-app rules requiring a regular file that is not a link to another
  file, is not owned by a system package and includes supported built-in update
  information. Updatarr must download and check the new copy beside the current
  file, replace the current file in one completed step and keep a recovery copy.
- Read-only checks for Cargo-installed tools, fnm Node.js versions, global npm
  packages, uv tools and portable apps in approved folders.
- Tool ownership rules that block npm folders reserved for system packages
  until the owning package is known, mark unknown Cargo folders and sources and
  an unknown uv installation method as Not supported, and keep installing an
  fnm version separate from making it the default.
- Maintenance previews with the exact file list, size of each file and rule for
  how many newer versions to keep. They clearly state that nothing was removed
  and provide no cleanup action.
- Practice-plan actions for firmware, portable apps, rustup and fnm. They can
  describe only the named action and provide no place for a command, program
  path, environment setting or extra command option.
- An issue-first Safety checklist that Updatarr completes automatically, with
  visible passed, needs-attention, not-checked and not-supported counts; blockers
  and next steps stay visible while extra detail remains expandable.
- Small, raised circled information controls on every page. All explanations
  appear in anchored panels on pointer hover or keyboard focus without
  requiring a click; longer guidance uses a wider, scrollable panel.
- A complete plain-language pass across page text, help, plan messages,
  firmware/startup details, portable apps, developer tools, maintenance and
  server-provided errors.

## Safety result

Live mode reports these M4 capabilities as **Not checked** until their exact
read-only evidence has been collected. Unsupported and ownership-conflicting
cases have no update control. The restricted system tool was not given any new
permitted administrator action. No firmware-information refresh, package
update, tool update, portable-file
replacement, deletion, online-source change, service change or other change to
the computer was performed.

The signed-in safety result records that system-package ownership,
disabled Flatpak sources and the computer remain unchanged. First real uses
still require the separate approvals in [MILESTONES.md](../MILESTONES.md).

## Verification

The complete Python suite passed **247 tests in 163.35 seconds** with one known
third-party deprecation warning. The M4 browser suite separately passed all
five checklist, help, plain-language, desktop, mobile and 18-theme checks.
TypeScript checking, the Vite production build and Python compilation also
passed.

The refreshed [desktop](design/screenshots/m4-safety-ultraviolet-desktop.png)
and [mobile](design/screenshots/m4-safety-norse-mobile.png) evidence shows the
final safety checks, exact maintenance file list and responsive layouts.
Independent re-review found no remaining critical, high or medium findings.
The complete requirement, host-observation and review record is in the
[M4 validation note](research/m4-validation.md).

## Still separately gated

- Install or give more abilities to the restricted system tool.
- Run any live firmware or startup-related update.
- Run any live rustup, Cargo, fnm, npm or uv change.
- Replace any AppImage or remove its recovery copy.
- Delete package caches, unused data or any other file shown in a maintenance
  preview.
- Install/enable services or autostart and perform the later Octopi migration.

## Acceptance gate

- [x] User accepts M4 and authorizes the next milestone.
