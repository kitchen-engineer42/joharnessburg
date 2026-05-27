# PLAN.md — synthetic-5-phase-project (test fixture)

*Synthetic PLAN.md used to verify M1+M3+M4 skill guidance applies cleanly to a realistic structure. NOT a real project. Lives in `joharnessburg/tests/fixtures/`.*

## Project intent

Build a quiz app from a single chapter of a high-school biology textbook (provided as PDF). The runtime is a single-page web app where students answer multiple-choice questions about the chapter; the build pipeline parses the chapter, extracts key concepts as facts, and produces a quiz with explanations.

## Knowledge inventory

- Initial input: `.john/input/bio-chapter-3.pdf` (one PDF, ~60 pages)
- Produced skills (after 2skills half): `.claude/skills/` will contain ~30 fact entries + a glossary

## Four structures (per spec §4)

- **Format of knowledge**: facts (atomic biology claims) + glossary (technical terms)
- **Schema of knowledge**: facts have `{id, claim, citation, difficulty, glossary_refs[]}`; glossary entries have `{term, definition, used_in_facts[]}`. Header (one-liner + difficulty + classification) and body (full claim with citation + 1-paragraph elaboration).
- **Runtime structure**: single-page web app, served as static HTML + JSON data file. User clicks "Start," answers MCQ questions one at a time, gets immediate feedback. No runtime LLM.
- **Production pipeline**: phases below.

## Phases

### Phase 1: parse ✓ done 2026-05-23

- Intent: parse `bio-chapter-3.pdf` into structured markdown for downstream extraction.
- Skills to invoke: `parsing`
- Required artifacts: `.john/parsed/bio-chapter-3/doc.md`, `.john/parsed/bio-chapter-3/doc.json`, `.john/parsed/bio-chapter-3/metadata.json`
- Done criteria: `doc.md` exists with >5000 characters of clean markdown; `metadata.json` records source path + jyppx parser + timestamp.

### Phase 2: chunk + extract

- Intent: chunk the parsed markdown into sections (one per textbook section header), then extract fact entries from each chunk via subagent fan-out.
- Skills to invoke: `chunking`, `knowledge-extraction`, `subagent-dispatch`, `event-log-and-reducer`
- Required artifacts: `.john/chunks/<id>.md` files + `chunks_index.json`; `.john/events/extract/<chunk-id>/*.json`; `.john/checkpoints/extract/state.json`
- Done criteria: every chunk has at least one `entry_extracted` event; reducer produces canonical state with ~30 entries.

#### Subagent matrix

| Work unit | Status | Events | Entries |
|---|---|---|---|
| chunk_001 (3.1 Cells) | done | 4 | 6 |
| chunk_002 (3.2 DNA) | done | 5 | 8 |
| chunk_003 (3.3 Photosynthesis) | done | 3 | 5 |
| chunk_004 (3.4 Respiration) | in_flight | 1 | — |
| chunk_005 (3.5 Reproduction) | pending | 0 | — |
| chunk_006 (3.6 Evolution) | pending | 0 | — |

### Phase 3: rewrite + cross-link + package

- Intent: rewrite entries for header+body progressive disclosure; cross-link facts to glossary terms; package as Claude Code skills at `.claude/skills/`.
- Skills to invoke: `knowledge-rewrite`, `packaging`
- Required artifacts: `.claude/skills/bio-fact-*/SKILL.md` files; `.claude/skills/bio-glossary/SKILL.md`
- Done criteria: every fact has a header + body; every glossary term has a corresponding entry; cross-links resolve.

### Phase 4: TBD — quiz app scaffolding and content seeding

- Intent: TBD. Will settle after Phase 3 ships and we see the actual facts that came out.
- Tentative: scaffold a static SPA, seed facts into a JSON data file, render MCQ component.
- Skills to invoke (anticipated): `app-design-thinking`, `phase-design` (for subdividing if needed)

### Phase 5: TBD — polish + deploy

- Intent: TBD. Will settle after Phase 4. Likely: error states, mobile responsiveness, deploy as a static site.
- Tentative skills: `code-quality-guardrails`

## Open Decisions

1. Should the quiz randomize question order each session, or present them in chapter order? (Affects runtime data loading and UX.)
2. Question difficulty: pull difficulty from the fact schema, or compute from a different signal? (Schema currently has `difficulty` field but it's not populated yet — extraction hasn't decided how to set it.)

## Log

*Append-only, most recent first.*

- 2026-05-23: Phase 1 done. doc.md = 8,234 chars; metadata.json records jyppx parse with default backend. Spot-check shows clean OCR.
- 2026-05-23: Phase 2 partially done (3 of 6 chunks). chunk_004 in flight; chunk_005 + chunk_006 pending. Reducer not run yet; will run when all chunks complete.
- 2026-05-22: Schema confirmed: facts + glossary. Header has classification, difficulty, cross-refs. Decision logged after corpus survey (parsing's doc.md confirmed the chapter is fact-heavy with ~40 technical terms — supports the format choice).
- 2026-05-22: PLAN.md scaffolded by `/joharnessburg:init`.
