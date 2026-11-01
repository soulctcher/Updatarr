# Updatarr agent workflow

Read [PLAN.md](PLAN.md) and [MILESTONES.md](MILESTONES.md) before changing the
project. Work only inside the currently authorized milestone; documentation is
not authorization for host mutation.

## Route by task

- **Domain/update-source/planning work:** read [GLOSSARY.md](GLOSSARY.md),
  [DATA_MODEL.md](DATA_MODEL.md), [ARCHITECTURE.md](ARCHITECTURE.md), and
  [CAPABILITY_MATRIX.md](CAPABILITY_MATRIX.md).
- **Web/API/auth work:** also read [SECURITY.md](SECURITY.md) and the
  [architecture-security research](docs/research/architecture-security-research.md).
- **Interface/design work:** read the
  [visual direction](docs/design/VISUAL_DIRECTION.md) and
  [theme contract](docs/design/THEMES.md) plus the
  [interface language rules](docs/design/CONTENT_STYLE.md); test changed flows
  at the documented responsive boundaries and every shipped profile when shared
  tokens change.
- **Privileged or transaction work:** read every accepted/proposed ADR in
  [docs/adr](docs/adr), [SECURITY.md](SECURITY.md), and
  [TEST_PLAN.md](TEST_PLAN.md); stop at the applicable approval gate.
- **Packaging, services, migration or recovery:** read
  [OPERATIONS.md](OPERATIONS.md) before acting.

## Invariants

- Preserve the native full-upgrade group.
- Keep the web service, browser and tray unprivileged.
- Pass typed identities and immutable plans across seams; privileged execution
  accepts no arbitrary command surface.
- Require managed-host local confirmation before every executable software
  mutation; require Polkit separately when root privilege is needed.
- Preserve ownership, disabled origins and update-source trust settings.
- Keep up to date, turned off, needs refresh, blocked, error, not supported and
  not checked as distinct states.
- Use simulators and fixtures before live update sources, and obtain the
  explicit approval named in MILESTONES.md before any live mutation.

## Completion

A task is complete only when its requirement and risks map to tests, the tests
and static checks actually run, changed behavior is documented, and an
independent reviewer has resolved significant findings. Record exact evidence;
never infer success from process health alone.
