# M7 RC3 Signing and Local Installation — 2026-11-03

## Authorization and Boundary

The owner authorized the remaining RC3 steps, including clean packaging,
signing and local installation. This did not authorize publication, remote
push, user-service enablement at login, notifier migration, Octopi removal or
any software update through Updatarr.

## Frozen Source and Repeated Build

- Commit: `1e734f9a7028e89774a9b8bf1ca025ed6eb09f8f`
- Signed label: `v0.6.0-rc.3`
- Label object: `39269ff4c47f4e88a8f5168eca1173cafd755889`
- Source archive SHA-256:
  `6f05f0e9068c49a9aa40ded310807869fefda2cd48659b88a789112f72149d24`
- Installed package SHA-256:
  `07062442b9cdc6cbe4bab6d88afa09c407223a057f69c29e74f02de6632470fc`
- Repeated package SHA-256:
  `c473b5872cf008d2e1cb3be663c225cb600fa63fcb7319bdc8fd3f7e58ae5cb7`
- Normalized 219-file payload SHA-256:
  `cd7cd87c10b266bd89ea6db958b46a688a57754e889f699d3c2d051c101a98d9`
- Builder inventory SHA-256:
  `a2cb2bf8ca6db33e144040b4e3a6fc74219f2bad6e9d68671b34362e03b682d0`

Two networkless, capability-free, read-only-root builds ran with a 2 GiB memory
limit. Their normalized payloads and builder inventories are identical. Package
inspection found the two disabled-by-default user units, the new tray
preferences Module and rebuilt About interface. It found no enablement link,
XDG autostart entry, install script, Polkit rule, built-in demonstration
password or private signing material.

The disposable lifecycle installed release 1, started the loopback application,
backed up and restored state, upgraded to release 2, downgraded, uninstalled and
preserved private user state. Its log SHA-256 is
`4b013450cc40479a3dc2918578098e5f3d69e6bd5a4efa0fd1dbdbe8bab37482`.

## Signing and Independent Verification

The owner-controlled Ed25519 signing subkey
`5BD6 C0A8 D98B 655A EAF0 5EC2 E689 CC8D 9BBB 0AA4` signed the annotated Git
label, source archive, package and checksum list. A fresh keyring containing
only the bundled public key verified all four signatures and every listed file.
The checksum-list SHA-256 is
`7fb21f2f88aa34f7b338068534680e268b022d2be8e96ea2a9716fc63161c087`.

The release files remain local under `build/m7-release-v0.6.0-rc.3/`; nothing
was pushed, uploaded or published.

## Managed-Computer Installation

Before installation, the transient pilot and tray were stopped. The live
database and a new owner-only offline backup both returned `ok` from SQLite's
integrity check. The configuration and backup hashes were recorded without
printing the configuration contents.

The simulated pacman transaction contained only Updatarr. A graphical Polkit
prompt authorized pacman to upgrade `updatarr 0.6.0-1` to `0.6.0-2`; no package
was added or removed. `pacman -Qkk updatarr` then verified all 257 package files
without alteration. The private configuration hash and database integrity
remain unchanged.

## Live Read-Only Verification

- The packaged core is active at `127.0.0.1:8788`, serves the new browser
  bundle and remains disabled at login.
- `PrivateTmp=yes`, `NoNewPrivileges=yes` and `UMask=0077` remain active.
- A short-lived read-only service with the same `PrivateTmp=true` boundary
  accepted `/usr/bin/pacman` as package-owned and completed both pacman probes.
- The packaged tray is active, remains disabled at login and registered
  `updatarr-tray` with Plasma using a 32 × 32 dynamic icon pixmap.
- Installed files contain the tray Settings action, muted green/red icon colors,
  reminder controls and requested About strings.
- All 33 before/after read-only host probes are semantically identical after
  normalizing the expected Updatarr version change and AUR result ordering.
- Octopi remains installed and its notifier process and autostart-file checksum
  are unchanged.

The tray may initially show neutral gray until a signed-in browser requests the
current Overview. This is intentional: gray means no status has yet been handed
to the restarted tray, while red or green requires a recorded result.

## Current State and Remaining Gates

`updatarr.service` and `updatarr-tray.service` are manually active for owner
testing and both remain disabled at login. The transient pilot is inactive.
Service enablement, notifier migration, release publication, remote push, live
AUR and every software-changing Updatarr action remain separately gated.
