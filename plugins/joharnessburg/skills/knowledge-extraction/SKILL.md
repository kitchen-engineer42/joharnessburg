---
name: knowledge-extraction
description: Sweep chunks for entries that satisfy the app-first extraction plan and internal schema, then emit them via the event log. Use whenever the chunk phase has produced chunks and the schema pilot/full extraction phase is next, when the user says "extract X from the corpus," or when [[ralph-loop]] advances into extraction. Subagent fan-out is the norm; each subagent processes one chunk; canonical state lives in the reducer's output.
metadata:
  triggers:
    - extract knowledge
    - extract entries
    - sweep the chunks
    - fan out extraction
    - run the extractor
    - extract rules
    - extract facts
    - extraction phase
---

# knowledge-extraction

The phase where chunks become entries. This is where the vertical axis of John's matrix earns its keep — hundreds of subagents in parallel, each processing one chunk, each emitting events the reducer folds into canonical state. Without subagent fan-out, this phase doesn't scale.

## Where the work happens

- **Inputs**: `<project>/.john/chunks/<chunk-id>.md` + `<project>/.john/chunks/chunks_index.json` (from [[chunking]])
- **Display/extraction references**: `.john/contracts/app_blueprint.json` + `.john/contracts/extraction_plan.json` (from [[app-design-thinking]])
- **Schema reference**: PLAN.md app-type definition section (per [[schema-design]])
- **Outputs**: subagents emit to `<project>/.john/events/extract/<chunk-id>/<subagent-id>-*.json` (one file per event; exact event shapes and filename suffixes are in the `knowledge-extractor` agent definition); reducer (`${CLAUDE_PLUGIN_ROOT}/scripts/reduce_events.py extract`) folds to `<project>/.john/checkpoints/extract/state.json`; canonical state then drives [[knowledge-rewrite]].

## The MECE sweep

Extract "everything there is" OR "everything needed for what" — which one depends on the project's intent. In app-first projects, "needed for what" is primarily `.john/contracts/extraction_plan.json`. Decide that early and let it shape the sweep.

- **Comprehensive sweep**: "extract everything there is in this corpus that matches the schema." Right for encyclopedic projects, regulations, broad knowledge bases.
- **Goal-directed sweep**: "extract everything needed to fill these UI slots." Right for ordinary-user apps where coverage outside the public experience is wasteful.

