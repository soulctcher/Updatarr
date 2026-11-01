from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def test_m7_scope_is_accepted_without_expanding_host_authority() -> None:
    proposal = (ROOT / "docs/M7_PROPOSAL.md").read_text()
    milestones = (ROOT / "MILESTONES.md").read_text()

    assert "[x] User accepts this proposed M7 scope" in proposal
    assert "project-local M7 implementation" in milestones
    assert "release publication" in milestones
    assert "every live software mutation remain" in milestones


def test_selected_license_is_consistent_but_publication_is_still_blocked() -> None:
    project = (ROOT / "pyproject.toml").read_text()
    browser = json.loads((ROOT / "web/package.json").read_text())
    package = (ROOT / "packaging/arch/PKGBUILD").read_text()
    limits = (ROOT / "docs/KNOWN_LIMITATIONS.md").read_text()

    assert 'license = "AGPL-3.0-or-later"' in project
    assert browser["license"] == "AGPL-3.0-or-later"
    assert "license=('AGPL-3.0-or-later')" in package
    assert "'uvicorn'" in package
    assert "python-uvicorn" not in package
    assert (ROOT / "LICENSE").read_text().startswith(
        "GNU AFFERO GENERAL PUBLIC LICENSE"
    )
    assert "Copyright-holder text is pending" in limits


def test_recorded_logo_digest_matches_the_packaged_asset() -> None:
    asset = ROOT / "web/src/assets/updatarr-loop.png"
    digest = hashlib.sha256(asset.read_bytes()).hexdigest()
    provenance = (ROOT / "docs/release/ASSET_PROVENANCE.md").read_text()

    assert digest == "0abf402bdd51a9913b6116f4630bd245e76353db4836885aa0e2dacb66838a69"
    assert digest in provenance


def test_locked_runtime_sboms_are_generated_without_release_actions(tmp_path: Path) -> None:
    output = tmp_path / "evidence"
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/generate_m7_evidence.sh"), str(output)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    python_bom = json.loads((output / "sboms/python-runtime.cdx.json").read_text())
    web_bom = json.loads((output / "sboms/web-runtime.cdx.json").read_text())

    assert python_bom["bomFormat"] == "CycloneDX"
    assert python_bom["metadata"]["component"]["name"] == "updatarr"
    assert len(python_bom["components"]) >= 10

    assert web_bom["bomFormat"] == "CycloneDX"
    assert web_bom["metadata"]["component"]["name"] == "updatarr-web"
    assert {component["name"] for component in web_bom["components"]} == {
        "react",
        "react-dom",
        "scheduler",
    }

    reviewed_inputs = (output / "reviewed-inputs.sha256").read_text()
    assert "pyproject.toml" in reviewed_inputs
    assert "web/package-lock.json" in reviewed_inputs
    assert "web/src/assets/updatarr-loop.png" in reviewed_inputs
    assert (output / "sboms.sha256").is_file()
    licenses = json.loads((output / "dependency-licenses.json").read_text())
    assert licenses["format"] == "updatarr-declared-license-inventory-v1"
    assert len(licenses["python_runtime"]) == len(python_bom["components"])
    assert len(licenses["browser_runtime"]) == len(web_bom["components"])
    assert all("license_expression" in item for item in licenses["python_runtime"])

    repeated = subprocess.run(
        ["bash", str(ROOT / "scripts/generate_m7_evidence.sh"), str(output)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert repeated.returncode == 2
    assert "already exists" in repeated.stderr


def test_disposable_build_and_lifecycle_scripts_keep_hard_limits() -> None:
    build = (ROOT / "scripts/build_m7_arch_container.sh").read_text()
    lifecycle = (ROOT / "scripts/run_m7_package_lifecycle.sh").read_text()
    lifecycle_container = (
        ROOT / "packaging/release/Dockerfile.m7-lifecycle"
    ).read_text()

    for script in (build, lifecycle):
        assert "--memory=2g" in script
    assert "--network=none" in build
    assert "--network=none" in lifecycle
    assert "--read-only" in build
    assert "--cap-drop=ALL" in build
    assert "UPDATARR_PROVIDER_MODE=simulator" in lifecycle_container
    assert "pacman -R --noconfirm updatarr" in lifecycle_container
    assert "test -f /home/updatarr-test/.local/state/updatarr/updatarr.db" in lifecycle_container
    archive = (ROOT / "scripts/build_source_archive.sh").read_text()
    assert 'tar -C "$project_root/packaging"' in archive
    assert "-cf - release" in archive

