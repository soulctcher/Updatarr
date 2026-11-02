# M7 Acceptance Packet

**Prepared:** 2026-11-01  
**Status:** corrected RC2 is ready for owner acceptance
**Candidate:** `v0.6.0-rc.2`

## RC1 Rejection

RC1 completed its clean builds, lifecycle and signatures, but failed final
package inspection because the installed runtime, browser and packaged README
contained the old demonstration password. Its signed label remains immutable
at `ee18e9a7f789404ece81488f150fd02e33837a42` for an honest record. RC1 is
rejected and must not be published.

RC2 removes every built-in development password, requires an explicit password
even in development mode and adds shipped-input and package-level regression
checks. Both extracted RC2 packages were scanned for `updatarr-demo` and
`test-only-password`; neither string is present.

No package was installed on the managed computer. No service, startup entry,
notifier, Octopi/Pamac installation, update source, firewall, proxy or software
was changed. Nothing was pushed or published.

## Candidate Identity

| Item | Recorded Value |
| --- | --- |
| Frozen Git revision | `660f4918ebc612e63953a0014199dfe481c100ef` |
| Signed annotated label | `v0.6.0-rc.2` |
| Label object | `d46c9f88dc87b9f67d371351a899cc4767bbd63c` |
| Release-key fingerprint | `721E ED2D 67AD EE74 D26E 75C5 7DAF 7D14 02C8 082E` |
| Signing subkey | `5BD6 C0A8 D98B 655A EAF0 5EC2 E689 CC8D 9BBB 0AA4` |
| Local release directory | `build/m7-release-v0.6.0-rc.2/` |

The local directory is ignored build output. It is not a public release or a
remote repository.

## Signed Release Files

| File | SHA-256 |
| --- | --- |
| `updatarr-0.6.0.tar.gz` | `3f00d78bb7784487daaa8f687006404de30620e9486ff67bbd78aa8681af3eb9` |
| `updatarr-0.6.0.tar.gz.asc` | `42307d8e93aa4dc82debfa7f54a3893d01f27826a99651e65dc480e9305b28dd` |
| `updatarr-0.6.0-1-any.pkg.tar.zst` | `59a95be67a26776da10a365e7088cb16c3f3dd09fbca0141308411a3cc2ad666` |
| `updatarr-0.6.0-1-any.pkg.tar.zst.asc` | `3a1031ccad708250621d29e9de544c001f796102ea6f57ddb4452bf4e25fb680` |
| `SHA256SUMS` | `9076812e00f8fa2964b07f74f4f2c0ae3ece01e10184dcc19da901c78eea5b95` |
| `SHA256SUMS.asc` | `40db9e34ad06a212e3c32b0d5688ac54aec6591e5bdce4e33d3f1c3be68e0d8a` |

The source archive, package and checksum-list signatures all passed from a
fresh GnuPG directory containing only the bundled public key. The signed Git
label passed the same check. The expected fresh-keyring trust warning remains
until a verifier independently compares the complete fingerprint.

## Clean Build and Lifecycle Evidence

Two networkless package builds ran sequentially under the documented 2 GiB
container ceiling. Their 213-file normalized payload manifests and 183-package
builder inventories are identical. The package archives differ only because
Arch records the build timestamp in generated package metadata.

| Evidence | SHA-256 |
| --- | --- |
| First package | `59a95be67a26776da10a365e7088cb16c3f3dd09fbca0141308411a3cc2ad666` |
| Repeated package | `429f94ce834a6317d1f44ac4437ad21cbc5d7913f322253a0702d4a35fe66696` |
| Drill-only release-2 package | `8a7889462aef57321b4a6ae6248cfd3ce006cad36af8a498f0c13c803960750d` |
| Normalized payload manifest | `221413a2d48695d63472aab34d767982dd8ae6562a7630bfb1d8ebaa58f11f92` |
| Builder package inventory | `a2cb2bf8ca6db33e144040b4e3a6fc74219f2bad6e9d68671b34362e03b682d0` |
| Builder image record | `032c8bfc0ea173ed6f12b349780d767321de8c44af7f19dd25b46e77131d0744` |
| Lifecycle log | `591feb125de313f4bcffcfa6f98630d0325494d1afd3afc244f9c172d12152f0` |
| Lifecycle package checksums | `9ba5f67f89b69202dfd15711594c26c135015aff2c675fd56d07ddd7236247dc` |
| Lifecycle image records | `4ea6c66d99434c2fbfa21d0932d287c3f15f9139dee833d27556eb95aabaace2` |

The disposable lifecycle passed package install, disabled-by-default service
checks, unprivileged loopback startup, browser serving, SQLite backup and
offline restore, upgrade, downgrade recovery, uninstall and user-state
preservation.

## Inventory and Verification Results

| Check | Result |
| --- | --- |
| Complete Python suite | **324 passed in 195.73 seconds**; one known third-party warning |
| Focused M7 AUR and release-evidence suite | **23 passed in 13.79 seconds** |
| TypeScript and production browser build | Passed |
| Locked Python and browser dependency audits | No known vulnerabilities |
| Python compilation, shell parsing and Git whitespace | Passed |
| Arch source checksum | Passed |
| Actual package password scan | Passed for both repeated extracted packages |
| Python runtime SBOM | 18 components |
| Browser runtime SBOM | 3 components |
| Declared dependency-license inventory | 21 components recorded |
| Final independent candidate review | Passed; no critical, high or medium findings |

Final RC2 evidence hashes:

- dependency licenses:
  `51dec1f0a350a06981ef48bc00dc170f52ebb923f3299609b579c26ed7025bb5`
- reviewed inputs:
  `9836b3c3800bb9489c8f9c14e40641da8269e337bbf2fe396fd565e97d9a1898`
- SBOM hash manifest:
  `1a421ce70c6a5defc05950358d059527ed864cf25668d5becb1dad0f0a9f13d1`
- Python SBOM:
  `e57fede6276abf10bc7e9a3d0a6f35f80e0f637cb00db320fe348dc8c659e1aa`
- browser SBOM:
  `5fb573d78bee04861d1b718c22babb0cfeba52eaf97653f99d8c819bfbf3585b`

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

- [x] Final independent candidate review has no unresolved critical, high or
      medium findings.
- [ ] User accepts M7. Acceptance creates a reviewed local release candidate;
      it does not authorize publication, host installation, service/notifier
      changes or live software mutation.
