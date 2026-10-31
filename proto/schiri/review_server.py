"""Tiny local web server for the swipe review. Serves the UI, scenes, clips (with Range support)
and stores reviews in data/matches/<id>/reviews.json."""
from __future__ import annotations

import json
import mimetypes
import re
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from .config import DATA_DIR, REVIEW_DIR

_lock = threading.Lock()
SAFE = re.compile(r"^[A-Za-z0-9_.-]+$")


def _match_path(match_id: str) -> Path:
    if not SAFE.match(match_id):
        raise ValueError("bad id")
    return DATA_DIR / match_id


class Handler(BaseHTTPRequestHandler):
    server_version = "SchiriReview/0.1"

    def log_message(self, fmt, *args):  # quieter console
        pass

    def _json(self, data, status=HTTPStatus.OK):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path):
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        size = path.stat().st_size
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        status = HTTPStatus.OK
        if rng and (m := re.match(r"bytes=(\d*)-(\d*)", rng)):
            if m.group(1):
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else size - 1
            else:
                start = max(0, size - int(m.group(2)))
            end = min(end, size - 1)
            status = HTTPStatus.PARTIAL_CONTENT
        length = end - start + 1
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if status == HTTPStatus.PARTIAL_CONTENT:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with path.open("rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(1 << 16, remaining))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                remaining -= len(chunk)

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        try:
            if path in ("/", "/index.html"):
                return self._file(REVIEW_DIR / "index.html")
            if path == "/api/matches":
                out = []
                if DATA_DIR.exists():
                    for d in sorted(DATA_DIR.iterdir()):
                        f = d / "scenes.json"
                        if f.exists():
                            data = json.loads(f.read_text(encoding="utf-8"))
                            reviews = _load_reviews(d)
                            out.append({"id": d.name, "match": data.get("match", {}),
                                        "scenes": len(data["scenes"]), "reviewed": len(reviews)})
                return self._json(out)
            if m := re.match(r"^/api/matches/([^/]+)$", path):
                d = _match_path(m.group(1))
                data = json.loads((d / "scenes.json").read_text(encoding="utf-8"))
                data["reviews"] = _load_reviews(d)
                return self._json(data)
            if m := re.match(r"^/media/([^/]+)/clips/([^/]+)$", path):
                d = _match_path(m.group(1))
                if not SAFE.match(m.group(2)):
                    raise ValueError("bad file")
                return self._file(d / "clips" / m.group(2))
            self.send_error(HTTPStatus.NOT_FOUND)
        except (ValueError, FileNotFoundError):
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self):
        path = urlparse(self.path).path
        m = re.match(r"^/api/matches/([^/]+)/reviews$", path)
        if not m:
            return self.send_error(HTTPStatus.NOT_FOUND)
        try:
            d = _match_path(m.group(1))
            length = int(self.headers.get("Content-Length", 0))
            if length > 100_000:
                return self.send_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            review = json.loads(self.rfile.read(length) or b"{}")
            scene_id = str(review.get("scene_id", ""))
            role = review.get("role", "self")
            if not SAFE.match(scene_id) or role not in ("self", "observer"):
                return self._json({"error": "ungültig"}, HTTPStatus.BAD_REQUEST)
            allowed = {"action", "decision", "foul_type", "sanction", "comment", "agrees_with_ai", "referee_correct", "role", "scene_id"}
            review = {k: v for k, v in review.items() if k in allowed}
            review["saved_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            with _lock:
                reviews = _load_reviews(d)
                reviews[f"{scene_id}:{role}"] = review
                (d / "reviews.json").write_text(json.dumps(reviews, indent=2, ensure_ascii=False), encoding="utf-8")
            return self._json({"ok": True})
        except (ValueError, json.JSONDecodeError):
            return self._json({"error": "ungültig"}, HTTPStatus.BAD_REQUEST)


def _load_reviews(d: Path) -> dict:
    f = d / "reviews.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    httpd = ThreadingHTTPServer((host, port), Handler)
    shown = "localhost" if host in ("127.0.0.1", "0.0.0.0") else host
    print(f"Sichtung läuft: http://{shown}:{port}  (Beenden mit Strg+C)")
    if host == "0.0.0.0":
        print("Vom Handy im selben WLAN: http://<IP-dieses-PCs>:%d" % port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
