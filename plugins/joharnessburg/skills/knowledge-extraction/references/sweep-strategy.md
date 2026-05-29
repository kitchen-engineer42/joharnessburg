# sweep-strategy — what MECE means in extraction

Two framings for extraction: "everything there is" or "everything needed for what." Both modes are legitimate; the project's intent decides.

## Comprehensive sweep — "everything there is"

The right mode for encyclopedic/coverage-driven projects. Examples:

- A regulation: extract every rule the regulation contains.
- A textbook chapter: extract every concept, every example, every relationship.
- A wiki source: every entry, every cross-reference.

Comprehensive sweep is more expensive (more entries, more subagent calls) but it ensures the produced app or knowledge base isn't accidentally missing material.

## Goal-directed sweep — "everything needed for what"

The right mode when the project has a narrow goal and exhaustive coverage is wasteful. Examples:

- An FAQ generator: extract Q+A pairs relevant to a specific user-facing scenario; ignore in-the-weeds background.
- A summary app: extract claims and their sources; skip examples that aren't going to surface.
- A character-sheet generator from a novel: extract character details; skip plot mechanics.

Goal-directed sweep is cheaper but riskier — if you mis-state the goal, you mis-extract.

## How to choose

Ask the user during schema-design or plan-md-authoring. The four-structures section's *runtime structure* usually answers this:

- Runtime needs broad knowledge → comprehensive.
- Runtime answers specific kinds of questions → goal-directed, with the goal stated explicitly in PLAN.md.

If the user's unclear, ask. Don't guess. The choice affects the schema (goal-directed schemas can drop fields the goal doesn't need) and the briefing each subagent gets.

## MECE inside the scope

Regardless of mode, MECE inside the chosen scope:

- **Mutually Exclusive**: don't extract the same entry twice. Cross-chunk duplicates are common (a fact mentioned in two chapters) — the reducer's dedup handles this in [[knowledge-rewrite]]. Within one chunk, the extractor shouldn't emit duplicates.
- **Collectively Exhaustive**: don't leave the scope partially covered. The chunk_echo pattern (see `self-correction-echo.md`) helps catch chunks where the extractor under-extracted.

## Coverage check at end of phase

When the extract phase wraps:

1. Sanity check: every chunk should have at least one event (or a noted "intentionally empty" event for chunks with no in-scope content).
2. Volume check: does the entry count look reasonable for the corpus size? Wildly low → re-extract a sample; wildly high → check for duplicates.
3. Spot-check: random-sample 5-10 entries, read them, confirm they fit the schema and the scope.

Don't try to verify every entry. The reducer's deterministic fold gives you a single canonical state to inspect; spot-check that.

## When to expand the sweep mid-phase

Sometimes the comprehensive sweep reveals the schema needs to grow (a new field or a new type). Two options:

1. **Re-extract** affected chunks with the updated schema. Slow but produces the cleanest canonical state.
2. **Emit corrective events** for the new field — append to the event log, let the reducer fold them in. Faster but the reducer's fold function needs to handle the heterogeneous events.

Most projects: (2) is correct. Schema evolution should be cheap.
