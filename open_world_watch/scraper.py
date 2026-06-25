from __future__ import annotations

import hashlib
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from .analyzer import analyze_text, is_relevant
from .models import Article, ScanResult, Source, utc_now_iso
from .storage import append_articles, save_scan_history

DEFAULT_TIMEOUT_SECONDS = 20
USER_AGENT = "OpenWorldWatch/0.1 (+local research scraper; respectful RSS polling)"


def load_sources(path: Path) -> list[Source]:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    return [Source(**item) for item in payload]


def run_scan(source_path: Path, data_dir: Path, limit_per_source: int = 50, query: str = "") -> ScanResult:
    started_at = utc_now_iso()
    run_id = hashlib.sha1(started_at.encode("utf-8")).hexdigest()[:12]
    sources = load_sources(source_path)
    articles: list[Article] = []
    errors: list[dict[str, str]] = []

    for source in sources:
        try:
            entries = fetch_rss_entries(source, limit=limit_per_source)
            for entry in entries:
                article = article_from_entry(source, entry)
                if article and is_relevant(article.title, article.summary, query=query):
                    articles.append(article)
        except (urllib.error.URLError, ET.ParseError, TimeoutError, OSError) as exc:
            errors.append({"source": source.name, "error": str(exc)})
        time.sleep(0.6)

    deduped = dedupe_articles(articles)
    merged_rows = append_articles(data_dir, deduped)
    finished_at = utc_now_iso()
    scan = ScanResult(
        run_id=run_id,
        started_at=started_at,
        finished_at=finished_at,
        sources_checked=len(sources),
        articles_found=len(deduped),
        errors=errors,
        articles=deduped,
    )
    history_payload = scan.to_dict()
    history_payload["stored_article_total"] = len(merged_rows)
    save_scan_history(data_dir, history_payload)
    return scan


def fetch_rss_entries(source: Source, limit: int = 50) -> list[dict[str, str]]:
    request = urllib.request.Request(source.url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
        payload = response.read()
    root = ET.fromstring(payload)
    entries = parse_rss(root)
    if not entries:
        entries = parse_atom(root)
    return entries[:limit]


def parse_rss(root: ET.Element) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for item in root.findall(".//item"):
        summary = first_text(item, ["description", "summary", "content:encoded"])
        entries.append(
            {
                "title": text_of(item, "title"),
                "url": text_of(item, "link"),
                "summary": summary,
                "published": first_text(item, ["pubDate", "published", "updated"]),
                "image_url": image_url_from_entry(item, summary),
            }
        )
    return entries


def parse_atom(root: ET.Element) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    namespace = namespace_of(root.tag)
    for entry in root.findall(f".//{namespace}entry"):
        link = ""
        for link_node in entry.findall(f"{namespace}link"):
            href = link_node.attrib.get("href", "")
            rel = link_node.attrib.get("rel", "alternate")
            if href and rel == "alternate":
                link = href
                break
        summary = first_text(entry, [f"{namespace}summary", f"{namespace}content"])
        entries.append(
            {
                "title": text_of(entry, f"{namespace}title"),
                "url": link,
                "summary": summary,
                "published": first_text(entry, [f"{namespace}published", f"{namespace}updated"]),
                "image_url": image_url_from_entry(entry, summary),
            }
        )
    return entries


def article_from_entry(source: Source, entry: dict[str, str]) -> Article | None:
    title = clean_html(entry.get("title", ""))
    url = normalize_url(entry.get("url", ""))
    summary = clean_html(entry.get("summary", ""))
    if not title or not url:
        return None
    analysis = analyze_text(title, summary)
    article_id = hashlib.sha1(f"{source.name}|{url}".encode("utf-8")).hexdigest()
    return Article(
        id=article_id,
        title=title,
        url=url,
        source=source.name,
        published=parse_date(entry.get("published", "")),
        summary=summary[:700],
        matched_terms=analysis["matched_terms"],
        platforms=analysis["platforms"],
        games=analysis["games"],
        prices=analysis["prices"],
        tags=analysis["tags"],
        image_url=normalize_image_url(entry.get("image_url", ""), url),
    )


def dedupe_articles(articles: list[Article]) -> list[Article]:
    by_id: dict[str, Article] = {}
    for article in articles:
        by_id[article.id] = article
    return sorted(by_id.values(), key=lambda article: article.published or "", reverse=True)


def text_of(node: ET.Element, tag: str) -> str:
    found = node.find(tag)
    if found is None:
        found = first_child_by_local_name(node, tag)
    return found.text.strip() if found is not None and found.text else ""


def first_text(node: ET.Element, tags: list[str]) -> str:
    for tag in tags:
        value = text_of(node, tag)
        if value:
            return value
    return ""


def namespace_of(tag: str) -> str:
    match = re.match(r"(\{.+\})", tag)
    return match.group(1) if match else ""


def clean_html(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(without_tags)).strip()


def image_url_from_entry(entry: ET.Element, summary: str) -> str:
    for child in entry.iter():
        tag_name = local_name(child.tag)
        image_url = child.attrib.get("url", "") or child.attrib.get("href", "")
        media_type = child.attrib.get("type", "")
        media_medium = child.attrib.get("medium", "")
        if image_url and tag_name in {"thumbnail", "image"}:
            return image_url
        if image_url and tag_name == "link" and child.attrib.get("rel") == "enclosure" and media_type.startswith("image/"):
            return image_url
        if image_url and tag_name == "content" and (media_medium == "image" or media_type.startswith("image/")):
            return image_url
        if image_url and tag_name == "enclosure" and media_type.startswith("image/"):
            return image_url
    return image_url_from_html(summary)


def image_url_from_html(value: str) -> str:
    match = re.search(r"<img\b[^>]*\bsrc=[\"']?([^\"'\s>]+)", value, re.IGNORECASE)
    return html.unescape(match.group(1)) if match else ""


def normalize_image_url(image_url: str, base_url: str) -> str:
    if not image_url:
        return ""
    return normalize_url(urllib.parse.urljoin(base_url, image_url.strip()))


def first_child_by_local_name(node: ET.Element, tag: str) -> ET.Element | None:
    target_name = local_name(tag)
    for child in node:
        if local_name(child.tag) == target_name:
            return child
    return None


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":", 1)[-1]


def normalize_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url.strip())
    if not parsed.scheme:
        return url.strip()
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    filtered = [(key, value) for key, value in query if not key.lower().startswith("utm_")]
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(filtered), ""))


def parse_date(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    except (TypeError, ValueError, IndexError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()
        except ValueError:
            return value
