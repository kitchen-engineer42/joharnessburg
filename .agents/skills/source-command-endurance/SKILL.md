---
name: "source-command-endurance"
description: "Codex-compatible project skill for the John endurance command. Use when the user wants the equivalent of /john:endurance in this source checkout."
---

# source-command-endurance

This project-level skill runs the same script as Claude Code's
`/john:endurance`.

Run from the source checkout root:

```bash
python3 "plugins/joharnessburg/scripts/set_endurance.py" <goal-text-or---clear>
```

Behavior:

- with goal text: stores it in `.john/workspace.json`
- with no arguments: prints the current goal
- with `--clear`: removes the current goal

In Codex, re-read `.john/workspace.json` and `PLAN.md` at resumed-session
boundaries unless the project has Codex `SessionStart` hooks enabled.
