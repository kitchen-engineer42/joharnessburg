#!/usr/bin/env python3
"""Scaffold a John workspace in the current working directory.

Creates `.john/` with subdirs (input, parsed, chunks, knowledge, events,
checkpoints, trace), writes `.john/workspace.json` with initial state,
writes a starter `PLAN.md` and (only if missing) a starter `CLAUDE.md`.
Optionally copies a user-provided input path into `.john/input/`.

This script runs in **layer-2 sessions** inside the user's project. It
writes to `Path.cwd()` — never to the John dev workspace, never to the
plugin install location. Use `${CLAUDE_PLUGIN_ROOT}` only when finding
sibling scripts; never as a write target.

Exit codes:
  0  success
  1  expected failure (bad input path, .john/ already exists without --force)
  2  unexpected exception (caller should inspect stderr for traceback)
"""

import argparse
import json
import os
import shutil
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path


SUBDIRS = [
    "input",
    "parsed",
    "chunks",
    "knowledge",
    "events",
    "checkpoints",
    "trace",
]


PLAN_TEMPLATE = """\
# PLAN.md — {project_name}

*Created by `/joharnessburg:init` on {date}. Edit freely; this is your living plan and the durable contract that spans 2skills (knowledge engineering) and 2app (app building) in one session.*

## Project intent

<!-- What the produced app does, who uses it, what it consumes, what success looks like. Filled in during the start-of-project conversation between you and Claude — see the `plan-md-authoring` skill. -->

## Knowledge inventory

- Initial input: `.john/input/` (populated at scaffold time)
- Produced skills (after the 2skills half ships): `.claude/skills/`

## Four structures (per John's spec §4)

These four constrain each other in a cascade — format determines schema, schema constrains runtime, runtime drives the production pipeline. See the `plan-md-authoring` and `schema-design` skills for the methodology.

- **Format of knowledge**: <facts? rules? stories? wiki? mixed? — initial sketch, may evolve>
- **Schema of knowledge**: <starter shape per entry — fields, header/body, MECE>
- **Runtime structure**: <how the produced app works for end-users>
- **Production pipeline**: <the phases below>

## Phases

### Phase 1: bootstrap

- Intent: confirm project intent + four-structures sketch with the user; settle the project's shape.
- Skills to invoke: `plan-md-authoring`, `phase-design`
- Required artifacts: this PLAN.md filled in with intent + initial four-structures section
- Done criteria: user has read and approved the four-structures section + the first 2-3 phases

### Phase 2: TBD

*Design phases 2+ once the four-structures sketch is settled. The `phase-design` skill teaches how. Wide tunnel — don't over-specify too early.*

## Subagent matrix

*For any phase with vertical fan-out, list work units and their state here. Empty until phases need it. See the `subagent-dispatch` skill.*

## Open decisions

*Things you want the user's input on. Append as they arise; clear as they resolve.*

## Log

*Append-only, most recent first.*

- {date}: PLAN.md scaffolded by `/joharnessburg:init`
"""


CLAUDE_TEMPLATE = """\
# CLAUDE.md

Project memory for this John-driven project. Loaded automatically into every Claude Code session in this directory.

## Project context

<!-- Fill in as the project develops:
- Domain / subject matter
- Source provenance
- Project-specific terminology or conventions
- User taste preferences (writing style, output formats, what to avoid)

The `using-john` skill provides general John orientation; this file is for what's specific to THIS project. -->

## Active template

Whatever template is loaded is the one your session launched with — Claude Code reads `$CLAUDE_PLUGIN_ROOT` at session start, which is fixed for the lifetime of the session. To check from inside a session: ask Claude "which template am I running?" — it can read the plugin install path and report.

To switch templates: exit, optionally run `~/.claude/plugins/joharnessburg-templates/<name>/apply.sh`, then relaunch with `claude --plugin-dir ~/.claude/plugins/joharnessburg-applied/<name>/`.

## Project status

- Scaffolded by `/joharnessburg:init` on {date}
"""


