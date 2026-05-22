# John templates — authoring guide

A template is a layered sibling plugin that customizes John for a specific domain (slide decks, doc verification, mystery games, portfolio sites, etc.). John core stays unchanged; templates add/override/delete its skills and scripts at session-start time.

This guide is for anyone authoring a template — internal team members, external contributors who reach this guide via the plugin repo, or layer-2 Claude when the user says "let's make a template for X."

## What a template is

A template is a directory at `~/.claude/plugins/joharnessburg-templates/<name>/` (user-scope on the install machine). When the user runs `/joharnessburg-template <name>` in a project, the choice is written to `<project>/.john/workspace.json`. The next time a Claude Code session starts in that project, John's `SessionStart` hook reads the active-template entry and merges the template's contents over John core for that session.

Templates can:

- **Add** new skills, scripts, commands, agents (additive — files placed under the same dir layout as the plugin).
- **Override** any core skill (same-named file under `skills/_override/<name>/SKILL.md` fully replaces the core skill of that name).
- **Delete** a core skill (name listed line-by-line in `skills/_delete`).
- **Append** to project CLAUDE.md (via `claude_addon.md`).
- **Seed** the starter PLAN.md (via `plan_md_template.md`, used by `/joharnessburg-init` when present).

Templates **cannot**:

- Modify John core's `plugin.json` or `marketplace.json`.
- Ship binary executables beyond Python scripts callable from Bash.
- Reach outside `<project>/.john/` or `<project>/.claude/skills/` in the user's project (don't touch the user's actual source code; that's the produced-app phase's job).

## Directory anatomy

```
~/.claude/plugins/joharnessburg-templates/<name>/
├── template.json              # required: name, version, description, requires_john
├── claude_addon.md            # optional: appended to project CLAUDE.md when this template is active
├── plan_md_template.md        # optional: starter PLAN.md used by /joharnessburg-init when this template is active
├── skills/
│   ├── <new-skill>/           # additive — new skill not in John core
│   │   ├── SKILL.md
│   │   └── references/
│   ├── _override/             # overrides — mirror the core skill path here
│   │   └── <core-skill>/SKILL.md
│   └── _delete                # optional: newline-delimited list of core skill names to hide
├── scripts/                   # optional: additional Python scripts
├── commands/                  # optional: additional slash commands
└── agents/                    # optional: additional subagent role definitions
```

## template.json schema

Required fields:

```json
{
  "name": "your-template-name",
  "version": "0.1.0",
  "description": "One-paragraph what the template is + when to use it.",
  "requires_john": ">=0.1.4"
}
```

`name` must match the directory name. `version` follows semver. `requires_john` constrains the John plugin version this template targets.

## Override mechanics (precise)

The override system in v0.1.6 is **convention-driven, not auto-merged**. The SessionStart hook surfaces the active template name in additionalContext; layer-2 Claude then manually reads from `~/.claude/plugins/joharnessburg-templates/<name>/` and applies the contents mentally to its loaded skill set for the session.

When layer-2 Claude reads a template's contents:

| Template file | Intended effect |
|---|---|
| `skills/<new-name>/SKILL.md` (a skill name NOT in core) | Additive — treat as available alongside core skills. |
| `skills/_override/<core-name>/SKILL.md` | Use this body in place of the core skill of the same name for this session. |
| `skills/_delete` (newline-delimited core skill names) | Treat those core skills as unavailable for this session. |
| `scripts/<name>.py` | Available alongside core scripts; same NOT-OVERRIDE rule (don't shadow a core script name). |
| `commands/<name>.md` | Available alongside core slash commands; same NOT-OVERRIDE rule. |
| `claude_addon.md` | Read and apply as additional project-CLAUDE.md guidance (not written to disk; mental append). |
| `plan_md_template.md` | Used by `/joharnessburg-init` as the PLAN.md skeleton instead of John's generic one. |

Override semantics: full replacement, not merge. If a template ships `skills/_override/chunking/SKILL.md`, layer-2 Claude reads THAT body in place of the core `chunking/SKILL.md` — the override file must stand on its own (frontmatter + body + references/ subdir as needed). Don't ship a partial override expecting it to merge with the original.

**Why convention, not auto-merge?** Auto-merging template content into the SessionStart hook's additionalContext would inflate every session start by potentially hundreds of lines (one per override + one per addition). Convention-driven reading lets layer-2 Claude pull only the template content actually relevant to the current phase. A future revision (post-v0.1.6) may add selective auto-injection for the most-trigger-critical template content if the convention turns out to be unreliable in practice.

## Install location

```
~/.claude/plugins/joharnessburg-templates/<name>/
```

For v1, install is manual:

```sh
mkdir -p ~/.claude/plugins/joharnessburg-templates
cp -r /path/to/your/template-source ~/.claude/plugins/joharnessburg-templates/<name>/
# OR symlink for live editing:
ln -s /path/to/your/template-source ~/.claude/plugins/joharnessburg-templates/<name>
```

Marketplace-style packaging (so templates install via `claude plugin install <template-name>`) is deferred to v2. For now, distribute templates as git repos or zipped directories the team copies into the install location.

## How to author a template

1. **Start from an example.** Copy `templates/examples/slides-from-textbook/` or `templates/examples/doc-verification/` (in the joharnessburg plugin source) as a starting point. Both demonstrate the override mechanics at different levels of complexity.

2. **Settle the four structures for your domain.** Per spec §4 and the `app-design-thinking` skill: what format does knowledge take? What schema per entry? What's the produced app's runtime? What phases build it? Capture these decisions in your `plan_md_template.md`.

3. **Decide what to override vs add.** If John's `chunking` skill is fine for your domain, don't override it. If your domain has a strict schema (rules-only verification, slide-only output), override `schema-design` to narrow it. If your pipeline has steps John doesn't anticipate (slide rendering, rule testing), add new skills for those.

4. **Write `claude_addon.md`** to capture domain conventions and aesthetic that don't fit in the per-skill bodies: terminology, taste preferences, what to avoid, what good output looks like.

5. **Test locally** by installing the template via symlink and activating it in a fresh test project. Verify the active skill set changes (use `claude plugin details` or trigger a skill to see what's loaded). Run a minimal pipeline end-to-end if possible.

6. **Iterate** based on what real use reveals. Templates are living documents; expect to revise after every project that uses them.

## Examples bundled in this plugin

Under `templates/examples/`:

- **`slides-from-textbook/`** — lighter example. Overrides `chunking` for slide-shaped output; adds `slide-rendering` skill; ships a slide-tailored `plan_md_template.md`. Inspired by the team's `lesson2slides` subsite.
- **`doc-verification/`** — heavier example, KC-equivalent. Overrides `schema-design` to enforce rule shape; overrides `packaging` for per-rule-skill emission; adds `rule-extraction` + `rule-testing` skills; ships a KC-style 7-phase `plan_md_template.md`. Inspired by `kc_cli` and the team's compliance-verification work.

Both are **functional examples**, not production-ready templates. Their job is to demonstrate the layered runtime override mechanism. The team's production templates ship separately (per spec §8.10) when this plugin moves to production.

## Layer-2 framing for template authors

Template content runs in **layer-2 sessions inside users' projects**. Same rules as John core skills:

- Skill bodies address Claude in user projects, not the plugin developer.
- Paths reference `<project>/.john/...` and `${CLAUDE_PLUGIN_ROOT}/...`, never the workspace where the template was developed.
- `claude_addon.md` is appended to the user's project CLAUDE.md; treat it as project memory, not template documentation.

If you find yourself writing "I/my workspace" in a template skill, you've slipped into layer-1 framing. Rewrite as if you're addressing the next Claude Code session that loads this template.

## Anti-patterns

- **Overriding a core skill with a near-identical copy.** If your override is 90% the same as the core skill, you don't need to override; just add the small differences as a sibling skill the user/template consults when relevant.
- **Bundling a closed checklist** when John's skill leaves the door open *without good reason*. Templates can narrow — that's their job — and locking the schema is fine when the domain genuinely requires it (the bundled `doc-verification` template locks the schema to rules-only because verification only makes sense with that schema). The anti-pattern is *unjustified* rigidity: locking a choice that should stay project-specific just because you picked it for your first project. If you narrow, write down in the override skill body *why* it's locked so future template users can judge whether their project still fits. Per spec §8.13: don't tighten the pipeline more than necessary.
- **Shipping a `plan_md_template.md` with hardcoded project intent.** The plan template is a *skeleton*; the user fills in their project's specific intent during `/joharnessburg-init`. Leave the intent and four-structures rows as fill-in placeholders.
- **Duplicating prose from John core.** If you need to reference how chunking works in general, link to the core skill — don't restate it. Your template's `chunking` override should explain what's *different* for your domain, not re-teach the basics.

## When to NOT write a template

- One-off projects where the customizations only apply to this single project. Modify PLAN.md directly; don't generalize.
- Projects where John core's defaults are already 95% right. The 5% lives in PLAN.md's Open Decisions, not in a template.
- Projects where the cost of authoring + maintaining a template exceeds the value of running the project. Templates pay off when you build multiple projects of the same shape; for a one-off, they're overhead.
