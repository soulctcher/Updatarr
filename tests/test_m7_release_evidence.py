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

