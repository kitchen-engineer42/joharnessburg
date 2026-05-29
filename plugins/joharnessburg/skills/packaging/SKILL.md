---
name: packaging
description: Emit the cleaned, cross-linked, deduplicated knowledge from the rewrite phase as Claude Code skills at `<project>/.claude/skills/`. Use this skill whenever the 2skills half wraps, when the user says "package the skills" / "ship the knowledge" / "finalize 2skills" / "we're ready for 2app," or when [[ralph-loop]] signals packaging is next. Make sure to invoke this skill before the 2app phases run — 2app reads the produced skills as its starting context. This is the deliverable boundary between knowledge engineering and app building; getting it wrong means the 2app half operates without a real knowledge source.
metadata:
  triggers:
    - package the skills
    - ship the knowledge
    - emit skills
    - publish to .claude/skills
    - finalize 2skills
    - packaging phase
    - ready for 2app
---

# packaging

The 2skills half ends here. Packaging turns John's working knowledge state (in `<project>/.john/knowledge/`) into the deliverable that the 2app half consumes (in `<project>/.claude/skills/`). After this phase, the produced skills are project-scoped Claude Code skills — auto-discovered by any Claude Code session opened in this project, including the one that will build the app.

## Where the work happens

- **Inputs**: `<project>/.john/knowledge/<entry-id>/{header.md, body.md}` (from [[knowledge-rewrite]])
- **Outputs**: `<project>/.claude/skills/<skill-name>/SKILL.md` (+ optional `references/`, `scripts/`, `assets/`)

`<project>/.claude/skills/` is Claude Code's project-scoped skill auto-discovery path. Skills emitted here load into any Claude Code session in this project, including future-Claude that builds the 2app runtime. This is the handoff.

## What "skill" means here

A skill in Claude Code is one directory with at minimum a `SKILL.md`:

```
<project>/.claude/skills/<skill-name>/
├── SKILL.md          # required: YAML frontmatter + markdown body
├── references/       # optional: deeper material loaded on demand
├── scripts/          # optional: executable code
└── assets/           # optional: templates, icons, fonts, etc.
```

The frontmatter has `name` and `description`. Optionally `metadata.triggers[]` for keyword-based auto-load. Body is markdown — what the agent should do/know.

This is the same skill format John itself ships. Your packaging output is structurally identical to a John meta-skill or phase skill — the difference is who wrote it (humans for John core; layer-2 Claude during a 2skills run for produced knowledge).

## Mapping knowledge entries → skills

The transformation per entry depends on the entry's format-of-knowledge:

