---
name: assessment-provider
description: How the AI assessment proposal per scene is built and which model provider is called. Use when changing prompts, the output schema, rule retrieval or the Claude/Gemini provider code.
---
# Assessment provider

## Interface
`assess(scene: SceneInput) -> Assessment` behind `ASSESSMENT_PROVIDER` (`claude` | `gemini`). Provider code lives in `worker/assessment/providers/`; nothing else imports a vendor SDK.

## Input
- Frames (Claude) or a short clip (Gemini) around the event, cropped to the duel.
- Scene facts: whistled yes/no, restart type, positions, distance of the referee.
- The 2-4 most relevant rule passages from the rule database (with rule number and season version).

## Output (strict JSON)
`decision` (foul | no_foul | unclear), `foul_type`, `sanction` (none | yellow | red), `rule_ref`, `confidence` (0-1), `reason` (German, max 3 sentences).
Invalid JSON is retried once, then stored as `unclear`.

## Cost
- Cheap model for every scene, stronger model only when confidence is low or providers disagree.
- Use batch APIs (not time-critical) and cache the static rule/system prompt.
- Log tokens and cost per scene and per match.

## Rules
- Never use phase 0 test scenes as examples in prompts.
- Similar, already reviewed scenes may be added as examples (learning loop stage 1), observer-released assessments first.
