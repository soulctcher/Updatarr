# M3 reviewed update planning and simulation validation

**Date:** 2026-10-27  
**Scope:** project-local code, simulator, disposable SQLite state and browser UI  
**Host changes:** none

## Delivered evidence

| Risk or requirement | Implemented evidence |
| --- | --- |
| Reviewed content cannot change | Canonical plan content has a SHA-256 fingerprint and trigger-protected immutable storage; lifecycle state and append-only events are separate. |
| Arch partial upgrades | Any selected native subset is rejected; a valid native plan contains one complete full-upgrade step. |
| Stale or replayed authority | Plans expire after 15 minutes, invalidate on inventory or saved-choice drift, follow constrained transitions and can be consumed once. |
| Browser cannot start mutation | Browser review stops at **Waiting for confirmation on this computer**. Local endpoints require loopback plus a separate local-agent credential. |
| Administrator separation | Root-required plans enter **Waiting for administrator permission** only after managed-computer confirmation. The repository simulates this state; no Polkit policy or helper was installed. |
| No arbitrary command seam | Plans and privileged envelopes contain typed operation and software identities only. Tests reject hostile identifiers, stale generations, caller mismatches, locks and unknown steps. |
| Honest cancellation and recovery | Simulator events distinguish safe cancellation from result checking. An unfinished run discovered after restart becomes **Needs manual recovery**. |
| AUR code risk | Live AUR execution is blocked in plan validation pending tested isolation and service-secret separation; there is no override. |
| Result truthfulness | Simulator success is recorded only after its result checker passes; failure becomes **Needs manual recovery**. |

## Verification commands

```text
npm --prefix web run check
npm --prefix web run build
.venv/bin/python -m compileall -q src tests
.venv/bin/pytest -q
```

The TypeScript check, Vite production build and Python compilation passed. The
final complete M3 run passed **221 tests in 88.22 seconds** with one non-failing
third-party Starlette TestClient/httpx deprecation warning.

Focused M3 backend/API/browser evidence passed before the complete run. Browser
coverage includes 1280-pixel desktop and 390-pixel mobile plan review, no
document overflow, exact fingerprint/expiry/permission text, and proof that no
browser confirmation action appears.

Independent review drove repairs for authoritative privileged checks, atomic
replay prevention, durable pre-execution state, expected-version result checks,
application cancellation, local human confirmation, exact plan/run pairing,
session binding, side-effect-free GET behavior, claim-time drift checks,
browser progress and Unicode canonicalization. The final targeted review found
**no remaining critical, high or medium findings**.

## Visual evidence

- [Desktop exact-plan review](../design/screenshots/m3/plan-review-desktop.png)
- [Mobile waiting-for-local-confirmation state](../design/screenshots/m3/local-confirmation-mobile.png)

## Deliberately not performed

- no package-manager metadata refresh;
- no pacman, AUR or Flatpak mutation;
- no privileged helper or Polkit policy installation;
- no service, autostart or linger change;
- no Octopi change.

Those actions retain the separate approvals listed in `MILESTONES.md`. Live AUR
work additionally remains blocked by the security decision in
[m3-aur-isolation.md](m3-aur-isolation.md).
