# Release Signing

**Prepared:** 2026-11-01  
**Status:** corrected RC2 label and release-file signatures verify locally;
RC2 remains historical, and the owner authorized signing and locally installing
the reviewed follow-up as RC3 on 2026-11-03. Nothing has been pushed or
published.

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
- **Package release:** `updatarr 0.6.0-2`
- **Purpose:** replace the rejected RC2 service behavior and include the
  accepted local-test interface and tray follow-ups
- **Authorization:** owner authorized clean packaging, local signing and local
  installation on 2026-11-03

The label and release files must be verified before installation. Publication,
remote push, service enablement at login, notifier migration and live software
updates remain separate and unauthorized.

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
