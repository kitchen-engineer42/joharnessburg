---
name: "source-command-init"
description: "Codex-compatible project skill for the John init command. Use when the user wants the equivalent of /john:init in this source checkout."
---

# source-command-init

This project-level skill runs the same script as Claude Code's `/john:init`.

Run from the user's target project directory:

```bash
python3 "plugins/joharnessburg/scripts/init_workspace.py" <input-path-if-any> <--force-if-present>
```

Behavior:

- creates `.john/` and its working subdirectories
- writes `.john/workspace.json`
- writes `PLAN.md` unless it already exists, or regenerates it with `--force`
- writes `CLAUDE.md` only when it is missing
- optionally copies the provided input path into `.john/input/`

After a successful run, read `PLAN.md` and continue with `plan-md-authoring`.
