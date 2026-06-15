---
name: "source-command-init"
description: "Codex-compatible project skill for the John init command. Use when the user wants the equivalent of /john:init in this source checkout."
---

# source-command-init

This project-level skill runs the same script as Claude Code's `/john:init`.

Run from the source checkout root. This project-level bridge skill is for
working inside the joharnessburg source tree; installed Codex plugins resolve
the plugin root from the loaded plugin instead.

```bash
python3 "plugins/joharnessburg/scripts/init_workspace.py" <input-path-if-any> <--force-if-present>
```

Behavior:

- creates `.john/` and its working subdirectories
- creates `.john/brief/` and `.john/contracts/` for the app-first intent flow
- writes `.john/workspace.json`
- writes `PLAN.md` unless it already exists, or regenerates it with `--force`
- writes `CLAUDE.md` and `AGENTS.md` only when missing
- optionally copies the provided input path into `.john/input/`

After a successful run, read `PLAN.md` and continue with `plan-md-authoring`:
capture known intent, parse/survey enough input to infer the app direction,
ask the single product-question batch only if needed, then produce
`.john/brief/user_intent.json`, `.john/contracts/app_blueprint.json`, and
`.john/contracts/extraction_plan.json`.
