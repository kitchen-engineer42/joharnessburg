# app-type-definition-cascade — how app-first contracts constrain extraction

John works with interlocking structures. They form a cascade: each constrains the next. Getting the order right means the project's shape is internally consistent.

## The default cascade

Vanilla John now uses an app-first cascade:

1. **User intent**: who the app is for, what it should help them do, and what tone/language it should use.
2. **App mechanism**: how the produced app works for end-users — the main flow from input to output.
3. **Display contract**: public pages, navigation, labels, modules, and forbidden visible terms.
4. **Extraction targets**: what each UI slot needs from the corpus.
5. **Knowledge format/schema**: the internal representation that can fill those targets.
6. **Build pipeline**: phases that turn raw input into the deliverable.

## The app-first shape

```
  Intent ──► Runtime ──► Display ──► Extraction ──► Schema ──► Pipeline
   (1)        (2)         (3)          (4)           (5)        (6)
```

Each step is shaped by what came before:

- **Runtime is shaped by Intent.** A general-reader Chinese book site is likely a guided reading app; a compliance corpus may be a verifier.
- **Display is shaped by Runtime.** A guided reading app needs public pages and labels such as "导读" and "核心概念"; a verifier needs inputs, verdicts, and explanations.
- **Extraction is shaped by Display.** If a page has a "核心概念" slot, the extraction plan needs concept names, plain explanations, related sections, and source evidence.
- **Schema is shaped by Extraction.** Internal fields exist to fill public UI slots, not because a generic schema menu looked neat.
- **Pipeline is shaped by Schema and Runtime.** It should produce what the app needs and nothing that leaks internals into the UI.

## Why the order matters

If you design the schema before the app contract, the UI inherits internal terms: `chapter_id`, long skill names, raw JSON, schema keys. If you design the app before reading any corpus sample, the extraction targets may be unsupported. The cheap path is survey first, app contract second, schema third.

The user owns product preference when it is genuinely ambiguous. Claude owns inferred defaults. Ask at most one product-question batch, then persist fixed JSON contracts.

## Examples (cross-product to ground the cascade)

| Format | Schema (sketch) | Runtime (sketch) | Pipeline (sketch) |
|---|---|---|---|
| Rules | id, source_ref, trigger, decision_tree | upload doc → apply rules → show violations | extract rules → author skills → distill workflows |
| Storylines | char, scene, motive, branches | play case → interrogate → submit theory | gen case → seed clues → wire game → deploy |
| Slides | concept, visual_kind, components[] | arrow-key SPA, slide deck | extract concepts → research media → render slides → assemble |
| Wiki | id, title, body, links | browsable site | extract entries → cross-link → render → deploy |

Each row is internally consistent because the cascade was respected.

These examples show internal consistency, not the default order. For vanilla John, derive the schema from the app/display/extraction contract unless an active template deliberately uses a domain-specific schema-first method.

## What iteration looks like

The cascade is not a one-shot waterfall. You sketch all four at PLAN.md authoring time, then iterate as the corpus and conversations reveal new constraints:

- Discover during extraction that a UI slot needs a new field. Update extraction targets → update schema → re-emit affected entries via corrective events.
- Discover during rendering that public labels leak internals. Update display contract → update rendering → rerun UI leak guardrails.

Iteration is fine. Locking too early is what's costly.

## Source

Plan-md-authoring covers the app-type definition at the surface; this note dives deeper into the cascade itself.
