---
name: rule-extraction
description: Source-first sweep of regulation documents to extract atomic, falsifiable, testable rules + glossary terms — the Phase 2 extraction step for doc-verification projects. Use this skill whenever the extract phase fires in a doc-verification project, when the user says "extract the rules" / "sweep the regulations" / "find rules" / "extract from regulation". The source-first principle (sweep regulations BEFORE looking at samples) is MANDATORY — kc_cli learned this the hard way.
metadata:
  triggers:
    - extract rules
    - sweep regulations
    - rule extraction
    - rule extraction phase
    - find rules
    - extract from regulation
    - phase 2 extraction
    - extract glossary
    - source-first sweep
---

# rule-extraction

The Phase 2 extraction step for doc-verification projects. Sweep regulation source documents and produce atomic, falsifiable, testable rules + glossary terms in the schema defined by the overridden [[schema-design]].

This skill specializes John core's [[knowledge-extraction]] for the rule format. Triggers are tighter (verification-specific phrasings) so it wins over generic extraction in this template.

## The source-first principle (mandatory)

**Extract from the source regulations FIRST. Only after a complete first-pass catalog is built do you open sample documents for validation (Phase 4).** Reverse the order and you silently drop rules the samples don't exercise.

Why: regulations contain rules whether or not your samples violate them. If you start with samples, you only find rules that have visible violations. Comprehensive coverage requires reading the regulations exhaustively.

This is kc_cli's hard-won lesson — in one project, sample-first extraction missed 30% of the rules. Don't repeat. If you find yourself tempted to "just glance at one sample to see what rules look like in context," resist; you've already started biasing toward sample-visible rules.

## Phase shape

For each regulation chunk (from the overridden [[chunking]] in Phase 2's chunk step), dispatch a subagent. Per chunk, the subagent:

1. **Chunk echo**: emit a `chunk_echo` event with a 2-3 sentence summary of what this chunk of regulation says. Confirms the subagent read the chunk before extracting (catches subagents that hallucinate rules without reading).

2. **Atomic rule sweep**: identify every distinct rule the chunk contains.
   - A rule is **atomic** if it can be applied to a document independently of other rules.
   - **Compound rules** (e.g., "X must happen unless Y, in which case Z") get split into multiple atomic rules with `related_rules` cross-references.
   - **Compound requirements** (e.g., "A and B and C are required") may be one rule (compound check) or three rules (independent checks) — pick by whether they're independently falsifiable. Three independent checks is usually right.
   - **Definitions disguised as rules** (e.g., "An X is something that does Y") become glossary terms, not rules. Unless they have a falsifiability condition on a doc-under-test.

3. **Severity assignment**: from the project-declared severity vocabulary (in PLAN.md's Project intent). Map the rule's language:
   - 必须 / 应当 / shall / must → typically high or critical
   - 不得 / shall not / must not → typically high or critical
   - 应 / should / ought to → typically medium
   - 鼓励 / encourage / recommended → typically low or advisory

   The exact mapping is project-specific; if uncertain, mark severity as `unknown` and surface as Open Decision.

4. **Falsifiability check**: for each rule, write the precise condition under which the rule FAILS on a doc-under-test. Examples:
   - "Rule fails if the disclosure_date is more than 15 business days after the quarter_end_date."
   - "Rule fails if the document contains no Risk Disclosure section."
   - "Rule fails if non_standard_debt_ratio > 0.35."

   **If you can't articulate falsifiability in one sentence, the rule isn't actually mechanically checkable.** Mark `incomplete` and emit an `incomplete_rule` event. The user resolves in PLAN.md's Open Decisions.

5. **Test case stub**: sketch how to test this rule on a sample document. Format: "Read X from the doc; compute Y; check Z." One or two sentences. This becomes the seed for `assets/samples/` in Phase 3.

6. **Glossary identification**: every technical term the rule uses goes in the glossary. Check `.john/knowledge/glossary/` for an existing entry; if missing, emit a `glossary_term` event. If a term exists with a different scope, emit a SECOND glossary entry (different scope ↔ different definition, per overridden [[schema-design]]).

7. **Emit events** to `<project>/.john/events/extract/<chunk-id>/`:
   - One `rule_extracted` event per rule, payload matching the rule schema (overridden [[schema-design]]).
   - One or more `glossary_term` events for new terms.
   - One `chunk_echo` event (step 1).
   - Optional `incomplete_rule` events for candidates lacking falsifiability.

## Briefing per subagent

Per [[subagent-dispatch]], brief each subagent with:

- **Project intent** from PLAN.md top (one paragraph).
- **The specific chunk** to process (path + chunk_id + chapter_id + article_id).
- **The rule schema** (paste from overridden [[schema-design]] — do not link, paste).
- **The glossary schema** (paste).
- **The project-declared severity vocabulary** (paste from PLAN.md Project intent).
- **The source-first reminder**: "Don't peek at samples while extracting; that's Phase 4's job."
- **Output expectations**: events to `<project>/.john/events/extract/<chunk-id>/`, JSON shape per the schema.
- **Chunk_echo + incomplete_rule patterns** explained verbatim above.

See `agents/rule-extractor.md` for the canonical briefing template.

## MECE coverage at end of phase

After fan-out completes and [[event-log-and-reducer]] runs:

1. **Mutually Exclusive**: no two rules describe the same precondition + verdict. The dedup pass in [[knowledge-rewrite]] catches most; spot-check 10 random pairs. Rules with the same `falsifiability_statement` but different `severity` are duplicates — collapse to higher severity.

2. **Collectively Exhaustive**: every regulation chapter / article that should have rules does.
   - Spot-check 5 random chapters; if any has zero rules AND the chapter clearly contains prescriptive language ("应当" / "must" / "shall" / "不得" / "must not"), re-extract that chapter.
   - Specifically check: chapters with definitions (definitional rules + glossary terms), chapters with quantitative thresholds (quantitative rules), chapters with prohibition lists (prohibitive rules — kc_cli noticed these get under-extracted because they're often itemized lists buried in prose).

3. **Open Decisions surfacing**: incomplete rules surface as a list in PLAN.md's Open Decisions. The user resolves each:
   - Extend the rule schema to handle the case (uncommon — the schema is locked; usually means picking a different template).
   - Drop the rule as unenforceable (common — some prescriptive language is genuinely ambiguous).
   - Accept ambiguity with a "needs-review" verdict and low confidence floor (medium — surface in dashboard for manual review).

## What this skill does NOT do

- It doesn't validate rules against samples. That's [[rule-testing]] in Phase 4.
- It doesn't package rules as skills. That's the overridden [[packaging]] in Phase 3.
- It doesn't iterate the schema. The schema is locked per [[schema-design]] override.
- It doesn't read sample docs. Source-first.
- It doesn't write `check_R<id>.py`. That happens in Phase 3 packaging, based on the rule's `falsifiability_statement` + `requirement_type`.

## Cross-references

- [[knowledge-extraction]] — John core extraction; this skill specializes it for rules
- [[schema-design]] (overridden) — the rule + glossary schema this extraction targets
- [[chunking]] (overridden) — produces the chunks this skill sweeps; passes provenance through
- [[subagent-dispatch]] — fan-out per chunk
- [[event-log-and-reducer]] — coordination of per-chunk extraction events
- [[knowledge-rewrite]] — dedup + cross-link after extraction
- [[rule-testing]] — verifies extracted rules in Phase 4
- [[packaging]] (overridden) — emits per-rule skill directories in Phase 3
- See `agents/rule-extractor.md` for the canonical subagent briefing template
