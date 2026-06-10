---
name: endurance-goal
description: Set, show, or clear the long-running John goal from Codex. Use when the user wants endurance mode, a persistent project finish line, or the Claude command equivalent of /john:endurance.
---

# endurance-goal

This is the Codex equivalent of Claude Code's `/john:endurance` command.

## When to use

Use this for long John runs that span many iterations, context compactions, or
fresh sessions. The goal is stored in `.john/workspace.json` under
`session_metadata.endurance_goal`.

## Procedure

1. Parse the user's request:
   - goal text: set the endurance goal
   - no arguments: show the current endurance goal
   - `--clear`: remove the current endurance goal

2. Resolve the plugin root:
   - In a Codex plugin install, this skill lives under `<plugin-root>/skills/endurance-goal/SKILL.md`.
   - The script is at `<plugin-root>/scripts/set_endurance.py`.
   - In a source checkout, use `plugins/joharnessburg/scripts/set_endurance.py`.

3. Run the script from the user's project directory:

```bash
python3 "<plugin-root>/scripts/set_endurance.py" <goal-text-or---clear>
```

4. Report the result:
   - set: confirm the goal is written to `.john/workspace.json`
   - clear: confirm the goal was removed
   - show: print the current goal or say none is set

In Codex, persistence depends on the project state and any enabled Codex
`SessionStart` hook. If hooks are not enabled, re-read `.john/workspace.json`
and `PLAN.md` at the start of a resumed run.
