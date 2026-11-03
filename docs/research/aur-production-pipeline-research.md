# AUR Production Pipeline Research

**Date:** 2026-11-03  
**Status:** implementation direction established; live AUR build and install
remain gated  
**Scope:** official Arch tooling, source/dependency preparation, isolation and
the typed Updatarr boundary

## Outcome

Updatarr can replace the blanket “AUR builds are not available” rule with a
real readiness gate, but the existing Bubblewrap prototype is only the final
untrusted-code layer. A production pipeline also needs the official Arch
`devtools` clean-root workflow, a reviewed source snapshot, a dependency graph
whose AUR members are built in order, and an artifact handoff that is separate
from installation.

The safe project direction is:

1. acquire one exact AUR Git commit from the fixed HTTPS AUR host;
2. record and show the complete build-file diff before approval;
3. acquire and verify upstream sources in a disposable, secret-free networked
   stage;
4. prepare a clean Arch build root with official repository dependencies;
5. recursively build reviewed AUR dependencies and pass only their verified
   package files into the clean working root;
6. run the reviewed build with bounded resources and no Updatarr state,
   browser data, user home or service secrets;
7. inspect and hash the exact package outputs; and
8. require a fresh local confirmation, plus separate administrator permission,
   before a fixed package-install operation.

No public or browser-facing interface should accept a command, executable,
environment, mount, repository URL or arbitrary argument list.

## What Arch Supports

### Clean builds

