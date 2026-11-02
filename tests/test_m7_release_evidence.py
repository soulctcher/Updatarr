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
    notice = (ROOT / "NOTICE").read_text()
    assert "Copyright © 2026 Erik Winblad" in notice
    assert "Copyright-holder text is pending" not in limits
    assert '"$project_root/NOTICE"' in (
        ROOT / "scripts/build_source_archive.sh"
    ).read_text()
    assert 'usr/share/licenses/updatarr/NOTICE' in package


def test_recorded_logo_digest_matches_the_packaged_asset() -> None:
    asset = ROOT / "web/src/assets/updatarr-loop.png"
    digest = hashlib.sha256(asset.read_bytes()).hexdigest()
    provenance = (ROOT / "docs/release/ASSET_PROVENANCE.md").read_text()
    decisions = (ROOT / "docs/M7_OWNER_DECISIONS.md").read_text()
    limits = (ROOT / "docs/KNOWN_LIMITATIONS.md").read_text()
    normalized_limits = " ".join(limits.split())
    milestones = (ROOT / "MILESTONES.md").read_text()

    assert digest == "0abf402bdd51a9913b6116f4630bd245e76353db4836885aa0e2dacb66838a69"
    assert digest in provenance
    assert "Owner approved inclusion" in provenance
    assert "AGPL-3.0-or-later" in provenance
    assert "owner approved the recorded AI-generated loop logo" in decisions
    assert "Generated-logo terms are not confirmed" not in limits
    assert "reproducibility limitation, not a release blocker" in limits
    assert "reproducibility limitation, not a release blocker" in milestones
    assert "The exact image model/version was not retained" in normalized_limits


def test_release_public_key_matches_the_recorded_fingerprint() -> None:
    public_key = ROOT / "docs/release/UPDATARR_RELEASE_KEY.asc"
    public_key_text = public_key.read_text()
    result = subprocess.run(
        ["gpg", "--batch", "--with-colons", "--show-keys", str(public_key)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    records = [row.split(":") for row in result.stdout.splitlines()]
    assert [row[0] for row in records] == ["pub", "fpr", "uid", "sub", "fpr"]
    primary, signing_subkey = records[0], records[3]
    assert primary[1] == "u" and primary[3] == "22"
    assert "c" in primary[11]
    assert signing_subkey[1] == "u" and signing_subkey[3] == "22"
    assert signing_subkey[11] == "s"
    assert not {"sec", "ssb", "rvk"}.intersection(row[0] for row in records)

    fingerprints = [
        row.split(":")[9]
        for row in result.stdout.splitlines()
        if row.startswith("fpr:")
    ]
    assert fingerprints == [
        "721EED2D67ADEE74D26E75C57DAF7D1402C8082E",
        "5BD6C0A8D98B655AEAF05EC2E689CC8D9BBB0AA4",
    ]

    assert "BEGIN PGP PUBLIC KEY BLOCK" in public_key_text
    assert "PRIVATE KEY" not in public_key_text
    assert "SECRET KEY" not in public_key_text
    release_files = [
        path for path in (ROOT / "docs/release").rglob("*") if path.is_file()
    ]
    assert not any(path.suffix == ".rev" for path in release_files)
    assert not any(
        b"This is a revocation certificate" in path.read_bytes()
        for path in release_files
    )

    signing = (ROOT / "docs/release/RELEASE_SIGNING.md").read_text()
    normalized_signing = " ".join(signing.split())
    assert (
        "RC1 signatures verify, but RC1 is rejected"
        in normalized_signing
    )
    assert "721E ED2D 67AD EE74 D26E 75C5 7DAF 7D14 02C8 082E" in signing
    assert "5BD6 C0A8 D98B 655A EAF0 5EC2 E689 CC8D 9BBB 0AA4" in signing
    assert (
        "The first local M7 candidate label is `v0.6.0-rc.1`"
        in normalized_signing
    )

    milestones = " ".join((ROOT / "MILESTONES.md").read_text().split())
    assert (
        "Signing-key use is authorized only for the final local M7 release "
        "label and release files"
        in milestones
    )
    assert "it does not authorize publication or a push" in milestones
    tag = subprocess.run(
        ["git", "cat-file", "tag", "v0.6.0-rc.1"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert tag.returncode == 0, tag.stderr
    assert "object ee18e9a7f789404ece81488f150fd02e33837a42" in tag.stdout
    assert "-----BEGIN PGP SIGNATURE-----" in tag.stdout
    test_plan = (ROOT / "TEST_PLAN.md").read_text()
    assert "GnuPG command-line tool" in test_plan


def test_shipped_application_inputs_contain_no_known_demo_password() -> None:
    shipped_inputs = (
        ROOT / "README.md",
        ROOT / "src/updatarr/app.py",
        ROOT / "src/updatarr/deployment.py",
        ROOT / "web/src/App.tsx",
    )

    for path in shipped_inputs:
        content = path.read_text()
        assert "updatarr-demo" not in content, path
        assert "test-only-password" not in content, path


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

