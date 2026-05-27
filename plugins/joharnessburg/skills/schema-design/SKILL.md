---
name: schema-design
description: Decide what shape the knowledge takes in this project — facts, rules, stories, wiki entries, screenplays, custom. Use whenever the user is starting a project, the four-structures section of PLAN.md is unsettled, you're about to enter the extract phase without a clear target schema, or anyone says "what format should we use?". Schema decisions cascade — get this loose enough to iterate but specific enough to write a starter extractor.
metadata:
  triggers:
    - design the schema
    - schema design
    - what format
    - knowledge schema
    - four structures
    - format of knowledge
    - structure the knowledge
---

# schema-design

This is the most consequential decision in the 2skills half. Get it wrong-or-too-rigid and every downstream phase pays for it (the production `to-skills-backend` is a cautionary tale — see `references/to-skills-backend-sku-regression.md`). Get it right and the rest of the pipeline becomes obvious.

## What schema-design is NOT

- It's not picking from a closed menu. There is no "the John schema." Different projects want different shapes.
- It's not a one-shot decision. The schema **evolves** through the early phases as the corpus reveals itself.
- It's not a JSON spec for layer-2 Claude to autocomplete. It's a *taste call* the user owns.

## The four-structures cascade

Per spec §4: format → schema → runtime → production-pipeline. Each constrains the next. Schema is the second link in the chain — downstream of *what kind of knowledge* and upstream of *what the app does*. The cascade itself is explained in `references/four-structures-cascade.md` and applied in [[plan-md-authoring]]; this skill is where the *schema link* gets designed.

You make schema decisions **only after the format decision is roughly settled**. Reverse the order and you end up over-fitting the schema to the corpus, then re-doing it when the runtime asks for something the schema can't represent.

## Before you design — read the corpus first

Per spec §8.4: *"John should teach Claude to design a good schema. Abstract from previous projects the methodology, tell Claude what to consider, when and how to iterate."* That methodology starts with **reading what's actually in the corpus** before sketching a schema. Pre-designing in a vacuum is how you get over-fit or under-specified schemas.

Practical method:

1. **Read [[parsing]]'s output**. Walk through a representative sample of `<project>/.john/parsed/*/doc.md` (don't read everything; read enough to recognize patterns).
2. **Ask survey questions** as you read:
   - Is the corpus mostly *atomic statements* (factual)?
   - Mostly *prescriptive how-to* (procedural / rules)?
   - Mostly *narrative* (storylines / characters / scenes)?
   - Heavy on *connections between entities* (relational / wiki)?
   - Mixed? Which mix?
3. **Notice structural features** the corpus already exhibits: causal chains, taxonomies, glossary-shaped terminology, recurring entities, citations, decision flowcharts.
4. **Cross-reference user intent** from PLAN.md's project intent + runtime structure (the four-structures cascade). A corpus full of facts might suit a quiz app (procedural runtime) OR a wiki (browsable runtime); user intent decides.
5. **THEN sketch the schema** to fit (corpus shape × user intent), not to fit a default.

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

## Schema shape per format (starting points)

For each format, a starter schema. **These are starting points, not requirements.** Wide tunnel.

- **Facts**: `{id, claim, sources[], confidence, related_facts[]}`. Header (one-liner) + body (full elaboration).
- **Rules**: `{id, source_ref, trigger, judgment, decision_tree, glossary_refs[]}`. From KC's design — see `references/kc-rule-schema.md`.
- **Skills**: SKILL.md frontmatter (name, description) + body + optional `references/`/`scripts/`/`assets/` subdirs. See [[packaging]].
- **Wiki entries**: `{id, title, body, links[], categories[]}`. Plain-old wiki.
- **Storylines**: `{id, narrative_arc, characters[], scenes[], branches[]}`. See mystery-detective-game's GameData type as one shape.
- **Screenplays**: `{scene_id, location, time, dialogue[], action[]}`.
- **Graphs**: nodes `{id, type, attrs}` + edges `{from, to, type, attrs}`.

## The MECE principle

Per the user's PLAN.md M3 framing: extract "everything there is OR everything needed for what." Mutually Exclusive, Collectively Exhaustive within the chosen schema. **Don't extract the same fact three times under different schemas; don't leave the user's input partially covered.**

MECE applies to coverage, not granularity — a fact and a rule that depends on the fact can coexist if they're in different formats. Inside a single format, no duplicates.

## Header + body — a universal layer above schema

Every entry, regardless of format, gets a two-tier structure:

- **Header**: one-line description + classification + cross-references. Pinned in any retrieval context; cheap to load.
- **Body**: full content. Loaded on demand when an extractor or runtime consumes the entry.

This is **not a schema choice** — it's a universal practice applied on top of whichever schema you design. The schema defines what fields the *body* has; the header is always present, always one-line + classification + refs. Enforced during [[knowledge-rewrite]]. Design the schema with this split assumed.

## When to iterate the schema

You will. Plan for it.

- After parsing: realize the corpus has a kind of content you didn't anticipate (e.g., "this regulation has both rules AND a glossary; I need both formats").
- During extraction: an extractor subagent surfaces a structure that doesn't fit (e.g., "this rule has multi-step prerequisites the schema doesn't represent").
- During app design: the runtime needs a field the schema doesn't carry (e.g., "the game runtime needs character motivations as first-class objects").

When iteration happens, **update PLAN.md's four-structures section + the schema-design notes**. Log the change. Re-emit affected entries via corrective events ([[event-log-and-reducer]]) rather than rewriting the canonical state in place.

## Locking too early — the to-skills-backend regression

Production's `to-skills-backend` collapsed the research-grade 4-type schema (factual/relational/procedural/meta) into one 5-part SKU shape (`metadata/context/trigger/core_logic/output`). Easier to implement; lost information richness. The collapse was an over-fitting move for the verification domain; for general knowledge engineering it leaves entries forcibly squeezed into a shape they don't fit. Don't repeat. See `references/to-skills-backend-sku-regression.md`.

John's stance, in three rules drawn from the regression:

- **Let the knowledge format drive the schema, not the app shape.** If the format is rules, the schema has rule-shaped fields; if it's facts, fact-shaped. Don't reverse-engineer schema from the runtime.
- **Templates may collapse types** if their domain only ever uses one. A doc-verification template can ship a rules-only schema. That's the template's choice, not core John's default.
- **Header + body progressive disclosure remains universal**, regardless of schema choice. See the universal layer below.

## Working with the user

Schema-design is **co-authored**. You sketch options, the user picks. Show them the menu + your read of what fits this project; ask them to choose or correct. Capture the chosen schema in PLAN.md's four-structures section before [[knowledge-extraction]] starts. Write any unresolved questions to PLAN.md's Open Decisions section.

## Cross-references

- [[plan-md-authoring]] — where the four-structures section first appears
- [[phase-design]] — phases the schema dictates
- [[knowledge-extraction]] — what reads against the schema
- [[knowledge-rewrite]] — header+body progressive disclosure enforcement
- [[packaging]] — final emission shape for skills format
- See `references/` for: four-structures cascade dive, A2O's 4-type taxonomy, to-skills-backend regression, KC's rule schema
