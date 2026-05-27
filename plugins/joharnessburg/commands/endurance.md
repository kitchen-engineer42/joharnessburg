---
description: Set or clear the long-running goal for this John session. Pinned into the system prompt by the SessionStart hook so it survives context compaction and stays visible across long ralph-loop runs. Use this command when the user says "let's run this in endurance mode", "set the endurance goal to ...", "/endurance ...", or starts any long-running shakedown / pipeline / build that should hold a finish line across many compactions.
argument-hint: "[goal-text] [--clear]"
---

When this command fires:

1. Parse the user's argument. Everything after `/endurance` (joined into one string) is the endurance goal — a short, concrete statement of what the long run is trying to produce. The `--clear` flag (if present, alone) clears the active endurance goal.

2. Invoke the script via Bash:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/set_endurance.py" <user-args>
   ```

   Pass the goal text as a single argument (quote it). For `--clear`, pass only `--clear`.

3. The script returns JSON with `action: "set" | "clear" | "show"`. Show the user:
   - For `set`: confirm the goal is now written to `<cwd>/.john/workspace.json` under `session_metadata.endurance_goal`. Tell them the SessionStart hook will inject it into the system prompt at the top of every session in this directory from now on — so the goal survives context compaction and fresh-terminal restarts.
   - For `clear`: confirm the goal is removed. SessionStart will fall back to the "no endurance goal set" message.
   - For `show` (no args and no `--clear`): print the currently-set goal, or note that none is set.

4. After a successful `set`, gently remind the user that this is best used for *real* long runs — not every John session needs an endurance goal. A short Q&A session or a one-phase iteration is fine with just the project intent at the top of PLAN.md. Endurance mode is for runs that span hours, multiple compactions, or many ralph-loop iterations.

5. On `success: false` with "No .john/workspace.json found", tell the user to run `/joharnessburg:init` first — endurance goals attach to a John workspace.

Endurance mode pairs with the `ralph-loop` and `context-management` skills — the goal is what survives compaction and what you re-align to after each iteration.
