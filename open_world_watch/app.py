from __future__ import annotations

import argparse
import json
import mimetypes
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .analyzer import summarize_articles
from .scraper import run_scan
from .storage import export_csv, load_json

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SOURCE_PATH = PROJECT_ROOT / "config" / "sources.json"
STATIC_DIR = PROJECT_ROOT / "static"
WEEK_SECONDS = 7 * 24 * 60 * 60


class OpenWorldWatchHandler(BaseHTTPRequestHandler):
    server_version = "OpenWorldWatch/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/articles":
            self.send_json(load_json(DATA_DIR / "articles.json", []))
            return
        if parsed.path == "/api/summary":
            rows = load_json(DATA_DIR / "articles.json", [])
            self.send_json(summarize_articles(rows))
            return
        if parsed.path == "/api/history":
            self.send_json(load_json(DATA_DIR / "scan_history.json", []))
            return
        if parsed.path == "/api/sources":
            self.send_json(load_json(SOURCE_PATH, []))
            return
        if parsed.path == "/export/articles.csv":
            rows = load_json(DATA_DIR / "articles.json", [])
            export_csv(DATA_DIR / "articles.csv", rows)
            self.send_file(DATA_DIR / "articles.csv", "text/csv")
            return
        self.send_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/run-scan":
            payload = self.read_json_body()
            query = str(payload.get("query", "")).strip() if isinstance(payload, dict) else ""
            scan = run_scan(SOURCE_PATH, DATA_DIR, query=query)
            self.send_json(scan.to_dict(), status=HTTPStatus.CREATED)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")

    def read_json_body(self) -> object:
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        if content_length <= 0:
            return {}
        try:
            body = self.rfile.read(content_length)
            return json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    def send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_static(self, path: str) -> None:
        clean_path = "index.html" if path in ("", "/") else path.lstrip("/")
        target = (STATIC_DIR / clean_path).resolve()
        if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_file(target, content_type)

    def send_file(self, target: Path, content_type: str) -> None:
        body = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def run_weekly_loop(source_path: Path = SOURCE_PATH, data_dir: Path = DATA_DIR, interval_seconds: int = WEEK_SECONDS) -> None:
    while True:
        run_scan(source_path, data_dir)
        time.sleep(interval_seconds)


def start_scheduler_thread(enabled: bool) -> None:
    if not enabled:
        return
    thread = threading.Thread(target=run_weekly_loop, daemon=True)
    thread.start()


def serve(host: str, port: int, weekly: bool) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    start_scheduler_thread(weekly)
    server = ThreadingHTTPServer((host, port), OpenWorldWatchHandler)
    print(f"Open World Watch running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Open World Watch news tracker")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    parser.add_argument("--weekly", action="store_true", help="run the scraper every seven days while the server is alive")
    parser.add_argument("--once", action="store_true", help="run one scan and exit")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.once:
        scan = run_scan(SOURCE_PATH, DATA_DIR)
        print(json.dumps(scan.to_dict(), indent=2))
        return
    serve(args.host, args.port, args.weekly)


if __name__ == "__main__":
    main()
