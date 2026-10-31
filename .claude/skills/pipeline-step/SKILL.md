---
name: pipeline-step
description: Contract for analysis steps in the Python worker (worker/). Use when adding, changing or debugging a pipeline step such as import, whistle detection, tracking, referee tracking, candidates or assessment.
---
# Pipeline step contract

Order: `import -> audio_whistle -> vision_tracking -> game_state -> whistled_scenes -> candidate_scenes -> officials_tracking -> assessment -> finalize`. `audio_whistle` and `vision_tracking` are independent.

## Every step
- Lives in `worker/steps/<name>.py` and exposes `run(job: JobContext) -> StepResult`.
- Reads only declared inputs from earlier steps; writes its output to `<storage>/jobs/<job_id>/<name>/` plus a small `result.json` (version, params, timings, counts).
- Idempotent: if `result.json` exists with the same step version and params, skip. Bump the step version when logic changes so only this and later steps rerun.
- Reports progress and errors to the `jobs` table; never swallows exceptions.
- Logs runtime and, for GPU steps, estimated cost.

## Data conventions
- Times in seconds from video start (float) plus game minute where known.
- Positions in pitch metres once calibrated (origin centre spot, x along the long side); image pixels only inside tracking internals.
- Visibility is explicit: never interpolate across gaps of the referee or assistants; mark them.
- Candidate thresholds favour recall; dismissed cards later tune them.

## Never
- Load whole videos into memory; stream frames.
- Add a model or repo without noting its license in `docs/lizenzen.md`.
- Import AGPL/GPL code (Ultralytics, opensportslib, MVFoul) into production steps; use RF-DETR, supervision and SAM 2.
