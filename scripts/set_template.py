#!/usr/bin/env python3
"""Set or list the active John template for the current project.

With no arg: lists installed templates under
`~/.claude/plugins/joharnessburg-templates/`.

With `<name>`: validates the template exists, then updates
`<cwd>/.john/workspace.json` `active_template` field.

Use `--clear` to unset the active template (set to null).

This script runs in **layer-2 sessions** inside the user's project.

Exit codes:
  0  success
  1  expected failure (no .john/, template not found, conflicting flags)
  2  unexpected exception
"""

import argparse
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path


TEMPLATES_ROOT = Path.home() / ".claude" / "plugins" / "joharnessburg-templates"


def emit(payload, success=True, exit_code=0):
    payload["success"] = success
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()
    sys.exit(exit_code)


def err(msg, exit_code=1):
    sys.stderr.write(msg + "\n")
    emit({"error": msg}, success=False, exit_code=exit_code)


def list_installed_templates():
    """Return a list of template names found under TEMPLATES_ROOT."""
    if not TEMPLATES_ROOT.exists():
        return []
    return sorted([d.name for d in TEMPLATES_ROOT.iterdir() if d.is_dir()])


def main():
    parser = argparse.ArgumentParser(
        description="Set or list the active John template.",
    )
    parser.add_argument(
        "name",
        nargs="?",
        help="Template name to activate. Omit to list installed templates.",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear the active template (set to null).",
    )
    args = parser.parse_args()

    if args.name and args.clear:
        err("Cannot pass both <name> and --clear.", exit_code=1)
        return

    installed = list_installed_templates()

    # List mode
    if not args.name and not args.clear:
        emit(
            {
                "action": "list",
                "templates_root": str(TEMPLATES_ROOT),
                "installed": installed,
                "count": len(installed),
            }
        )
        return

    # Update mode requires .john/
    cwd = Path.cwd()
    workspace_json = cwd / ".john" / "workspace.json"
    if not workspace_json.exists():
        err(
            f"No .john/workspace.json found in {cwd}. "
            f"Run /joharnessburg-init first.",
            exit_code=1,
        )
        return

    try:
        state = json.loads(workspace_json.read_text())
    except json.JSONDecodeError as exc:
        err(f"workspace.json is not valid JSON: {exc}", exit_code=1)
        return

    previous = state.get("active_template")

    if args.clear:
        new_template = None
    else:
        if args.name not in installed:
            err(
                f"Template '{args.name}' is not installed. "
                f"Installed: {installed if installed else '(none)'}. "
                f"Expected location: {TEMPLATES_ROOT / args.name}",
                exit_code=1,
            )
            return
        new_template = args.name

    state["active_template"] = new_template
    state.setdefault("session_metadata", {})
    state["session_metadata"]["template_set_at"] = datetime.now(timezone.utc).isoformat()

    workspace_json.write_text(json.dumps(state, indent=2) + "\n")

    emit(
        {
            "action": "clear" if args.clear else "set",
            "previous_template": previous,
            "active_template": new_template,
            "installed": installed,
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
