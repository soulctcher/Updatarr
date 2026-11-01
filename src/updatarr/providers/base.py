"""The small external Interface at the read-only provider Seam."""

from __future__ import annotations

from typing import Protocol

from ..domain import SourceResult


class ProviderAdapter(Protocol):
    source_id: str
    name: str
    scope: str

    def check(self) -> SourceResult:
        """Return one bounded, truthful read-only observation."""
        ...
