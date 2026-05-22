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
   - For `list`: the list of installed templates (and their location). If the list is empty, note that no templates are installed yet and point at `templates/README.md` in the plugin source for template-authoring.
   - For `set`: confirmation that the template is now active. The SessionStart hook surfaces the active template name in every new session's additionalContext, and you should manually read the template's content from `~/.claude/plugins/joharnessburg-templates/<name>/` — specifically `claude_addon.md`, `plan_md_template.md`, `skills/_override/*/SKILL.md`, `skills/*/SKILL.md`, and `skills/_delete` if present — and apply them mentally for this session. Auto-merge of template content into the loaded skill set is NOT implemented in v0.1.6; the active_template field is the pointer, not the merger.
   - For `clear`: confirmation that no template is now active.

4. On `success: false` with "Template '<name>' is not installed", tell the user the list of installed templates and where templates live on disk (`~/.claude/plugins/joharnessburg-templates/`).
