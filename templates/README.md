# John templates — authoring guide (v0.1.7)

A template is a **diff to original John** that customizes the plugin for a specific domain (slide decks, doc verification, mystery games, portfolio sites, etc.). John core stays unchanged; templates add/override/delete skills, ship a PLAN.md skeleton, and append project guidance to CLAUDE.md.

This guide is for anyone authoring a template — internal team members, external contributors, or layer-2 Claude when the user says "let's make a template for X."

## The v0.1.7 architecture

1. **Templates live at `~/.claude/plugins/joharnessburg-templates/<name>/`** as directories. Distribution: copy/symlink/git-clone into that location.
2. **Applying a template** runs `apply_template.py` (via the template's `apply.sh` or via `/joharnessburg-template <name>`). The script:
   - Copies the joharnessburg install to `~/.claude/plugins/joharnessburg-applied/<template-name>/`.
   - Overlays the template's diff (overrides + additions + deletes).
   - Writes `.applied-metadata.json` with provenance.
   - Prints the launch command for the user.
3. **Running John with the template**: `claude --plugin-dir ~/.claude/plugins/joharnessburg-applied/<template-name>/`. The merged dir IS John for that session — all skills load equally, no special template layer.
4. **Reset** = delete the merged dir. `/joharnessburg-template --clear` does this. Or run `reset_john.py` directly.
5. **Switching templates**: reset → apply new. `/joharnessburg-template <new> --reset-all` is the one-shot. (Templates are diffs to **original John**, not to each other. Stacking them isn't supported by design.)

## Why this design

- **Clean run state**: layer-2 Claude doesn't have to remember to read template files mid-session. Whatever's in the merged plugin IS what's loaded.
- **Skills-analytics works**: template skills appear as regular skill invocations in the dashboard. No "phantom skill" mystery.
- **Production-aligned**: when the tech team deploys John for production, templates can ship as part of the deployed plugin; same merge mechanic.
- **Authoring is local + one-click**: a template author edits files in their template dir, runs `./apply.sh`, launches Claude with the merged plugin, iterates. No plugin republish needed during iteration.

## Directory anatomy

```
~/.claude/plugins/joharnessburg-templates/<name>/
├── template.json                    # required: name, version, description, requires_john
├── apply.sh                         # required (copy of joharnessburg/templates/apply.sh)
├── claude_addon.md                  # optional: project-CLAUDE.md guidance, copied to templates-active/ in merged plugin
├── plan_md_template.md              # optional: starter PLAN.md, copied to templates-active/ for /joharnessburg-init to consume
├── skills/
│   ├── <new-skill>/                 # additive — new skill not in John core
│   │   ├── SKILL.md
│   │   └── references/
│   ├── _override/                   # mirror the core skill path here
│   │   └── <core-skill>/SKILL.md    # replaces same-named core skill
│   └── _delete                      # optional: newline-delimited list of core skill names to remove from merged plugin
├── scripts/                         # optional: additional Python scripts (additive, no override semantics)
├── commands/                        # optional: additional slash commands (additive)
└── agents/                          # optional: additional subagent role definitions (additive)
```

## template.json schema

Required:

```json
{
  "name": "your-template-name",
  "version": "0.1.0",
  "description": "What this template does and when to use it.",
  "requires_john": ">=0.1.7"
}
```

`name` must match the directory name. `requires_john` is informational in v0.1.7 (apply_template.py doesn't enforce it yet; v0.1.8 may).

## Apply mechanics (precise)

When `apply_template.py` runs for your template:

| Template file/dir | Effect on merged plugin |
|---|---|
| `skills/<new-name>/` (new dir, name NOT in core skills) | Copied into the merged plugin as a new skill. |
| `skills/_override/<core-name>/` | Deletes the existing `<core-name>/` from the merged plugin, replaces with this directory. The override file must stand on its own (full frontmatter + body + references/ as needed). Not a partial overlay. |
| `skills/_delete` (newline-delimited core skill names; `#` comments ok) | Each named core skill dir is removed from the merged plugin. |
| `scripts/<name>.py` | Copied into the merged plugin's `scripts/`. NOT-OVERRIDE: shadowing a core script name is a warning + skip. Use different names. |
| `commands/<name>.md` | Same NOT-OVERRIDE rule. |
| `agents/<name>.md` | Same NOT-OVERRIDE rule. |
| `claude_addon.md` | Copied to `templates-active/claude_addon.md` in the merged plugin. Layer-2 Claude can `Read` it and apply its guidance. The merged `/joharnessburg-init` command also surfaces it. |
| `plan_md_template.md` | Copied to `templates-active/plan_md_template.md`. `/joharnessburg-init` uses it as the PLAN.md skeleton instead of the default. |

Override semantics: **full replacement**, not merge. The override file is the new core file; nothing from the original is preserved.

## Authoring workflow

1. **Start from an example** at `templates/examples/{slides-from-textbook,doc-verification}/`. Both are functional demonstrators (per spec §8.10 — production-ready templates are tech-team / team-lead work post-handoff).
2. **Settle the four structures** for your domain (format of knowledge / schema / runtime / pipeline). Capture in `plan_md_template.md`.
3. **Decide what to override vs add**:
   - John's `chunking` skill is generic — if your domain needs slide-shape or rule-shape chunking, override it.
   - Add new skills for steps John doesn't anticipate (slide-rendering, rule-extraction, etc.).
4. **Write `claude_addon.md`** for taste preferences, terminology, what good output looks like.
5. **Test the apply cycle**:
   - Symlink your template dir into `~/.claude/plugins/joharnessburg-templates/<name>/`.
   - Run `./apply.sh` (or `/joharnessburg-template <name>`).
   - Launch `claude --plugin-dir ~/.claude/plugins/joharnessburg-applied/<name>/` in a fresh test project.
   - Verify the new skills + overrides are loaded; check skills-analytics for invocations during a small task.
6. **Iterate** by editing template files, re-running apply.sh (with `--force` or via the slash command which auto-forces).

## Install location

Production: `~/.claude/plugins/joharnessburg-templates/<name>/` (user-scope; manual install via `cp -r` or `ln -s`). Distribution: git repos or zipped tarballs the team copies.

For your team: keep template source under git, symlink into the install location during development:

```bash
ln -s /path/to/your/template-source ~/.claude/plugins/joharnessburg-templates/<name>
```

Edits to source files reflect immediately; just re-run apply.sh to rebuild the merged plugin.

## Layer-2 framing for template authors

Template content runs in **layer-2 sessions inside users' projects** (once merged). Same rules as John core skills:

- Skill bodies address Claude in user projects, not the plugin developer.
- Paths reference `<project>/.john/...` and `${CLAUDE_PLUGIN_ROOT}/...`, never the workspace where the template was developed.
- `claude_addon.md` is read by layer-2 Claude as additional project memory; treat it as project-CLAUDE.md guidance, not template documentation.

If you find yourself writing "I/my workspace" in a template skill, you've slipped into layer-1 framing. Rewrite as if you're addressing the next Claude Code session that loads the merged plugin.

## Anti-patterns

- **Overriding a core skill with a near-identical copy**. If your override is 90% the same as the core, you don't need to override — add the small differences as a sibling skill the user/template consults when relevant.
- **Trying to stack templates**. Templates are diffs to original John, not to each other. Switching = reset → apply, never apply-on-top-of-apply.
- **Patching the joharnessburg cache directly**. apply_template.py builds a separate merged dir under `joharnessburg-applied/`. Never edit the cache at `joharnessburg/joharnessburg/<version>/` — `claude plugin update` will clobber your changes.
- **Bundling a closed checklist** unnecessarily. Templates can and should narrow the open methodology of John core when the domain genuinely calls for it (doc-verification locks the rule schema; that's appropriate). But don't lock things that should stay project-specific.
- **Shipping a `plan_md_template.md` with hardcoded project intent**. The template provides a skeleton; the user fills in their project's specific intent during `/joharnessburg-init`.

## When NOT to write a template

- One-off projects where the customizations only apply to this single project. Edit PLAN.md directly; don't generalize.
- Projects where John core's defaults are already 95% right. The 5% lives in PLAN.md's Open Decisions.
- Projects where the cost of authoring + maintaining a template exceeds the value. Templates pay off when you build multiple projects of the same shape; for a one-off, they're overhead.

## What changed from v0.1.6

- **v0.1.6** had a "manual-read convention": layer-2 Claude was instructed to read template files at session start. The SessionStart hook surfaced the template name but didn't merge content. Friction-prone; cognitive load; no skills-analytics signal.
- **v0.1.7** has the diff-script architecture above. SessionStart hook just surfaces the applied-template name as an info line. The merge happened offline via apply.sh. Cleaner.

If you authored a template under v0.1.6, no changes needed to the directory structure — same `skills/`, `_override/`, `_delete`, `claude_addon.md`, `plan_md_template.md` conventions. Add an `apply.sh` (copy/symlink `${CLAUDE_PLUGIN_ROOT}/templates/apply.sh`) and you're done.
