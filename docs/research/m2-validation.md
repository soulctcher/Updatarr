# M2 catalog, saved-choice and history validation

**Validation date:** 2026-10-26  
**Status:** technical gate complete; accepted by the user on 2026-10-26  
**Host changes:** none; fixed HTTPS reads, bounded local history reads,
simulators, project-local state and disposable databases only

## Requirement and risk map

| M2 area | Implemented behavior | Primary evidence |
| --- | --- | --- |
| Catalog | Arch, AUR and Flatpak results retain complete source identity; identical names never merge; cutoffs remain visible; AUR build files have an inert fixed-host preview | catalog domain/API/browser tests and simulator fixtures |
| Search truth | Live Arch/AUR use fixed bounded HTTPS sources; live Flatpak search says Not checked because its command may refresh AppStream data | primary-source research, live read and negative state test |
| Source information | Descriptions and Arch notices become bounded plain text; every installed and catalog item links to its source documentation using HTTPS | hostile-text, URL-boundary, domain, API and browser tests |
| Saved choices | Turn off, postpone for 24 hours, skip this version and pause until resumed persist with complete stable identity, reason, expiry, append-only events and last application; choices can be removed beside the affected update | same-ref/different-remote, storage, API, browser and restart tests |
| Native safety | A selected subset or a native group with an active exclusion is blocked centrally; no install or execution route exists | domain/API/browser negative tests |
| History | Pacman and Flatpak records import idempotently into separate append-only partial history; batches explain missing coverage; persisted source generations handle replacement and copy-truncate rotation | parser/storage/API/browser tests and live disposable import |
| Analytics | Counts derive from stored events; unknown download data remains unknown | storage/API/browser tests |
| Interface | Existing five-destination shell gains focused catalog, safety, source-setting and history flows without moving appearance out of Settings; the generated loop mark is centered, process-label spacing is balanced and update choices are explained in plain language | responsive browser, generated-asset and theme regression tests |

## Live read-only evidence

The target-host check used only fixed official HTTPS requests and the already
accepted trusted executable registry. It did not run `flatpak search`, refresh
pacman or Flatpak metadata, change a remote or mask, or modify software.

- Arch package search for `kdenlive`: **1** bounded result.
- AUR RPC v5 search for `kdenlive`: **4** bounded results.
- Flatpak live search: **Not checked**, with the metadata-refresh reason.
- Official Arch news feed: **2** bounded notices requested and parsed.
- Existing Flatpak settings: **21** disabled user remotes, **0** system disabled
  remotes and **0** masks, read without changing them.
- Pacman log: **15,351** recognized external package actions.
- Flatpak user/system journal history: **28** recognized deploy/remove actions.
- Disposable SQLite import with persisted source generation: **15,379** added
  in **0.093 seconds**; unchanged repeat added **0** in **0.068 seconds**. The
  repeated read retained generation **1** for the same open log file.

Current state remained authoritative; the imported records were not used to
claim installed versions or successful Updatarr update runs.

## Visual evidence

- [Catalog choices, Ultraviolet desktop](../design/screenshots/m2-catalog-ultraviolet-desktop.png)
- [Imported history, Norse desktop](../design/screenshots/m2-history-norse-desktop.png)
- [Blocked system-package subset, Norse mobile](../design/screenshots/m2-native-block-norse-mobile.png)
- [Revised logo and Overview spacing, Ultraviolet desktop](../design/screenshots/m2-revision-overview-ultraviolet-desktop.png)
- [Installed software source links, Ultraviolet desktop](../design/screenshots/m2-revision-software-links-ultraviolet-desktop.png)
- [Plain-language update choices, Ultraviolet desktop](../design/screenshots/m2-revision-updates-ultraviolet-desktop.png)
- [Correctly inset detected-update header, Ultraviolet desktop](../design/screenshots/m2-revision3-updates-header-corrected.png)
- [Centered enlarged logo in Settings, Ultraviolet desktop](../design/screenshots/m2-revision2-settings-logo-desktop.png)

## Verification record

The first independent review identified gaps in complete identity, catalog
cutoff reporting, imported-history coverage and rotation, existing Flatpak
settings, native saved-choice safety, AUR preview coverage and notice integrity.
All significant findings were repaired and assigned focused negative tests.
The final independent re-review found no critical, high or medium findings.

Final verification on 2026-10-26:

- `npm --prefix web run check` — passed.
- `npm --prefix web run build` — passed.
- `uv lock --check` — passed.
- `.venv/bin/python -m compileall -q src scripts` — passed.
- `.venv/bin/python -m pytest -q` — **197 passed** in **80.93 seconds**.

The sole warning is a third-party Starlette TestClient/httpx deprecation notice;
it does not skip or fail a test. M2 is ready for user acceptance.
