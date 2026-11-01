# M5 Arch packaging, systemd and Caddy research

Date checked: 2026-10-29

> The risk sections record the first review of the M5 draft. The implementation
> was revised afterward; the resolution record below states the current result.

## Resolution after review

- The PKGBUILD now consumes only `updatarr-0.5.0.tar.gz`, a deterministic
  source archive with a fixed SHA-256 checksum. It no longer uses `$startdir`
  or walks outside `$srcdir`. The archive declares the verified built frontend
  as an input; a published release still needs authenticated release provenance.
- `python-pydantic` is now a direct runtime dependency. The development-only
  license notice remains an explicit publication blocker rather than being
  presented as a release license.
- Reverse-proxy mode is now explicit, HTTPS-public-origin only and loopback
  bound. Uvicorn proxy interpretation stays off. Updatarr accepts forwarding
  headers only from the configured loopback proxy peer and ignores their
  values; every other peer is rejected. The Caddy example uses exact example
  subnets and no longer claims Caddy can suppress the fields it recreates.
- The user-unit namespace restrictions that could silently be unavailable were
  removed. The remaining unit hardening is not represented as a namespace
  sandbox. The operations guide now states the systemd 254 minimum and resolves
  the database through the actual XDG state path rather than assuming the
  default.
- The target does not have `devtools`, `namcap` or Caddy installed. M5 therefore
  proves a checksummed clean-source makepkg build in disposable directories,
  package-manager install/remove in a fakeroot, and application startup from
  the staged package. It does not claim a clean-chroot, namcap or live-Caddy
  result.

## Scope and method

This note checks the current M5 packaging and network-access documentation
against primary Arch Linux, systemd/XDG and Caddy sources. It is a research
record, not approval to install a package, enable a unit, expose a listener or
change the host. The inspected project material was:

- `packaging/arch/PKGBUILD` and the files installed from `packaging/`;
- `packaging/systemd/updatarr.service` and `updatarr-tray.service`;
- `pyproject.toml`, direct Python imports and the committed `web/dist` output;
- `docs/operations/ARCH_INSTALL.md`; and
- `docs/operations/NETWORK_ACCESS.md`.

## Verified facts

### Arch package and Python build