Arch identifies `pkgctl` as its canonical package-building tool. It builds in a
clean chroot and uses `systemd-nspawn`; the clean environment exists so the
build contains only declared dependencies rather than packages accidentally
present on the managed computer. The current `pkgctl build` manual says its
default chroots live in `/var/lib/archbuild`, and that `-I` installs an already
built package into the working copy. [ALPM building model](https://man.archlinux.org/man/alpm.7.en#Building_from_source) ·
[pkgctl build manual](https://man.archlinux.org/man/pkgctl-build.1)

The lower-level supported route is `mkarchroot <root>/root base-devel`, followed
by `makechrootpkg -c -r <root>`. The `-c` option cleans the working copy and
`-I <package-file>` preinstalls a dependency package into that copy. The
official clean-chroot guide recommends the same flow and says AUR-only
dependencies must be built first and supplied to the chroot. [makechrootpkg manual](https://man.archlinux.org/man/makechrootpkg.1) ·
[Arch clean-chroot guide](https://wiki.archlinux.org/title/Building_in_a_clean_chroot) ·
[Arch package-creation guide](https://wiki.archlinux.org/title/Creating_packages#Using_pkgctl_to_build_in_a_clean_chroot_environment)

Therefore the required host tools are the official `devtools` package and its
dependencies, plus `base-devel` inside the clean root. Updatarr must treat
absence or an unsafe version/ownership check of those fixed tools as “AUR build
not ready,” not fall back to `yay`, host `makepkg`, or a shell command.

### Build-file acquisition and review

The official AUR workflow retrieves build files from the package's Git clone
URL, normally `https://aur.archlinux.org/<package-base>.git`, and requires the
user to inspect the `PKGBUILD` and related files. Arch warns that AUR content is
unofficial and not thoroughly vetted. [Arch User Repository guide](https://wiki.archlinux.org/title/Arch_User_Repository) ·
[AUR helper warning](https://wiki.archlinux.org/title/AUR_helpers)

`.SRCINFO` is the non-shell metadata format intended for tools that need
package names, sources, dependencies, provided names and conflicts without
parsing a `PKGBUILD`. It is useful for an initial graph, but Updatarr must bind
it to the same reviewed Git commit and must not call it a trust verdict.
[`.SRCINFO` specification](https://wiki.archlinux.org/title/.SRCINFO)

The AUR RPC v5 `info` response also exposes `Depends`, `MakeDepends`,
`CheckDepends`, `Provides`, `Conflicts` and package-base identity. It is useful
for bounded discovery and cross-checking, but it is server metadata rather than
proof of the downloaded commit. [AUR RPC v5 interface](https://wiki.archlinux.org/title/Aurweb_RPC_interface)

### Upstream source verification

`makepkg --verifysource` downloads each declared source and performs configured
checksum and signature checks without extracting or building it. Arch describes
this as suitable preparation for a later offline build. `--skipinteg`,
`--skipchecksums` and `--skippgpcheck` explicitly disable protections and must
never be exposed by Updatarr. [makepkg manual](https://man.archlinux.org/man/makepkg.8#OPTIONS)

This separation matters because `makechrootpkg` currently passes
`--skipinteg` to its internal `makepkg` by default: it assumes the caller has
already prepared and verified sources. The acquisition stage must therefore
record the exact local files, source hashes, signature results and VCS commit
identities before the clean build stage starts. [makechrootpkg manual](https://man.archlinux.org/man/makechrootpkg.1#DESCRIPTION)

Arch's package standards prefer HTTPS sources and cryptographic signatures
where upstream supplies them. VCS package sources cannot always provide a
content checksum, so the resolved commit must be recorded and displayed as an
unknown/trust limitation rather than silently treated like a fixed archive.
[Arch package source standards](https://wiki.archlinux.org/title/Arch_package_guidelines#Package_sources) ·
[AUR VCS limitation](https://wiki.archlinux.org/title/Arch_User_Repository#What_is_the_difference_between_foo_and_foo-git_packages?)

## Security Boundary

A clean chroot is a dependency-purity mechanism, not sufficient evidence that
hostile build code is contained. The `systemd-nspawn` manual warns that its
sandbox is easily circumvented without user namespaces and says untrusted code
must run in a user namespace. [systemd-nspawn security guidance](https://man.archlinux.org/man/systemd-nspawn.1#DESCRIPTION)

Consequently, Updatarr must keep these properties from its accepted prototype
when it adopts the clean root:

- an empty environment and disposable home;
- no bind mount of an ordinary user's home, runtime directory, SSH/GPG agent,
  browser data, Updatarr database or notification credentials;
- a private network for the build stage after sources are acquired;
- a user namespace or an independently reviewed equivalent confinement;
- bounded memory, swap, process count, CPU time, output size, open files and
  wall-clock time;
- a new clean working copy for every build; and
- output copied through a narrow, regular-file-only verifier.

The pipeline must fail closed if the installed `devtools` implementation does
not provide the required user-namespace/confinement behavior. A successful
clean-chroot build alone is not a safety attestation.

## AUR Dependency Handling

Official repository dependencies belong in the disposable clean root, where
`pkgctl`/`makechrootpkg` can resolve them. An AUR dependency is different:
Arch's documented method is to build that dependency first and pass its package
file with `pkgctl build -I` or `makechrootpkg -I`. [pkgctl build `-I`](https://man.archlinux.org/man/pkgctl-build.1#INSTALL_OPTIONS) ·
[clean-chroot pre-installation](https://wiki.archlinux.org/title/Building_in_a_clean_chroot#Pre-install_required_packages)

Updatarr therefore needs a bounded dependency Module that:

- reads names and constraints from reviewed `.SRCINFO` plus bounded RPC
  cross-checks;
- asks the official repositories first;
- makes unresolved alternatives and `provides` choices explicit to the user;
- treats every selected AUR dependency as another independently reviewed Git
  commit;
- rejects cycles, excessive depth/count and conflicting providers;
- builds in topological order; and
- supplies only already verified package files to later working roots.

Arch explicitly warns that AUR helpers are unsupported. `yay` may remain a
read-only update-discovery adapter, but it must not become Updatarr's privileged
or production build interface. [AUR helper warning](https://wiki.archlinux.org/title/AUR_helpers)

## Typed Project Contract

The production seam should be a deep Module with a small interface such as:

```text
inspect(AurPackageIdentity, ExpectedAurCommit)
  -> ReviewedAurTree

resolve(ReviewedAurTree, RepositorySnapshot)
  -> DependencyPlan | ExplicitUserChoice

prepare(ReviewedAurTree, DependencyPlan)
  -> VerifiedSourceBundle

build(VerifiedSourceBundle, CleanRootIdentity, ResourceLimits)
  -> VerifiedPackageSet

install(SealedPlanId, VerifiedPackageSetIdentity, LocalSubject)
  -> InstallResult
```

The values crossing each seam must contain stable package/base names, exact Git
commit, file-manifest digest, source-verification results, clean-root package
database digest, dependency artifact digests, expected output identities,
resource policy version and expiry. The implementation—not the caller—chooses
fixed executable paths, AUR hostname, repository configuration, chroot path
policy and arguments.

A readiness record should be immutable and short-lived:

```text
AurPipelineReadiness
  tools_verified
  clean_root_verified
  user_namespace_verified
  secret_isolation_verified
  source_stage_verified
  dependency_stage_verified
  artifact_handoff_verified
  policy_version
  checked_at
  evidence_digest
```

The planner may set an AUR step to executable only when every field is true and
the evidence is current. A plain constructor boolean is acceptable only in the
deterministic simulator; it is not a production attestation.

## Current Host Observation

A read-only local probe on 2026-11-03 found `yay`, `git`, `bwrap`, `makepkg` and
`systemd-run`, but did not find `pkgctl`, `makechrootpkg`, `mkarchroot` or the
`devtools` package. No package was installed and no chroot was created.

This means the present installed build cannot honestly enable live AUR work.
Installing `devtools`, creating/updating the clean root and proving the full
typed path are host changes and remain separate approval-gated work.

## Remaining Gates

Before Updatarr may perform the first live AUR build:

1. implement and test the typed acquisition, dependency, clean-root and
   artifact-handoff Modules with hostile fixtures;
2. independently review the complete path, including the actual installed
   `devtools`/`systemd-nspawn` user-namespace behavior;
3. obtain explicit approval to install `devtools` and create the managed clean
   root;
4. present one exact package commit, dependency graph, source-verification
   record, resource limits and expected outputs for local confirmation; and
5. keep package installation separately sealed behind local confirmation and
   Polkit.

The current request authorizes project work to remove the permanent blocker;
it does not by itself authorize these host mutations or the first live AUR
build/install.
