---
name: schema-design
description: Schema for doc-verification projects is PRE-SPECIFIED — rules + glossary, with the field shapes below. Use this skill whenever the user (or a phase) is about to design schema; tell them the schema is already locked, no further design conversation needed. The only project-level decision is the severity controlled vocabulary, which gets declared in PLAN.md's Project intent block. If anything else doesn't fit, surface as Open Decision; do NOT invent a third format.
metadata:
  triggers:
    - design the schema
    - schema design
    - what format
    - knowledge schema
    - what fields
    - app-type definition
    - knowledge format
    - rule schema
    - glossary schema
---

# schema-design (doc-verification override)

For doc-verification projects the schema is locked. John core's `schema-design` is co-authored, open-ended, taste-driven; this template narrows it. **Do not engage the user in a schema-design conversation for this project type.** The schema is specified below. If the user wants to deviate, they should either pick a different template or fork this one and propose the change.

The one decision left to the project is the **severity controlled vocabulary** — see "Severity vocabulary" below.

## What schema-design is NOT (in this template)

- It's not picking from a menu of formats. The format is **rules + glossary**, period.
- It's not designing schema fields from the corpus up. The fields below are pre-fixed.
- It's not a taste call. Layer-3 Claude executes; doesn't deliberate.

## Knowledge format

**Rules + glossary.** Every entry is either a rule or a glossary term. No facts, no stories, no wiki entries, no graphs, no screenplays. This is the KC-derived discipline that produced reliable verifiers in production.

If you encounter source content that doesn't fit either format (e.g., a list of regulator entity names that doesn't act like a glossary term), surface as Open Decision per [[plan-md-evolution]] — usually the right move is to extend the glossary entry schema with optional fields, or treat the content as project metadata in PLAN.md, NOT to invent a third format.

## Rule schema (per entry — locked shape)

```yaml
id: R001                              # sequential, R-prefixed; assigned at extraction time
source_ref: "Reg 15.2"                # exact citation in the source regulation document
chapter_id: "Chapter 3"               # OPTIONAL — chapter-level locator (Chinese: 第三章)
article_id: "Article 20"              # OPTIONAL — article-level locator (Chinese: 第二十条)
description: "..."                    # one-line plain-language summary of what the rule says
requirement_type:                     # REQUIRED — one of:
  # imperative      (must do X — Chinese 应当)
  # prohibitive     (must not do Y — Chinese 不得)
  # conditional     (if Z then must W)
  # quantitative    (threshold check, e.g., ratio ≤ 35%)
  # definitional    (defines what counts as something — often paired with a glossary term)
applicable_scope: [...]               # which doc types this rule applies to (controlled vocab — project declares in PLAN.md)
applicable_entities: [...]            # who must comply (e.g., manager, custodian, seller, all)
severity: "..."                       # REQUIRED — value from the project-declared severity vocab
trigger: "..."                        # precondition on the doc-under-test (when this rule fires)
judgment: "..."                       # the rule's verdict logic (pass / fail / needs-review)
decision_tree: "..."                  # if-then logic for judgment; prose or YAML
falsifiability_statement: "..."       # MANDATORY — the precise condition under which the rule FAILS on a doc
test_case_stub: "..."                 # sketch of how to test this rule on a labeled sample
glossary_refs: [...]                  # term IDs used in this rule that are defined in the glossary
source_chunk_ids: [...]               # chunk IDs in the regulation source providing the evidence (for provenance)
related_rules: [...]                  # rule IDs that depend on, contradict, or interact with this one
cross_doc: false                      # OPTIONAL — true if the verdict needs facts from multiple docs (set in Phase 5)
```

**`falsifiability_statement` is mandatory.** Without it, the rule isn't machine-checkable, the runtime can't apply it, and the Phase 4 testing skill has nothing to measure against. If extraction can't determine the falsifiability, mark the rule as `incomplete` (via `incomplete_rule` event) and surface to PLAN.md's Open Decisions for the user to resolve — don't fabricate a falsifiability statement.