Either way, MECE applies to coverage within the chosen scope: don't extract the same entry twice; don't leave the scope partially covered. Dedup across chunks happens later, in the rewrite phase (see [[knowledge-rewrite]]'s two-tier dedup) — the shipped reducer folds events without deduplicating; your job is to give that pipeline good raw events.

## Fan-out per chunk

For each chunk, dispatch a subagent. Brief them comprehensively (per [[subagent-dispatch]]'s checklist):

1. **Project intent** (from PLAN.md top).
2. **The chunk** they're processing — the chunk file path or contents.
3. **The public app blueprint** — user-facing pages, labels, forbidden visible terms.
4. **The extraction plan** — which UI slots this chunk might help fill.
5. **The schema reference** — what an internal entry looks like, what fields, what cross-link semantics.
6. **The event log target** — where to write events (`<project>/.john/events/extract/<chunk-id>/`).
7. **What to return** — a one-line digest. No raw extracted content in the digest; that's in the event log.
8. **What NOT to do** — don't write canonical state directly; don't ask the user; don't expose internal field names as public labels; don't try to dedupe across chunks (the reducer does that).

For small corpora (<10 chunks), inline extraction in the main agent context is fine. For real-world corpora (10s-1000s of chunks), always fan out.

## The self-correction echo (mathlab pattern)

Borrowed from mathlab's "ops[0] echoes the problem" trick: have each extraction subagent's first action be to **echo back its understanding of the chunk** before extracting from it. This catches misreading, character encoding bugs, and chunks-handed-to-the-wrong-subagent failures cheaply.

Mechanically: the briefing includes the instruction *"Before extracting any entries, emit an event of type `chunk_echo` with a 2-3 sentence summary of what this chunk says. Then proceed."* The reducer folds the echoes into the checkpoint (and its completeness check flags chunks missing one); YOU spot-check them there — a wildly off-base echo flags a chunk for re-extraction.

Cost: one event per chunk's worth of summarization. Cheap compared to re-running an extraction that silently extracted from the wrong chunk.

## Schema iteration during extraction

[[schema-design]] says the schema will iterate. Extraction is one of the phases where iteration surfaces:

- An extractor reports *"this chunk has structure the schema doesn't represent."* The subagent emits a `schema_observation` event to the same event log; these fold into the extract phase's canonical state alongside the other events (filter on `event_type` when reviewing; a template's custom reducer may split them into a separate observations array).
- You (the main agent, per [[ralph-loop]]) review these observations after the phase-fanout completes. If N≥3 observations point at the same gap, first decide whether to extend the schema or adapt the app blueprint. Ask the user only if the one-shot product-question budget is unused and the gap is a high-impact product decision; otherwise record an assumption or blocker in PLAN.md.
- [[knowledge-rewrite]] also reads these observations during the rewrite phase to guide cross-linking and dedup decisions — observations may flag entries that should be kept separate despite similarity.
- Don't re-extract the entire corpus on every schema change. Use corrective events instead: a new `entry_replaced` event supersedes the older one. The reducer's fold function handles supersession deterministically.

## Model tier per chunk

John core uses Claude's defaults: Opus for the main agent, Sonnet/Haiku for subagents per task. For extraction subagents:

- **Sonnet** is usually right. Extraction needs decent reading comprehension + schema adherence; Sonnet has both.
- **Haiku** works for highly structured chunks (e.g., extracting facts from a clean table). Cheap, fast.
- **Opus** for chunks with judgment-heavy content (e.g., extracting *intent* from a legal preamble where the wording is deliberately vague).
- **WorkerLLMs** (SiliconFlow, DeepSeek, etc.) where templates wire them — typically for very high volume on cost-sensitive projects. The template owns the routing.

Don't model-shop chunk by chunk; pick a tier for the phase and stick with it unless evidence forces an escalation.

## When the extraction phase is done

Per [[ralph-loop]] step 4-5 (the run-reducer-and-update-PLAN cycle), the main agent runs the reducer at the end of the fan-out wave — **gated**, with the expected entry count/range from PLAN.md's extract-phase done criteria:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/reduce_events.py" extract --expect-entries 35-50 --verify-knowledge
```

Exit 3 = far short of the expected count: the phase is not done; find and re-dispatch the missing work before anything else. Then verifies:

- All chunks have at least one event in `events/extract/<chunk-id>/`.
- The reducer ran without errors and produced `checkpoints/extract/state.json`.
- The chunk_echo events look reasonable (manual spot-check).
- Each committed UI slot in `.john/contracts/extraction_plan.json` has enough extracted support to render a minimum viable public view.
- Coverage: every chunk that should have produced entries has produced entries; chunks that legitimately had no schema-matching content are noted.
- PLAN.md's extract phase Done criteria are satisfied (see [[phase-design]]).

If coverage is weak (some chunks empty), decide: re-extract with better briefing? Or accept that the corpus has gaps and proceed? Often the latter, with a Log entry recording the gap.

## What this skill does NOT do

- **Schema design.** That's [[schema-design]]; do that first.
- **App blueprint design.** That's [[app-design-thinking]]; do that before schema design.
- **Chunk creation.** That's [[chunking]].
- **Cross-linking + dedup.** That's [[knowledge-rewrite]], the next phase.
- **Final emission as Claude Code skills.** That's [[packaging]].

## Cross-references

- [[app-design-thinking]] — public app blueprint and UI-driven extraction targets
- [[schema-design]] — internal schema derived from those targets
- [[chunking]] — where chunks come from
- [[subagent-dispatch]] — the fan-out mechanism
- [[event-log-and-reducer]] — how subagent outputs become canonical state
- [[knowledge-rewrite]] — the next phase
- [[ralph-loop]] — what advances the phase
- See `references/` for: sweep strategy detail, the self-correction echo pattern, extraction briefing template
