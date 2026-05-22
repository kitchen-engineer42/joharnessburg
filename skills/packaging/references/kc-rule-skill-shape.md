# kc-rule-skill-shape — one real-world example of packaged rules

KC (the verification harness, sibling project to John) emits packaged rule skills as the deliverable of its skill-authoring phase. Each rule becomes one Claude Code skill. The shape is worth knowing as one concrete instance of packaging in action.

## Structure per rule

```
rule_skills/R<id>/
├── SKILL.md
├── check_<id>.py          # algorithmic check
├── references/
│   ├── source.md          # quoted regulation text + citation
│   ├── decision-tree.md   # if-then logic for judgment
│   └── glossary-refs.md   # cross-links to glossary entries
└── assets/
    └── samples/           # test cases (sample inputs that should pass/fail)
```

## SKILL.md content

```markdown
---
name: rule-R042
description: Verify quarterly disclosure timing. Use this skill whenever the user uploads a quarterly financial report, asks "is this report on time?", or wants to check filings against §15.2 of [Disclosure Reg]. Apply for any quarterly-filing scenario, even when the user doesn't reference the rule explicitly.
metadata:
  triggers:
    - quarterly disclosure
    - filing timing
    - 15.2
    - quarterly report on time
---

# Rule R042: Quarterly disclosure timing

When you encounter a quarterly financial report, verify that the disclosure
date is within 15 business days of the quarter-end date.

## Source

§15.2 of [Disclosure Reg]: "Quarterly reports must be disclosed within
15 business days after quarter-end."

(Full quote with citation in `references/source.md`.)

## Check logic

1. Extract `disclosure_date` and `quarter_end_date` from the report.
   The extraction is implemented in `check_R042.py`.
2. Compute business-day difference.
3. If > 15 business days → rule fails. Emit a violation event.
4. If ≤ 15 business days → rule passes.

Edge cases: what counts as a business day depends on jurisdiction. See
`references/decision-tree.md`.

## Glossary references

- [[glossary-quarterly-report]]
- [[glossary-disclosure-date]]
- [[glossary-business-day]]
```

## What's generalizable

- **One skill per atomic unit** of knowledge (one per rule, here). Granular enough that the runtime can load only what's needed for the current scenario.
- **Source-anchored**. The `references/source.md` is the audit trail. The skill is the actionable version of the source.
- **Mechanically testable where possible**. `check_<id>.py` automates the judgment.
- **Cross-linked to a glossary**. Shared vocabulary lives in glossary entries; rules reference it.

## What's KC-specific (don't blindly copy)

- The `check_<id>.py` script. KC has algorithmic checks because its domain is mechanical compliance. Other domains might have storyteller skills with no scripts, design skills with HTML templates as assets, etc.
- The numbered IDs. Use whatever ID scheme makes sense; KC's `R001`, `R002`... is just one choice.
- The decision-tree subdirectory. KC has these because rules often have complex if-then branches; other domains might not.

## Source

KC is at `/Users/mac/Desktop/kc_cli` on the dev machine. The packaged rule skills produced by KC live in each project's `rule_skills/` directory after the skill-authoring phase. The `skill-authoring` skill (in `kc_cli/template/skills/en/skill-authoring/`) documents the authoring process.