**`requirement_type` distinguishes verification strategy.** Imperative + prohibitive rules need entity extraction + presence/absence checks. Conditional rules need branch-aware checks. Quantitative rules need numeric extraction + comparison. Definitional rules typically pair with a glossary term and may be enforced by the glossary skill rather than a per-rule check. `check_R<id>.py` implementations vary by type — see [[packaging]].

**`source_ref` + `chapter_id` + `article_id` together give the full citation trail.** The runtime surfaces all three in violation reports so an auditor can navigate back to the source. `chapter_id` and `article_id` are optional only because not every regulation is structured this way; `source_ref` is mandatory.

## Glossary entry schema (per term — locked shape)

```yaml
term: "..."                           # the term as it appears in rules (canonical form)
definition: "..."                     # canonical definition
scope: [...]                          # which regulations / source documents this definition applies in
aliases: [...]                        # synonyms across regulations (Chinese-reg corpora often have these)
used_in_rules: [...]                  # rule IDs that reference this term
notes: "..."                          # OPTIONAL — disambiguation, jurisdictional variation, etc.
```

Glossary terms are shared across rules within their `scope`. If two regulations define the same term differently, **create two glossary entries with different `scope` lists** — don't merge. The rule's `source_ref` determines which definition applies.

## Severity vocabulary — the ONE project-level decision

Severity is a controlled vocabulary, but the **values are project-defined**, not template-fixed.

In Phase 0 the user (or layer-2 Claude on the user's behalf, with sign-off) picks a vocab and declares it in PLAN.md's "Project intent" block. Examples:

- Financial regulation: `critical / high / medium / low / advisory` (5 tiers)
- Code-style verification: `blocker / warning / info` (3 tiers, KC's default)
- Contract review: `material / non-material` (binary)
- Custom domain: whatever the user picks

Once declared, every extracted rule's `severity` field MUST take a value from that list. Layer-3 Claude validates during extraction (Phase 2) and surfaces violations as `incomplete_rule` events.

The dashboard skill ([[dashboard-reporting]]) reads the declared vocab to color-code violations.

## Header + body progressive disclosure

Universal across all entries (rules + glossary terms), in the same way John core ships it:

- **Header**: id + source_ref + one-line description + severity (rules) | term + definition (glossary) + glossary_refs.
- **Body**: the full content — `falsifiability_statement`, `decision_tree`, `test_case_stub`, full elaboration; or for glossary, the full definition + scope + aliases.

The packaging skill ([[packaging]]) emits header → SKILL.md frontmatter description; body → SKILL.md body. Don't invert this layering.

## MECE

- **Mutually Exclusive**: no two rules describe the same precondition + verdict. If extraction surfaces apparent duplicates, dedup in [[knowledge-rewrite]] before they reach packaging. Note that rules with the SAME falsifiability_statement but DIFFERENT severities are still duplicates — collapse and pick the higher severity.
- **Collectively Exhaustive**: every chapter / section / article of the rule corpus that contains prescriptive language produces at least one rule. The MECE coverage audit at the end of Phase 2 spot-checks this; if a chapter has zero rules and clearly contains "must" / "must not" / "shall" language, re-extract that chapter.

MECE applies WITHIN the rule format. Glossary terms aren't subject to MECE the same way — synonyms / aliases are normal and live in the `aliases` field.

## What this skill does NOT do

- It doesn't propose alternative schemas. The schema is locked for this template.
- It doesn't run extraction. That's [[rule-extraction]] in Phase 2.
- It doesn't package. That's the overridden [[packaging]] in Phase 3 (per-rule emission) and Phase 8 (release-bundle emission).
- It doesn't iterate the schema. If extraction surfaces something the schema can't represent, surface as Open Decision in PLAN.md; the user decides whether to fork the template.

## Cross-references

- [[rule-extraction]] — uses this schema to extract rules from source
- [[packaging]] (overridden) — emits per-rule skill directories using these fields
- [[chunking]] (overridden) — preserves provenance for `source_chunk_ids`
- [[knowledge-extraction]] — John core; [[rule-extraction]] specializes it
- [[knowledge-rewrite]] — dedup + cross-link rules before packaging
- [[plan-md-authoring]] — populates the app-type definition section with this template's pre-filled schema
- [[app-design-thinking]] (overridden) — the runtime that consumes these schemas
