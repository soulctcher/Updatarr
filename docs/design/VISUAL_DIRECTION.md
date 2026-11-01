# Updatarr visual direction

**Status:** accepted direction for Phase 0 prototypes  
**Decision:** Ultraviolet selected by the user on 2026-10-23

## Design intent

Updatarr should be immediately understandable beside Sonarr and Radarr without
looking like a reskin. The family resemblance comes from information
architecture and operational rhythm: persistent navigation, compact action
bars, dense comparison tables, filters, progress, history and settings. The
distinct identity comes from color, update-oriented iconography, typography and
the way update safety is visualized.

The visual subject is **controlled change**. Updatarr is not a storefront or a
generic server dashboard; it is an operations console that makes ownership,
risk, readiness and irreversible steps legible.

## Principles

1. **Show the update plan.** System update groups, separately managed updates,
   blockers and approval state should be more prominent than decorative totals.
2. **Dense, not cramped.** Tables are the default for comparison; summary cards
   appear only when they encode a genuinely different level of information.
3. **Color has one job at a time.** Brand, update-source identity, health, severity
   and selection cannot all reuse the same hue.
4. **Consequences precede confirmation.** Dependency, permission, reboot and
   source information appear before the primary action.
5. **Motion explains state.** Use motion for scan/progress/change confirmation,
   not ambient decoration; honor reduced-motion preferences.
6. **Plain operational language.** Use title case for page, section and card
   titles while keeping actions, statuses, instructions and body copy in
   sentence case. Preserve the official casing of acronyms and product names.
7. **Help without clutter.** Put explanations behind a small, raised circled
   information button. Show compact or wide panels on hover and keyboard focus
   without requiring a click. Pointer-opened panels sit to the right of the
   pointer in a viewport-level top layer so page content cannot cover them.
   Place a panel once when it opens; it must not chase the pointer as the user
   moves into it. Prefer a width and height that show the complete explanation,
   with reachable scrolling only when the viewport genuinely requires it. Keep
   current status, consequences and required next steps visible.
8. **Checklist before risk.** Present automated update-safety results as one
   issue-first checklist: what passed, what needs attention, what was not
   checked and what is unavailable. Technical detail is expandable. A status
   becomes a link only when Updatarr has a real in-app place where the user can
   take the action; informational statuses remain non-interactive badges.

## Selected palette: Ultraviolet

| Token | Value | Intended role |
| --- | --- | --- |
| Brand bright | `#A78BFA` | Logo mark, selected rail accent and highlights on dark surfaces |
| Brand strong | `#6D28D9` | Accessible primary control/focus accent on light surfaces |
| Ink | `#172033` | Primary light-theme text and dark structural elements |
| Rail | `#202736` | Persistent navigation background |
| Canvas | `#F4F6F8` | Light operational workspace |
| Dark canvas | `#111827` | Dark-theme workspace |
| Line | `#D7DDE6` | Light-theme rules and table structure |

Measured contrast: brand bright against dark canvas is **6.52:1**; brand strong
against white is **7.10:1**. Both pass WCAG AA for normal text in their intended
roles. Semantic success, warning, failure, pause and update-source identity use
separate colors plus text/icons; brand violet never carries status by itself.

Seerr and Cleanuparr occupy adjacent indigo/violet territory in the bounded
survey, but the user considers them insufficiently common to outweigh this
direction. Updatarr differentiates itself through the two-tone token pair,
controlled-change plan steps and update-specific mark rather than hue
alone. See the [*arr ecosystem research](../research/arr-ecosystem-visual-research.md).

## Other possible color directions

Each option provides a bright dark-surface accent and a stronger light-surface
control color. Contrast figures are calculated against `#111827` and white.

