# *arr ecosystem and visual research for Updatarr

Research date: 2026-10-23

## Executive conclusion

The authoritative Servarr family is **Sonarr, Radarr, Lidarr, Prowlarr, Readarr, and Whisparr**. Servarr describes them respectively as TV, movie, music, indexer, book, and adult-video automation applications. The wider “*arr stack” is informal and open-ended; none of the adjacent projects below should be presented as part of Servarr's stated six-app family. [Servarr's official wiki](https://wiki.servarr.com/) is the source for that boundary, while each adjacent product is identified from its own project.

The expanded comparison shows that cyan, blue, teal, conventional green, amber/orange, red, purple/violet, pink, burgundy, and monochrome are all substantially represented. No verified active project in this bounded survey uses lime/chartreuse as its canonical identity, but **Recyclarr's `#6DB753` leaf green is the nearest collision**. Updatarr's proposed `#84CC16` remains distinctly more yellow-green; it should not drift toward Recyclarr's medium green.

Color values below are representative accents extracted directly from official project logo assets. They are **not claimed to be formal brand standards** unless a project itself says so. Short hex and RGB values have been normalized to six-digit uppercase hex for comparison.

## Core Servarr family

| Application | Primary role | Representative accent | Evidence and extraction note |
| --- | --- | --- | --- |
| Sonarr | TV-series PVR/collection automation | `#00CCFF` cyan | Servarr identifies Sonarr with TV collections, while Sonarr calls itself an internet PVR for Usenet and torrents. The official SVG uses `#0CF` for its central mark and linework; normalized here to `#00CCFF`. [Servarr](https://wiki.servarr.com/) · [Sonarr site](https://sonarr.tv/) · [official SVG](https://raw.githubusercontent.com/Sonarr/Sonarr/develop/Logo/Sonarr.svg) |
| Radarr | Movie collection automation | `#FFC230` amber/yellow | Servarr identifies Radarr with movies. The official SVG explicitly fills its center mark with `#FFC230`. [Servarr](https://wiki.servarr.com/) · [Radarr site](https://radarr.video/) · [official SVG](https://raw.githubusercontent.com/Radarr/Radarr/develop/Logo/Radarr.svg) |
| Lidarr | Music collection automation | `#009252` green | Servarr identifies Lidarr with music; Lidarr describes itself as a music collection manager. `#009252` is the repeated chromatic fill in the official SVG. [Servarr](https://wiki.servarr.com/) · [official repository](https://github.com/Lidarr/Lidarr) · [official SVG](https://raw.githubusercontent.com/Lidarr/Lidarr/develop/Logo/Lidarr.svg) |
| Prowlarr | Indexer manager/proxy that syncs with other *arr apps | `#E66001` orange, representative | Servarr identifies Prowlarr as its indexer manager. Its illustrated official logo contains many orange and brown shades; `#E66001` is an exact SVG fill selected as a representative bright orange, not a declared brand token. [Servarr](https://wiki.servarr.com/) · [official repository](https://github.com/Prowlarr/Prowlarr) · [official SVG](https://raw.githubusercontent.com/Prowlarr/Prowlarr/develop/Logo/Prowlarr.svg) |
| Readarr | Book/e-book collection automation | `#8E2222` burgundy/red | Servarr identifies Readarr with books. `#8E2222` is the repeated red fill and stroke in the official SVG. Readarr has been retired, but its identity still matters when avoiding confusion with familiar *arr colors. [Servarr](https://wiki.servarr.com/) · [official retirement notice](https://wiki.servarr.com/en/readarr/installation/docker) · [official SVG](https://raw.githubusercontent.com/Readarr/Readarr/develop/Logo/Readarr.svg) |
| Whisparr | Adult-video collection automation | `#FF69B4` hot pink | Servarr identifies Whisparr with adult videos. The official SVG uses `rgb(255, 105, 180)` for the main disc; converted exactly to `#FF69B4`. [Servarr](https://wiki.servarr.com/) · [official repository](https://github.com/Whisparr/Whisparr) · [official SVG](https://raw.githubusercontent.com/Whisparr/Whisparr/v2-develop/Logo/Whisparr.svg) |

## Prominent adjacent applications

These projects are commonly deployed alongside Servarr software or use an *arr-style name, but they should not be presented as part of the official Servarr six.

### Inclusion boundary

This is a bounded visual-confusion survey, not an attempt to enumerate every repository whose name ends in “arr.” The comparison includes:

1. Every project in Servarr's official family, including retired Readarr, because those are the primary visual references.
2. The established adjacent baseline—Bazarr, Seerr, and Tdarr.
3. The specifically requested candidates—Notifiarr, Recyclarr, Maintainerr, Cleanuparr, Huntarr, Houndarr, Decluttarr, and autobrr—whether active or not, so none silently disappears from the assessment.
4. An otherwise unrequested adjacent project only when, at the research date, its first-party repository is public and not archived, shows a release or source activity within the preceding 12 months, directly complements/interoperates with the media-*arr stack or explicitly follows the Sonarr/Radarr product model, has at least 500 visible GitHub stars, and has a first-party visual identity relevant to color collision. Profilarr and Sportarr met that addition threshold.

Forks, unofficial mirrors, dashboard icon packs, one-off scripts, projects that merely contain “arr” coincidentally, and projects without a currently attributable first-party source are excluded from the active color comparison. Activity and GitHub adoption are point-in-time screening signals, not endorsements of quality or security. The Servarr wiki itself labels its broader companion-tool list as projects not maintained, developed, or supported by the *arr development team. [Servarr useful-tools page](https://wiki.servarr.com/useful-tools)

### Established adjacent baseline

| Application | Primary role | Representative accent | Evidence and caveat |
| --- | --- | --- | --- |
| Bazarr | Downloads and manages subtitles for Sonarr and Radarr libraries | Monochrome; no defensible unique hue | Bazarr's official site states the Sonarr/Radarr subtitle role. Its current official icon is essentially black and white, so assigning it a chromatic “primary color” would be speculative. [official site](https://www.bazarr.media/) · [official repository](https://github.com/morpheus65535/bazarr) · [official icon](https://raw.githubusercontent.com/morpheus65535/bazarr/master/frontend/public/images/logo128.png) |
| Seerr | Media discovery and request management | `#4F65F5` indigo and `#C395FC` lavender | Seerr's official repository describes the request-management role. Both exact colors appear in its official gradient SVG, so it is better represented as a pair than forced into one color. [official repository](https://github.com/seerr-team/seerr) · [official SVG](https://raw.githubusercontent.com/seerr-team/seerr/develop/public/logo_full.svg) |
| Tdarr | Distributed media transcoding/remuxing and health checking | `#00FFF9` cyan, with blue support colors | Tdarr's official repository describes its transcoding and health-check role. The standout logo fill is `#00FFF9`, alongside `#00B7FF` and `#1174F0`; its family therefore overlaps Sonarr's cyan. [official repository](https://github.com/HaveAGitGat/Tdarr) · [official SVG](https://raw.githubusercontent.com/HaveAGitGat/Tdarr/master/assets/tdarr-logo.svg) |

### Extended active comparison

“Active” here means that the official repository was public and not archived and showed a first-party release or source activity in the preceding 12 months. Dates and versions are snapshot evidence, not promises about future maintenance.

| Application | Role and status at 2026-10-23 | Representative accent | Evidence and extraction caveat |
| --- | --- | --- | --- |
| Notifiarr | Notification and integration client for a media-server/*arr stack. Active; official v0.9.7 was released 2026-08-30. | Cyan/teal family: `#13CBE8`, `#27A2D5`, `#00A094`; UI mint `#3CD2A5` | The official logo is multicolor, so no single canonical hex should be invented. These exact fills occur in the repository-owned SVG; the mint is an exact current UI token. [official repository](https://github.com/Notifiarr/notifiarr) · [v0.9.7](https://github.com/Notifiarr/notifiarr/releases/tag/v0.9.7) · [official SVG](https://github.com/Notifiarr/notifiarr/blob/main/frontend/src/assets/notifiarr.svg) · [official UI CSS](https://github.com/Notifiarr/notifiarr/blob/main/frontend/src/assets/app.css) |
| Recyclarr | Synchronizes TRaSH Guide settings into Sonarr and Radarr. Active; official v8.8.0 was released 2026-10-14. | Logo green `#6DB753`; documentation teal `#25C2A0` | `#6DB753` is the dominant non-transparent pixel color in the official raster logo, not a declared brand standard. The docs theme separately declares `#25C2A0`; the logo green is the relevant visual-collision value. [official repository](https://github.com/recyclarr/recyclarr) · [v8.8.0](https://github.com/recyclarr/recyclarr/releases/tag/v8.8.0) · [official logo](https://github.com/recyclarr/wiki/blob/master/static/img/recyclarr.png) · [official docs tokens](https://github.com/recyclarr/wiki/blob/master/src/css/_variables.scss) |
| Maintainerr | Applies configurable media-retention and collection-maintenance rules. Active; official v3.31.0 was released 2026-10-21. | Amber `#F59E0B` and orange `#E88F36` | Both exact colors are gradient stops in the official icon. White is another endpoint, not a separate identity hue. [official repository](https://github.com/Maintainerr/Maintainerr) · [v3.31.0](https://github.com/Maintainerr/Maintainerr/releases/tag/v3.31.0) · [official SVG](https://github.com/Maintainerr/Maintainerr/blob/development/apps/ui/public/logo_icon.svg) |
| Cleanuparr | Automates download-queue cleanup, blocklisting, and related maintenance. Active; official v2.10.12 was released 2026-10-18. | Logo purple `#430074`; current UI violet `#8B5CF6` / `#7C3AED` | The illustrated logo contains several closely related dark purples. `#430074` is a prominent exact fill; the brighter pair comes from the project's current UI variables. Purple/violet is therefore occupied even though the logo and UI values differ. [official repository](https://github.com/Cleanuparr/Cleanuparr) · [v2.10.12](https://github.com/Cleanuparr/Cleanuparr/releases/tag/v2.10.12) · [official SVG](https://github.com/Cleanuparr/Cleanuparr/blob/main/Logo/logo.svg) · [official UI tokens](https://github.com/Cleanuparr/Cleanuparr/blob/main/code/frontend/src/styles/_variables.scss) |
| Houndarr | Runs rate-controlled missing, cutoff, and upgrade searches across connected *arr instances. Active; official v1.13.3 was released 2026-09-19. | Current UI cyan `#22D3EE`, active/hover cyan `#06B6D4` | The official logo is raster and does not declare one vector brand value. The exact current design tokens are more defensible for collision checking, but should be called UI accents rather than a formal logo standard. [official repository](https://github.com/av1155/houndarr) · [v1.13.3](https://github.com/av1155/houndarr/releases/tag/v1.13.3) · [official logo](https://github.com/av1155/houndarr/blob/main/src/houndarr/static/img/houndarr-logo-dark.png) · [official design tokens](https://github.com/av1155/houndarr/blob/main/src/houndarr/static/css/tokens.css) |
| Decluttarr | Removes stalled, failed, redundant, orphaned, and otherwise unwanted downloads from *arr queues. Active; the official repository documents its V2 line and showed source activity in October 2026. | No defensible unique hue | No logo, favicon, SVG, or declared brand palette was found in the official repository tree. A color from a third-party dashboard-icon collection would not satisfy this research's source rule. [official repository](https://github.com/ManiMatter/decluttarr) |
| autobrr | Automates acquisition from IRC announces, RSS, and related feeds and can send matches to download clients or *arr applications. Active; official v1.89.0 was released 2026-10-21. | Blue `#4788C7`, with pale blue `#DFF0FE` | Both are exact fills in the official SVG; the darker blue is the representative identity accent. The project's stylization is lowercase `autobrr`, not “Autobrr.” [official repository](https://github.com/autobrr/autobrr) · [v1.89.0](https://github.com/autobrr/autobrr/releases/tag/v1.89.0) · [official SVG](https://github.com/autobrr/autobrr/blob/develop/web/src/logo.svg) |
| Profilarr | Manages and synchronizes Sonarr/Radarr configuration profiles. Active; it clears the additional-project prominence threshold and official v2.3.1 was released 2026-10-21. | Blue `#4A90E2`, with dark slate `#374151` / `#1F2937` | These are exact fills in the official logo SVG. Blue is the chromatic identity; the slates are support colors. [official repository](https://github.com/Dictionarry-Hub/profilarr) · [v2.3.1](https://github.com/Dictionarry-Hub/profilarr/releases/tag/v2.3.1) · [official SVG](https://github.com/Dictionarry-Hub/profilarr/blob/develop/src/lib/client/assets/logo.svg) |
| Sportarr | Sports PVR explicitly modeled on Sonarr/Radarr. Active; it clears the additional-project prominence threshold and official v4.1.10.1120 was released 2026-10-17. | Deep red `#B91C1C` | The project supplies multiple logo variants; `#B91C1C` is the exact fill in its official red SVG and is therefore representative rather than an asserted universal token. [official repository](https://github.com/Sportarr/Sportarr) · [v4.1.10.1120](https://github.com/Sportarr/Sportarr/releases/tag/v4.1.10.1120) · [official red SVG](https://github.com/Sportarr/Sportarr/blob/main/Logo/red/1024-red.svg) |

### Requested project without a current attributable source

| Application | Assessment | Color consequence |
| --- | --- | --- |
| Huntarr | The formerly official `github.com/plexguide/Huntarr.io` repository, project site, and official container source were unavailable when checked on 2026-10-23; the former repository returned HTTP 404. Independently preserved forks/copies cannot establish a current first-party identity. Huntarr is therefore recorded as formerly relevant but **not classified as an active official project** in this survey. | No currently verifiable first-party logo/accent. Excluded from active color-collision conclusions rather than assigning a color from an unofficial mirror. |

## Sonarr and Radarr interface language

The following observations come from visual inspection of first-party promotional screenshots. Those pages are useful evidence for the recognizable *arr visual grammar, but some screenshots are older than the current applications and should not be treated as pixel-perfect current UI specifications. Sonarr also announced a redesigned, more responsive v5 interface in October 2026, so Updatarr should borrow the family resemblance rather than freeze an old screenshot. [Sonarr v5 announcement](https://forums.sonarr.tv/t/sonarr-v5-beta/41099)

Common patterns visible in the official Sonarr and Radarr material:

- A persistent dark left rail carries the logo and primary navigation, leaving a wide, light content canvas. [Sonarr overview screenshot](https://raw.githubusercontent.com/Sonarr/sonarr.github.io/master/img/slider/overview.png) · [Radarr overview screenshot](https://raw.githubusercontent.com/Radarr/radarr.github.io/master/img/slider/overview.png)
- Content is operational and information-dense: sortable tables, compact icon actions, colored status marks, filters, legends, and progress indicators dominate rather than large decorative cards. [Sonarr table screenshot](https://raw.githubusercontent.com/Sonarr/sonarr.github.io/master/img/slider/table.png) · [Radarr table screenshot](https://raw.githubusercontent.com/Radarr/radarr.github.io/master/img/slider/table.png)
- Major collections support multiple views rather than one prescribed layout. Both official sites explicitly advertise multiple library views. [Sonarr site](https://sonarr.tv/) · [Radarr site](https://radarr.video/)
- A calendar is a first-class navigation destination and uses small status colors plus a legend to communicate many scheduled items at once. [Sonarr calendar screenshot](https://raw.githubusercontent.com/Sonarr/sonarr.github.io/master/img/features/calendar.png) · [Radarr calendar screenshot](https://raw.githubusercontent.com/Radarr/radarr.github.io/master/img/features/calendar.png)
- Manual search is a dense comparison table with decision-relevant columns and per-row actions. [Sonarr manual-search screenshot](https://raw.githubusercontent.com/Sonarr/sonarr.github.io/master/img/features/manualsearch.png) · [Radarr manual-search screenshot](https://raw.githubusercontent.com/Radarr/radarr.github.io/master/img/features/manualsearch.png)
- Updates and release notes are managed inside the app, with current-version state visually separated from the changelog. Both product sites advertise this behavior. [Sonarr updates screenshot](https://raw.githubusercontent.com/Sonarr/sonarr.github.io/master/img/slider/updates.png) · [Radarr updates screenshot](https://raw.githubusercontent.com/Radarr/radarr.github.io/master/img/slider/updates.png)
- Settings are reached from the sidebar, divided into sub-sections, and use an advanced-setting reveal plus explicit save state. [Radarr settings documentation](https://wiki.servarr.com/radarr/settings)
- Dark mode and responsive behavior are part of the current direction: Sonarr v4 introduced dark mode, while the official v5 announcement calls out redesigned navigation, layouts, tables, dialogs, responsiveness, and accessibility. [Sonarr v4 announcement](https://forums.sonarr.tv/t/sonarr-v4-released/33089) · [Sonarr v5 announcement](https://forums.sonarr.tv/t/sonarr-v5-beta/41099)

### What Updatarr should inherit

Updatarr should use the *arr information architecture and interaction rhythm, not copy logos, trademarks, or source assets:

- Persistent responsive side navigation for Overview, Updates, Catalog, Activity/History, System Health, and Settings.
- A slim top action/search area, dense sortable tables, explicit filters, compact status badges, and clear row-level actions.
- Multiple views where they genuinely help: compact update table as the default, with optional source-grouped or card summaries.
- Detail pages or drawers that preserve context, and dialogs for focused configuration or transaction confirmation.
- Theme-aware light/dark presentation with Updatarr's own lime identity and accessible semantic colors that remain distinct from the brand accent.
- Release notes, transaction history, task progress, health warnings, and manual intervention requirements surfaced as first-class operational state.

## “Broadcast a web page” architecture implications

The *arr management model is a long-running service that serves a browser interface. Sonarr directs users to its interface at `http://localhost:8989`; Radarr does the same at `http://localhost:7878`, and both describe substituting the host address for remote access. [Sonarr installation page](https://sonarr.tv/) · [Radarr installation page](https://radarr.video/)

For Updatarr, this changes the earlier desktop-first assumption:

1. **Make the local service the product's authority.** One continuously running unprivileged `updatarr` service should own inventory, plans, policy, history, scheduling, and live task state.
2. **Serve a responsive SPA and versioned API from the same origin.** The primary management surface should work in any modern browser. A KDE launcher/tray component can open or embed that same local page rather than implement a separate feature set.
3. **Default to loopback-only binding.** LAN listening should be an explicit setting. Radarr exposes bind address, port, URL base, allowed hosts, SSL, and reverse-proxy-related controls; Updatarr needs equivalent deployment controls without copying its implementation. [Radarr host and security settings](https://wiki.servarr.com/radarr/settings)
4. **Require authenticated HTTPS before non-loopback access.** Current Sonarr and Radarr require authentication, and Radarr warns that forwarded-client headers must only be trusted from configured proxy networks. Updatarr should require HTTPS directly or through a trusted TLS-terminating proxy, mandatory credentials, secure session cookies, CSRF protection, login throttling, explicit trusted-proxy configuration, and no unauthenticated mutation endpoints. [Sonarr forced-authentication FAQ](https://wiki.servarr.com/sonarr/faq) · [Radarr host and security settings](https://wiki.servarr.com/radarr/settings)
5. **Keep privilege out of the web process.** The web-facing service remains unprivileged. Approved mutations pass immutable plans through the narrow Polkit/helper boundary already required by the Updatarr safety model.
6. **Support reverse proxies deliberately.** A configurable URL base, allowed-host validation, correct forwarded-header handling, SSE compatibility for live progress, and documented proxy examples should be planned from the beginning. Add WebSocket support only if a later requirement cannot be met by HTTP commands plus SSE.
7. **Do not equate LAN reachability with Internet-safe exposure.** The initial supported posture should be loopback or trusted LAN/VPN. Direct public exposure should remain unsupported until TLS, authentication, session handling, proxy trust, audit logging, and security testing are complete.

## Palette recommendation

> **Decision note (2026-10-23):** This research originally recommended the
> least-crowded lime direction. The user selected Ultraviolet (`#A78BFA` /
> `#6D28D9`) after weighing actual familiarity with Seerr and Cleanuparr. The
> survey below remains the evidence record rather than being rewritten to make
> the selected choice appear inevitable.

Across the bounded expanded survey, the occupied accent families are:

- **Cyan/teal:** Sonarr, Tdarr, Notifiarr, and Houndarr.
- **Blue/indigo/lavender:** autobrr, Profilarr, and Seerr.
- **Conventional green:** Lidarr and, most importantly for comparison, Recyclarr's `#6DB753`.
- **Amber/orange:** Radarr, Prowlarr, and Maintainerr.
- **Red/burgundy:** Sportarr and retired Readarr.
- **Purple/violet:** Cleanuparr.
- **Pink:** Whisparr.
- **Monochrome or no defensible project hue:** Bazarr and Decluttarr.

No verified active project here owns a distinctly **yellow-green/chartreuse** identity. Use **Updatarr lime** as a viable but deliberately yellow-shifted family:

- Brand/highlight candidate: `#84CC16`
- Dark accessible candidate for light surfaces: `#4D7C0F`
- Keep the primary hue visibly more yellow than Recyclarr's `#6DB753`; do not evolve it toward a medium leaf green.
- Do not use lime itself as a success status; reserve a separate semantic green so brand and system health cannot be confused.
- Validate final tokens against WCAG contrast targets in both light and dark themes before adoption.

The expanded research weakens the earlier phrase “clearly unoccupied”: lime is still the least-crowded practical direction, but it sits next to Recyclarr in hue space. This recommendation remains provisional until an Updatarr logo and representative screens are tested together. Hue distinctness alone does not establish a complete, accessible visual system.
