---
name: "source-command-status"
description: "Codex-compatible project skill for the John status command. Use when the user wants the equivalent of /john:status in this source checkout."
---

# source-command-status

This project-level skill runs the same script as Claude Code's `/john:status`.

Run from the user's John project directory:

```bash
python3 "plugins/joharnessburg/scripts/workspace_status.py"
```

Show the human-readable summary from stderr. Use the JSON on stdout to decide
the next phase. If the user asks what to do next, read `PLAN.md` and proceed
through `ralph-loop`.