- Arch's Python packaging guidance uses `python-build` to produce a wheel and
  `python-installer` with `--destdir` to install it; distribution builds should
  use `python -m build --wheel --no-isolation`, with the selected build backend
  in `makedepends`. The current setuptools/PyPA build shape follows that model.
  [Arch Python package guidelines](https://wiki.archlinux.org/title/Python_package_guidelines)
- A PKGBUILD `source` entry must be local to the PKGBUILD directory or be a URL
  makepkg can fetch. Build and package functions run in `$srcdir`; `$startdir`
  is deprecated and strongly discouraged.
  [PKGBUILD(5): sources and packaging functions](https://man.archlinux.org/man/PKGBUILD.5)
- `makechrootpkg` runs from a directory containing a PKGBUILD and builds inside
  a clean chroot. Files reached by walking above that directory are not declared
  package sources and are not a clean-chroot input unless explicitly mounted.
  [makechrootpkg(1)](https://man.archlinux.org/man/makechrootpkg.1.en)
- Arch packaging guidance requires runtime dependencies used directly by the
  packaged program to be declared, even when another package currently brings
  one in transitively. License identifiers for official-style packaging should
  be SPDX expressions.
  [Arch package guidelines](https://wiki.archlinux.org/title/Arch_package_guidelines)

### systemd user units and XDG directories

- Distribution-provided user units belong in `/usr/lib/systemd/user`; local
  administrator units and overrides belong in `/etc/systemd/user`, and per-user
  configuration belongs below `$XDG_CONFIG_HOME/systemd/user`. The PKGBUILD's
  `/usr/lib/systemd/user` destination is correct for Arch.
  [systemd user unit search path](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html#User%20Unit%20Search%20Path)
- In a user unit, `RuntimeDirectory=`, `StateDirectory=` and `CacheDirectory=`
  create paths below `$XDG_RUNTIME_DIR`, `$XDG_STATE_HOME` and
  `$XDG_CACHE_HOME`. systemd exposes the resulting full paths as
  `$RUNTIME_DIRECTORY`, `$STATE_DIRECTORY` and `$CACHE_DIRECTORY`. Runtime
  directories are removed when the unit stops unless preservation is requested;
  state and cache directories remain.
  [systemd.exec directory table and lifecycle](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html#RuntimeDirectory=)
- `%t`, `%S` and `%C` are the corresponding user-manager roots. Therefore
  `StateDirectory=updatarr` with `%S/updatarr/updatarr.db`, and
  `CacheDirectory=updatarr` with `%C/updatarr`, are internally aligned on a
  current Arch system. `$XDG_STATE_HOME` defaults to `~/.local/state`, while
  `$XDG_CACHE_HOME` defaults to `~/.cache`; these are bases, not
  application-specific directories.
  [systemd specifiers](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html#Specifiers),
  [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir/latest/)
- The user-unit state base changed from `$XDG_CONFIG_HOME` to
  `$XDG_STATE_HOME` in systemd 254. Current Arch satisfies that assumption, but
  portability to older systemd requires a minimum-version statement or a test.
  [systemd issue and v254 milestone](https://github.com/systemd/systemd/issues/25739)
- Filesystem namespace restrictions such as `ProtectSystem=`, `ProtectHome=`,
  `ReadOnlyPaths=` and `ReadWritePaths=` are generally unavailable to ordinary
  user services unless used with `PrivateUsers=true`; that in turn depends on
  unprivileged user-namespace support. Unsupported sandboxing can be gracefully
  disabled, so the directive's presence alone is not evidence that it works.
  [systemd.exec sandboxing limitations](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html#Sandboxing)

### Caddy request headers and client matching

- `header_up -Field` deletes one upstream request header, and a suffix pattern
  such as `header_up -X-Forwarded-*` deletes all matching fields at that stage.
  However, Caddy's reverse proxy then automatically sets or augments
  `X-Forwarded-For`, sets `X-Forwarded-Proto`, and sets `X-Forwarded-Host`.
  [Caddy reverse-proxy header documentation](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy#headers)
- Current Caddy source applies configured upstream header operations before
  `addForwardedHeaders()`. Consequently, deleting those three fields with
  `header_up` does not prove that they are absent at Updatarr: Caddy recreates
  them afterward. Caddy does not automatically create the standardized
  `Forwarded` field, so deleting that field remains effective.
  [Caddy reverse-proxy implementation](https://github.com/caddyserver/caddy/blob/master/modules/caddyhttp/reverseproxy/reverseproxy.go),
  [Caddy issue 4375](https://github.com/caddyserver/caddy/issues/4375)
- `remote_ip` matches the immediate peer (or PROXY-protocol address). The
  `private_ranges` shortcut includes all RFC 1918 IPv4 space, loopback, IPv6
  ULA and IPv6 loopback. It is broader than a managed LAN/VPN subnet and does
  not mean "every VPN range."
  [Caddy `remote_ip` matcher](https://caddyserver.com/docs/caddyfile/matchers#remote-ip)
- When another proxy sits in front of Caddy, real-client matching uses
  `client_ip` together with exact trusted upstream-proxy ranges in the global
  `servers { trusted_proxies static ... }` option. Without trusted proxies,
  `client_ip` behaves like `remote_ip`; Caddy recommends
  `trusted_proxies_strict` for common append-style X-Forwarded-For chains.
  [Caddy `client_ip` matcher](https://caddyserver.com/docs/caddyfile/matchers#client-ip),
  [Caddy trusted proxies options](https://caddyserver.com/docs/caddyfile/options#trusted-proxies)

## Project alignment and concrete risks

### Must resolve before calling the Arch package release-ready

1. **The PKGBUILD is not a clean-chroot build.** It declares no sources, then
   builds and copies files from `$startdir/../..`. This contradicts the clean
   build instruction in `ARCH_INSTALL.md`, relies on a deprecated makepkg
   variable and leaves source integrity outside makepkg. The file already calls
   itself a local milestone package; that limitation must remain explicit until
   a release archive and checksums replace the workspace traversal.
2. **The frontend is copied, not built.** `web/dist` is an undeclared prebuilt
   workspace input. A release must either ship authenticated generated assets in
   the release source with a documented provenance/reproducibility policy, or
   build the SPA in `build()` with the required toolchain and locked inputs.
3. **A direct Python dependency is missing from `depends`.**
   `src/updatarr/app.py` imports `pydantic`, while the PKGBUILD omits
   `python-pydantic` and currently relies on FastAPI's dependency graph.
   `pyside6` is correctly declared for the direct tray imports.
4. **The license is intentionally not releasable.**
   `license=('custom:development-only')` matches the current development notice,
   but is not a selected redistribution license or an SPDX release declaration.

### Must resolve before publishing the current Caddy sample

1. **The sample does not meet Updatarr's forwarding-header rejection policy.**
   Its three `header_up -X-Forwarded-*` lines are followed by Caddy recreating
   those same fields. Replacing them with a wildcard would remove additional
   incoming `X-Forwarded-*` names but would still not suppress Caddy's three
   automatic fields. Under the current Updatarr invariant, ordinary Caddy
   `reverse_proxy` is not yet a supported example.
2. **The access matcher is too broad for the stated trust goal.**
   `remote_ip private_ranges` admits every immediate peer in broad private
   address space. Prefer exact managed LAN/VPN CIDRs. If Caddy is itself behind
   another proxy, that matcher sees the proxy; use the documented `client_ip`
   and exact `trusted_proxies` configuration instead.
3. **The network guide needs an end-to-end proxy acceptance test.** Use a real
   Caddy build and an echo upstream to capture the exact headers received by the
   application, in addition to Host, Origin, CSRF, cookie, TLS and long-lived
   event tests. Configuration parsing alone cannot prove the header invariant.

### systemd and operations documentation risks

1. The unit-directory destination and state/runtime/cache directory declarations
   are correct for current Arch. The systemd >=254 state-path assumption should
   be declared if non-current distributions remain in scope.
2. `Environment=XDG_CACHE_HOME=%C/updatarr` changes the XDG cache *base* to an
   application subdirectory. The unit already declares `CacheDirectory=updatarr`,
   which supplies `$CACHE_DIRECTORY`; use that application-specific variable if
   the program needs a cache path instead of redefining the XDG base.
3. `ARCH_INSTALL.md` describes the database as always under
   `~/.local/state/updatarr`. That is only the XDG default. Operational text and
   backup tooling should resolve `$STATE_DIRECTORY`/`%S/updatarr` so a user with
   a custom `$XDG_STATE_HOME` is not told to back up the wrong location.
4. The user units request filesystem namespace hardening without
   `PrivateUsers=true`. Treat `ProtectSystem`, `ProtectHome` and path restrictions
   as unverified on the target until a staged start plus
   `systemd-analyze --user security`/namespace behavior test demonstrates their
   effect. Adding `PrivateUsers=true` is a compatibility and runtime decision,
   not a documentation-only correction.

## Recommended M5 disposition

- Keep the current PKGBUILD explicitly local/development-only; do not describe
  it as clean-chroot reproducible.
- Before release packaging, use a checksummed release source in `$srcdir`, add
  all direct runtime dependencies, decide frontend build provenance, and select
  the project license.
- Retain `/usr/lib/systemd/user` and the directory directives, but stop
  redefining the XDG cache base and verify user-unit hardening on the target.
- Withdraw or clearly mark the Caddy snippet unsupported while Updatarr rejects
  all forwarding headers. Resolve the application/proxy trust contract first,
  then prove the chosen configuration with an echo-upstream integration test.
- Replace `private_ranges` with explicit deployment CIDRs in any final example;
  document the direct-Caddy and proxy-in-front-of-Caddy cases separately.

## Local read-only evidence

- `pkg-config systemd --variable=systemduserunitdir` returned
  `/usr/lib/systemd/user` on the inspected Arch host.
- `systemd-analyze --user verify` parsed both unit files and reported only that
  `/usr/bin/updatarr` and `/usr/bin/updatarr-tray` are absent on this uninstalled
  development host. This does not test sandbox effectiveness or service startup.
- Direct-import inspection found `pydantic` and `PySide6`; the PKGBUILD declares
  `pyside6` but not `python-pydantic`.
- `namcap` and `caddy` were not installed, so no package lint or live proxy test
  was claimed.
