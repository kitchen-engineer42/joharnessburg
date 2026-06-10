---
name: archive-workspace
description: Bundle a finished John workspace from Codex. Use when the user wants to archive, package, hand off, or preserve a John project, or wants the Claude command equivalent of /john:archive.
---

# archive-workspace

This is the Codex equivalent of Claude Code's `/john:archive` command.

## Procedure

1. Parse the user's request:
   - optional label: used in the default archive filename
   - optional `--output PATH`: write to a specific zip path
   - optional `--force`: overwrite an existing archive

2. Resolve the plugin root:
   - In a Codex plugin install, this skill lives under `<plugin-root>/skills/archive-workspace/SKILL.md`.
   - The script is at `<plugin-root>/scripts/archive_workspace.py`.
   - In a source checkout, use `plugins/joharnessburg/scripts/archive_workspace.py`.

3. Run the script from the user's project directory:

```bash
python3 "<plugin-root>/scripts/archive_workspace.py" <label-if-any> <--output PATH> <--force>
```

4. Parse the JSON on stdout and tell the user:
   - archive path
   - file count
   - archive size

The archive includes durable John artifacts such as `PLAN.md`, `CLAUDE.md`,
`AGENTS.md`, `.john/`, `.claude/skills/`, and `.agents/skills/`. It excludes
git metadata, dependency folders, Python bytecode, and other local noise.
