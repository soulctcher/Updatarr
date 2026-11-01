#!/usr/bin/env python3
"""Measure target-scale inventory storage and paging without host mutation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from updatarr.domain import InventorySnapshot, SoftwareRecord, SourceResult, SourceState, utc_now  # noqa: E402
from updatarr.storage import StateStore  # noqa: E402


def _elapsed(action):  # type: ignore[no-untyped-def]
    started = time.perf_counter()
    value = action()
    return (time.perf_counter() - started) * 1000, value


def profile(record_count: int, repetitions: int) -> dict[str, object]:
    records = tuple(
        SoftwareRecord(
            "native", "system", f"package-{index:05d}", f"Package {index:05d}",
            "1.0.0", origin="extra", architecture="x86_64",
            ownership="native_repository",
        )
        for index in range(record_count)
    )
    snapshot = InventorySnapshot.create(utc_now(), [
        SourceResult(
            "native", "System packages", "system", SourceState.UP_TO_DATE,
            "The last check completed.", utc_now(), 1, records, (),
        ),
    ])
    with tempfile.TemporaryDirectory(prefix="updatarr-m6-profile-") as directory:
        path = Path(directory) / "state.db"
        store = StateStore(path)
        store.initialize()
        store_ms, _ = _elapsed(lambda: store.save_snapshot(snapshot))
        first_page: list[float] = []
        filtered_page: list[float] = []
        for _ in range(repetitions):
            duration, page = _elapsed(lambda: store.inventory_page(limit=100, offset=0))
            assert page.total == record_count and len(page.items) == min(record_count, 100)
            first_page.append(duration)
            duration, filtered = _elapsed(
                lambda: store.inventory_page(limit=100, offset=0, query="package-009")
            )
            assert filtered.total == min(100, max(0, record_count - 900))
            assert len(filtered.items) == filtered.total
            filtered_page.append(duration)
        return {
            "records": record_count,
            "database_bytes": path.stat().st_size,
            "store_snapshot_ms": round(store_ms, 3),
            "first_page_median_ms": round(statistics.median(first_page), 3),
            "first_page_max_ms": round(max(first_page), 3),
            "filtered_page_median_ms": round(statistics.median(filtered_page), 3),
            "filtered_page_max_ms": round(max(filtered_page), 3),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=int, default=10_000)
    parser.add_argument("--repetitions", type=int, default=7)
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()
    if args.records < 1 or args.repetitions < 1:
        parser.error("records and repetitions must be positive")
    result = profile(args.records, args.repetitions)
    if args.enforce:
        budget = {
            "store_snapshot_ms": 1_000,
            "first_page_max_ms": 100,
            "filtered_page_max_ms": 150,
            "database_bytes": max(4_000_000, args.records * 1_600),
        }
        failures = {
            key: {"observed": result[key], "maximum": maximum}
            for key, maximum in budget.items()
            if float(result[key]) > maximum
        }
        result["budget_passed"] = not failures
        result["budget_failures"] = failures
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.enforce and not result["budget_passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
