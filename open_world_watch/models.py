from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(slots=True)
class Source:
    name: str
    url: str
    type: str = "rss"
    homepage: str = ""


@dataclass(slots=True)
class Article:
    id: str
    title: str
    url: str
    source: str
    published: str
    summary: str
    matched_terms: list[str]
    platforms: list[str]
    games: list[str]
    prices: list[str]
    tags: list[str] = field(default_factory=list)
    image_url: str = ""
    collected_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ScanResult:
    run_id: str
    started_at: str
    finished_at: str
    sources_checked: int
    articles_found: int
    errors: list[dict[str, str]]
    articles: list[Article]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["articles"] = [article.to_dict() for article in self.articles]
        return payload
