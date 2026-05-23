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
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path


def resolve_templates_root(override: str = None) -> Path:
    """Locate the templates install dir, with override + env-var + default fallback.

    Resolution order:
    1. Explicit --templates-root CLI arg (passed as `override`).
    2. JOHN_TEMPLATES_ROOT env var.
    3. Default: ~/.claude/plugins/joharnessburg-templates/
    """
    if override:
        return Path(override).expanduser().resolve()
    env_val = os.environ.get("JOHN_TEMPLATES_ROOT")
    if env_val:
        return Path(env_val).expanduser().resolve()
    return Path.home() / ".claude" / "plugins" / "joharnessburg-templates"


# Module-level constant kept for backward-compat with any callers that imported it;
# new code should call resolve_templates_root() directly.
TEMPLATES_ROOT = resolve_templates_root()


def emit(payload, success=True, exit_code=0):
    payload["success"] = success
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()
    sys.exit(exit_code)


def err(msg, exit_code=1):
    sys.stderr.write(msg + "\n")
    emit({"error": msg}, success=False, exit_code=exit_code)


def list_installed_templates(templates_root: Path = None):
    """Return a list of template names found under templates_root (or the resolved default)."""
    root = templates_root or resolve_templates_root()
    if not root.exists():
        return []
    return sorted([d.name for d in root.iterdir() if d.is_dir()])


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
    parser.add_argument(
        "--templates-root",
        default=None,
        help="Override the templates install dir (default: $JOHN_TEMPLATES_ROOT or ~/.claude/plugins/joharnessburg-templates/).",
    )
    parser.add_argument(
        "--no-apply",
        action="store_true",
        help="Set active_template in workspace.json but skip running the template's apply.sh. Use for debug/dev when you want to inspect the template before merging.",
    )
    parser.add_argument(
        "--reset-all",
        action="store_true",
        help="When applying a template (default), pass --reset-all to apply.sh so any prior merged template is wiped first. Required for switching templates.",
    )
    args = parser.parse_args()

    if args.name and args.clear:
        err("Cannot pass both <name> and --clear.", exit_code=1)
        return

    templates_root = resolve_templates_root(args.templates_root)
    installed = list_installed_templates(templates_root)

    # List mode
    if not args.name and not args.clear:
        emit(
            {
                "action": "list",
                "templates_root": str(templates_root),
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
                f"Expected location: {templates_root / args.name}",
                exit_code=1,
            )
            return
        new_template = args.name

    # v0.1.9 — Codex #2: make set + apply atomic from the workspace's perspective.
    # Run apply/reset FIRST; only update workspace.json after success.
    # On failure: leave `active_template` untouched and record forensic fields
    # `active_template_pending` + `active_template_error` for diagnosis.
    apply_result = None
    apply_failed = False
    apply_error = None

    if not args.no_apply:
        if args.clear:
            apply_result = _run_reset(plugin_root=_resolve_plugin_root())
        else:
            apply_result = _run_apply(
                template_root=templates_root / new_template,
                reset_all=args.reset_all,
            )
        if apply_result is not None and "error" in apply_result:
            apply_failed = True
            apply_error = apply_result.get("error")
        elif apply_result is not None and apply_result.get("success") is False:
            apply_failed = True
            apply_error = apply_result.get("error", "apply subprocess reported success=false")

    state.setdefault("session_metadata", {})
    now_iso = datetime.now(timezone.utc).isoformat()

    if apply_failed:
        # Don't commit the new template; record forensics for the user/Claude to debug.
        state["session_metadata"]["active_template_pending"] = new_template
        state["session_metadata"]["active_template_error"] = apply_error
        state["session_metadata"]["active_template_attempted_at"] = now_iso
        workspace_json.write_text(json.dumps(state, indent=2) + "\n")
        emit(
            {
                "action": "clear" if args.clear else "set",
                "previous_template": previous,
                "active_template": previous,  # unchanged
                "active_template_pending": new_template,
                "active_template_error": apply_error,
                "installed": installed,
                "apply_result": apply_result,
            },
            success=False,
            exit_code=1,
        )
        return

    # Success path: commit the new template and clear any stale pending forensics.
    state["active_template"] = new_template
    state["session_metadata"]["template_set_at"] = now_iso
    state["session_metadata"].pop("active_template_pending", None)
    state["session_metadata"].pop("active_template_error", None)
    state["session_metadata"].pop("active_template_attempted_at", None)
    workspace_json.write_text(json.dumps(state, indent=2) + "\n")

    emit(
        {
            "action": "clear" if args.clear else "set",
            "previous_template": previous,
            "active_template": new_template,
            "installed": installed,
            "apply_result": apply_result,
        }
    )


def _resolve_plugin_root() -> Path:
    """The joharnessburg install dir, for invoking sibling scripts.

    Tries CLAUDE_PLUGIN_ROOT (set by Claude Code), then falls back to walking up
    from this script's location (works when set_template.py is in the plugin's
    scripts/ dir).
    """
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env:
        return Path(env)
    # set_template.py lives at <plugin>/scripts/set_template.py
    return Path(__file__).resolve().parent.parent


def _run_apply(template_root: Path, reset_all: bool) -> dict:
    """Run apply_template.py for the given template. Returns its parsed JSON output."""
    import subprocess
    plugin_root = _resolve_plugin_root()
    apply_script = plugin_root / "scripts" / "apply_template.py"
    if not apply_script.is_file():
        return {"error": f"apply_template.py not found at {apply_script}; skipping apply."}
    cmd = ["python3", str(apply_script), "--template-root", str(template_root)]
    if reset_all:
        cmd.append("--reset-all")
    cmd.append("--force")  # set_template invokes; rebuild for fresh state
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return {"error": "apply_template.py timed out after 300s"}
    if result.returncode != 0:
        return {"error": f"apply_template.py failed (rc={result.returncode}): {result.stderr.strip()}"}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": "apply_template.py output was not valid JSON", "stdout": result.stdout}


def _run_reset(plugin_root: Path) -> dict:
    """Run reset_john.py --yes. Returns its parsed JSON output."""
    import subprocess
    reset_script = plugin_root / "scripts" / "reset_john.py"
    if not reset_script.is_file():
        return {"error": f"reset_john.py not found at {reset_script}; skipping reset."}
    try:
        result = subprocess.run(
            ["python3", str(reset_script), "--yes"],
            capture_output=True, text=True, timeout=60,
        )
    except subprocess.TimeoutExpired:
        return {"error": "reset_john.py timed out after 60s"}
    if result.returncode != 0:
        return {"error": f"reset_john.py failed (rc={result.returncode}): {result.stderr.strip()}"}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": "reset_john.py output was not valid JSON", "stdout": result.stdout}


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        sys.stderr.write(traceback.format_exc())
        emit({"error": f"unexpected exception: {exc}"}, success=False, exit_code=2)
