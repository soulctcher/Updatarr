from __future__ import annotations

import inspect
import hashlib
import os
from pathlib import Path
import subprocess
import sys

import pytest

from updatarr import aur_prepare


def test_privileged_preparation_has_no_caller_selected_input_surface() -> None:
    assert tuple(inspect.signature(aur_prepare.prepare).parameters) == ()
    assert tuple(inspect.signature(aur_prepare.main).parameters) == ()
    assert aur_prepare.STATE_ROOT.as_posix() == "/var/lib/updatarr/aur"
    assert aur_prepare.EXPECTED_CLEAN_ROOT == "/var/lib/updatarr/aur/arch/root"


def test_entrypoint_rejects_every_argument_before_preparation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    def should_not_run() -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(aur_prepare, "prepare", should_not_run)
    monkeypatch.setattr(sys, "argv", ["updatarr-aur-prepare", "anything"])

    with pytest.raises(SystemExit, match="accepts no arguments"):
        aur_prepare.main()

    assert called is False


def test_fixed_tool_set_covers_every_directly_invoked_interpreter() -> None:
    expected = {
        "/usr/bin/arch-nspawn",
        "/usr/bin/bwrap",
        "/usr/bin/bsdtar",
        "/usr/bin/env",
        "/usr/bin/makechrootpkg",
        "/usr/bin/makepkg",
        "/usr/bin/mkarchroot",
        "/usr/bin/pacman",
        "/usr/bin/python",
        "/usr/bin/runuser",
    }
    assert expected <= {path.as_posix() for path in aur_prepare.FIXED_TOOLS}


def test_canary_inputs_remain_read_only_and_outputs_are_separate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(aur_prepare, "STATE_ROOT", tmp_path)

    source, output = aur_prepare._prepare_canary(os.getuid(), os.getgid())

    assert source != output
    assert source.stat().st_mode & 0o777 == 0o755
    assert (source / "PKGBUILD").stat().st_mode & 0o777 == 0o644
    assert (source / "canary.txt").stat().st_mode & 0o777 == 0o644
    assert output.stat().st_mode & 0o777 == 0o700
    assert (output / "packages").stat().st_mode & 0o777 == 0o700


def test_artifact_handoff_uses_one_open_descriptor_during_path_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tree = tmp_path / "tree"
    target = tree / "usr/share" / aur_prepare.CANARY_NAME
    target.mkdir(parents=True)
    (tree / ".PKGINFO").write_text(
        f"pkgname = {aur_prepare.CANARY_NAME}\npkgver = 1-1\n",
        encoding="utf-8",
    )
    (tree / ".BUILDINFO").write_text("format = 2\n", encoding="utf-8")
    (tree / ".MTREE").write_text("#mtree\n", encoding="utf-8")
    (target / "canary.txt").write_text(aur_prepare.CANARY_SOURCE, encoding="utf-8")
    artifact = tmp_path / f"{aur_prepare.CANARY_NAME}-1-1-any.pkg.tar.zst"
    completed = subprocess.run(
        (
            "/usr/bin/bsdtar", "-caf", str(artifact),
            ".BUILDINFO", ".MTREE", ".PKGINFO", "usr",
        ),
        cwd=tree,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    original = artifact.read_bytes()
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    monkeypatch.setattr(aur_prepare, "EVIDENCE_ROOT", evidence)
    real_run = aur_prepare._run
    calls = 0

    def swap_after_first_read(*args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal calls
        result = real_run(*args, **kwargs)
        calls += 1
        if calls == 1:
            artifact.rename(tmp_path / "original.pkg.tar.zst")
            artifact.write_bytes(b"not the opened package")
        return result

    monkeypatch.setattr(aur_prepare, "_run", swap_after_first_read)

    digest = aur_prepare._retain_verified_canary(artifact, os.getuid())

    assert digest == hashlib.sha256(original).hexdigest()
    assert (evidence / "canary.pkg.tar.zst").read_bytes() == original
