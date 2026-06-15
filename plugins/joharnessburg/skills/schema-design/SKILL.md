---
name: schema-design
description: Decide the internal knowledge schema from the app-first display contract and extraction plan — facts, rules, stories, wiki entries, screenplays, custom. Use whenever `.john/contracts/app_blueprint.json` and `.john/contracts/extraction_plan.json` exist but the internal schema is unsettled, you're about to enter the schema pilot/extract phase without a clear target schema, or anyone says "what format should we use?".
metadata:
  triggers:
    - design the schema
    - schema design
    - what format
    - knowledge schema
    - app-type definition
    - knowledge format
    - structure the knowledge
---

# schema-design

This is the most consequential decision in the knowledge phases. Get it wrong-or-too-rigid and every downstream phase pays for it (an earlier production system is a cautionary tale — see `references/sku-regression-case-study.md`). Get it right and the rest of the pipeline becomes obvious.

## What schema-design is NOT

- It's not picking from a closed menu. There is no "the John schema." Different projects want different shapes.
- It's not a one-shot decision. The schema **evolves** through the early phases as the corpus reveals itself.
- It's not a public UI contract. Public labels and visible modules live in `.john/contracts/app_blueprint.json`; schema fields are internal and must be mapped before display.
- It's not a question to push back to the user unless the one-shot product-question budget is unused and the choice is high-impact.

## The app-first cascade

John's default cascade is now user intent → app mechanism → display contract → extraction targets → internal knowledge format/schema → build pipeline. Schema is downstream of what the public app needs to show. The legacy knowledge-first cascade remains useful for template-specific projects, but vanilla John should not design schema in isolation and then let the UI inherit awkward internal fields.

You make schema decisions **only after** the corpus survey and app-first contracts are available. Reverse the order and you end up extracting tidy internal data that produces a confusing app.

## Before you design — read the corpus first

John's job is to *teach* schema design, not hand you a schema: abstract the methodology from prior projects — what to consider, when and how to iterate — and apply it here. That methodology starts with **reading what's actually in the corpus** before sketching a schema. Pre-designing in a vacuum is how you get over-fit or under-specified schemas.

Practical method:

1. **Read [[parsing]]'s output**. Walk through a representative sample of `<project>/.john/parsed/*/doc.md` (don't read everything; read enough to recognize patterns).
2. **Read app-first contracts**. Load `.john/brief/user_intent.json`, `.john/contracts/app_blueprint.json`, and `.john/contracts/extraction_plan.json`. If they do not exist, run [[app-design-thinking]] before schema-design.
3. **Ask survey questions** as you read:
   - Is the corpus mostly *atomic statements* (factual)?
   - Mostly *prescriptive how-to* (procedural / rules)?
   - Mostly *narrative* (storylines / characters / scenes)?
   - Heavy on *connections between entities* (relational / wiki)?
   - Mixed? Which mix?
4. **Notice structural features** the corpus already exhibits: causal chains, taxonomies, glossary-shaped terminology, recurring entities, citations, decision flowcharts.
5. **Cross-reference extraction targets** from `.john/contracts/extraction_plan.json`. A corpus full of facts might be extracted as concept cards, chapter digests, a searchable library, or a quiz bank; UI slots decide which fields matter.
6. **THEN sketch the schema** to fit (corpus shape × display contract × extraction targets), not to fit a default.

Skip this survey and you'll re-do the schema mid-extraction. Cheap to do early; expensive to fix late.

## Format options (the menu, but it's open)

Common forms knowledge takes:

- **Facts** (atomic statements with citations): for encyclopedic projects, briefings, knowledge bases
- **Rules** (trigger + decision + action): for verification, compliance, business-logic apps
- **Skills** (Claude Code-style how-to procedures): for distillation projects, where final output is itself reusable
- **Wiki entries** (long-form, cross-linked, browsable): for navigable knowledge products
- **Storylines** (character + event + setting + branching): for narrative/game projects
- **Screenplays** (scene + dialogue + direction): for content production
- **Graphs** (entities + typed relationships): for structured-data products
- **Custom**: for projects that don't fit. The user defines.

A project can have **multiple formats** — e.g., facts + skills + glossary, or storylines + character profiles. They don't have to share a schema.

## Schema shape per format

Design the schema for *this* corpus — there's no canonical shape to fill in. For illustrations of the *kind* of fields each common format tends to want (facts, rules, skills, wiki, storylines, screenplays, graphs), see `references/starter-schemas.md`. Read them as examples, not a menu. Header + body progressive disclosure stays universal regardless of which format you land on.

## The MECE principle

Extract "everything there is" OR "everything needed for what" — Mutually Exclusive, Collectively Exhaustive within the chosen schema. In app-first projects, "needed for what" is defined by `.john/contracts/extraction_plan.json`. **Don't extract the same fact three times under different schemas; don't leave any committed UI slot unsupported.**

