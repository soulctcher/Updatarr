# M3 acceptance

**Prepared:** 2026-10-27  
**Status:** accepted by the user on 2026-10-27

M3 adds exact reviewed update plans and a safe, inspectable simulator path. It
does not enable live installation. The browser can prepare and approve one
sealed plan, but it cannot replace confirmation on the managed computer or
administrator permission.

## Delivered

- Immutable, content-addressed plans tied to one inventory generation, active
  saved choices, exact operations, permission needs and a short expiry.
- One indivisible native system-package step and separate user/system Flatpak
  steps. AUR plans remain visibly blocked until isolation is proven.
- Plain-language plan review showing the fingerprint, expiry, exact software,
  permission level, blockers and current approval state.
- Distinct web review, interactive managed-computer confirmation and
  administrator permission states, with Unix identity/session evidence and a
  separately authenticated simulator seam.
- A typed privileged-boundary prototype that accepts no arbitrary command,
  executable path, environment or caller-provided argument list.
- Single-use simulator runs with safe cancellation points, result verification,
  append-only progress evidence and honest restart recovery.
- SQLite schema version 5 for immutable plans, plan events, runs and run steps.

## Safety result

The production entry point still has no live execution credential and cannot
invoke the local simulator execution endpoints. No privileged helper or Polkit
policy was installed. No package-manager command, metadata refresh, software
change, service change, autostart change or Octopi change was performed.

Live native and Flatpak trials still require their separate first-trial and
software-change approvals. Live AUR work has an additional unresolved security
blocker and no override.

## Verification

- TypeScript check, Vite production build and Python compilation: passed.
- Complete Python/backend/API/browser suite: **221 passed in 88.22 seconds**.
- Desktop and mobile screenshots inspected for exact-plan hierarchy, plain
  language, responsive layout and absence of a browser local-confirm action.
- Independent security review: no remaining critical, high or medium findings.

Detailed evidence is in the [M3 validation note](research/m3-validation.md),
with the lasting plan-sealing choice in [ADR 0009](adr/0009-content-addressed-single-use-update-plans.md)
and the AUR blocker in [the isolation note](research/m3-aur-isolation.md).

## Still separately gated

- Install or enable a privileged helper or Polkit policy.
- Run the first live native or Flatpak update trial.
- Make any package or Flatpak change.
- Design and prove AUR isolation before any live AUR build.
- Install/enable services or autostart and perform the later Octopi migration.

## Acceptance gate

- [x] User accepted M3 and authorized work within the M4 scope and gate on
  2026-10-27. Live firmware, boot-affecting, toolchain, AppImage replacement
  and cleanup trials remain separately gated.
