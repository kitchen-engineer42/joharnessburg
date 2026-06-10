# John templates — authoring guide

A template is a **diff to original John** that customizes the plugin for a specific domain (slide decks, doc verification, mystery games, portfolio sites, etc.). John core stays unchanged; templates add/override/delete skills, ship a PLAN.md skeleton, and append project guidance to CLAUDE.md.

This guide is for anyone authoring a template — internal team members, external contributors, or layer-2 Claude when the user says "let's make a template for X."

## Architecture (apply.sh + --plugin-dir)

The end-to-end flow:

1. **Templates live at `~/.claude/plugins/joharnessburg-templates/<name>/`** as directories. Distribution: copy/symlink/git-clone into that location. (You can keep template sources in their own git repo and `ln -s` into the install dir.)
2. **Applying a template** runs `apply_template.py` (via the template's `apply.sh`). The script:
   - Copies the joharnessburg install to `~/.claude/plugins/joharnessburg-applied/<template-name>/`.
   - Overlays the template's diff (overrides + additions + deletes).
   - Writes `.applied-metadata.json` with provenance.
   - Prints the launch command on stderr at success.
3. **Running John with the template**: `claude --plugin-dir ~/.claude/plugins/joharnessburg-applied/<template-name>/`. The merged dir IS John for that session — all skills load equally, no special template layer. Which template is loaded is fixed at session start (CLAUDE_PLUGIN_ROOT) and cannot be hot-swapped mid-session.
4. **Reset** = delete merged dirs. `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/reset_john.py` (or just `rm -rf ~/.claude/plugins/joharnessburg-applied/`).
5. **Switching templates**: exit the current session, apply a different template (or reuse an existing merged dir), relaunch with the new `--plugin-dir`. No per-workspace "active template" state to worry about — the session's plugin is determined entirely by how you launched.
6. **Parallel sessions, different templates**: each Claude Code session is independent. Multiple applied dirs at `~/.claude/plugins/joharnessburg-applied/<name>/` coexist freely; each parallel `claude --plugin-dir <one>` sees only that template's content.

## Why this design

- **Clean run state**: layer-2 Claude doesn't have to remember to read template files mid-session. Whatever's in the merged plugin IS what's loaded.
- **No per-workspace template state**: there's no `active_template` field to drift or to manage. The plugin path is the source of truth.
- **Skills-analytics works**: template skills appear as regular skill invocations in the dashboard. No "phantom skill" mystery.
- **Production-aligned**: when the tech team deploys John for production, templates can ship as part of the deployed plugin; same merge mechanic.
- **Authoring is local + one-click**: edit template files, run `./apply.sh`, launch Claude with the merged plugin, iterate. No plugin republish needed during iteration.

## Directory anatomy

```
~/.claude/plugins/joharnessburg-templates/<name>/
├── template.json                    # required: name, version, description, requires_john
├── apply.sh                         # required (copy/symlink of joharnessburg/templates/apply.sh)
├── claude_addon.md                  # optional: project-CLAUDE.md guidance, copied to templates-active/ in merged plugin
├── plan_md_template.md              # optional: starter PLAN.md, copied to templates-active/ for /john:init to consume
├── skills/
│   ├── <new-skill>/                 # additive — new skill not in John core
│   │   ├── SKILL.md
│   │   └── references/
│   ├── _override/                   # mirror the core skill path here
│   │   └── <core-skill>/SKILL.md    # replaces same-named core skill
│   └── _delete                      # optional: newline-delimited list of core skill names to remove from merged plugin
├── scripts/                         # optional: additional Python scripts (additive, no override semantics)
├── commands/                        # optional: additional slash commands (additive)
├── agents/                          # optional: additional subagent role definitions (additive)
└── workflows/                       # optional: saved dynamic-workflow scripts; installed into the project's .claude/workflows/ by /john:init
```

## template.json schema

Required:

```json
{
  "name": "your-template-name",
  "version": "0.1.0",
  "description": "What this template does and when to use it.",
  "requires_john": ">=0.1.15"
}
```

`name` must match the directory name. `requires_john` is checked at apply time (v0.2.0+): `>=X.Y.Z` (at-least) or bare `X.Y.Z` (exact) is compared against the installed John version, and a mismatch prints a prominent warning — **warn-only, the apply still proceeds**. Hamster's packager stamps it automatically; if you author by hand, pin the John version you actually built against.

## Apply mechanics (precise)

When `apply_template.py` runs for your template:

| Template file/dir | Effect on merged plugin |
|---|---|
| `skills/<new-name>/` (new dir, name NOT in core skills) | Copied into the merged plugin as a new skill. |
| `skills/_override/<core-name>/` | Deletes the existing `<core-name>/` from the merged plugin, replaces with this directory. The override file must stand on its own (full frontmatter + body + references/ as needed). Not a partial overlay. |
| `skills/_delete` (newline-delimited core skill names; full-line `#` comments and same-line `name # reason` comments ok) | Each named core skill dir is removed from the merged plugin. Deleting one of John's **load-bearing core skills** (using-john, ralph-loop, event-log-and-reducer, workspace-discipline, context-management, subagent-dispatch) is allowed but loud: state the why as a same-line comment (`ralph-loop # replaced by template loop`) or the apply prints an extra-loud warning. The warning also lists the remaining skills that still reference the deleted one. Warn-only — deliberate trim-downs (e.g. a minimal static-page template) go through, with a paper trail. |
| `scripts/<name>.py` | Copied into the merged plugin's `scripts/`. NOT-OVERRIDE: shadowing a core script name is a warning + skip. Use different names. |
| `commands/<name>.md` | Same NOT-OVERRIDE rule. |
| `agents/<name>.md` | Same NOT-OVERRIDE rule. |
| `claude_addon.md` | Copied to `templates-active/claude_addon.md` in the merged plugin. Layer-2 Claude can `Read` it and apply its guidance. `/john:init` also surfaces it under the scaffolded CLAUDE.md's "From active template" section. |
| `plan_md_template.md` | Copied to `templates-active/plan_md_template.md`. `/john:init` uses it as the PLAN.md skeleton instead of the hardcoded default. |
| `workflows/<name>.js` | Copied to `templates-active/workflows/` in the merged plugin, then installed by `/john:init` into the project's `.claude/workflows/` (skip-if-exists). Claude Code registers it as a `/<name>` command. |

Override semantics: **full replacement**, not merge. The override file is the new core file; nothing from the original is preserved.

**`plan_md_template.md` placeholders**: `/john:init` substitutes exactly two
placeholders — `{project_name}` and `{date}` — via targeted string
replacement. Any other braces (code snippets, JSON examples, a stray `{`)
pass through verbatim; no escaping needed.

## Shipping a saved workflow (research preview)

John core ships the *skill* to author workflows (the `vertical-workflows` skill), not rigid scripts — Claude writes the right fan-out for each project live. But when a template has a **stable** sweep shape (doc-verification's rule × chapter sweep; slides-from-textbook's per-slide render), you can freeze that orchestration as a reviewed, saved workflow and ship it in `workflows/`.

How it flows: `apply_template.py` copies `workflows/*` into the merged plugin's `templates-active/workflows/`; `/john:init` then copies them into the user's project `.claude/workflows/`, where Claude Code reads saved workflows (a plugin can't register them directly — that's why they ride through `templates-active/` to the project). Each becomes a `/<name>` command in that project.

Caveats — this is a research-preview surface, so keep it optional and graceful:

- **Requires the user's Claude Code to support dynamic workflows** (and the feature enabled). If it doesn't, the script files are inert and Claude falls back to authoring/dispatching live per the `vertical-workflows` skill — don't make a template *depend* on a shipped workflow.
- **Whether Claude auto-invokes a saved `/name` workflow** (vs the user typing it, or Claude re-authoring live under ultracode) is not guaranteed. Frame shipped workflows as reviewed *starting points* Claude can invoke or adapt, not as a hard pipeline step.
- **Freeze the shape, not the project specifics.** A shipped workflow encodes the fan-out *structure*; the per-entry prompt + schema stay project-specific. Don't bake one corpus's details into it (same discipline as `plan_md_template.md`).

## Authoring workflow

1. **Reference an example template** — they live in [Hamster](https://github.com/kitchen-engineer42/hamster) under `examples/`; this plugin deliberately ships none, so John's runtime carries only the template you load (or none). They're functional demonstrators of the diff format. For a methodical, Claude-guided build, use Hamster's full workflow.
2. **Settle the app-type definition** for your domain (knowledge format / knowledge schema / app mechanism / build pipeline). Capture in `plan_md_template.md`.
3. **Decide what to override vs add**:
   - John's `chunking` skill is generic — if your domain needs slide-shape or rule-shape chunking, override it.
   - Add new skills for steps John doesn't anticipate (slide-rendering, rule-extraction, etc.).
4. **Write `claude_addon.md`** for taste preferences, terminology, what good output looks like.
5. **Test the apply cycle**:
   - Symlink your template dir into `~/.claude/plugins/joharnessburg-templates/<name>/`.
   - Run `./apply.sh` from the template dir.
   - Read the printed launch command and copy-paste it: `claude --plugin-dir ~/.claude/plugins/joharnessburg-applied/<name>/`.
   - In a fresh test project, verify the new skills + overrides are loaded; check skills-analytics for invocations during a small task.
6. **Iterate** by editing template files and re-running `./apply.sh` (pass `--force` to overwrite the existing merged dir).

## Install location

`~/.claude/plugins/joharnessburg-templates/<name>/` (user-scope; manual install via `cp -r` or `ln -s`). Distribution: git repos or zipped tarballs the team copies.

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
- **Trying to stack templates**. Templates are diffs to original John, not to each other. You can have multiple applied dirs coexist for parallel sessions, but each session only ever uses ONE template (the one its `--plugin-dir` points at). Stacking template A's diff on top of template B's merged plugin isn't supported.
- **Patching the joharnessburg cache directly**. apply_template.py builds a separate merged dir under `joharnessburg-applied/`. Never edit the cache at `~/.claude/plugins/cache/joharnessburg/...` — `claude plugin update` will clobber your changes.
- **Bundling a closed checklist** unnecessarily. Templates can and should narrow the open methodology of John core when the domain genuinely calls for it (a verification-style template locking its rule schema is appropriate). But don't lock things that should stay project-specific.
- **Shipping a `plan_md_template.md` with hardcoded project intent**. The template provides a skeleton; the user fills in their project's specific intent during `/john:init`.

## When NOT to write a template

- One-off projects where the customizations only apply to this single project. Edit PLAN.md directly; don't generalize.
- Projects where John core's defaults are already 95% right. The 5% lives in PLAN.md's Open Decisions.
- Projects where the cost of authoring + maintaining a template exceeds the value. Templates pay off when you build multiple projects of the same shape; for a one-off, they're overhead.