MECE applies to coverage, not granularity — a fact and a rule that depends on the fact can coexist if they're in different formats. Inside a single format, no duplicates.

## Header + body — a universal layer above schema

Every entry, regardless of format, gets a two-tier structure:

- **Header**: one-line description + classification + cross-references. Pinned in any retrieval context; cheap to load.
- **Body**: full content. Loaded on demand when an extractor or runtime consumes the entry.

This is **not a schema choice** — it's a universal practice applied on top of whichever schema you design. The schema defines what fields the *body* has; the header is always present, always one-line + classification + refs. Enforced during [[knowledge-rewrite]]. Design the schema with this split assumed.

## The schema pilot — test before mass production

A schema that is only *designed* but never *tested* is a hypothesis, and betting hundreds of extractions on a hypothesis is how you discover a structural mismatch at the most expensive possible moment. Before the full fan-out, run a **schema pilot**:

1. Pick a **deliberately diverse 10–20 chunk sample** — and chase the corpus's *edge cases*, not its average. A pilot of typical chunks proves nothing; the chunks that looked weird in the survey (the table-heavy chapter, the appendix, the one document in a different genre) are exactly the ones that break schemas.
2. Extract the sample against the draft schema and `.john/contracts/extraction_plan.json` (the [[knowledge-extraction]] mechanics in miniature, or the `schema-designer` agent's iteration loop).
3. Check fit: did every pilot chunk's relevant content land in the schema without forcing? Did any UI slot stay unfillable? Did any field stay always-empty (over-design) or overflow into free text (under-design)?
4. Iterate the schema on what the pilot showed, *then* commit to the full extraction. Schema changes before bulk extraction are nearly free; after it, every change carries a migration bill.

Record the pilot's outcome (sample size, what changed) in PLAN.md's Log. [[phase-design]] treats the pilot as a natural early step of the extraction phase (or a thin phase of its own for large corpora).

## When to iterate the schema

You will. Plan for it.

- After parsing: realize the corpus has a kind of content you didn't anticipate (e.g., "this regulation has both rules AND a glossary; I need both formats").
- During extraction: an extractor subagent surfaces a structure that doesn't fit (e.g., "this rule has multi-step prerequisites the schema doesn't represent").
- During app design: the runtime needs a field the schema doesn't carry (e.g., "the concept page needs a plain-language explanation and a quote, but the schema only stores technical labels").

When iteration happens, **update PLAN.md's app-type definition section + the schema-design notes**. Log the change. Re-emit affected entries via corrective events ([[event-log-and-reducer]]) rather than rewriting the canonical state in place.

Three lines of discipline for mid-pipeline schema changes:

- **Give entries a `schema_version` field** (an integer is fine). It makes a mixed population *detectable from disk* — without it, "did we re-align everything after the change?" is unanswerable, which collides with disk-is-truth.
- **Adapt already-produced assets to the change** — never leave a silent mixed population; downstream phases assume uniformity.
- **Realign economically**: migrate the stale entries (reuse and modify what exists) rather than re-extracting everything from source, whenever the change permits it. `schema_version` is what tells you which entries are stale.

## Locking too early — the single-SKU regression

An earlier production system collapsed its research-grade 4-type schema (factual/relational/procedural/meta) into one 5-part SKU shape (`metadata/context/trigger/core_logic/output`). Easier to implement; lost information richness. The collapse was an over-fitting move for the verification domain; for general knowledge engineering it leaves entries forcibly squeezed into a shape they don't fit. Don't repeat. See `references/sku-regression-case-study.md`.

John's stance, in three rules drawn from the regression:

- **Let extraction targets constrain the schema, not internal taste.** If the UI needs concept cards, chapter digests, and source evidence, the schema must support those public slots even if the internal entry type is factual, relational, or mixed.
- **Templates may collapse types** if their domain only ever uses one. A doc-verification template can ship a rules-only schema. That's the template's choice, not core John's default.
- **Header + body progressive disclosure remains universal**, regardless of schema choice. See the universal layer below.

## Working with the user

Schema-design is agent-led after the app-first contracts are set. The user already had one chance to weigh in on product direction. If schema uncertainty is merely internal, choose the best schema, record assumptions, and continue. Ask only if the one-shot product-question budget is still unused and the decision would materially change the product. Capture the chosen schema in PLAN.md's app-type definition section before [[knowledge-extraction]] starts.

## Cross-references

- [[plan-md-authoring]] — where the app-type definition section first appears
- [[phase-design]] — phases the schema dictates
- [[knowledge-extraction]] — what reads against the schema
- [[knowledge-rewrite]] — header+body progressive disclosure enforcement
- [[packaging]] — final emission shape for skills format
- See `references/` for: app-type definition cascade dive, the research 4-type taxonomy, the single-SKU regression case study, KC's rule schema
