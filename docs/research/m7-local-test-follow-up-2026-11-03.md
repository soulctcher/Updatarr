# M7 Local-Test Follow-Up Evidence — 2026-11-03

## Scope and Safety Boundary

This project-local follow-up adds the requested Settings About information,
status-colored tray icon and tray notification preferences. It does not install
the new source archive, replace the installed RC2 package, enable a service,
change another notifier, contact an update source or perform a software update.

Tray preferences remain separate from the core service and update policy. The
owner-only JSON file controls status refresh timing, notification behavior,
optional reminder frequency and notification display time only.

## Requirement Evidence

| Requirement or Risk | Evidence |
| --- | --- |
| About is the final Settings section | Real Chromium desktop/mobile inspection and `test_settings_ends_with_version_contact_and_license_information` |
| Exact display copyright, email link and official license link | Browser role/link assertions and rebuilt production web bundle inspection |
| Muted red with recorded updates and muted green after a clear check | `TrayStatus.icon_state`, rendered-pixel tests and manual inspection of all three icon variants |
| No misleading green result before a check | Separate neutral-gray `not_checked` state and tooltip text |
| Tray Settings menu opens a real settings window | Offscreen Qt dialog control/save test and rendered dialog inspection |
| Notification frequency and behavior are customizable | Bounded no-repeat/hourly/four-hour/daily reminder choices, two behavior choices, Never, and timing tests |
| Preferences remain private and valid | Atomic owner-only file tests, bounded value validation and invalid-file recovery |
| A failed save does not partly apply | Persist-before-apply regression with a plain-language cause/effect/next-step error |
| No update authority is added to the tray | ADR 0010, operations guide and test-plan updates; no command channel or core API was added |

## Exact Checks Run

- `npm run build` in `web`: passed; TypeScript and Vite production build
  completed.
- `uv run pytest -q tests/test_m4_browser.py`: **9 passed** in 88.09 seconds.
- System runtime `pytest -q tests/test_m1_tray.py`: **9 passed** in 0.22
  seconds with PySide6, including real icon composition and the settings dialog.
- Final `uv run pytest -q`: **339 passed, 2 skipped** in 198.84 seconds. The
  two skips are the Qt-only tests in the isolated Python environment; both pass
  in the system runtime above. The one warning is the pre-existing FastAPI
  test-client deprecation.
- `git diff --check`: passed.
- Desktop 1280 × 1000 and mobile 390 × 844 Settings screenshots were inspected;
  the About grid reflows to one column without horizontal overflow.
- All shipped theme profiles remain covered by the M4 real-browser suite.

## Source Archive

The deterministic source archive was rebuilt after the changes:

```text
6f05f0e9068c49a9aa40ded310807869fefda2cd48659b88a789112f72149d24  packaging/arch/updatarr-0.6.0.tar.gz
```

The Arch recipe records the same digest. Direct archive inspection confirmed
that it contains `src/updatarr/tray_settings.py`, the rebuilt production web
bundle, the tray Settings action and the requested About strings.

## Independent Review

Independent specification and standards reviewers initially found missing
reminder cadence, overstated notification wording, incomplete GUI evidence and
partial-apply behavior on a failed preference write. All were corrected and
tested. Both re-reviews reported no remaining significant findings. The final
low-level documentation wording and packaged-loop test gaps were also fixed.

## Remaining Gate

This refreshed archive has not been turned into a new clean-build Arch package,
signed, installed or started on the managed computer. The currently installed
RC2 pilot and tray therefore do not contain these changes. A new package build
and a separate owner installation approval remain required before live desktop
testing of this follow-up.
