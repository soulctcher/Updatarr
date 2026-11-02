# M7 Clean Build and Package Validation

**Prepared:** 2026-11-01
**Status:** RC1 build and lifecycle evidence passed, but final package
inspection rejected RC1; corrected RC2 rebuild is required
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

Two builds used the same builder image and produced the same 212-file payload
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

Generated build evidence stays under ignored `build/` paths. The reviewed
release files are assembled separately under the ignored local release
directory. Exact final source, package, builder and inventory digests for
candidate revision `ee18e9a7f789404ece81488f150fd02e33837a42` are:

| Evidence | SHA-256 |
| --- | --- |
| Source archive | `b8dbeb571e99d8248b30b9571b3f289ec22749a0d117496f3103f35337c4a794` |
| First package archive | `47266c88b5029e5cb25a7bb91437fdfa5d3f95b160855b922cc06609f7238837` |
| Repeated package archive | `1bf8c185be95d78f35c9d3661a4eb9a79de0c1b5ea36c3f7fda0a8ec364740fb` |
| Normalized payload manifest | `6e2d5e2e80bad6af87478c857e89312a673441553f77a7062e9c02ad17b09e2f` |
| Builder package inventory | `a2cb2bf8ca6db33e144040b4e3a6fc74219f2bad6e9d68671b34362e03b682d0` |
| Builder image record | `032c8bfc0ea173ed6f12b349780d767321de8c44af7f19dd25b46e77131d0744` |

The normalized comparison contains 212 ordinary payload files; the package
archive contains 253 entries including directories and Arch metadata. The only
`.PKGINFO` difference is `builddate` (`1793578191` versus `1793578199`).

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
| Lifecycle log | `64e299002a332fca34dc0b1747ccffcfc73d7d46c3d53b984faa25c33920930c` |
| Lifecycle package checksums | `2c1fd4334e5be66a55be8110796def046859b343cae19bcafaf2c5ba5749743e` |
| Lifecycle image records | `e25305435b9a41925e3b63acd944ddcc720d2d44e375ae2b5702778c556a47d2` |

## Runtime Inventory Evidence

The reviewed lock produced 18 Python runtime components and 3 browser runtime
components. All 21 have publisher-declared license metadata; the collected
identifiers are MIT, MIT-0, BSD-3-Clause, Apache-2.0 and PSF-2.0. This is an
inventory, not legal advice.

| Evidence | SHA-256 |
| --- | --- |
| Declared dependency-license inventory | `51dec1f0a350a06981ef48bc00dc170f52ebb923f3299609b579c26ed7025bb5` |
| Reviewed-input hash manifest | `dd99263ac4254de5c47ddc5d54b7883835b7b1cd68a950da9e3403157b69dc98` |
| SBOM hash manifest | `7880247e77e68b5a0227ef1446553634924d25e6f7dfda4dd46503a031565216` |
| Python CycloneDX SBOM | `0b8b8532faf9b4a419ed345c3990ff1e4fbce893bc8cf21b525610f642e257d5` |
| Browser CycloneDX SBOM | `66fc012c188c4b4df8ba5ec732e0688b58e250a6c77b858df5a419e84d96fa63` |

## Remaining Gates

- Repeat the clean builds, package inspection, lifecycle, evidence generation
  and signatures for RC2 after removing the built-in development password.
- Keep live AUR disabled until isolated source acquisition, clean dependency-
  root preparation and dependency handling are implemented and separately
  accepted.
- Keep release publication blocked until the owner accepts M7 and separately
  authorizes a remote, push and upload.
- Keep the managed-computer pilot unauthorized until its exact plan and host
  changes receive their separate approvals.

## Final Automated Verification

- Complete Python suite: **322 passed in 194.85 seconds**, with one known
  Starlette test-client deprecation warning.
- Focused M7 AUR and release-evidence suite: **22 passed**.
- TypeScript checking and the Vite production build passed.
- Python compilation, shell parsing, Git whitespace checks and
  `makepkg --verifysource` passed.
- Independent implementation re-review found no remaining critical, high or
  medium findings. Final candidate re-review is recorded in the M7 acceptance
  packet.
