---
description: Print John workspace status — active template, current phase, inventory of inputs/parsed/chunks/knowledge/events/checkpoints/produced-skills. Use whenever the user asks "where are we?", "what's done?", "what's next?", or you need to verify state before advancing a phase. Cheap; run it generously.
---

When this command fires:

1. Invoke the status script via Bash:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/workspace_status.py"
   ```

2. The script emits JSON to stdout and a human-readable summary to stderr. Show the user the human-readable summary directly. Use the JSON to decide your own next action (e.g., advance phase, dispatch subagents).

3. On `success: false` with "No .john/ directory found", tell the user to run `/joharnessburg-init` first to scaffold the workspace.

After showing the status, if the user is asking "what's next?", consult `PLAN.md` (read the file) to identify the next incomplete phase and propose advancing it per the `ralph-loop` skill.
