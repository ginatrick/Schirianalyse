---
name: veo-video-prep
description: ffmpeg recipes for Veo match videos - probing, proxy video, audio extraction, clip cutting, panorama vs follow-cam detection. Use for any video or audio preparation in the worker.
---
# Veo video preparation

- Probe: `ffprobe -v error -show_entries stream=codec_type,width,height,r_frame_rate:format=duration -of json in.mp4`
- Source type: panorama exports are much wider than 16:9; follow-cam is 16:9. Store as `videos.has_panorama`.
- Proxy for analysis and review: `ffmpeg -i in.mp4 -vf "scale=-2:720,fps=25" -c:v libx264 -preset veryfast -crf 23 -c:a aac -b:a 96k proxy.mp4`
- Audio for whistle detection: `ffmpeg -i in.mp4 -vn -ac 1 -ar 16000 -c:a pcm_s16le audio.wav`
- Clip (fast seek, re-encoded for exact cut): `ffmpeg -ss <start> -i proxy.mp4 -t <duration> -c:v libx264 -preset veryfast -crf 23 -c:a aac clip.mp4`
- Frames for an assessment: sample around the event (e.g. 8 before, 8 after) and crop to the duel region before sending to a model.
- Keep the original only until analysis is done; long term keep proxy and clips (deletion periods in docs/entscheidungen.md).
