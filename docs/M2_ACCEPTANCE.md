# M2 acceptance

**Prepared:** 2026-10-26  
**Status:** accepted by the user on 2026-10-26

M2 adds catalog search, source information, saved update choices and clearly
separated earlier activity to the loopback-only Updatarr application. It does
not install, remove or update software.

## Delivered

- Source-qualified Arch, AUR and simulated Flatpak search with explicit source
  and installation-place choices. Live Flatpak search remains **Not checked**
  because the installed command may refresh catalog data.
- Every installed-software row and every catalog result links to readable source
  documentation in a new tab.
- Truthful incomplete, unavailable and invalid-response states; similarly named
  results never merge across sources, remotes or installation places.
- Bounded plain-text official notices with source, time, parse state and content
  hash, plus an inert AUR build-file preview that says when no earlier copy is
  available for comparison.
- Durable postpone, skip-this-version, pause and turned-off-source choices with
  expiry, reason, last use and append-only decision events.
- Central rejection of partial Arch/EndeavourOS system-package selections and
  of a native update group that still has an active saved exclusion.
- Idempotent pacman and Flatpak history import, labeled as incomplete outside
  activity. Append-only import batches explain coverage, and a persisted source
  generation distinguishes log replacement and copy-truncate rotation.
- Read-only detection of existing Flatpak disabled sources and update blocks.
- Responsive desktop/mobile flows and all 18 appearance profiles, with theme
  selection kept under **Settings → Appearance**.
- A generated metallic-white update-loop logo is centered in the Ultraviolet
  tile, and the Overview process labels have balanced connector spacing.
- The Updates page now explains its purpose in plain language: postponing waits
  24 hours, skipping applies only to the shown version, and pausing lasts until
  resumed. An active choice can be removed from the same row to restore the
  update source's reported status.

## Safety result

M2 exposes no install or arbitrary-command route. The browser, web service and
tray remain unprivileged. Live verification used fixed HTTPS reads, the closed
trusted read-only probe registry, disposable databases and project-local state.
It did not refresh package metadata, change a Flatpak remote or update block,
edit pacman settings, install software, alter a service or change autostart.

## Verification

- TypeScript check, Vite production build, lockfile check and Python compilation:
  passed.
- Complete Python/backend/API/browser suite: **197 passed in 80.93 seconds**.
- Target-scale tests cover 10,000 catalog records and 10,000 saved-choice
  comparisons.
- Live disposable import: **15,379** events in **0.093 seconds**; unchanged
  repeat added **0** in **0.068 seconds**.
- Independent review findings were repaired. Final re-review found **no
  critical, high or medium findings**.
- One non-failing third-party Starlette TestClient/httpx deprecation warning is
  recorded for later dependency maintenance.

Detailed evidence and screenshots are in the
[M2 validation note](research/m2-validation.md).

## Still outside M2

M3 installation plans, privileged execution, local confirmation, Polkit,
live software changes and first update-source mutation trials remain blocked.
Services, autostart and Octopi migration remain later separately approved work.

## Acceptance gate

- [x] User accepted M2 and authorized M3 work on 2026-10-26.
