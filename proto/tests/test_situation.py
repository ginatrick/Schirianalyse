"""Run: python proto/tests/test_situation.py"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from schiri.situation import _parse, extra_scenes, label_for, rule_based  # noqa: E402


def _w(i, t, dur=0.4, count=1):
    return {"id": f"s{i:03d}", "type": "whistled", "t_event": t,
            "whistle": {"t_start": t, "t_end": t + dur, "duration": dur, "count": count}}


def test_rules():
    scenes = [_w(1, 60), _w(2, 300), _w(3, 1500, 1.2), _w(4, 2000), _w(5, 2500), _w(6, 3550, 0.5, 2),
              {"id": "s007", "type": "candidate", "t_event": 3560}]
    r = rule_based(scenes, 3600)
    assert r["s001"]["label"] == "Anpfiff"
    assert r["s003"]["label"] == "Halbzeit" and r["s004"]["label"] == "Anpfiff 2. Halbzeit"
    assert r["s006"]["label"] == "Spielende"
    assert "s002" not in r and "s005" not in r
    # a long gap after a short whistle is not half-time
    assert "s002" not in rule_based([_w(1, 60), _w(2, 100), _w(3, 900)], 3600)


def test_labels_and_parse():
    assert label_for("toraus", "eckstoss") == ("Eckstoß", "routine")
    assert label_for("toraus", "abstoss") == ("Abstoß", "routine")
    assert label_for("seitenaus", "einwurf") == ("Einwurf", "routine")
    assert label_for("foul", "strafstoss") == ("Foul · Strafstoß", "decision")
    assert label_for("fortsetzung", "anstoss") == ("Anstoß", "routine")
    assert label_for("quatsch", None) == ("Unklar", "decision")
    p = _parse('```json\n{"situation": "tor", "fortsetzung": "anstoss", "confidence": 0.9, "description": "x"}\n```')
    assert p["label"] == "Tor" and p["kind"] == "routine" and p["confidence"] == 0.9
    assert _parse("keine Ahnung") is None


def test_extra_scenes():
    key = lambda sc: sc["id"]
    scenes = [{"id": "a", "t_event": 100, "start": 92, "end": 104, "time_label": "01:40"},
              {"id": "b", "t_event": 110, "start": 102, "end": 114, "time_label": "01:50"}]
    more = [{"time_s": 2.0, "situation": "foul", "label": "Foul", "location": "rechts", "description": "x", "confidence": 0.7},
            {"time_s": 9.0, "situation": "foul", "label": "Foul", "location": "mitte", "description": "y", "confidence": 0.7},
            {"time_s": 1.0, "situation": "foul", "label": "Foul", "location": "mitte", "description": "z", "confidence": 0.2}]
    ex = extra_scenes(scenes, {"a": {"more": more}}, key, 3600)
    assert len(ex) == 1 and ex[0]["t_event"] == 94.0   # 101 s is covered by scene a/b, 93 s has too little confidence
    assert ex[0]["type"] == "candidate" and ex[0]["situation"]["label"] == "Foul"
    p = _parse('{"situation": "foul", "weitere": [{"time_s": 3, "situation": "anstoss", "confidence": 0.9}]}')
    assert p["more"][0]["situation"] == "sonstiges"     # routine situations are not extra incidents


if __name__ == "__main__":
    test_extra_scenes()
    test_rules()
    test_labels_and_parse()
    print("ok")
