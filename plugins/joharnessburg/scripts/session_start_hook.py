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
import os
import sys
import traceback
from pathlib import Path


PLAN_PREVIEW_CHARS = 3000


def _detect_template_from_env() -> str | None:
    """If running under a merged template plugin, return the template name.

    Detection rule: if $CLAUDE_PLUGIN_ROOT resolves to a path with parent
    `~/.claude/plugins/joharnessburg-applied/`, the template name is that
    path's basename. Otherwise (vanilla John, or any non-applied install)
    return None.
    """
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if not plugin_root:
        return None
    p = Path(plugin_root).resolve()
    applied_parent = (Path.home() / ".claude" / "plugins" / "joharnessburg-applied").resolve()
    try:
        if p.parent == applied_parent:
            return p.name
    except (OSError, ValueError):
        pass
    return None


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
    # Template detection derives from the merged plugin path
    # (CLAUDE_PLUGIN_ROOT). The plugin loaded at session start IS the
    # source of truth for what template is "active".
    active_template = _detect_template_from_env()
    active_template_label = active_template or "(none — vanilla John)"
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
            f"layer-2 Claude should investigate or re-run /john:init)"
        )

    # Compose the additionalContext string
    additional_context = (
        f"# John (joharnessburg) — Active Session\n\n"
        f"You are in a Claude Code session where the John plugin is active and this project's "
        f"workspace has been initialized.\n\n"
        f"**Endurance goal**: {endurance_goal}\n\n"
        f"**Active template applied**: {active_template_label}\n"
        + (
            ""
            if not active_template
            else (
                f"  (the template's diff was merged into the running plugin via "
                f"`apply_template.py`; treat all loaded skills as core — there is no "
                f"second-class \"template skill\" layer at runtime)\n"
            )
        )
        + f"\n**Current phase**: {current_phase}\n\n"
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
