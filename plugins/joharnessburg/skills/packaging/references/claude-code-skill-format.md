# claude-code-skill-format — what to emit

Claude Code expects each skill at one directory containing at minimum a `SKILL.md` file. The format is universal — John core skills, John template skills, and produced project skills all use the same shape.

## Directory layout

```
<skill-name>/
├── SKILL.md          # required
├── references/       # optional — deeper material, loaded on demand
│   ├── <topic-1>.md
│   └── <topic-2>.md
├── scripts/          # optional — executable code, Python/shell
│   └── <name>.py
└── assets/           # optional — templates, icons, fonts, fixtures
    └── <file>
```

## SKILL.md structure

```markdown
---
name: <skill-name>
description: <pushy description; see description-pushiness.md>
metadata:
  triggers:
    - <trigger phrase 1>
    - <trigger phrase 2>
---

# <skill-name>

<body — markdown>
```

## Frontmatter rules

- `name`: lowercase, kebab-case, ASCII. ≤ 64 chars. Must match the directory name. Globally distinctive within whatever scope loads the skill (plugin / user / project).
- `description`: plain text, no markup. The primary triggering mechanism. Length: enough to convey "what" + "when to use." 2-4 sentences typical.
- `metadata.triggers[]`: optional. Keyword phrases that auto-load the SKILL.md body when matched in user messages. Tight, specific, domain-relevant.

## Body conventions

- **Imperative voice** ("when you see X, do Y") not descriptive ("the skill describes X").
- **Explain *why***, not just *what*. A future agent reading this should understand the rationale, not just the rule.
- **≤ 500 lines** ideal. If longer, push detail into `references/`.
- **Cross-link via `[[other-skill-name]]`** to sibling skills.

## Reference subdirectory

For material that's relevant but bulky:

- Schema definitions, formula tables, decision matrices.
- Examples — when one carefully-chosen example genuinely teaches the pattern. (Be sparing; per spec, examples can overfit.)
- External reading lists.
- Historical context that helps but isn't load-bearing.

The SKILL.md body references files in `references/` by relative path: *"See `references/<topic>.md` for the detailed decision tree."*

## Scripts subdirectory

For executable code the skill calls:

- Each script is its own file with shebang + docstring.
- The SKILL.md body invokes via Bash: *"Run `${CLAUDE_PLUGIN_ROOT}/skills/<skill-name>/scripts/<name>.py <args>`."*
- Scripts emit JSON to stdout for parsing.

Most packaged skills don't need scripts — they're informational, not action-taking. Templates may add scripts for domain-specific operations.

## Assets subdirectory

For files the skill body needs at runtime but doesn't read as markdown:

- HTML templates, CSS, fonts.
- Reference images, icons.
- Fixture data.

The skill body references assets via relative path. The runtime uses them.

## Source

The format is documented in Claude Code's plugin docs and exemplified by every shipped skill in this plugin and by Anthropic's official skill-creator.
