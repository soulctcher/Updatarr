# M7 Release Foundations Research

**Prepared:** 2026-11-01  
**Scope:** license selection, source and artifact provenance, clean Arch builds,
software bills of materials and AUR isolation  
**Method:** primary specifications, official project documentation and local
read-only inspection

This note supplies decision evidence. It does not select a license, create a
repository or signing key, publish an artifact, install a package or enable AUR
execution.

## Verified Facts

### License Records Need Exact Identifiers and Complete Text

The SPDX License List provides stable identifiers, canonical text and permanent
links for common licenses. Current identifiers distinguish “only” from “or
later,” such as `GPL-3.0-only` and `GPL-3.0-or-later`; the same distinction
exists for AGPL. The M7 package should use the exact owner-selected SPDX
expression and include the matching complete license text.
[SPDX License List](https://spdx.org/licenses/)

The Open Source Initiative separately maintains its approved-license list and
describes approved open-source licenses as allowing software to be used,
modified and shared. Choosing a familiar SPDX identifier is not, by itself,
proof that the owner has rights to every source file or bundled asset.
[OSI approved licenses](https://opensource.org/licenses)

The three practical choices presented for Updatarr have materially different
effects:

- MIT permits use, modification, redistribution, sublicensing and sale when
  the copyright and permission notice are retained.
  [OSI MIT text](https://opensource.org/license/mit)
- GPLv3 applies its source-sharing conditions when covered software is
  conveyed. The license explicitly says that mere network interaction, without
  transfer of a copy, is not conveying.
  [GNU GPLv3](https://www.gnu.org/licenses/gpl-3.0.html)
- AGPLv3 adds a source offer for users who interact with a modified program
  over a network. GNU identifies interactive web applications as a common case
  and recommends exposing a source link in a network application's interface.
  [GNU license FAQ](https://www.gnu.org/licenses/gpl-faq.html#AGPLv3InteractingRemotely),
  [GNU licensing guide](https://www.gnu.org/licenses/gpl-howto.html)

These are license characteristics, not legal advice. The owner must select the
license and confirm that they have the rights needed to license the complete
first-party work and bundled assets.

### Release Tags and Signatures Are Separate Provenance Facts

Git distinguishes lightweight tags from annotated tags. Annotated tags contain
the tagger, date and message, and may contain a cryptographic signature. Git's
own documentation describes annotated tags as the form intended for releases;
`git tag -v` verifies a signed tag.
[Git tag documentation](https://git-scm.com/docs/git-tag)

Git can sign with OpenPGP, SSH or X.509. GitHub can display cryptographically
verifiable GPG, SSH or S/MIME commit and tag signatures when the corresponding
public identity is registered. This proves a relationship between a key and a
Git object; it does not by itself prove the build environment or package
contents.
[GitHub signature verification](https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification)

Arch's build tooling can create an OpenPGP detached signature beside the built
package. `makepkg --sign` or the `sign` setting in `makepkg.conf` produces a
`.sig` file through GnuPG, and `GPGKEY` selects the signing key. The key should
not be copied into the clean build environment: build first, hash the exact
output, then sign in a separate owner-controlled step.
[makepkg manual](https://man.archlinux.org/man/makepkg.8),
[makepkg.conf manual](https://man.archlinux.org/man/makepkg.conf.5.en)

A checksum detects whether bytes differ from a recorded artifact. It does not
identify who approved the checksum. A signature authenticates the signed bytes
only after the verifier has separately established which signing identity to
trust. A signed Git tag, a package signature and a build-provenance statement
therefore answer different questions and should remain separate evidence.

### Arch Release Builds Need a Clean Build Environment

Arch's clean-chroot guidance uses `mkarchroot` to create a clean environment and
`makechrootpkg` to build the package from the directory containing the
`PKGBUILD`. It warns that custom package-manager or build configuration can
silently change the environment. M7 should retain the exact clean environment,
package databases, commands and output manifest as evidence.
[Arch clean-chroot guidance](https://wiki.archlinux.org/title/clean_chroot),
[makechrootpkg manual](https://man.archlinux.org/man/makechrootpkg.1.en)

A clean build proves dependency declarations and reduces host contamination; it
does not prove reproducibility by itself. `makepkg` exposes
`SOURCE_DATE_EPOCH` for reproducible-build inputs, but M7 must still repeat the
build and compare exact source hashes plus normalized package contents while
recording any archive-metadata difference.
[makepkg reproducible-build environment](https://man.archlinux.org/man/makepkg.8)

### SBOMs Describe Components but Do Not Replace License Review

CycloneDX can record first- and third-party components, hashes, licenses,
dependencies, provenance and build formulation. SPDX likewise defines an SBOM
as a collection describing a package, potentially including composition,
provenance, licensing, quality and security information. An SBOM is structured
inventory evidence; it is not a compatibility opinion or a substitute for
reviewing license terms.
[CycloneDX specification overview](https://cyclonedx.org/specification/overview/),
[SPDX 3.0.1 SBOM model](https://spdx.github.io/spdx-spec/v3.0.1/model/Software/Classes/Sbom/)

The locked local tools already produce CycloneDX 1.5 JSON without adding a new
project dependency:

- `uv export --locked --no-dev --format cyclonedx1.5` describes the Python
  runtime dependency graph; and
- `npm sbom --package-lock-only --omit=dev --sbom-format=cyclonedx` describes
  the browser runtime graph.

The uv project explicitly labels CycloneDX export as preview functionality, so
M7 must pin and record the uv version and validate the resulting document
instead of treating the format as a stable API. npm documents SPDX and
CycloneDX output as supported `npm sbom` formats.
[uv CycloneDX export](https://docs.astral.sh/uv/concepts/projects/export/),
[npm SBOM command](https://docs.npmjs.com/cli/commands/npm-sbom/)

Local inspection found that npm includes declared license identifiers for the
browser runtime components, while the current uv export omits license fields
for the Python components. The Python license inventory therefore needs a
separate declared-license collection and review; an empty SBOM license field
must remain unknown rather than being guessed.

These two dependency-graph documents also do not prove what the final Arch
package contains. M7 needs a manifest from the extracted package and a
package-payload SBOM or an explicit statement that the candidate contains
separate Python, browser and installed-file inventories rather than one falsely
complete SBOM. A whole-payload scanner such as Syft can read directories and
archives, but it is not currently installed and must be evaluated and pinned
before use rather than downloaded implicitly.
[Syft supported sources](https://github.com/anchore/syft/wiki/Supported-Sources)

### Bubblewrap Is a Policy Tool, Not a Complete AUR Sandbox

Bubblewrap creates namespaces and an explicitly constructed filesystem view,
can hide the network, sets `no_new_privs`, and supports a cleared environment.
Its own documentation warns that it is not a complete ready-made sandbox: the
security boundary is determined by the caller's exact arguments. It also warns
that mounted sockets, especially D-Bus, can become escape paths and that
`--new-session` is needed for terminal isolation unless an appropriate seccomp
filter is used.
[Bubblewrap README](https://github.com/containers/bubblewrap/blob/main/README.md)

Therefore, the presence of `/usr/bin/bwrap` is not evidence that AUR execution
is safe. Updatarr still needs a closed policy, hostile build tests, source-fetch
separation, output validation and independent review. Until then, the
M3/M6 block remains correct.

Arch describes AUR packages as unofficial user-produced content and tells
users to inspect the `PKGBUILD`, install files and repository content for
malicious commands. Arch also notes that `PKGBUILD` files can contain arbitrary
commands and that `makepkg` must not run as root. Manual review is necessary,
but cannot replace runtime isolation for an automated service.
[Arch AUR guidance](https://wiki.archlinux.org/title/Arch_User_Repository),
[Arch makepkg guidance](https://wiki.archlinux.org/title/Makepkg)

The minimum prototype therefore needs to demonstrate all of the following,
with the entire `makepkg` process inside the boundary:

- a fresh mount, user, PID, IPC, UTS and network view, with no network during
  the build stage and a separately bounded source-fetch stage when required;
- no mounted Updatarr state, configuration, runtime directory, home directory,
  SSH/GPG agents, display sockets, D-Bus sockets or host package-manager socket;
- an allowlisted read-only tool/runtime view and one dedicated writable build
  tree, with only a validated package output crossing back;
- a cleared, rebuilt environment, `no_new_privs`, a new terminal session,
  minimal devices and no administrator or package-install capability;
- CPU, memory, process, file-size and time limits, plus complete child-process
  cleanup; and
- hostile tests for path traversal, symbolic links, socket access, process and
  `/proc` visibility, network access, resource exhaustion and malformed output.

These are engineering requirements inferred from Bubblewrap's documented
policy responsibility and systemd's cgroup resource controls. They are not a
claim that one particular argument list is already safe.
[systemd resource controls](https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html)

## Local Findings

- The owner authorized a local Git baseline, which now exists without a remote
  or push. No signed release label exists yet.
- The owner selected `AGPL-3.0-or-later`; the project and package metadata now
  record it and include the official license text. Exact copyright-holder text
  remains pending.
- The M6 source archive is checksummed, but it predates the M7 working tree and
  is not tied to a signed release label.
- `git`, `gpg`, `makepkg`, `npm`, `uv` and `bwrap` are present. The standard
  Arch clean-chroot helper commands are not currently on `PATH`; M7 must not
  install them without separate approval.
- With the current locks, `uv 0.13.1` exports 18 non-development CycloneDX
  components and labels the feature experimental; none contains a license
  field. A separate metadata pass found declared SPDX expressions for all 18:
  MIT, MIT-0, BSD-3-Clause, Apache-2.0 and PSF-2.0. `npm 12.2.1` exports three
  non-development browser components and all three declare MIT. No obvious
  conflict with the selected AGPL license was found, but publisher declarations
  are inventory evidence rather than a legal compatibility conclusion.
- The project has one first-party generated bitmap logo. The packaged copy and
  browser source copy have the same SHA-256 digest. Browser screenshots are
  generated from Updatarr's own interface and are documentation evidence, not
  third-party artwork.
- The owner selected one OpenPGP identity for both signed Git release labels
  and downloaded files. No private key or owner identity was inspected or used;
  that remains a later local visual credential flow.
- Official OpenAI image-generation documentation explains how outputs are
  generated and saved but does not state the redistribution terms that applied
  to the earlier in-product logo generation. The asset record therefore keeps
  that permission question open instead of inferring rights.

## Recommended M7 Direction

These points are engineering recommendations inferred from the verified facts:

1. Use an exact SPDX license expression and include the complete selected
   license text; never convert the development-only notice into a release
   license automatically.
2. Establish a Git baseline only after the owner selects the repository
   authority. Use signed annotated release tags and detached signatures for
   release artifacts, with keys retained by the owner and outside the build
   environment. Record verification commands and the trusted public-key
   fingerprint.
3. Generate separate runtime and build SBOMs from the locked Python and npm
   graphs. Add a reviewed Python declared-license inventory because the current
   uv SBOM does not supply those fields, and inventory the extracted Arch
   package so the evidence does not imply unsupported whole-payload coverage.
4. Require a clean Arch build before calling an artifact a release candidate.
   Compare source hashes and normalized installed-file manifests rather than
   hiding unavoidable archive metadata differences.
5. Keep AUR build/install disabled in the first release candidate unless a
   later isolation prototype passes the complete adversarial gate. Read-only
   AUR discovery and review can remain visible.

## Owner Decisions

The owner must now choose the project license, repository/tag authority,
signing method and initial AUR release boundary. Those choices are presented in
[M7 owner decisions](../M7_OWNER_DECISIONS.md).

