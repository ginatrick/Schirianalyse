---
name: eval-against-annotation
description: Evaluates pipeline output against the phase 0 hand annotation (docs/annotation-template.csv format). Use to check a phase gate, compare models or measure the effect of a pipeline change.
---
# Evaluation against hand annotation

## Matching
- Annotation rows from `data/annotations/<match_id>.csv`; detected scenes from the job output or the `scenes` table.
- A detection matches an annotated event of the same type if their times differ by at most 2 s (whistles) or 3 s (fouls, flags).

## Metrics per match and overall
- Whistles: recall, precision.
- Fouls not whistled: recall of annotated fouls among candidates; candidates per match (review load).
- Assessment: agreement of the AI decision with the annotation/observer decision, per decision class; share of `unclear`.
- Officials: share of time the referee was tracked; distance vs GPS where available; position error at sampled annotation points.
- Cost: GPU minutes and model cost per match.

## Report
`docs/eval/YYYY-MM-DD-<topic>.md`: setup (versions, provider, params), a table of the metrics, the three most important findings, a recommendation. Numbers only, no video content or personal data.
