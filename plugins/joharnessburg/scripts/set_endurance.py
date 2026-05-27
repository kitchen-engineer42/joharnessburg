#!/usr/bin/env python3
"""Set, clear, or show the endurance goal for the current John project.

The endurance goal is a long-running finish-line statement that the
SessionStart hook injects into the model's system prompt at the top of
every session, so it survives context compaction and fresh-terminal
restarts. Stored in `<cwd>/.john/workspace.json` under
`session_metadata.endurance_goal`.

Usage:
  set_endurance.py "<goal>"   # set the goal (positional args joined)
  set_endurance.py --clear    # clear the goal
  set_endurance.py            # show the current goal (or note none)

This script runs in **layer-2 sessions** inside the user's project. It
writes to `Path.cwd()` — never to the John dev workspace, never to the
plugin install location.

Exit codes:
  0  success
  1  expected failure (no .john/, conflicting flags)
  2  unexpected exception
"""

import argparse
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path


def emit(payload, success=True, exit_code=0):
    payload["success"] = success
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()
    sys.exit(exit_code)


def err(msg, exit_code=1):
    sys.stderr.write(msg + "\n")
    emit({"error": msg}, success=False, exit_code=exit_code)


def main():
    parser = argparse.ArgumentParser(
        description="Set, clear, or show the endurance goal for this project.",
    )
    parser.add_argument(
        "goal",
        nargs="*",
        help="Endurance goal text (joined into one string). Omit to show current goal.",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear the active endurance goal (set to null).",
    )
    args = parser.parse_args()

    goal_text = " ".join(args.goal).strip() if args.goal else ""

    if goal_text and args.clear:
        err("Cannot pass both a goal and --clear.", exit_code=1)
        return

    cwd = Path.cwd()
    workspace_json = cwd / ".john" / "workspace.json"
    if not workspace_json.exists():
        err(
            f"No .john/workspace.json found in {cwd}. "
            f"Run /joharnessburg:init first.",
            exit_code=1,
        )
        return

    try:
        state = json.loads(workspace_json.read_text())
    except json.JSONDecodeError as exc:
        err(f"workspace.json is not valid JSON: {exc}", exit_code=1)
        return

    state.setdefault("session_metadata", {})
    previous = state["session_metadata"].get("endurance_goal")

    # Show mode (no goal, no --clear)
    if not goal_text and not args.clear:
        emit(
            {
                "action": "show",
                "endurance_goal": previous,
                "is_set": previous is not None,
            }
        )
        return

    # Set or clear
    now = datetime.now(timezone.utc).isoformat()
    if args.clear:
        state["session_metadata"]["endurance_goal"] = None
        state["session_metadata"]["endurance_cleared_at"] = now
        new_goal = None
        action = "clear"
    else:
        state["session_metadata"]["endurance_goal"] = goal_text
        state["session_metadata"]["endurance_set_at"] = now
        new_goal = goal_text
        action = "set"

    workspace_json.write_text(json.dumps(state, indent=2) + "\n")

    emit(
        {
            "action": action,
            "previous_goal": previous,
            "endurance_goal": new_goal,
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
