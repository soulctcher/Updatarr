# Updatarr Overview prototype

> Throwaway Phase 0 prototype. This is not production application code.

**Question:** Which information hierarchy should anchor Updatarr's responsive
Overview page?

Three structurally different variants share the same mocked read-only FastAPI
snapshot and SSE progress stream:

- `A` — Update progress: readiness and blockers lead.
- `B` — Update sources: source status and grouping lead.
- `C` — Review updates: the update list and plan details lead.

## Run

The prototype uses only packages already installed on the target host:

```bash
python prototypes/overview/app.py
```

Open <http://127.0.0.1:8787/?variant=A>. Use the floating arrows or keyboard
Left/Right to switch variants. The server binds only to loopback and exposes no
mutating operation.

Use the bottom **Preview theme** review control or append a documented theme ID,
for example `?variant=C&theme=amoled`. This control belongs only to the
throwaway prototype; the production theme setting belongs under Settings →
Appearance. The prototype keeps theme selection in the URL and does not persist
it.

Run its disposable HTTP, SSE, security-header and responsive browser checks
with:

```bash
python -m pytest -q tests/test_overview_prototype.py
```

## Scope

This prototype validates the Ultraviolet visual direction, responsive shell,
same-origin FastAPI delivery, a versioned mock JSON shape, basic SSE transport
and three information hierarchies. It intentionally does not validate SSE
resume/reset semantics, React/Vite, authentication, persistence, real update sources
or privileged execution.
