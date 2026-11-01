# M7 AUR Isolation Prototype Validation

**Prepared:** 2026-11-01  
**Status:** project-local prototype passes its bounded fixture checks; live AUR
execution remains blocked  
**Host changes:** no package, source, service, notifier or installed software
change; only collected transient user scopes and disposable files were used

## Module Interface

`BubblewrapAurSandbox.build(reviewed_tree, expected_packages)` is the complete
build-operation interface. Application composition supplies one private output
root when it creates the Module; the ordinary constructor accepts no resource
limit or executable override. The build caller supplies one already reviewed
source tree and the exact package identities expected from it. It cannot
supply a command, executable, environment variable, mount, Bubblewrap option,
package-manager argument or resource-control option. Tests use one private
factory to lower fixed limits without expanding the production interface.

The Module hides private workspace creation, input copying, namespace and
filesystem policy, environment construction, `makepkg` arguments, time and
resource ceilings, log cleanup, package-archive inspection, identity matching,
hashing and private output retention.

## Implemented Isolation

- Bubblewrap, `makepkg`, `systemd-run` and `bsdtar` must be ordinary,
  root-owned files at fixed system paths and may not be group- or
  world-writable.
- The build receives new user, PID, IPC, UTS, network and mount namespaces,
  `no_new_privs`, a new terminal session, an empty root, a new `/proc`, minimal
  `/dev` and private `/tmp`.
- Only `/usr` is visible read-only. The real home, runtime directory, D-Bus,
  display sockets, SSH/GPG agents, `/run`, `/var`, `/sys` and host `/tmp` are
  absent.
- The environment is cleared and rebuilt with only fixed `PATH`, `HOME`,
  `LANG` and `SOURCE_DATE_EPOCH` values.
- One copied build tree is writable. Symbolic links and non-regular input files
  are rejected before the process starts. Files are opened without following
  links and checked again after opening so a changed path cannot redirect the
  copy. File count and byte limits apply.
- The build has no network. Source material must already exist in the reviewed
  tree; a package that tries to download during the build fails.
- The outer transient user scope declares memory, swap, task and CPU ceilings.
  Process time, output size, open files, address space and wall time have
  additional process limits. Failure to create the scope fails closed.
- The private build tree is created only on the verified `/dev/shm` tmpfs, not
  on a host disk. Input bytes are bounded before execution; build-time tmpfs
  pages are charged to the transient scope's memory ceiling. Captured standard
  output and error are drained continuously while retaining only a fixed-size
  tail, so untrusted output cannot grow the service process without limit.
- Compression uses one thread and ordinary build work is limited to two jobs,
  keeping the test and future build envelope predictable.
- Exact split-package identities are accepted. Missing, unexpected, ambiguous
  or duplicate package identities are rejected. Total retained package bytes
  have one aggregate ceiling.
- Each package is parsed in a second networkless Bubblewrap scope. Absolute or
  parent-directory archive paths, unreadable package metadata and a mismatched
  internal `pkgname` are rejected before the output is retained.
- Retained files are ordinary private files with their size and SHA-256 digest.
  Multiple outputs are staged privately and become visible as one complete
  result, so a failed copy cannot expose a partial result. Malformed UTF-8 in
  archive paths or package metadata is rejected cleanly. This step does not
  install or sign the files.

## Adversarial Evidence

The bounded fixture suite covers:

- a normal package and an exact two-output split package;
- attempts to read a host test secret, the real home/runtime, D-Bus, display
  state and inherited secret variables;
- attempts to write into `/usr` or reach the network;
- symbolic-link input and symbolic-link package output;
- invalid caller package identity; and
- a runaway build stopped at the wall-time limit.

### Resource-Test Correction

An early test deliberately committed memory to confirm the cgroup ceiling. The
kernel stopped that scope as configured, but the desktop displayed a low-memory
notification. The process left no surviving scope or child, and system memory
returned to normal. Deliberate memory- and process-pressure fixtures were then
removed permanently. Current tests use a 512 MiB, 32-task ceiling and verify
the declared resource policy without allocating memory or spawning a process
flood.

## Remaining Blockers

This prototype is not yet sufficient for live AUR builds:

1. **Source acquisition is absent.** A separately isolated download/VCS stage
   must fetch the exact reviewed sources, retain hashes or commits and hand
   only those inputs to the networkless build.
2. **The build tool root is host-derived.** `/usr` is read-only and contains no
   user secrets, but it reflects the managed computer rather than a clean,
   versioned Arch build root. Undeclared dependencies could therefore be
   available.
3. **Dependencies are not prepared.** `makepkg --nodeps` prevents package
   installation inside the sandbox. A later design must create a disposable
   dependency root without modifying the managed computer.
4. **Package review is structural, not a trust verdict.** The output identity,
   paths, readability and digest are checked, but package contents and install
   scripts remain the result of untrusted reviewed build code. Final
   installation still needs exact local confirmation and the separate
   privileged path.
5. **Independent security review is pending.** Live execution remains blocked
   even after the remaining engineering work until that review accepts the
   source, dependency, build and output handoff together.

The owner's M7 option 4B remains enforced: no release candidate is produced
until these blockers are resolved and the complete isolation gate passes.

