# M1 acceptance packet

**Prepared:** 2026-10-24  
**Status:** accepted by the user on 2026-10-24; M2 work authorized within its
documented scope and gate

## Delivered

- Typed update-source-qualified software identity, truthful source states,
  future policy states and terminal update-run states.
- Explicit SQLite WAL repository with atomic initialization, immutable
  snapshots, bounded event history, append-only audit rows, owner-only default
  state/backup files, preferences, Argon2id credentials and hashed durable
  session identifiers.
- Closed-command live read-only inventory for native/foreign packages, Flatpak
  user/system scopes, firmware and Rust toolchains. Foreign packages are not
  mislabeled as AUR packages.
- One deduplicated inventory coordinator. Cancellation waits for synchronous
  provider work to stop before another check can begin.
- Versioned authenticated loopback API with CSRF, Host/Origin validation,
  bounded requests and a persistent SSE channel with replay and keepalive.
- Responsive five-view Ultraviolet interface, 18 themes under Settings to
  Appearance, persistent theme selection and an optional unprivileged Qt tray
  prototype.

## Safety result

M1 cannot install or update software. The live validation did not refresh
metadata and recorded update availability as **Not checked**. It matched direct
installed-state counts for 1,743 native packages, 22 user Flatpaks, 1 system
Flatpak, 29 firmware records and 1 Rust toolchain. Octopi, services, autostart,
package databases, origins and host configuration were unchanged.

## Verification commands

```bash
uv sync --extra test
npm --prefix web run check
npm --prefix web run build
.venv/bin/python -m compileall -q src tests scripts
.venv/bin/python -m pytest -q
```

Final local results on Python 3.14.8 and Node.js 24.22.1:

- `uv lock --check` and `uv sync --extra test` — passed; 31 locked packages;
- TypeScript check — passed;
- Vite production build — passed;
- Python compilation — passed;
- complete test suite — **151 passed, 0 failed, 0 skipped in 65.75 seconds**;
- focused M1 suite — **27 passed, 0 failed, 0 skipped in 4.56 seconds**;
- relative Markdown links — **0 missing targets**.

Additional evidence:

- focused M1 domain/storage/provider/coordinator/API/tray suite;
- direct read-only source-count comparison and 10,000-row timing observation;
- all five views at 1440, 681, 680, 390 and 320 CSS pixels;
- all 18 themes across all five views, theme contrast checks, system light/dark,
  keyboard selection, reduced motion, 200% zoom and retired-theme fallback;
- four reviewed desktop/mobile screenshots;
- relative Markdown link audit.

## Independent review

The first full M1 review found no critical or high issues and eight medium
issues. The implementation now has targeted regressions for every finding:

1. opposite Flatpak scopes are rejected;
2. state backups and app-created directories are owner-only;
3. SSE remains open and delivers events published after connection;
4. cancellation cannot overlap another provider check;
5. truncated output fails closed;
6. stored snapshot children cannot be rewritten;
7. the complete production theme contract is exercised;
8. this packet records exact evidence and known limits.

Final independent re-review result: **PASS**. No critical, high or medium
findings remain. The reviewer independently confirmed the 27-test focused M1
suite, 151-test complete suite, dependency lock, TypeScript check, production
build, Python compilation and zero broken relative documentation links.

## Known limits owned by later milestones

- Update availability, search, policy editing and imported package history are
  M2 work. M1 live adapters inventory installed state only.
- Software planning, confirmation on this computer, privileged execution and
  all live mutations remain M3 or later gated work.
- Account bootstrap, supported service installation and Octopi migration remain
  packaging/deployment work. The development password is not a supported
  deployment configuration.

## Acceptance

- [x] User accepts M1 and authorizes the next milestone.

The user's acceptance authorizes only M2 work. M3 installation work, live
software changes, system dependency installation, service or autostart changes,
and Octopi migration retain their separate approval gates.
