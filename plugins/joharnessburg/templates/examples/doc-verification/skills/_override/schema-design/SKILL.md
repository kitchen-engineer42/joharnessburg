---
name: schema-design
description: Schema for doc-verification projects is FIXED — this template narrows John core's open methodology to a single shape. Use this skill whenever the user (or a phase) is about to design schema; tell them the schema is already locked, no further design conversation needed. The schema is rules + glossary; the rule fields are pre-specified below.
metadata:
  triggers:
    - design the schema
    - schema design
    - what format
    - knowledge schema
    - what fields
---

# schema-design (doc-verification override)

For doc-verification projects, the schema is locked. John core's `schema-design` is open-ended; this template narrows it. **Do not engage the user in a schema-design conversation for this project type** — the schema is already specified below. If the user wants to deviate, they should either pick a different template or fork this one.

## Format of knowledge

**Rules + glossary.** Every entry is either a rule or a glossary term. No facts, no stories, no wiki entries.

## Rule schema (per entry)

```
{
  "id": "R001"                       // sequential rule ID, R-prefixed
  "source_ref": "Reg 15.2"           // exact citation in the source document
  "description": "..."               // one-line summary of what the rule says
  "applicable_sections": [...]       // which doc types/chapters this rule applies to
  "severity": "high|medium|low"      // optional but recommended; affects runtime UX
  "trigger": "..."                   // when this rule applies (precondition on the doc)
  "judgment": "..."                  // the rule's verdict logic (pass/fail/needs-review)
  "decision_tree": "..."             // structured if-then logic for judgment; can be prose or YAML
  "falsifiability_statement": "..."  // MANDATORY — precise condition under which the rule fails
  "test_case_stub": "..."            // sketch of how to test this rule on a sample
  "glossary_refs": [...]             // terms used in this rule that are defined in the glossary
  "source_chunk_ids": [...]          // chunk IDs in the regulation source providing the evidence
  "related_rules": [...]             // rule IDs that depend on or interact with this one
}
```

**`falsifiability_statement` is mandatory.** Without it, the rule isn't machine-checkable, the runtime can't apply it, and the testing phase can't verify accuracy. If extraction can't determine the falsifiability, mark the rule as `incomplete` and surface it as an Open Decision.

## Glossary entry schema (per term)

```
{
  "term": "..."           // the term as it appears in rules
  "definition": "..."     // canonical definition
  "scope": [...]          // which regulations this definition applies in
  "used_in_rules": [...]  // rule IDs that reference this term
}
```

## Header + body progressive disclosure

Universal across all entries (rules + glossary):

- **Header**: id + source_ref + one-line description + severity + glossary_refs (for rules) or term + definition (for glossary).
- **Body**: full content — falsifiability_statement, decision_tree, test_case_stub, full elaboration.

## MECE

- Every rule in the source regulations should produce exactly one entry (mutually exclusive).
- Coverage check at end of extract phase: spot-check that randomly sampled chapters of the source contain at least one rule entry. If a section was missed, re-extract.

## What this skill does NOT do

- It doesn't propose alternative schemas. The schema is locked for this project type.
- It doesn't run extraction. That's `rule-extraction` (also template-provided).
- It doesn't package — that's the overridden `packaging` skill, which emits per-rule directories.

## Cross-references

- [[rule-extraction]] — uses this schema to extract rules from source
- [[packaging]] (template-overridden) — emits per-rule directories
- [[knowledge-extraction]] — John core; the template-specific `rule-extraction` skill wraps and constrains this
- [[plan-md-authoring]] — populates the four-structures section with this template's pre-filled schema
