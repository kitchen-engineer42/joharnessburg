---
description: Set or list the active John template (e.g., doc-verification, slides-from-textbook). Templates layer on top of John core to specialize phases, skills, and PLAN.md skeleton for a domain. Use this command when the user mentions a template name, says "use template X", or asks "what templates are available?". With no argument, lists installed templates.
argument-hint: "[template-name] [--clear]"
---

When this command fires:

1. Parse the user's argument. The first positional argument (if any) is the template name to activate. The `--clear` flag (if present) clears the active template (sets to null).

2. Invoke the template script via Bash:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/set_template.py" <user-args>
   ```

3. The script returns JSON with `action: "list" | "set" | "clear"`. Show the user:
   - For `list`: the list of installed templates (and their location). If the list is empty, note that no templates are installed yet and point at the workspace docs for template-authoring (M5 deliverable).
   - For `set`: confirmation that the template is now active, plus a note that the change takes effect on next John session start (SessionStart hook reads workspace.json — M5 affordance; for now, you should mentally apply the template's conventions when reading PLAN.md and skills).
   - For `clear`: confirmation that no template is now active.

4. On `success: false` with "Template '<name>' is not installed", tell the user the list of installed templates and where templates live on disk (`~/.claude/plugins/joharnessburg-templates/`).

Note: until M5 ships, the active_template field is informational — there's no hook yet that auto-applies template overrides. Active template still gets tracked in workspace.json for forward compatibility and so layer-2 Claude can read it from `/joharnessburg-status`.
