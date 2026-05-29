# app-archetypes — 5 reference shapes from our subsites

Five apps the team built manually before John existed. Each is one combination of runtime structure + production pipeline. They're reference shapes — patterns to pattern-match new projects against — not a closed menu. Wide tunnel: templates and projects invent their own when these don't fit.

## 1. Portfolio builder (create-any-portfolio)

**Runtime**: a user uploads resume/project materials, has a conversational chat with the app to design their portfolio, then the app generates a Next.js static site (hero / about / projects / skills / timeline / education sections) and hosts it.

**Pipeline shape**: ingest materials → entity extraction (person, projects, skills, etc.) → conversational PRD generation → spec compile → code-gen (Code Agent with 15+ deterministic guardrails) → static site build → preview/iterate via natural-language Edit Agent → publish.

**Why it's useful as a reference**: knowledge-heavy at build-time (entity graph extraction); produces a static deliverable (no runtime LLM); has natural-language iteration after first build (Edit Agent loop).

## 2. Mystery detective game (mystery-detective-game)

**Runtime**: a single-player text-based deduction game. Player interrogates suspects, challenges lies, searches scenes, submits an archive card. LLM responses for dialogue at every player turn; case generated up front by SOTA LLM (with local fallback).

**Pipeline shape**: AI-driven case generation (with local fallback) → seed clues + suspects + scenes → wire game state machine → wire runtime LLM proxy (Doubao) → polish → deploy. 38 hand-curated golden cases as quality reference.

**Why it's useful**: heavy at both build (case gen) and runtime (NPC dialogue). Dual-path (AI primary + local fallback) as production resilience.

## 3. Lesson-to-slides (lesson2slides)

**Runtime**: teacher uploads a textbook chapter, gets back a downloadable HTML slide deck with interactive slides, mini-games, quizzes, embedded media. Arrow-key navigation, in-browser SVG editor for post-edit. Output is one .html file with base64-inlined media.

**Pipeline shape**: extract lesson text (with cascading parser fallback) → plan spec (slide-by-slide) → research-agent fetches media from the web → render HTML slide fragments → assemble single .html file.

**Why it's useful**: heavy at build, no runtime LLM. Locked component templates (model fills placeholders, doesn't design containers). Strong example of skill-as-template constraint.

## 4. Mathlab (mathlab)

**Runtime**: student pastes a math problem (text + optional image), gets back an interactive geometry/calculus widget. GPT-5.5 vision generates JSON `ops` at runtime that the client interprets into draggable, constraint-linked figures. Teacher can edit in-browser and export standalone HTML.

**Pipeline shape**: build-time is hand-coded (the geometry engine, the ops DSL, the constraint solver). No knowledge engineering pipeline; the team wrote the app. Runtime LLM at every user request.

**Why it's useful**: the only one where LLM lives at runtime, not build-time. The team built the runtime by hand; John's analog would be John+mathlab-template producing John-driven math apps for specific corpora. Imperative DSL (`ops`) is the right shape for runtime LLM output.

## 5. Vote for your app (voteforyourapp)

**Runtime**: a public voting page (real-time leaderboard, 5-vote-per-user cap, search, upload modal). Vanilla HTML SPA with 3-second polling against a thin Express+Postgres backend. Zero LLM.

**Pipeline shape**: design (mock HTML) → template+logic injection script (regex-rewrite) → Docker compose deploy. No knowledge engineering, no LLM.

**Why it's useful**: the simplest end of the spectrum. Some apps don't need much — a flat schema, a thin API, a polled SPA. John's templates should accommodate this minimum.

## What these archetypes have in common

- **Build-time vs runtime LLM split is the biggest dimension.** Mathlab is runtime-heavy; voteforyourapp has none; the others are build-time heavy.
- **Output shape varies wildly**: static HTML file, deployed container, downloadable widget, browser SPA.
- **Knowledge density varies**: portfolio's entity graph is dense; voteforyourapp has 3 flat tables. John spans both.

## When none of these fit

Invent. The 5 above are precedents, not categories. Real projects often combine elements — e.g., a quiz app might have voteforyourapp's polling + mystery-detective-game's runtime LLM + lesson2slides' build-time content generation.

## Source

The 5 reference subsites each have their own README and design docs with deeper analysis. The production `skills2app` service builds apps like these via Celery — that's the system John eventually replaces.
