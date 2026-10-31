"""Local web app: create matches, run the analysis, follow progress and review scenes.

Writing endpoints and the file browser answer only to this computer (127.0.0.1), so that
`serve --host 0.0.0.0` for phone access does not expose the file system to the network."""
from __future__ import annotations

import json
import mimetypes
import os
import re
import string
import threading
import time
from datetime import date
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import media, pipeline
from .config import DATA_DIR, PITCH_TYPES, REVIEW_DIR, Settings, pitch_label
from .jobs import JobManager

_lock = threading.Lock()
SAFE = re.compile(r"^[A-Za-z0-9_.-]+$")
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".m4v", ".mts", ".webm"}
META_FIELDS = ("date", "home", "away", "league", "venue", "referee", "assistant1", "assistant2", "notes")
JOBS: JobManager | None = None


def _match_path(match_id: str) -> Path:
    if not SAFE.match(match_id):
        raise ValueError("bad id")
    return DATA_DIR / match_id


def _slug(text: str) -> str:
    text = (text or "").lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:40]


def _load_json(f: Path, default):
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else default


def _load_reviews(d: Path) -> dict:
    return _load_json(d / "reviews.json", {})


def _clean_meta(body: dict, meta: dict) -> dict:
    for k in META_FIELDS:
        if k in body:
            v = str(body.get(k) or "").strip()[:120]
            if v:
                meta[k] = v
            else:
                meta.pop(k, None)
    p = body.get("pitch")
    if isinstance(p, dict):
        pitch = {}
        if p.get("type") in PITCH_TYPES:
            pitch["type"] = p["type"]
        for k, cast in (("players", int), ("length_m", float), ("width_m", float)):
            try:
                if p.get(k) not in (None, ""):
                    pitch[k] = cast(p[k])
            except (TypeError, ValueError):
                pass
        meta["pitch"] = pitch
    return meta


def _save_pitch_preset(meta: dict) -> None:
    venue, p = meta.get("venue"), meta.get("pitch") or {}
    if not venue or not p.get("type"):
        return
    f = DATA_DIR / "plaetze.json"
    with _lock:
        presets = _load_json(f, {})
        presets[venue] = p
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(presets, indent=2, ensure_ascii=False), encoding="utf-8")


def _match_summary(d: Path) -> dict:
    meta = _load_json(d / "match.json", {})
    scenes = _load_json(d / "scenes.json", {}).get("scenes", [])
    reviews = _load_reviews(d)
    job = JOBS.get(d.name) if JOBS else None
    analysis = dict(meta.get("analysis", {}))
    if job:
        analysis.update({"status": job["status"], "step_label": job["step_label"], "error": job["error"],
                         "started_at": job["started_at"], "last_log": job["log"][-1] if job["log"] else "",
                         "cancel_requested": job["cancel_requested"]})
    roles = {"self": 0, "observer": 0}
    for key in reviews:
        role = key.rsplit(":", 1)[-1]
        if role in roles:
            roles[role] += 1
    return {"id": d.name, "match": {k: v for k, v in meta.items() if k != "analysis"},
            "pitch_label": pitch_label(meta), "analysis": analysis, "scenes": len(scenes),
            "whistled": sum(1 for s in scenes if s["type"] == "whistled"),
            "candidates": sum(1 for s in scenes if s["type"] == "candidate"),
            "assessed": sum(1 for s in scenes if s.get("ai")), "reviewed": roles,
            "scanned": (d / "steps" / "gemini_scan" / "result.json").is_file()}


