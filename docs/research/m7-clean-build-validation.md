# M7 Clean Build and Package Validation

**Prepared:** 2026-11-01
**Status:** corrected RC2 build, package inspection, lifecycle, signatures and
independent review passed; ready for owner acceptance
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

Two builds used the same builder image and produced the same 213-file payload
manifest. The package archives differed only in generated package metadata:
`.PKGINFO` recorded build timestamps 13 seconds apart, which also changes
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
candidate revision `660f4918ebc612e63953a0014199dfe481c100ef` are:

| Evidence | SHA-256 |
| --- | --- |
| Source archive | `3f00d78bb7784487daaa8f687006404de30620e9486ff67bbd78aa8681af3eb9` |
| First package archive | `59a95be67a26776da10a365e7088cb16c3f3dd09fbca0141308411a3cc2ad666` |
| Repeated package archive | `429f94ce834a6317d1f44ac4437ad21cbc5d7913f322253a0702d4a35fe66696` |
| Normalized payload manifest | `221413a2d48695d63472aab34d767982dd8ae6562a7630bfb1d8ebaa58f11f92` |
| Builder package inventory | `a2cb2bf8ca6db33e144040b4e3a6fc74219f2bad6e9d68671b34362e03b682d0` |
| Builder image record | `032c8bfc0ea173ed6f12b349780d767321de8c44af7f19dd25b46e77131d0744` |

The normalized comparison contains 213 ordinary payload files; the package
archive contains 254 entries including directories and Arch metadata. The only
`.PKGINFO` difference is `builddate` (`1793578902` versus `1793578915`). Neither
extracted package contains either `updatarr-demo` or `test-only-password`.

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
| Lifecycle log | `591feb125de313f4bcffcfa6f98630d0325494d1afd3afc244f9c172d12152f0` |
| Lifecycle package checksums | `9ba5f67f89b69202dfd15711594c26c135015aff2c675fd56d07ddd7236247dc` |
| Lifecycle image records | `4ea6c66d99434c2fbfa21d0932d287c3f15f9139dee833d27556eb95aabaace2` |

## Runtime Inventory Evidence

The reviewed lock produced 18 Python runtime components and 3 browser runtime
components. All 21 have publisher-declared license metadata; the collected
identifiers are MIT, MIT-0, BSD-3-Clause, Apache-2.0 and PSF-2.0. This is an
inventory, not legal advice.

| Evidence | SHA-256 |
| --- | --- |
| Declared dependency-license inventory | `51dec1f0a350a06981ef48bc00dc170f52ebb923f3299609b579c26ed7025bb5` |
| Reviewed-input hash manifest | `9836b3c3800bb9489c8f9c14e40641da8269e337bbf2fe396fd565e97d9a1898` |
| SBOM hash manifest | `1a421ce70c6a5defc05950358d059527ed864cf25668d5becb1dad0f0a9f13d1` |
| Python CycloneDX SBOM | `e57fede6276abf10bc7e9a3d0a6f35f80e0f637cb00db320fe348dc8c659e1aa` |
| Browser CycloneDX SBOM | `5fb573d78bee04861d1b718c22babb0cfeba52eaf97653f99d8c819bfbf3585b` |

## Remaining Gates

- Obtain owner acceptance of the reviewed local RC2 candidate.
- Keep live AUR disabled until isolated source acquisition, clean dependency-
  root preparation and dependency handling are implemented and separately
  accepted.
- Keep release publication blocked until the owner accepts M7 and separately
  authorizes a remote, push and upload.
- Keep the managed-computer pilot unauthorized until its exact plan and host
  changes receive their separate approvals.

## Final Automated Verification

- Complete Python suite: **324 passed in 195.73 seconds**, with one known
  Starlette test-client deprecation warning.
- Focused M7 AUR and release-evidence suite: **23 passed in 13.79 seconds**.
- TypeScript checking and the Vite production build passed.
- Python compilation, shell parsing, Git whitespace checks and
  `makepkg --verifysource` passed.
- Independent final RC2 review found no remaining critical, high or medium
  findings. Its two low wording/status findings were corrected before owner
  acceptance was requested.
