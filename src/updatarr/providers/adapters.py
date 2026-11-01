"""Concrete simulator and trusted read-only provider Adapters."""

from __future__ import annotations

from dataclasses import dataclass
import time

from ..domain import DetectedUpdate, SoftwareRecord, SourceResult, SourceState, stable_software_id, utc_now
from .base import ProviderAdapter
from .parsers import (
    ProviderOutputError,
    parse_firmware_devices,
    parse_appimage_paths,
    parse_cargo_tools,
    parse_fnm_versions,
    parse_flatpak_apps,
    parse_flatpak_settings,
    parse_npm_globals,
    parse_package_updates,
    parse_pacman_packages,
    parse_rustup_toolchains,
    parse_uv_tools,
)
from .probes import LiveProbeClient, ProbeClient


def _results(report: dict) -> dict[str, dict]:
    return {result["probe_id"]: result for result in report.get("results", [])}


def _failure(source_id: str, name: str, scope: str, started: float, results: list[dict]) -> SourceResult | None:
    failed = next(
        (item for item in results if item.get("state") != "completed" or item.get("output_truncated")),
        None,
    )
    if failed is None:
        return None
    state = SourceState.NOT_SUPPORTED if failed.get("state") == "not_available" else SourceState.ERROR
    message = (
        f"{name} is not available on this computer."
        if state is SourceState.NOT_SUPPORTED
        else f"{name} returned incomplete information. No result was recorded."
        if failed.get("output_truncated")
        else f"{name} could not be read. Check the technical details and try again."
    )
    return SourceResult(
        source_id, name, scope, state, message, utc_now(), int((time.monotonic() - started) * 1000),
        evidence={"probe": failed.get("probe_id"), "state": failed.get("state"),
                  "output_truncated": bool(failed.get("output_truncated"))},
    )


@dataclass
class NativePackagesAdapter:
    client: ProbeClient
    source_id: str = "native"
    name: str = "System packages"
    scope: str = "system"

    def check(self) -> SourceResult:
        started = time.monotonic()
        report = self.client.run(["pacman-installed", "pacman-foreign", "pacman-version", "native-updates"])
        values = _results(report)
        required = [values[key] for key in ("pacman-installed", "pacman-foreign", "pacman-version")]
        failure = _failure(self.source_id, self.name, self.scope, started, required)
        if failure:
            return failure
        foreign = {line.rsplit(maxsplit=1)[0] for line in values["pacman-foreign"]["stdout"].splitlines() if line.strip()}
        try:
            software = parse_pacman_packages(values["pacman-installed"]["stdout"], foreign)
        except ProviderOutputError as error:
            return SourceResult(self.source_id, self.name, self.scope, SourceState.ERROR,
                                "System package information was incomplete. No update result was recorded.",
                                utc_now(), int((time.monotonic() - started) * 1000), evidence={"error": str(error)})
        update_result = values["native-updates"]
        if update_result.get("state") != "completed" or update_result.get("output_truncated"):
            return SourceResult(
                self.source_id, self.name, self.scope, SourceState.NOT_CHECKED,
                "Installed software was recorded. Update availability could not be checked safely.", utc_now(),
                int((time.monotonic() - started) * 1000), software=software,
                tool_version=values["pacman-version"]["stdout"].splitlines()[0][:120],
                evidence={"read_only": True, "foreign_count": len(foreign),
                          "update_probe_state": update_result.get("state")},
            )
        try:
            updates = parse_package_updates(update_result["stdout"], "native", "system")
        except ProviderOutputError as error:
            return SourceResult(self.source_id, self.name, self.scope, SourceState.ERROR,
                                "System update information was incomplete. No update result was recorded.",
                                utc_now(), int((time.monotonic() - started) * 1000), software=software,
                                evidence={"error": str(error), "read_only": True})
        return SourceResult(
            self.source_id, self.name, self.scope,
            SourceState.READY_TO_REVIEW if updates else SourceState.UP_TO_DATE,
            f"{len(updates)} system package updates are ready to review." if updates else
            "No system package updates were reported by the safe check.", utc_now(),
            int((time.monotonic() - started) * 1000), software=software,
            updates=updates,
            tool_version=values["pacman-version"]["stdout"].splitlines()[0][:120],
            evidence={"read_only": True, "foreign_count": len(foreign),
                      "separate_temporary_database": True},
        )


