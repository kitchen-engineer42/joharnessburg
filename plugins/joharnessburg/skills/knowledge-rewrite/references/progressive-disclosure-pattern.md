# progressive-disclosure-pattern — header vs body

Every entry gets a header file and a body file (or equivalent split). This is the same pattern Claude Code skills use (frontmatter+description vs body) and the same pattern documents use (TOC vs chapters). It scales reading cost.

## Why split

If you load 200 entries into a context all at once, each in their full glory, you've burned your context budget on material the agent doesn't yet know it needs. If you load 200 *one-line headers*, you've spent maybe 4K tokens, and the agent can decide which entries to load fully based on what the current task asks.

Progressive disclosure isn't an optimization — it's the only way large knowledge bases work at all.

## Header content

A header is ~1-3 lines. Includes:

1. **One-line description**. What this entry says, in 20 words or less. Specific enough to disambiguate from siblings.
2. **Classification**. From the schema. E.g., `factual` / `rule` / `glossary` / `skill`.
3. **Cross-refs**. The most important `related_to` / `depends_on` / `caused_by` / etc., per the schema. Three or four IDs, not all of them.
4. **Source pointer**. Chunk ID or source ref. Enough to find the original.

Optional:

- **Confidence** (if the schema has it).
- **Severity / importance** (if the schema has it).

What does NOT go in the header:

- Full quote / claim text — that's body.
- All cross-refs — pick the load-bearing ones.
- Examples — body.
- Edge cases — body.

## Body content

The body is the full entry: claim, citations, elaboration, examples, edge cases, glossary expansions. As long as it needs to be. Targeted at a reader who has read the header and committed to this entry — no need to re-explain context the header already established.

## File layout per entry

```
<project>/.john/knowledge/<entry-id>/
├── header.md
└── body.md
```

The reducer's canonical state references both. Cross-link queries hit headers first; full content loads body on demand.

## During packaging

When [[packaging]] emits to `<project>/.claude/skills/<skill-name>/`, the SKILL.md frontmatter is essentially the header content (name + description = identifier + one-liner; cross-refs go in body as `[[skill-name]]` links). The SKILL.md body is essentially `body.md`. Same split, different shape.

## Source

The pattern is canonical across our prior projects:

- A predecessor pipeline: `header.md` + `content.md` per entry.
- KC's rule format: rule metadata file + rule body file.
- Claude Code skills: SKILL.md frontmatter + body.

All instances of one underlying idea.
