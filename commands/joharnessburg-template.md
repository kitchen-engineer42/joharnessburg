---
description: Set, clear, or list John templates. In v0.1.7+, setting a template ALSO merges its diff onto the joharnessburg plugin (via apply_template.py) and prints the launch command. Templates layer domain-specific skills, overrides, and PLAN.md skeletons onto John. Use when the user mentions a template name, says "use template X", or asks "what templates are available?". No argument → lists installed templates.
argument-hint: "[template-name] [--clear] [--no-apply] [--reset-all]"
---

When this command fires:

1. Parse the user's argument. The first positional argument (if any) is the template name to activate. Flags:
   - `--clear` — clear the active template AND delete all applied merged dirs (vanilla John for next session)
   - `--no-apply` — set `active_template` in `workspace.json` but skip the apply merge (debug/dev only; almost no one wants this)
   - `--reset-all` — when switching templates, wipe any prior merged dir first (required to switch from template A to template B)

2. Invoke the template script via Bash:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/set_template.py" <user-args>
   ```

3. The script returns JSON with `action: "list" | "set" | "clear"` and (for set/clear) an `apply_result` field showing what apply_template.py / reset_john.py did. Show the user:

   - **For `list`**: the list of installed templates + their location. If empty, point at `templates/README.md` for authoring.
   - **For `set`**: the JSON output's `apply_result.launch_command` is the headline — tell the user to copy-paste it. Example:
     ```
     Template 'doc-verification' is set + merged.

     Launch a fresh Claude Code session with:
       claude --plugin-dir ~/.claude/plugins/joharnessburg-applied/doc-verification

     The merged plugin IS John for that session — all skills load equally (no second-class
     template layer at runtime). To switch templates: run /joharnessburg-template <other>
     --reset-all. To return to vanilla John: /joharnessburg-template --clear.
     ```
   - **For `clear`**: confirm vanilla John is restored. `apply_result.deleted` lists which merged dirs got wiped.

4. **Switching-templates error path**: if the user runs `/joharnessburg-template <new>` when `<other>` is already applied, `set_template.py`'s subprocess to `apply_template.py` will fail with "Cannot apply '<new>': other templates already applied (<other>)". Tell the user to either (a) re-run with `--reset-all`, or (b) explicitly clear first with `/joharnessburg-template --clear`.

5. **Re-applying the same template** (e.g., after template files changed, or after `claude plugin update joharnessburg` lands new core skills): re-running `/joharnessburg-template <same-name>` rebuilds the merged dir fresh (set_template passes `--force` to apply_template.py). User just re-runs the command.

6. **Verifying the merge worked**: layer-2 Claude (you, in the user's Claude Code session) cannot directly inspect the merged dir without filesystem access. Tell the user to run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/apply_template.py --template-root ~/.claude/plugins/joharnessburg-templates/<name>/ --force` standalone if they want to see the merge output without going through set_template's JSON envelope.

## Architecture note (v0.1.7 design)

Templates are **diffs to original John**, applied via `apply_template.py` to produce a runnable merged plugin at `~/.claude/plugins/joharnessburg-applied/<name>/`. The user launches Claude with `--plugin-dir` pointing at that dir. After merge, template content is indistinguishable from core John — no SessionStart-time content injection, no "template skill" second class. Reset = delete the merged dir. Switch = reset + apply new.

This replaces the v0.1.6 "manual-read convention" (which required Claude to read template files mid-session). Cleaner, more reliable, and aligns with `skills-analytics` (template skills now log as regular skill invocations).