@dataclass
class AurUpdatesAdapter:
    client: ProbeClient
    source_id: str = "aur"
    name: str = "AUR packages"
    scope: str = "user"

    def check(self) -> SourceResult:
        started = time.monotonic()
        values = _results(self.client.run(["aur-updates", "yay-version"]))
        failure = _failure(self.source_id, self.name, self.scope, started, list(values.values()))
        if failure:
            return failure
        try:
            updates = parse_package_updates(values["aur-updates"]["stdout"], self.source_id, self.scope)
        except ProviderOutputError as error:
            return SourceResult(self.source_id, self.name, self.scope, SourceState.ERROR,
                                "AUR update information was incomplete. No result was recorded.", utc_now(),
                                int((time.monotonic() - started) * 1000), evidence={"error": str(error)})
        return SourceResult(
            self.source_id, self.name, self.scope,
            SourceState.READY_TO_REVIEW if updates else SourceState.UP_TO_DATE,
            f"{len(updates)} AUR updates are ready to review." if updates else
            "No AUR updates were reported by the installed helper.", utc_now(),
            int((time.monotonic() - started) * 1000), updates=updates,
            tool_version=values["yay-version"]["stdout"].splitlines()[0][:120],
            evidence={"read_only": True, "helper_query_only": True,
                      "foreign_packages_not_reclassified": True},
        )


@dataclass
class FlatpakAdapter:
    client: ProbeClient
    scope: str
    source_id: str = "flatpak"

    @property
    def name(self) -> str:
        return "Flatpak (current user)" if self.scope == "user" else "Flatpak (whole system)"

    def check(self) -> SourceResult:
        started = time.monotonic()
        probe_id = f"flatpak-{self.scope}-apps"
        remotes_id = f"flatpak-{self.scope}-remotes"
        masks_id = f"flatpak-{self.scope}-masks"
        report = self.client.run([probe_id, remotes_id, masks_id, "flatpak-version"])
        values = _results(report)
        failure = _failure(self.source_id, self.name, self.scope, started, list(values.values()))
        if failure:
            return failure
        try:
            software = parse_flatpak_apps(values[probe_id]["stdout"], self.scope)
            provider_settings = parse_flatpak_settings(
                values[remotes_id]["stdout"], values[masks_id]["stdout"]
            )
        except ProviderOutputError as error:
            return SourceResult(self.source_id, self.name, self.scope, SourceState.ERROR,
                                "Flatpak information was incomplete. No update result was recorded.", utc_now(),
                                int((time.monotonic() - started) * 1000), evidence={"error": str(error)})
        return SourceResult(
            self.source_id, self.name, self.scope, SourceState.NOT_CHECKED,
            "Installed apps were recorded. Update availability was not checked.", utc_now(),
            int((time.monotonic() - started) * 1000), software=software,
            tool_version=values["flatpak-version"]["stdout"].strip()[:120],
            evidence={"read_only": True, **provider_settings},
        )


@dataclass
class FirmwareAdapter:
    client: ProbeClient
    source_id: str = "firmware"
    name: str = "Firmware"
    scope: str = "system"

    def check(self) -> SourceResult:
        started = time.monotonic()
        report = self.client.run(["fwupd-devices", "fwupd-version"])
        values = _results(report)
        failure = _failure(self.source_id, self.name, self.scope, started, list(values.values()))
        if failure:
            return failure
        try:
            software = parse_firmware_devices(values["fwupd-devices"]["stdout"])
        except ProviderOutputError as error:
            return SourceResult(self.source_id, self.name, self.scope, SourceState.ERROR,
                                "Firmware devices could not be read safely.", utc_now(),
                                int((time.monotonic() - started) * 1000), evidence={"error": str(error)})
        return SourceResult(
            self.source_id, self.name, self.scope, SourceState.NOT_CHECKED,
            "Known devices were recorded without refreshing firmware information.", utc_now(),
            int((time.monotonic() - started) * 1000), software=software,
            tool_version=values["fwupd-version"]["stdout"].strip()[:120], evidence={"read_only": True},
        )


