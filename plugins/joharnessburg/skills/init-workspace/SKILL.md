---
name: init-workspace
description: Scaffold a John workspace in the current project from Codex. Use when the user wants to start using John, initialize a John project, import input materials into .john/input, or run the Claude command equivalent of /john:init.
---

# init-workspace

This is the Codex equivalent of Claude Code's `/john:init` command.

## When to use

Use this skill when starting or re-bootstrapping a John project. It creates the
project-local John state:

- `.john/`
- `.john/workspace.json`
- `.john/input/`
- `PLAN.md`
- `CLAUDE.md` if missing

## Procedure

1. Parse the user's request:
   - optional first path: file or directory to copy into `.john/input/`
   - optional `--force`: recreate `.john/` and regenerate `PLAN.md`

2. Resolve the plugin root:
   - In a Codex plugin install, this skill lives under `<plugin-root>/skills/init-workspace/SKILL.md`.
   - The script is at `<plugin-root>/scripts/init_workspace.py`.
   - In a source checkout, use `plugins/joharnessburg/scripts/init_workspace.py`.

3. Run the script from the user's project directory:

```bash
python3 "<plugin-root>/scripts/init_workspace.py" <input-path-if-any> <--force-if-present>
```

4. Parse the JSON on stdout. On success, tell the user:
   - project root
   - `.john/` created
   - whether `PLAN.md` was written or preserved
   - whether `CLAUDE.md` was written or preserved
   - which input files were copied

5. After success, read the new `PLAN.md` and start the project-shaping
   conversation using `plan-md-authoring`: confirm project intent, decide the
   app-type definition, and sketch the first phases.

Do not skip step 5. The script only scaffolds; the plan still needs user-facing
project decisions.
