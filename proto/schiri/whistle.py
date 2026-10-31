"""Referee whistle detection from the audio track (CPU only).

A referee whistle is a loud, narrow-band tone, usually between 2 and 5 kHz.
Per 32 ms frame we measure
  * band ratio: share of the spectrum energy inside the whistle band
  * tonality:   strongest band bin compared with the mean band energy
  * level:      band energy above a rolling noise floor (dB)
Frames passing all three are joined into events; events that are too short or too long
are dropped, events close together (double whistle) are merged.
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


def frame_features(x: np.ndarray, sr: int, p: WhistleParams, chunk_s: float = 60.0):
    """Returns per-frame times, band ratio, tonality, band level (dB) and peak frequency.
    Processes the signal in chunks so a full match fits easily in memory."""
    n, hop = p.frame_len, p.hop
    window = np.hanning(n).astype(np.float32)
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    band = (freqs >= p.band_low_hz) & (freqs <= p.band_high_hz)
    band_freqs = freqs[band]

    total_frames = max(0, 1 + (len(x) - n) // hop)
    times = np.arange(total_frames) * hop / sr + (n / 2) / sr
    ratio = np.zeros(total_frames, np.float32)
    tonal = np.zeros(total_frames, np.float32)
    level = np.zeros(total_frames, np.float32)
    peak = np.zeros(total_frames, np.float32)

    frames_per_chunk = max(1, int(chunk_s * sr / hop))
    for f0 in range(0, total_frames, frames_per_chunk):
        f1 = min(total_frames, f0 + frames_per_chunk)
        idx = np.arange(f0, f1)[:, None] * hop + np.arange(n)[None, :]
        spec = np.abs(np.fft.rfft(x[idx] * window, axis=1)) ** 2
        band_spec = spec[:, band]
        band_e = band_spec.sum(axis=1) + 1e-12
        total_e = spec.sum(axis=1) + 1e-12
        ratio[f0:f1] = band_e / total_e
        tonal[f0:f1] = band_spec.max(axis=1) / (band_spec.mean(axis=1) + 1e-12)
        level[f0:f1] = 10 * np.log10(band_e)
        peak[f0:f1] = band_freqs[np.argmax(band_spec, axis=1)]
    return times, ratio, tonal, level, peak


def rolling_floor(level_db: np.ndarray, window_frames: int) -> np.ndarray:
    """Rolling 20th percentile of the band level: the background noise without whistles."""
    if len(level_db) == 0:
        return level_db
    step = max(1, window_frames // 4)
    anchors = np.arange(0, len(level_db), step)
    vals = []
    for a in anchors:
        lo, hi = max(0, a - window_frames // 2), min(len(level_db), a + window_frames // 2)
        vals.append(np.percentile(level_db[lo:hi], 20))
    return np.interp(np.arange(len(level_db)), anchors, np.array(vals))


def detect(x: np.ndarray, sr: int, p: WhistleParams | None = None) -> list[WhistleEvent]:
    p = p or WhistleParams()
    times, ratio, tonal, level, peak = frame_features(x, sr, p)
    if len(times) == 0:
        return []
    floor = rolling_floor(level, int(p.floor_window_s * sr / p.hop))
    above = level - floor
    hit = (ratio >= p.min_band_ratio) & (tonal >= p.min_tonality) & (above >= p.min_db_above_floor)

    events: list[WhistleEvent] = []
    i, frame_s = 0, p.hop / sr
    while i < len(hit):
        if not hit[i]:
            i += 1
            continue
        j, gap = i, 0
        while j + 1 < len(hit) and (hit[j + 1] or gap < p.max_gap_frames):
            gap = 0 if hit[j + 1] else gap + 1
            j += 1
        while j > i and not hit[j]:
            j -= 1
        seg = slice(i, j + 1)
        mask = hit[seg]
        t0, t1 = times[i] - frame_s / 2, times[j] + frame_s / 2
        dur = t1 - t0
        if p.min_duration_s <= dur <= p.max_duration_s:
            conf = _confidence(ratio[seg][mask], tonal[seg][mask], above[seg][mask], p)
            pk = float(np.median(peak[seg][mask]))
            events.append(WhistleEvent(round(float(t0), 3), round(float(t1), 3), round(pk, 1), conf))
        i = j + 1
    return merge(events, p.merge_gap_s)


def _confidence(ratio, tonal, above, p: WhistleParams) -> float:
    s_ratio = np.clip((np.mean(ratio) - p.min_band_ratio) / (1 - p.min_band_ratio), 0, 1)
    s_tonal = np.clip((np.log(np.mean(tonal)) - np.log(p.min_tonality)) / np.log(8), 0, 1)
    s_level = np.clip((np.mean(above) - p.min_db_above_floor) / 15.0, 0, 1)
    return round(float(0.4 + 0.6 * (0.3 * s_ratio + 0.35 * s_tonal + 0.35 * s_level)), 3)


def merge(events: list[WhistleEvent], gap_s: float) -> list[WhistleEvent]:
    out: list[WhistleEvent] = []
    for ev in sorted(events, key=lambda e: e.t_start):
        if out and ev.t_start - out[-1].t_end <= gap_s:
            last = out[-1]
            out[-1] = WhistleEvent(last.t_start, ev.t_end, last.peak_hz, max(last.confidence, ev.confidence))
        else:
            out.append(ev)
    return out


def detect_file(wav: Path, p: WhistleParams | None = None) -> list[WhistleEvent]:
    x, sr = read_wav(wav)
    return detect(x, sr, p)
