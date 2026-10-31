"""OpenRouter access (OpenAI-compatible chat completions) using only the standard library.

Video goes in as a base64 data URL. On OpenRouter, Gemini on Google AI Studio only accepts
YouTube links, so base64 video requests are served by Google Vertex."""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from .logs import run_cancellable, sleep

BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()


def available() -> bool:
    return bool(os.environ.get("OPENROUTER_API_KEY", "").strip())


def data_url(path: Path, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def video_part(path: Path) -> dict:
    return {"type": "video_url", "video_url": {"url": data_url(path, "video/mp4")}}


def image_part(path: Path) -> dict:
    return {"type": "image_url", "image_url": {"url": data_url(path, "image/jpeg")}}


def chat(model: str, content: list[dict], system: str | None = None, max_tokens: int = 2000,
         temperature: float = 0.1, retries: int = 3, timeout: int = 600) -> tuple[str, dict]:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip().strip('"').strip("'")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY fehlt (.env).")
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": content}]
    body = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "usage": {"include": True},          # returns the cost of the call
    }).encode("utf-8")
    req = urllib.request.Request(f"{BASE_URL}/chat/completions", data=body, method="POST", headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "X-Title": "SchiriAnalyse",
    })
    last = None
    for attempt in range(retries):
        try:
            def call():
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            data = run_cancellable(call)
            if "error" in data:
                raise RuntimeError(data["error"])
            text = data["choices"][0]["message"].get("content") or ""
            u = data.get("usage") or {}
            usage = {"input_tokens": u.get("prompt_tokens", 0), "output_tokens": u.get("completion_tokens", 0),
                     "cost_usd": u.get("cost", 0.0) or 0.0, "calls": 1}
            return text, usage
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500]
            hint = {401: "API-Key ungültig – OPENROUTER_API_KEY in .env prüfen",
                    402: "OpenRouter-Guthaben aufgebraucht – unter openrouter.ai/credits aufladen",
                    403: "Anfrage abgelehnt (Modell gesperrt oder Datenschutz-Einstellung bei OpenRouter)",
                    404: "Modell nicht gefunden – Modellname in .env prüfen"}.get(e.code)
            last = f"{hint} (HTTP {e.code})" if hint else f"HTTP {e.code}: {detail}"
            if e.code not in (408, 429, 500, 502, 503, 504):
                break
        except (urllib.error.URLError, TimeoutError, RuntimeError) as e:
            last = str(e)
        sleep(5 * (attempt + 1))
    raise RuntimeError(f"OpenRouter-Aufruf fehlgeschlagen ({model}): {last}")