@dataclass
class RustToolchainsAdapter:
    client: ProbeClient
    source_id: str = "rustup"
    name: str = "Rust toolchains"
    scope: str = "user"

    def check(self) -> SourceResult:
        started = time.monotonic()
        report = self.client.run(["rustup-toolchains"])
        values = _results(report)
        failure = _failure(self.source_id, self.name, self.scope, started, list(values.values()))
        if failure:
            return failure
        software = parse_rustup_toolchains(values["rustup-toolchains"]["stdout"])
        return SourceResult(
            self.source_id, self.name, self.scope, SourceState.NOT_CHECKED,
            "Installed toolchains were recorded. Update availability was not checked.", utc_now(),
            int((time.monotonic() - started) * 1000), software=software, evidence={"read_only": True},
        )


@dataclass
class CargoToolsAdapter:
    client: ProbeClient
    source_id: str = "cargo"
    name: str = "Cargo-installed tools"
    scope: str = "user"

    def check(self) -> SourceResult:
        started = time.monotonic(); values = _results(self.client.run(["cargo-tools"]))
        failure = _failure(self.source_id, self.name, self.scope, started, list(values.values()))
        if failure: return failure
        software = parse_cargo_tools(values["cargo-tools"]["stdout"])
        return SourceResult(self.source_id, self.name, self.scope, SourceState.NOT_CHECKED,
                            "Installed Cargo tools were recorded. Newer versions were not checked.", utc_now(),
                            int((time.monotonic() - started) * 1000), software=software,
                            evidence={"read_only": True, "empty_is_valid": True})


@dataclass
class FnmAdapter:
    client: ProbeClient
    source_id: str = "fnm"
    name: str = "Node.js from fnm"
    scope: str = "user"

    def check(self) -> SourceResult:
        started = time.monotonic(); values = _results(self.client.run(["fnm-versions"]))
        failure = _failure(self.source_id, self.name, self.scope, started, list(values.values()))
        if failure: return failure
        software = parse_fnm_versions(values["fnm-versions"]["stdout"])
        return SourceResult(self.source_id, self.name, self.scope, SourceState.NOT_CHECKED,
                            "Installed fnm Node.js versions were recorded. Newer versions were not checked.", utc_now(),
                            int((time.monotonic() - started) * 1000), software=software,
                            evidence={"read_only": True, "default_unchanged": True})


@dataclass
class NpmGlobalsAdapter:
    client: ProbeClient
    source_id: str = "npm"
    name: str = "Global npm packages"
    scope: str = "system"

    def check(self) -> SourceResult:
        started = time.monotonic(); values = _results(self.client.run(["npm-root", "npm-globals"]))
        failure = _failure(self.source_id, self.name, self.scope, started, list(values.values()))
        if failure: return failure
        root = values["npm-root"]["stdout"].strip()
        try: software = parse_npm_globals(values["npm-globals"]["stdout"], root)
        except ProviderOutputError as error:
            return SourceResult(self.source_id, self.name, self.scope, SourceState.ERROR,
                                "Global npm package information was incomplete.", utc_now(),
                                int((time.monotonic() - started) * 1000), evidence={"error": str(error)})
        blocked = any(item.ownership == "system_prefix" for item in software)
        return SourceResult(self.source_id, self.name, self.scope,
                            SourceState.BLOCKED if blocked else SourceState.NOT_CHECKED,
                            "Global packages in a folder reserved for system packages cannot be changed through npm." if blocked else
                            "Global npm packages were recorded. Newer versions were not checked.", utc_now(),
                            int((time.monotonic() - started) * 1000), software=software,
                            evidence={"read_only": True, "ownership_classification": "prefix_only",
                                      "package_owner_checked": False})


@dataclass
class UvToolsAdapter:
    client: ProbeClient
    source_id: str = "uv"
    name: str = "uv tools"
    scope: str = "user"

    def check(self) -> SourceResult:
        started = time.monotonic(); values = _results(self.client.run(["uv-tools"]))
        failure = _failure(self.source_id, self.name, self.scope, started, list(values.values()))
        if failure: return failure
        software = parse_uv_tools(values["uv-tools"]["stdout"])
        return SourceResult(self.source_id, self.name, self.scope, SourceState.NOT_SUPPORTED,
                            "Tools managed by uv were recorded, but Updatarr does not know how uv was installed.",
                            utc_now(), int((time.monotonic() - started) * 1000), software=software,
                            evidence={"read_only": True, "uv_self_update_enabled": False})


