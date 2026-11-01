# M2 catalog, policy and history research

**Captured:** 2026-10-25  
**Scope:** M2 catalog search, saved choices, notes/advisory provenance and
imported history  
**Host changes:** none; research and read-only HTTP requests only

## Outcome

M2 can implement a useful catalog and history model without pretending that all
sources provide the same facts. The important boundaries are:

- an Arch web result describes an official Arch repository package, but the
  host's configured pacman databases remain the authority for whether that
  package is currently available to this computer;
- AUR RPC metadata helps people find a user-submitted build recipe; votes,
  popularity and maintainer state are context, not proof that the recipe is
  safe;
- Flatpak identity includes installation scope and remote, and catalog search
  must not silently refresh metadata or enable a disabled remote;
- imported pacman and Flatpak events are external history, not Updatarr plans,
  approvals or proof of one successful all-or-nothing transaction; and
- every description, news item, advisory and external URL remains untrusted
  display data even when it came from an official source.

These conclusions fit the existing `Software`, `SelectionPolicy` and
`ExternalHistoryEvent` models. They also preserve the M2 gate: no metadata
refresh, remote change, package change or other host mutation is required.

## Catalog behavior

### Official and configured pacman repositories

Arch provides JSON package detail, file-list and search interfaces. Search
accepts name/description text, exact name, repository, architecture, maintainer,
packager and flagged-state filters. Detail identity is
`repository/architecture/package`. The current search response is versioned and
paginated; a read-only request on 2026-10-25 returned response version `2`, a
page limit of `250`, and package facts including repository, architecture,
version, description, dependencies, sizes, maintainer and timestamps.
[Official repository web interface](https://wiki.archlinux.org/title/Official_repositories_web_interface)
· [live JSON search example](https://archlinux.org/packages/search/json/?q=pacman)

The web interface covers Arch's repositories, not every repository configured
in `/etc/pacman.conf`. Pacman's `-Ss` operation searches package names and
descriptions in the locally synchronized databases. Therefore Updatarr should
model these as two related facts:

1. `catalog_origin=arch_web` means an official Arch web result.
2. `installability=confirmed` is set only when a matching package identity is
   present in an enabled local sync database for the requested architecture.

An Arch web result that is absent locally remains searchable but must say
**Not available from this computer's configured sources**. A package found only
in an EndeavourOS or other configured repository is labeled with that actual
repository; it must not be relabeled as an official Arch result. Search and
detail responses need a captured time and response/schema version, and failed,
cut-off or malformed pages produce an explicit incomplete result rather than an
empty successful result. [pacman sync search](https://man.archlinux.org/man/pacman.8.en#SYNC_OPTIONS_(APPLY_TO_-S))

M2 must not refresh `/var/lib/pacman/sync`. It may search the already configured
local databases and query the official HTTPS interface, with bounded time,
response size, page count and result count. Installing any result belongs to a
later milestone and must re-check the current configured source.

### AUR

The official AUR RPC v5 interface supports `search` and multi-package `info`
requests and returns JSON with a top-level version, type, result count and
results. Search defaults to name plus description and can search fields such as
name, maintainer, dependency, provider, conflict and group. `info` adds
dependency, conflict, provider, replacement, license and keyword fields.
[AUR RPC v5 interface](https://wiki.archlinux.org/title/Aurweb_RPC_interface)
· [live RPC example](https://aur.archlinux.org/rpc/v5/info?arg%5B%5D=yay)

The published operating limits affect the adapter design:

- search text must be at least two characters;
- searches that would return 5,000 or more results fail;
- the service allows at most 4,000 requests per IP each day; and
- the official server's request-target limit means large `info` lookups must be
  split; the documentation estimates roughly 200 package names per request.

Use a small debounced request rate, cache successful responses by normalized
query, honor errors as errors, and never retry enough to consume the daily
allowance. The official metadata archives support `ETag` and `Last-Modified`
and are better than repeated bulk RPC calls, but M2 search does not need to
download a complete archive. [AUR RPC limitations and archives](https://wiki.archlinux.org/title/Aurweb_RPC_interface#Limitations)

`Maintainer`, `OutOfDate`, `NumVotes`, `Popularity`, `FirstSubmitted` and
`LastModified` are descriptive metadata. None is a trust verdict. AUR contains
user-submitted `PKGBUILD` files rather than official binary packages, and the
Arch submission guidance says those recipes are unofficial and not thoroughly
vetted. The interface must therefore use the visible source label **AUR
(user-submitted)** and retain the package-base name, recipe URL, maintainer
state and last-modified time without turning any of them into a “safe” badge.
[AUR submission guidance](https://wiki.archlinux.org/title/AUR_submission_guidelines)

An RPC result also does not prove that an installed foreign package came from
the AUR. Ownership remains unresolved until separate evidence establishes it.
If a package disappears, is orphaned, is marked out of date, or returns omitted
fields, those are distinct states rather than a blank description or an
invented update.

### Flatpak

Flatpak has separate per-user, default system-wide and named system-wide
installations. `flatpak remotes` lists repositories from both common scopes by
default and supports explicit `--user`, `--system` and `--installation=NAME`
selection. Consequently the stable catalog identity is at least
`installation_scope + installation_name + remote + ref + architecture + branch`;
a remote name by itself is not unique enough.
[Flatpak command reference](https://docs.flatpak.org/en/latest/flatpak-command-reference.html#flatpak-remotes)

`flatpak search` uses AppStream data and may automatically update that data when
it is at least a day old. That automatic refresh conflicts with the current M2
authorization. The live adapter must therefore stay disabled unless a tested
read-only path can guarantee that it will not refresh metadata. M2 can implement
and test search with fixtures, and may show already cached, explicitly scoped
remote data only after proving the selected command cannot contact or modify a
remote. It must not describe a skipped live query as “no results.”
[flatpak search](https://docs.flatpak.org/en/latest/flatpak-command-reference.html#flatpak-search)

Remote state changes search meaning. Flatpak documents that a non-enumerated
remote is not used to list applications, and a disabled remote is not
automatically updated from. Updatarr must preserve both states and must never
enable, enumerate or otherwise change a remote to make search work. This is
especially important for disabled local bundle origins.
[flatpak remote settings](https://docs.flatpak.org/en/latest/flatpak-command-reference.html#flatpak-remote-modify)

Search results need an explicit remote and scope choice. If the same application
ID is present in user and system scopes, or in more than one remote, those are
separate choices. A display name collision with a pacman package is an
alternative, not a duplicate identity.

## Saved choices and native safety

Updatarr should keep an append-only `PolicyEvent` and derive the current rule.
Each rule records its exact target, kind, actor, reason, creation time, optional
expiry, last application and current state. The four user-facing choices remain
different:

| Choice | Saved meaning | Provider change in M2 |
| --- | --- | --- |
| Turn off an update source | Updatarr does not check or plan that source; its last data becomes **Needs refresh** | None |
| Postpone | Keep the matching update visible but out of plans until a date or manual resume | None |
| Skip this version | Suppress one exact detected version; a different version appears again | None |
| Pause updates | Prevent matching software from entering a plan until resumed, while keeping the reason visible | None |

Rules match the complete source-qualified identity. Missing or expired targets
do not broaden into name-only matches. A skip-version comparison for pacman
packages must use libalpm's version rules (including epoch), not lexical string
ordering. [vercmp behavior](https://man.archlinux.org/man/vercmp.8.en)

Arch supports full system upgrades, not arbitrary partial upgrades. Arch's
maintenance guidance also warns that `IgnorePkg` and `IgnoreGroup` can create
the same partial-upgrade risk. Therefore a postpone, skip or pause affecting one
native repository update blocks or postpones the whole native upgrade group; it
never produces an executable subset. Updatarr must not edit `pacman.conf` to
save a preference. [Arch partial-upgrade guidance](https://wiki.archlinux.org/title/System_maintenance#Partial_upgrades_are_unsupported)

Flatpak masks are real provider state. Flatpak documents masks as ref patterns
that prevent automatic update or installation, with separate user and system
scope. Updatarr should read existing masks and label their source as **Flatpak
setting**. Creating or removing a mask is a future typed mutation, not an M2
settings write. An Updatarr pause remains an app policy unless a later approved
plan explicitly changes the provider mask.
[Flatpak masking](https://docs.flatpak.org/en/latest/tips-and-tricks.html#masking)

## Notes, news and advisories

### Provenance

Every item needs a stable source ID, source class, canonical HTTPS URL, source
item ID when available, published/updated time, fetched time, content hash and
parse status. The UI must display the source and distinguish these classes:

| Source | Meaning | Matching rule |
| --- | --- | --- |
| Arch news feed | Posts from Arch Linux development staff, including manual-intervention notices | General notice unless the source provides an exact package reference |
| Arch Security Tracker | Package advisory with Arch advisory/group IDs, affected/fixed versions, severity and status | Exact pacman package name plus libalpm version comparison |
| EndeavourOS Important-news | Distribution-maintained operational notice | Preserve its stated `Relates to` value; do not invent a package match |
| Package or AppStream description | Catalog description, not a security advisory or release note | Exact catalog identity only |

Arch explicitly tells users to read its news before upgrading because unusual
manual intervention is announced there, and provides an official news RSS feed.
The feed should be the machine-readable Arch news source; the canonical article
remains the user-visible link. [Arch update guidance](https://wiki.archlinux.org/title/System_maintenance#Read_before_upgrading_the_system)
· [official Arch feeds](https://archlinux.org/feeds/)

The Arch Security Tracker exposes advisory IDs, package names, affected and
fixed versions, severity, status and related vulnerability groups. Preserve the
tracker's own status and severity; do not infer either from news wording. A
tracker request or parse failure yields **Not checked**, not “no advisories.”
[Arch Security Tracker](https://security.archlinux.org/)
· [published advisories](https://security.archlinux.org/advisory)

The EndeavourOS team's `Important-news` repository is an official
distribution-owned source containing date, description, additional remarks and
what the notice relates to. It is Markdown maintained in Git, not a stable JSON
API. Treat parser breakage as a source error, retain the upstream canonical
link, and do not scrape unrelated forum posts as equivalent notices.
[EndeavourOS Important-news](https://github.com/endeavouros-team/Important-news/blob/main/README.md)

### Safe display

Source ownership does not make content safe HTML. Updatarr should store a
normalized plain-text title and body, keep the original bytes only outside the
rendering path if diagnostics require them, and render text through normal
React interpolation. It must not pass provider HTML, Markdown output, package
descriptions or log text to `dangerouslySetInnerHTML`. React warns that
untrusted input there creates an XSS risk.
[React common component security note](https://react.dev/reference/react-dom/components/common#dangerously-setting-the-inner-html)

Links are separate data. Accept only canonical `https` links from the expected
source host or a narrowly defined package upstream field, validate the parsed
scheme and host, show external-link behavior, and add `rel="noopener noreferrer"`
when opening another tab. Never render event attributes, inline SVG, remote
images or `javascript:`/`data:` URLs from source content. OWASP recommends text
sinks for untrusted strings and explicit validation of URL schemes.
[OWASP XSS prevention guidance](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)

When a source does not provide release notes or a changelog, the API returns an
explicit `not_available` state. A package description, AUR last-modified time,
Flatpak commit log or general news post must not be relabeled as release notes.

## Imported history

### Pacman

Pacman's configured `LogFile` defaults to `/var/log/pacman.log`. Current
libalpm writes an ISO-8601 local timestamp, a caller prefix, and an action. Its
source emits these package facts:

- `installed NAME (VERSION)`;
- `reinstalled NAME (VERSION)`;
- `upgraded NAME (OLD -> NEW)`;
- `downgraded NAME (OLD -> NEW)`; and
- `removed NAME (VERSION)`.

[pacman log implementation](https://gitlab.archlinux.org/pacman/pacman/-/blob/master/lib/libalpm/log.c)
· [package action logging](https://gitlab.archlinux.org/pacman/pacman/-/blob/master/lib/libalpm/add.c#L639)
· [removal logging](https://gitlab.archlinux.org/pacman/pacman/-/blob/master/lib/libalpm/remove.c#L721)
· [pacman.conf LogFile](https://man.archlinux.org/man/pacman.conf.5.en#OPTIONS)

The official `paclog-pkglist` utility supports both newer lines with a caller
field and older lines without one. That is evidence that an importer must not
assume one timeless line shape. It also confirms that install, upgrade,
downgrade and removal entries can reconstruct package state, while unknown
lines should be ignored without being reinterpreted.
[paclog-pkglist source](https://gitlab.archlinux.org/pacman/pacman-contrib/-/blob/master/src/paclog-pkglist.sh.in)
· [paclog-pkglist manual](https://man.archlinux.org/man/extra/pacman-contrib/paclog-pkglist.8.en)

Import each recognized package action as an external event. Preserve caller,
timestamp, action, exact versions, source path and a deterministic deduplication
key. A practical key is the source kind plus a hash of the canonical parsed
fields and stable source-position evidence; duplicate identical lines at
different positions must remain distinct because reinstalling the same version
twice is possible. Re-import must be idempotent across an unchanged file and
safe across append, truncation and rotation.

Do not claim that adjacent lines form an atomic transaction or that a command
succeeded overall. Pacman logs a `Running ...` command line, action facts and
hook/error messages, but exposes no durable transaction ID in this text format.
Package action facts may be grouped visually by a conservative import batch,
but the group label must say **Imported pacman activity**, not **Updatarr update
run**.

### Flatpak

`flatpak history` reports installs, updates and removals for applications and
runtimes. It combines user and system installations by default, supports
explicit scope selection, and reads its records from the systemd journal using
a documented message ID. Journal retention and access therefore determine how
complete the import can be.
[flatpak history](https://docs.flatpak.org/en/latest/flatpak-command-reference.html#flatpak-history)

Import Flatpak history separately for user, default system and every supported
named installation so scope is never guessed. Preserve operation, ref,
architecture, branch, old/new commit when supplied, remote when supplied and
journal cursor or other stable source evidence. If the journal is unavailable,
permission-limited, rotated or begins after the requested range, history is
**Incomplete** with the reason recorded; it is not empty or complete.

### Completeness and ownership

Every import batch records `complete`, `incomplete` or `failed`, the requested
range, observed first/last source positions, count, skipped-line count and
reason. Imported events always carry `origin=external`. They never imply:

- an Updatarr account requested the action;
- Updatarr built or approved a plan;
- local confirmation or administrator authorization occurred; or
- the current installed state still matches the historical event.

Current inventory remains the authority for present state. History is evidence
of prior activity only.

## M2 implementation contract

| Area | Required behavior | Required negative evidence |
| --- | --- | --- |
| Search identity | Preserve source, repository/remote, scope, architecture and branch | Same name across sources/scopes never collapses |
| Search truth | Report stale, incomplete, unavailable and failed separately from zero results | Timeout, cutoff, schema drift and disabled remote fixtures |
| AUR context | Show user-submitted label and raw trust metadata without a safety verdict | Missing maintainer, out-of-date, malicious description and 5,000-result error |
| Policy | Append events; derive exact current rule; expire deterministically | Name-only collision, expired rule, changed version and wrong scope do not match |
| Native safety | Any native exclusion blocks/postpones the full native group | No subset plan and no `IgnorePkg` write path |
| Provider settings | Detect Flatpak masks and disabled remotes without changing them | No enable, enumerate, mask or unmask command in M2 |
| Advisory display | Preserve source/type/time/hash and render plain text | HTML, SVG, Markdown link and unsafe-URL payloads remain inert |
| History | Idempotent external import with completeness marker | Rotation, truncation, duplicate identical actions, older pacman format and missing journal |

Target-scale tests should use at least the established 10,000-record inventory,
high-cardinality search results and repeated history imports. Performance
measurements must report the actual host, fixture size, warm/cold state and
elapsed time; a passing number must not be invented after the measurement.

## Boundaries retained after this research

- No pacman or Flatpak metadata refresh is authorized in M2.
- No Flatpak remote, mask or installation may be changed.
- No result may be installed; M3's immutable-plan, local-confirmation and
  privilege gates remain closed.
- Live Flatpak search remains blocked until its no-refresh behavior is proven
  for the exact target version and command shape.
- HTML scraping is not a silent fallback for a broken feed or schema. A source
  without a stable, tested parser reports **Not checked** or **Source
  unavailable**.