- **Procedural** entries (skill-shaped knowledge) → emit as SKILL.md directly. `header.md` content becomes the description; `body.md` content becomes the body.
- **Factual** entries → can be packaged as a single "facts skill" with all facts in the body, OR as one skill per fact (rare; only for hugely important facts). Usually facts go into a single browsable skill with cross-links.
- **Rules** → one skill per rule (KC's pattern). Each rule's SKILL.md teaches the runtime when to apply the rule and what action to take.
- **Storylines / scenes / characters** → one skill per character or scene; cross-links between them.
- **Glossary** → one skill that contains the whole glossary, OR one skill per term (rare). Usually one.

**Pattern:** chunky entries (rules, characters, scenes) become per-entry skills; granular entries (glossary terms, individual facts) often bundle into one skill per category. KC's "one skill per rule" works because rules are medium-grain and independent; other schemas may shape the mapping differently. The user's [[plan-md-authoring]] phase 1 sketch usually anticipates which way to go.

## Frontmatter conventions

Per Claude Code's standard + skill-creator's writing guidance:

- **`name`**: kebab-case, lowercase, max 64 chars. Globally distinctive within the project.
- **`description`**: pushy per skill-creator. Don't write "Does X." Write *"Use this skill when the user mentions X / wants to do Y / asks about Z. Make sure to consult this skill whenever the runtime is about to apply <domain-specific operation>."* Combat the LLM tendency to undertrigger.
- **`metadata.triggers[]`**: tight keyword list of phrases that should auto-load the body. 5-10 entries. Specific to the domain.

The header of each entry maps to the description; the rest of the entry maps to body + optional references/.

## The packaging script — discovery and invocation

Two paths, depending on whether a template is active:

**Template-defined packaging** (preferred when applicable). Active templates may ship `scripts/package_<domain>.py` inside the merged plugin (at `$CLAUDE_PLUGIN_ROOT/scripts/`). To check whether you're running under a template, inspect `$CLAUDE_PLUGIN_ROOT` — if its parent is `~/.claude/plugins/joharnessburg-applied/`, you're in a merged-template session and its basename is the template name. List `$CLAUDE_PLUGIN_ROOT/scripts/` for any `package_*.py`; if present, invoke it via Bash with the project root as an argument. The script handles the schema-specific mapping. Output lands in `<project>/.claude/skills/`.

**Inline packaging** (default when no template script is provided). Iterate over `<project>/.john/knowledge/<entry-id>/`, emit each entry as a skill following the conventions in `references/claude-code-skill-format.md`. Map per the patterns above (chunky vs granular). Straightforward but slower because each entry's emission is a Claude-driven decision rather than a deterministic script.

John core ships packaging as **skill-only** — there's no core packaging script. Template-specific packaging scripts are a template concern; expect inline packaging in most projects unless the active template provides its own.

## Asset lifecycle for template-provided media

Some templates ship reusable assets (HTML templates, icons, image sets) that produced skills reference. Asset handling is **template-defined**: each template specifies whether assets are copied into each produced skill's `assets/` directory, symlinked, or referenced via the template install path. Defer asset questions to the active template's documentation; if no template is active, skills typically don't need bundled assets and `assets/` stays empty.

## What ships, what doesn't

Ships in `<project>/.claude/skills/`:

- One directory per produced skill, with SKILL.md at minimum.
- `references/` subdirs for material that's useful but loads on demand.
- `assets/` for non-text files the skill body needs (rare; templates handle this).

Does NOT ship:

- Raw `<project>/.john/knowledge/` — that's working state, not deliverable.
- Event logs from extraction/rewrite — audit trail, not deliverable.
- Source documents from `<project>/.john/input/` — provenance, not deliverable.

If the user wants to ship the working state too (for transparency, reproducibility, archival), they use `/john:archive` which bundles everything. Packaging is about the *runtime-consumable* output, not the audit trail.

## Quality checks before the phase is done

1. **Every produced skill loads cleanly.** YAML frontmatter parses; body is valid markdown.
2. **Descriptions are pushy.** Spot-check 5: would Claude reliably trigger this skill on a relevant prompt?
3. **Cross-links resolve.** `[[skill-name]]` references in bodies point to skills that actually exist.
4. **No leaked workspace paths.** Skills shouldn't reference `<project>/.john/` (working state) or the user's input source paths — those don't matter to the runtime.
5. **The skills-analytics dashboard (if installed) shows the new skills as discoverable.** Optional check, valuable when shaking down a fresh run.

## The handoff to 2app

After packaging completes, PLAN.md's Knowledge inventory section transitions from "pointer to `.john/input/`" to "pointer to `.claude/skills/`" — the 2app phases now have a *real* knowledge source to consume, not raw input. Update PLAN.md's Log section accordingly.

The 2app half (the app-building phase skills) reads from `.claude/skills/` as its starting context. The two halves of John meet at this directory.

## Cross-references

- [[knowledge-rewrite]] — the prior phase, where the knowledge is cleaned
- [[schema-design]] — what determines the per-entry-to-skill mapping
- [[plan-md-authoring]] — the Knowledge inventory section that gets updated
- [[ralph-loop]] — advances out of packaging into 2app
- [[app-design-thinking]] — the next phase reads what packaging emits; settles the runtime + production-pipeline links of the four-structures cascade
- See `references/` for: Claude Code's skill format, skill-creator's description-pushiness advice, KC's rule-skill shape
