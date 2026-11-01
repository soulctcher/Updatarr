"""Advisory Module: bounded official notices with explicit provenance."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from .catalog import plain_text
from .domain import Advisory, utc_now


class AdvisoryAdapter(Protocol):
    source_id: str
    source_name: str

    def read(self, limit: int) -> tuple[Advisory, ...]:
        ...


def _advisory_id(source_id: str, source_url: str) -> str:
    return sha256(f"{source_id}\0{source_url}".encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SimulatorAdvisoryAdapter:
    source_id: str = "arch-news"
    source_name: str = "Arch Linux news"

    def read(self, limit: int) -> tuple[Advisory, ...]:
        url = "https://archlinux.org/news/"
        return (Advisory(
            _advisory_id(self.source_id, url), self.source_id, self.source_name,
            "Example notice requiring review",
            "This simulated notice shows where official manual steps would appear before an update.",
            url, None, utc_now(), "general_notice", True,
            sha256(b"Example notice requiring review\0This simulated notice shows where official manual steps would appear before an update.").hexdigest(),
            "parsed",
        ),)[:limit]


@dataclass(frozen=True)
class ArchNewsAdapter:
    source_id: str = "arch-news"
    source_name: str = "Arch Linux news"

    def read(self, limit: int) -> tuple[Advisory, ...]:
        request = Request(
            "https://archlinux.org/feeds/news/",
            headers={"Accept": "application/rss+xml, application/xml", "User-Agent": "Updatarr/0.1"},
        )
        with urlopen(request, timeout=8) as response:
            final = urlparse(response.geturl())
            if final.scheme != "https" or final.hostname != "archlinux.org":
                raise ValueError("Arch news response left the fixed source boundary.")
            payload = response.read(1_000_001)
        if len(payload) > 1_000_000:
            raise ValueError("Arch news exceeded the safe size limit.")
        return _parse_arch_news(payload, limit, self.source_id, self.source_name)


def _parse_arch_news(
    payload: bytes, limit: int, source_id: str = "arch-news", source_name: str = "Arch Linux news"
) -> tuple[Advisory, ...]:
    root = ET.fromstring(payload)
    channel = root.find("./channel")
    if channel is None:
        raise ValueError("Arch news response did not contain an RSS channel.")
    items: list[Advisory] = []
    raw_items = channel.findall("./item")[:limit]
    for item in raw_items:
        title = plain_text(item.findtext("title"), limit=300)
        summary = plain_text(item.findtext("description"), limit=1200)
        link = (item.findtext("link") or "").strip()
        parsed = urlparse(link)
        if not title or not summary or parsed.scheme != "https" or parsed.hostname != "archlinux.org":
            raise ValueError("Arch news response contained an unsafe or incomplete item.")
        items.append(Advisory(
            _advisory_id(source_id, link), source_id, source_name,
            title, summary, link, item.findtext("pubDate"), utc_now(), "general_notice",
            False,
            sha256(f"{title}\0{summary}\0{link}".encode("utf-8")).hexdigest(),
            "parsed",
        ))
    return tuple(items)


class AdvisoryService:
    def __init__(self, adapters: list[AdvisoryAdapter]) -> None:
        self.adapters = adapters

    def read(self, limit: int = 10) -> dict[str, object]:
        items: list[Advisory] = []
        sources: list[dict[str, str]] = []
        for adapter in self.adapters:
            try:
                found = adapter.read(limit)
            except Exception:
                sources.append({
                    "source_id": adapter.source_id, "source_name": adapter.source_name,
                    "state": "not_checked", "message": "Notices could not be checked.",
                })
                continue
            items.extend(found)
            sources.append({
                "source_id": adapter.source_id, "source_name": adapter.source_name,
                "state": "source_working", "message": f"{len(found)} notices recorded.",
            })
        items.sort(key=lambda item: item.published_at or "", reverse=True)
        return {"items": [item.to_dict() for item in items[:limit]], "sources": sources}
