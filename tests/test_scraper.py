import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock, patch

from open_world_watch.models import Source
from open_world_watch.scraper import (
    article_from_entry,
    clean_html,
    dedupe_articles,
    fetch_rss_entries,
    normalize_url,
    parse_atom,
    parse_date,
    parse_rss,
    run_scan,
)


class ScraperTests(unittest.TestCase):
    def test_clean_html_and_tracking_url_normalization(self):
        self.assertEqual(clean_html("<p>Open&nbsp;World</p>"), "Open World")
        self.assertEqual(
            normalize_url("https://example.com/a?utm_source=x&id=42#frag"),
            "https://example.com/a?id=42",
        )

    def test_parse_date_handles_rss_dates(self):
        parsed = parse_date("Tue, 23 Jun 2026 12:30:00 GMT")
        self.assertTrue(parsed.startswith("2026-06-23T12:30:00"))

    def test_article_from_entry_extracts_metadata(self):
        article = article_from_entry(
            Source(name="Test Source", url="https://example.com/feed"),
            {
                "title": "Crimson Harbor announced as open world title for PS5",
                "url": "https://example.com/story?utm_campaign=nope",
                "summary": "Launch price is USD 59.99.",
                "published": "2026-06-23T10:00:00+00:00",
            },
        )

        self.assertIsNotNone(article)
        assert article is not None
        self.assertEqual(article.source, "Test Source")
        self.assertEqual(article.url, "https://example.com/story")
        self.assertIn("PS5", article.platforms)
        self.assertIn("USD 59.99", article.prices)

    def test_dedupe_articles_uses_article_id(self):
        source = Source(name="Test", url="https://example.com")
        first = article_from_entry(source, {"title": "Open world PS5 one", "url": "https://x.test/a", "summary": "", "published": ""})
        second = article_from_entry(source, {"title": "Open world PS5 two", "url": "https://x.test/a", "summary": "", "published": ""})
        assert first is not None and second is not None

        deduped = dedupe_articles([first, second])

        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0].title, "Open world PS5 two")

    def test_parse_rss_items(self):
        import xml.etree.ElementTree as ET

        root = ET.fromstring(
            """
            <rss><channel>
              <item>
                <title>Open world PS5 report</title>
                <link>https://example.com/report</link>
                <description>Summary</description>
                <pubDate>Tue, 23 Jun 2026 12:30:00 GMT</pubDate>
              </item>
            </channel></rss>
            """
        )

        entries = parse_rss(root)

        self.assertEqual(entries[0]["title"], "Open world PS5 report")
        self.assertEqual(entries[0]["url"], "https://example.com/report")

    def test_parse_atom_items(self):
        import xml.etree.ElementTree as ET

        root = ET.fromstring(
            """
            <feed xmlns="http://www.w3.org/2005/Atom">
              <entry>
                <title>Open world Switch 2 report</title>
                <link href="https://example.com/atom" rel="alternate" />
                <summary>Summary</summary>
                <updated>2026-06-23T12:30:00+00:00</updated>
              </entry>
            </feed>
            """
        )

        entries = parse_atom(root)

        self.assertEqual(entries[0]["title"], "Open world Switch 2 report")
        self.assertEqual(entries[0]["url"], "https://example.com/atom")

    @patch("open_world_watch.scraper.urllib.request.urlopen")
    def test_fetch_rss_entries_falls_back_to_atom(self, urlopen):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=None)
        response.read.return_value = b"""
            <feed xmlns="http://www.w3.org/2005/Atom">
              <entry>
                <title>Open world PS5 atom report</title>
                <link href="https://example.com/atom" rel="alternate" />
                <summary>Summary</summary>
                <updated>2026-06-23T12:30:00+00:00</updated>
              </entry>
            </feed>
        """
        urlopen.return_value = response

        entries = fetch_rss_entries(Source(name="Atom", url="https://example.com/feed"), limit=1)

        self.assertEqual(entries[0]["url"], "https://example.com/atom")

    @patch("open_world_watch.scraper.fetch_rss_entries")
    def test_run_scan_writes_articles_and_history(self, fetch):
        fetch.return_value = [
            {
                "title": "Crimson Harbor launches as open world game for PS5",
                "url": "https://example.com/crimson",
                "summary": "Price is $69.99.",
                "published": "2026-06-23T10:00:00+00:00",
            },
            {
                "title": "Unrelated game news",
                "url": "https://example.com/nope",
                "summary": "",
                "published": "",
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sources = root / "sources.json"
            sources.write_text('[{"name":"Test","url":"https://example.com/feed","type":"rss"}]', encoding="utf-8")

            scan = run_scan(sources, root)

            self.assertEqual(scan.sources_checked, 1)
            self.assertEqual(scan.articles_found, 1)
            self.assertTrue((root / "articles.json").exists())
            self.assertTrue((root / "articles.csv").exists())
            self.assertTrue((root / "scan_history.json").exists())

    @patch("open_world_watch.scraper.fetch_rss_entries")
    def test_run_scan_records_source_errors(self, fetch):
        fetch.side_effect = urllib.error.URLError("offline")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sources = root / "sources.json"
            sources.write_text('[{"name":"Broken","url":"https://example.com/feed","type":"rss"}]', encoding="utf-8")

            scan = run_scan(sources, root)

            self.assertEqual(scan.articles_found, 0)
            self.assertEqual(scan.errors[0]["source"], "Broken")


if __name__ == "__main__":
    unittest.main()
