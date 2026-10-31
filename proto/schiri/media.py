"""ffmpeg helpers: probe, proxy, audio, scan video for Gemini, clips, frames."""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from .logs import Cancelled, cancel_event


def _bin(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"{name} nicht gefunden. Bitte ffmpeg installieren (Windows: winget install Gyan.FFmpeg).")
    return path


def _run(args: list[str]) -> None:
    """Run ffmpeg. The last argument is the output file; it is removed again if the run
    fails or is cancelled, so a half-written clip is never mistaken for a finished one."""
    ev = cancel_event()
    with tempfile.TemporaryFile() as err:
        proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=err)
        while True:
            try:
                proc.wait(timeout=0.5)
                break
            except subprocess.TimeoutExpired:
                if ev is not None and ev.is_set():
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                    Path(args[-1]).unlink(missing_ok=True)
                    raise Cancelled()
        if proc.returncode != 0:
            Path(args[-1]).unlink(missing_ok=True)
            err.seek(0)
            tail = err.read().decode("utf-8", "replace")[-2000:]
            raise RuntimeError(f"Befehl fehlgeschlagen: {' '.join(args[:6])} ...\n{tail}")


def probe(video: Path) -> dict:
    out = subprocess.run(
        [_bin("ffprobe"), "-v", "error", "-show_entries",
         "stream=codec_type,width,height,r_frame_rate:format=duration", "-of", "json", str(video)],
        capture_output=True, text=True, check=True,
    ).stdout
    data = json.loads(out)
    v = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    has_audio = any(s.get("codec_type") == "audio" for s in data.get("streams", []))
    w, h = int(v.get("width", 0)), int(v.get("height", 0))
    num, _, den = v.get("r_frame_rate", "25/1").partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 25.0
    return {
        "width": w,
        "height": h,
        "fps": round(fps, 3),
        "duration_s": float(data.get("format", {}).get("duration", 0.0)),
        "has_audio": has_audio,
        # Veo panorama exports are much wider than 16:9
        "has_panorama": bool(h and w / h > 2.2),
    }


def make_proxy(video: Path, out: Path) -> None:
    _run([_bin("ffmpeg"), "-y", "-i", str(video), "-vf", "scale=-2:720,fps=25",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
          "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(out)])


def extract_audio(video: Path, out: Path, sample_rate: int = 16000) -> None:
    _run([_bin("ffmpeg"), "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", str(sample_rate),
          "-c:a", "pcm_s16le", str(out)])


def make_scan_video(video: Path, out: Path, start_s: float, duration_s: float, small: bool = False) -> None:
    """Low-fps version for the Gemini scan (keeps audio so the model hears whistles).
    small=True for base64 upload via OpenRouter: Gemini samples about 1 frame per second anyway."""
    vf, crf, abr = ("scale=-2:360,fps=1", "32", "32k") if small else ("scale=-2:480,fps=5", "30", "48k")
    _run([_bin("ffmpeg"), "-y", "-ss", f"{start_s:.2f}", "-i", str(video), "-t", f"{duration_s:.2f}",
          "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", crf,
          "-c:a", "aac", "-ac", "1", "-b:a", abr, str(out)])


def cut_clip(proxy: Path, out: Path, start_s: float, end_s: float) -> None:
    start = max(0.0, start_s)
    _run([_bin("ffmpeg"), "-y", "-ss", f"{start:.2f}", "-i", str(proxy), "-t", f"{end_s - start:.2f}",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-c:a", "aac", "-b:a", "96k",
          "-movflags", "+faststart", str(out)])


def extract_frames(proxy: Path, out_dir: Path, start_s: float, end_s: float, count: int,
                   width: int = 1280) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    start = max(0.0, start_s)
    duration = max(0.5, end_s - start)
    fps = count / duration
    pattern = out_dir / "f_%03d.jpg"
    _run([_bin("ffmpeg"), "-y", "-ss", f"{start:.2f}", "-i", str(proxy), "-t", f"{duration:.2f}",
          "-vf", f"fps={fps:.4f},scale={width}:-2", "-q:v", "4", str(pattern)])
    return sorted(out_dir.glob("f_*.jpg"))[:count]
