"""Turn whistle events and KI candidates into review scenes."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .config import SceneParams


@dataclass
class Scene:
    id: str
    t_event: float              # whistle time or candidate time (seconds from video start)
    start: float
    end: float
    type: str                   # whistled | candidate
    detected_by: list[str]
    confidence: float
    whistle: dict | None = None
    candidate: dict | None = None
    clip: str | None = None
    ai: dict | None = None      # assessment proposal
    video: dict | None = None   # play stoppage from the picture (motion.classify)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["minute"] = int(self.t_event // 60)
        d["time_label"] = fmt_time(self.t_event)
        return d


def fmt_time(t: float) -> str:
    t = max(0, int(round(t)))
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def group_whistles(whistles: list[dict], gap_s: float) -> list[dict]:
    """Join whistles that follow each other within gap_s into one event (count = number of whistles)."""
    out: list[dict] = []
    for w in sorted(whistles, key=lambda w: w["t_start"]):
        if out and w["t_start"] - out[-1]["t_end"] <= gap_s:
            g = out[-1]
            g["t_end"] = max(g["t_end"], w["t_end"])
            g["duration"] = round(g["t_end"] - g["t_start"], 3)
            g["confidence"] = max(g["confidence"], w["confidence"])
            g["count"] = g.get("count", 1) + 1
            g["kind"] = "long" if w.get("kind") == "long" or g.get("kind") == "long" else g.get("kind", "short")
        else:
            out.append(dict(w))
    return out


def build(whistles: list[dict], candidates: list[dict], duration_s: float, p: SceneParams | None = None) -> list[Scene]:
    p = p or SceneParams()
    scenes: list[Scene] = []
    for w in group_whistles(whistles, p.group_gap_s):
        t = w["t_start"]
        scenes.append(Scene(
            id="", t_event=t, start=round(max(0.0, t - p.pre_s), 2), end=round(min(duration_s, w["t_end"] + p.post_s), 2),
            type="whistled", detected_by=["audio"], confidence=w["confidence"], whistle=w,
        ))
    for c in candidates:
        t = c["t"]
        near = [s for s in scenes if s.type == "whistled" and -p.link_window_s <= s.t_event - t <= p.link_window_s + p.pre_s]
        if near:
            s = min(near, key=lambda s: abs(s.t_event - t))
            if "gemini" not in s.detected_by:
                s.detected_by.append("gemini")
            s.candidate = c
            continue
        scenes.append(Scene(
            id="", t_event=t, start=round(max(0.0, t - p.candidate_pre_s), 2), end=round(min(duration_s, t + p.candidate_post_s), 2),
            type="candidate", detected_by=["gemini"], confidence=float(c.get("confidence", 0.5)), candidate=c,
        ))
    scenes.sort(key=lambda s: s.t_event)
    for i, s in enumerate(scenes, 1):
        s.id = f"s{i:03d}"
    return scenes
