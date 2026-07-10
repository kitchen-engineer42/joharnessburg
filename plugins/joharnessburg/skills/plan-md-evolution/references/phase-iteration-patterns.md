# phase-iteration-patterns — subdivide / merge / drop / insert

Four patterns. Each has a "when" and a "how." All require a Log entry.

## Subdivide

**When**: a phase turns out to contain too much. Common signal: you're advancing the phase and realize you've been doing two distinct things that should have separate done criteria.

**Example**: "Phase 3: extract knowledge" turned out to need both summary-level extraction (read the chapter, produce one-paragraph summary) and detail-level extraction (read each section, produce schema-shaped entries). Different prompts, different verification.

**How**:
1. Append a Log entry: "Phase 3 subdivided into 3a (summary extraction) and 3b (detail extraction). Rationale: ..."
2. Split the Phase 3 section into 3a + 3b. Each gets its own intent, skills, artifacts, done criteria.
3. The original Phase 3's done criteria becomes the union of 3a + 3b's.
4. Renumber subsequent phases (Phase 4 stays Phase 4; only the subdivided one is renamed).
5. If subagent fan-out was planned, redistribute units across 3a + 3b.

## Merge

**When**: two adjacent phases turn out to be so coupled that running one without the other corrupts state. Less common than subdivide.

**Example**: "Phase 5: cross-link entries" and "Phase 6: deduplicate" turned out to share too much logic — buckets are computed once, used for both. They should be one phase.

**How**:
1. Append a Log entry explaining the coupling.
2. Combine the sections into one. Take the union of intents, skills, artifacts, done criteria.
3. Renumber subsequent phases.

## Drop

**When**: a phase's intent no longer applies. Often because the corpus or runtime decision invalidated the assumption that made the phase necessary.

**Example**: "Phase 4: research and embed media" planned for a slide deck — but the corpus turned out to be all text and the user decided no media is needed. Phase 4's intent doesn't apply.

**How**:
1. Append a Log entry: "Phase 4 dropped. Rationale: corpus is text-only; runtime doesn't need media."
2. Keep the Phase 4 section as a struck-through stub for traceability. (Markdown: `### ~~Phase 4: research and embed media (DROPPED)~~`)
3. Adjust subsequent phases that depended on Phase 4's artifacts.

Why keep the stub: a fresh John-equipped session reading PLAN.md sees the historical context. Without the stub, the gap looks like an error.

## Insert

**When**: a phase you didn't anticipate is needed. Often surfaced by an extraction or app-design phase revealing a missing step.

**Example**: "Phase 5: cross-link entries" requires that proper nouns be resolved across the corpus — but the entries from Phase 3 have inconsistent name spellings. Need to insert "Phase 4.5: coreference resolution" before Phase 5.

**How**:
1. Append a Log entry: "Inserting Phase 4.5 (coreference resolution) before Phase 5. Rationale: extracted entries have inconsistent name spellings; Phase 5's cross-linking needs canonical names."
2. Add the new phase section. Decimal-numbered (4.5) to preserve neighbors' numbers, or full renumbering (4.5 becomes new 5, old 5 becomes new 6) — your choice. Decimal is less disruptive.
3. If decimal-numbered, note in the Log that the numbering is non-sequential by design.

## Promoting TBD to concrete

**When**: a phase was sketched as `TBD — decide after Phase N ships` and now Phase N has shipped. Time to settle the TBD.

**How**:
1. Confirm Phase N is actually done (disk-verifiable).
2. With the user, settle the TBD phase's intent, skills, artifacts, done criteria — same as if it were a freshly-authored phase per [[plan-md-authoring]].
3. Append a Log entry: "Phase X resolved from TBD. ..."
4. Update the phase section with the now-concrete fields.

## What you don't do

- **Edit prior Log entries.** They're append-only. Mistakes get superseded by new entries, not erased.
- **Re-number phases multiple times in a project.** Numbering churn confuses readers. If you're inserting frequently, consider decimal numbering as a stable convention.
- **Mass restructures.** If the plan needs a major rewrite, that's [[plan-md-authoring]] territory — archive the old PLAN.md, re-author, log the migration.

## Source

Patterns synthesized from John's phase-orchestration design + KC's "milestones derived from disk" principle + real experience iterating a PLAN.md (milestones routinely subdivide, insert, and promote phases as work proceeds).
