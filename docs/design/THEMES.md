# Updatarr theme system

**Status:** accepted Phase 0 direction; token prototype implemented  
**Brand:** Ultraviolet remains constant across every theme

Themes change the reading environment, not the meaning of the interface.
Update-source state, warnings, failures, success, selection and Updatarr's identity
must remain recognizable in every profile. No theme may turn brand violet into
a success or error signal.

## Included profiles

| ID | Display name | Mode | Character |
| --- | --- | --- | --- |
| `system` | System | Adaptive | Default; follows the browser/OS light or dark preference. |
| `light` | Light | Light | Neutral operational canvas and dark structural rail. |
| `dark` | Dark | Dark | Slate workspace with restrained contrast. |
| `amoled` | AMOLED | Dark | True-black canvas and rail for OLED displays. |
| `solarized-light` | Solarized Light | Light | Warm cream and blue-green neutrals. |
| `solarized-dark` | Solarized Dark | Dark | Deep blue-green workspace with warm text. |
| `github-light` | GitHub Light | Light | Cool gray, code-oriented neutral surfaces. |
| `github-dark` | GitHub Dark | Dark | Deep neutral gray with crisp table structure. |
| `norse` | Norse | Dark | Custom Updatarr forest, stone and ice profile. |
| `nord` | Nord | Dark | Polar blue-gray workspace. |
| `gruvbox-light` | Gruvbox Light | Light | Warm parchment and brown neutrals. |
| `gruvbox-dark` | Gruvbox Dark | Dark | Warm charcoal and sand neutrals. |
| `dracula` | Dracula | Dark | Cool charcoal with high-legibility pale text. |
| `catppuccin-latte` | Catppuccin Latte | Light | Soft cool light surfaces. |
| `catppuccin-mocha` | Catppuccin Mocha | Dark | Soft deep plum-gray surfaces. |
| `sepia` | Sepia | Light | Low-glare warm reading profile. |
| `midnight` | Midnight | Dark | Near-navy, low-luminance workspace. |
| `high-contrast` | High Contrast | Dark | Black/white structural profile for maximum separation. |

Names that refer to established palette families describe compatible,
locally-defined token profiles; Updatarr does not import their stylesheets,
logos or runtime assets. Norse, Sepia and Midnight are Updatarr profiles.

## Token contract

Every profile supplies the same semantic interface:

- canvas, surface, top bar, rail, rail-hover, rule, primary ink and muted ink;
- light- or dark-surface brand accent and a visible focus indicator;
- status foreground/background pairs for success, warning and failure;
- selected-group, independent-group, blocked-note and table-rule surfaces;
- a correct browser `color-scheme` so native controls render coherently.

The fixed brand pair remains `#A78BFA` on dark surfaces and `#6D28D9` on light
surfaces. A profile can tune neutral surroundings but cannot substitute a new
brand hue. Status always uses wording or an icon in addition to color.

## Selection and persistence

- `system` is the default and resolves with `prefers-color-scheme` in the
  browser; it does not guess from server time or KDE configuration.
- A signed-in user's explicit profile becomes an appearance preference in M1,
  selected under **Settings → Appearance**. It is presentation-only and cannot
  alter update-source or installation behavior.
- The Phase 0 prototype stores its choice only in the URL (`?theme=<id>`) so it
  remains disposable and easy to review; it writes no preference database.
- Unknown or retired IDs fall back to `system`. Theme schema changes are
  versioned, and migrations never block access to update controls.
- Theme choice belongs in Settings, not the production top bar. The future tray
  uses desktop theme icons and is not required to mirror the web canvas.

## Acceptance matrix

Before M1's theme work closes:

- every included profile renders Overview, Updates/review, Settings, dialogs,
  anchored hover/focus help panels, tables and empty/loading/stale/error states;
- body text meets WCAG AA, focus and non-text state indicators meet their
  applicable contrast targets, and 200% zoom remains usable;
- desktop, 681/680 breakpoint boundaries, 390 px and 320 px widths have no
  document-level horizontal overflow;
- keyboard selection, system light/dark changes, reduced motion and a missing
  stored theme are exercised;
- charts and code/log views use tokenized colors and accessible non-color
  legends rather than hard-coded palette values.

The prototype currently proves token switching and representative shell
rendering, not full production persistence or page coverage. Retained evidence
and findings are in the [prototype review](PROTOTYPE_REVIEW.md).
