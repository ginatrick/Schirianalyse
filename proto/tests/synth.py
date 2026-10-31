"""Synthetic match audio with known whistle times, for testing the detector without real videos.

Modelled on a real Veo youth match: the hard part is not the crowd noise but children
shouting, whose harmonics fill the 2-5 kHz band just like a whistle."""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 16000


def _whistle(dur: float, f0: float, rng: np.random.Generator, level: float) -> np.ndarray:
    """Pea whistle: steady pitch with a slight trill, second tone a few hundred Hz above, one overtone."""
    t = np.arange(int(dur * SR)) / SR
    warble = 15 * np.sin(2 * np.pi * rng.uniform(20, 35) * t)
    phase = 2 * np.pi * np.cumsum(f0 + warble) / SR
    phase2 = 2 * np.pi * np.cumsum(f0 * 1.085 + warble) / SR
    trill = 1 + 0.3 * np.sin(2 * np.pi * rng.uniform(20, 35) * t)     # amplitude flutter of the pea
    sig = trill * (np.sin(phase) + 0.4 * np.sin(phase2)) + 0.2 * np.sin(2 * phase)
    env = np.minimum(1, np.minimum(t / 0.02, (dur - t) / 0.03))
    return level * env * sig


def _crowd(n: int, rng: np.random.Generator) -> np.ndarray:
    white = rng.normal(0, 1, n)
    spec = np.fft.rfft(white)
    f = np.fft.rfftfreq(n, 1 / SR)
    spec /= np.maximum(f, 50) ** 0.6          # pinkish background
    spec[f > 3500] *= 0.3
    x = np.fft.irfft(spec, n)
    return 0.03 * x / np.std(x)


def _voice(dur: float, f0: float, rng: np.random.Generator, level: float, glide: float) -> np.ndarray:
    """Harmonic voice with pitch glide/vibrato; harmonics up to 7 kHz like a child's shout."""
    t = np.arange(int(dur * SR)) / SR
    f = f0 * (1 + glide * t / dur) * (1 + 0.03 * np.sin(2 * np.pi * rng.uniform(4, 7) * t))
    phase = 2 * np.pi * np.cumsum(f) / SR
    nh = int(7000 // (f0 * (1 + max(0, glide))))
    sig = sum(np.sin(k * phase) * (1 / k ** 0.7) * (4.0 if 2500 < k * f0 < 4200 else 1) for k in range(1, nh + 1))
    env = np.sin(np.pi * t / dur) ** 0.5
    return level * env * sig / 4


def make(path: Path, seconds: int = 600, seed: int = 7) -> dict:
    rng = np.random.default_rng(seed)
    n = seconds * SR
    x = _crowd(n, rng)
    for _ in range(seconds // 2):                          # adults talking: low voices
        dur, i = rng.uniform(0.3, 1.2), int(rng.integers(0, n - 2 * SR))
        v = _voice(dur, rng.uniform(110, 250), rng, 0.08, rng.uniform(-0.2, 0.2))
        x[i:i + len(v)] += v
    for _ in range(seconds):                               # children shouting: high, loud, gliding
        dur, i = rng.uniform(0.15, 1.0), int(rng.integers(0, n - 2 * SR))
        v = _voice(dur, rng.uniform(300, 750), rng, rng.uniform(0.05, 0.4), rng.uniform(-0.3, 0.3))
        x[i:i + len(v)] += v
    truth = []
    f0 = rng.choice([2700, 3150, 3350, 3600, 4200])        # one referee, one whistle per match
    t = 15.0
    while t < seconds - 10:
        long = rng.random() < 0.08
        dur = rng.uniform(1.2, 2.8) if long else rng.uniform(0.25, 0.7)
        level = rng.uniform(0.1, 0.5)                      # near and far referee
        w = _whistle(dur, f0 * rng.uniform(0.98, 1.04), rng, level)
        i = int(t * SR)
        x[i:i + len(w)] += w
        truth.append({"t": round(t, 2), "dur": round(dur, 2), "f0": int(f0), "level": round(level, 3)})
        if rng.random() < 0.15:                            # double whistle shortly after
            t2 = t + dur + 0.25
            w2 = _whistle(0.3, f0, rng, level)
            x[int(t2 * SR):int(t2 * SR) + len(w2)] += w2
        t += rng.uniform(25, 70)
    horn_t = np.arange(int(1.0 * SR)) / SR                 # car horn (low)
    x[int(100 * SR):int(101 * SR)] += 0.3 * (np.sign(np.sin(2 * np.pi * 420 * horn_t)) * 0.5)
    x = np.clip(x, -1, 1)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes((x * 32767).astype(np.int16).tobytes())
    return {"whistles": truth, "seconds": seconds}
