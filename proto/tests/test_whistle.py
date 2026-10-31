"""Run: python -m pytest proto/tests  (or: python proto/tests/test_whistle.py)"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from schiri.scenes import group_whistles  # noqa: E402
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
    ok = True
    for seed in (7, 11, 23):
        with tempfile.TemporaryDirectory() as d:
            wav = Path(d) / "synth.wav"
            info = make(wav, seconds=900, seed=seed)
            events = detect_file(wav)
            recall, precision = evaluate(events, info["whistles"])
            print(f"seed={seed} f0={info['whistles'][0]['f0']} whistles={len(info['whistles'])} "
                  f"detected={len(events)} recall={recall:.2f} precision={precision:.2f}")
            ok &= recall >= 0.9 and precision >= 0.9
    assert ok


def test_grouping():
    ws = [{"t_start": 10.0, "t_end": 10.4, "confidence": 0.7, "kind": "short"},
          {"t_start": 11.0, "t_end": 11.3, "confidence": 0.9, "kind": "short"},
          {"t_start": 30.0, "t_end": 31.5, "confidence": 0.8, "kind": "long"}]
    g = group_whistles(ws, 3.0)
    assert len(g) == 2 and g[0]["count"] == 2 and g[0]["t_end"] == 11.3 and g[0]["confidence"] == 0.9


if __name__ == "__main__":
    test_grouping()
    test_detector_on_synthetic_match()
    print("ok")
