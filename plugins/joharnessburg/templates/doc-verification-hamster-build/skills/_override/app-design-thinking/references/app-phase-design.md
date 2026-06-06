# app-phase-design — common patterns

The app phases don't have a default pipeline (the way the knowledge phases have a parse → survey → schema-design → chunk → extract → rewrite → package suggestion). Build pipelines for apps are too varied. But there are recurring shapes.

## Shape 1: Static-output app

For apps where the output is a static deliverable (slides, portfolio, wiki, vote page):

```
1. scaffold — set up framework/project structure, install deps
2. wire content layer — pull entries from .claude/skills/, structure into the runtime's data model
3. wire layout/rendering — pages, components, templates
4. assemble — produce the final static output (HTML, JSON, etc.)
5. preview + iterate — natural-language edits, deterministic guardrails
6. publish — deploy/upload the artifact
```

Typical: 4-6 phases. Pipeline is mostly sequential.

## Shape 2: Interactive runtime app

For apps where the end-user interacts repeatedly (games, chat, verifier):

```
1. scaffold
2. wire core mechanics — the central loop the user interacts with
3. wire data layer — runtime state, persistence
4. seed content — pull from .claude/skills/ into the runtime
5. wire runtime LLM (if applicable) — provider abstraction, prompts, fallback
6. wire UX — error states, edge cases, polish
7. wire observability — telemetry (if production)
8. deploy
9. smoke test + iterate
```

Typical: 6-9 phases. Some can run in parallel (UX polish + telemetry).

## Shape 3: Tool/utility app

For apps that do a specific bounded thing on demand (verifier, parser builder, transformer):

```
1. scaffold
2. wire I/O — define what the user provides and what they get back
3. wire core logic — pull the relevant skills from .claude/skills/
4. test against known inputs — produce a confidence threshold
5. wire interface — CLI, web, or API
6. deploy
```

Typical: 4-6 phases.

## Choosing phases for your project

Start by asking [[app-design-thinking]]'s four runtime questions, then walk the shape closest to the runtime answer and adapt. The lists above are patterns, not requirements; templates often ship more domain-specific phase pipelines (e.g., a doc-verification template might have its own 7 phases tuned for compliance work).

## Phase enforcement is soft

Phases are closer to phases-as-skills, but leave room for a template to overwrite them. John provides the most general level of phase as a suggestive, not enforcing, guideline.

Don't write rigid phase definitions. Write phase intents + done criteria; let layer-2 Claude (and the user) judge when each is satisfied. See [[phase-design]] for the general rubric and [[workspace-discipline]]'s "verify done criteria" pattern.

## Subagent fan-out in the app phases

Not every app phase fans out, but some can:

- **Content seeding** (Shape 1 step 2, Shape 2 step 4): if each skill maps to one piece of content, fan out per skill. Each subagent transforms one skill entry into the runtime's data shape.
- **Per-feature implementation**: for apps with many independent features, fan out per feature. Each subagent implements one feature in isolation; reducer assembles.
- **Polish + edge-case fixes**: rarely worth fanning out (these are sequential decisions about what to fix).

See [[subagent-dispatch]] for the briefing pattern and [[event-log-and-reducer]] for the coordination model.

## When phases reveal schema gaps

An app phase might surface that the schema from the knowledge phases doesn't carry a field the runtime needs. Don't silently work around it — emit a `schema_observation` event (same pattern as [[knowledge-extraction]]), update PLAN.md's Open Decisions, decide with the user whether to extend the schema and re-emit affected entries, or adapt the runtime to what the schema gives. The cascade goes both ways.

## Source

Shapes synthesized from the 5 reference apps' pipelines (see `app-archetypes.md`) plus a production app-builder's 8-stage pipeline (init → coding → review → build → run → health → deploy → success).
