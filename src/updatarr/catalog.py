"""Catalog Module: source-qualified search with plain-text provenance."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from html import unescape
from html.parser import HTMLParser
import json
from functools import lru_cache
import re
from typing import Protocol
import unicodedata
from urllib.parse import quote, urlencode, urlparse
from urllib.error import URLError
from urllib.request import Request, urlopen

from .domain import CatalogRecord, ProvenancedNote, utc_now


AUR_PACKAGE_NAME = re.compile(r"^[A-Za-z0-9@._+:-]{1,300}$")


def remove_format_controls(value: str) -> str:
    """Remove invisible direction/format controls from untrusted display text."""

    return "".join(
        character for character in value
        if unicodedata.category(character) != "Cf"
    )


def stable_catalog_id(
    source_id: str,
    scope: str,
    origin: str,
    software_id: str,
    architecture: str | None = None,
    branch: str | None = None,
) -> str:
    raw = "\0".join((source_id, scope, origin, software_id, architecture or "", branch or ""))
    return sha256(raw.encode("utf-8")).hexdigest()


class _PlainText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() in {"script", "style", "template"}:
            self.hidden += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in {"script", "style", "template"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def plain_text(value: str | None, *, limit: int = 1200) -> str | None:
    """Turn untrusted catalog prose into bounded, control-free plain text."""

    if value is None:
        return None
    parser = _PlainText()
    parser.feed(value[: limit * 4])
    cleaned = remove_format_controls(" ".join(unescape(" ".join(parser.parts)).split()))
    cleaned = "".join(character for character in cleaned if ord(character) >= 32).strip()
    return cleaned[:limit] or None


@dataclass(frozen=True)
class CatalogPage:
    items: tuple[CatalogRecord, ...]
    source_states: tuple[dict[str, object], ...]
    query: str
    complete: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "items": [item.to_dict() for item in self.items],
            "sources": list(self.source_states),
            "query": self.query,
            "total": len(self.items),
            "complete": self.complete,
        }


class CatalogAdapter(Protocol):
    source_id: str
    source_name: str
    scope: str
    origin: str

    def search(self, query: str, limit: int) -> tuple[CatalogRecord, ...]:
        ...


@dataclass(frozen=True)
class SimulatorCatalogAdapter:
    source_id: str
    source_name: str
    scope: str
    origin: str
    rows: tuple[tuple[str, str, str, str, str], ...]

    def search(self, query: str, limit: int) -> tuple[CatalogRecord, ...]:
        needle = query.casefold()
        found: list[CatalogRecord] = []
        for software_id, name, version, description, trust in self.rows:
            if needle not in f"{software_id} {name} {description}".casefold():
                continue
            summary = plain_text(description)
            source_url = _simulator_source_url(self.source_id, software_id)
            note = ProvenancedNote(
                text=summary or "No description supplied.",
                source_name=self.source_name,
                source_url=source_url,
                observed_at=utc_now(),
            )
            found.append(CatalogRecord(
                catalog_id=stable_catalog_id(self.source_id, self.scope, self.origin, software_id),
                source_id=self.source_id,
                source_name=self.source_name,
                scope=self.scope,
                origin=self.origin,
                software_id=software_id,
                name=name,
                version=version,
                summary=summary,
                trust=trust,
                note=note,
                metadata={"simulated": True},
                architecture=(software_id.split("/")[1] if self.source_id == "flatpak" and software_id.count("/") >= 2 else None),
                branch=(software_id.split("/")[2] if self.source_id == "flatpak" and software_id.count("/") >= 2 else None),
            ))
            if len(found) >= limit:
                break
        return tuple(found)


def _simulator_source_url(source_id: str, software_id: str) -> str:
    if source_id == "native":
        return f"https://archlinux.org/packages/?q={software_id}"
    if source_id == "aur":
        return f"https://aur.archlinux.org/packages/{software_id}"
    return f"https://flathub.org/apps/{software_id.split('/', 1)[0]}"


class CatalogService:
    def __init__(self, adapters: list[CatalogAdapter]) -> None:
        self.adapters = adapters

    def search(
        self,
        query: str,
        *,
        source_id: str | None = None,
        scope: str | None = None,
        limit: int = 20,
        turned_off: set[tuple[str, str]] | None = None,
    ) -> CatalogPage:
        query = query.strip()
        if len(query) < 2 or len(query) > 100:
            raise ValueError("Enter between 2 and 100 characters.")
        disabled = turned_off or set()
        items: list[CatalogRecord] = []
        states: list[dict[str, object]] = []
        complete = True
        selected = [
            adapter for adapter in self.adapters
            if (source_id is None or adapter.source_id == source_id)
            and (scope is None or adapter.scope == scope)
        ]
        if not selected:
            raise ValueError("Choose an available update source and installation place.")
        per_source_limit = max(1, min(limit, 50))
        for adapter in selected:
            if (adapter.source_id, adapter.scope) in disabled:
                states.append({
                    "source_id": adapter.source_id,
                    "scope": adapter.scope,
                    "state": "turned_off",
                    "message": "This update source is turned off in Settings.",
                })
                continue
            try:
                found = adapter.search(query, per_source_limit + 1)
            except (TimeoutError, URLError):
                complete = False
                states.append({
                    "source_id": adapter.source_id,
                    "scope": adapter.scope,
                    "state": "source_unavailable",
                    "message": "The search source did not answer in time. Try again later.",
                })
                continue
            except ValueError:
                complete = False
                states.append({
                    "source_id": adapter.source_id,
                    "scope": adapter.scope,
                    "state": "error",
                    "message": "The search response could not be read safely.",
                })
                continue
            except Exception:
                complete = False
                states.append({
                    "source_id": adapter.source_id,
                    "scope": adapter.scope,
                    "state": getattr(adapter, "unavailable_state", "source_unavailable"),
                    "message": getattr(
                        adapter, "unavailable_message",
                        "Search information is unavailable. Try again later.",
                    ),
                })
                continue
            cutoff = len(found) > per_source_limit
            if cutoff:
                complete = False
            shown = found[:per_source_limit]
            items.extend(shown)
            states.append({
                "source_id": adapter.source_id,
                "scope": adapter.scope,
                "state": "incomplete" if cutoff else "source_working",
                "message": (
                    f"Showing the first {len(shown)} matching results; more may exist."
                    if cutoff else f"{len(shown)} matching results."
                ),
            })
        items.sort(key=lambda item: (item.name.casefold(), item.source_name, item.scope, item.software_id))
        if len(items) > limit:
            complete = False
        return CatalogPage(tuple(items[:limit]), tuple(states), query, complete)


def _bounded_json(url: str, *, expected_host: str, max_bytes: int = 1_000_000) -> dict:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != expected_host:
        raise ValueError("Catalog URL is outside the fixed source boundary.")
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "Updatarr/0.1"})
    with urlopen(request, timeout=8) as response:
        final = urlparse(response.geturl())
        if final.scheme != "https" or final.hostname != expected_host:
            raise ValueError("Catalog response left the fixed source boundary.")
        payload = response.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise ValueError("Catalog response exceeded the safe size limit.")
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise ValueError("Catalog response was not an object.")
    return value


def aur_build_preview(package: str, *, simulated: bool = False) -> dict[str, object]:
    """Return inert, bounded AUR build instructions; never execute or source them."""

    if not AUR_PACKAGE_NAME.fullmatch(package):
        raise ValueError("Choose a valid AUR package name.")
    source_url = f"https://aur.archlinux.org/cgit/aur.git/plain/PKGBUILD?h={quote(package, safe='')}"
    if simulated:
        content = (
            f"pkgname={package}\n"
            "pkgver=25.12.r42\n"
            "source=('https://example.invalid/source.tar.gz')\n"
            "build() { printf 'Safe preview only'; }\n"
        )
    else:
        request = Request(source_url, headers={"Accept": "text/plain", "User-Agent": "Updatarr/0.2"})
        with urlopen(request, timeout=8) as response:
            final = urlparse(response.geturl())
            if final.scheme != "https" or final.hostname != "aur.archlinux.org":
                raise ValueError("AUR build-file response left the fixed source boundary.")
            payload = response.read(65_537)
        if len(payload) > 65_536:
            raise ValueError("AUR build file exceeded the safe size limit.")
        content = payload.decode("utf-8", errors="replace")
    content = remove_format_controls("".join(
        character for character in content
        if character in "\n\t" or ord(character) >= 32
    ))
    return {
        "package": package,
        "source_url": source_url,
        "observed_at": utc_now(),
        "content": content[:65_536],
        "content_hash": sha256(content.encode("utf-8")).hexdigest(),
        "comparison_state": "no_earlier_copy",
        "message": "Current build instructions are shown. No earlier copy is recorded for comparison.",
        "simulated": simulated,
    }


@lru_cache(maxsize=64)
def _arch_search(query: str, limit: int) -> tuple[CatalogRecord, ...]:
    url = "https://archlinux.org/packages/search/json/?" + urlencode({"q": query, "limit": limit})
    body = _bounded_json(url, expected_host="archlinux.org")
    if body.get("version") != 2 or not isinstance(body.get("results"), list):
        raise ValueError("Arch catalog response version is not supported.")
    records: list[CatalogRecord] = []
    for row in body["results"][:limit]:
        if not isinstance(row, dict):
            continue
        package = str(row.get("pkgname", ""))[:300]
        repository = str(row.get("repo", ""))[:100]
        architecture = str(row.get("arch", ""))[:50]
        if not package or not repository or not architecture:
            continue
        description = plain_text(row.get("pkgdesc") if isinstance(row.get("pkgdesc"), str) else None)
        source_url = f"https://archlinux.org/packages/{quote(repository)}/{quote(architecture)}/{quote(package)}/"
        note = ProvenancedNote(
            text=description or "No description supplied.", source_name="Arch Linux package search",
            source_url=source_url, observed_at=utc_now(),
        )
        records.append(CatalogRecord(
            stable_catalog_id("native", "system", repository, package, architecture),
            "native", "Arch repositories", "system", repository, package, package,
            str(row.get("pkgver"))[:200] if row.get("pkgver") is not None else None,
            description,
            "Official Arch web listing; availability on this computer is not confirmed",
            note,
            {"architecture": architecture, "catalog_origin": "arch_web", "response_version": 2},
            architecture,
        ))
    return tuple(records)


@lru_cache(maxsize=64)
def _aur_search(query: str, limit: int) -> tuple[CatalogRecord, ...]:
    url = f"https://aur.archlinux.org/rpc/v5/search/{quote(query, safe='')}?by=name-desc"
    body = _bounded_json(url, expected_host="aur.archlinux.org")
    if body.get("version") != 5 or body.get("type") != "search" or not isinstance(body.get("results"), list):
        raise ValueError("AUR catalog response version is not supported.")
    records: list[CatalogRecord] = []
    for row in body["results"][:limit]:
        if not isinstance(row, dict):
            continue
        package = str(row.get("Name", ""))[:300]
        if not package:
            continue
        description = plain_text(row.get("Description") if isinstance(row.get("Description"), str) else None)
        source_url = f"https://aur.archlinux.org/packages/{quote(package, safe='')}"
        note = ProvenancedNote(
            text=description or "No description supplied.", source_name="AUR (user-submitted)",
            source_url=source_url, observed_at=utc_now(),
        )
        metadata = {
            "maintainer": plain_text(str(row["Maintainer"]), limit=200) if row.get("Maintainer") else None,
            "out_of_date": row.get("OutOfDate"),
            "votes": row.get("NumVotes"),
            "popularity": row.get("Popularity"),
            "last_modified": row.get("LastModified"),
            "catalog_origin": "aur_rpc_v5",
        }
        records.append(CatalogRecord(
            stable_catalog_id("aur", "user", "aur", package),
            "aur", "AUR (user-submitted)", "user", "aur", package, package,
            str(row.get("Version"))[:200] if row.get("Version") is not None else None,
            description,
            "User-submitted build instructions; not audited by Arch Linux",
            note,
            metadata,
        ))
    return tuple(records)


@dataclass(frozen=True)
class ArchWebCatalogAdapter:
    source_id: str = "native"
    source_name: str = "Arch repositories"
    scope: str = "system"
    origin: str = "arch-web"

    def search(self, query: str, limit: int) -> tuple[CatalogRecord, ...]:
        return _arch_search(query.casefold(), limit)


@dataclass(frozen=True)
class AurRpcCatalogAdapter:
    source_id: str = "aur"
    source_name: str = "AUR (user-submitted)"
    scope: str = "user"
    origin: str = "aur"

    def search(self, query: str, limit: int) -> tuple[CatalogRecord, ...]:
        return _aur_search(query.casefold(), limit)


@dataclass(frozen=True)
class BlockedFlatpakCatalogAdapter:
    scope: str
    source_id: str = "flatpak"
    source_name: str = "Flatpak"
    origin: str = "configured-remotes"
    unavailable_message: str = (
        "Live Flatpak search is not checked because the installed command may refresh catalog data."
    )
    unavailable_state: str = "not_checked"

    def search(self, query: str, limit: int) -> tuple[CatalogRecord, ...]:
        raise RuntimeError(self.unavailable_message)


def live_catalog_adapters() -> list[CatalogAdapter]:
    """Safe live searches; Flatpak stays absent because its search may refresh metadata."""

    return [
        ArchWebCatalogAdapter(), AurRpcCatalogAdapter(),
        BlockedFlatpakCatalogAdapter("user"), BlockedFlatpakCatalogAdapter("system"),
    ]


def simulator_catalog_adapters() -> list[CatalogAdapter]:
    return [
        SimulatorCatalogAdapter(
            "native", "Arch repositories", "system", "extra",
            (
                ("kdenlive", "Kdenlive", "25.08.2-1", "Video editor from the signed Arch repositories.", "Official repository"),
                ("firefox", "Firefox", "143.0.1-1", "Web browser from the signed Arch repositories.", "Official repository"),
                ("signal-desktop", "Signal Desktop", "7.70.0-1", "Private messaging desktop application.", "Official repository"),
            ),
        ),
        SimulatorCatalogAdapter(
            "aur", "AUR (user-submitted)", "user", "aur",
            (
                ("kdenlive-git", "Kdenlive development build", "25.12.r42", "Community build instructions. Review the files before building.", "Community build instructions; not audited by Arch"),
                ("visual-studio-code-bin", "Visual Studio Code", "1.104.1-1", "Community build instructions for the vendor binary.", "Community build instructions; not audited by Arch"),
            ),
        ),
        SimulatorCatalogAdapter(
            "flatpak", "Flatpak", "user", "flathub",
            (
                ("org.kde.kdenlive/x86_64/stable", "Kdenlive", "25.08.2", "Sandboxed video editor from Flathub.", "Configured Flatpak remote"),
                ("org.mozilla.firefox/x86_64/stable", "Firefox", "143.0.1", "Sandboxed web browser from Flathub.", "Configured Flatpak remote"),
            ),
        ),
        SimulatorCatalogAdapter(
            "flatpak", "Flatpak", "system", "flathub",
            (
                ("org.kde.kdenlive/x86_64/stable", "Kdenlive", "25.08.2", "System-wide sandboxed video editor from Flathub.", "Configured Flatpak remote"),
            ),
        ),
    ]
