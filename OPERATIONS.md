# Updatarr operations and recovery

**Status:** M7 operator runbook; exact RC2 package installation and a manual
loopback-only read-only pilot were authorized on 2026-11-02. Service enablement
and migration remain separately approval-gated.

## Supported deployment posture

Initial support targets one EndeavourOS/Arch workstation with KDE Plasma and:

- an unprivileged Updatarr service;
- a browser interface bound to loopback by default;
- an optional explicitly enabled authenticated HTTPS listener for trusted-LAN
  or VPN use, terminated directly or at a configured trusted reverse proxy;
- a KDE tray/launcher in the logged-in desktop session;
- a separately installed privileged executor only after M3 approval.

Direct public-Internet exposure is not initially supported.

## Service states

| State | Meaning | Operator response |
| --- | --- | --- |
| Healthy | Service, database and enabled update sources have current successful checks | None |
| Degraded | Some update sources failed, need a refresh or are unavailable | Inspect the cause for each update source; do not treat the system as current |
| Awaiting review | A plan exists but has not been approved | Review exact changes and advisories |
| Awaiting local confirmation | A reviewed plan needs explicit consent at the managed host before any software mutation | Confirm or reject in the local approval surface |
| Waiting for administrator permission | Confirmation on this computer is complete and a root-required plan is waiting on Polkit | Allow or reject it through the desktop password prompt |
| Running | One update run owns the relevant coordinator lock | Observe progress; cancel only when shown as safe |
| Needs reboot | Backend reports activation or running/installed kernel difference | Reboot only when user chooses |
| Needs manual recovery | Updatarr cannot verify the outcome automatically | Preserve evidence and follow the update source's recovery guidance |

## Startup model

Choose exactly one supervised service mechanism and one tray startup mechanism.
Do not configure both XDG autostart and a user systemd unit for the same process.
The final package must document enable, disable and rollback steps.

The provisional model uses a core systemd user unit plus a tray unit bound to
`graphical-session.target`. Quitting the tray must not stop the core or an active
update run. User lingering may keep the core reachable after logout, but is an
explicit opt-in; privileged work remains pending when no eligible graphical
administrator-permission prompt is available.

M5 selects this model in proposed ADR 0010 and ships no XDG autostart entry.
The exact staged install, enable, disable, backup and recovery procedure is in
[Arch installation and recovery](docs/operations/ARCH_INSTALL.md).

The tray menu includes **Settings…** for tray-only preferences. They are saved
in the current user's `$XDG_CONFIG_HOME/updatarr/tray-settings.json` with
owner-only permissions. The refresh choice controls how often the tray rereads
the service's recorded summary; it does not run **Check software**. Notification
choices control when and how long desktop messages appear. The dialog also
allows an optional hourly, four-hour or daily reminder while updates are
waiting. Removing the preferences file restores the five-second refresh,
notification on new or changed update counts, no repeated reminder and
eight-second message defaults the next time the tray starts.

## Configuration and secrets

Final paths will follow Arch/XDG conventions and package ownership. Separate:

- ordinary settings suitable for export;
- database and audit history;
- password verifiers, sessions and recovery material;
- update-source caches and disposable download/build staging;
- diagnostic logs with bounded retention.

Exports exclude secrets by default. Configuration changes affecting bind
address, authentication or trusted proxies require validation before restart.

## Backup and restore requirements

Before schema or configuration migrations:

1. quiesce application writes;
2. create a consistent SQLite backup using the database-supported mechanism;
3. copy configuration with permissions preserved;
4. record application/schema version and backup checksum;
5. perform migration atomically;
6. run integrity and startup checks;
7. retain the prior compatible package/configuration path until rollback is
   proven.

A backup is not considered valid until a disposable restore test succeeds.

## Update run recovery

On startup, verify unfinished update runs against update-source state and logs.
Never convert `running` to `succeeded` based only on process disappearance.
Possible outcomes are succeeded, failed, partially succeeded, cancelled, needs
reboot or needs manual recovery. When actual state remains unknown after
the result check, use needs manual recovery and preserve that uncertainty in the
diagnostic evidence.

Do not remove a package-manager lock automatically. First establish whether a
live process owns it, what operation was in progress and what the backend's
documented recovery procedure requires.

## M4 follow-up and recovery states

- Firmware can require a restart, full shutdown, reconnect or separate
  activation. Show the exact provider instruction and do not mark the update
  finished until fresh device history/state supports it.
- A startup-related system update remains one complete native update. A failed
  driver build, early startup image hook or boot-file result is **Needs manual
  recovery**, not a partly successful standalone kernel update.
- A staged portable-app replacement keeps the previous file until the new file
  identity, mode and launch eligibility are checked. Removing that recovery
  copy is a later maintenance decision.
- Tool updates preserve the owning installer, user data root, active/default
  selection and project pins. An ownership collision blocks the plan.
- A maintenance preview is evidence only. M4 has no cleanup action, so there is
  no operational shortcut from preview to deletion.

## Network recovery

If authentication or proxy configuration prevents access:

- recovery must require access to the managed host;
- provide an offline validation/report command before any reset command;
- back up current configuration;
- reset only the minimum affected web setting or session material;
- retain an audit event without logging new credentials;
- return to loopback-only mode when safe intent cannot be established.

Updatarr must never solve a connectivity problem by silently binding to all
interfaces, disabling authentication or permitting cleartext non-loopback
credentials/sessions.

Validated environment settings and supported proxy behavior are documented in
[trusted network and reverse-proxy access](docs/operations/NETWORK_ACCESS.md).

## Octopi migration and rollback

Migration occurs only in M5:

1. prove Updatarr checks every approved source side-by-side;
2. verify counts and failure visibility across reboot/login;
3. record current Octopi package and autostart configuration;
4. stop only the duplicate notifier with explicit approval;
5. verify one active tray/notifier and current scans;
6. remove Octopi only under a separate explicit approval;
7. retain documented reinstall/autostart restoration steps.

PackageKit and update-source tools are not removal targets merely because
Updatarr exists.

The evidence checklist, separate approval points and exact rollback drill are
in [Octopi side-by-side migration and rollback](docs/operations/OCTOPI_MIGRATION.md).

## M6 release and recovery references

- [Upgrade and interrupted-run recovery](docs/operations/UPGRADE_RECOVERY.md)
  records backup validation, API compatibility, restart reconciliation, lock
  handling and rollback.
- [Known limitations and release blockers](docs/KNOWN_LIMITATIONS.md) separates
  unsupported behavior from publication and live-trial approval gates.

## Diagnostic bundle requirements

A future support bundle should contain version/capability summaries, redacted
logs, update-source health, schema version and recent update-run state. It must
exclude credentials, session tokens, authorization headers and full local paths
or usernames unless the user explicitly opts in after previewing the bundle.
