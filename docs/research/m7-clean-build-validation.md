# M7 Clean Build and Package Validation

**Prepared:** 2026-11-01
**Status:** implementation clean-build comparison, disposable lifecycle and
complete suite passed; candidate rebuild is required after owner records close
**Authorization:** disposable project-local environments only; no package was
installed on the managed computer

## Boundary

`scripts/build_m7_arch_container.sh` builds the package in a disposable Arch
container based on a digest-pinned `archlinux:base-devel` image. Build tools
are installed only while creating that builder image. The actual package build
then runs as user 1000 with no network, a read-only container root, no Linux
capabilities, `no-new-privileges`, and explicit memory, task, CPU and temporary
storage limits. Only the package inputs are mounted read-only; only a new
evidence directory is writable.

This proves a controlled clean-container build. It is not a claim that Arch
`devtools` clean-chroot packaging has run, and it does not install the package
on the managed computer.

## Repeated Build Result

Two builds used the same builder image and produced the same 205-file payload
manifest. The package archives differed only in generated package metadata:
`.PKGINFO` recorded build timestamps 19 seconds apart, which also changes
`.BUILDINFO`, `.MTREE` and the compressed archive bytes. After excluding those
three generated metadata files, every installed payload path and SHA-256
digest matched.

Both builds recorded an identical installed builder-package inventory. The
package contains the selected `AGPL-3.0-or-later` license, the AUR sandbox
Module, the browser application, user service files and desktop launcher. It
contains no service-enable link, XDG autostart entry, package install script,
Polkit rule, `/etc` payload or workspace path.

Generated build evidence stays under ignored `build/` paths and is not a
release artifact. Exact final source, package, builder and inventory digests
for implementation revision `497634e` are:

| Evidence | SHA-256 |
| --- | --- |
| Source archive | `9833f98ee16c39a448fa61457f2f30a53b83041b1765679fd2953bbe95501d07` |
| First package archive | `8957c7109b6ddfb3bca9b2cc267dd650cca9352e8c4e0a4ff498a4b0d602fd94` |
| Repeated package archive | `60ed0ca8046c5960bc5fd7a79be5b6ac83d3f0e35361fecbce79fa7f31a9c076` |
| Builder package inventory | `a2cb2bf8ca6db33e144040b4e3a6fc74219f2bad6e9d68671b34362e03b682d0` |
| Builder image record | `032c8bfc0ea173ed6f12b349780d767321de8c44af7f19dd25b46e77131d0744` |

The normalized comparison contains 208 ordinary payload files; the package
archive contains 249 entries including directories and Arch metadata. The only
`.PKGINFO` difference is `builddate` (`1793560408` versus `1793560413`).

## Disposable Lifecycle Result

A second package with drill-only release number `2` was built from the same
source. In a separate disposable Arch system, pacman installed release 1 and
the drill proved that neither user service was enabled. Updatarr then started
as an unprivileged user in simulator mode, bound to loopback, returned the
health response and served the packaged browser application.

The drill created state, made a consistent SQLite backup, upgraded to release
2, changed state, performed an offline restore, downgraded to release 1 and
removed the package. The restored preference remained correct, packaged files
were removed, and the private database, backup and user configuration remained.
The lifecycle build had no network after its runtime base was prepared.

The first recovery attempt intentionally failed the drill because a plain copy
over a WAL-mode database allowed newer WAL state to survive. The accepted
procedure checkpoints and truncates the database while offline, removes stale
sidecars, copies the consistent backup to a new private file and atomically
replaces the database. The recovered value is verified before downgrade.

Final lifecycle evidence hashes:

| Evidence | SHA-256 |
| --- | --- |
| Lifecycle log | `bc7180ec8928be7942534aa95324e367a98cf96a60acbe2b86fda6b5bb89e031` |
| Lifecycle package checksums | `31d45da3654b2689e279dbb3cb146a7926d7938ed9de7dc89a3e87b8ac0b4f00` |
| Lifecycle image records | `ff4bb96bd38a14091d03fb550e8c2ec55de1ef2b51d19b23ccf78d4382a33865` |

## Runtime Inventory Evidence

The reviewed lock produced 18 Python runtime components and 3 browser runtime
components. All 21 have publisher-declared license metadata; the collected
identifiers are MIT, MIT-0, BSD-3-Clause, Apache-2.0 and PSF-2.0. This is an
inventory, not legal advice.

| Evidence | SHA-256 |
| --- | --- |
| Declared dependency-license inventory | `51dec1f0a350a06981ef48bc00dc170f52ebb923f3299609b579c26ed7025bb5` |
| Reviewed-input hash manifest | `35757bce71fe097d5fd4177ce2acb879da614d88753f48486507ba5ba0997b72` |
| SBOM hash manifest | `24ee86b8cee550fdae3c3ba4aebec82a56dcca750ee9f314d44435a8c08c7969` |
| Python CycloneDX SBOM | `249b3279bd0e7c7267561f3715d93f808b2d31cb3b743f8dfc12e283a9063c35` |
| Browser CycloneDX SBOM | `2f9bd95b6ad9e7934d68ab67a2724efb64520f3d28cb19abe2b7934d11402060` |

## Remaining Work

- Repeat the clean build, normalized comparison, evidence generation and
  lifecycle drill after the release-proof records are final.
- Keep live AUR disabled until isolated source acquisition, clean dependency-
  root preparation and dependency handling are implemented and separately
  accepted.
- Keep release publication blocked until owner-controlled release proof is
  available.

## Final Automated Verification

- Complete Python suite: **321 passed in 193.39 seconds**, with one known
  Starlette test-client deprecation warning.
- Focused M7 AUR and release-evidence suite: **21 passed**.
- TypeScript checking and the Vite production build passed.
- Python compilation, shell parsing, Git whitespace checks and
  `makepkg --verifysource` passed.
- Independent re-review found no remaining critical, high or medium
  implementation findings.
