---
name: "source-command-archive"
description: "Codex-compatible project skill for the John archive command. Use when the user wants the equivalent of /john:archive in this source checkout."
---

# source-command-archive

This project-level skill runs the same script as Claude Code's `/john:archive`.

Run from the source checkout root:

```bash
python3 "plugins/joharnessburg/scripts/archive_workspace.py" <label-if-any> <--output PATH> <--force>
```

Report the generated archive path, file count, and size from the JSON output.
The archive contains durable John workspace artifacts for both Claude Code and
Codex, and excludes local noise such as git metadata, dependency folders, and
Python bytecode.
