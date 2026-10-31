"""Run: python proto/tests/test_motion.py"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from schiri.config import MotionParams  # noqa: E402
from schiri.motion import classify  # noqa: E402


def _series(cam_before: float, cam_after: float, pic_before: float, pic_after: float, t_whistle: float = 30.0):
    t = np.arange(1, 300) / 5.0
    cam = np.where(t < t_whistle, cam_before, cam_after)
    pic = np.where(t < t_whistle, pic_before, pic_after)
    return np.stack([t, pic, cam], axis=1).astype(np.float32)


def test_phases():
    p = MotionParams()
    assert classify(_series(1.5, 0.05, 6, 2), 30, 30.4, p)["phase"] == "stopped"     # foul: camera stops
    assert classify(_series(0.05, 1.5, 2, 6), 30, 30.4, p)["phase"] == "restart"     # kick-off
    assert classify(_series(1.5, 1.5, 6, 6), 30, 30.4, p)["phase"] == "running"      # play goes on
    assert classify(_series(0.0, 0.0, 2, 2), 30, 30.4, p)["phase"] == "unclear"
    assert classify(_series(0.0, 0.0, 2, 4), 30, 30.4, p, panorama=True)["phase"] == "restart"
    assert classify(_series(0.0, 0.0, 6, 2), 30, 30.4, p, panorama=True)["phase"] == "stopped"
    assert classify(_series(1, 1, 1, 1), 59.5, 59.9, p) is None                       # no frames after the whistle


if __name__ == "__main__":
    test_phases()
    print("ok")
