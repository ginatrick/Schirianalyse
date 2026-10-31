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


@dataclass
class WhistleParams:
    sample_rate: int = 16000
    frame_len: int = 1024          # 64 ms
    hop: int = 512                 # 32 ms
    band_low_hz: float = 2000.0
    band_high_hz: float = 5000.0
    min_band_ratio: float = 0.45   # share of energy in the whistle band
    min_tonality: float = 8.0      # peak bin vs. mean band energy
    min_db_above_floor: float = 9.0
    floor_window_s: float = 20.0
    max_gap_frames: int = 3
    min_duration_s: float = 0.12
    max_duration_s: float = 4.0
    merge_gap_s: float = 0.6


@dataclass
class SceneParams:
    pre_s: float = 8.0     # the incident usually happens before the whistle
    post_s: float = 4.0
    candidate_pre_s: float = 5.0
    candidate_post_s: float = 5.0
    link_window_s: float = 4.0   # candidate this close to a whistle belongs to that scene


@dataclass
class Settings:
    whistle: WhistleParams = field(default_factory=WhistleParams)
    scenes: SceneParams = field(default_factory=SceneParams)
    gemini_model: str = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
    gemini_chunk_s: int = int(os.environ.get("GEMINI_CHUNK_S", "1200"))
    claude_model: str = os.environ.get("CLAUDE_MODEL", "claude-haiku-5-5")
    claude_model_strong: str = os.environ.get("CLAUDE_MODEL_STRONG", "claude-sonnet-5-5")
    escalate_below: float = float(os.environ.get("ESCALATE_BELOW", "0.6"))


def match_dir(match_id: str) -> Path:
    d = DATA_DIR / match_id
    d.mkdir(parents=True, exist_ok=True)
    return d
