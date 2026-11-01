# Release Asset Provenance

**Prepared:** 2026-11-01  
**Status:** initial M7 inventory; the project license is selected, while the
applicable generated-output terms remain unconfirmed

## Packaged Brand Asset

| Asset | Origin | Inputs | Local Processing | SHA-256 | Release State |
| --- | --- | --- | --- | --- | --- |
| `web/src/assets/updatarr-loop.png` | Generated for Updatarr with OpenAI image generation during M2 | Text request for a minimal circular arrow loop in metallic white on a transparent background; no external reference image | Stored as a 128×128 RGBA PNG; the Ultraviolet rounded square and sizing are applied by Updatarr interface styles | `0abf402bdd51a9913b6116f4630bd245e76353db4836885aa0e2dacb66838a69` | Project use is intended under AGPL-3.0-or-later; confirmation of the applicable generated-output terms is still required |

The generated copy emitted into the current browser build has the same digest
as the source asset. The exact image-generation model/version was not retained,
so this asset cannot be claimed as bit-for-bit regenerable from the prompt.
The current [official image-generation documentation](https://developers.openai.com/api/docs/guides/tools-image-generation)
describes creating and saving output but does not state the redistribution
rights that applied to this earlier in-product generation. That limitation
must remain in release evidence rather than being treated as permission.

## Interface Screenshots

Files under `docs/design/screenshots/` were captured from Updatarr's own local
prototype or production interface during milestone review. Their visual inputs
are first-party Updatarr code, simulated data and the generated logo above.
They are documentation evidence and are not installed as runtime artwork.

The screenshots may display names such as Arch, AUR, Flatpak, KDE, GitHub,
AMOLED and the theme names solely as interface text. No third-party logo file
is bundled in the screenshot source directory.

## Generated Browser Files

Files under `web/dist/` are generated from locked first-party browser source
and locked npm dependencies. They are excluded from Git by policy and rebuilt
for packaging. M7 release evidence must record the source revision, npm lock
digest, build command and resulting file manifest rather than describing built
files as independently authored assets.

## Fonts and External Artwork

The project currently bundles no font files and no third-party icon or logo
pack. Browser font fallbacks are selected from fonts already available on the
client system.

## Required Follow-Up

- Record the exact generated-output terms relied on for the logo, or replace it
  with a newly documented reproducible vector asset if that cannot be
  established confidently.
- Re-run the asset digest and package inventory checks for the reviewed release
  revision.

