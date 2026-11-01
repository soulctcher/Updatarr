"""History Module: bounded, idempotent import of clearly labeled outside activity."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re

from .domain import ExternalHistoryEvent
from .providers.probes import ProbeClient


PACMAN_LINE = re.compile(
    r"^\[(?P<time>[^]]+)] (?:\[ALPM] )?(?P<action>installed|reinstalled|upgraded|downgraded|removed) "
    r"(?P<name>[^ ]+) \((?P<versions>[^)]*)\)$"
)


@dataclass(frozen=True)
class HistoryImportBatch:
    batch_id: str
    source_id: str
    scope: str
    status: str
    requested_range: str
    first_position: str | None
    last_position: str | None
    record_count: int
    skipped_count: int
    reason: str
    observed_at: str

    def to_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class HistorySourceState:
    source_key: str
    device: int
    inode: int
    size: int
    mtime_ns: int
    generation: int
    tail_hash: str


def _versions(action: str, value: str) -> tuple[str | None, str | None]:
    if " -> " in value:
        before, after = value.split(" -> ", 1)
        return before, after
    if action == "installed":
        return None, value
    if action == "reinstalled":
        return value, value
    if action == "removed":
        return value, None
    return None, None


def parse_pacman_history(
    text: str,
    *,
    source_name: str = "/var/log/pacman.log",
    start_position: int = 0,
    source_generation: str = "unspecified",
) -> tuple[ExternalHistoryEvent, ...]:
    events: list[ExternalHistoryEvent] = []
    byte_position = start_position
    for line_number, line in enumerate(text.splitlines(keepends=True), start=1):
        stripped_line = line.rstrip("\r\n")
        match = PACMAN_LINE.fullmatch(line.strip())
        if not match:
            byte_position += len(line.encode("utf-8"))
            continue
        values = match.groupdict()
        before, after = _versions(values["action"], values["versions"])
        dedupe_key = sha256(
            f"pacman\0{source_name}\0{source_generation}\0{byte_position}\0{stripped_line}".encode("utf-8")
        ).hexdigest()
        events.append(ExternalHistoryEvent(
            event_id=f"pacman-{dedupe_key[:24]}",
            dedupe_key=dedupe_key,
            source_id="native",
            scope="system",
            occurred_at=values["time"],
            action=values["action"],
            software_id=values["name"],
            name=values["name"],
            version_before=before,
            version_after=after,
            result="recorded",
            completeness="partial",
            provenance=source_name,
            details={
                "imported": True, "source_line": line_number,
                "source_position": byte_position, "source_generation": source_generation,
            },
        ))
        byte_position += len(line.encode("utf-8"))
    return tuple(events)


def read_pacman_history_report(
    path: Path = Path("/var/log/pacman.log"),
    *,
    max_bytes: int = 5_000_000,
    previous: HistorySourceState | None = None,
) -> tuple[tuple[ExternalHistoryEvent, ...], HistoryImportBatch, HistorySourceState]:
    """Read only a bounded tail; never modify or rotate the original log."""

    with path.open("rb") as handle:
        file_stat = os.fstat(handle.fileno())
        size = file_stat.st_size
        generation = 1 if previous is None else previous.generation
        same_file = (
            previous is not None
            and previous.device == file_stat.st_dev
            and previous.inode == file_stat.st_ino
        )
        continued = False
        if same_file and size >= previous.size:
            boundary_start = max(0, previous.size - 512)
            handle.seek(boundary_start)
            boundary = handle.read(previous.size - boundary_start)
            continued = sha256(boundary).hexdigest() == previous.tail_hash
            if size == previous.size and file_stat.st_mtime_ns != previous.mtime_ns:
                continued = False
        if previous is not None and not (same_file and continued):
            generation += 1
        source_generation = (
            f"device-{file_stat.st_dev}-inode-{file_stat.st_ino}-generation-{generation}"
        )
        handle.seek(0, 2)
        start = max(0, size - max_bytes)
        handle.seek(start)
        raw = handle.read(max_bytes)
        tail_start = max(0, size - 512)
        handle.seek(tail_start)
        tail_hash = sha256(handle.read(size - tail_start)).hexdigest()
    if size > max_bytes:
        first, separator, remainder = raw.partition(b"\n")
        start += len(first) + len(separator)
        raw = remainder
    text = raw.decode("utf-8", errors="replace")
    events = parse_pacman_history(
        text, source_name=str(path), start_position=start,
        source_generation=source_generation,
    )
    line_count = len(text.splitlines())
    observed = events[-1].occurred_at if events else "not available"
    batch = HistoryImportBatch(
        batch_id=sha256(f"pacman\0{path}\0{source_generation}\0{size}\0{start}\0{sha256(raw).hexdigest()}".encode()).hexdigest(),
        source_id="native", scope="system", status="incomplete",
        requested_range=f"last {max_bytes} bytes",
        first_position=str(start), last_position=str(size), record_count=len(events),
        skipped_count=max(0, line_count - len(events)),
        reason=("Only the bounded end of the log was read." if start else
                "Pacman logs can be rotated or removed, so this is partial history."),
        observed_at=observed,
    )
    state = HistorySourceState(
        source_key=str(path), device=file_stat.st_dev, inode=file_stat.st_ino,
        size=size, mtime_ns=file_stat.st_mtime_ns,
        generation=generation, tail_hash=tail_hash,
    )
    return events, batch, state


def read_pacman_history(path: Path = Path("/var/log/pacman.log"), *, max_bytes: int = 5_000_000) -> tuple[ExternalHistoryEvent, ...]:
    return read_pacman_history_report(path, max_bytes=max_bytes)[0]


def parse_flatpak_history(text: str, *, scope: str) -> tuple[ExternalHistoryEvent, ...]:
    try:
        rows = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError("Flatpak history was not valid JSON.") from error
    if not isinstance(rows, list):
        raise ValueError("Flatpak history was not a list.")
    events: list[ExternalHistoryEvent] = []
    occurrences: dict[str, int] = {}
    actions = {"deploy install": "installed", "deploy update": "updated", "uninstall": "removed"}
    for source_position, row in enumerate(rows):
        if not isinstance(row, dict) or row.get("change") not in actions:
            continue
        name = row.get("application")
        time_value = row.get("time")
        if not isinstance(name, str) or not name or not isinstance(time_value, str) or not time_value:
            continue
        reported_scope = row.get("installation")
        if reported_scope != scope:
            raise ValueError("Flatpak history reported a different installation scope.")
        branch = row.get("branch") if isinstance(row.get("branch"), str) else None
        architecture = row.get("arch") if isinstance(row.get("arch"), str) else None
        remote = row.get("remote") if isinstance(row.get("remote"), str) else None
        software_id = "/".join(value for value in (name, architecture, branch) if value)
        canonical = json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        occurrence = occurrences.get(canonical, 0)
        occurrences[canonical] = occurrence + 1
        dedupe_key = sha256(
            f"flatpak\0{scope}\0{canonical}\0{occurrence}".encode("utf-8")
        ).hexdigest()
        events.append(ExternalHistoryEvent(
            event_id=f"flatpak-{dedupe_key[:24]}", dedupe_key=dedupe_key,
            source_id="flatpak", scope=scope, occurred_at=time_value,
            action=actions[str(row["change"])], software_id=software_id, name=name,
            version_before=None, version_after=None, result="recorded",
            completeness="partial", provenance=f"Flatpak {scope} history",
            details={
                "architecture": architecture, "branch": branch, "remote": remote,
                "old_commit": row.get("old-commit"), "new_commit": row.get("new-commit"),
                "source_position": source_position, "identical_occurrence": occurrence,
            },
        ))
    return tuple(events)


def read_flatpak_history(client: ProbeClient) -> tuple[ExternalHistoryEvent, ...]:
    return read_flatpak_history_report(client)[0]


def read_flatpak_history_report(
    client: ProbeClient,
) -> tuple[tuple[ExternalHistoryEvent, ...], tuple[HistoryImportBatch, ...]]:
    report = client.run(["flatpak-user-history", "flatpak-system-history"])
    results = {item["probe_id"]: item for item in report.get("results", [])}
    events: list[ExternalHistoryEvent] = []
    batches: list[HistoryImportBatch] = []
    for scope in ("user", "system"):
        result = results.get(f"flatpak-{scope}-history", {})
        if result.get("state") != "completed" or result.get("output_truncated"):
            batches.append(HistoryImportBatch(
                batch_id=sha256(f"flatpak\0{scope}\0{result.get('state')}\0{result.get('output_truncated')}".encode()).hexdigest(),
                source_id="flatpak", scope=scope, status="failed",
                requested_range="available journal records", first_position=None,
                last_position=None, record_count=0, skipped_count=0,
                reason=("The journal output was cut off." if result.get("output_truncated")
                        else "Flatpak history could not be read."),
                observed_at=str(report.get("captured_at", "not available")),
            ))
            continue
        raw = result.get("stdout", "")
        try:
            parsed = parse_flatpak_history(raw, scope=scope)
        except ValueError:
            batches.append(HistoryImportBatch(
                batch_id=sha256(f"flatpak\0{scope}\0invalid\0{sha256(str(raw).encode()).hexdigest()}".encode()).hexdigest(),
                source_id="flatpak", scope=scope, status="failed",
                requested_range="available journal records", first_position=None,
                last_position=None, record_count=0, skipped_count=0,
                reason="Flatpak history could not be read safely because its format was not recognized.",
                observed_at=str(report.get("captured_at", "not available")),
            ))
            continue
        try:
            row_count = len(json.loads(raw))
        except (json.JSONDecodeError, TypeError):
            row_count = len(parsed)
        events.extend(parsed)
        batches.append(HistoryImportBatch(
            batch_id=sha256(f"flatpak\0{scope}\0{sha256(str(raw).encode()).hexdigest()}".encode()).hexdigest(),
            source_id="flatpak", scope=scope, status="incomplete",
            requested_range="available journal records", first_position="oldest returned record",
            last_position="newest returned record", record_count=len(parsed),
            skipped_count=max(0, row_count - len(parsed)),
            reason="Journal retention is limited and this output has no stable journal cursor.",
            observed_at=str(report.get("captured_at", "not available")),
        ))
    return tuple(events), tuple(batches)


def simulator_history() -> tuple[ExternalHistoryEvent, ...]:
    return parse_pacman_history(
        "\n".join((
            "[2026-10-18T13:04:22-0400] [ALPM] upgraded firefox (143.0-1 -> 143.0.1-1)",
            "[2026-10-18T13:04:23-0400] [ALPM] upgraded linux (6.17.2-1 -> 6.17.4-1)",
            "[2026-10-02T09:12:00-0400] [ALPM] installed kdenlive (25.08.1-1)",
        )),
        source_name="Simulated pacman history",
    )
