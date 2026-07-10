# app-type-definition-cascade — how format constrains everything downstream

John works with four interlocking structures. They form a cascade: each constrains the next. Getting the order right means the project's shape is internally consistent.

## The four

1. **Knowledge format**: what *kinds* of knowledge exist in this project (facts? rules? stories? wiki? mixed?).
2. **Knowledge schema**: what *shape* an entry has — fields, types, relationships, header/body split.
3. **App mechanism**: how the produced app *works* for end-users — the main flow from input to output.
4. **Build pipeline**: how the app is *built* — phases that turn raw input into deliverable.

## The cascade

```
  Format ──► Schema ──► Runtime ──► Pipeline
   (1)        (2)        (3)         (4)
```

Each step is shaped by what came before:

- **Schema is shaped by Format.** If the format is "rules," the schema has trigger conditions and decision trees. If the format is "storylines," the schema has characters and scenes. The schema doesn't make sense without knowing what kind of knowledge it's holding.
- **Runtime is shaped by Schema.** If the schema has rules with decision trees, the runtime applies rules to user input and shows verdicts. If the schema has storylines, the runtime presents narrative beats. The runtime can only consume what the schema represents.
- **Pipeline is shaped by Runtime.** A verification runtime needs a pipeline that extracts rules. A game runtime needs a pipeline that produces playable cases. The pipeline reverse-engineers the steps to produce what the runtime needs.

## Why the order matters

If you design the runtime before the schema, the schema gets forced to match an arbitrary app shape — over-fitting. If you design the schema before the format, the schema gets too general or too specific without knowing what kind of knowledge it serves.

The user owns format. The John-equipped agent can sketch options. Lock format first, then derive the rest.

## Examples (cross-product to ground the cascade)

| Format | Schema (sketch) | Runtime (sketch) | Pipeline (sketch) |
|---|---|---|---|
| Rules | id, source_ref, trigger, decision_tree | upload doc → apply rules → show violations | extract rules → author skills → distill workflows |
| Storylines | char, scene, motive, branches | play case → interrogate → submit theory | gen case → seed clues → wire game → deploy |
| Slides | concept, visual_kind, components[] | arrow-key SPA, slide deck | extract concepts → research media → render slides → assemble |
| Wiki | id, title, body, links | browsable site | extract entries → cross-link → render → deploy |

Each row is internally consistent because the cascade was respected.

## What iteration looks like

The cascade is not a one-shot waterfall. You sketch all four at PLAN.md authoring time, then iterate as the corpus and conversations reveal new constraints:

- Discover during extraction that the format actually needs *two* sub-formats (e.g., rules + glossary). Update format → update schema → check runtime still fits → maybe add a glossary-lookup step to the pipeline.
- Discover during runtime design that the schema's missing a field the user wants surfaced. Backfill schema → re-emit affected entries via corrective events.

Iteration is fine. Locking too early is what's costly.

## Source

Plan-md-authoring covers the app-type definition at the surface; this note dives deeper into the cascade itself.
