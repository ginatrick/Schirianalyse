"""Assessment proposal per scene via Claude (frames + scene facts + rule summary), through
OpenRouter (OPENROUTER_API_KEY) or directly (ANTHROPIC_API_KEY).
Cheap model first, stronger model when confidence is low."""
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
        v = scene.get("video") or {}
        hint = {"stopped": "Nach dem Pfiff ruht das Spiel (Kamera steht) – vermutlich eine Unterbrechung.",
                "restart": "Vor dem Pfiff ruhte das Spiel, danach läuft es – vermutlich ein Pfiff zur Spielfortsetzung "
                           "(Anstoß, Frei- oder Strafstoß). Dann gibt es meist nichts zu bewerten: decision not_a_foul_situation.",
                "running": "Das Spiel läuft nach dem Pfiff weiter – Vorteil, oder der Pfiff kam von woanders."}.get(v.get("phase"))
        if hint:
            lines.append(f"Bewegungsanalyse (nur Hinweis): {hint}")
    else:
        lines.append("Kein Pfiff erkannt. Die Szene wurde als Verdachtsfall vorgeschlagen.")
    sit = scene.get("situation") or {}
    if sit.get("label"):
        lines.append(f"Situation laut Videoanalyse (nur Hinweis): {sit['label']}"
                     + (f" – {sit['description']}" if sit.get("description") else "") + ".")
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


def _call_direct(client, model: str, images: list[Path], facts: str) -> tuple[dict, dict]:
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


def _call_openrouter(_client, model: str, images: list[Path], facts: str) -> tuple[dict, dict]:
    from . import llm
    content = [llm.image_part(img) for img in images]
    content.append({"type": "text", "text": facts + "\nBewerte die Szene."})
    text, usage = llm.chat(model, content, system=SYSTEM, max_tokens=600)
    return _parse(text), usage


def assess_scene(scene: dict, proxy: Path, work: Path, s: Settings, meta: dict | None = None) -> tuple[dict, dict]:
    if s.provider == "openrouter":
        client, call = None, _call_openrouter
    else:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise SystemExit("ANTHROPIC_API_KEY fehlt (.env). Ohne Key: analyze mit --no-assess starten.")
        import anthropic
        client, call = anthropic.Anthropic(api_key=key), _call_direct

    start, end = _window(scene)
    frames = media.extract_frames(proxy, work.parent / "frames" / work.name, start, end, count=10, width=1024)
    facts = _facts(scene, meta)
    result, usage = call(client, s.assess_model, frames, facts)
    result["model"] = s.assess_model
    if result["confidence"] < s.escalate_below and s.assess_model_strong:
        strong, u2 = call(client, s.assess_model_strong, frames, facts)
        strong["model"] = s.assess_model_strong
        strong["first_opinion"] = {k: result.get(k) for k in ("decision", "confidence")}
        for k in ("input_tokens", "output_tokens", "cost_usd", "calls"):
            usage[k] = (usage.get(k, 0) or 0) + (u2.get(k, 0) or 0)
        result = strong
    work.mkdir(parents=True, exist_ok=True)
    (work / "assessment.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result, usage
