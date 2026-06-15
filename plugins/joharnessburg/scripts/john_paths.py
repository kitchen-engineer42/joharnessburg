#!/usr/bin/env python3
from __future__ import annotations

"""Workspace-root discovery shared by John's hooks and CLI toolkit.

A session's working directory is frequently a SUBDIRECTORY of the project
(Claude cd's into app/ and the like). Resolving `.john/` only at cwd made
the hooks silently no-op from subdirectories — context injection and trace
offload just stopped — and made the CLI scripts error confusingly.
`find_john_root()` walks up from a start path to the nearest directory
containing `.john/`, the same discovery semantics as git's `.git`.

Scripts that CREATE a workspace (init_workspace.py) deliberately do NOT use
this — init scaffolds at cwd, and walking up would hijack nested projects.
"""

from pathlib import Path


def find_john_root(start: Path) -> Path | None:
    """Nearest ancestor of `start` (inclusive) containing a `.john/` dir.

    Returns None when no `.john/` exists anywhere up the tree.
    """
    try:
        current = Path(start).resolve()
    except OSError:
        return None
    for candidate in (current, *current.parents):
        try:
            if (candidate / ".john").is_dir():
                return candidate
        except OSError:
            return None
    return None
