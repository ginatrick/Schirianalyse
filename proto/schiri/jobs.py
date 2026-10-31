"""Background analysis jobs for the web UI: one at a time, progress and log per match."""
from __future__ import annotations

import queue
import threading
import time
import traceback

from . import pipeline
from .logs import Cancelled, set_cancel, set_sink, set_step

STEP_LABELS = {
    "import": "Video aufbereiten",
    "whistle": "Pfiffe suchen",
    "gemini": "Gemini sucht Szenen",
    "scenes": "Szenen bilden",
    "clips": "Clips schneiden",
    "assess": "KI-Bewertung",
    "publish": "Abschluss",
}


class JobManager:
    def __init__(self):
        self.jobs: dict[str, dict] = {}       # latest job per match id
        self._q: queue.Queue = queue.Queue()
        self._lock = threading.Lock()
        threading.Thread(target=self._worker, daemon=True).start()

    def submit(self, match_id: str, kind: str, fn) -> dict:
        with self._lock:
            cur = self.jobs.get(match_id)
            if cur and cur["status"] in ("queued", "running"):
                return cur
            job = {"match_id": match_id, "kind": kind, "status": "queued", "step": None, "step_label": "wartet",
                   "log": [], "queued_at": time.time(), "started_at": None, "finished_at": None, "error": None,
                   "cancel": threading.Event(), "cancel_requested": False}
            self.jobs[match_id] = job
        _persist(match_id, {"status": "queued", "kind": kind, "error": None})
        self._q.put((job, fn))
        return job

    def get(self, match_id: str) -> dict | None:
        return self.jobs.get(match_id)

    def cancel(self, match_id: str) -> dict | None:
        """Queued jobs are dropped at once; a running job stops at the next safe point
        (ffmpeg is stopped, a pending KI request is abandoned). Finished steps stay cached."""
        with self._lock:
            job = self.jobs.get(match_id)
            if not job or job["status"] not in ("queued", "running"):
                return job
            job["cancel"].set()
            job["cancel_requested"] = True
            if job["status"] == "queued":
                job["status"], job["finished_at"] = "cancelled", time.time()
                _persist(match_id, {"status": "cancelled", "kind": job["kind"], "error": None})
            else:
                job["step_label"] = "wird abgebrochen …"
        return job

    def _worker(self):
        while True:
            job, fn = self._q.get()
            if job["cancel"].is_set():
                continue
            job["status"], job["started_at"] = "running", time.time()
            _persist(job["match_id"], {"status": "running", "kind": job["kind"], "error": None})

            def sink(line, job=job):
                job["log"].append(line)
                del job["log"][:-200]

            def on_step(name, job=job):
                if not job["cancel_requested"]:
                    job["step"], job["step_label"] = name, STEP_LABELS.get(name, name)

            set_sink(sink)
            set_step(on_step)
            set_cancel(job["cancel"])
            try:
                result = fn()
                job["status"] = "done"
                extra = {"scenes": result} if isinstance(result, int) else {}
                _persist(job["match_id"], {"status": "done", "kind": job["kind"], "error": None, **extra})
            except Cancelled:
                job["status"] = "cancelled"
                job["log"].append(f"[{time.strftime('%H:%M:%S')}] Abgebrochen")
                if job["kind"] == "assess":
                    try:
                        pipeline.publish(pipeline.Match(job["match_id"]))   # show the suggestions paid for so far
                    except Exception:
                        traceback.print_exc()
                _persist(job["match_id"], {"status": "cancelled", "kind": job["kind"], "error": None})
            except BaseException as e:  # SystemExit carries our user-facing messages
                if isinstance(e, KeyboardInterrupt):
                    raise
                msg = str(e.code if isinstance(e, SystemExit) else e) or e.__class__.__name__
                job["status"], job["error"] = "error", msg
                job["log"].append(f"FEHLER: {msg}")
                traceback.print_exc()
                _persist(job["match_id"], {"status": "error", "kind": job["kind"], "error": msg[:500]})
            finally:
                job["finished_at"] = time.time()
                set_sink(None)
                set_step(None)
                set_cancel(None)


def _persist(match_id: str, analysis: dict) -> None:
    m = pipeline.Match(match_id)
    meta = m.meta
    prev = meta.get("analysis", {})
    meta["analysis"] = {**prev, **analysis, "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    m.write_meta(meta)
