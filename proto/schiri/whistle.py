"""Referee whistle detection from the audio track (CPU only).

Tuned on a real Veo recording of a youth match, where children's shouting fills the
2-5 kHz band (970 false hits with the first version). What separates a whistle from a voice:
  * prominence: the strongest bin in the whistle band towers over the band median
    (whistle 40-55 dB, shouting 10-25 dB)
  * nothing underneath: a whistle has no harmonics below 1.5 kHz, a voice always has.
    "low" = strongest bin 300-1500 Hz relative to the whistle peak (whistle -15 to -45 dB,
    voice -10 to +20 dB)
  * steady pitch: consecutive frames stay within a few tens of Hz; voice harmonics glide
Two passes: strong events teach us the pitch of this referee's whistle, then quieter or
partly covered events are accepted only at that pitch.
"""
from __future__ import annotations

import wave
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from .config import WhistleParams


@dataclass
class WhistleEvent:
    t_start: float
    t_end: float
    peak_hz: float
    confidence: float

    @property
    def t(self) -> float:
        return self.t_start

    @property
    def duration(self) -> float:
        return self.t_end - self.t_start

    def to_dict(self) -> dict:
        d = asdict(self)
        d["duration"] = round(self.duration, 3)
        d["kind"] = "long" if self.duration >= 1.2 else "short"
        return d


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wf:
        if wf.getsampwidth() != 2:
            raise ValueError("Erwartet 16-bit PCM")
        sr = wf.getframerate()
        ch = wf.getnchannels()
        raw = wf.readframes(wf.getnframes())
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x, sr


def frame_features(x: np.ndarray, sr: int, p: WhistleParams, chunk_frames: int = 2000) -> dict:
    """Per frame: time, peak frequency in the whistle band, prominence (dB) and low-band level (dB)."""
    n, hop = p.frame_len, p.hop
    window = np.hanning(n).astype(np.float32)
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    ctx = (freqs >= p.context_low_hz) & (freqs <= p.context_high_hz)   # reference for the median
    ctx_freqs = freqs[ctx]
    in_band = (ctx_freqs >= p.band_low_hz) & (ctx_freqs <= p.band_high_hz)
    band_offset = int(np.argmax(in_band))
    low = (freqs >= p.low_band_low_hz) & (freqs < p.low_band_high_hz)

    total = max(0, 1 + (len(x) - n) // hop)
    out = {k: np.zeros(total, np.float32) for k in ("f", "prom", "low")}
    out["t"] = np.arange(total) * hop / sr + (n / 2) / sr
    for f0 in range(0, total, chunk_frames):
        f1 = min(total, f0 + chunk_frames)
        idx = np.arange(f0, f1)[:, None] * hop + np.arange(n)[None, :]
        spec = np.abs(np.fft.rfft(x[idx] * window, axis=1)) ** 2 + 1e-14
        c = spec[:, ctx]
        rows = np.arange(f1 - f0)
        k = np.argmax(c[:, in_band], axis=1) + band_offset
        pk = c[rows, k]
        # parabolic interpolation for a finer pitch estimate
        a = np.log(c[rows, np.clip(k - 1, 0, c.shape[1] - 1)])
        b = np.log(pk)
        g = np.log(c[rows, np.clip(k + 1, 0, c.shape[1] - 1)])
        d = np.clip(0.5 * (a - g) / (a - 2 * b + g - 1e-9), -0.5, 0.5)
        out["f"][f0:f1] = ctx_freqs[k] + d * sr / n
        out["prom"][f0:f1] = 10 * np.log10(pk / np.median(c, axis=1))
        out["low"][f0:f1] = 10 * np.log10(spec[:, low].max(axis=1) / pk)
    return out


def _events(F: dict, hit: np.ndarray, p: WhistleParams, frame_s: float, min_dur: float) -> list[dict]:
    """Join hit frames with a steady pitch into events."""
    ev, i, n = [], 0, len(hit)
    while i < n:
        if not hit[i]:
            i += 1
            continue
        j, last, gap = i, i, 0
        while j + 1 < n:
            j += 1
            if hit[j] and abs(F["f"][j] - F["f"][last]) <= p.max_step_hz:
                last, gap = j, 0
            else:
                gap += 1
                if gap > p.max_gap_frames:
                    break
        seg = np.arange(i, last + 1)
        m = seg[hit[seg]]
        t0, t1 = float(F["t"][i] - frame_s / 2), float(F["t"][last] + frame_s / 2)
        if t1 - t0 >= min_dur and t1 - t0 <= p.max_duration_s:
            ev.append({"t0": t0, "t1": t1, "f": float(np.median(F["f"][m])),
                       "prom": float(np.median(F["prom"][m])), "low": float(np.median(F["low"][m]))})
        i = last + 1
    return ev


def detect(x: np.ndarray, sr: int, p: WhistleParams | None = None) -> list[WhistleEvent]:
    p = p or WhistleParams()
    F = frame_features(x, sr, p)
    if len(F["t"]) == 0:
        return []
    frame_s = p.hop / sr

    # pass 1: unmistakable whistles
    strong = _events(F, (F["prom"] >= p.strong_prom_db) & (F["low"] <= p.strong_low_db), p, frame_s, p.min_duration_s)
    for e in strong:
        e["strong"] = True

    # pass 2: quieter / partly covered whistles, only at a pitch the strong ones confirmed
    pitches = np.array([e["f"] for e in strong])
    weak = []
    if len(pitches) >= p.min_strong_for_pitch:
        cand = _events(F, (F["prom"] >= p.weak_prom_db) & (F["low"] <= p.weak_low_db), p, frame_s, p.weak_min_duration_s)
        for e in cand:
            close = int(np.sum(np.abs(pitches - e["f"]) <= p.pitch_tolerance_hz))
            overlaps = any(e["t0"] < s["t1"] and s["t0"] < e["t1"] for s in strong)
            if close >= p.min_strong_for_pitch and not overlaps:
                e["strong"] = False
                weak.append(e)

    events = [WhistleEvent(round(e["t0"], 3), round(e["t1"], 3), round(e["f"], 1), _confidence(e, p))
              for e in sorted(strong + weak, key=lambda e: e["t0"])]
    return merge(events, p.merge_gap_s)


def _confidence(e: dict, p: WhistleParams) -> float:
    s_prom = np.clip((e["prom"] - p.weak_prom_db) / 25.0, 0, 1)
    s_low = np.clip((p.weak_low_db - e["low"]) / 30.0, 0, 1)
    base = 0.6 if e["strong"] else 0.35
    return round(float(base + 0.4 * (0.5 * s_prom + 0.5 * s_low)), 3)


def merge(events: list[WhistleEvent], gap_s: float) -> list[WhistleEvent]:
    out: list[WhistleEvent] = []
    for ev in sorted(events, key=lambda e: e.t_start):
        if out and ev.t_start - out[-1].t_end <= gap_s:
            last = out[-1]
            out[-1] = WhistleEvent(last.t_start, max(last.t_end, ev.t_end), last.peak_hz,
                                   max(last.confidence, ev.confidence))
        else:
            out.append(ev)
    return out


def detect_file(wav: Path, p: WhistleParams | None = None) -> list[WhistleEvent]:
    x, sr = read_wav(wav)
    return detect(x, sr, p)