@dataclass
class AppImageAdapter:
    client: ProbeClient
    source_id: str = "appimage"
    name: str = "Portable apps"
    scope: str = "user"

    def check(self) -> SourceResult:
        started = time.monotonic(); probe_ids = ["appimages-applications", "appimages-local-bin", "appimages-bin"]
        values = _results(self.client.run(probe_ids))
        failures = [item for item in values.values() if item.get("state") not in {"completed", "not_available"}]
        if failures:
            return _failure(self.source_id, self.name, self.scope, started, failures) or SourceResult(
                self.source_id, self.name, self.scope, SourceState.ERROR,
                "Portable app paths could not be read.", utc_now(), int((time.monotonic() - started) * 1000))
        software = parse_appimage_paths(*(values[item]["stdout"] for item in probe_ids
                                         if values[item].get("state") == "completed"))
        return SourceResult(self.source_id, self.name, self.scope, SourceState.NOT_CHECKED,
                            "Portable app files were recorded. Ownership and update support were not checked.", utc_now(),
                            int((time.monotonic() - started) * 1000), software=software,
                            evidence={"read_only": True, "bounded_paths": True})


@dataclass
class SimulatorAdapter:
    source_id: str
    name: str
    scope: str
    state: SourceState
    software: tuple[SoftwareRecord, ...]
    updates: tuple[DetectedUpdate, ...]
    message: str
    delay_seconds: float = 0.1

    def check(self) -> SourceResult:
        time.sleep(self.delay_seconds)
        return SourceResult(
            self.source_id, self.name, self.scope, self.state, self.message, utc_now(), 12,
            software=self.software, updates=self.updates, tool_version="simulated", evidence={"simulated": True},
        )


def live_adapters() -> list[ProviderAdapter]:
    client = LiveProbeClient()
    return [
        NativePackagesAdapter(client), AurUpdatesAdapter(client),
        FlatpakAdapter(client, "user"), FlatpakAdapter(client, "system"),
        FirmwareAdapter(client), RustToolchainsAdapter(client), CargoToolsAdapter(client), FnmAdapter(client),
        NpmGlobalsAdapter(client), UvToolsAdapter(client), AppImageAdapter(client),
    ]


def simulator_adapters() -> list[ProviderAdapter]:
    rows = [
        ("native", "system", "linux", "Linux", "6.17.2", "6.17.4", True),
        ("native", "system", "firefox", "Firefox", "143.0", "143.0.1", False),
        ("aur", "user", "visual-studio-code-bin", "Visual Studio Code", "1.104.0", "1.104.1", False),
        ("flatpak", "user", "org.kde.kdenlive/x86_64/stable", "Kdenlive", "25.08.1", "25.08.2", False),
    ]
    grouped: dict[tuple[str, str], list[tuple]] = {}
    for row in rows:
        grouped.setdefault((row[0], row[1]), []).append(row)
    names = {"native": "System packages", "aur": "AUR packages", "flatpak": "Flatpak (user)"}
    adapters: list[ProviderAdapter] = []
    for (source_id, scope), values in grouped.items():
        software = tuple(SoftwareRecord(source_id, scope, row[2], row[3], row[4], origin="preview") for row in values)
        updates = tuple(DetectedUpdate(
            stable_id=stable_software_id(source_id, scope, row[2], "preview"), source_id=source_id, scope=scope,
            software_id=row[2], name=row[3], installed_version=row[4], available_version=row[5],
            restart_needed=row[6], summary="Simulated update for interface testing.",
        ) for row in values)
        adapters.append(SimulatorAdapter(source_id, names[source_id], scope, SourceState.READY_TO_REVIEW,
                                         software, updates, "Simulated updates are ready to review."))
    adapters.append(SimulatorAdapter(
        "firmware", "Firmware", "system", SourceState.BLOCKED,
        (SoftwareRecord("firmware", "system", "demo-device", "Example firmware device", "1.0"),),
        (DetectedUpdate(stable_software_id("firmware", "system", "demo-device"), "firmware", "system",
                        "demo-device", "Example firmware device", "1.0", "1.1", SourceState.BLOCKED,
                        restart_needed=True, summary="Connect power before reviewing this simulated update."),),
        "Connect power before this simulated update can be reviewed.",
    ))
    return adapters
