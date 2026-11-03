"""M4 safety classification for firmware, boot, portable apps and tools.

The public interface returns presentation-ready facts.  Adapters and tests feed
it observed data; it never constructs commands or mutates provider state.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
import hashlib
import json
from pathlib import PurePath
from typing import Any
from urllib.parse import urlparse


class Readiness(StrEnum):
    READY = "ready"
    BLOCKED = "blocked"
    NOT_SUPPORTED = "not_supported"
    NOT_CHECKED = "not_checked"


class RestartAction(StrEnum):
    NONE = "none"
    RESTART = "restart"
    SHUT_DOWN = "shut_down"
    REPLUG = "replug"
    ACTIVATE = "activate"
    OFFLINE = "offline"
    DISAPPEAR = "disappear"
    UNKNOWN = "unknown"


FWUPD_FOLLOW_UP_FLAGS = {
    "needs-reboot": RestartAction.RESTART, "requires-reboot": RestartAction.RESTART,
    "needs-shutdown": RestartAction.SHUT_DOWN, "requires-shutdown": RestartAction.SHUT_DOWN,
    "needs-replug": RestartAction.REPLUG, "requires-replug": RestartAction.REPLUG,
    "wait-for-replug": RestartAction.REPLUG,
    "needs-activation": RestartAction.ACTIVATE, "requires-activation": RestartAction.ACTIVATE,
    "only-offline": RestartAction.OFFLINE,
    "will-disappear": RestartAction.DISAPPEAR,
}
FWUPD_KNOWN_NON_FOLLOW_UP_FLAGS = {
    "internal", "updatable", "require-ac", "locked", "supported",
    "registered", "reported", "notified", "use-runtime-version", "install-parent-first",
    "is-bootloader", "ignore-validation", "trusted", "another-write-required",
    "no-auto-instance-ids", "historical", "ensure-semver", "only-supported",
    "can-verify", "can-verify-image", "dual-image", "self-recovery",
    "usable-during-update", "signed-payload", "unsigned-payload", "affects-fde",
}


@dataclass(frozen=True)
class SafetyCheck:
    check_id: str
    label: str
    state: Readiness
    explanation: str

    def to_dict(self) -> dict[str, str]:
        value = asdict(self)
        value["state"] = self.state.value
        return value


@dataclass(frozen=True)
class M4Capability:
    capability_id: str
    category: str
    name: str
    state: Readiness
    summary: str
    next_step: str
    restart_action: RestartAction = RestartAction.NONE
    checks: tuple[SafetyCheck, ...] = ()
    simulated: bool = False
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "state": self.state.value,
            "restart_action": self.restart_action.value,
            "checks": [check.to_dict() for check in self.checks],
        }


def firmware_restart_action(flags: list[str]) -> RestartAction:
    """Map fwupd release/device flags without treating an unknown flag as safe."""

    normalized = {str(flag).strip().lower().replace("_", "-") for flag in flags}
    actions = tuple(dict.fromkeys(FWUPD_FOLLOW_UP_FLAGS[flag] for flag in normalized
                                  if flag in FWUPD_FOLLOW_UP_FLAGS))
    unknown = normalized - set(FWUPD_FOLLOW_UP_FLAGS) - FWUPD_KNOWN_NON_FOLLOW_UP_FLAGS
    return actions[0] if len(actions) == 1 and not unknown else (
        RestartAction.NONE if not actions and not unknown else RestartAction.UNKNOWN
    )


def firmware_follow_up_actions(flags: list[str]) -> tuple[RestartAction, ...]:
    normalized = [str(flag).strip().lower().replace("_", "-") for flag in flags]
    return tuple(dict.fromkeys(FWUPD_FOLLOW_UP_FLAGS[flag] for flag in normalized
                               if flag in FWUPD_FOLLOW_UP_FLAGS))


def parse_firmware_releases(text: str) -> tuple[dict[str, Any], ...]:
    """Parse bounded fwupd JSON and preserve requirements as explicit facts."""

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError("Firmware update information could not be read.") from error
    devices = payload.get("Devices") if isinstance(payload, dict) else None
    if not isinstance(devices, list):
        raise ValueError("Firmware update information has no device list.")
    releases: list[dict[str, Any]] = []
    for device in devices[:200]:
        if not isinstance(device, dict):
            raise ValueError("A firmware device record is incomplete.")
        device_id = str(device.get("DeviceId") or "").strip()
        if not device_id:
            raise ValueError("A firmware device has no recognizable device ID.")
        for release in device.get("Releases", [])[:50]:
            if not isinstance(release, dict) or not str(release.get("Version") or "").strip():
                raise ValueError("A firmware release record is incomplete.")
            device_flags = device.get("Flags", [])
            release_flags = release.get("Flags", [])
            problems = device.get("Problems", [])
            if not isinstance(device_flags, list) or not isinstance(release_flags, list) or not isinstance(problems, list):
                raise ValueError("A firmware release requirement list is incomplete.")
            flags = [str(value) for value in [*device_flags, *release_flags]]
            normalized_flags = {value.strip().lower().replace("_", "-") for value in flags}
            unknown_flags = sorted(normalized_flags - set(FWUPD_FOLLOW_UP_FLAGS) - FWUPD_KNOWN_NON_FOLLOW_UP_FLAGS)
            checksums = release.get("Checksum", release.get("Checksums", []))
            if isinstance(checksums, str):
                checksums = [checksums]
            requests = release.get("Requests", device.get("Requests", []))
            if isinstance(requests, dict):
                requests = [requests]
            if not isinstance(checksums, list) or not isinstance(requests, list):
                raise ValueError("Firmware trust or consent information is incomplete.")
            remote_id = str(release.get("RemoteId") or "").strip() or None
            release_id = str(release.get("ReleaseId") or release.get("Id") or "").strip() or None
            trusted = release.get("Trusted")
            remote_enabled = release.get("RemoteEnabled")
            battery_level = device.get("BatteryLevel")
            battery_threshold = device.get("BatteryThreshold")
            battery_values_known = (isinstance(battery_level, (int, float)) and not isinstance(battery_level, bool)
                                    and isinstance(battery_threshold, (int, float)) and not isinstance(battery_threshold, bool))
            battery_blocked = battery_values_known and battery_level < battery_threshold
            readiness = "blocked" if problems or unknown_flags or battery_blocked else (
                "not_checked" if not release_id or not checksums or not remote_id
                or not isinstance(trusted, bool) or not isinstance(remote_enabled, bool) else "ready"
            )
            releases.append({
                "device_id": device_id,
                "name": str(device.get("Name") or "Firmware device")[:300],
                "installed_version": str(device.get("Version") or "")[:100] or None,
                "available_version": str(release["Version"])[:100],
                "release_id": release_id,
                "checksums": [str(value)[:300] for value in checksums[:20]],
                "remote_id": remote_id,
                "remote_enabled": remote_enabled if isinstance(remote_enabled, bool) else None,
                "trusted": trusted if isinstance(trusted, bool) else None,
                "battery_level": battery_level,
                "battery_threshold": battery_threshold,
                "battery_blocked": battery_blocked,
                "update_message": str(release.get("UpdateMessage") or "")[:1000] or None,
                "requests": requests[:20],
                "restart_action": firmware_restart_action(flags).value,
                "follow_up_actions": [action.value for action in firmware_follow_up_actions(flags)],
                "unknown_flags": unknown_flags,
                "problems": [str(value)[:300] for value in problems[:20]],
                "flags": flags[:100],
                "readiness": readiness,
            })
    return tuple(releases)


def assess_appimage(path: str, *, package_owner: str | None,
                    update_information: str | None, regular_file: bool = True,
                    symlink: bool = False, ownership_checked: bool = False) -> M4Capability:
    """Classify a portable app before any staged replacement can be planned."""

    name = PurePath(path).name or "Portable app"
    checks = (
        SafetyCheck("regular-file", "App file", Readiness.READY if regular_file and not symlink else Readiness.BLOCKED,
                    "The app must be a regular file, not a link to another file."),
        SafetyCheck("package-owner", "System package owner",
                    Readiness.NOT_CHECKED if not ownership_checked else
                    Readiness.READY if not package_owner else Readiness.BLOCKED,
                    "Package ownership has not been checked." if not ownership_checked else
                    "No system package owns this file." if not package_owner else f"This file belongs to {package_owner}."),
        SafetyCheck("update-information", "Update download information",
                    Readiness.READY if _supported_update_information(update_information) else Readiness.NOT_SUPPORTED,
                    "The app provides a supported place to download its replacement."
                    if _supported_update_information(update_information) else
                    "This app does not declare a supported update source."),
    )
    state = Readiness.READY if all(check.state is Readiness.READY for check in checks) else (
        Readiness.BLOCKED if any(check.state is Readiness.BLOCKED for check in checks) else
        Readiness.NOT_SUPPORTED if any(check.state is Readiness.NOT_SUPPORTED for check in checks) else Readiness.NOT_CHECKED
    )
    return M4Capability(
        f"appimage:{path}", "Portable apps", name, state,
        "Updatarr can download and check a new copy while keeping the current copy for recovery."
        if state is Readiness.READY else "Updatarr will not replace this portable app.",
        "Review the downloaded replacement and recovery copy." if state is Readiness.READY else
        "Use the publisher's instructions or keep managing this file manually.",
        checks=checks,
    )


def _supported_update_information(value: str | None) -> bool:
    if not value or len(value) > 2048 or "\n" in value or "\x00" in value:
        return False
    parts = value.split("|")
    if len(parts) == 2 and parts[0] == "zsync":
        parsed = urlparse(parts[1])
        return parsed.scheme == "https" and bool(parsed.netloc) and parsed.path.endswith(".zsync")
    if len(parts) == 5 and parts[0] == "gh-releases-zsync":
        return all(parts[1:4]) and parts[4].endswith(".zsync") and "/" not in parts[1] + parts[2]
    return False


@dataclass(frozen=True)
class PortableReplacementPlan:
    canonical_path: str
    device: int
    inode: int
    owner_uid: int
    mode: int
    parent_directory: str
    parent_writable: bool
    installed_size: int
    candidate_size: int
    installed_digest: str
    candidate_digest: str
    update_information: str
    trust_policy: str
    trust_verified: bool


@dataclass(frozen=True)
class PortableReplacementResult:
    steps: tuple[str, ...]
    backup_retained: bool
    installed_digest: str


@dataclass(frozen=True)
class MaintenanceCandidate:
    candidate_id: str
    display_name: str
    size_bytes: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MaintenancePreview:
    preview_id: str
    operation: str
    retention: str
    candidates: tuple[MaintenanceCandidate, ...]
    simulated: bool = True

    @property
    def total_bytes(self) -> int:
        return sum(item.size_bytes for item in self.candidates)

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "candidates": [item.to_dict() for item in self.candidates],
                "total_bytes": self.total_bytes, "removal_performed": False}


def prepare_portable_replacement(*, canonical_path: str, installed_bytes: bytes,
                                 candidate_bytes: bytes, device: int, inode: int,
                                 owner_uid: int, mode: int, package_owner: str | None,
                                 update_information: str | None, regular_file: bool = True,
                                 symlink: bool = False, parent_writable: bool = False,
                                 trust_policy: str = "publisher digest", trust_verified: bool = False,
                                 ownership_checked: bool = False) -> PortableReplacementPlan:
    capability = assess_appimage(canonical_path, package_owner=package_owner,
                                 update_information=update_information,
                                 regular_file=regular_file, symlink=symlink,
                                 ownership_checked=ownership_checked)
    if capability.state is not Readiness.READY or update_information is None:
        raise ValueError("This portable app cannot be replaced safely.")
    if (not canonical_path.startswith("/") or ".." in PurePath(canonical_path).parts or device < 0
            or inode <= 0 or owner_uid < 0 or mode & 0o111 == 0 or not parent_writable
            or not trust_policy.strip() or not trust_verified):
        raise ValueError("The portable app file identity is incomplete.")
    if not installed_bytes or not candidate_bytes:
        raise ValueError("Both current and staged portable app content are required.")
    return PortableReplacementPlan(
        canonical_path, device, inode, owner_uid, mode, str(PurePath(canonical_path).parent),
        parent_writable, len(installed_bytes), len(candidate_bytes),
        hashlib.sha256(installed_bytes).hexdigest(),
        hashlib.sha256(candidate_bytes).hexdigest(), update_information, trust_policy, trust_verified,
    )


def simulate_portable_replacement(plan: PortableReplacementPlan, *, observed_installed: bytes,
                                  staged_candidate: bytes, observed_device: int,
                                  observed_inode: int, staged_device: int, observed_mode: int,
                                  replacement_path: str, replacement_bytes: bytes, replacement_mode: int,
                                  replacement_executable: bool) -> PortableReplacementResult:
    """Exercise the verified sequence without touching a filesystem."""

    observed_digest = hashlib.sha256(observed_installed).hexdigest()
    candidate_digest = hashlib.sha256(staged_candidate).hexdigest()
    replacement_digest = hashlib.sha256(replacement_bytes).hexdigest()
    if (observed_digest != plan.installed_digest or candidate_digest != plan.candidate_digest
            or observed_device != plan.device or observed_inode != plan.inode
            or staged_device != plan.device or observed_mode != plan.mode
            or replacement_path != plan.canonical_path
            or replacement_digest != plan.candidate_digest or replacement_mode != plan.mode
            or not replacement_executable or not plan.parent_writable or not plan.trust_verified):
        raise ValueError("The portable app changed after review; prepare a new plan.")
    return PortableReplacementResult(
        ("stage beside current file", "verify staged digest", "retain recovery copy",
         "replace atomically", "verify installed digest and mode"),
        True, candidate_digest,
    )


def assess_boot(*, running_kernel: str, installed_kernels: tuple[str, ...],
                dkms_failures: tuple[str, ...], initramfs_tool: bool,
                boot_loader_known: bool, headers_match: bool | None = None,
                effective_hooks_known: bool | None = None,
                dracut_config_known: bool | None = None,
                boot_artifacts_present: bool | None = None,
                boot_space_sufficient: bool | None = None,
                recovery_available: bool | None = None,
                target_kernel: str | None = None, update_applied: bool = False) -> M4Capability:
    def observed(check_id: str, label: str, value: bool | None, ready: str, blocked: str) -> SafetyCheck:
        return SafetyCheck(check_id, label,
                           Readiness.NOT_CHECKED if value is None else Readiness.READY if value else Readiness.BLOCKED,
                           "This check has not completed." if value is None else ready if value else blocked)
    checks = (
        SafetyCheck("kernel-tree", "Installed kernel files", Readiness.READY if installed_kernels and running_kernel else Readiness.BLOCKED,
                    "Updatarr found both the installed and currently running kernels." if installed_kernels and running_kernel else "Installed or running kernel information is missing."),
        SafetyCheck("dkms", "Driver builds", Readiness.BLOCKED if dkms_failures else Readiness.READY,
                    "A driver build needs attention: " + ", ".join(dkms_failures) if dkms_failures else "No failed driver build was reported."),
        observed("headers", "Files needed to build drivers", headers_match,
                 "The files needed to build drivers for the new kernel were found.",
                 "Files needed to build drivers for the new kernel are missing."),
        SafetyCheck("initramfs", "Startup file builder", Readiness.READY if initramfs_tool else Readiness.BLOCKED,
                    "The dracut startup-file builder is available." if initramfs_tool else "The configured startup-file builder was not found."),
        observed("hooks", "Automatic startup steps", effective_hooks_known,
                 "The automatic startup steps and settings were checked.",
                 "A required automatic startup step is missing or turned off."),
        observed("dracut-config", "Startup file settings", dracut_config_known,
                 "The dracut startup-file settings were recorded.", "The dracut startup-file settings could not be confirmed."),
        SafetyCheck("boot-loader", "Startup program", Readiness.READY if boot_loader_known else Readiness.NOT_CHECKED,
                    "The program that starts the computer was identified." if boot_loader_known else "The program that starts the computer was not identified."),
        observed("boot-artifacts", "Startup files", boot_artifacts_present,
                 "Referenced startup files were found.", "A referenced startup file is missing."),
        observed("boot-space", "Startup file space", boot_space_sufficient,
                 "Enough space was reported for startup files.", "The startup file location does not have enough space."),
        SafetyCheck("recovery", "Recovery option",
                    Readiness.NOT_CHECKED if recovery_available is None else Readiness.READY if recovery_available else Readiness.NOT_SUPPORTED,
                    "Recovery availability was not checked." if recovery_available is None else
                    "A tested recovery path was reported." if recovery_available else "No tested recovery path was found."),
    )
    blocked = any(check.state is Readiness.BLOCKED for check in checks)
    not_checked = any(check.state is Readiness.NOT_CHECKED for check in checks if check.check_id != "recovery")
    state = Readiness.BLOCKED if blocked else Readiness.NOT_CHECKED if not_checked else Readiness.READY
    restart = (RestartAction.RESTART if update_applied and target_kernel is not None
               and target_kernel != running_kernel else RestartAction.NONE)
    return M4Capability(
        "boot-stack", "System startup", "Kernel and startup files", state,
        "Kernel, driver and startup-file checks are reviewed together.",
        "Fix the blocked check before reviewing a startup-related update." if blocked else
        "Review the full system update group and restart only when shown.",
        restart_action=restart, checks=checks,
    )


def firmware_capability(release: dict[str, Any], *, simulated: bool = False) -> M4Capability:
    problems = tuple(str(value) for value in release.get("problems", []))
    unknown_flags = tuple(str(value) for value in release.get("unknown_flags", []))
    battery_level = release.get("battery_level")
    battery_threshold = release.get("battery_threshold")
    battery_known = (isinstance(battery_level, (int, float)) and not isinstance(battery_level, bool)
                     and isinstance(battery_threshold, (int, float)) and not isinstance(battery_threshold, bool))
    remote_enabled = release.get("remote_enabled")
    trusted = release.get("trusted")
    checks = (
        SafetyCheck("requirements", "Device requirements", Readiness.BLOCKED if problems else Readiness.READY,
                    "; ".join(problems) if problems else "The device reported no unmet requirement."),
        SafetyCheck("remote", "Firmware source",
                    Readiness.NOT_CHECKED if remote_enabled is None else Readiness.READY if remote_enabled else Readiness.BLOCKED,
                    "The firmware source state was not reported." if remote_enabled is None else
                    "The recorded firmware source is turned on." if remote_enabled else "The recorded firmware source is turned off."),
        SafetyCheck("trust", "Trusted firmware source",
                    Readiness.NOT_CHECKED if trusted is None else Readiness.READY if trusted else Readiness.BLOCKED,
                    "Firmware source trust was not reported." if trusted is None else
                    "fwupd reported this release from a trusted source." if trusted else
                    "fwupd did not report this release as trusted."),
        SafetyCheck("known-flags", "Known requirements", Readiness.BLOCKED if unknown_flags else Readiness.READY,
                    "Unknown firmware requirements: " + ", ".join(unknown_flags) if unknown_flags else
                    "All recorded firmware requirements are understood."),
        SafetyCheck("battery", "Battery level",
                    Readiness.BLOCKED if release.get("battery_blocked") else
                    Readiness.READY if battery_known else Readiness.NOT_CHECKED,
                    (f"Battery level {battery_level} is below the required "
                     f"{battery_threshold}.") if release.get("battery_blocked") else
                    "The recorded battery level meets the device threshold."
                    if battery_known else
                    "The device did not report both battery level and threshold."),
    )
    state = Readiness.BLOCKED if any(check.state is Readiness.BLOCKED for check in checks) else (
        Readiness.READY if release.get("readiness") == "ready"
        and not any(check.state is Readiness.NOT_CHECKED for check in checks if check.check_id != "battery")
        else Readiness.NOT_CHECKED)
    action = RestartAction(str(release.get("restart_action", "unknown")))
    return M4Capability(
        "firmware:" + str(release.get("device_id", "unknown")), "Firmware",
        str(release.get("name") or "Firmware device"), state,
        "The exact signed firmware update and its device requirements were recorded."
        if state is Readiness.READY else "This firmware update cannot be reviewed until every requirement passes.",
        "Review the device, version, source and required follow-up." if state is Readiness.READY else
        "Fix the problem shown and check the device again.",
        action, checks, simulated, {"release": release},
    )


def simulator_report() -> dict[str, Any]:
    firmware_release = parse_firmware_releases(json.dumps({"Devices": [{
        "DeviceId": "demo-device", "Name": "Example firmware device", "Version": "1.0",
        "Flags": ["needs-reboot"], "Problems": ["External power is not connected."],
        "BatteryLevel": 42, "BatteryThreshold": 50,
        "Releases": [{"Version": "1.1", "ReleaseId": "demo-release-1.1",
                      "Checksum": ["sha256:" + "a" * 64], "RemoteId": "lvfs",
                      "RemoteEnabled": True, "Trusted": True,
                      "UpdateMessage": "Keep the computer connected to power.", "Requests": []}],
    }]}))[0]
    cache_preview = MaintenancePreview(
        "preview-package-cache", "Old package downloads", "Keep the two newest versions",
        (MaintenanceCandidate("cache-linux-6.16", "linux 6.16 package", 180_000_000,
                              "Older than the two retained versions"),
         MaintenanceCandidate("cache-firefox-142", "Firefox 142 package", 145_000_000,
                              "Older than the two retained versions"),
         MaintenanceCandidate("cache-mesa-25.1", "Mesa 25.1 package", 107_000_000,
                              "Older than the two retained versions")),
    )
    capabilities = [
        firmware_capability(firmware_release, simulated=True),
        assess_boot(running_kernel="6.17.2", installed_kernels=("6.17.2", "6.17.4"),
                    dkms_failures=(), initramfs_tool=True, boot_loader_known=True, headers_match=True,
                    effective_hooks_known=True, dracut_config_known=True, boot_artifacts_present=True,
                    boot_space_sufficient=True, recovery_available=False),
        assess_appimage("/home/demo/Applications/Example.AppImage", package_owner=None,
                        update_information="gh-releases-zsync|example|app|latest|Example.AppImage.zsync",
                        ownership_checked=True),
        M4Capability("rustup:stable", "Developer tools", "Rust stable toolchain", Readiness.READY,
                     "rustup manages this user toolchain separately from the pacman-owned launcher.",
                     "Review the toolchain version change.", simulated=True),
        M4Capability("cargo:none", "Developer tools", "Cargo-installed tools", Readiness.NOT_SUPPORTED,
                     "No Cargo-installed tools were found.", "Nothing needs to be changed.", simulated=True),
        M4Capability("fnm:node", "Developer tools", "Node.js from fnm", Readiness.READY,
                     "fnm owns this user runtime. The selected default will not change automatically.",
                     "Choose an exact version and review project compatibility.", simulated=True),
        M4Capability("npm:system", "Developer tools", "Global npm packages", Readiness.BLOCKED,
                     "The recorded global packages are in a folder reserved for system packages.",
                     "Update them with the system package update group.", simulated=True),
        M4Capability("uv:unknown", "Developer tools", "uv tools", Readiness.NOT_SUPPORTED,
                     "No tools managed by uv were found, and Updatarr does not know how uv was installed.",
                     "Record a supported installation method before allowing uv to update itself.", simulated=True),
        M4Capability("maintenance:package-cache", "Maintenance", "Old package downloads", Readiness.READY,
                     "Preview: 3 older package files, 412 MiB. Nothing has been removed.",
                     "Review the file list before separately approving removal.", simulated=True,
                     details={"preview": cache_preview.to_dict()}),
        M4Capability("maintenance:flatpak", "Maintenance", "Unused Flatpak data", Readiness.NOT_CHECKED,
                     "Unused Flatpak data has not been calculated because that check may contact configured sources.",
                     "Run a separately reviewed preview when Updatarr is allowed to contact those sources.", simulated=True),
    ]
    return report(capabilities, simulated=True)


def live_read_only_report(snapshot: Any | None = None) -> dict[str, Any]:
    sources = [] if snapshot is None else list(snapshot.sources)
    def matching(*source_ids: str) -> list[Any]:
        return [source for source in sources if source.source_id in source_ids]
    def observed_capability(identity: str, category: str, name: str, source_ids: tuple[str, ...]) -> M4Capability:
        observed = matching(*source_ids)
        count = sum(len(source.software) for source in observed)
        blocked_sources = [source for source in observed if source.state.value in {"blocked", "error"}]
        blocked = bool(blocked_sources)
        item_word = "item" if count == 1 else "items"
        source_word = "source" if len(observed) == 1 else "sources"
        recorded = (
            f"The read-only software check found {count} installed software {item_word} across "
            f"{len(observed)} related update {source_word}. It did not check for newer versions or "
            "whether changes would be safe."
        )
        if blocked_sources:
            problems = " ".join(f"{source.name} needs attention: {source.message}" for source in blocked_sources)
            recorded = f"{recorded} {problems}"
        return M4Capability(
            identity, category, name, Readiness.BLOCKED if blocked else Readiness.NOT_CHECKED,
            recorded if observed else
            "No matching read-only inventory has completed, so Updatarr does not claim this change is ready.",
            ("No action is available in Updatarr for this result. Follow the update source's message, "
             "then choose Check software again.") if blocked else
            "Complete the source-specific version and safety checks before preparing a plan.",
            details={"observed_sources": [source.to_dict(include_software=False) for source in observed]},
        )
    capabilities = [
        observed_capability("firmware", "Firmware", "Firmware updates", ("firmware",)),
        M4Capability("boot-stack", "System startup", "Kernel and startup files", Readiness.NOT_CHECKED,
                     "The software check does not confirm driver-building files, automatic startup steps, startup files or free space.",
                     "Complete every startup safety check before preparing a startup-related plan."),
        observed_capability("portable-apps", "Portable apps", "Portable apps", ("appimage",)),
        observed_capability("developer-tools", "Developer tools", "Developer tools",
                            ("rustup", "cargo", "fnm", "npm", "uv")),
        M4Capability("maintenance", "Maintenance", "Maintenance preview", Readiness.NOT_CHECKED,
                     "No file-removal preview has been recorded.",
                     "Create a preview file list before reviewing any removal."),
    ]
    return report(capabilities, simulated=False)


def report(capabilities: list[M4Capability], *, simulated: bool) -> dict[str, Any]:
    return {
        "mode": "Safe preview" if simulated else "Read-only",
        "items": [item.to_dict() for item in capabilities],
        "preservation": {
            "package_ownership_changed": False,
            "flatpak_origins_changed": False,
            "host_changes_performed": False,
        },
    }
