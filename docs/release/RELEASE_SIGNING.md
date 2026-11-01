# Release Signing

**Prepared:** 2026-11-01  
**Status:** owner-controlled release key created; no release label or file has
been signed or published

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
managed computer.

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
