---
name: packaging
description: Emit cleaned, cross-linked, deduplicated knowledge from the rewrite phase as provider-discoverable skills in the project's Claude Code and Codex skill trees. Use this skill whenever the knowledge phases wrap, when the user says "package the skills" / "ship the knowledge" / "finalize the knowledge phases" / "we're ready for the app phases," or when [[ralph-loop]] signals packaging is next. Make sure to invoke this skill before the app phases run — they read the produced skills as their starting context. This is the deliverable boundary between knowledge engineering and app building; getting it wrong means the app phases operate without a real knowledge source.
metadata:
  triggers:
    - package the skills
    - ship the knowledge
    - emit skills
    - publish to .claude/skills
    - publish to .agents/skills
    - finalize knowledge phases
    - packaging phase
    - ready for app phases
---

# packaging

The knowledge phases end here. Packaging turns John's working knowledge state (in `<project>/.john/knowledge/`) into the deliverable that the app phases consume. For dual-provider projects, emit the same produced skills into both provider discovery roots:

- Claude Code: `<project>/.claude/skills/`
- Codex: `<project>/.agents/skills/`

After this phase, the produced skills are project-scoped skills auto-discovered by the matching provider session that builds the app.

## Where the work happens

- **Inputs**: `<project>/.john/knowledge/<entry-id>/{header.md, body.md}` (from [[knowledge-rewrite]])
- **Outputs**:
  - `<project>/.claude/skills/<skill-name>/SKILL.md`
  - `<project>/.agents/skills/<skill-name>/SKILL.md`
  - optional `references/`, `scripts/`, `assets/` in both provider roots when needed

`<project>/.claude/skills/` is Claude Code's project-scoped skill auto-discovery path. `<project>/.agents/skills/` is Codex's project-scoped skill auto-discovery path. Keep the two trees content-identical unless a provider-specific path or command truly requires a fork.

## What "skill" means here

A skill in Claude Code is one directory with at minimum a `SKILL.md`:

```
<project>/.claude/skills/<skill-name>/       # Claude Code
<project>/.agents/skills/<skill-name>/       # Codex
├── SKILL.md          # required: YAML frontmatter + markdown body
├── references/       # optional: deeper material loaded on demand
├── scripts/          # optional: executable code
└── assets/           # optional: templates, icons, fonts, etc.
```

The frontmatter has `name` and `description`. Optionally `metadata.triggers[]` for keyword-based auto-load. Body is markdown — what the agent should do/know.

This is the same skill format John itself ships. Your packaging output is structurally identical to a John meta-skill or phase skill — the difference is who wrote it (humans for John core; a John-equipped agent during the knowledge phases for produced knowledge).

## Mapping knowledge entries → skills

The transformation per entry depends on the entry's knowledge-format:

- **Procedural** entries (skill-shaped knowledge) → emit as SKILL.md directly. `header.md` content becomes the description; `body.md` content becomes the body.
- **Factual** entries → can be packaged as a single "facts skill" with all facts in the body, OR as one skill per fact (rare; only for hugely important facts). Usually facts go into a single browsable skill with cross-links.
- **Rules** → one skill per rule (KC's pattern). Each rule's SKILL.md teaches the runtime when to apply the rule and what action to take.
- **Storylines / scenes / characters** → one skill per character or scene; cross-links between them.
- **Glossary** → one skill that contains the whole glossary, OR one skill per term (rare). Usually one.

**Pattern:** chunky entries (rules, characters, scenes) become per-entry skills; granular entries (glossary terms, individual facts) often bundle into one skill per category. KC's "one skill per rule" works because rules are medium-grain and independent; other schemas may shape the mapping differently. The user's [[plan-md-authoring]] phase 1 sketch usually anticipates which way to go.

## Frontmatter conventions

Per Claude Code/Codex skill standards + skill-creator's writing guidance:

- **`name`**: kebab-case, lowercase, max 64 chars. Globally distinctive within the project.
- **`description`**: pushy per skill-creator. Don't write "Does X." Write *"Use this skill when the user mentions X / wants to do Y / asks about Z. Make sure to consult this skill whenever the runtime is about to apply <domain-specific operation>."* Combat the LLM tendency to undertrigger.
- **`metadata.triggers[]`**: tight keyword list of phrases that should auto-load the body. 5-10 entries. Specific to the domain.

The header of each entry maps to the description; the rest of the entry maps to body + optional references/.

## The packaging script — discovery and invocation

Two paths, depending on whether a template is active:

**Template-defined packaging** (preferred when applicable). Active templates may ship `scripts/package_<domain>.py` inside the merged plugin. In Claude Code this is usually under `$CLAUDE_PLUGIN_ROOT/scripts/`; in Codex, resolve the plugin root from the loaded skill path or the source checkout. List `<plugin-root>/scripts/` for any `package_*.py`; if present, invoke it via Bash with the project root as an argument. The script handles the schema-specific mapping. For dual-provider projects, output must land in both `<project>/.claude/skills/` and `<project>/.agents/skills/`.

**Inline packaging** (default when no template script is provided). Iterate over `<project>/.john/knowledge/<entry-id>/`, emit each entry as a skill following the conventions in `references/claude-code-skill-format.md`. Map per the patterns above (chunky vs granular). Straightforward but slower because each entry's emission is an agent judgment rather than a deterministic script.

John core ships packaging as **skill-only** — there's no core packaging script. Template-specific packaging scripts are a template concern; expect inline packaging in most projects unless the active template provides its own.

## Asset lifecycle for template-provided media

Some templates ship reusable assets (HTML templates, icons, image sets) that produced skills reference. Asset handling is **template-defined**: each template specifies whether assets are copied into each produced skill's `assets/` directory, symlinked, or referenced via the template install path. Defer asset questions to the active template's documentation; if no template is active, skills typically don't need bundled assets and `assets/` stays empty.

## What ships, what doesn't

Ships in both `<project>/.claude/skills/` and `<project>/.agents/skills/`:

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
2. **Descriptions are pushy.** Spot-check 5: would either supported runtime reliably trigger this skill on a relevant prompt?
3. **Cross-links resolve.** `[[skill-name]]` references in bodies point to skills that actually exist.
4. **No leaked workspace paths.** Skills shouldn't reference `<project>/.john/` (working state) or the user's input source paths — those don't matter to the runtime.
4b. **Trained skills carry their provenance header.** Any worker skill that went through the training loop ([[skill-evolution]]) ships with its provenance comment (when trained, scorer, baseline → final scores) intact — that header is how the next builder knows the text was earned, not guessed.
5. **The skills-analytics dashboard (if installed) shows the new skills as discoverable.** Optional check, valuable when shaking down a fresh run.

## The handoff to the app phases

After packaging completes, PLAN.md's Knowledge inventory section transitions from "pointer to `.john/input/`" to "pointer to produced skills in `.claude/skills/` and `.agents/skills/`" — the app phases now have a *real* knowledge source to consume, not raw input. Update PLAN.md's Log section accordingly.

The app phases (the app-building phase skills) read from the provider's produced-skills directory as their starting context. The two halves of John meet at these directories.

## Cross-references

- [[knowledge-rewrite]] — the prior phase, where the knowledge is cleaned
- [[schema-design]] — what determines the per-entry-to-skill mapping
- [[plan-md-authoring]] — the Knowledge inventory section that gets updated
- [[ralph-loop]] — advances out of packaging into the app phases
- [[app-design-thinking]] — the next phase reads what packaging emits; settles the runtime + production-pipeline links of the app-type definition cascade
- See `references/` for: Claude Code's skill format, skill-creator's description-pushiness advice, KC's rule-skill shape
