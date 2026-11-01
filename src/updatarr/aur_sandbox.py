"""Closed AUR build isolation prototype for M7.

The Module accepts one reviewed source tree and exact expected package names. It
never accepts a command, executable, environment, mount or Bubblewrap option
from its caller. Live AUR execution remains disabled outside this prototype.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import stat
import subprocess
import tempfile
import threading
import unicodedata
import uuid


_PACKAGE_NAME = re.compile(r"[a-z0-9][a-z0-9@._+\-]{0,127}\Z")
_PACKAGE_SUFFIXES = (".pkg.tar.zst", ".pkg.tar.xz", ".pkg.tar.gz")


class AurSandboxState(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class AurSandboxLimits:
    timeout_seconds: float = 300.0
    cpu_seconds: int = 300
    maximum_files: int = 10_000
    maximum_input_bytes: int = 512 * 1024 * 1024
    maximum_output_bytes: int = 2 * 1024 * 1024 * 1024
    maximum_log_bytes: int = 256 * 1024
    maximum_open_files: int = 256
    maximum_address_space_bytes: int = 4 * 1024 * 1024 * 1024
    cgroup_memory_bytes: int = 4 * 1024 * 1024 * 1024
    cgroup_tasks: int = 128
    cgroup_cpu_percent: int = 400


@dataclass(frozen=True)
class AurBuildArtifact:
    name: str
    path: Path
    size: int
    sha256: str


@dataclass(frozen=True)
class AurSandboxResult:
    state: AurSandboxState
    explanation: str
    artifacts: tuple[AurBuildArtifact, ...] = ()
    stdout: str = ""
    stderr: str = ""


class BubblewrapAurSandbox:
    """Build a reviewed AUR tree inside one fixed, networkless policy."""

    def __init__(self, output_root: Path) -> None:
        self._output_root = output_root
        self._limits = AurSandboxLimits()
        self._bubblewrap = Path("/usr/bin/bwrap")
        self._makepkg = Path("/usr/bin/makepkg")
        self._systemd_run = Path("/usr/bin/systemd-run")
        self._archive_tool = Path("/usr/bin/bsdtar")

    @classmethod
    def _testing(
        cls, output_root: Path, *, limits: AurSandboxLimits
    ) -> "BubblewrapAurSandbox":
        subject = cls(output_root)
        subject._limits = limits
        return subject

    def build(
        self, reviewed_tree: Path, expected_packages: tuple[str, ...]
    ) -> AurSandboxResult:
        """Build one reviewed tree without exposing caller-selected execution."""

        unavailable = self._tool_problem()
        if unavailable:
            return AurSandboxResult(AurSandboxState.UNAVAILABLE, unavailable)
        workspace_problem = self._workspace_problem()
        if workspace_problem:
            return AurSandboxResult(AurSandboxState.UNAVAILABLE, workspace_problem)
        if (
            not expected_packages
            or len(expected_packages) > 32
            or len(set(expected_packages)) != len(expected_packages)
            or any(not _PACKAGE_NAME.fullmatch(name) for name in expected_packages)
        ):
            return AurSandboxResult(
                AurSandboxState.REJECTED,
                "The expected package identities are invalid.",
            )

        try:
            source = reviewed_tree.resolve(strict=True)
        except OSError:
            return AurSandboxResult(
                AurSandboxState.REJECTED,
                "The reviewed build tree is unavailable.",
            )
        if reviewed_tree.is_symlink() or not source.is_dir():
            return AurSandboxResult(
                AurSandboxState.REJECTED,
                "The reviewed build tree must be one ordinary directory.",
            )

        with tempfile.TemporaryDirectory(
            prefix="updatarr-aur-sandbox.", dir="/dev/shm"
        ) as temporary:
            private_root = Path(temporary)
            build_root = private_root / "build"
            etc_root = private_root / "etc"
            try:
                self._copy_reviewed_tree(source, build_root)
                self._prepare_etc(etc_root)
            except ValueError as error:
                return AurSandboxResult(AurSandboxState.REJECTED, str(error))
            except OSError:
                return AurSandboxResult(
                    AurSandboxState.UNAVAILABLE,
                    "The private build workspace could not be prepared.",
                )

            argv = self._sandbox_argv(build_root, etc_root)
            try:
                completed = self._run(argv)
            except subprocess.TimeoutExpired:
                return AurSandboxResult(
                    AurSandboxState.TIMED_OUT,
                    "The isolated build exceeded its time limit and was stopped.",
                )
            except OSError:
                return AurSandboxResult(
                    AurSandboxState.UNAVAILABLE,
                    "The isolated build process could not start.",
                )

            stdout = self._bounded_text(completed.stdout)
            stderr = self._bounded_text(completed.stderr)
            if completed.returncode != 0:
                return AurSandboxResult(
                    AurSandboxState.FAILED,
                    "The isolated build failed without releasing an artifact.",
                    stdout=stdout,
                    stderr=stderr,
                )

            try:
                artifacts = self._retain_artifacts(build_root, expected_packages)
            except ValueError as error:
                return AurSandboxResult(
                    AurSandboxState.REJECTED,
                    str(error),
                    stdout=stdout,
                    stderr=stderr,
                )
            except OSError:
                return AurSandboxResult(
                    AurSandboxState.UNAVAILABLE,
                    "The private package output could not be retained.",
                    stdout=stdout,
                    stderr=stderr,
                )
            return AurSandboxResult(
                AurSandboxState.SUCCEEDED,
                "The reviewed tree built inside the isolated workspace.",
                artifacts=artifacts,
                stdout=stdout,
                stderr=stderr,
            )

    def _tool_problem(self) -> str | None:
        for path, label in (
            (self._bubblewrap, "Bubblewrap"),
            (self._makepkg, "makepkg"),
            (self._systemd_run, "systemd-run"),
            (self._archive_tool, "package archive reader"),
        ):
            try:
                metadata = path.lstat()
            except OSError:
                return f"{label} is unavailable at its fixed system path."
            if not stat.S_ISREG(metadata.st_mode):
                return f"{label} is not an ordinary system file."
            if metadata.st_uid != 0 or metadata.st_mode & 0o022:
                return f"{label} has unsafe ownership or permissions."
        return None

    @staticmethod
    def _workspace_problem() -> str | None:
        shared_memory = Path("/dev/shm")
        try:
            metadata = shared_memory.stat()
            mount_lines = Path("/proc/self/mountinfo").read_text(
                encoding="utf-8"
            ).splitlines()
        except OSError:
            return "The private memory-backed build workspace is unavailable."
        if metadata.st_uid != 0 or not shared_memory.is_dir():
            return "The private memory-backed build workspace has unsafe ownership."
        for line in mount_lines:
            left, separator, right = line.partition(" - ")
            fields = left.split()
            if separator and len(fields) > 4 and fields[4] == "/dev/shm":
                if right.split(maxsplit=1)[0] == "tmpfs":
                    return None
                break
        return "The private build workspace is not a memory-backed filesystem."

    def _copy_reviewed_tree(self, source: Path, destination: Path) -> None:
        destination.mkdir(mode=0o700)
        total_files = 0
        total_bytes = 0
        for current, directory_names, file_names, directory_fd in os.fwalk(
            source, follow_symlinks=False
        ):
            current_path = Path(current)
            relative = current_path.relative_to(source)
            target_directory = destination / relative
            target_directory.mkdir(mode=0o700, parents=True, exist_ok=True)

            for directory_name in directory_names:
                metadata = os.stat(
                    directory_name, dir_fd=directory_fd, follow_symlinks=False
                )
                if not stat.S_ISDIR(metadata.st_mode):
                    raise ValueError("The reviewed build tree contains a symbolic link.")

            for file_name in file_names:
                metadata = os.stat(
                    file_name, dir_fd=directory_fd, follow_symlinks=False
                )
                try:
                    descriptor = os.open(
                        file_name,
                        os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
                        dir_fd=directory_fd,
                    )
                except OSError as error:
                    raise ValueError(
                        "The reviewed build tree changed while it was copied."
                    ) from error
                opened = os.fstat(descriptor)
                if (
                    not stat.S_ISREG(metadata.st_mode)
                    or not stat.S_ISREG(opened.st_mode)
                    or (metadata.st_dev, metadata.st_ino)
                    != (opened.st_dev, opened.st_ino)
                ):
                    os.close(descriptor)
                    raise ValueError("The reviewed build tree contains a non-regular file.")
                total_files += 1
                total_bytes += opened.st_size
                if total_files > self._limits.maximum_files:
                    os.close(descriptor)
                    raise ValueError("The reviewed build tree contains too many files.")
                if total_bytes > self._limits.maximum_input_bytes:
                    os.close(descriptor)
                    raise ValueError("The reviewed build tree is larger than the allowed limit.")
                target = target_directory / file_name
                with os.fdopen(descriptor, "rb") as input_file, target.open("xb") as output:
                    shutil.copyfileobj(input_file, output, length=1024 * 1024)
                target.chmod(0o600)

        if not (destination / "PKGBUILD").is_file():
            raise ValueError("The reviewed build tree has no PKGBUILD file.")

    @staticmethod
    def _prepare_etc(etc_root: Path) -> None:
        etc_root.mkdir(mode=0o700)
        shutil.copyfile("/etc/makepkg.conf", etc_root / "makepkg.conf")
        with (etc_root / "makepkg.conf").open("a", encoding="utf-8") as config:
            config.write(
                "\n# Updatarr isolated-build resource policy\n"
                "MAKEFLAGS='-j2'\n"
                "COMPRESSZST=(zstd -c -T1 -)\n"
            )
        (etc_root / "makepkg.conf").chmod(0o400)
        (etc_root / "passwd").write_text(
            f"build:x:{os.getuid()}:{os.getgid()}:build:/home/build:/usr/bin/bash\n"
        )
        (etc_root / "group").write_text(f"build:x:{os.getgid()}:\n")
        (etc_root / "nsswitch.conf").write_text("passwd: files\ngroup: files\n")
        (etc_root / "pacman.conf").write_text(
            "[options]\n"
            "Architecture = auto\n"
            "DBPath = /tmp/pacman-db/\n"
            "CacheDir = /tmp/pacman-cache/\n"
            "LogFile = /tmp/pacman.log\n"
            "GPGDir = /tmp/pacman-gnupg/\n"
        )
        for path in etc_root.iterdir():
            path.chmod(0o400)

    def _sandbox_argv(self, build_root: Path, etc_root: Path) -> list[str]:
        sandbox = [
            str(self._bubblewrap),
            "--unshare-all",
            "--die-with-parent",
            "--new-session",
            "--clearenv",
            "--tmpfs",
            "/",
            "--ro-bind",
            "/usr",
            "/usr",
            "--symlink",
            "usr/bin",
            "/bin",
            "--symlink",
            "usr/lib",
            "/lib",
            "--symlink",
            "usr/lib",
            "/lib64",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
            "--dir",
            "/tmp/pacman-db",
            "--dir",
            "/tmp/pacman-cache",
            "--dir",
            "/tmp/pacman-gnupg",
            "--dir",
            "/etc",
            "--ro-bind",
            str(etc_root / "makepkg.conf"),
            "/etc/makepkg.conf",
            "--ro-bind",
            str(etc_root / "passwd"),
            "/etc/passwd",
            "--ro-bind",
            str(etc_root / "group"),
            "/etc/group",
            "--ro-bind",
            str(etc_root / "nsswitch.conf"),
            "/etc/nsswitch.conf",
            "--ro-bind",
            str(etc_root / "pacman.conf"),
            "/etc/pacman.conf",
            "--dir",
            "/home",
            "--dir",
            "/home/build",
            "--bind",
            str(build_root),
            "/build",
            "--chdir",
            "/build",
            "--setenv",
            "PATH",
            "/usr/bin",
            "--setenv",
            "HOME",
            "/home/build",
            "--setenv",
            "LANG",
            "C.UTF-8",
            "--setenv",
            "SOURCE_DATE_EPOCH",
            "1",
            "--",
            str(self._makepkg),
            "--noconfirm",
            "--nodeps",
            "--cleanbuild",
            "--clean",
            "--force",
        ]
        return self._resource_argv(sandbox)

    def _resource_argv(self, command: list[str]) -> list[str]:
        unit = f"updatarr-aur-build-{uuid.uuid4().hex}.scope"
        return [
            str(self._systemd_run),
            "--user",
            "--scope",
            "--quiet",
            "--collect",
            f"--unit={unit}",
            f"--property=MemoryMax={self._limits.cgroup_memory_bytes}",
            "--property=MemorySwapMax=0",
            f"--property=TasksMax={self._limits.cgroup_tasks}",
            f"--property=CPUQuota={self._limits.cgroup_cpu_percent}%",
            "--",
            *command,
        ]

    def _inspection_argv(
        self, artifact: Path, mode: str, member: str | None = None
    ) -> list[str]:
        sandbox = [
            str(self._bubblewrap),
            "--unshare-all",
            "--die-with-parent",
            "--new-session",
            "--clearenv",
            "--tmpfs",
            "/",
            "--ro-bind",
            "/usr",
            "/usr",
            "--symlink",
            "usr/bin",
            "/bin",
            "--symlink",
            "usr/lib",
            "/lib",
            "--symlink",
            "usr/lib",
            "/lib64",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
            "--ro-bind",
            str(artifact),
            "/artifact.pkg.tar",
            "--setenv",
            "PATH",
            "/usr/bin",
            "--",
            str(self._archive_tool),
            mode,
            "/artifact.pkg.tar",
        ]
        if member is not None:
            sandbox.append(member)
        return self._resource_argv(sandbox)

    def _run(
        self, argv: list[str], *, capture_limit: int | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        def limits() -> None:
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            resource.setrlimit(
                resource.RLIMIT_CPU,
                (self._limits.cpu_seconds, self._limits.cpu_seconds),
            )
            resource.setrlimit(
                resource.RLIMIT_FSIZE,
                (self._limits.maximum_output_bytes, self._limits.maximum_output_bytes),
            )
            resource.setrlimit(
                resource.RLIMIT_NOFILE,
                (self._limits.maximum_open_files, self._limits.maximum_open_files),
            )
            resource.setrlimit(
                resource.RLIMIT_AS,
                (
                    self._limits.maximum_address_space_bytes,
                    self._limits.maximum_address_space_bytes,
                ),
            )

        process = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            preexec_fn=limits,
        )
        limit = self._limits.maximum_log_bytes if capture_limit is None else capture_limit
        stdout_buffer = bytearray()
        stderr_buffer = bytearray()
        totals = {"stdout": 0, "stderr": 0}

        def drain(
            stream: object, buffer: bytearray, name: str
        ) -> None:
            while block := stream.read(64 * 1024):  # type: ignore[attr-defined]
                totals[name] += len(block)
                buffer.extend(block)
                if len(buffer) > limit:
                    del buffer[: len(buffer) - limit]

        stdout_thread = threading.Thread(
            target=drain,
            args=(process.stdout, stdout_buffer, "stdout"),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=drain,
            args=(process.stderr, stderr_buffer, "stderr"),
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()
        try:
            process.wait(timeout=self._limits.timeout_seconds)
        except subprocess.TimeoutExpired as error:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            stdout_thread.join(timeout=5)
            stderr_thread.join(timeout=5)
            raise error
        stdout_thread.join(timeout=5)
        stderr_thread.join(timeout=5)
        if stdout_thread.is_alive() or stderr_thread.is_alive():
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            raise OSError("The isolated process left an output stream open.")
        completed = subprocess.CompletedProcess(
            argv, process.returncode, bytes(stdout_buffer), bytes(stderr_buffer)
        )
        completed.stdout_truncated = totals["stdout"] > limit  # type: ignore[attr-defined]
        completed.stderr_truncated = totals["stderr"] > limit  # type: ignore[attr-defined]
        return completed

    def _retain_artifacts(
        self, build_root: Path, expected_packages: tuple[str, ...]
    ) -> tuple[AurBuildArtifact, ...]:
        candidates: dict[str, Path] = {}
        total_output_bytes = 0
        for candidate in build_root.iterdir():
            if not candidate.name.endswith(_PACKAGE_SUFFIXES):
                continue
            metadata = candidate.lstat()
            if not stat.S_ISREG(metadata.st_mode):
                raise ValueError("The build produced a linked or non-regular package file.")
            matches = [
                name
                for name in expected_packages
                if candidate.name.startswith(name + "-")
            ]
            matched = max(matches, key=len) if matches else None
            if matched is None:
                raise ValueError("The build produced an unexpected package identity.")
            if matched in candidates:
                raise ValueError("The build produced a duplicate package identity.")
            if metadata.st_size > self._limits.maximum_output_bytes:
                raise ValueError("The build produced a package larger than the allowed limit.")
            total_output_bytes += metadata.st_size
            if total_output_bytes > self._limits.maximum_output_bytes:
                raise ValueError("The build produced packages larger than the allowed limit.")
            self._inspect_artifact(candidate, matched)
            candidates[matched] = candidate
        if not candidates:
            raise ValueError("The build did not produce the expected package file.")
        if set(candidates) != set(expected_packages):
            raise ValueError("The build omitted an expected package identity.")

        self._output_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        run_name = uuid.uuid4().hex
        staging_root = self._output_root / f".{run_name}.partial"
        run_root = self._output_root / run_name
        staging_root.mkdir(mode=0o700)
        staged: list[tuple[str, int, str]] = []
        try:
            for candidate in sorted(candidates.values()):
                target = staging_root / candidate.name
                digest = hashlib.sha256()
                size = 0
                with candidate.open("rb") as source, target.open("xb") as output:
                    while block := source.read(1024 * 1024):
                        size += len(block)
                        if size > self._limits.maximum_output_bytes:
                            raise ValueError(
                                "The build produced a package larger than the allowed limit."
                            )
                        digest.update(block)
                        output.write(block)
                target.chmod(0o600)
                staged.append((candidate.name, size, digest.hexdigest()))
            staging_root.rename(run_root)
        except (OSError, ValueError):
            shutil.rmtree(staging_root, ignore_errors=True)
            raise
        return tuple(
            AurBuildArtifact(name, run_root / name, size, digest)
            for name, size, digest in staged
        )

    def _inspect_artifact(self, artifact: Path, expected_package: str) -> None:
        try:
            listing = self._run(
                self._inspection_argv(artifact, "-tf"),
                capture_limit=min(
                    self._limits.maximum_output_bytes,
                    self._limits.maximum_files * 4096,
                ),
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ValueError("The built package could not be inspected safely.") from error
        if listing.returncode != 0:
            raise ValueError("The built package is not a readable package archive.")
        if getattr(listing, "stdout_truncated", False):
            raise ValueError("The built package file inventory is too large.")
        try:
            names = (listing.stdout or b"").decode(
                "utf-8", errors="strict"
            ).splitlines()
        except UnicodeDecodeError as error:
            raise ValueError(
                "The built package has an unreadable file inventory."
            ) from error
        if not names or len(names) > self._limits.maximum_files:
            raise ValueError("The built package has an invalid file inventory.")
        for name in names:
            path = Path(name)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("The built package contains an unsafe file path.")

        try:
            package_info = self._run(
                self._inspection_argv(artifact, "-xOf", ".PKGINFO")
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ValueError("The built package identity could not be inspected safely.") from error
        if package_info.returncode != 0:
            raise ValueError("The built package has no readable package identity.")
        if getattr(package_info, "stdout_truncated", False):
            raise ValueError("The built package metadata is too large.")
        try:
            metadata = (package_info.stdout or b"").decode(
                "utf-8", errors="strict"
            )
        except UnicodeDecodeError as error:
            raise ValueError(
                "The built package has unreadable package metadata."
            ) from error
        package_names = {
            line.partition("=")[2].strip()
            for line in metadata.splitlines()
            if line.startswith("pkgname =")
        }
        if package_names != {expected_package}:
            raise ValueError("The built package metadata has an unexpected identity.")

    def _bounded_text(self, value: bytes | None) -> str:
        text = (value or b"").decode("utf-8", errors="replace")
        clean = "".join(
            character
            for character in text
            if character in "\n\t" or unicodedata.category(character) not in {"Cc", "Cf"}
        )
        return clean[-self._limits.maximum_log_bytes :]

