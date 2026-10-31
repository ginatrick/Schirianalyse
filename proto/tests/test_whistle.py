"""Run: python -m pytest proto/tests  (or: python proto/tests/test_whistle.py)"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from schiri.whistle import detect_file  # noqa: E402
from synth import make  # noqa: E402


def evaluate(events, truth, tol=0.5):
    matched, used = 0, set()
    for tr in truth:
        for k, ev in enumerate(events):
            if k not in used and abs(ev.t_start - tr["t"]) <= tol:
                matched += 1
                used.add(k)
                break
    recall = matched / max(1, len(truth))
    precision = len(used) / max(1, len(events))
    return recall, precision


def test_detector_on_synthetic_match():
    with tempfile.TemporaryDirectory() as d:
        wav = Path(d) / "synth.wav"
        info = make(wav, seconds=600)
        events = detect_file(wav)
        recall, precision = evaluate(events, info["whistles"])
        print(f"whistles={len(info['whistles'])} detected={len(events)} recall={recall:.2f} precision={precision:.2f}")
        assert recall >= 0.9
        assert precision >= 0.8


if __name__ == "__main__":
    test_detector_on_synthetic_match()
    print("ok")
