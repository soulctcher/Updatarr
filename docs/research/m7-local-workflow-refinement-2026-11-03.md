# M7 Local Workflow Refinement

**Date:** 2026-11-03  
**Status:** versioned `0.6.1 / M7.1` candidate and automated validation pass;
package build, signing and local replacement authorized

## User Findings

Local testing found that the Updates page exposed too much safety and planning
detail before the user knew what to do, that AUR plans were blocked by an
unconditional rule, and that an expired plan could touch the following safety
section.

## Implemented Direction

- **Ready Updates** now leads with a concise list, last-check time, **Check
  Again**, direct per-item wait/skip/pause choices and **Update Ready
  Software**.
- Clicking an update notification or the tray while updates need attention now
  opens the canonical web interface at **Ready Updates**; authentication still
  occurs first when the session has expired.
- Known problems appear in a small **Needs Attention** area. Instructions are
  gated per problem, and a button appears only when Updatarr has a real action
  or destination.
- The complete safety checklist, individual selection controls and detailed
  update table are under **Safety and technical details**.
- Starting the primary action prepares the exact typed plan for every item
  currently ready. Review, managed-computer confirmation and separate
  administrator permission remain intact.
- A shared 18 px workflow gap separates plan state, including **Plan Expired**,
  from following detail.
- The AUR planner now has a fail-closed readiness seam instead of permanently
  rejecting AUR in every mode. Deterministic simulator plans pass the seam;
  its production attestation provider is not implemented, so live mode remains
  closed until the production pipeline can provide current immutable evidence.

## AUR Boundary

The source-backed production design is recorded in
[AUR production pipeline research](aur-production-pipeline-research.md). The
current host lacks the official Arch `devtools` clean-build tools. No host
package was installed, no clean root was created and no live AUR build or
software update was run as part of this refinement.

## Required Evidence

- TypeScript check and production build.
- Planner regression proving default fail-closed behavior and simulator-only
  readiness.
- Browser checks at 1280x900 and 390x844 for the primary workflow and expanded
  detail.
- Existing full 18-theme safety-readiness profile check.
- Complete affected Python/browser suite and independent review before the
  installed package is replaced.

## Recorded Validation

- Complete Python/browser suite: **347 passed, 2 skipped in 209.66 seconds**.
  The skips are environment-conditioned integration cases. One Starlette
  `httpx` deprecation warning remains unchanged.
- TypeScript check and Vite production build: passed.
- Focused concise-workflow and real expired-plan spacing checks: passed at the
  documented desktop and mobile boundaries.
- The existing all-18-theme safety-readiness browser check: passed as part of
  the complete suite.
- Focused live-AUR API/default-planner contract after the complete run: **2
  passed**. It directly proves that live AUR is returned as an issue and is not
  included in the ready set.
