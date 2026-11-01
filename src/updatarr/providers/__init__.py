"""Read-only update-source Adapters for the inventory Seam."""

from .adapters import (
    AurUpdatesAdapter, FirmwareAdapter,
    FlatpakAdapter,
    NativePackagesAdapter,
    RustToolchainsAdapter,
    SimulatorAdapter,
    live_adapters,
    simulator_adapters,
)
from .base import ProviderAdapter

__all__ = [
    "AurUpdatesAdapter", "FirmwareAdapter", "FlatpakAdapter", "NativePackagesAdapter", "ProviderAdapter",
    "RustToolchainsAdapter", "SimulatorAdapter", "live_adapters", "simulator_adapters",
]
