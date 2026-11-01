"""Provider Adapter contract, hostile-output and truthfulness checks."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from updatarr.domain import SourceState  # noqa: E402
from updatarr.providers.adapters import AurUpdatesAdapter, FlatpakAdapter, NativePackagesAdapter  # noqa: E402
from updatarr.providers.parsers import (  # noqa: E402
    ProviderOutputError, parse_firmware_devices, parse_flatpak_apps, parse_package_updates, parse_pacman_packages,
    parse_flatpak_settings,
)
from updatarr.providers.probes import FixtureProbeClient  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"


def _completed(stdout: str) -> dict:
    return {"stdout": stdout}


def test_native_adapter_records_inventory_without_inventing_updates() -> None:
    client = FixtureProbeClient({
        "pacman-installed": _completed("linux 6.17.2\nforeign-tool 1.0\n"),
        "pacman-foreign": _completed("foreign-tool 1.0\n"),
        "pacman-version": _completed("Pacman v7.1.0\n"),
    })
    result = NativePackagesAdapter(client).check()
    assert result.state is SourceState.NOT_CHECKED
    assert result.updates == ()
    assert len(result.software) == 2
    assert result.software[1].ownership == "foreign_unresolved"


def test_native_and_aur_update_queries_remain_separate_and_read_only() -> None:
    native_client = FixtureProbeClient({
        "pacman-installed": _completed("linux 6.17.2\nforeign-tool 1.0\n"),
        "pacman-foreign": _completed("foreign-tool 1.0\n"),
        "pacman-version": _completed("Pacman v7.1.0\n"),
        "native-updates": _completed("linux 6.17.2 -> 6.17.4\n"),
    })
    native = NativePackagesAdapter(native_client).check()
    assert native.state is SourceState.READY_TO_REVIEW
    assert [item.software_id for item in native.updates] == ["linux"]
    assert native.evidence["separate_temporary_database"] is True

    aur_client = FixtureProbeClient({
        "aur-updates": _completed("foreign-tool 1.0 -> 1.1 [2d2h]\n"),
        "yay-version": _completed("yay v13.0.1 - libalpm v16.0.1\n"),
    })
    aur = AurUpdatesAdapter(aur_client).check()
    assert aur.state is SourceState.READY_TO_REVIEW
    assert [item.software_id for item in aur.updates] == ["foreign-tool"]
    assert aur.software == ()
    assert aur.evidence["foreign_packages_not_reclassified"] is True


def test_update_output_is_bounded_by_strict_rows() -> None:
    with pytest.raises(ProviderOutputError):
        parse_package_updates("name 1.0; touch /tmp/no -> 2.0\n", "aur", "user")


@pytest.mark.parametrize("state, expected", [("not_available", SourceState.NOT_SUPPORTED), ("timed_out", SourceState.ERROR), ("error", SourceState.ERROR)])
def test_source_failures_remain_distinct_from_no_updates(state: str, expected: SourceState) -> None:
    client = FixtureProbeClient({
        "pacman-installed": {"state": state, "stdout": "", "exit_code": None},
        "pacman-foreign": _completed(""), "pacman-version": _completed("Pacman"),
    })
    result = NativePackagesAdapter(client).check()
    assert result.state is expected
    assert result.state is not SourceState.UP_TO_DATE


def test_malformed_contracts_fail_closed() -> None:
    with pytest.raises(ProviderOutputError):
        parse_pacman_packages((FIXTURES / "providers" / "pacman-malformed.txt").read_text())
    with pytest.raises(ProviderOutputError):
        parse_flatpak_apps((FIXTURES / "providers" / "flatpak-malformed.tsv").read_text(), "user")
    with pytest.raises(ProviderOutputError):
        parse_firmware_devices((FIXTURES / "providers" / "fwupd-malformed.json").read_text())


def test_hostile_text_is_inert_data_and_control_codes_are_removed() -> None:
    native = parse_pacman_packages((FIXTURES / "providers" / "pacman-hostile.txt").read_text())
    assert "<script>" in native[1].name
    assert "\x1b" not in native[2].name
    flatpak = parse_flatpak_apps((FIXTURES / "providers" / "flatpak-hostile.tsv").read_text(), "user")
    assert "<img-src=x>" in flatpak[0].name


def test_flatpak_scope_is_part_of_identity() -> None:
    text = (FIXTURES / "read_only" / "flatpak-apps.tsv").read_text()
    user_text = "\n".join(line for line in text.splitlines() if "\tuser\t" in line)
    records = parse_flatpak_apps(user_text, "user")
    assert all(record.scope == "user" for record in records)
    assert len({record.stable_id for record in records}) == len(records)
    system_row = user_text.replace("\tuser\t", "\tsystem\t", 1)
    with pytest.raises(ProviderOutputError, match="identity"):
        parse_flatpak_apps(system_row, "user")


def test_flatpak_existing_masks_and_disabled_remotes_are_read_only_evidence() -> None:
    settings = parse_flatpak_settings(
        "flathub\thttps://example.invalid\t-\t-\t1\nold-origin\t\t-\t-\t0\tdisabled,no-enumerate\n",
        "org.example.App/*\n",
    )
    assert settings == {"disabled_remotes": ["old-origin"], "masks": ["org.example.App/*"]}
    client = FixtureProbeClient({
        "flatpak-user-apps": _completed("org.example.App/x86_64/stable\tflathub\tuser\tabc\t1 MB\tcurrent\n"),
        "flatpak-user-remotes": _completed("old-origin\t\t-\t-\t0\tdisabled\n"),
        "flatpak-user-masks": _completed("org.example.App/*\n"),
        "flatpak-version": _completed("Flatpak 1.16\n"),
    })
    result = FlatpakAdapter(client, "user").check()
    assert result.evidence["disabled_remotes"] == ["old-origin"]
    assert result.evidence["masks"] == ["org.example.App/*"]


def test_truncated_output_fails_closed() -> None:
    client = FixtureProbeClient({
        "pacman-installed": {"stdout": "linux 1.0\n", "output_truncated": True},
        "pacman-foreign": _completed(""),
        "pacman-version": _completed("Pacman"),
    })
    result = NativePackagesAdapter(client).check()
    assert result.state is SourceState.ERROR
    assert result.software == ()
    assert result.evidence["output_truncated"] is True
