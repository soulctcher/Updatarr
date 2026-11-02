# M7 Acceptance Packet

**Prepared:** 2026-11-01  
**Status:** RC1 rejected; corrected RC2 build, signing and final review pending  
**Candidate:** `v0.6.0-rc.1` — rejected; do not publish

## RC1 Rejection

RC1 completed its clean builds, lifecycle and signatures, but failed final
package inspection because the installed runtime, browser and packaged README
contained the old demonstration password. RC1 remains immutably signed for an
honest record, but it is rejected and must not be published. The corrected
candidate will be `v0.6.0-rc.2`.

No package was installed on the managed computer. No service, startup entry,
notifier, Octopi/Pamac installation, update source, firewall, proxy or software
was changed. Nothing was pushed or published.

## Candidate Identity

| Item | Recorded Value |
| --- | --- |
| Frozen Git revision | `ee18e9a7f789404ece81488f150fd02e33837a42` |
| Signed annotated label | `v0.6.0-rc.1` |
| Label object | `e3a031d5681bb093233475cc5e0292d8c1ebab2d` |
| Release-key fingerprint | `721E ED2D 67AD EE74 D26E 75C5 7DAF 7D14 02C8 082E` |
| Signing subkey | `5BD6 C0A8 D98B 655A EAF0 5EC2 E689 CC8D 9BBB 0AA4` |
| Local release directory | `build/m7-release-v0.6.0-rc.1/` |

The local directory is ignored rejected build output. It is not a public
release or a remote repository. All hashes below describe rejected RC1 and are
retained only as failure evidence.

## Signed Release Files

| File | SHA-256 |
| --- | --- |
| `updatarr-0.6.0.tar.gz` | `b8dbeb571e99d8248b30b9571b3f289ec22749a0d117496f3103f35337c4a794` |
| `updatarr-0.6.0.tar.gz.asc` | `7d03b2ccf4853a3c4c8c8c243e3f814b3bb734b02c8b9325e4d34e026842b1a4` |
| `updatarr-0.6.0-1-any.pkg.tar.zst` | `47266c88b5029e5cb25a7bb91437fdfa5d3f95b160855b922cc06609f7238837` |
| `updatarr-0.6.0-1-any.pkg.tar.zst.asc` | `19c6582a609443cd15e9cc432da7acd1f9ea2dcc689971d0bdbad6f4e148e227` |
| `SHA256SUMS` | `89fc57c384065cd5294b88bdd3f2de31f7fc826e5ecf97f741afa22df2b826a3` |
| `SHA256SUMS.asc` | `d8b6bcd1eb6b7bc39a46ecbd8413431a967d98834fee1d845014a8f8849ea5de` |

The source archive, package and checksum-list signatures all passed from a
fresh GnuPG directory containing only the bundled public key. The signed Git
label passed the same check. The expected fresh-keyring trust warning remains
until a verifier independently compares the complete fingerprint.

## Clean Build and Lifecycle Evidence

Two networkless package builds ran sequentially under the documented 2 GiB
container ceiling. Their 212-file normalized payload manifests and builder
package inventories are identical. The package archives differ only because
Arch records the build timestamp in generated package metadata.

| Evidence | SHA-256 |
| --- | --- |
| Repeated package | `1bf8c185be95d78f35c9d3661a4eb9a79de0c1b5ea36c3f7fda0a8ec364740fb` |
| Normalized payload manifest | `6e2d5e2e80bad6af87478c857e89312a673441553f77a7062e9c02ad17b09e2f` |
| Builder package inventory | `a2cb2bf8ca6db33e144040b4e3a6fc74219f2bad6e9d68671b34362e03b682d0` |
| Builder image record | `032c8bfc0ea173ed6f12b349780d767321de8c44af7f19dd25b46e77131d0744` |
| Lifecycle log | `64e299002a332fca34dc0b1747ccffcfc73d7d46c3d53b984faa25c33920930c` |
| Lifecycle package checksums | `2c1fd4334e5be66a55be8110796def046859b343cae19bcafaf2c5ba5749743e` |
| Lifecycle image records | `e25305435b9a41925e3b63acd944ddcc720d2d44e375ae2b5702778c556a47d2` |

The disposable lifecycle passed package install, disabled-by-default service
checks, unprivileged loopback startup, browser serving, SQLite backup and
offline restore, upgrade, downgrade recovery, uninstall and user-state
preservation.

## Inventory and Verification Results

| Check | Result |
| --- | --- |
| Complete Python suite | **322 passed in 194.85 seconds**; one known third-party warning |
| TypeScript and production browser build | Passed |
| Locked Python and browser dependency audits | No known vulnerabilities |
| Python compilation, shell parsing and Git whitespace | Passed |
| Arch source checksum | Passed |
| Python runtime SBOM | 18 components |
| Browser runtime SBOM | 3 components |
| Declared dependency-license inventory | 21 components recorded |
| Final independent candidate review | RC1 review aborted after package defect; RC2 pending |

Final evidence hashes:

- dependency licenses:
  `51dec1f0a350a06981ef48bc00dc170f52ebb923f3299609b579c26ed7025bb5`
- reviewed inputs:
  `dd99263ac4254de5c47ddc5d54b7883835b7b1cd68a950da9e3403157b69dc98`
- Python SBOM:
  `0b8b8532faf9b4a419ed345c3990ff1e4fbce893bc8cf21b525610f642e257d5`
- browser SBOM:
  `66fc012c188c4b4df8ba5ec732e0688b58e250a6c77b858df5a419e84d96fa63`

## Retained Gates

- Public release, remote creation, push and upload remain unauthorized.
- The managed-computer pilot remains unauthorized. Its plan does not install
  or start anything by itself.
- Package/service installation, startup changes, notifier migration and
  Octopi/Pamac removal remain separate approvals.
- Every first live software-changing path remains separately gated.
- Live AUR remains disabled with no override. The bounded prototype and its
  independent review passed for M7, but isolated source acquisition, a clean
  dependency root and dependency preparation are not implemented.
- The generated logo's exact image model/version was not retained. This is a
  reproducibility limitation, not a release blocker.

## Acceptance

- [ ] Final independent candidate review has no unresolved critical, high or
      medium findings.
- [ ] User accepts M7. Acceptance creates a reviewed local release candidate;
      it does not authorize publication, host installation, service/notifier
      changes or live software mutation.
