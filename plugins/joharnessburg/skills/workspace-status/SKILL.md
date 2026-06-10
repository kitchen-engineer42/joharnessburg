---
name: workspace-status
description: Show John workspace status from Codex. Use when the user asks what is done, where the John project is, what phase is current, what inputs or events exist, or wants the Claude command equivalent of /john:status.
---

# workspace-status

This is the Codex equivalent of Claude Code's `/john:status` command.

## Procedure

1. Resolve the plugin root:
   - In a Codex plugin install, this skill lives under `<plugin-root>/skills/workspace-status/SKILL.md`.
   - The script is at `<plugin-root>/scripts/workspace_status.py`.
   - In a source checkout, use `plugins/joharnessburg/scripts/workspace_status.py`.

2. Run the script from the user's project directory:

```bash
python3 "<plugin-root>/scripts/workspace_status.py"
```

3. Show the human-readable summary from stderr directly to the user.

4. Use the JSON on stdout to decide the next action. If the user is asking what
   is next, read `PLAN.md`, identify the next incomplete phase, and continue via
   `ralph-loop`.

If the script reports no `.john/` directory, tell the user to initialize the
workspace with `init-workspace`.
