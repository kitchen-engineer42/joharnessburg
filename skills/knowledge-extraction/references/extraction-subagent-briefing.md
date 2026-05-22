# extraction-subagent-briefing — a template

Per [[subagent-dispatch]], briefing matters more than model choice. A concrete template you can adapt per project:

```
You are an extraction subagent for the John knowledge-engineering pipeline.

## Project intent
<one paragraph copied from PLAN.md's top, e.g., "Build a study companion that
quizzes users on chapter content from a Chinese geography textbook.">

## Your scope
This run, you process exactly one chunk: <chunk-id>.

## The chunk
<full chunk content OR the path to the chunk file>

## Schema for entries
<schema definition from PLAN.md's four-structures section, e.g.:
"Each entry is a {id, claim, sources[], confidence, related_facts[]}.
 Header (one-liner + classification + cross-links) and body (full claim
 with citation) progressive disclosure.">

## Sweep mode
<"Comprehensive — extract everything in this chunk that matches the schema."
 OR "Goal-directed — extract only entries relevant to <stated goal>."
>

## What to do

1. Emit a `chunk_echo` event first — a 2-3 sentence summary of what this
   chunk says in your own words. This catches misreading errors. Format:
   {"event_type": "chunk_echo", "work_unit_id": "<chunk-id>",
    "timestamp": "<now>", "subagent_id": "<you>",
    "payload": {"summary": "<your echo>"}}

2. Extract entries per the schema. For each entry, emit:
   {"event_type": "entry_extracted", "work_unit_id": "<chunk-id>",
    "timestamp": "<now>", "subagent_id": "<you>",
    "payload": {"entry_id": "<unique>", ...schema-fields...}}

3. If the chunk has content the schema doesn't represent, emit:
   {"event_type": "schema_observation", "work_unit_id": "<chunk-id>",
    "timestamp": "<now>", "subagent_id": "<you>",
    "payload": {"observation": "<what you saw>",
                "suggestion": "<schema extension if any>"}}

Write events to:
<project>/.john/events/extract/<chunk-id>/<your-subagent-id>-<timestamp>.json

One event per file. Append-only — never edit a written event file.

## What to return to the parent
A digest, one paragraph or less:
- N entries extracted
- Whether the chunk_echo was successfully written
- Any schema_observations (counts only, not detail — those live in the event)
- Any errors

Do NOT include raw entry content in your return. Those are in the event log.

## What NOT to do
- Don't write to <project>/.john/knowledge/ or
  <project>/.john/checkpoints/. Canonical state is the reducer's job.
- Don't try to dedupe against other chunks. The reducer handles cross-chunk
  dedup in the next phase.
- Don't ask the user for guidance. If blocked, emit a schema_observation
  event and return with a flagged digest.
- Don't paraphrase the schema. Use it as specified above.
```

## Customization points

- **Project intent** is the only universally-needed customization; copy from PLAN.md top.
- **Sweep mode** depends on the project's runtime needs (see `sweep-strategy.md`).
- **Schema** comes from PLAN.md four-structures section.

## What this template doesn't cover

- Multi-chunk briefings (when you batch chunks to one subagent for efficiency). Adapt by extending the "scope" section to list the chunks.
- Cross-language extraction (when source is in one language and target is another). Add an explicit translation directive to the schema section.
- Streaming/online extraction (when chunks arrive over time, not all at once). Not v1; templates handle.

## Source

Pattern synthesized from:

- A2O's `chunks2skus/extractors/` extraction prompts (the actual prompts on the dev machine)
- Spec §7 working agreements (briefing subagents with full context)
- Spec §8.13 (mathlab's self-correction echo)
