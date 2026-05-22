#!/usr/bin/env python3
"""SessionStart hook: inject endurance goal + PLAN.md state into the new session.

Wired in hooks/hooks.json for the SessionStart event. Reads the user's
<cwd>/.john/workspace.json + <cwd>/PLAN.md, composes an `additionalContext`
string Claude Code injects into the model's context before the first turn.

No-op (emit empty `{}`) when there's no `.john/workspace.json` — layer-2
Claude in a non-John project shouldn't trip over John's hooks.

This script runs in layer-2 sessions inside the user's project. Reads from
`cwd` (the user's project), never from the John workspace.

Exit codes:
  0  success (always — hook failures shouldn't break the session)
"""

import json
import sys
import traceback
from pathlib import Path


PLAN_PREVIEW_CHARS = 3000


def emit(payload):
    """Emit JSON to stdout and exit 0. Hook failures should never break the session."""
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()
    sys.exit(0)


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        # Malformed stdin — emit empty response, harness defaults to allow
        emit({})
        return

    cwd = Path(data.get("cwd", ".")).resolve()
    workspace_path = cwd / ".john" / "workspace.json"

    if not workspace_path.exists():
        # No John workspace in this directory — no-op
        emit({})
        return

    try:
        state = json.loads(workspace_path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        sys.stderr.write(f"WARN: could not read workspace.json: {exc}\n")
        emit({})
        return

    endurance_goal = (
        state.get("session_metadata", {}).get("endurance_goal")
        or "(no endurance goal set; ask the user with /endurance <goal> if running a long project)"
    )
    active_template = state.get("active_template") or "(none)"
    current_phase = state.get("current_phase") or "(unset)"
    initialized_at = state.get("initialized_at", "?")

    # PLAN.md preview
    plan_path = cwd / "PLAN.md"
    plan_preview = ""
    if plan_path.exists():
        try:
            plan_text = plan_path.read_text()
            if len(plan_text) > PLAN_PREVIEW_CHARS:
                plan_preview = (
                    plan_text[:PLAN_PREVIEW_CHARS]
                    + f"\n\n[... truncated; full PLAN.md is at {plan_path}, {len(plan_text)} total chars ...]"
                )
            else:
                plan_preview = plan_text
        except OSError as exc:
            sys.stderr.write(f"WARN: could not read PLAN.md: {exc}\n")
            plan_preview = f"(PLAN.md present at {plan_path} but could not read: {exc})"
    else:
        plan_preview = (
            f"(no PLAN.md at {plan_path}; the workspace was scaffolded but PLAN.md is missing — "
            f"layer-2 Claude should investigate or re-run /joharnessburg-init)"
        )

    # Compose the additionalContext string
    additional_context = (
        f"# John (joharnessburg) — Active Session\n\n"
        f"You are in a Claude Code session where the John plugin is active and this project's "
        f"workspace has been initialized.\n\n"
        f"**Endurance goal**: {endurance_goal}\n\n"
        f"**Active template**: {active_template}\n\n"
        f"**Current phase**: {current_phase}\n\n"
        f"**Workspace initialized at**: {initialized_at}\n\n"
        f"**Read PLAN.md first** before doing any substantive work. Re-read it after every context "
        f"compaction. The `using-john` skill is your top-level orientation; consult it if anything "
        f"about John's conventions is unclear.\n\n"
        f"## PLAN.md preview\n\n"
        f"```\n{plan_preview}\n```\n"
    )

    emit({
        "additionalContext": additional_context,
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
        },
    })


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        # Never break the session — log to stderr and emit empty
        sys.stderr.write(traceback.format_exc())
        emit({})