def emit(payload, success=True, exit_code=0):
    """Print JSON status to stdout and exit."""
    payload["success"] = success
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()
    sys.exit(exit_code)


def err(msg, exit_code=1):
    """Print human-readable error to stderr + JSON to stdout, then exit."""
    sys.stderr.write(msg + "\n")
    emit({"error": msg}, success=False, exit_code=exit_code)


def copy_input(src: Path, dest_dir: Path, copied: list, project_root: Path):
    """Copy a file or the contents of a directory into dest_dir.

    Skips hidden entries recursively via shutil.copytree's `ignore=` parameter,
    so .git/, .DS_Store, etc. inside nested input dirs don't get copied.
    """
    if src.is_file():
        dest = dest_dir / src.name
        shutil.copy2(src, dest)
        copied.append(str(dest.relative_to(project_root)))
    elif src.is_dir():
        ignore_hidden = shutil.ignore_patterns(".*")
        for item in sorted(src.iterdir()):
            if item.name.startswith("."):
                continue
            target = dest_dir / item.name
            if item.is_file():
                shutil.copy2(item, target)
                copied.append(str(target.relative_to(project_root)))
            elif item.is_dir():
                shutil.copytree(item, target, ignore=ignore_hidden)
                copied.append(str(target.relative_to(project_root)) + "/")


def main():
    p = argparse.ArgumentParser(
        description="Scaffold a John workspace in the current directory.",
    )
    p.add_argument(
        "input_path",
        nargs="?",
        help="Path to a file or directory to copy into .john/input/. Optional.",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help=(
            "Delete and recreate .john/ if it already exists. PLAN.md is REGENERATED from "
            "the template (existing project intent + log is lost — back it up first if you "
            "need it). CLAUDE.md is never overwritten by --force (project memory is "
            "preserved); delete it manually if you want a clean slate."
        ),
    )
    p.add_argument(
        "--project-name",
        help="Project name used in PLAN.md header. Defaults to current directory name.",
    )
    args = p.parse_args()

    cwd = Path.cwd()
    john_dir = cwd / ".john"

    # Pre-flight: .john/ existence check
    if john_dir.exists() and not args.force:
        err(
            f".john/ already exists at {john_dir}. Use --force to recreate it, "
            f"or delete it manually first.",
            exit_code=1,
        )
        return

    if args.force and john_dir.exists():
        shutil.rmtree(john_dir)

    # Create the dir tree
    john_dir.mkdir()
    for sd in SUBDIRS:
        (john_dir / sd).mkdir()

    # workspace.json — initial state
    # Note: the template, if any, is determined by the merged plugin the
    # session launched with (CLAUDE_PLUGIN_ROOT), not by per-workspace state.
    now = datetime.now(timezone.utc).isoformat()
    workspace_state = {
        "name": "joharnessburg-workspace",
        "schema_version": 1,
        "initialized_at": now,
        "current_phase": "bootstrap",
        "session_metadata": {},
    }
    (john_dir / "workspace.json").write_text(
        json.dumps(workspace_state, indent=2) + "\n"
    )

    # If running inside a merged template plugin, the plugin install ships a
    # templates-active/ dir with plan_md_template.md + claude_addon.md.
    # apply_template.py writes these. Prefer them over the hardcoded
    # defaults so projects scaffolded via /joharnessburg:init pick up the
    # active template's intended skeleton automatically.
    templates_active = _resolve_templates_active()
    template_plan_md = None
    template_claude_addon = None
    if templates_active is not None:
        candidate_plan = templates_active / "plan_md_template.md"
        if candidate_plan.is_file():
            try:
                content = candidate_plan.read_text()
                if content.strip():
                    template_plan_md = content
            except OSError as exc:
                sys.stderr.write(
                    f"WARN: could not read {candidate_plan}: {exc}\n"
                )
        candidate_addon = templates_active / "claude_addon.md"
        if candidate_addon.is_file():
            try:
                content = candidate_addon.read_text()
                if content.strip():
                    template_claude_addon = content
            except OSError as exc:
                sys.stderr.write(
                    f"WARN: could not read {candidate_addon}: {exc}\n"
                )

    # PLAN.md — write if missing, overwrite if --force
    plan_path = cwd / "PLAN.md"
    project_name = args.project_name or cwd.name
    date = now[:10]
    plan_written = False
    plan_source = "default"
    if not plan_path.exists() or args.force:
        if template_plan_md is not None:
            try:
                body = template_plan_md.format(project_name=project_name, date=date)
            except (KeyError, IndexError):
                # Template authors may use literal `{...}` strings without
                # intending format substitution. Fall back to raw content.
                body = template_plan_md
            plan_path.write_text(body)
            plan_source = "template"
        else:
            plan_path.write_text(
                PLAN_TEMPLATE.format(project_name=project_name, date=date)
            )
        plan_written = True

    # CLAUDE.md — only write if missing; never overwrite (user may have content).
    # If a template's claude_addon.md is available, append it under a clearly
    # labeled section so layer-2 Claude can incorporate the addon as project memory.
    claude_path = cwd / "CLAUDE.md"
    claude_written = False
    claude_addon_appended = False
    if not claude_path.exists():
        body = CLAUDE_TEMPLATE.format(date=date)
        if template_claude_addon is not None:
            body += (
                "\n\n## From active template\n\n"
                "*Appended by `/joharnessburg:init` from the merged template's "
                "`templates-active/claude_addon.md`. Treat as project memory.*\n\n"
                + template_claude_addon.rstrip()
                + "\n"
            )
            claude_addon_appended = True
        claude_path.write_text(body)
        claude_written = True

    # Copy input materials (if provided)
    copied = []
    if args.input_path:
        src = Path(args.input_path).expanduser().resolve()
        if not src.exists():
            err(f"Input path does not exist: {src}", exit_code=1)
            return
        copy_input(src, john_dir / "input", copied, cwd)

    emit(
        {
            "project_root": str(cwd),
            "john_dir": str(john_dir.relative_to(cwd)),
            "plan_md": "PLAN.md" if plan_path.exists() else None,
            "plan_md_written": plan_written,
            "plan_md_source": plan_source,
            "claude_md": "CLAUDE.md" if claude_path.exists() else None,
            "claude_md_written": claude_written,
            "claude_addon_appended": claude_addon_appended,
            "templates_active_used": templates_active is not None and (
                template_plan_md is not None or template_claude_addon is not None
            ),
            "copied_input": copied,
            "active_template": None,
            "current_phase": "bootstrap",
            "initialized_at": now,
        }
    )


