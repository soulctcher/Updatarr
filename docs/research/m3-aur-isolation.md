# M3 AUR build-isolation decision

**Date:** 2026-10-26  
**Result:** live AUR build and installation remains blocked

## Why this is blocked

An AUR build file is executable community-provided code. Running it as the
Updatarr service user would allow it to read that account's files, including
application state, sessions and service credentials. Running it as root would
be substantially worse. A reviewed text diff reduces surprise but does not
create process isolation.

The current repository has no tested boundary that proves all of the following:

- builds run as a dedicated unprivileged identity rather than root or the
  Updatarr service account;
- the build cannot read Updatarr state, web sessions, credentials or approval
  material;
- source and package output paths cannot escape a disposable staging area;
- network, D-Bus, home-directory and process visibility have an explicit,
  tested policy;
- only reviewed output artifacts cross into a separately authorized install
  step;
- split packages, VCS sources, signing keys and interactive failures remain
  usable without weakening the boundary.

## M3 behavior

The planner may show an exact AUR build step so the limitation is visible, but
it marks the step disabled and adds a blocking explanation. Validation refuses
the plan before local confirmation, administrator permission or process start.
There is no override or “run anyway” action.

Native repository and Flatpak simulator paths remain testable independently.
Enabling live AUR work requires a later accepted isolation design, adversarial
escape tests and a separate first-live-trial approval.

