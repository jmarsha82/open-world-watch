import csv
import tempfile
import unittest
from pathlib import Path

from open_world_watch.models import Article
from open_world_watch.storage import append_articles, csv_value, export_csv, load_json, save_json


class StorageTests(unittest.TestCase):
    def test_json_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "data.json"
            save_json(path, {"ok": True})
            self.assertEqual(load_json(path, {}), {"ok": True})
            self.assertEqual(load_json(Path(tmp) / "missing.json", []), [])

    def test_csv_value_serializes_lists(self):
        self.assertEqual(csv_value(["PS5", "price"]), "PS5; price")
        self.assertEqual(csv_value(None), "")

    def test_append_articles_dedupes_and_exports_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            article = Article(
                id="abc",
                title="Open world PS5 article",
                url="https://example.com",
                source="Test",
                published="2026-06-23T10:00:00+00:00",
                summary="Summary",
                matched_terms=["Open World", "PS5"],
                platforms=["PS5"],
                games=["Example Game"],
                prices=["$69.99"],
                tags=["price"],
            )

            rows = append_articles(data_dir, [article, article])

            self.assertEqual(len(rows), 1)
            with (data_dir / "articles.csv").open(encoding="utf-8") as file:
                csv_rows = list(csv.DictReader(file))
            self.assertEqual(csv_rows[0]["platforms"], "PS5")

    def test_export_csv_empty_rows_still_writes_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "articles.csv"
            export_csv(path, [])
            self.assertIn("title", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
