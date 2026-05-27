#!/usr/bin/env python3
"""Print a status report for the John workspace in the current directory.

Reads `.john/workspace.json` and checkpoint files, emits structured JSON
to stdout (for Claude) and a human-readable summary to stderr (for the
user).

This script runs in **layer-2 sessions** inside the user's project. It
reads from `Path.cwd()`, never from the John dev workspace.

Exit codes:
  0  success (status emitted)
  1  no .john/ found in cwd (suggest /joharnessburg-init)
  2  unexpected exception
"""

import argparse
import json
import os
import sys
import traceback
from pathlib import Path


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


def emit(payload, success=True, exit_code=0):
    payload["success"] = success
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()
    sys.exit(exit_code)


def err(msg, exit_code=1):
    sys.stderr.write(msg + "\n")
    emit({"error": msg}, success=False, exit_code=exit_code)


def count_files(p: Path, pattern: str = "*"):
    if not p.is_dir():
        return 0
    return sum(1 for _ in p.rglob(pattern) if _.is_file())


def list_dirs(p: Path):
    if not p.exists():
        return []
    return sorted([d.name for d in p.iterdir() if d.is_dir()])


def main():
    parser = argparse.ArgumentParser(
        description="Print John workspace status.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the human-readable summary on stderr; JSON only.",
    )
    args = parser.parse_args()

    cwd = Path.cwd()
    john_dir = cwd / ".john"

    if not john_dir.exists():
        err(
            f"No .john/ directory found in {cwd}. "
            f"Run /joharnessburg-init to scaffold one.",
            exit_code=1,
        )
        return

    workspace_json = john_dir / "workspace.json"
    if not workspace_json.exists():
        err(
            f".john/ exists but workspace.json is missing. Workspace may be corrupt; "
            f"consider /joharnessburg-init --force to rebuild.",
            exit_code=1,
        )
        return

    try:
        state = json.loads(workspace_json.read_text())
    except json.JSONDecodeError as exc:
        err(f"workspace.json is not valid JSON: {exc}", exit_code=1)
        return

    # Inventory of phase artifacts
    phases_with_events = list_dirs(john_dir / "events")
    phases_with_checkpoints = list_dirs(john_dir / "checkpoints")

    inventory = {
        "input_files": count_files(john_dir / "input"),
        "parsed_dirs": len(list_dirs(john_dir / "parsed")),
        "chunks_files": count_files(john_dir / "chunks"),
        "knowledge_entries": len(list_dirs(john_dir / "knowledge")),
        "events_phases": phases_with_events,
        "checkpoints_phases": phases_with_checkpoints,
        "trace_files": count_files(john_dir / "trace"),
    }

    # Produced skills (the 2skills deliverable)
    skills_dir = cwd / ".claude" / "skills"
    inventory["produced_skills"] = len(list_dirs(skills_dir)) if skills_dir.exists() else 0

    plan_exists = (cwd / "PLAN.md").exists()
    claude_md_exists = (cwd / "CLAUDE.md").exists()

    report = {
        "project_root": str(cwd),
        "workspace": state,
        "plan_md_present": plan_exists,
        "claude_md_present": claude_md_exists,
        "inventory": inventory,
    }

    if not args.quiet:
        sys.stderr.write(_human_summary(report))
        sys.stderr.flush()

    emit(report)


def _human_summary(report):
    ws = report["workspace"]
    inv = report["inventory"]
    lines = [
        "",
        f"John workspace at: {report['project_root']}",
        f"  initialized: {ws.get('initialized_at', '?')}",
        f"  loaded template: {_detect_template_from_env() or '(none — vanilla John)'}",
        f"  current phase: {ws.get('current_phase') or '?'}",
        "",
        "Inventory:",
        f"  input files: {inv['input_files']}",
        f"  parsed dirs: {inv['parsed_dirs']}",
        f"  chunks files: {inv['chunks_files']}",
        f"  knowledge entries: {inv['knowledge_entries']}",
        f"  events phases: {len(inv['events_phases'])} ({', '.join(inv['events_phases']) or 'none'})",
        f"  checkpoints phases: {len(inv['checkpoints_phases'])} ({', '.join(inv['checkpoints_phases']) or 'none'})",
        f"  trace files: {inv['trace_files']}",
        f"  produced skills: {inv['produced_skills']}",
        "",
        f"PLAN.md present: {report['plan_md_present']}",
        f"CLAUDE.md present: {report['claude_md_present']}",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        sys.stderr.write(traceback.format_exc())
        emit({"error": f"unexpected exception: {exc}"}, success=False, exit_code=2)