| Direction | Bright / strong | Contrast | Character | Tradeoff |
| --- | --- | --- | --- | --- |
| **Signal lime** | `#84CC16` / `#4D7C0F` | 8.98:1 dark / 4.99:1 white | Distinct, energetic, update-oriented | Nearest collision is Recyclarr leaf green; can resemble generic developer tooling |
| **Deep teal** | `#14B8A6` / `#0F766E` | 7.13:1 dark / 5.47:1 white | Trustworthy, infrastructure-oriented | Crowded by Sonarr, Lidarr, Notifiarr, Houndarr and Recyclarr docs |
| **Cobalt** | `#3B82F6` / `#1D4ED8` | 4.82:1 dark / 6.70:1 white | Familiar KDE/control-center energy | Crowded by Sonarr, Seerr, autobrr and Profilarr |
| **Signal rose** | `#F43F5E` / `#BE123C` | 4.83:1 dark / 6.29:1 white | Urgent and memorable | Can overstate danger and approach Readarr, Sportarr and Whisparr territory |

All four remain documented alternatives, but Ultraviolet is the selected
direction. Representative Overview, Updates and plan-review screens must
still validate the complete semantic palette rather than the brand swatches in
isolation.

## Semantic color separation

The final token system needs distinct accessible pairs for:

- success / current;
- warning / manual review;
- danger / destructive or failed;
- information / neutral activity;
- postponed / paused;
- focus and selection;
- update-source identity where color adds value.

Every state also needs text or iconography. Charts require patterns, direct
labels or accessible tables so they do not depend on hue alone.

## Typography

- Use the KDE/browser system sans stack with `Noto Sans` as the preferred Linux
  face. It is familiar on the target system, highly legible and avoids a webfont
  dependency for the administrative surface.
- Use one family across navigation, headings, forms and tables. Hierarchy comes
  from size, weight and spacing rather than decorative type switching.
- Use the system monospace stack only for logs, package identifiers and exact
  command evidence—not for generic metadata labels.
- Default body size: 14–16 px depending on density mode; compact tables may use
  13–14 px with adequate row height. Keep prose lines under roughly 80
  characters.
- Use tabular numerals for sizes, versions where appropriate, durations and
  statistics.

## Layout concept

Desktop:

```text
┌──────────── rail ────────────┬────────────────────────────────────────────┐
│ Updatarr                     │ Search…             scan state     account │
│                              ├────────────────────────────────────────────┤
│ Overview                     │ Updates                                    │
│ Updates                12    │ [All] [Native 8] [Flatpak 3] [Tools 1]    │
│ Catalog                      │                                            │
│ Activity                     │ ┌ system updates ──────── ready/review ─┐ │
│ System Health          1     │ │ dense sortable update table           │ │
│ Settings                     │ └────────────────────────────────────────┘ │
│                              │ update-plan summary / contextual detail    │
└──────────────────────────────┴────────────────────────────────────────────┘
```

Mobile:

```text
┌──────────────────────────────┐
│ Updatarr       checking  ⋮   │
├──────────────────────────────┤
│ Updates                      │
│ [All] [Native] [Flatpak] ›  │
│                              │
│ System updates · 8 updates  │
│ blocked by 1 paused item    │
│ [Review group]              │
│                              │
│ compact update rows         │
├──────────────────────────────┤
│ Overview Updates Activity ☰ │
└──────────────────────────────┘
```

Desktop content is left-aligned. Mobile replaces the persistent rail with a
small bottom set of frequent destinations plus a menu for the rest; it must not
compress the desktop rail into an icon-only mystery strip.

## Signature element

Spend visual distinctiveness on the **update-plan steps**: a compact horizontal
or vertical sequence showing check → review → confirm here → allow access when
needed → verify results, with update groups and blockers attached to the
relevant stage. This is
specific to Updatarr's job and more useful than a generic hero statistic or
gradient card.

## Self-critique before prototyping

- Violet can drift into a generic media-server or entertainment aesthetic.
  Counter that with calm neutral surfaces, package-manager-specific content and
  limited use of the accent.
- An *arr-like rail plus tables can become visual imitation. Updatarr's
  update-plan steps, source labels and safe-group presentation must establish
  its own interaction model.
- Dense tables can fail on mobile. Prioritize decisions and collapse secondary
  metadata into contextual detail rather than turning every row into a large
  generic card.
- Validate real warning, failure, paused and success states together in both
  themes before finalizing secondary semantic tokens.
