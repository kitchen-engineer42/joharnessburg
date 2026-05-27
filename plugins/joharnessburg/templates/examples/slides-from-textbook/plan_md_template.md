# PLAN.md — {project_name}

*Created by `/joharnessburg:init` on {date}, using the **slides-from-textbook** template. Edit freely; this is your living plan.*

## Project intent

<!-- What textbook chapter or topic? Who's the audience (high-schoolers? grad students? professional learners?)? What's the deck size target (15 slides? 40?)? What's success — students understand X by the end? -->

## Knowledge inventory

- Initial input: `.john/input/` (textbook PDF or markdown)
- Produced skills (after 2skills half): `.claude/skills/` will contain per-slide concept entries + a glossary

## Four structures (per spec §4, pre-filled for slides)

- **Format of knowledge**: per-slide concepts. Each concept = one teachable idea that fits one slide.
- **Schema of knowledge**: `{id, concept, topic, visual_kind, visual_hint, component_type, difficulty, related[]}`. Header (one-line description + classification + cross-refs) and body (full elaboration + citation + visual specification).
- **Runtime structure**: single-page HTML slide deck. Arrow-key navigation. 13 component types: cover-slide, section-divider, content-two-col, timeline, bar-chart, chain-process, comparison, fill-blank, mcq, mini-game, canvas-sim, web-source, media-embed, summary. In-browser edit mode for teacher post-edit.
- **Production pipeline**: 6 phases below.

## Phases

### Phase 1: parse

- Intent: parse the input textbook/chapter into structured markdown.
- Skills to invoke: `parsing`
- Required artifacts: `.john/parsed/<source>/doc.md`
- Done criteria: doc.md exists with clean markdown; metadata.json records source path + parser

### Phase 2: survey

- Intent: read the corpus shape; estimate slide count; identify section structure.
- Skills to invoke: `phase-design` (for surveying)
- Required artifacts: `.john/checkpoints/survey/observations.md`
- Done criteria: section list with target slide counts per section

### Phase 3: schema-design

- Intent: confirm the per-slide schema (mostly pre-filled above); decide visual_kind taxonomy specific to this corpus.
- Skills to invoke: `schema-design`
- Required artifacts: `.john/checkpoints/schema/schemas.md`
- Done criteria: user has reviewed + approved the schema sketch

### Phase 4: chunk

- Intent: chunk by slide-candidate (one chunk per potential slide). Override of John core's chunking; see `chunking` skill.
- Skills to invoke: `chunking` (template-overridden version)
- Required artifacts: `.john/chunks/<id>.md` + `chunks_index.json`
- Done criteria: chunks_index.json lists N chunks (matches survey's slide-count estimate)

### Phase 5: extract (subagent fan-out per chunk)

- Intent: extract per-slide concept entries from each chunk.
- Skills to invoke: `knowledge-extraction`, `subagent-dispatch`, `event-log-and-reducer`
- Required artifacts: `.john/events/extract/<chunk-id>/*.json`; `.john/checkpoints/extract/state.json`
- Done criteria: every chunk has at least one entry_extracted event; reducer's canonical state has the expected entry count

### Phase 6: render + assemble (the 2app deliverable)

- Intent: map each entry to a slide component; render HTML per slide; assemble single .html file with inlined media.
- Skills to invoke: `slide-rendering` (template-provided), `packaging`
- Required artifacts: `<app-output>/deck.html`
- Done criteria: deck.html opens in a browser, all slides render, arrow-key nav works, no broken media refs

## Subagent matrix

*Populated by the extract phase when fan-out begins.*

## Open Decisions

*Capture decisions you want the user to weigh in on. Examples for a slides project:*
- Should slides include audio narration? (affects assets/ size and runtime)
- One deck per chapter, or one deck per section? (affects chunk count and pipeline)
- Bilingual content (zh/en) or single language?

## Log

- {date}: PLAN.md scaffolded by `/joharnessburg:init` using the slides-from-textbook template.
