# M7 User-Service Namespace Validation

**Prepared:** 2026-11-02  
**Scope:** project-local correction for the rejected RC2 service behavior  
**Host changes:** none; only short-lived read-only user-service checks ran

## Problem

RC2 keeps `PrivateTmp=true` in its unprivileged user service. On this host,
systemd must create a user namespace to provide that private file area. Host
root is not mapped into a per-user service namespace, so `stat()` reports
root-owned files such as `/usr/bin/pacman` with Linux's overflow user ID,
currently 65534. RC2 required the visible owner to be exactly user ID 0 and
therefore rejected every fixed system tool before checking its package owner.

The systemd documentation says file-system namespace settings such as
`PrivateTmp=` implicitly enable `PrivateUsers=` for services run by a per-user
service manager. It also explains that the root mapping is omitted for a
per-user manager. The Linux user-namespace documentation says an unmapped file
owner is returned as the overflow user ID. Sources:

- [systemd.exec](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html)
- [Linux user_namespaces(7)](https://man7.org/linux/man-pages/man7/user_namespaces.7.html)
- [Linux overflow UID settings](https://docs.kernel.org/admin-guide/sysctl/fs.html#overflowgid-overflowuid)

## Narrow Correction

Updatarr still uses its closed list of exact executable paths. A fixed system
tool is accepted as root-owned only when all of these checks pass:

1. the visible owner is user ID 0; or it is the configured overflow user ID
   and `/proc/self/uid_map` proves host root is not mapped;
2. the executable is directly under `/usr/bin`;
3. the executable, `/usr`, `/usr/bin` and every directory leading to a
   symbolic-link target are not group- or world-writable;
4. the link, target and checked directories have the same safe
   root/namespace ownership result;
5. the current service user cannot write the executable; and
6. the read-only pacman ownership query reports the exact package named in the
   closed probe registry.

Missing, malformed or contradictory namespace information fails closed. The
exception does not apply to caller-chosen paths or user-owned tools. The
package keeps `PrivateTmp=true`; the correction does not weaken the service
unit.

## Evidence

Focused unit tests cover a root mapping, a root-absent mapping, an unrelated
owner and writable or non-system paths. A short-lived user service with
`PrivateTmp=true` and `NoNewPrivileges=true` then produced:

```text
{'accepted': True, 'owner': 'pacman', 'error': None}
[('pacman-version', 'completed', 'pacman'),
 ('pacman-installed', 'completed', 'pacman')]
{'npm': ('/usr/bin/npm', 'npm', None),
 'cargo': ('/usr/bin/cargo', 'rustup', None)}
```

Both transient units ended successfully, used no network or write-capable
provider action and were collected immediately. The installed RC2 package and
running pilot were not replaced.

