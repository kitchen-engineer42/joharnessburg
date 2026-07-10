# four-type-taxonomy — the research-grade 4-type taxonomy

A research-stage predecessor pipeline modeled knowledge as four distinct types. This was a stronger design than the later single-SKU collapse (see `sku-regression-case-study.md`).

## The four types

1. **Factual** — atomic statements with sources. *"The Earth's atmosphere is 78% nitrogen."* Header: classification + one-liner + source ref. Body: full elaboration, citations, related facts. Used when the project's value is providing accurate information.

2. **Relational** — typed relationships between entities + a label tree + glossary. `is-a`, `has-a`, `part-of`, `causes`, `caused-by`, `requires`, `enables`, `contradicts`, `related-to`, `depends-on`, `regulates`, `implements`, `example-of`. Used when the project's value is showing how entities connect — knowledge graphs, ontology pages, lookup tables of cross-references.

3. **Procedural** — provider-discoverable SKILL.md packages. Reusable how-to procedures. Used when the project's value is *teaching the runtime* or a downstream agent to do something repeatedly. Often becomes the deliverable for distillation projects.

4. **Meta** — cross-cutting insights, glossary entries, "eureka" observations. Header: classification (`mapping`, `eureka`, `glossary`, ...) + summary. Body: the insight + which other entries it bears on. Used to capture the connective tissue that isn't an entry per se but matters for navigation and reasoning.

## Why four (and not three or five)

The four-type taxonomy maps cleanly to the cognitive operations a knowledge base supports:

- **Factual** answers "what is true here?"
- **Relational** answers "how do these things connect?"
- **Procedural** answers "how do I do something?"
- **Meta** answers "what's the shape of this knowledge?"

These are orthogonal — a fact, a relation, a procedure, and a meta-note are not redundant. Adding more (say, a separate "rule" type) usually fragments the taxonomy without adding signal; adding fewer (collapsing factual + relational) loses signal about how entries connect.

## When this taxonomy fits

- Encyclopedic projects with mixed content.
- Knowledge bases that need both factual answers AND procedural how-tos.
- Anything that benefits from cross-linking + a glossary.

## When it doesn't fit

- Purely narrative projects (stories, games, screenplays) — better served by domain-specific schemas (character + scene + arc).
- Single-purpose projects (e.g., a slide deck) — overkill; simpler "concept + visual" schema works.
- Streaming/time-series data — needs a temporal schema this taxonomy doesn't address.

## Practical guidance

If the project is encyclopedic or knowledge-base-shaped, this taxonomy is a **strong starting point** — richer than production's single-SKU collapse, with clear cognitive boundaries. But it's a starting point that needs validation against your actual corpus, per [[schema-design]]'s corpus-survey step. Don't default to it without that check.

If the project is something else, **let knowledge-format drive the schema** rather than forcing the four-type model. Storylines, screenplays, custom domain schemas — they don't fit this taxonomy, and shouldn't.

Practical wiring when this taxonomy fits: each type gets its own subdir under `<project>/.john/knowledge/{factual,relational,procedural,meta}/`. The reducer at end-of-extract emits canonical state per type.

## Source

The predecessor defined `SKUType` (an enum: FACTUAL, RELATIONAL, PROCEDURAL, META) plus a `LabelTree`, `RelationType`, etc., consumed by its extractor stage.
