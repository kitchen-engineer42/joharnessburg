---
description: Set, clear, or list John templates. In v0.1.7+, setting a template ALSO merges its diff onto the joharnessburg plugin (via apply_template.py) and prints the launch command. Templates layer domain-specific skills, overrides, and PLAN.md skeletons onto John. Use when the user mentions a template name, says "use template X", or asks "what templates are available?". No argument → lists installed templates.
argument-hint: "[template-name] [--clear] [--no-apply] [--reset-all]"
---

When this command fires:

1. Parse the user's argument. The first positional argument (if any) is the template name to activate. Flags:
   - `--clear` — clear the active template AND delete all applied merged dirs (vanilla John for next session)
   - `--no-apply` — set `active_template` in `workspace.json` but skip the apply merge (debug/dev only; almost no one wants this)
   - `--reset-all` — optional clean-slate flag. v0.1.8+ allows multiple applied templates to coexist for parallel sessions, so switching between them does NOT require `--reset-all`. Use this flag only when you want to explicitly wipe ALL prior applied dirs.

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
     template layer at runtime). Parallel sessions with different templates can coexist
     (v0.1.8+). To return to vanilla John in a session: relaunch without --plugin-dir.
     ```
   - **For `clear`**: confirm all applied merged dirs are wiped. `apply_result.deleted` lists the dirs removed.

4. **Switching templates** (v0.1.8+): applying a new template no longer requires `--reset-all`. Each applied template dir at `~/.claude/plugins/joharnessburg-applied/<name>/` is independent; multiple can coexist for parallel sessions. If you DO want a clean slate (delete all prior applied dirs before applying the new one), use `--reset-all`. Otherwise the new template just adds to the set.

5. **Re-applying the same template** (e.g., after template files changed, or after `claude plugin update joharnessburg` lands new core skills): re-running `/joharnessburg-template <same-name>` rebuilds the merged dir fresh (set_template passes `--force` to apply_template.py). User just re-runs the command.

6. **v0.1.9 atomic apply**: in v0.1.9+, `set_template.py` runs the apply step FIRST and only writes `active_template` to workspace.json after success. If apply fails, workspace.json is left unchanged and forensic fields (`active_template_pending`, `active_template_error`) appear under `session_metadata`. Tell the user to check these if a set command reports failure.

7. **Verifying the merge worked**: layer-2 Claude cannot directly inspect the merged dir. Tell the user to run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/apply_template.py --template-root ~/.claude/plugins/joharnessburg-templates/<name>/ --force` standalone if they want to see the merge output without going through set_template's JSON envelope.

## Architecture note (v0.1.7+ diff-script, v0.1.8+ per-session isolation)

Templates are **diffs to original John**, applied via `apply_template.py` to produce a runnable merged plugin at `~/.claude/plugins/joharnessburg-applied/<name>/`. The user launches Claude with `--plugin-dir` pointing at that dir. After merge, template content is indistinguishable from core John — no SessionStart-time content injection, no "template skill" second class.

Per-session isolation (v0.1.8+): multiple applied dirs coexist; each Claude Code session sees only the template its `--plugin-dir` points at; no cross-session leakage. Reset = delete one or all merged dirs. Switch between templates in one session = relaunch with a different `--plugin-dir`.

This replaces the v0.1.6 "manual-read convention" (which required Claude to read template files mid-session). Cleaner, more reliable, and aligns with `skills-analytics` (template skills now log as regular skill invocations).
