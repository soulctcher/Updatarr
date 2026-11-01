from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import inspect

import pytest

from updatarr.aur_sandbox import (
    AurSandboxLimits,
    AurSandboxState,
    BubblewrapAurSandbox,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/aur"


def sandbox(
    output: Path,
    *,
    timeout: float = 20.0,
    memory_bytes: int = 512 * 1024 * 1024,
    tasks: int = 32,
) -> BubblewrapAurSandbox:
    required = ("/usr/bin/bwrap", "/usr/bin/makepkg", "/usr/bin/systemd-run")
    if any(not Path(path).is_file() for path in required):
        pytest.skip("Arch Bubblewrap/makepkg/systemd integration is unavailable")
    return BubblewrapAurSandbox._testing(
        output,
        limits=AurSandboxLimits(
            timeout_seconds=timeout,
            cpu_seconds=max(2, int(timeout)),
            cgroup_memory_bytes=memory_bytes,
            cgroup_tasks=tasks,
        ),
    )


def package_member(artifact: Path, member: str) -> str:
    result = subprocess.run(
        ["/usr/bin/bsdtar", "-xOf", str(artifact), member],
        text=True,
        capture_output=True,
        check=False,
        timeout=5,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_safe_fixture_builds_as_a_regular_private_artifact(tmp_path: Path) -> None:
    result = sandbox(tmp_path / "out").build(
        FIXTURES / "safe", ("updatarr-sandbox-safe",)
    )

    assert result.state is AurSandboxState.SUCCEEDED, result.stderr
    assert len(result.artifacts) == 1
    artifact = result.artifacts[0]
    assert artifact.path.is_file() and not artifact.path.is_symlink()
    assert artifact.path.stat().st_mode & 0o077 == 0
    assert len(artifact.sha256) == 64


def test_hostile_fixture_cannot_reach_host_data_network_or_parent_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    host_secret = Path("/tmp/updatarr-aur-host-secret")
    host_secret.write_text("must remain outside the sandbox")
    monkeypatch.setenv("UPDATARR_TEST_SECRET", "must not cross the seam")

    try:
        result = sandbox(tmp_path / "out").build(
            FIXTURES / "hostile", ("updatarr-sandbox-hostile",)
        )

        assert result.state is AurSandboxState.SUCCEEDED, result.stderr
        assert host_secret.read_text() == "must remain outside the sandbox"
        assert package_member(
            result.artifacts[0].path,
            "usr/share/updatarr-sandbox-hostile/isolation-result",
        ) == "host data unavailable; network unavailable; environment cleared\n"
    finally:
        host_secret.unlink(missing_ok=True)


def test_exact_split_package_outputs_are_supported(tmp_path: Path) -> None:
    result = sandbox(tmp_path / "out").build(
        FIXTURES / "split",
        ("updatarr-sandbox-split-core", "updatarr-sandbox-split-extra"),
    )

    assert result.state is AurSandboxState.SUCCEEDED, result.stderr
    assert {artifact.name.split("-1.0-")[0] for artifact in result.artifacts} == {
        "updatarr-sandbox-split-core",
        "updatarr-sandbox-split-extra",
    }


def test_symbolic_link_in_reviewed_input_is_rejected(tmp_path: Path) -> None:
    reviewed = tmp_path / "reviewed"
    shutil.copytree(FIXTURES / "safe", reviewed)
    (reviewed / "escape").symlink_to("/home")

    result = sandbox(tmp_path / "out").build(reviewed, ("updatarr-sandbox-safe",))

    assert result.state is AurSandboxState.REJECTED
    assert "symbolic link" in result.explanation


def test_invalid_package_identity_is_rejected_before_process_start(tmp_path: Path) -> None:
    result = sandbox(tmp_path / "out").build(FIXTURES / "safe", ("../../escape",))

    assert result.state is AurSandboxState.REJECTED
    assert not (tmp_path / "out").exists()


def test_runaway_build_is_stopped_at_the_outer_time_limit(tmp_path: Path) -> None:
    result = sandbox(tmp_path / "out", timeout=0.5).build(
        FIXTURES / "timeout", ("updatarr-sandbox-timeout",)
    )

    assert result.state is AurSandboxState.TIMED_OUT
    assert not result.artifacts


def test_interface_has_no_command_environment_or_mount_surface() -> None:
    fields = set(BubblewrapAurSandbox.build.__annotations__)
    assert fields == {"reviewed_tree", "expected_packages", "return"}
    assert "command" not in fields
    assert "environment" not in fields
    assert "mount" not in fields
    constructor = set(BubblewrapAurSandbox.__init__.__annotations__)
    assert constructor == {"output_root", "return"}


def test_linked_package_output_is_rejected(tmp_path: Path) -> None:
    result = sandbox(tmp_path / "out").build(
        FIXTURES / "linked-output", ("updatarr-sandbox-linked-output",)
    )

    assert result.state is AurSandboxState.REJECTED
    assert "linked or non-regular" in result.explanation
    assert not result.artifacts


def test_private_resource_envelope_is_declared_without_pressure() -> None:
    implementation = inspect.getsource(BubblewrapAurSandbox._resource_argv)

    assert "MemoryMax=" in implementation
    assert "MemorySwapMax=0" in implementation
    assert "TasksMax=" in implementation
    assert "CPUQuota=" in implementation


@pytest.mark.parametrize(
    ("member", "message"),
    (
        ("inventory", "unreadable file inventory"),
        ("metadata", "unreadable package metadata"),
    ),
)
def test_non_utf8_archive_output_is_rejected_cleanly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    member: str,
    message: str,
) -> None:
    subject = sandbox(tmp_path / "out")
    responses = {
        "inventory": (
            subprocess.CompletedProcess([], 0, b"\xff", b""),
            subprocess.CompletedProcess([], 0, b"pkgname = expected\n", b""),
        ),
        "metadata": (
            subprocess.CompletedProcess([], 0, b".PKGINFO\n", b""),
            subprocess.CompletedProcess([], 0, b"\xff", b""),
        ),
    }
    calls = iter(responses[member])
    monkeypatch.setattr(subject, "_run", lambda _argv, **_kwargs: next(calls))

    with pytest.raises(ValueError, match=message):
        subject._inspect_artifact(tmp_path / "artifact", "expected")


def test_reviewed_tree_change_during_copy_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject = sandbox(tmp_path / "out")

    original_open = os.open

    def changed(path: object, *args: object, **kwargs: object) -> int:
        if path == "PKGBUILD":
            raise OSError("simulated path replacement")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr("updatarr.aur_sandbox.os.open", changed)
    with pytest.raises(ValueError, match="changed while it was copied"):
        subject._copy_reviewed_tree(FIXTURES / "safe", tmp_path / "copy")


def test_duplicate_package_identity_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject = sandbox(tmp_path / "out")
    build = tmp_path / "build"
    build.mkdir()
    (build / "expected-1.0-1-any.pkg.tar.zst").write_bytes(b"first")
    (build / "expected-2.0-1-any.pkg.tar.zst").write_bytes(b"second")
    monkeypatch.setattr(subject, "_inspect_artifact", lambda *_args: None)

    with pytest.raises(ValueError, match="duplicate package identity"):
        subject._retain_artifacts(build, ("expected",))


def test_longest_expected_package_prefix_is_used(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject = sandbox(tmp_path / "out")
    build = tmp_path / "build"
    build.mkdir()
    (build / "example-1.0-1-any.pkg.tar.zst").write_bytes(b"core")
    (build / "example-doc-1.0-1-any.pkg.tar.zst").write_bytes(b"docs")
    inspected: list[str] = []
    monkeypatch.setattr(
        subject,
        "_inspect_artifact",
        lambda _artifact, expected: inspected.append(expected),
    )

    artifacts = subject._retain_artifacts(build, ("example", "example-doc"))

    assert set(inspected) == {"example", "example-doc"}
    assert len(artifacts) == 2


def test_process_output_is_drained_into_a_bounded_tail(tmp_path: Path) -> None:
    subject = BubblewrapAurSandbox._testing(
        tmp_path / "out",
        limits=AurSandboxLimits(
            timeout_seconds=5,
            maximum_log_bytes=1024,
            cgroup_memory_bytes=512 * 1024 * 1024,
            cgroup_tasks=32,
        ),
    )

    completed = subject._run(
        ["/usr/bin/python", "-c", "import sys; sys.stdout.write('x' * 1048576)"]
    )

    assert completed.returncode == 0
    assert len(completed.stdout) == 1024
    assert completed.stdout == b"x" * 1024
    assert completed.stdout_truncated is True


def test_artifact_retention_io_failure_returns_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject = sandbox(tmp_path / "out")
    monkeypatch.setattr(
        subject,
        "_run",
        lambda _argv: subprocess.CompletedProcess([], 0, b"", b""),
    )

    def unavailable(*_args: object, **_kwargs: object) -> object:
        raise OSError("simulated output failure")

    monkeypatch.setattr(subject, "_retain_artifacts", unavailable)
    result = subject.build(FIXTURES / "safe", ("updatarr-sandbox-safe",))

    assert result.state is AurSandboxState.UNAVAILABLE
    assert "could not be retained" in result.explanation

