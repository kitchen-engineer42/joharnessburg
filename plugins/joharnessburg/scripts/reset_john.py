#!/usr/bin/env python3
"""Reset John: delete all applied-template merged dirs under
`~/.claude/plugins/joharnessburg-applied/`.

After reset, launching `claude` (without --plugin-dir) loads the standard
joharnessburg plugin (vanilla John). Use this to switch templates: reset → apply
a different template → launch.

Exit codes:
  0  success
  1  expected failure (no applied dirs found)
  2  unexpected exception
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import traceback
from pathlib import Path


def resolve_applied_parent(override: str = None) -> Path:
    """Where applied-template merged dirs live.

    Resolution: --applied-parent CLI arg > $JOHN_APPLIED_PARENT env > default.
    Default: ~/.claude/plugins/joharnessburg-applied/
    """
    if override:
        return Path(override).expanduser().resolve()
    env = os.environ.get("JOHN_APPLIED_PARENT")
    if env:
        return Path(env).expanduser().resolve()
    return Path.home() / ".claude" / "plugins" / "joharnessburg-applied"


APPLIED_PARENT = resolve_applied_parent()


def emit(payload, success=True, exit_code=0):
    payload["success"] = success
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    sys.stdout.flush()
    sys.exit(exit_code)


def err(msg, exit_code=1):
    sys.stderr.write(msg + "\n")
    emit({"error": msg}, success=False, exit_code=exit_code)


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Delete all applied John templates (return to vanilla joharnessburg).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List currently-applied templates and exit without deleting.",
    )
    parser.add_argument(
        "--applied-parent",
        default=None,
        help="Override the applied-templates parent dir (default: $JOHN_APPLIED_PARENT or ~/.claude/plugins/joharnessburg-applied/).",
    )
    args = parser.parse_args(argv)

    applied_parent = resolve_applied_parent(args.applied_parent)

    if not applied_parent.is_dir():
        emit({"applied_dirs": [], "deleted": [], "message": "Nothing to reset (no applied dir)."})
        return

    applied = sorted([d for d in applied_parent.iterdir() if d.is_dir()], key=lambda p: p.name)

    if args.list:
        emit({"applied_dirs": [str(d) for d in applied]})
        return

    if not applied:
        emit({"applied_dirs": [], "deleted": [], "message": "Nothing to reset."})
        return

    if not args.yes:
        names = ", ".join(d.name for d in applied)
        sys.stderr.write(
            f"About to delete {len(applied)} applied template(s): {names}\n"
            f"  Parent dir: {applied_parent}\n"
            f"Re-run with --yes to proceed.\n"
        )
        err("Refused (no --yes); pass --yes to confirm.", exit_code=1)
        return

    deleted = []
    for d in applied:
        shutil.rmtree(d)
        deleted.append(str(d))

    emit(
        {
            "deleted": deleted,
            "message": f"Reset complete. Launch `claude` (without --plugin-dir) for vanilla John.",
        }
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        sys.stderr.write(traceback.format_exc())
        emit({"error": f"unexpected exception: {exc}"}, success=False, exit_code=2)
