from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any

PLATFORM_PATTERNS = {
    "PS5": re.compile(r"\b(ps5|playstation\s*5|playstation\s+five)\b", re.I),
    "Nintendo Switch 2": re.compile(r"\b(nintendo\s+switch\s*2|switch\s*2)\b", re.I),
}

PRICE_PATTERN = re.compile(
    r"(?<!\w)(?:\$|USD\s*)\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\b\d{1,3}(?:\.\d{2})?\s*(?:USD|dollars)\b",
    re.I,
)

GAME_PATTERNS = [
    re.compile(r"(?P<game>[A-Z][A-Za-z0-9:'\-]+(?:\s+[A-Z0-9][A-Za-z0-9:'\-]+){0,5})\s+(?:for|on)\s+(?:PS5|PlayStation 5|Nintendo Switch 2|Switch 2)", re.I),
    re.compile(r"(?:open world|open-world)\s+(?:game|rpg|adventure|title)\s+(?P<game>[A-Z][A-Za-z0-9:'\-]+(?:\s+[A-Z0-9][A-Za-z0-9:'\-]+){0,4})", re.I),
    re.compile(r"(?P<game>[A-Z][A-Za-z0-9:'\-]+(?:\s+[A-Z0-9][A-Za-z0-9:'\-]+){0,5})\s+(?:is|gets|launches|arrives|announced)", re.I),
]

STOP_GAME_WORDS = {
    "Open World",
    "Nintendo Switch",
    "Nintendo Switch 2",
    "PlayStation 5",
    "PS5",
    "The Game",
    "This Game",
    "New Open",
}


def analyze_text(title: str, summary: str = "") -> dict[str, list[str]]:
    haystack = f"{title}\n{summary}"
    normalized = haystack.lower()
    matched_terms: list[str] = []
    if "open world" in normalized or "open-world" in normalized:
        matched_terms.append("Open World")

    platforms = [
        platform
        for platform, pattern in PLATFORM_PATTERNS.items()
        if pattern.search(haystack)
    ]
    for platform in platforms:
        matched_terms.append(platform)

    prices = unique(PRICE_PATTERN.findall(haystack))
    games = extract_games(haystack)
    tags = classify_tags(haystack, platforms, prices)

    return {
        "matched_terms": unique(matched_terms),
        "platforms": unique(platforms),
        "games": games,
        "prices": prices,
        "tags": tags,
    }


def is_relevant(title: str, summary: str = "") -> bool:
    result = analyze_text(title, summary)
    return "Open World" in result["matched_terms"] and bool(result["platforms"])


def extract_games(text: str) -> list[str]:
    found: list[str] = []
    for pattern in GAME_PATTERNS:
        for match in pattern.finditer(text):
            game = clean_game_name(match.group("game"))
            if game and game not in STOP_GAME_WORDS:
                found.append(game)
    return unique(found)[:5]


def clean_game_name(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value.strip(" -:|.,"))
    cleaned = re.sub(r"\b(?:Review|Preview|Trailer|News|Guide|Update)$", "", cleaned, flags=re.I).strip()
    return cleaned


def classify_tags(text: str, platforms: list[str], prices: list[str]) -> list[str]:
    lower = text.lower()
    tags: list[str] = []
    keyword_map = {
        "release date": ["release date", "launches", "arrives", "coming"],
        "trailer": ["trailer", "showcase", "gameplay"],
        "review": ["review", "hands-on", "preview"],
        "price": ["price", "preorder", "pre-order", "discount", "sale"],
        "exclusive": ["exclusive", "console exclusive"],
        "update": ["update", "patch", "dlc", "expansion"],
    }
    for tag, needles in keyword_map.items():
        if any(needle in lower for needle in needles):
            tags.append(tag)
    if prices and "price" not in tags:
        tags.append("price")
    tags.extend(platforms)
    return unique(tags)


def summarize_articles(rows: list[dict[str, Any]]) -> dict[str, Any]:
    platform_counts = Counter()
    source_counts = Counter()
    tag_counts = Counter()
    game_counts = Counter()
    price_rows: list[dict[str, Any]] = []

    for row in rows:
        for platform in row.get("platforms", []):
            platform_counts[platform] += 1
        for tag in row.get("tags", []):
            tag_counts[tag] += 1
        for game in row.get("games", []) or ["Unclassified"]:
            game_counts[game] += 1
        source_counts[row.get("source", "Unknown")] += 1
        if row.get("prices"):
            price_rows.append(row)

    by_platform: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        for platform in row.get("platforms", ["Unclassified"]):
            by_platform[platform].append(row)

    return {
        "total_articles": len(rows),
        "platform_counts": dict(platform_counts),
        "source_counts": dict(source_counts),
        "tag_counts": dict(tag_counts),
        "game_counts": dict(game_counts.most_common(20)),
        "price_signal_count": len(price_rows),
        "latest_price_signals": price_rows[:20],
        "by_platform": {key: len(value) for key, value in by_platform.items()},
    }


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        normalized = value.strip()
        key = normalized.casefold()
        if normalized and key not in seen:
            seen.add(key)
            output.append(normalized)
    return output
