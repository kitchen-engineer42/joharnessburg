---
name: packaging
description: Emit each rule as a Claude Code skill at <project>/.claude/skills/rule-R<id>/ with SKILL.md + check_R<id>.py + references/ + assets/samples/. Use this skill in the per-rule authoring phase (Phase 3) of a doc-verification project. Overrides John core's general packaging with KC's per-rule shape.
metadata:
  triggers:
    - package the rules
    - emit rule skills
    - ship the rules
    - finalize 2skills
    - per-rule skill emission
---

# packaging (doc-verification override)

For doc-verification, each rule becomes one Claude Code skill at `<project>/.claude/skills/rule-R<id>/`. Drawn from KC_CLI's proven shape. Overrides John core's generic packaging.

## Per-rule directory structure

```
<project>/.claude/skills/rule-R<id>/
├── SKILL.md              # required: pushy description + body teaching when + how to apply this rule
├── check_R<id>.py        # required: deterministic check (or algorithmic + LLM hybrid; see below)
├── references/
│   ├── source.md         # quoted regulation text + citation
│   ├── decision-tree.md  # the rule's if-then logic, structured
│   └── glossary-refs.md  # cross-links to glossary terms
└── assets/
    └── samples/
        ├── pass-1.md     # sample documents that should pass this rule
        ├── fail-1.md     # sample documents that should fail this rule
        └── ...
```

Plus a separate glossary skill at `<project>/.claude/skills/glossary/SKILL.md` for shared terms.

## SKILL.md frontmatter per rule

```yaml
---
name: rule-R042
description: Verify quarterly disclosure timing (15-business-day deadline). Apply this skill whenever the user uploads a quarterly financial report, asks "is this filing on time?", or wants to check filings against §15.2. Apply for ANY quarterly-filing scenario, even when the user doesn't reference the rule explicitly. Severity: medium.
metadata:
  triggers:
    - quarterly disclosure
    - quarterly report timing
    - 15.2
    - is the report on time
    - quarterly filing deadline
---
```

Note: descriptions are **pushy** per skill-creator's anti-undertriggering advice. List the contexts in which the rule applies, not just what the rule says.

## SKILL.md body per rule

```markdown
# Rule R042: Quarterly disclosure timing

## What the rule says
<one-paragraph summary in plain language>

## Source
§15.2 of [Disclosure Reg]: "Quarterly reports must be disclosed within 15 business days after quarter-end."
(Full quote with citation in `references/source.md`.)

## Check logic

1. Extract `disclosure_date` and `quarter_end_date` from the document. Implementation in `check_R042.py`.
2. Compute business-day difference.
3. If > 15 → rule fails. Emit a violation event with citation.
4. If ≤ 15 → rule passes.

Edge cases: business-day definition depends on jurisdiction. See `references/decision-tree.md`.

## Glossary references

- [[glossary-quarterly-report]]
- [[glossary-disclosure-date]]
- [[glossary-business-day]]

## Confidence

This rule is mechanically checkable; confidence is binary (date arithmetic). Mark `confidence: 1.0` if both dates extracted cleanly; `confidence: 0.5` if extraction was ambiguous.
```

## check_R<id>.py — the deterministic check

A Python file with a single function `check(document)` that:

1. Extracts the relevant fields from the document (call into the workflow distilled from this rule in Phase 5, OR uses regex/parser if extraction is trivial).
2. Applies the falsifiability check.
3. Returns `{verdict, confidence, evidence, citation}`.

For rules where mechanical checking isn't possible (judgment-heavy rules), `check_R<id>.py` calls a workerLLM with a tight prompt and returns the verdict; confidence comes from the workerLLM's stated certainty.

## assets/samples/

Labeled examples that should pass or fail. Used in Phase 4 (testing) to measure rule accuracy. At minimum: 2 pass + 2 fail per rule. Real production templates may need 10+ each.

## What this skill does NOT do

- It doesn't extract rules from source. That's [[rule-extraction]].
- It doesn't test rule accuracy. That's [[rule-testing]] in Phase 4.
- It doesn't distill rules into cheap-LLM workflows. That's Phase 5 (out of M5 scope; templates may ship their own distill skill).

## Cross-references

- [[rule-extraction]] — produces the rules this skill packages
- [[rule-testing]] — verifies the packaged skills work on samples
- [[schema-design]] (template-overridden) — defines the rule fields this skill must emit into SKILL.md
- [[knowledge-rewrite]] — runs before this skill to ensure rules are clean + deduplicated + cross-linked
