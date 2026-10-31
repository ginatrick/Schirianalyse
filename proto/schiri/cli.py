"""Command line: python -m schiri analyze|assess|serve|list"""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

from . import pipeline
from .config import DATA_DIR, PITCH_TYPES, Settings


def _match_id(args) -> str:
    if args.match_id:
        return args.match_id
    return re.sub(r"[^a-z0-9-]+", "-", Path(args.video).stem.lower()).strip("-")


def cmd_analyze(args) -> None:
    s = Settings()
    video = Path(args.video).expanduser().resolve()
    if not video.exists():
        raise SystemExit(f"Video nicht gefunden: {video}")
    m = pipeline.Match(_match_id(args))
    meta = m.meta
    for k in ("date", "home", "away", "referee", "league"):
        if getattr(args, k):
            meta[k] = getattr(args, k)
    if args.pitch or args.players or args.pitch_length or args.pitch_width:
        pitch = meta.get("pitch", {})
        if args.pitch:
            pitch["type"] = args.pitch
        if args.players:
            pitch["players"] = args.players
        if args.pitch_length:
            pitch["length_m"] = args.pitch_length
        if args.pitch_width:
            pitch["width_m"] = args.pitch_width
        meta["pitch"] = pitch
    if not (meta.get("pitch") or {}).get("type"):
        pipeline.log("Hinweis: keine Spielform angegeben (--pitch grossfeld|verkuerzt|kleinfeld)")
    meta.setdefault("id", m.id)
    m.write_meta(meta)

    use_gemini = not args.no_gemini and s.scan_available()
    use_assess = not args.no_assess and s.assess_available()
    if use_gemini or use_assess:
        pipeline.log(f"KI-Zugang: {s.provider} · Suche {s.scan_model if use_gemini else '-'} · Bewertung {s.assess_model if use_assess else '-'}")

    pipeline.log(f"Spiel '{m.id}' – Daten in {m.dir}")
    pipeline.step_import(m, video, force=args.force)
    pipeline.step_whistle(m, s, force=args.force)
    if use_gemini:
        pipeline.step_gemini(m, s, force=args.force)
    else:
        pipeline.log("Gemini-Suche übersprungen (kein API-Key oder --no-gemini) – nur gepfiffene Szenen")
    pipeline.step_scenes(m, s, use_gemini)
    pipeline.step_clips(m, force=args.force)
    if use_assess:
        pipeline.step_assess(m, s, limit=args.assess_limit, force=args.force)
    else:
        pipeline.log("KI-Bewertung übersprungen (kein API-Key oder --no-assess)")
    f = pipeline.publish(m)
    pipeline.cleanup_original_copies(m)
    n = len(__import__("json").loads(f.read_text(encoding="utf-8"))["scenes"])
    pipeline.log(f"Fertig: {n} Szenen. Sichtung starten mit: python -m schiri serve")


def cmd_assess(args) -> None:
    s = Settings()
    m = pipeline.Match(args.match_id)
    if not m.result("clips"):
        raise SystemExit("Erst analyze ausführen.")
    pipeline.step_assess(m, s, limit=args.limit, force=args.force)
    pipeline.publish(m)
    pipeline.log("Bewertungsvorschläge aktualisiert.")


def cmd_list(_args) -> None:
    if not DATA_DIR.exists():
        print("Noch keine Spiele.")
        return
    for d in sorted(DATA_DIR.iterdir()):
        if (d / "scenes.json").exists():
            print(d.name)


def cmd_serve(args) -> None:
    from .review_server import serve
    serve(args.host, args.port)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m schiri", description="SchiriAnalyse Rohentwurf")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("analyze", help="Video analysieren")
    a.add_argument("video")
    a.add_argument("--match-id")
    a.add_argument("--date")
    a.add_argument("--home")
    a.add_argument("--away")
    a.add_argument("--referee")
    a.add_argument("--league", help="Liga/Altersklasse, z. B. 'C-Junioren Landesklasse'")
    a.add_argument("--pitch", choices=list(PITCH_TYPES), help="Spielform: grossfeld, verkuerzt, kleinfeld")
    a.add_argument("--players", type=int, help="Spieler pro Team auf dem Feld, z. B. 11, 9, 7")
    a.add_argument("--pitch-length", type=float, help="Feldlänge in Metern (gemessen)")
    a.add_argument("--pitch-width", type=float, help="Feldbreite in Metern (gemessen)")
    a.add_argument("--no-gemini", action="store_true", help="keine Kandidatensuche mit Gemini")
    a.add_argument("--no-assess", action="store_true", help="keine Bewertungsvorschläge mit Claude")
    a.add_argument("--assess-limit", type=int, default=None, help="höchstens N Szenen bewerten (Kosten testen)")
    a.add_argument("--force", action="store_true", help="alle Schritte neu rechnen")
    a.set_defaults(func=cmd_analyze)

    b = sub.add_parser("assess", help="Bewertungsvorschläge (nach)holen")
    b.add_argument("match_id")
    b.add_argument("--limit", type=int, default=None)
    b.add_argument("--force", action="store_true")
    b.set_defaults(func=cmd_assess)

    c = sub.add_parser("serve", help="Sichtung im Browser starten")
    c.add_argument("--host", default="127.0.0.1", help="0.0.0.0 für Zugriff vom Handy im WLAN")
    c.add_argument("--port", type=int, default=8765)
    c.set_defaults(func=cmd_serve)

    d = sub.add_parser("list", help="analysierte Spiele anzeigen")
    d.set_defaults(func=cmd_list)

    args = p.parse_args(argv)
    args.func(args)
