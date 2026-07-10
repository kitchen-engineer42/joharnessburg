---
name: codex-template-activation
description: Activate a Hamster-built or otherwise applied John template for Codex in the current project. Use when a merged template plugin already exists, when the user asks to use a John template in Codex, or after template apply has produced a Claude `--plugin-dir` path and Codex needs the same overrides, additions, guidance, and agents.
---

# Codex template activation

Keep Claude's `apply.sh` and `claude --plugin-dir` flow unchanged. Activate its
merged result for Codex through project-local state:

```sh
python3 "<john-plugin>/scripts/activate_codex_template.py" \
  --merged-plugin "<applied-plugin-path>" \
  --project-root "<user-project>"
```

Read the JSON response. Report the installed/skipped agent names and reproduce
every instruction exactly. The script materializes the plugin under
`.john-codex/plugins/<template>/`, merges `.agents/plugins/marketplace.json`,
and adds `.john-codex/` to the repository-local Git exclude when possible.

The printed handoff verifies the installed listing, disables vanilla John for
this project, enables the applied listing, reviews and trusts its current hook
definition through `/hooks`, and restarts Codex. Treat all five as required;
installation alone neither enables the correct project state nor trusts hooks.

Do not edit a personal marketplace or global enablement automatically. Explain
that applied John replaces vanilla John for this project session; enabling both
creates duplicate hooks and ambiguous methodology.

Use `--force` only to rebuild a directory carrying John's activation marker.
The script rejects traversal, symlinks, and unmarked destinations, and restores
the prior activation and marketplace if publication fails.
