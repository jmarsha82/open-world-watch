import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import open_world_watch.app as app
from open_world_watch.app import OpenWorldWatchHandler, build_parser, main, run_weekly_loop, serve, start_scheduler_thread
from open_world_watch.models import Article, ScanResult
from open_world_watch.storage import save_json


class AppTests(unittest.TestCase):
    def test_build_parser_supports_once_and_weekly(self):
        args = build_parser().parse_args(["--once", "--weekly", "--port", "9000"])

        self.assertTrue(args.once)
        self.assertTrue(args.weekly)
        self.assertEqual(args.port, 9000)

    def test_scheduler_skips_when_disabled(self):
        start_scheduler_thread(False)

    @patch("open_world_watch.app.threading.Thread")
    def test_scheduler_starts_daemon_thread_when_enabled(self, thread_class):
        thread = thread_class.return_value

        start_scheduler_thread(True)

        thread_class.assert_called_once()
        self.assertTrue(thread_class.call_args.kwargs["daemon"])
        thread.start.assert_called_once()

    def test_api_static_and_csv_routes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = root / "data"
            static_dir = root / "static"
            source_path = root / "sources.json"
            data_dir.mkdir()
            static_dir.mkdir()
            source_path.write_text(
                '[{"name":"Test","url":"https://example.com/feed","type":"rss","homepage":"https://example.com/"}]',
                encoding="utf-8",
            )
            (static_dir / "index.html").write_text("<h1>Open World Watch</h1>", encoding="utf-8")
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
            save_json(data_dir / "articles.json", [article.to_dict()])
            save_json(data_dir / "scan_history.json", [])

            old_data, old_source, old_static = app.DATA_DIR, app.SOURCE_PATH, app.STATIC_DIR
            app.DATA_DIR, app.SOURCE_PATH, app.STATIC_DIR = data_dir, source_path, static_dir
            server = ThreadingHTTPServer(("127.0.0.1", 0), OpenWorldWatchHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_address[1]}"
            try:
                self.assertIn("Open World Watch", urllib.request.urlopen(base + "/").read().decode("utf-8"))
                articles = json.loads(urllib.request.urlopen(base + "/api/articles").read().decode("utf-8"))
                summary = json.loads(urllib.request.urlopen(base + "/api/summary").read().decode("utf-8"))
                sources = json.loads(urllib.request.urlopen(base + "/api/sources").read().decode("utf-8"))
                history = json.loads(urllib.request.urlopen(base + "/api/history").read().decode("utf-8"))
                csv_text = urllib.request.urlopen(base + "/export/articles.csv").read().decode("utf-8")

                self.assertEqual(articles[0]["title"], "Open world PS5 article")
                self.assertEqual(summary["total_articles"], 1)
                self.assertEqual(sources[0]["name"], "Test")
                self.assertEqual(sources[0]["homepage"], "https://example.com/")
                self.assertEqual(history, [])
                self.assertIn("Open world PS5 article", csv_text)
                with self.assertRaises(urllib.error.HTTPError) as missing:
                    urllib.request.urlopen(base + "/missing.css")
                self.assertEqual(missing.exception.code, 404)
            finally:
                server.shutdown()
                thread.join(timeout=5)
                app.DATA_DIR, app.SOURCE_PATH, app.STATIC_DIR = old_data, old_source, old_static

    @patch("open_world_watch.app.run_scan")
    def test_post_run_scan_returns_created_payload(self, run_scan):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = root / "data"
            static_dir = root / "static"
            source_path = root / "sources.json"
            data_dir.mkdir()
            static_dir.mkdir()
            source_path.write_text("[]", encoding="utf-8")
            run_scan.return_value = ScanResult(
                run_id="run",
                started_at="2026-06-23T00:00:00+00:00",
                finished_at="2026-06-23T00:00:01+00:00",
                sources_checked=0,
                articles_found=0,
                errors=[],
                articles=[],
            )

            old_data, old_source, old_static = app.DATA_DIR, app.SOURCE_PATH, app.STATIC_DIR
            app.DATA_DIR, app.SOURCE_PATH, app.STATIC_DIR = data_dir, source_path, static_dir
            server = ThreadingHTTPServer(("127.0.0.1", 0), OpenWorldWatchHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            request = urllib.request.Request(
                f"http://127.0.0.1:{server.server_address[1]}/api/run-scan",
                method="POST",
            )
            try:
                response = urllib.request.urlopen(request)
                payload = json.loads(response.read().decode("utf-8"))

                self.assertEqual(response.status, 201)
                self.assertEqual(payload["run_id"], "run")
            finally:
                server.shutdown()
                thread.join(timeout=5)
                app.DATA_DIR, app.SOURCE_PATH, app.STATIC_DIR = old_data, old_source, old_static

    def test_unknown_post_returns_404(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = root / "data"
            static_dir = root / "static"
            source_path = root / "sources.json"
            data_dir.mkdir()
            static_dir.mkdir()
            source_path.write_text("[]", encoding="utf-8")
            old_data, old_source, old_static = app.DATA_DIR, app.SOURCE_PATH, app.STATIC_DIR
            app.DATA_DIR, app.SOURCE_PATH, app.STATIC_DIR = data_dir, source_path, static_dir
            server = ThreadingHTTPServer(("127.0.0.1", 0), OpenWorldWatchHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            request = urllib.request.Request(
                f"http://127.0.0.1:{server.server_address[1]}/unknown",
                method="POST",
            )
            try:
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(request)
                self.assertEqual(error.exception.code, 404)
            finally:
                server.shutdown()
                thread.join(timeout=5)
                app.DATA_DIR, app.SOURCE_PATH, app.STATIC_DIR = old_data, old_source, old_static

    @patch("open_world_watch.app.time.sleep", side_effect=KeyboardInterrupt)
    @patch("open_world_watch.app.run_scan")
    def test_weekly_loop_runs_scan_then_sleeps(self, run_scan_mock, sleep_mock):
        with self.assertRaises(KeyboardInterrupt):
            run_weekly_loop(Path("sources.json"), Path("data"), interval_seconds=3)

        run_scan_mock.assert_called_once_with(Path("sources.json"), Path("data"))
        sleep_mock.assert_called_once_with(3)

    @patch("open_world_watch.app.ThreadingHTTPServer")
    @patch("open_world_watch.app.start_scheduler_thread")
    def test_serve_starts_scheduler_and_server(self, scheduler, server_class):
        server = server_class.return_value

        serve("127.0.0.1", 8766, weekly=True)

        scheduler.assert_called_once_with(True)
        server_class.assert_called_once()
        server.serve_forever.assert_called_once()

    @patch("open_world_watch.app.run_scan")
    def test_main_once_runs_scan_and_prints(self, run_scan_mock):
        run_scan_mock.return_value = ScanResult(
            run_id="run",
            started_at="2026-06-23T00:00:00+00:00",
            finished_at="2026-06-23T00:00:01+00:00",
            sources_checked=0,
            articles_found=0,
            errors=[],
            articles=[],
        )
        with patch.object(sys, "argv", ["open-world-watch", "--once"]):
            main()

        run_scan_mock.assert_called_once()

    @patch("open_world_watch.app.run_scan")
    def test_post_run_scan_passes_custom_query(self, run_scan):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = root / "data"
            static_dir = root / "static"
            source_path = root / "sources.json"
            data_dir.mkdir()
            static_dir.mkdir()
            source_path.write_text("[]", encoding="utf-8")
            run_scan.return_value = ScanResult(
                run_id="run",
                started_at="2026-06-23T00:00:00+00:00",
                finished_at="2026-06-23T00:00:01+00:00",
                sources_checked=0,
                articles_found=0,
                errors=[],
                articles=[],
            )

            old_data, old_source, old_static = app.DATA_DIR, app.SOURCE_PATH, app.STATIC_DIR
            app.DATA_DIR, app.SOURCE_PATH, app.STATIC_DIR = data_dir, source_path, static_dir
            server = ThreadingHTTPServer(("127.0.0.1", 0), OpenWorldWatchHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            request = urllib.request.Request(
                f"http://127.0.0.1:{server.server_address[1]}/api/run-scan",
                data=json.dumps({"query": "Silksong release date"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                response = urllib.request.urlopen(request)

                self.assertEqual(response.status, 201)
                run_scan.assert_called_once_with(source_path, data_dir, query="Silksong release date")
            finally:
                server.shutdown()
                thread.join(timeout=5)
                app.DATA_DIR, app.SOURCE_PATH, app.STATIC_DIR = old_data, old_source, old_static


if __name__ == "__main__":
    unittest.main()
