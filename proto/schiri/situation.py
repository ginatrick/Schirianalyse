"""What kind of situation is a scene? Tor, Abstoß, Eckstoß, Einwurf, Anstoß, Foul ...

Two sources:
  * rules (free): first whistle = Anpfiff; a long/double whistle followed by a long
    break = Halbzeit and the next whistle = Anpfiff 2. Halbzeit; a long/double whistle
    at the very end = Spielende.
  * Gemini (optional, about 0.15 $ per match): watches each scene clip with sound and
    names the situation and how play continued. Results are cached per time window,
    so a re-analysis does not pay twice.
Scenes stay in the list either way; the label helps to sort them. Routine situations
(Anstoß, Abstoß, Eckstoß, Einwurf, Halbzeit ...) skip the paid foul assessment.
"""
from __future__ import annotations

import json
from pathlib import Path

from .config import Settings, pitch_label
from .scenes import fmt_time
from .logs import log

SITUATIONS = {  # code -> (label, kind)   kind: decision = worth assessing, routine = normal flow of play
    "foul": ("Foul", "decision"),
    "handspiel": ("Handspiel", "decision"),
    "abseits": ("Abseits", "decision"),
    "verletzung": ("Verletzung", "decision"),
    "tor": ("Tor", "routine"),
    "toraus": ("Toraus", "routine"),
    "seitenaus": ("Einwurf", "routine"),
    "fortsetzung": ("Spielfortsetzung", "routine"),
    "spielbeginn": ("Anpfiff", "routine"),
    "halbzeit": ("Halbzeit", "routine"),
    "spielende": ("Spielende", "routine"),
    "sonstiges": ("Sonstiges", "decision"),
    "unklar": ("Unklar", "decision"),
}
RESTARTS = {
    "anstoss": "Anstoß", "abstoss": "Abstoß", "eckstoss": "Eckstoß", "einwurf": "Einwurf",
    "freistoss_direkt": "direkter Freistoß", "freistoss_indirekt": "indirekter Freistoß",
    "strafstoss": "Strafstoß", "schiedsrichterball": "Schiedsrichterball",
}

PROMPT = """Du bist Assistent eines Schiedsrichter-Beobachters. Der Clip ({dur:.0f} s, mit Ton) zeigt eine Szene aus einem
Amateur-Fußballspiel, aufgenommen mit einer automatischen Kamera. {whistle}
Bestimme, was das für eine Situation ist und wie das Spiel danach weitergeht. Gib NUR ein JSON-Objekt zurück:
{{"situation": "foul|handspiel|abseits|verletzung|tor|toraus|seitenaus|fortsetzung|spielbeginn|halbzeit|spielende|sonstiges|unklar",
  "fortsetzung": "anstoss|abstoss|eckstoss|einwurf|freistoss_direkt|freistoss_indirekt|strafstoss|schiedsrichterball|keine|unklar",
  "whistle_heard": true|false, "confidence": 0.0-1.0, "description": "kurz, deutsch, max 20 Wörter",
  "weitere": [{{"time_s": Sekunde im Clip, "situation": "foul|handspiel|abseits|verletzung|sonstiges",
               "location": "links|mitte|rechts", "description": "kurz, deutsch", "confidence": 0.0-1.0}}]}}
- "situation" ist der Grund für den Pfiff bzw. die Unterbrechung. "fortsetzung" bedeutet: der Pfiff gibt nur die
  Ausführung frei (z. B. Anstoß nach einem Tor, Freistoß nach Mauerstellen).
- "toraus": Ball hinter der Torlinie ohne Tor; dann "fortsetzung" abstoss oder eckstoss.
- "weitere": andere Vorfälle im selben Clip, die ein Beobachter ebenfalls prüfen sollte (z. B. ein zweiter Zweikampf
  an anderer Stelle). Nur echte, eigenständige Vorfälle; sonst leere Liste.
- Wenn du es nicht sicher erkennst, "unklar" und eine niedrige confidence. Keine Namen, keine Rückennummern.{context}"""


