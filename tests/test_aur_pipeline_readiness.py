from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path

from updatarr.aur_pipeline import (
    AUR_POLICY_VERSION,
    AttestedAurPipeline,
    AurPipelineReadiness,
    REQUIRED_CHECKS,
    REQUIRED_TOOL_PACKAGES,
)


def _attestation(now: datetime) -> dict[str, object]:
    document: dict[str, object] = {
        "schema_version": 1,
        "policy_version": AUR_POLICY_VERSION,
        "prepared_at": now.isoformat(),
        "expires_at": (now + timedelta(days=7)).isoformat(),
        "tool_packages": {name: "test-version" for name in sorted(REQUIRED_TOOL_PACKAGES)},
        "clean_root": "/var/lib/updatarr/aur/arch/root",
        "checks": {name: True for name in sorted(REQUIRED_CHECKS)},
        "canary_artifact_sha256": "b" * 64,
    }
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":"))
    document["evidence_digest"] = hashlib.sha256(canonical.encode()).hexdigest()
    return document


def _write(path: Path, document: dict[str, object]) -> None:
    path.write_text(json.dumps(document), encoding="utf-8")
    path.chmod(0o444)


def test_complete_current_root_owned_attestation_enables_aur(tmp_path: Path) -> None:
    now = datetime(2026, 11, 3, tzinfo=UTC)
    record = tmp_path / "readiness.json"
    _write(record, _attestation(now))

    readiness = AttestedAurPipeline._testing(
        record,
        expected_owner=os.getuid(),
        now=lambda: now,
        package_versions=lambda: {name: "test-version" for name in REQUIRED_TOOL_PACKAGES},
    ).assess()

    assert readiness.ready is True
    assert readiness.evidence_digest
    assert readiness.policy_version == AUR_POLICY_VERSION


def test_missing_expired_tampered_or_incomplete_attestation_fails_closed(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 11, 3, tzinfo=UTC)
    missing = AttestedAurPipeline._testing(
        tmp_path / "missing.json",
        expected_owner=os.getuid(),
        now=lambda: now,
        package_versions=lambda: {name: "test-version" for name in REQUIRED_TOOL_PACKAGES},
    ).assess()
    assert missing.ready is False

    cases: list[dict[str, object]] = []
    expired = _attestation(now - timedelta(days=8))
    cases.append(expired)
    tampered = _attestation(now)
    tampered["canary_artifact_sha256"] = "changed-after-attestation"
    cases.append(tampered)
    incomplete = _attestation(now)
    checks = dict(incomplete["checks"])
    checks["repository_dependency_canary_verified"] = False
    incomplete["checks"] = checks
    canonical = json.dumps(
        {key: value for key, value in incomplete.items() if key != "evidence_digest"},
        sort_keys=True,
        separators=(",", ":"),
    )
    incomplete["evidence_digest"] = hashlib.sha256(canonical.encode()).hexdigest()
    cases.append(incomplete)

    for index, document in enumerate(cases):
        record = tmp_path / f"readiness-{index}.json"
        _write(record, document)
        result = AttestedAurPipeline._testing(
            record,
            expected_owner=os.getuid(),
            now=lambda: now,
            package_versions=lambda: {name: "test-version" for name in REQUIRED_TOOL_PACKAGES},
        ).assess()
        assert result.ready is False


def test_changed_installed_tool_version_invalidates_attestation(tmp_path: Path) -> None:
    now = datetime(2026, 11, 4, tzinfo=UTC)
    record = tmp_path / "readiness.json"
    _write(record, _attestation(now))

    result = AttestedAurPipeline._testing(
        record,
        expected_owner=os.getuid(),
        now=lambda: now,
        package_versions=lambda: {name: "new-version" for name in REQUIRED_TOOL_PACKAGES},
    ).assess()

    assert result.ready is False
    assert "changed after preparation" in result.explanation


def test_readiness_interface_contains_no_command_path_or_argument_surface() -> None:
    fields = set(AurPipelineReadiness.__dataclass_fields__)
    assert fields == {
        "ready",
        "explanation",
        "policy_version",
        "checked_at",
        "evidence_digest",
    }
    assert set(AttestedAurPipeline.assess.__annotations__) == {"return"}
