"""Pipeline steps with per-step caching (see .claude/skills/pipeline-step)."""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from . import media, scenes as scene_mod, whistle
from .config import Settings, match_dir

STEP_VERSIONS = {"import": 1, "audio_whistle": 1, "gemini_scan": 1, "scenes": 1, "clips": 1, "assessment": 1}


class Match:
    def __init__(self, match_id: str):
        self.id = match_id
        self.dir = match_dir(match_id)

    def step_dir(self, name: str) -> Path:
        d = self.dir / "steps" / name
        d.mkdir(parents=True, exist_ok=True)
        return d

    def result(self, name: str) -> dict | None:
        f = self.step_dir(name) / "result.json"
        if not f.exists():
            return None
        data = json.loads(f.read_text(encoding="utf-8"))
        return data if data.get("version") == STEP_VERSIONS[name] else None

    def save(self, name: str, data: dict, started: float) -> dict:
        data = {"version": STEP_VERSIONS[name], "duration_s": round(time.time() - started, 2), **data}
        (self.step_dir(name) / "result.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return data

    @property
    def meta(self) -> dict:
        f = self.dir / "match.json"
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}

    def write_meta(self, meta: dict) -> None:
        (self.dir / "match.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def window_key(sc: dict) -> str:
    return f"w{int(round(sc['start'] * 100)):07d}-{int(round(sc['end'] * 100)):07d}"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def step_import(m: Match, video: Path, force: bool = False) -> dict:
    if not force and (r := m.result("import")):
        return r
    t0 = time.time()
    info = media.probe(video)
    if not info["has_audio"]:
        raise SystemExit("Das Video hat keine Tonspur – Pfiff-Erkennung nicht möglich.")
    d = m.step_dir("import")
    log(f"Proxy-Video erstellen ({info['width']}x{info['height']}, {info['duration_s'] / 60:.0f} min) ...")
    media.make_proxy(video, d / "proxy.mp4")
    log("Tonspur extrahieren ...")
    media.extract_audio(video, d / "audio.wav")
    return m.save("import", {"source": str(video), **info}, t0)


def step_whistle(m: Match, s: Settings, force: bool = False) -> dict:
    if not force and (r := m.result("audio_whistle")):
        return r
    t0 = time.time()
    log("Pfiffe suchen ...")
    events = whistle.detect_file(m.step_dir("import") / "audio.wav", s.whistle)
    log(f"{len(events)} Pfiffe gefunden")
    return m.save("audio_whistle", {"events": [e.to_dict() for e in events]}, t0)


def step_gemini(m: Match, s: Settings, force: bool = False) -> dict:
    if not force and (r := m.result("gemini_scan")):
        return r
    from . import gemini_scan
    t0 = time.time()
    imp = m.result("import")
    cands, usage = gemini_scan.scan(Path(imp["source"]), imp["duration_s"], m.step_dir("gemini_scan"), s, m.meta)
    log(f"{len(cands)} Kandidaten von Gemini")
    return m.save("gemini_scan", {"candidates": cands, "usage": usage, "model": s.gemini_model}, t0)


def step_scenes(m: Match, s: Settings, use_gemini: bool) -> dict:
    t0 = time.time()
    imp = m.result("import")
    whistles = m.result("audio_whistle")["events"]
    cands = (m.result("gemini_scan") or {}).get("candidates", []) if use_gemini else []
    built = scene_mod.build(whistles, cands, imp["duration_s"], s.scenes)
    return m.save("scenes", {"scenes": [sc.to_dict() for sc in built]}, t0)


def step_clips(m: Match, force: bool = False) -> dict:
    t0 = time.time()
    proxy = m.step_dir("import") / "proxy.mp4"
    clips_dir = m.dir / "clips"
    clips_dir.mkdir(exist_ok=True)
    scs = m.result("scenes")["scenes"]
    for i, sc in enumerate(scs, 1):
        out = clips_dir / f"{window_key(sc)}.mp4"   # named by time window, stable when scene ids shift
        if force or not out.exists():
            media.cut_clip(proxy, out, sc["start"], sc["end"])
        sc["clip"] = f"clips/{out.name}"
        if i % 10 == 0:
            log(f"Clips {i}/{len(scs)}")
    return m.save("clips", {"scenes": scs}, t0)


def step_assess(m: Match, s: Settings, limit: int | None, force: bool = False) -> dict:
    from . import assess
    t0 = time.time()
    prev = {} if force else {window_key(sc): sc.get("ai") for sc in (m.result("assessment") or {}).get("scenes", [])}
    scs = m.result("clips")["scenes"]
    proxy = m.step_dir("import") / "proxy.mp4"
    usage_total = {"input_tokens": 0, "output_tokens": 0, "calls": 0}
    done = 0
    for sc in scs:
        if prev.get(window_key(sc)):
            sc["ai"] = prev[window_key(sc)]
            continue
        if limit is not None and done >= limit:
            continue
        sc["ai"], usage = assess.assess_scene(sc, proxy, m.step_dir("assessment") / window_key(sc), s, m.meta)
        for k in ("input_tokens", "output_tokens"):
            usage_total[k] += usage.get(k, 0)
        usage_total["calls"] += usage.get("calls", 1)
        done += 1
        log(f"Bewertet {sc['id']} ({sc['time_label']}): {sc['ai'].get('decision')} ({sc['ai'].get('confidence')})")
    return m.save("assessment", {"scenes": scs, "usage": usage_total}, t0)


def publish(m: Match) -> Path:
    """Write the final scenes.json the review UI reads."""
    src = m.result("assessment") or m.result("clips")
    out = {"match": m.meta, "video": m.result("import"), "scenes": src["scenes"]}
    out["video"] = {k: v for k, v in out["video"].items() if k != "source"}
    f = m.dir / "scenes.json"
    f.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return f


def cleanup_original_copies(m: Match) -> None:
    """Delete the large intermediate scan videos (originals stay where the user keeps them)."""
    scan = m.dir / "steps" / "gemini_scan"
    for f in scan.glob("*.mp4"):
        f.unlink(missing_ok=True)
    shutil.rmtree(m.dir / "steps" / "assessment" / "frames", ignore_errors=True)