def label_for(code: str, restart: str | None) -> tuple[str, str]:
    label, kind = SITUATIONS.get(code, SITUATIONS["unklar"])
    r = RESTARTS.get(restart or "")
    if code == "toraus" and r in ("Abstoß", "Eckstoß"):
        label = r
    elif code in ("fortsetzung", "spielbeginn") and r:
        label = r if code == "fortsetzung" else label
    elif code == "foul" and restart == "strafstoss":
        label = "Foul · Strafstoß"
    return label, kind


def rule_based(scenes: list[dict], duration_s: float, break_s: float = 300.0) -> dict[str, dict]:
    """Anpfiff, Halbzeit, Anpfiff 2. Halbzeit, Spielende from the whistle pattern alone."""
    ws = [sc for sc in scenes if sc["type"] == "whistled" and sc.get("whistle")]
    out: dict[str, dict] = {}
    if not ws:
        return out

    def strong(sc):   # long whistle, or several in a row
        w = sc["whistle"]
        return w.get("duration", 0) >= 1.0 or w.get("count", 1) >= 2

    def put(sc, code, label):
        out[sc["id"]] = {"situation": code, "label": label, "kind": "routine", "source": "regel", "confidence": 0.8,
                         "accepts": (code, "fortsetzung", "unklar", "sonstiges")}

    put(ws[0], "spielbeginn", "Anpfiff")
    for a, b in zip(ws, ws[1:]):
        if b["whistle"]["t_start"] - a["whistle"]["t_end"] >= break_s and strong(a):
            put(a, "halbzeit", "Halbzeit")
            put(b, "spielbeginn", "Anpfiff 2. Halbzeit")
    last = ws[-1]
    if len(ws) > 1 and strong(last) and duration_s - last["whistle"]["t_end"] <= break_s:
        put(last, "spielende", "Spielende")
    return out


def _parse(text: str) -> dict | None:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        d = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(d, dict):
        return None
    code = str(d.get("situation", "unklar")).strip().lower()
    code = code if code in SITUATIONS else "unklar"
    restart = str(d.get("fortsetzung", "") or "").strip().lower() or None
    label, kind = label_for(code, restart)
    try:
        conf = max(0.0, min(1.0, float(d.get("confidence", 0.5) or 0.5)))
    except (TypeError, ValueError):
        conf = 0.5
    more = []
    for x in d.get("weitere") or []:
        if not isinstance(x, dict):
            continue
        try:
            t = float(x.get("time_s"))
            c = max(0.0, min(1.0, float(x.get("confidence", 0.5) or 0.5)))
        except (TypeError, ValueError):
            continue
        sc_code = str(x.get("situation", "sonstiges")).strip().lower()
        sc_code = sc_code if sc_code in SITUATIONS and SITUATIONS[sc_code][1] == "decision" else "sonstiges"
        more.append({"time_s": round(t, 1), "situation": sc_code, "label": SITUATIONS[sc_code][0],
                     "location": x.get("location"), "description": str(x.get("description", ""))[:200],
                     "confidence": round(c, 2)})
    return {"situation": code, "restart": restart if restart in RESTARTS else None, "label": label, "kind": kind,
            "source": "gemini", "confidence": round(conf, 2), "whistle_heard": bool(d.get("whistle_heard", False)),
            "description": str(d.get("description", ""))[:200], "more": more}


