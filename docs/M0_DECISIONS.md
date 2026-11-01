# M0 decision and sign-off packet

**Prepared:** 2026-10-24  
**Status:** accepted by the user on 2026-10-24; M1 work authorized within its
documented scope and gate

## Decisions ready for acceptance

- The product name is **Updatarr**.
- The interface follows the familiar information structure of Sonarr and
  Radarr while using its own controlled-change workflow and iconography.
- **Ultraviolet** is the permanent brand direction. Status meaning never relies
  on violet alone.
- The web interface is canonical and is served by the Updatarr service.
- FastAPI + React/TypeScript/Vite + reconnectable server-sent events is the
  accepted application stack.
- Theme selection belongs under **Settings → Appearance**, never in the top
  bar. System, Light, Dark, AMOLED, Solarized, GitHub, Norse and the other
  documented profiles ship from one semantic token contract.
- Visible language uses ordinary update terminology; implementation terms are
  confined to technical details and developer documentation.
- Native repository packages form one full-upgrade group.
- Every executable software change requires confirmation on the managed
  computer. Root-required work then requires separate Polkit authorization.
- The web service, browser and tray stay unprivileged. A later privileged
  executor accepts only typed, fixed operations from an unchangeable,
  short-lived plan.
- Default networking is loopback-only. Non-loopback use requires deliberately
  configured authentication and HTTPS.

## Evidence complete

- Product, domain, architecture, security, operations, test and capability
  documents are present.
- Official-source *arr visual and application research is recorded.
- The target-host read-only capability probe passed independent review.
- The throwaway shell exercised the chosen visual direction and theme catalog.
- The production-stack slice exercises authentication boundaries, reconnectable
  progress, a non-root URL base, responsive layouts and all theme choices while
  remaining unable to mutate software.

## Explicitly not authorized by M0 sign-off

Signing off M0 does not authorize dependency installation outside this
workspace, package-manager changes, Flatpak changes, firmware work, services,
autostart, a privileged helper, firewall changes, Octopi migration, or any live
software update. Each later approval in `MILESTONES.md` remains separate.

## Final verification

- `npm --prefix web run check` — passed.
- `npm --prefix web run build` — passed with Vite 8.3.5.
- `python -m compileall -q src tests` — passed.
- `python -m pytest -q tests/test_m0_modules.py tests/test_m0_web_slice.py` —
  16 passed.
- `python -m pytest -q` — 119 passed.
- Independent review — passed after bounded-request and accessibility findings
  were fixed; no critical, high or medium findings remain.
- Independent responsive audit — 18 themes × 4 views × 5 widths, 360
  combinations, with no document-level horizontal overflow.

## Sign-off

- [x] User accepts the M0 decisions and authorizes work to begin within the M1
      scope and gate.

The user provided that explicit acceptance on 2026-10-24. No later-milestone or
host-mutation approval is implied.
