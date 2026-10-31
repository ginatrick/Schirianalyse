"""Play stoppage from the picture: does the game stop or restart around a whistle?

Players are only a few pixels tall in a Veo recording, so we do not look at the referee.
Instead we measure, at 5 frames per second on a 192x108 grey image:
  * camera motion: how far the (virtual) Veo camera pans between frames (phase correlation).
    The camera follows the ball; while the ball is dead it hardly moves.
  * picture motion: mean change between frames (players running, camera moving).
Around each whistle:
  * stopped   - camera moving before, quiet after     -> play was interrupted (foul, out, goal)
  * restart   - quiet before, moving after            -> kick-off, free kick, goal kick ...
  * running   - camera keeps moving on both sides     -> advantage, half-time/final whistle (players walk off),
                                                        or a whistle from elsewhere
  * unclear   - quiet on both sides without a clear change
On a panorama recording (fixed full-pitch view) the camera never moves, so only the
picture motion before/after is compared.
Tuned on one real Veo youth match; random moments show a quiet phase too in about 45 %
of cases, so this is a hint for sorting scenes, not proof that a whistle is real.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

from .config import MotionParams
from .logs import Cancelled, cancel_event, check_cancel, log
from .media import _bin

LABELS = {
    "stopped": "Spiel unterbrochen",
    "restart": "Spielfortsetzung",
    "running": "Keine Ruhephase im Bild",
    "unclear": "Bild unklar",
}


def compute(video: Path, out: Path, p: MotionParams, duration_s: float = 0.0) -> int:
    """Write an (n, 3) float32 array [t, picture_motion, camera_motion] to `out` (.npy)."""
    w, h = p.width, p.height
    cmd = [_bin("ffmpeg"), "-v", "error", "-i", str(video),
           "-vf", f"fps={p.fps},scale={w}:{h},format=gray", "-f", "rawvideo", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    win = np.outer(np.hanning(h), np.hanning(w)).astype(np.float32)
    rows, prev, prev_fft, i = [], None, None, 0
    next_log = 300.0
    ev = cancel_event()
    try:
        while True:
            buf = proc.stdout.read(w * h)
            if len(buf) < w * h:
                break
            i += 1
            f = np.frombuffer(buf, np.uint8).astype(np.float32).reshape(h, w)
            cur_fft = np.fft.fft2((f - f.mean()) * win)
            if prev is not None:
                r = prev_fft * np.conj(cur_fft)
                c = np.fft.ifft2(r / (np.abs(r) + 1e-6)).real
                dy, dx = np.unravel_index(int(np.argmax(c)), c.shape)
                dy = dy - h if dy > h // 2 else dy
                dx = dx - w if dx > w // 2 else dx
                rows.append((i / p.fps, float(np.abs(f - prev).mean()), float(np.hypot(dx, dy))))
            prev, prev_fft = f, cur_fft
            t = i / p.fps
            if t >= next_log:
                check_cancel()
                log(f"Bewegung im Bild: {t / 60:.0f}" + (f" von {duration_s / 60:.0f} min" if duration_s else " min"))
                next_log += 300.0
            elif ev is not None and i % 50 == 0 and ev.is_set():
                raise Cancelled()
    except BaseException:
        proc.kill()
        proc.wait()
        raise
    proc.wait()
    if proc.returncode not in (0, None) and not rows:
        raise RuntimeError("Bewegungsanalyse: ffmpeg konnte das Video nicht lesen.")
    np.save(out, np.array(rows, np.float32).reshape(-1, 3))
    return len(rows)


def load(path: Path) -> np.ndarray | None:
    try:
        return np.load(path)
    except (OSError, ValueError):
        return None


def _mean(t: np.ndarray, x: np.ndarray, a: float, b: float) -> float | None:
    m = (t >= a) & (t < b)
    return float(x[m].mean()) if m.any() else None


def classify(data: np.ndarray, t_start: float, t_end: float, p: MotionParams, panorama: bool = False) -> dict | None:
    t, pic, cam = data[:, 0], data[:, 1], data[:, 2]
    pre = (t_start - p.pre_s, t_start)
    post = (t_end + p.post_gap_s, t_end + p.post_gap_s + p.post_s)
    pic_pre, pic_post = _mean(t, pic, *pre), _mean(t, pic, *post)
    cam_pre, cam_post = _mean(t, cam, *pre), _mean(t, cam, *post)
    if None in (pic_pre, pic_post, cam_pre, cam_post):
        return None
    ratio = pic_post / max(pic_pre, 1e-3)
    if panorama:
        phase = "stopped" if ratio <= p.drop_ratio else "restart" if ratio >= p.rise_ratio else "unclear"
    else:
        quiet_pre, quiet_post = cam_pre <= p.still_cam_px, cam_post <= p.still_cam_px
        if quiet_post and not quiet_pre:
            phase = "stopped"
        elif quiet_pre and not quiet_post:
            phase = "restart"
        elif quiet_pre and quiet_post:
            phase = "restart" if ratio >= p.rise_ratio else "stopped" if ratio <= p.drop_ratio else "unclear"
        else:
            phase = "running"
    return {"phase": phase, "label": LABELS[phase], "camera_pre": round(cam_pre, 2), "camera_post": round(cam_post, 2),
            "motion_ratio": round(ratio, 2)}