def extra_scenes(scenes: list[dict], found: dict[str, dict], key_fn, duration_s: float,
                 min_gap_s: float = 4.0, min_conf: float = 0.5, pre_s: float = 5.0, post_s: float = 5.0) -> list[dict]:
    """Further incidents Gemini saw inside a scene clip become scenes of their own,
    unless another scene already covers that moment."""
    events = [sc["t_event"] for sc in scenes]
    out: list[dict] = []
    for sc in scenes:
        v = found.get(key_fn(sc)) or {}
        for x in v.get("more") or []:
            t = round(sc["start"] + x["time_s"], 2)
            if x["confidence"] < min_conf or not (sc["start"] <= t <= sc["end"]):
                continue
            if any(abs(t - e) < min_gap_s for e in events):
                continue
            events.append(t)
            out.append({
                "id": "", "t_event": t, "minute": int(t // 60), "time_label": fmt_time(t), "start": round(max(0.0, t - pre_s), 2), "end": round(min(duration_s, t + post_s), 2),
                "type": "candidate", "detected_by": ["gemini-clip"], "confidence": x["confidence"],
                "whistle": None, "candidate": {"t": t, "type": "foul_suspect" if x["situation"] == "foul" else "other",
                                                "whistle_heard": False, "location": x.get("location"),
                                                "description": x["description"], "confidence": x["confidence"]},
                "clip": None, "ai": None, "video": None, "notes": [f"zweiter Vorfall in der Szene bei {sc['time_label']}"],
                "situation": {"situation": x["situation"], "label": x["label"], "kind": "decision", "source": "gemini",
                              "confidence": x["confidence"], "description": x["description"]},
            })
    return out


def classify_scenes(scenes: list[dict], clips_dir: Path, work: Path, s: Settings, meta: dict, key_fn,
                    duration_s: float, use_ai: bool) -> tuple[dict[str, dict], dict]:
    """Returns {window_key: situation} and the usage of the AI calls made now."""
    rules = rule_based(scenes, duration_s)
    usage = {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "calls": 0}
    out: dict[str, dict] = {}
    if use_ai:
        from .gemini_scan import _direct_asker, _openrouter_asker
        ask_factory = _openrouter_asker if s.provider == "openrouter" else _direct_asker
    context = "; ".join(x for x in (pitch_label(meta), meta.get("league")) if x)
    work.mkdir(parents=True, exist_ok=True)
    done = 0
    for sc in scenes:
        key = key_fn(sc)
        ai = None
        cache = work / f"{key}.json"
        if use_ai and sc.get("clip"):
            if cache.is_file():
                ai = json.loads(cache.read_text(encoding="utf-8"))
            else:
                clip = clips_dir / Path(sc["clip"]).name
                at = sc["t_event"] - sc["start"]
                whistle = (f"Bei etwa {at:.0f} s im Clip ist ein Pfiff zu hören." if sc["type"] == "whistled"
                           else f"Bei etwa {at:.0f} s im Clip gibt es einen Verdachtsfall ohne erkannten Pfiff.")
                prompt = PROMPT.format(dur=sc["end"] - sc["start"], whistle=whistle,
                                       context=f"\nSpielkontext: {context}." if context else "")
                text, u = ask_factory(s, prompt)(clip)
                for k in ("input_tokens", "output_tokens", "cost_usd"):
                    usage[k] += u.get(k, 0) or 0
                usage["calls"] += 1
                ai = _parse(text or "") or {"situation": "unklar", "label": "Unklar", "kind": "decision",
                                              "source": "gemini", "confidence": 0.0, "description": "Antwort nicht auswertbar."}
                ai["model"] = s.scan_model
                cache.write_text(json.dumps(ai, indent=2, ensure_ascii=False), encoding="utf-8")
                done += 1
                log(f"Situation {sc['id']} ({sc['time_label']}): {ai['label']} ({ai['confidence']:.2f})")
        rule = rules.get(sc["id"])
        # The whistle pattern wins unless Gemini clearly saw something else (e.g. the recording
        # started mid-game, so the first whistle is a foul and not the kick-off).
        compatible = ai is None or ai["situation"] in (rule or {}).get("accepts", ()) or ai["confidence"] < 0.6
        if rule and compatible:
            r = {k: v for k, v in rule.items() if k != "accepts"}
            if ai and ai["situation"] in rule["accepts"]:
                r["description"] = ai.get("description", "")
            if ai:
                r["more"] = ai.get("more", [])
            out[key] = r
        elif ai:
            out[key] = ai
    if done:
        log(f"Situationen: {done} Szenen von Gemini eingeordnet, {usage['cost_usd']:.2f} $")
    return out, usage
