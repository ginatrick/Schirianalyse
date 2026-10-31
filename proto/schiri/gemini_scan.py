"""Gemini watches the whole match (in chunks) and lists candidate scenes.

Sends low-resolution video with audio to the Gemini API. Requires GEMINI_API_KEY.
Use only the paid API tier for real match videos (privacy, see docs/datenschutz)."""
from __future__ import annotations

import json
import math
import os
import re
import time
from pathlib import Path

from . import media
from .config import Settings

PROMPT = """Du bist Assistent eines Schiedsrichter-Beobachters. Das Video zeigt einen Ausschnitt eines Amateur-Fußballspiels,
aufgenommen mit einer automatischen Kamera (Ton enthalten). Finde alle Situationen, die ein Beobachter prüfen sollte:
- mögliche Fouls oder Handspiele, besonders solche OHNE Pfiff
- Stürze von Spielern nach Zweikampf, harte Zweikämpfe, Rudelbildung
- erhobene Fahne eines Assistenten, gezeigte Karten
Gib NUR JSON zurück, eine Liste von Objekten:
[{"time": "MM:SS", "type": "foul_suspect|handball_suspect|fall|hard_duel|flag|card|confrontation|other",
  "whistle_heard": true|false, "location": "links|mitte|rechts", "description": "kurz, deutsch, max 20 Wörter",
  "confidence": 0.0-1.0}]
"time" ist die Zeit im Videoausschnitt. Lieber eine Situation zu viel als eine zu wenig. Keine Namen, keine Rückennummern."""


def _parse_time(s: str) -> float | None:
    m = re.match(r"^\s*(?:(\d+):)?(\d{1,2}):(\d{2}(?:\.\d+)?)\s*$", str(s))
    if not m:
        return None
    h = int(m.group(1) or 0)
    return h * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def _parse_json(text: str) -> list[dict]:
    text = text.strip()
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end < 0:
        return []
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return []
    return [d for d in data if isinstance(d, dict)]


def scan(video: Path, duration_s: float, work: Path, s: Settings) -> tuple[list[dict], dict]:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY fehlt (.env). Ohne Key: analyze mit --no-gemini starten.")
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=key)
    chunk = s.gemini_chunk_s
    n_chunks = max(1, math.ceil(duration_s / chunk))
    candidates: list[dict] = []
    usage = {"prompt_tokens": 0, "output_tokens": 0, "chunks": n_chunks}
    for i in range(n_chunks):
        start = i * chunk
        dur = min(chunk, duration_s - start)
        if dur < 5:
            continue
        part = work / f"scan_{i:02d}.mp4"
        print(f"  Gemini-Abschnitt {i + 1}/{n_chunks} vorbereiten ...", flush=True)
        media.make_scan_video(video, part, start, dur)
        f = client.files.upload(file=str(part))
        try:
            while getattr(f.state, "name", str(f.state)) == "PROCESSING":
                time.sleep(5)
                f = client.files.get(name=f.name)
            resp = client.models.generate_content(
                model=s.gemini_model,
                contents=[f, PROMPT],
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.1),
            )
        finally:
            try:
                client.files.delete(name=f.name)   # nothing stays at Google longer than needed
            except Exception:
                pass
        (work / f"scan_{i:02d}.json").write_text(resp.text or "", encoding="utf-8")
        um = getattr(resp, "usage_metadata", None)
        if um:
            usage["prompt_tokens"] += getattr(um, "prompt_token_count", 0) or 0
            usage["output_tokens"] += getattr(um, "candidates_token_count", 0) or 0
        for item in _parse_json(resp.text or ""):
            t = _parse_time(item.get("time", ""))
            if t is None or t > dur + 1:
                continue
            candidates.append({
                "t": round(start + t, 2),
                "type": item.get("type", "other"),
                "whistle_heard": bool(item.get("whistle_heard", False)),
                "location": item.get("location"),
                "description": str(item.get("description", ""))[:200],
                "confidence": float(item.get("confidence", 0.5) or 0.5),
            })
        part.unlink(missing_ok=True)
    candidates.sort(key=lambda c: c["t"])
    return candidates, usage
