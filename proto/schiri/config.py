"""Paths and settings for the prototype. Everything is local; nothing leaves the machine
unless a KI step (Gemini scan, Claude assessment) is enabled with an API key."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # dotenv is optional
    load_dotenv = None

PROTO_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = PROTO_DIR.parent
if load_dotenv:
    load_dotenv(REPO_DIR / ".env")

DATA_DIR = Path(os.environ.get("SCHIRI_DATA_DIR", REPO_DIR / "data" / "matches"))
REVIEW_DIR = PROTO_DIR / "review"


def env(name: str, default: str = "") -> str:
    """Environment value without surrounding spaces or quotes (robust against hand-edited .env files)."""
    return (os.environ.get(name) or default).strip().strip('"').strip("'").strip()


@dataclass
class WhistleParams:
    """Thresholds tuned on a real Veo youth match (see whistle.py for what they mean)."""
    sample_rate: int = 16000
    frame_len: int = 2048          # 128 ms, ~8 Hz resolution for the steady-pitch check
    hop: int = 512                 # 32 ms
    band_low_hz: float = 2500.0    # where the whistle peak is searched
    band_high_hz: float = 4800.0
    context_low_hz: float = 1500.0 # reference band for the prominence median
    context_high_hz: float = 5200.0
    low_band_low_hz: float = 300.0 # voices always have energy here, whistles don't
    low_band_high_hz: float = 1500.0
    strong_prom_db: float = 35.0
    strong_low_db: float = -15.0
    weak_prom_db: float = 28.0
    weak_low_db: float = -8.0
    weak_min_duration_s: float = 0.25
    pitch_tolerance_hz: float = 120.0
    min_strong_for_pitch: int = 2
    max_step_hz: float = 40.0      # pitch change allowed between frames
    max_gap_frames: int = 2
    min_duration_s: float = 0.15
    max_duration_s: float = 6.0
    merge_gap_s: float = 0.6


@dataclass
class MotionParams:
    """Play stoppage from the picture (see motion.py)."""
    fps: int = 5
    width: int = 192
    height: int = 108
    pre_s: float = 5.0           # window before the whistle
    post_gap_s: float = 1.0      # players need a moment to react
    post_s: float = 5.0          # window after the whistle
    still_cam_px: float = 0.3    # camera pans less than this per frame (at 192 px width) = ball dead
    drop_ratio: float = 0.7      # picture motion after/before at or below this = play stopped
    rise_ratio: float = 1.4      # at or above this = play restarted


@dataclass
class SceneParams:
    pre_s: float = 8.0     # the incident usually happens before the whistle
    post_s: float = 4.0
    candidate_pre_s: float = 5.0
    candidate_post_s: float = 5.0
    link_window_s: float = 4.0   # candidate this close to a whistle belongs to that scene
    group_gap_s: float = 3.0     # whistles closer than this (double whistle, whistle + restart) form one scene


@dataclass
class Settings:
    whistle: WhistleParams = field(default_factory=WhistleParams)
    motion: MotionParams = field(default_factory=MotionParams)
    scenes: SceneParams = field(default_factory=SceneParams)
    # KI access: "openrouter" (one key for Gemini and Claude) or "direct" (Google and Anthropic keys)
    provider: str = field(default_factory=lambda: env("KI_PROVIDER")
                          or ("openrouter" if env("OPENROUTER_API_KEY") else "direct"))
    scan_model: str = field(default_factory=lambda: env("SCAN_MODEL"))
    scan_chunk_s: int = field(default_factory=lambda: int(env("SCAN_CHUNK_S", "0") or 0))
    assess_model: str = field(default_factory=lambda: env("ASSESS_MODEL"))
    assess_model_strong: str = field(default_factory=lambda: env("ASSESS_MODEL_STRONG"))
    escalate_below: float = field(default_factory=lambda: float(env("ESCALATE_BELOW", "0.6") or 0.6))

    def __post_init__(self):
        if self.provider == "openrouter":
            self.scan_model = self.scan_model or "google/gemini-3.8-flash"
            self.assess_model = self.assess_model or "anthropic/claude-haiku-5.5"
            self.assess_model_strong = self.assess_model_strong or "anthropic/claude-sonnet-5.5"
            self.scan_chunk_s = self.scan_chunk_s or 300      # base64 upload: keep requests small
        else:
            self.scan_model = self.scan_model or "gemini-3.8-flash"
            self.assess_model = self.assess_model or "claude-haiku-5-5"
            self.assess_model_strong = self.assess_model_strong or "claude-sonnet-5-5"
            self.scan_chunk_s = self.scan_chunk_s or 1200

    def scan_available(self) -> bool:
        return bool(env("OPENROUTER_API_KEY" if self.provider == "openrouter" else "GEMINI_API_KEY"))

    def assess_available(self) -> bool:
        return bool(env("OPENROUTER_API_KEY" if self.provider == "openrouter" else "ANTHROPIC_API_KEY"))


# Spielformen. Feldmaße variieren je Platz: echte Maße mit --pitch-length/--pitch-width angeben,
# sonst gelten die Maße als unbekannt (wichtig für spätere Laufwege in Metern).
PITCH_TYPES = {
    "grossfeld": "Großfeld",
    "verkuerzt": "verkürztes Großfeld",
    "kleinfeld": "Kleinfeld",
}


def pitch_label(meta: dict) -> str:
    """Short description used in KI prompts and the review header, e.g. 'Kleinfeld, 7 gegen 7, 55 x 35 m'."""
    p = meta.get("pitch") or {}
    if not p.get("type"):
        return ""
    parts = [PITCH_TYPES.get(p["type"], p["type"])]
    if p.get("players"):
        parts.append(f"{p['players']} gegen {p['players']}")
    if p.get("length_m") and p.get("width_m"):
        parts.append(f"{p['length_m']:g} x {p['width_m']:g} m")
    return ", ".join(parts)


def match_dir(match_id: str) -> Path:
    d = DATA_DIR / match_id
    d.mkdir(parents=True, exist_ok=True)
    return d
