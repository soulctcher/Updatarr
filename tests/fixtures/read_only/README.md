# Read-only update-source fixtures

These small fixtures preserve output shapes observed on the target EndeavourOS
host on 2026-10-24. They are deliberately reduced and sanitized: they support
parser and safety-contract development without publishing device identifiers,
serial numbers, local paths or a complete personal software inventory.

They are not proof that an update is available. Empty output is meaningful and
must remain distinct from a failed command, a missing tool or information that
needs a refresh.

| Fixture | Observed command family | Important contract detail |
| --- | --- | --- |
| `pacman-foreign.txt` | `pacman -Qm` | Whitespace-separated name and version; “foreign” does not prove AUR origin. |
| `flatpak-apps.tsv` | `flatpak list --app --columns=...` | Installation scope, origin and branch are part of identity. |
| `flatpak-remotes.tsv` | `flatpak remotes --show-disabled --columns=...` | Disabled one-off origins must not be silently enabled or omitted. |
| `fwupd-devices-shape.json` | `fwupdmgr get-devices --json` | Device records have optional and device-specific fields. IDs are removed. |
| `npm-globals.json` | `npm ls --global --depth=0 --json` | npm lists packages but does not establish ownership; pacman ownership is a separate check. |
| `toolchains.txt` | rustup, Cargo, fnm, uv and DKMS read-only queries | Empty stdout can be a successful result; some tools report an empty result on stderr. |
| `appimage-candidates.tsv` | Bounded `find` plus `pacman -Qqo` | Discovery is not update support; candidates are never executed by the probe. |

The capture command registry and redaction boundary live in
[`scripts/read_only_capability_probe.py`](../../../scripts/read_only_capability_probe.py).
Malformed, hostile, timeout and unavailable fixtures belong to M1 alongside
the parsers that consume them.
