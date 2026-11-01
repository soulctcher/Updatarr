# M6 hardening and release validation

**Validation date:** 2026-10-30  
**Status:** technical gate complete; accepted by the user on 2026-10-30  
**Host changes:** none; project-local dependencies, disposable databases,
simulators, browser processes, source/package staging roots and read-only audits
only

## Requirement and risk map

| M6 area | Result | Primary evidence |
| --- | --- | --- |
| Interrupted runs | Fresh read-only provider observations run outside the database write transaction; only a complete expected-version match succeeds; missing, mismatched or failed checks require manual recovery; no plan replays | production startup integration, mismatch/unavailable and callback-write tests |
| Database recovery | Schema versions 1–6 migrate in one explicit transaction; a forced late failure leaves no new object/version, and a future schema is rejected unchanged | schema interruption, future-version and backup/restore tests |
| Native locks | No lock, alternative owner, current-process owner and owner not visible are distinct; every present lock blocks and is never removed | fake `/proc` owner and owner-unknown fixtures |
| Hostile/unavailable input | Provider, catalog, advisory and AUR preview text removes terminal and Unicode format controls; malformed/truncated data and AUR timeout fail closed | parser/catalog/provider hardening tests |
| Large inventory | Schema 6 performs indexed server-side paging; Software shows the complete range/count and Previous/Next controls without applying an unsubmitted search | 1,002-row storage test and 205-row browser flow |
| Browser closure | API version mismatch stops sign-in; high-density/400% reflow, 200% zoom, reduced motion, keyboard, names/labels, themes and responsive boundaries pass | real Chromium suite |
| Security | Browser/network, session, immutable plan, local confirmation, privilege, ownership, export and deployment boundaries pass; both locked dependency audits are clear | security review and focused negative suite |
| Operator/release | Upgrade/recovery runbook, known limitations, 22-scenario matrix and clean evaluation archive/package are present | documentation and archive/package inspection |

## Performance gate

The repeatable command is
`scripts/profile_m6_performance.py --records N --repetitions 9 --enforce`.
Both profiles passed the enforced storage, sorted first-page, populated filter
and database-size budgets:

| Records | Store | First page median/max | Populated filter median/max | Database |
| ---: | ---: | ---: | ---: | ---: |
| 2,000 | 12.316 ms | 1.042 / 1.445 ms | 1.509 / 1.537 ms | 1,363,968 bytes |
| 10,000 | 63.407 ms | 1.288 / 1.334 ms | 2.882 / 3.061 ms | 5,984,256 bytes |

The browser requests 100 rows at a time and reports the complete total. The
205-row Chromium test exercises Next, Previous, an unsubmitted search and the
subsequently applied five-result search.

## Security and dependency evidence

- `npm --prefix web audit --omit=dev --audit-level=moderate` — **0 known
  vulnerabilities**.
- `uv audit` — **no known vulnerabilities or adverse project statuses in 35
  packages**. The command identifies itself as experimental.
- The independent reviewer initially found recovery wiring/transaction,
  migration atomicity, Unicode coverage, archive hygiene/documentation and
  scale/paging gaps. Every significant and low finding was repaired and
  re-reviewed.

## Artifact evidence

- Deterministic source archive:
  `packaging/arch/updatarr-0.6.0.tar.gz`
- Source SHA-256 recorded in the PKGBUILD:
  `a9f429f9c219c54562a3f5f900bef16287c1cf98a70bb23b2964f81c2f2116b8`
- Final disposable package:
  `/tmp/updatarr-m6-final.I3Fnil/updatarr-0.6.0-1-any.pkg.tar.zst`
- Package SHA-256:
  `fdf011331b89a4b12f6827cf9c430716f44d490a4e6316214e7a107b0c9dfd09`
- Package inventory: **232 entries**; includes the read-only probe module,
  browser build, both user units, full linked operator documentation and the
  development-only license notice.
- All four launchers use `#!/usr/bin/python`; packaged bytecode exposes no home
  or temporary build path.
- Extracted package imports API version 1 and all 33 read-only probes through
  the project test environment. Its extracted static application returns
  `200 {"status": "ok"}` from `/healthz`.

The package was built in a disposable directory with dependency checks skipped
because the host does not have the declared `python-build` make dependency.
The build instead used the locked project-local package tools. This validates
the package content, not a clean-chroot release build. No package was installed
on the host.

## Final commands

- `npm --prefix web run check` — passed.
- `npm --prefix web run build` — passed.
- `uv lock --check` — passed.
- `.venv/bin/python -m compileall -q src scripts` — passed.
- `.venv/bin/python -m pytest -q` — **300 passed in 176.72 seconds**.

The sole test warning is the known third-party Starlette TestClient/httpx
deprecation notice. No test was skipped or failed.

## Release disposition

The user accepted the technical M6 gate on 2026-10-30. No release tag was
created because this workspace is not a Git checkout and publication remains
blocked by the missing redistribution license and release
signing/generated-asset provenance decisions. Live AUR execution and every
first live mutation remain separately blocked or approval-gated as listed in
[Known limitations](../KNOWN_LIMITATIONS.md).
