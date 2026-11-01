"""Adapter from the M0 trusted probe registry to M1 provider parsers."""

from __future__ import annotations

from typing import Protocol


class ProbeClient(Protocol):
    def run(self, probe_ids: list[str]) -> dict:
        ...


class LiveProbeClient:
    """Run only names already accepted by the closed M0 probe registry."""

    def __init__(self, timeout_seconds: int = 15) -> None:
        self.timeout_seconds = timeout_seconds

    def run(self, probe_ids: list[str]) -> dict:
        from scripts import read_only_capability_probe as probe

        unknown = set(probe_ids).difference(probe.PROBES_BY_ID)
        if unknown:
            raise ValueError(f"unknown read-only probe: {sorted(unknown)}")
        return probe.build_application_report(probe_ids, self.timeout_seconds)


class FixtureProbeClient:
    """Deterministic probe client used by contract and coordinator tests."""

    def __init__(self, results: dict[str, dict]) -> None:
        self.results = results

    def run(self, probe_ids: list[str]) -> dict:
        values = []
        for probe_id in probe_ids:
            value = self.results.get(probe_id)
            if value is None:
                values.append({
                    "probe_id": probe_id, "state": "not_available", "stdout": "", "stderr": "",
                    "exit_code": None, "output_truncated": False,
                })
            else:
                values.append({"probe_id": probe_id, "state": "completed", "stderr": "", "exit_code": 0,
                               "output_truncated": False, **value})
        return {"schema_version": 1, "read_only": True, "results": values}
