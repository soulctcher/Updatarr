"""Prepare and attest the fixed local AUR host prerequisites.

This command accepts no caller-selected command, package, path, URL or build
argument. It is intended to run through a graphical administrator prompt.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import stat
import subprocess
import sys
import tempfile

from .aur_pipeline import (
    AUR_POLICY_VERSION,
    ATTESTATION_PATH,
    EXPECTED_CLEAN_ROOT,
    REQUIRED_CHECKS,
    REQUIRED_TOOL_PACKAGES,
)


STATE_ROOT = Path("/var/lib/updatarr/aur")
CHROOT_ROOT = STATE_ROOT / "arch"
EVIDENCE_ROOT = STATE_ROOT / "evidence"
FIXED_TOOLS = {
    Path("/usr/bin/arch-nspawn"): "devtools",
    Path("/usr/bin/bwrap"): "bubblewrap",
    Path("/usr/bin/bsdtar"): "libarchive",
    Path("/usr/bin/env"): "coreutils",
    Path("/usr/bin/git"): "git",
    Path("/usr/bin/makechrootpkg"): "devtools",
    Path("/usr/bin/makepkg"): "pacman",
    Path("/usr/bin/mkarchroot"): "devtools",
    Path("/usr/bin/pacman"): "pacman",
    Path("/usr/bin/pkgctl"): "devtools",
    Path("/usr/bin/python"): "python",
    Path("/usr/bin/runuser"): "util-linux",
    Path("/usr/bin/systemd-run"): "systemd",
}
CANARY_NAME = "updatarr-aur-pipeline-canary"
CANARY_SOURCE = "Updatarr AUR host-prerequisite canary\n"
CANARY_SHA256 = hashlib.sha256(CANARY_SOURCE.encode()).hexdigest()
CANARY_PKGBUILD = f"""pkgname={CANARY_NAME}
pkgver=1
pkgrel=1
pkgdesc='Updatarr clean-build prerequisite canary'
arch=('any')
license=('AGPL-3.0-or-later')
source=('canary.txt')
sha256sums=('{CANARY_SHA256}')
package() {{
  install -Dm644 canary.txt \"$pkgdir/usr/share/{CANARY_NAME}/canary.txt\"
}}
"""


class AurPreparationError(RuntimeError):
    pass


def _run(
    argv: tuple[str, ...],
    *,
    cwd: Path | None = None,
    environment: dict[str, str] | None = None,
    timeout: int = 1800,
    pass_fds: tuple[int, ...] = (),
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        argv,
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
        pass_fds=pass_fds,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip().splitlines()
        message = detail[-1][:500] if detail else "The fixed preparation command failed."
        raise AurPreparationError(message)
    return completed


def _caller() -> tuple[int, int, str, Path]:
    raw_uid = os.environ.get("PKEXEC_UID") or os.environ.get("SUDO_UID")
    if raw_uid is None or not raw_uid.isdigit():
        raise AurPreparationError("The graphical administrator request has no calling user.")
    uid = int(raw_uid)
    if uid <= 0:
        raise AurPreparationError("The AUR build owner must be an ordinary local user.")
    record = pwd.getpwuid(uid)
    home = Path(record.pw_dir).resolve(strict=True)
    if not home.is_dir() or home == Path("/"):
        raise AurPreparationError("The AUR build owner's home directory is invalid.")
    return uid, record.pw_gid, record.pw_name, home


def _verify_tool(path: Path, expected_package: str) -> None:
    try:
        metadata = path.lstat()
        resolved = path.resolve(strict=True)
        resolved_metadata = resolved.stat()
    except OSError as error:
        raise AurPreparationError(f"Required build tool is unavailable: {path.name}") from error
    if path.is_symlink() and metadata.st_uid != 0:
        raise AurPreparationError(f"Required build tool link is not root-owned: {path.name}")
    if (
        not stat.S_ISREG(resolved_metadata.st_mode)
        or resolved_metadata.st_uid != 0
        or resolved_metadata.st_mode & 0o022
        or not resolved.is_relative_to(Path("/usr"))
    ):
        raise AurPreparationError(f"Required build tool is unsafe: {path.name}")
    owner = _run(("/usr/bin/pacman", "-Qqo", str(path)), timeout=10).stdout.strip()
    if owner != expected_package:
        raise AurPreparationError(f"Required build tool has the wrong package owner: {path.name}")


def _safe_environment(*, home: Path, user: str, output_root: Path) -> dict[str, str]:
    return {
        "HOME": str(home),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "MAKEFLAGS": "-j2",
        "NPROC": "2",
        "PATH": "/usr/bin",
        "PKGDEST": str(output_root / "packages"),
        "LOGDEST": str(output_root / "logs"),
        "SRCDEST": str(output_root / "sources"),
        "SRCPKGDEST": str(output_root / "source-packages"),
        "SUDO_USER": user,
        "USER": "root",
    }


def _prepare_canary(uid: int, gid: int) -> tuple[Path, Path]:
    # Fixed inputs remain root-owned. Only the separate destination tree is
    # writable by the build user, and it is never reused.
    canary_root = Path(tempfile.mkdtemp(prefix="canary.", dir=STATE_ROOT))
    canary_root.chmod(0o755)
    (canary_root / "PKGBUILD").write_text(CANARY_PKGBUILD, encoding="utf-8")
    (canary_root / "canary.txt").write_text(CANARY_SOURCE, encoding="utf-8")
    (canary_root / "PKGBUILD").chmod(0o644)
    (canary_root / "canary.txt").chmod(0o644)
    output_root = Path(tempfile.mkdtemp(prefix="output.", dir=STATE_ROOT))
    os.chown(output_root, uid, gid)
    output_root.chmod(0o700)
    for name in ("packages", "logs", "sources", "source-packages"):
        path = output_root / name
        path.mkdir(mode=0o700)
        os.chown(path, uid, gid)
    return canary_root, output_root


def _verify_user_namespace(user: str, home: Path) -> None:
    completed = _run(
        (
            "/usr/bin/runuser", "-u", user, "--",
            "/usr/bin/bwrap", "--unshare-all", "--die-with-parent", "--new-session",
            "--clearenv", "--tmpfs", "/", "--ro-bind", "/usr", "/usr",
            "--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib",
            "--symlink", "usr/lib", "/lib64", "--proc", "/proc", "--dev", "/dev",
            "--setenv", "PATH", "/usr/bin", "--",
            "/usr/bin/python", "-c",
            f"import os,socket; assert not os.path.exists({str(home)!r}); "
            "assert set(os.environ)=={'PATH'}; "
            "s=socket.socket(); assert s.connect_ex(('1.1.1.1',53)) != 0",
        ),
        timeout=30,
    )
    if completed.stdout or completed.stderr:
        raise AurPreparationError("The isolated user-namespace check returned unexpected output.")


def _write_attestation(tool_packages: dict[str, str], artifact_digest: str) -> None:
    now = datetime.now(UTC)
    document: dict[str, object] = {
        "schema_version": 1,
        "policy_version": AUR_POLICY_VERSION,
        "prepared_at": now.isoformat(),
        "expires_at": (now + timedelta(days=7)).isoformat(),
        "tool_packages": tool_packages,
        "clean_root": EXPECTED_CLEAN_ROOT,
        "checks": {name: True for name in sorted(REQUIRED_CHECKS)},
        "canary_artifact_sha256": artifact_digest,
    }
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":"))
    document["evidence_digest"] = hashlib.sha256(canonical.encode()).hexdigest()
    ATTESTATION_PATH.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".readiness.", dir=ATTESTATION_PATH.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(document, stream, sort_keys=True, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(0o444)
        temporary.replace(ATTESTATION_PATH)
    finally:
        if temporary.exists():
            temporary.unlink()


def _installed_tool_packages() -> dict[str, str]:
    completed = _run(
        ("/usr/bin/pacman", "-Q", *sorted(REQUIRED_TOOL_PACKAGES)), timeout=10
    )
    versions: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        name, separator, version = line.partition(" ")
        if not separator or name not in REQUIRED_TOOL_PACKAGES or not version:
            raise AurPreparationError("The installed AUR prerequisite versions were incomplete.")
        versions[name] = version
    if set(versions) != REQUIRED_TOOL_PACKAGES:
        raise AurPreparationError("The installed AUR prerequisite versions were incomplete.")
    return versions


def _retain_verified_canary(artifact: Path, uid: int) -> str:
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    descriptor = os.open(artifact, flags)
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != uid
            or metadata.st_nlink != 1
            or metadata.st_mode & 0o022
            or metadata.st_size <= 0
            or metadata.st_size > 64 * 1024 * 1024
        ):
            raise AurPreparationError("The clean-build canary artifact is unsafe.")
        descriptor_path = f"/proc/self/fd/{descriptor}"
        listing = _run(
            ("/usr/bin/bsdtar", "-tf", descriptor_path),
            timeout=30,
            pass_fds=(descriptor,),
        ).stdout.splitlines()
        expected_member = f"usr/share/{CANARY_NAME}/canary.txt"
        allowed = {
            ".BUILDINFO", ".MTREE", ".PKGINFO", "usr/", "usr/share/",
            f"usr/share/{CANARY_NAME}/", expected_member,
        }
        if expected_member not in listing or any(member not in allowed for member in listing):
            raise AurPreparationError("The clean-build canary package has unexpected contents.")
        package_info = _run(
            ("/usr/bin/bsdtar", "-xOf", descriptor_path, ".PKGINFO"),
            timeout=30,
            pass_fds=(descriptor,),
        ).stdout.splitlines()
        if f"pkgname = {CANARY_NAME}" not in package_info or "pkgver = 1-1" not in package_info:
            raise AurPreparationError("The clean-build canary package identity is invalid.")
        digest = hashlib.sha256()
        os.lseek(descriptor, 0, os.SEEK_SET)
        with os.fdopen(os.dup(descriptor), "rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        retained = EVIDENCE_ROOT / "canary.pkg.tar.zst"
        temporary_descriptor, temporary_name = tempfile.mkstemp(
            prefix=".canary.", dir=EVIDENCE_ROOT
        )
        temporary = Path(temporary_name)
        try:
            os.lseek(descriptor, 0, os.SEEK_SET)
            with os.fdopen(os.dup(descriptor), "rb") as source, os.fdopen(
                temporary_descriptor, "wb"
            ) as destination:
                shutil.copyfileobj(source, destination, length=1024 * 1024)
                destination.flush()
                os.fsync(destination.fileno())
            temporary.chmod(0o444)
            temporary.replace(retained)
        finally:
            if temporary.exists():
                temporary.unlink()
        return digest.hexdigest()
    finally:
        os.close(descriptor)


def prepare() -> None:
    if os.geteuid() != 0:
        raise AurPreparationError("A graphical administrator prompt is required.")
    uid, gid, user, home = _caller()
    for path, owner in FIXED_TOOLS.items():
        _verify_tool(path, owner)
    tool_packages = _installed_tool_packages()

    STATE_ROOT.mkdir(mode=0o755, parents=True, exist_ok=True)
    CHROOT_ROOT.mkdir(mode=0o755, parents=True, exist_ok=True)
    EVIDENCE_ROOT.mkdir(mode=0o755, parents=True, exist_ok=True)
    clean_root = Path(EXPECTED_CLEAN_ROOT)
    if not (clean_root / ".arch-chroot").is_file():
        _run(("/usr/bin/mkarchroot", str(clean_root), "base-devel"), timeout=1800)
    else:
        _run(("/usr/bin/arch-nspawn", str(clean_root), "/usr/bin/pacman", "-Syu", "--noconfirm"), timeout=1800)

    canary_root, output_root = _prepare_canary(uid, gid)
    environment = _safe_environment(home=home, user=user, output_root=output_root)
    _run(
        ("/usr/bin/runuser", "-u", user, "--", "/usr/bin/env", "-i",
         f"HOME={home}", "PATH=/usr/bin", "LANG=C.UTF-8", "LC_ALL=C.UTF-8",
         f"SRCDEST={output_root / 'sources'}",
         "/usr/bin/makepkg", "--verifysource", "--noconfirm"),
        cwd=canary_root,
        timeout=300,
    )
    _verify_user_namespace(user, home)
    _run(
        ("/usr/bin/makechrootpkg", "-c", "-r", str(CHROOT_ROOT), "-U", user, "--", "--noconfirm"),
        cwd=canary_root,
        environment=environment,
        timeout=1800,
    )
    artifacts = tuple((output_root / "packages").glob(f"{CANARY_NAME}-*.pkg.tar.zst"))
    if len(artifacts) != 1 or artifacts[0].is_symlink() or not artifacts[0].is_file():
        raise AurPreparationError("The clean build did not produce exactly one ordinary canary package.")
    digest = _retain_verified_canary(artifacts[0], uid)
    _write_attestation(tool_packages, digest)


def main() -> None:
    if len(sys.argv) != 1:
        raise SystemExit("updatarr-aur-prepare accepts no arguments")
    try:
        prepare()
    except (AurPreparationError, OSError, subprocess.TimeoutExpired) as error:
        raise SystemExit(f"AUR pipeline preparation failed: {error}") from None
    print("The Updatarr AUR host prerequisites are ready for exact package review.")


if __name__ == "__main__":
    main()
