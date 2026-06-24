from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .models import Article


FIELDNAMES = [
    "id",
    "title",
    "url",
    "source",
    "published",
    "summary",
    "matched_terms",
    "platforms",
    "games",
    "prices",
    "tags",
    "collected_at",
]


def ensure_data_dir(data_dir: Path) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)


def append_articles(data_dir: Path, articles: list[Article]) -> list[dict[str, Any]]:
    data_path = ensure_data_dir(data_dir) / "articles.json"
    existing: list[dict[str, Any]] = load_json(data_path, [])
    by_id = {item["id"]: item for item in existing}
    for article in articles:
        by_id[article.id] = article.to_dict()
    merged = sorted(by_id.values(), key=lambda item: item.get("published") or "", reverse=True)
    save_json(data_path, merged)
    export_csv(data_dir / "articles.csv", merged)
    return merged


def save_scan_history(data_dir: Path, scan: dict[str, Any]) -> list[dict[str, Any]]:
    history_path = ensure_data_dir(data_dir) / "scan_history.json"
    history: list[dict[str, Any]] = load_json(history_path, [])
    history.insert(0, scan)
    history = history[:52]
    save_json(history_path, history)
    return history


def export_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_value(row.get(field, "")) for field in FIELDNAMES})


def csv_value(value: Any) -> str:
    if isinstance(value, list):
        return "; ".join(str(item) for item in value)
    if value is None:
        return ""
    return str(value)
