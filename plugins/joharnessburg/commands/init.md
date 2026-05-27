---
description: Scaffold the John workspace in the current project. Creates .john/ working state, a starter PLAN.md, and (if missing) a starter CLAUDE.md. Optionally copies an input path into .john/input/. ALWAYS run this first when starting a new John project — every other John command depends on .john/ existing.
argument-hint: "[input-path] [--force]"
---

When this command fires, the user is starting a new John project (or re-bootstrapping one). Your job:

1. Parse the user's argument. The first positional argument (if any) is a path to a file or directory of input materials to copy into `.john/input/`. The `--force` flag (if present) recreates `.john/` even if it exists.

2. Invoke the init script via Bash:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init_workspace.py" <user-args>
   ```

   Pass the user's positional + `--force` (if present). If the user gave no input path, just run the script with no positional argument.

3. Parse the JSON status on stdout. On `success: true`, summarize for the user: project_root, .john/ created, PLAN.md written (or kept), CLAUDE.md written (or kept), files copied. On `success: false`, surface the human-readable error from stderr.

4. After a successful init, read the freshly-written `PLAN.md` and invite the user to start the start-of-project conversation per the `plan-md-authoring` skill — confirm project intent, decide the four structures, sketch the first 2-3 phases.

Do NOT skip step 4. The init script only writes a skeleton; the actual project intent + four-structures decisions are a conversation you owe the user.

If the user already has a PLAN.md or CLAUDE.md in the project, init preserves them by default (only `--force` recreates PLAN.md; CLAUDE.md is never overwritten). Tell the user when this happens so they know the existing files were kept.
