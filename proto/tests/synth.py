"""Synthetic match audio with known whistle times, for testing the detector without real videos."""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 16000


def _whistle(dur: float, f0: float, rng: np.random.Generator, level: float) -> np.ndarray:
    t = np.arange(int(dur * SR)) / SR
    warble = 120 * np.sin(2 * np.pi * rng.uniform(20, 35) * t)        # pea whistle trill
    phase = 2 * np.pi * np.cumsum(f0 + warble) / SR
    sig = np.sin(phase) + 0.3 * np.sin(2 * phase)
    env = np.minimum(1, np.minimum(t / 0.02, (dur - t) / 0.03))
    return level * env * sig


def _crowd(n: int, rng: np.random.Generator) -> np.ndarray:
    white = rng.normal(0, 1, n)
    spec = np.fft.rfft(white)
    f = np.fft.rfftfreq(n, 1 / SR)
    spec /= np.maximum(f, 50) ** 0.6          # pinkish background
    spec[f > 3500] *= 0.3                       # little energy up high, like wind/crowd
    x = np.fft.irfft(spec, n)
    return 0.05 * x / np.std(x)


def _voices(n: int, rng: np.random.Generator, count: int) -> np.ndarray:
    out = np.zeros(n)
    for _ in range(count):
        start = rng.integers(0, n - SR)
        dur = rng.uniform(0.3, 1.2)
        t = np.arange(int(dur * SR)) / SR
        f0 = rng.uniform(120, 300)
        sig = sum(np.sin(2 * np.pi * f0 * k * t) / k for k in range(1, 12))   # harmonic, mostly < 3 kHz
        env = np.sin(np.pi * t / dur)
        seg = 0.15 * env * sig
        out[start:start + len(seg)] += seg[: n - start]
    return out


def make(path: Path, seconds: int = 600, seed: int = 7) -> dict:
    rng = np.random.default_rng(seed)
    n = seconds * SR
    x = _crowd(n, rng) + _voices(n, rng, count=seconds // 4)
    truth = []
    t = 15.0
    while t < seconds - 10:
        long = rng.random() < 0.08
        dur = rng.uniform(1.8, 2.8) if long else rng.uniform(0.25, 0.7)
        f0 = rng.choice([2700, 3150, 3600, 4200])
        level = rng.uniform(0.08, 0.4)                    # near and far referee
        w = _whistle(dur, f0, rng, level)
        i = int(t * SR)
        x[i:i + len(w)] += w
        truth.append({"t": round(t, 2), "dur": round(dur, 2), "f0": int(f0), "level": round(level, 3)})
        if rng.random() < 0.15:                           # double whistle shortly after
            t2 = t + dur + 0.25
            w2 = _whistle(0.3, f0, rng, level)
            x[int(t2 * SR):int(t2 * SR) + len(w2)] += w2
        t += rng.uniform(12, 45)
    # distractors: car horn (low), two fans whistling far away (tonal but quiet)
    horn_t = np.arange(int(1.0 * SR)) / SR
    x[int(100 * SR):int(101 * SR)] += 0.3 * (np.sign(np.sin(2 * np.pi * 420 * horn_t)) * 0.5)
    fan = []
    for ft in (230.0, 470.0):
        w = _whistle(0.8, 2500, rng, 0.012)
        x[int(ft * SR):int(ft * SR) + len(w)] += w
        fan.append(ft)
    x = np.clip(x, -1, 1)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes((x * 32767).astype(np.int16).tobytes())
    return {"whistles": truth, "fan_whistles": fan, "seconds": seconds}
