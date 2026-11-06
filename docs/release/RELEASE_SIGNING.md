# Release Signing

**Prepared:** 2026-11-01  
**Status:** M7.2 RC4 label and release-file signatures verify locally; the
public `main` branch and signed RC4 label were published on 2026-11-06.

## Official Public Identity

- **Name:** `Erik Winblad (Updatarr Release Key)`
- **Primary fingerprint:**
  `721E ED2D 67AD EE74 D26E 75C5 7DAF 7D14 02C8 082E`
- **Signing-subkey fingerprint:**
  `5BD6 C0A8 D98B 655A EAF0 5EC2 E689 CC8D 9BBB 0AA4`
- **Algorithm:** Ed25519
- **Created:** 2026-11-01
- **Expires:** 2028-10-31
- **Public key:** [UPDATARR_RELEASE_KEY.asc](UPDATARR_RELEASE_KEY.asc)

Compare the complete primary fingerprint before trusting this key. Importing a
public key does not by itself prove that it belongs to the named owner.

## Intended Release Proof

The same owner-controlled OpenPGP identity will be used for:

1. signed, annotated Git release labels; and
2. detached signatures for the exact source and package files people download.

Signing happens only after the reviewed source revision and release files are
frozen and their checksums are recorded. The private key is not copied into a
build container, package, repository or evidence bundle. Creating the key did
not authorize publishing a release, pushing a Git label or changing the
managed computer. The owner separately authorized signing the final local M7
release label and release files on 2026-11-01; that authorization still does
not permit publication or a push.

## Release Label Policy

Release candidates use signed, annotated Git labels in the form
`v<version>-rc.<number>`. A final release uses `v<version>`. A label is never
moved or reused after it identifies reviewed files; a correction receives a
new candidate number. The first local M7 candidate label is `v0.6.0-rc.1`; it
was rejected without moving or deleting it. The corrected candidate is
`v0.6.0-rc.2`.
The post-pilot interface, service-namespace and tray follow-up receives the new
immutable label `v0.6.0-rc.3`; RC2 is not moved or reused.
The M7.2 readiness corrections use immutable labels `v0.7.0-rc.1` through
`v0.7.0-rc.4`; only RC4 is the published current candidate.

## Rejected Local RC1

- **Label:** `v0.6.0-rc.1`
- **Commit:** `ee18e9a7f789404ece81488f150fd02e33837a42`
- **Signed files:** `updatarr-0.6.0.tar.gz`,
  `updatarr-0.6.0-1-any.pkg.tar.zst` and `SHA256SUMS`
- **Verification:** the label and all three detached signatures passed from a
  fresh keyring containing only the bundled public key

RC1 must not be published. Package inspection found a built-in demonstration
password in its installed runtime, browser and README. The signed label is not
moved or deleted; the corrected candidate receives the new label
`v0.6.0-rc.2` and new detached signatures.

The fresh keyring reports the public key as untrusted until the verifier
independently compares the complete fingerprint. That trust warning is
expected and is separate from the successful cryptographic signature check.

## Corrected Local RC2

- **Label:** `v0.6.0-rc.2`
- **Commit:** `660f4918ebc612e63953a0014199dfe481c100ef`
- **Label object:** `d46c9f88dc87b9f67d371351a899cc4767bbd63c`
- **Signed files:** `updatarr-0.6.0.tar.gz`,
  `updatarr-0.6.0-1-any.pkg.tar.zst` and `SHA256SUMS`
- **Verification:** the label and all three detached signatures passed from a
  fresh keyring containing only the bundled public key

RC2 remains a local candidate pending owner acceptance. These signatures do
not authorize a push, upload or publication.

## Local RC3 Follow-Up

- **Label:** `v0.6.0-rc.3`
- **Commit:** `1e734f9a7028e89774a9b8bf1ca025ed6eb09f8f`
- **Label object:** `39269ff4c47f4e88a8f5168eca1173cafd755889`
- **Package release:** `updatarr 0.6.0-2`
- **Signed files:** `updatarr-0.6.0.tar.gz`,
  `updatarr-0.6.0-2-any.pkg.tar.zst` and `SHA256SUMS`
- **Purpose:** replace the rejected RC2 service behavior and include the
  accepted local-test interface and tray follow-ups
- **Authorization:** owner authorized clean packaging, local signing and local
  installation on 2026-11-03
- **Verification:** the label, all three detached signatures and every checksum
  passed from a fresh keyring containing only the bundled public key

At that RC3 point, publication, remote push, service enablement at login,
notifier migration and live software updates still required separate
authorization. The owner later authorized the M7.2 Git publication recorded
below; the other gates did not change.

## Published M7.2 RC4

- **Label:** `v0.7.0-rc.4`
- **Commit:** `6bafa3dc670495cb90fa365f9f8f4103503e687c`
- **Label object:** `e414794f5893a5d0961c9e2c21f9c82105f03ce0`
- **Package release:** `updatarr 0.7.0-4`
- **Remote:** <https://github.com/soulctcher/Updatarr>
- **Verification:** the label, source, package, checksum signature and every
  checksum passed from a fresh public-key-only keyring

RC1 and RC2 failed their managed-host canaries without issuing readiness
evidence. RC3 issued valid evidence but the private user service could not
recognize host-root ownership in its restricted namespace. RC4 corrected that
mapping without weakening the normal-namespace root-owner check. Release-file
upload remains separate from the Git branch and label publication completed
here.

## Verify the Public Key

Inspect the bundled public key without importing it:

```bash
gpg --show-keys --with-fingerprint \
  docs/release/UPDATARR_RELEASE_KEY.asc
```

After comparing the full fingerprint above, import it if desired:

```bash
gpg --import docs/release/UPDATARR_RELEASE_KEY.asc
```

Verify a future signed Git release label:

```bash
git tag --verify <release-label>
```

Verify a future downloaded file and its detached signature:

```bash
gpg --verify <downloaded-file>.asc <downloaded-file>
```

Verification proves that the matching private key signed those exact bytes. It
does not replace review of the source, checksums, build evidence or software
bill of materials.

## Owner Recovery Material

GnuPG created a local revocation certificate for this primary fingerprint with
owner-only permissions. It and the private key remain in the owner's GnuPG
storage outside the project. They must never be committed or shared in chat.
The owner should make a separately protected offline backup before relying on
this key for a public release.
