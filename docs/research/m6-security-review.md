# M6 security review

**Review date:** 2026-10-30  
**Scope:** Updatarr 0.6.0 M6 repository, web/API boundary, typed planning and
execution seams, provider parsing, persistence, packaging and recovery  
**Host mutation:** none

## Method

The review traced the threats in [SECURITY.md](../../SECURITY.md) to executable
negative tests and inspected the browser-to-service, service-to-provider and
service-to-future-helper seams. It also ran the locked JavaScript and Python
dependency audits, static checks and focused security suite. Live package,
service, notifier and software changes were outside the authorized scope.

## Control review

| Area | Result | Evidence |
| --- | --- | --- |
| Network boundary | Pass | Loopback default; exact Host and Origin checks; CSRF; bounded bodies; non-loopback HTTPS/auth requirements; wildcard bind rejection; untrusted forwarding-header rejection |
| Sessions and credentials | Pass | Argon2id verifier; server-side hashed session IDs; rotation, expiry, revocation, password-change invalidation and login throttling tests |
| Browser content | Pass | Restrictive CSP; React text rendering; bounded plain-text notes; fixed safe documentation links; HTML/script and terminal-control fixtures |
| Hostile Unicode | Pass after M6 hardening | Provider text now removes Unicode format controls, including bidirectional overrides and zero-width characters, in addition to terminal controls and length bounds |
| Plans and replay | Pass | Immutable content-addressed plans; 15-minute expiry; snapshot/policy drift checks; atomic single claim; browser cannot provide a command or stand in for managed-host confirmation |
| Privileged seam | Pass for the disabled prototype | Closed operation enum; fixed arguments; exact caller/session binding; no executable, path, environment, argv or shell surface; live helper remains uninstalled |
| Native transaction locks | Pass after M6 hardening | No lock, alternative live owner, current-process owner and owner-not-visible are distinct observations; every present lock blocks; no code removes it |
| Interrupted results | Pass after M6 hardening | Positive expected-version evidence is required for recovered success; false, missing or failed checks become Needs Manual Recovery; reconciliation never replays the plan |
| Provider failure isolation | Pass | Missing tools, timeouts, unavailable sources, truncated output and malformed data do not become Up to Date or empty success |
| Ownership/trust | Pass | Native full-upgrade group; unresolved foreign packages remain unresolved; disabled Flatpak origins preserved; npm/system, uv and AppImage ownership conflicts block |
| Persistence | Pass | Owner-only state, WAL, transactional migrations, append-only audit/plan-step events, rollback on interruption and disposable backup restore |
| Deployment/package | Pass as evaluation artifact | Unprivileged service/tray, one startup owner each, no automatic enablement, checksummed source archive and staged install/remove tests |

## Dependency audit

- `npm --prefix web audit --omit=dev --audit-level=moderate` reported **0
  vulnerabilities** in the production browser dependency tree.
- `uv audit` reported **no known vulnerabilities and no adverse project
  statuses** across 35 resolved packages. `uv audit` identifies itself as an
  experimental command; this result is supporting evidence, not a guarantee.
- Dependency versions remain locked in `web/package-lock.json` and `uv.lock`.

## Findings and disposition

No critical, high or medium implementation finding remains from this review.
The following are explicit release blockers or residual limits rather than
hidden security claims:

- no redistribution license or authenticated release/tag/signing provenance;
- live AUR execution blocked until build isolation protects service secrets and
  unrelated user data;
- every first live mutation path and helper installation still separately
  approval-gated;
- direct Internet exposure and unattended remote execution unsupported;
- a Caddy deployment requires the documented live header/TLS/session/event
  verification before remote access is enabled;
- no claim that a dependency audit proves the absence of unknown defects.

The complete list is in [Known limitations](../KNOWN_LIMITATIONS.md). The final
independent end-to-end re-review resolved its initial findings and reported no
remaining critical, high, medium or low finding.