class Handler(BaseHTTPRequestHandler):
    server_version = "SchiriAnalyse/0.2"

    def log_message(self, fmt, *args):
        pass

    @property
    def is_local(self) -> bool:
        return self.client_address[0] in ("127.0.0.1", "::1")

    # ---------- helpers
    def _json(self, data, status=HTTPStatus.OK):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, msg: str, status=HTTPStatus.BAD_REQUEST):
        self._json({"error": msg}, status)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length > 200_000:
            raise ValueError("zu groß")
        return json.loads(self.rfile.read(length) or b"{}")

    def _file(self, path: Path):
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        size = path.stat().st_size
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        rng = self.headers.get("Range")
        start, end, status = 0, size - 1, HTTPStatus.OK
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

    # ---------- GET
    def do_GET(self):
        url = urlparse(self.path)
        path, q = unquote(url.path), parse_qs(url.query)
        try:
            if path in ("/", "/index.html"):
                return self._file(REVIEW_DIR / "index.html")
            if path == "/api/config":
                s = Settings()
                return self._json({
                    "provider": s.provider, "scan_model": s.scan_model, "assess_model": s.assess_model,
                    "assess_model_strong": s.assess_model_strong, "scan_available": s.scan_available(),
                    "assess_available": s.assess_available(), "local": self.is_local,
                    "pitch_types": PITCH_TYPES, "today": date.today().isoformat(),
                    "video_dir": os.environ.get("SCHIRI_VIDEO_DIR", ""),
                })
            if path == "/api/matches":
                out = []
                if DATA_DIR.exists():
                    for d in DATA_DIR.iterdir():
                        if d.is_dir() and (d / "match.json").exists():
                            out.append(_match_summary(d))
                out.sort(key=lambda x: (x["match"].get("date", ""), x["id"]), reverse=True)
                return self._json(out)
            if m := re.match(r"^/api/matches/([^/]+)$", path):
                d = _match_path(m.group(1))
                data = _load_json(d / "scenes.json", None)
                if data is None:
                    return self._error("Noch keine Szenen – Analyse läuft oder ist fehlgeschlagen.", HTTPStatus.NOT_FOUND)
                data["match"] = _load_json(d / "match.json", {})
                data["reviews"] = _load_reviews(d)
                return self._json(data)
            if m := re.match(r"^/api/matches/([^/]+)/job$", path):
                job = JOBS.get(m.group(1)) if JOBS else None
                return self._json({k: v for k, v in job.items() if k != "cancel"} if job else {"status": "none"})
            if path == "/api/suggestions":
                refs, leagues, teams = set(), set(), set()
                if DATA_DIR.exists():
                    for d in DATA_DIR.iterdir():
                        meta = _load_json(d / "match.json", {}) if d.is_dir() else {}
                        refs.update(x for x in (meta.get("referee"), meta.get("assistant1"), meta.get("assistant2")) if x)
                        teams.update(x for x in (meta.get("home"), meta.get("away")) if x)
                        if meta.get("league"):
                            leagues.add(meta["league"])
                return self._json({"referees": sorted(refs), "leagues": sorted(leagues), "teams": sorted(teams),
                                   "venues": _load_json(DATA_DIR / "plaetze.json", {})})
            if path == "/api/browse":
                if not self.is_local:
                    return self._error("Nur am PC selbst verfügbar.", HTTPStatus.FORBIDDEN)
                return self._json(_browse(q.get("path", [""])[0]))
            if path == "/api/probe":
                if not self.is_local:
                    return self._error("Nur am PC selbst verfügbar.", HTTPStatus.FORBIDDEN)
                p = Path(q.get("path", [""])[0]).expanduser()
                if not p.is_file():
                    return self._error("Datei nicht gefunden.")
                info = media.probe(p)
                info["size_mb"] = round(p.stat().st_size / 1e6)
                return self._json(info)
            if m := re.match(r"^/media/([^/]+)/clips/([^/]+)$", path):
                d = _match_path(m.group(1))
                if not SAFE.match(m.group(2)):
                    raise ValueError("bad file")
                return self._file(d / "clips" / m.group(2))
            self.send_error(HTTPStatus.NOT_FOUND)
        except (ValueError, FileNotFoundError):
            self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as e:  # keep the server alive, show the reason
            self._error(str(e), HTTPStatus.INTERNAL_SERVER_ERROR)

    # ---------- POST
    def do_POST(self):
        path = urlparse(self.path).path
        try:
            if m := re.match(r"^/api/matches/([^/]+)/reviews$", path):
                return self._save_review(_match_path(m.group(1)), self._body())
            if not self.is_local:
                return self._error("Nur am PC selbst verfügbar.", HTTPStatus.FORBIDDEN)
            if path == "/api/matches":
                return self._create_match(self._body())
            if m := re.match(r"^/api/matches/([^/]+)/meta$", path):
                return self._update_meta(m.group(1), self._body())
            if m := re.match(r"^/api/matches/([^/]+)/(analyze|assess)$", path):
                return self._start(m.group(1), m.group(2), self._body())
            if m := re.match(r"^/api/matches/([^/]+)/cancel$", path):
                job = JOBS.cancel(m.group(1))
                if not job:
                    return self._error("Für dieses Spiel läuft nichts.", HTTPStatus.NOT_FOUND)
                return self._json({"ok": True, "status": job["status"]})
            self.send_error(HTTPStatus.NOT_FOUND)
        except (ValueError, json.JSONDecodeError) as e:
            self._error(f"Ungültige Anfrage: {e}")

    def _save_review(self, d: Path, review: dict):
        scene_id = str(review.get("scene_id", ""))
        role = review.get("role", "self")
        if not SAFE.match(scene_id) or role not in ("self", "observer"):
            return self._error("ungültig")
        allowed = {"action", "decision", "foul_type", "sanction", "comment", "agrees_with_ai", "referee_correct", "role", "scene_id"}
        review = {k: v for k, v in review.items() if k in allowed}
        review["saved_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        with _lock:
            reviews = _load_reviews(d)
            reviews[f"{scene_id}:{role}"] = review
            (d / "reviews.json").write_text(json.dumps(reviews, indent=2, ensure_ascii=False), encoding="utf-8")
        return self._json({"ok": True})

    def _create_match(self, body: dict):
        video = Path(str(body.get("video_path", "")).strip().strip('"')).expanduser()
        if not video.is_file():
            return self._error("Videodatei nicht gefunden. Bitte den vollständigen Pfad angeben.")
        meta = _clean_meta(body, {})
        if not meta.get("referee"):
            return self._error("Bitte den Schiedsrichter angeben.")
        base = "-".join(x for x in (meta.get("date", ""), _slug(meta.get("home", "")), _slug(meta.get("away", ""))) if x) or _slug(video.stem)
        match_id, n = base, 2
        while (DATA_DIR / match_id).exists():
            match_id, n = f"{base}-{n}", n + 1
        m = pipeline.Match(match_id)
        meta.update({"id": match_id, "video_path": str(video), "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                     "options": _options(body.get("options") or {})})
        m.write_meta(meta)
        _save_pitch_preset(meta)
        self._enqueue(match_id, "analyze", meta["options"])
        return self._json({"ok": True, "id": match_id})

    def _update_meta(self, match_id: str, body: dict):
        m = pipeline.Match(match_id)
        meta = _clean_meta(body, m.meta)
        if not meta.get("referee"):
            return self._error("Bitte den Schiedsrichter angeben.")
        m.write_meta(meta)
        _save_pitch_preset(meta)
        if m.result("clips"):
            pipeline.publish(m)
        return self._json({"ok": True})

    def _start(self, match_id: str, kind: str, body: dict):
        m = pipeline.Match(match_id)
        meta = m.meta
        if not meta:
            return self._error("Spiel nicht gefunden.", HTTPStatus.NOT_FOUND)
        opts = _options({**meta.get("options", {}), **body.get("options", {})}) if body.get("options") else meta.get("options", _options({}))
        if kind == "analyze" and not Path(meta.get("video_path", "")).is_file():
            return self._error("Videodatei nicht mehr am gespeicherten Ort.")
        if kind == "analyze" and body.get("options"):
            meta["options"] = opts  # "Erneut starten" nach einem Fehler nimmt dieselben Optionen
            m.write_meta(meta)
        job = self._enqueue(match_id, kind, opts, force=bool(body.get("force")))
        return self._json({"ok": True, "status": job["status"]})

    def _enqueue(self, match_id: str, kind: str, opts: dict, force: bool = False) -> dict:
        def run():
            s = Settings()
            m = pipeline.Match(match_id)
            if kind == "assess":
                pipeline.run_assessment(m, s, limit=opts.get("assess_limit"), force=force)
                return None
            return pipeline.run_analysis(
                m, Path(m.meta["video_path"]), s,
                use_gemini=opts.get("gemini", False) and s.scan_available(),
                use_assess=opts.get("assess", False) and s.assess_available(),
                assess_limit=opts.get("assess_limit"), force=force)
        return JOBS.submit(match_id, kind, run)


def _options(o: dict) -> dict:
    limit = o.get("assess_limit")
    try:
        limit = int(limit) if limit not in (None, "", 0, "0") else None
    except (TypeError, ValueError):
        limit = None
    return {"gemini": bool(o.get("gemini")), "assess": bool(o.get("assess")), "assess_limit": limit}


def _browse(raw: str) -> dict:
    if not raw:
        raw = os.environ.get("SCHIRI_VIDEO_DIR") or str(Path.home() / "Videos")
        if not Path(raw).is_dir():
            raw = str(Path.home())
    if raw == "::drives":
        drives = [f"{c}:\\" for c in string.ascii_uppercase if os.path.exists(f"{c}:\\")]
        return {"path": "", "parent": None, "dirs": drives, "files": [], "drives": True}
    p = Path(raw).expanduser()
    if p.is_file():
        p = p.parent
    if not p.is_dir():
        raise FileNotFoundError(raw)
    dirs, files = [], []
    try:
        for e in sorted(p.iterdir(), key=lambda x: x.name.lower()):
            if e.name.startswith((".", "$")):
                continue
            try:
                if e.is_dir():
                    dirs.append(e.name)
                elif e.suffix.lower() in VIDEO_EXT:
                    files.append({"name": e.name, "size_mb": round(e.stat().st_size / 1e6)})
            except OSError:
                continue
    except PermissionError:
        pass
    parent = str(p.parent) if p.parent != p else ("::drives" if os.name == "nt" else None)
    return {"path": str(p), "parent": parent, "dirs": dirs, "files": files, "sep": os.sep}


def _recover_interrupted() -> None:
    """Analyses that were running when the server stopped are marked as interrupted."""
    if not DATA_DIR.exists():
        return
    for d in DATA_DIR.iterdir():
        f = d / "match.json"
        if d.is_dir() and f.exists():
            meta = _load_json(f, {})
            if meta.get("analysis", {}).get("status") in ("queued", "running"):
                meta["analysis"].update({"status": "error", "error": "Abgebrochen (Server wurde beendet). Bitte neu starten."})
                f.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def serve(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = False) -> None:
    global JOBS
    _recover_interrupted()
    JOBS = JobManager()
    httpd = ThreadingHTTPServer((host, port), Handler)
    url = f"http://localhost:{port}"
    print(f"SchiriAnalyse läuft: {url}  (Beenden mit Strg+C)")
    if host == "0.0.0.0":
        print(f"Vom Handy im selben WLAN: http://<IP-dieses-PCs>:{port}  (dort nur Sichtung, kein Anlegen)")
    if open_browser:
        import webbrowser
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
