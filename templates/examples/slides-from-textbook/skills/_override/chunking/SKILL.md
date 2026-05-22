---
name: chunking
description: Chunk the parsed textbook into slide-candidate units — one chunk per potential slide. Use this skill in the chunk phase of a slides-from-textbook project. Overrides John core's general chunking to target slide-shaped output; the unit is "one slide's worth of concept," not chapters or paragraphs.
metadata:
  triggers:
    - chunk the textbook
    - chunk by slide
    - slide-aware chunking
    - prepare for slide extraction
    - chunking phase
---

# chunking (slides-from-textbook override)

For slide decks, the chunk unit is **one slide's worth of teachable content** — typically one concept, one comparison, one example, one exercise. NOT one chapter, NOT one paragraph, NOT one heading section. The chunk size targets ~50-300 tokens of dense content per chunk (a slide can't fit more without becoming illegible).

This overrides John core's general `chunking` skill. The peeler/wrapper rubric still applies for source shape, but the *granularity* is slide-sized regardless.

## The slide-candidate boundary

A chunk = one slide-candidate when one of these is true:

- A new H3/H4 heading introduces a new concept.
- A worked example starts.
- A comparison/contrast pair is introduced.
- An exercise or question is posed.
- A figure, chart, or diagram with its surrounding explanation forms a coherent unit.
- A summary or recap appears.

If a section's prose runs longer than ~300 tokens without one of these boundaries, split mid-section at a natural sentence boundary; the renderer will use a "content-two-col" component to split visually.

## Heuristics for fitting

- **Too small (<50 tokens)**: probably not its own slide. Merge with the previous or following chunk under the same parent heading.
- **Right size (50-300 tokens)**: one slide. Emit as its own chunk.
- **Too big (>300 tokens)**: split at the first internal boundary (sub-heading, example boundary, sentence boundary). Smaller chunks → more slides → finer-grained progression.

## Visual_kind hint during chunking

While chunking, attach a `visual_kind` hint to each chunk's frontmatter based on what the content suggests:

- Has a chart or table → `chart` / `table`
- Has a worked example with steps → `chain-process` or `timeline`
- Has a definition + properties → `content-two-col`
- Has a quiz-able fact → `mcq` or `fill-blank`
- Has comparison → `comparison`
- Has a figure description → `image` or `svg`
- Has a video reference → `media-embed`
- Otherwise → leave blank; the renderer picks default `content-two-col`

This hint guides the render phase. It's a starting point; the renderer can override if the extract phase reveals a better fit.

## Output

Each chunk gets standard frontmatter (chunk_id, parent_id, source_doc, char_count, header_path) plus the slide-specific `visual_kind` and `slide_candidate_score` (0-1 confidence that this is a single slide vs needs further splitting).

Master index at `<project>/.john/chunks/chunks_index.json` — same shape as John core, plus the slide-specific fields.

## What this skill does NOT do

- It doesn't decide the slide *component* type (cover-slide, mcq, etc.). That's the render phase's job per `slide-rendering` skill.
- It doesn't extract the actual slide content. That's `knowledge-extraction`'s job — each chunk becomes one or more entries.
- It doesn't fetch media. That's a later phase (research agent or manual selection).

## Cross-references

- [[knowledge-extraction]] — what runs over the chunks next
- [[slide-rendering]] — what consumes the entries the extract phase produces
- [[phase-design]] — the survey phase's slide-count estimate informs the chunking budget
- [[subagent-dispatch]] — chunking is usually one main-agent pass, not a fan-out; for very long textbooks, fan out per chapter
