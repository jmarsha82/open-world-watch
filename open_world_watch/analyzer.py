from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any

PLATFORM_PATTERNS = {
    "PS5": re.compile(r"\b(ps5|playstation\s*5|playstation\s+five)\b", re.I),
    "PlayStation": re.compile(r"\b(playstation|ps4|ps6|playstation\s*4|playstation\s*6)\b", re.I),
    "Nintendo Switch 2": re.compile(r"\b(nintendo\s+switch\s*2|switch\s*2)\b", re.I),
    "Nintendo Switch": re.compile(r"\b(nintendo\s+switch|switch)\b", re.I),
    "Xbox Series X|S": re.compile(r"\b(xbox\s+series\s+(?:x|s|x\s*/\s*s|x\|s)|series\s+(?:x|s))\b", re.I),
    "Xbox": re.compile(r"\b(xbox|game\s+pass)\b", re.I),
    "PC": re.compile(r"\b(pc|windows\s+pc|steam|epic\s+games\s+store|gog)\b", re.I),
    "Steam Deck": re.compile(r"\b(steam\s+deck|steamdeck)\b", re.I),
}

SYSTEM_NEWS_PATTERN = re.compile(
    r"\b("
    r"new\s+(?:gaming\s+)?(?:console|system|hardware|handheld|device)|"
    r"next[-\s]?gen\s+(?:console|system|hardware|handheld|device)|"
    r"gaming\s+(?:console|system|hardware|handheld|device)|"
    r"console\s+(?:launch|reveal|announcement|announced|rumor|leak|hardware)|"
    r"hardware\s+(?:launch|reveal|announcement|announced|rumor|leak)|"
    r"handheld\s+(?:console|gaming|pc|device)|"
    r"successor"
    r")\b",
    re.I,
)

PRICE_PATTERN = re.compile(
    r"(?<!\w)(?:\$|USD\s*)\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\b\d{1,3}(?:\.\d{2})?\s*(?:USD|dollars)\b",
    re.I,
)

GAME_PATTERNS = [
    re.compile(
        r"(?P<game>[A-Z][A-Za-z0-9:'\-]+(?:\s+[A-Z0-9][A-Za-z0-9:'\-]+){0,5})\s+"
        r"(?:launches|arrives|announced|revealed|delayed|gets|receives)\b.*?\b(?:for|on)\s+"
        r"(?:PS5|PlayStation 5|PlayStation|Nintendo Switch 2|Switch 2|Nintendo Switch|Xbox Series X|Xbox Series S|Xbox|PC|Steam|Steam Deck)",
        re.I,
    ),
    re.compile(
        r"(?P<game>[A-Z][A-Za-z0-9:'\-]+(?:\s+[A-Z0-9][A-Za-z0-9:'\-]+){0,5})\s+(?:for|on)\s+"
        r"(?:PS5|PlayStation 5|PlayStation|Nintendo Switch 2|Switch 2|Nintendo Switch|Xbox Series X|Xbox Series S|Xbox|PC|Steam|Steam Deck)",
        re.I,
    ),
    re.compile(r"(?:open world|open-world)\s+(?:game|rpg|adventure|title)\s+(?!for\b|on\b)(?P<game>[A-Z][A-Za-z0-9:'\-]+(?:\s+[A-Z0-9][A-Za-z0-9:'\-]+){0,4})", re.I),
]

STOP_GAME_WORDS = {
    "A New",
    "An Open",
    "Gaming System",
    "Open World",
    "Open World Game",
    "Open World RPG",
    "Open World Adventure",
    "Nintendo Switch",
    "Nintendo Switch 2",
    "PlayStation 5",
    "PlayStation",
    "PS5",
    "Xbox",
    "Xbox Series X",
    "Xbox Series S",
    "PC",
    "Steam Deck",
    "The Game",
    "This Game",
    "New Open",
    "New Xbox",
}


def analyze_text(title: str, summary: str = "") -> dict[str, list[str]]:
    haystack = f"{title}\n{summary}"
    normalized = haystack.lower()
    matched_terms: list[str] = []
    if "open world" in normalized or "open-world" in normalized:
        matched_terms.append("Open World")
    if SYSTEM_NEWS_PATTERN.search(haystack):
        matched_terms.append("Gaming System News")

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


def is_relevant(title: str, summary: str = "", query: str = "") -> bool:
    if query:
        return matches_query(title, summary, query)
    result = analyze_text(title, summary)
    if not result["platforms"]:
        return False
    return "Open World" in result["matched_terms"] or "Gaming System News" in result["matched_terms"]


def extract_games(text: str) -> list[str]:
    found: list[str] = []
    for pattern in GAME_PATTERNS:
        for match in pattern.finditer(text):
            game = clean_game_name(match.group("game"))
            if is_likely_game_name(game):
                found.append(game)
    return unique(found)[:5]


def clean_game_name(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value.strip(" -:|.,"))
    cleaned = re.sub(r"\b(?:Review|Preview|Trailer|News|Guide|Update)$", "", cleaned, flags=re.I).strip()
    cleaned = re.sub(r"^(?:new|upcoming|the)\s+", "", cleaned, flags=re.I).strip()
    return cleaned


def is_likely_game_name(value: str) -> bool:
    if not value or value in STOP_GAME_WORDS:
        return False
    words = value.split()
    if len(words) < 2:
        return False
    lowered = value.lower()
    blocked_fragments = ["open world", "gaming system", "console", "hardware", "platform"]
    return not any(fragment in lowered for fragment in blocked_fragments)


def query_keywords(query: str) -> list[str]:
    stop_words = {"a", "an", "and", "for", "from", "in", "new", "of", "on", "or", "the", "to", "with"}
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9+'-]*", query.lower())
    return unique([word for word in words if len(word) > 2 and word not in stop_words])


def matches_query(title: str, summary: str, query: str) -> bool:
    keywords = query_keywords(query)
    if not keywords:
        return False
    haystack = f"{title}\n{summary}".lower()
    return all(keyword in haystack for keyword in keywords)


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
        "system news": ["console", "hardware", "handheld", "system", "next-gen", "next gen"],
        "pc": ["pc", "steam", "windows"],
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
        for game in row.get("games", []):
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
