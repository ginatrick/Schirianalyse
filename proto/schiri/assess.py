"""Assessment proposal per scene via the Claude API (frames + scene facts + rule summary).
Requires ANTHROPIC_API_KEY. Cheap model first, stronger model when confidence is low."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from . import media
from .config import Settings, pitch_label

RULES = (Path(__file__).parent / "rules" / "kurzfassung.md").read_text(encoding="utf-8")

SYSTEM = f"""Du unterstützt Schiedsrichter-Beobachter im Amateur- und Jugendfußball. Du bekommst Einzelbilder einer Szene
aus einer automatischen Kamera (zeitlich geordnet) und Fakten zur Szene. Mache einen VORSCHLAG zur Bewertung, kein Urteil.
Sei vorsichtig: Ist der Kontakt aus den Bildern nicht erkennbar, antworte mit "unclear". Keine Namen, keine Rückennummern.

Regelgrundlage (Kurzfassung):
{RULES}

Antworte NUR mit JSON:
{{"decision": "foul|no_foul|unclear|not_a_foul_situation",
  "foul_type": "tackle|push|hold|trip|charge|strike|handball|dangerous_play|impeding|other|none",
  "sanction": "none|yellow|red",
  "rule_ref": "z. B. R12.1",
  "advantage_possible": true|false,
  "confidence": 0.0-1.0,
  "reason": "deutsch, höchstens 3 Sätze"}}
"not_a_foul_situation" verwendest du, wenn der Pfiff erkennbar etwas anderes war (Aus, Abseits, Anstoß, Halbzeit)."""


def _window(scene: dict) -> tuple[float, float]:
    t = scene["t_event"]
    if scene["type"] == "whistled":
        return t - 5.0, t + 1.0      # the incident happens before the whistle
    return t - 3.0, t + 3.0


def _facts(scene: dict, meta: dict | None = None) -> str:
    meta = meta or {}
    lines = [f"Szene {scene['id']} bei {scene['time_label']} im Video."]
    context = "; ".join(x for x in (pitch_label(meta), meta.get("league")) if x)
    if context:
        lines.append(f"Spielkontext: {context}. Bei Jugend- und Kleinfeldspielen können Durchführungsbestimmungen abweichen; "
                     "wenn das die Bewertung beeinflusst, nenne es in der Begründung oder antworte mit unclear.")
    if scene["type"] == "whistled":
        w = scene.get("whistle") or {}
        lines.append(f"Ein Pfiff ist zu hören (Dauer {w.get('duration', 0):.1f} s). Das letzte Bild liegt etwa 1 s nach dem Pfiff.")
    else:
        lines.append("Kein Pfiff erkannt. Die Szene wurde als Verdachtsfall vorgeschlagen.")
    c = scene.get("candidate")
    if c:
        lines.append(f"Hinweis aus der Videosuche: {c.get('type')} – {c.get('description')} (Position im Bild: {c.get('location')}).")
    return "\n".join(lines)


def _parse(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    try:
        data = json.loads(text[start:end + 1])
    except (ValueError, json.JSONDecodeError):
        return {"decision": "unclear", "confidence": 0.0, "reason": "Antwort nicht auswertbar."}
    data["confidence"] = float(data.get("confidence", 0) or 0)
    return data


def _call(client, model: str, images: list[Path], facts: str) -> tuple[dict, dict]:
    content = []
    for img in images:
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                     "data": base64.b64encode(img.read_bytes()).decode()}})
    content.append({"type": "text", "text": facts + "\nBewerte die Szene."})
    resp = client.messages.create(
        model=model,
        max_tokens=600,
        system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": content}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    usage = {"input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens, "calls": 1}
    return _parse(text), usage


def assess_scene(scene: dict, proxy: Path, work: Path, s: Settings, meta: dict | None = None) -> tuple[dict, dict]:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise SystemExit("ANTHROPIC_API_KEY fehlt (.env). Ohne Key: analyze mit --no-assess starten.")
    import anthropic

    client = anthropic.Anthropic(api_key=key)
    start, end = _window(scene)
    frames = media.extract_frames(proxy, work.parent / "frames" / work.name, start, end, count=10, width=1024)
    facts = _facts(scene, meta)
    result, usage = _call(client, s.claude_model, frames, facts)
    result["model"] = s.claude_model
    if result["confidence"] < s.escalate_below and s.claude_model_strong:
        strong, u2 = _call(client, s.claude_model_strong, frames, facts)
        strong["model"] = s.claude_model_strong
        strong["first_opinion"] = {k: result.get(k) for k in ("decision", "confidence")}
        for k in ("input_tokens", "output_tokens", "calls"):
            usage[k] += u2[k]
        result = strong
    work.mkdir(parents=True, exist_ok=True)
    (work / "assessment.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result, usage