def _resolve_templates_active() -> Path | None:
    """Locate the active template's overlay dir inside the merged plugin install.

    `apply_template.py` writes the template's claude_addon.md + plan_md_template.md
    into `<merged-plugin>/templates-active/`. When init_workspace.py runs from
    within a Claude Code session launched with `--plugin-dir <merged-plugin>`,
    `${CLAUDE_PLUGIN_ROOT}` resolves to that merged plugin dir.

    Returns the templates-active path if it exists, else None. Resolution order:
    - $CLAUDE_PLUGIN_ROOT/templates-active/ (the canonical Claude Code env var)
    - $JOHN_TEMPLATES_ACTIVE/ (explicit override; useful for tests)
    - Walk up from this script's location (this script lives at
      <merged-plugin>/scripts/init_workspace.py, so parent.parent/templates-active/
      is the sibling dir).
    """
    override = os.environ.get("JOHN_TEMPLATES_ACTIVE")
    if override:
        p = Path(override).expanduser().resolve()
        return p if p.is_dir() else None

    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin_root:
        p = Path(plugin_root).expanduser().resolve() / "templates-active"
        if p.is_dir():
            return p

    # Walk up from this script. init_workspace.py lives at
    # <plugin>/scripts/init_workspace.py.
    self_parent_parent = Path(__file__).resolve().parent.parent
    p = self_parent_parent / "templates-active"
    if p.is_dir():
        return p

    return None


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        sys.stderr.write(traceback.format_exc())
        emit({"error": f"unexpected exception: {exc}"}, success=False, exit_code=2)
