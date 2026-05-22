---
name: rule-extraction
description: Extract atomic, falsifiable, testable rules from regulation documents — the 2skills extraction phase for doc-verification projects. Use this skill whenever the extract phase fires in a doc-verification project. Source-first principle (sweep regulations BEFORE looking at samples) is mandatory; without it, rules silently get dropped.
metadata:
  triggers:
    - extract rules
    - sweep regulations
    - rule extraction phase
    - find rules
    - extract from regulation
---

# rule-extraction (doc-verification template)

The extraction phase for verification projects. Sweep regulation source documents and produce atomic, falsifiable, testable rules in the schema defined by this template's `schema-design` override.

## The source-first principle (kc_cli's hard-won lesson)

**Extract from the source regulations FIRST. Only after a complete first-pass catalog is built do you open sample documents for validation.** Reverse the order and you silently drop rules the samples don't exercise.

Why: regulations contain rules whether or not your samples violate them. If you start with samples, you only find rules that have visible violations. Comprehensive coverage requires reading the regulations exhaustively.

Per spec §8.5 user reply and the kc_cli DEVLOG entry on E2E #12: in one project, sample-first extraction missed 30% of the rules. Don't repeat.

## Phase shape

For each regulation chunk (from the chunk phase), dispatch a subagent. Per chunk, the subagent:

1. **Chunk echo** (mathlab pattern, per [[knowledge-extraction]]): emit a `chunk_echo` event with a 2-3 sentence summary of what this chunk of regulation says.

2. **Atomic rule sweep**: identify every distinct rule the chunk contains. A rule is *atomic* if it can be applied to a document independently of other rules. Compound rules (e.g., "X must happen unless Y, in which case Z") get split into multiple atomic rules with `related_rules` cross-references.

3. **Falsifiability**: for each rule, write the precise condition under which the rule fails. If you can't articulate falsifiability for a candidate rule, the rule isn't actually mechanically checkable — mark it `incomplete` and surface in Open Decisions for human review.

4. **Test case stub**: sketch how to test this rule on a sample document. "Read the disclosure date and quarter-end date; compute business-day difference; check ≤15."

5. **Glossary identification**: every technical term the rule uses goes in the glossary. If you encounter a term, check if it's already in `.john/knowledge/glossary/`; if not, add it.

6. **Emit events** to `<project>/.john/events/extract/<chunk-id>/`:
   - One `rule_extracted` event per rule, payload matching the rule schema.
   - One or more `glossary_term` events for new terms.
   - One `chunk_echo` event (see step 1).
   - Optional `incomplete_rule` events for candidates lacking falsifiability.

## Briefing per subagent

Per [[subagent-dispatch]], brief each subagent with:

- The project intent (from PLAN.md top).
- The specific chunk to process (path + ID).
- The rule schema (from this template's `schema-design` override — paste the schema fields).
- The source-first reminder ("don't peek at samples while extracting; that's Phase 4's job").
- The output expectations (events to `<project>/.john/events/extract/<chunk-id>/`, JSON shape per the schema).
- The chunk_echo and incomplete_rule patterns.

## MECE coverage at end of phase

After fan-out completes and the reducer runs:

1. **Mutually Exclusive**: no two rules describe the same precondition + verdict. The dedup pass in [[knowledge-rewrite]] catches this; spot-check.
2. **Collectively Exhaustive**: every regulation chapter that should have rules does. Spot-check 5 random chapters; if any has zero rules and the chapter clearly contains prescriptive language, re-extract that chapter.

Incomplete rules surface as a list in PLAN.md's Open Decisions. The user resolves each: extend the rule schema to handle the case, drop the rule as unenforceable, or accept ambiguity with a low confidence floor.

## What this skill does NOT do

- It doesn't validate rules against samples. That's [[rule-testing]] in Phase 4.
- It doesn't package rules as skills. That's the overridden [[packaging]] in Phase 3.
- It doesn't iterate the schema. The schema is locked per this template; if it doesn't fit, the project may need a different template.

## Cross-references

- [[knowledge-extraction]] — John core extraction; this skill is the template-specific specialization for rules
- [[schema-design]] (template-overridden) — the rule schema this extraction targets
- [[subagent-dispatch]] — fan-out per chunk
- [[event-log-and-reducer]] — coordination
- [[rule-testing]] — verifies the extracted rules in Phase 4
- [[packaging]] (template-overridden) — emits the per-rule skill directories
