---
description: Bundle the finished John workspace (PLAN.md, CLAUDE.md, .john/, .claude/skills/) into a release zip. Use when the user says "archive this project", "package it up", "we're done", or you've completed an end-to-end run and want a portable bundle. Excludes git/__pycache__/node_modules cruft.
argument-hint: "[label] [--output PATH] [--force]"
---

When this command fires:

1. Parse the user's argument. The first positional (if any) is a label for the archive (used in the default filename). `--output <path>` overrides the default location. `--force` allows overwriting an existing file.

2. Invoke the archive script via Bash:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/archive_workspace.py" <user-args>
   ```

3. The script returns JSON with `archive_path`, `file_count`, and `size_bytes`. Tell the user the zip is ready at the path, with the file count and size. If the user asked for the archive in the context of "we're done", consider also offering to run `/joharnessburg:status` for a final inventory check before they ship.

4. On `success: false` with "No .john/ directory found", tell the user there's no workspace to archive — they need `/joharnessburg:init` first.

The archive is suitable for handing to teammates, attaching to a release, or stashing for posterity. It does NOT include `subsites/`, `production/`, `node_modules/`, `__pycache__/`, `.git/`, or `.DS_Store` — only the durable John artifacts plus the produced skills.
