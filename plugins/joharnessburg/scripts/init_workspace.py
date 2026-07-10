#!/usr/bin/env python3
"""Scaffold a John workspace in the current working directory.

Creates `.john/` with subdirs (input, parsed, chunks, knowledge, events,
checkpoints, trace), writes `.john/workspace.json` with initial state,
writes a starter `PLAN.md`, and writes starter provider memory files
(`CLAUDE.md` for Claude Code, `AGENTS.md` for Codex) only when missing.
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
import uuid
from datetime import datetime, timezone
from pathlib import Path

from path_safety import (
    atomic_write_text,
    ensure_contained,
    reject_tree_symlinks,
    validate_template_slug,
)


SUBDIRS = [
    "input",
    "parsed",
    "chunks",
    "knowledge",
    "events",
    "checkpoints",
    "trace",
    "lessons",
]


def _john_version() -> str | None:
    """Best-effort version of the John plugin this script ships in.

    Stamped into workspace.json as run-manifest provenance — a run report must
    be attributable to the exact John version that produced the run.
    """
    manifest = Path(__file__).resolve().parent.parent / ".claude-plugin" / "plugin.json"
    try:
        return json.loads(manifest.read_text(encoding="utf-8")).get("version")
    except (OSError, json.JSONDecodeError):
        return None


PLAN_TEMPLATE = """\
# PLAN.md — {project_name}

*Created by `/john:init` on {date}. Edit freely; this is your living plan and the durable contract that spans the knowledge phases (knowledge engineering) and the app phases (app building) in one session.*

## Project intent

<!-- What the produced app does, who uses it, what it consumes, what success looks like. Filled in during the start-of-project conversation between you and Claude — see the `plan-md-authoring` skill. -->

## Knowledge inventory

- Initial input: `.john/input/` (populated at scaffold time)
- Produced skills (after the knowledge phases ship):
  - Claude Code: `.claude/skills/`
  - Codex: `.agents/skills/`

## App-type definition

The four decisions that define this app type, in two pairs (format = what it is / how it works; schema = what it has / how it is built). They constrain each other in a cascade — knowledge format determines knowledge schema, schema constrains the app mechanism, mechanism drives the build pipeline. See the `plan-md-authoring` and `schema-design` skills for the methodology.

- **Knowledge format**: <facts? rules? stories? wiki? mixed? — initial sketch, may evolve>
- **Knowledge schema**: <starter shape per entry — fields, header/body, MECE>
- **App mechanism**: <how the produced app works for end-users>
- **Build pipeline**: <the phases below>

## Phases

### Phase 1: bootstrap

- Intent: confirm project intent + app-type-definition sketch with the user; settle the project's shape.
- Skills to invoke: `plan-md-authoring`, `phase-design`
- Required artifacts: this PLAN.md filled in with intent + initial app-type definition section
- Done criteria: user has read and approved the app-type definition section + the first 2-3 phases

### Phase 2: TBD

*Design phases 2+ once the app-type definition sketch is settled. The `phase-design` skill teaches how. Wide tunnel — don't over-specify too early.*

## Subagent matrix

*For any phase with vertical fan-out, list work units and their state here. Empty until phases need it. Note whether the phase runs as a dynamic workflow (`vertical-workflows` skill) or inline dispatch (`subagent-dispatch`) — work units and event paths are the same either way.*

## Open decisions

*Things you want the user's input on. Append as they arise; clear as they resolve.*

## Log

*Append-only, most recent first.*

- {date}: PLAN.md scaffolded by `/john:init`
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

- Scaffolded by `/john:init` on {date}
"""


AGENTS_TEMPLATE = """\
# AGENTS.md

Project memory for this John-driven project. Loaded automatically into Codex sessions in this directory.

## Project context

<!-- Fill in as the project develops:
- Domain / subject matter
- Source provenance
- Project-specific terminology or conventions
- User taste preferences (writing style, output formats, what to avoid)

The `using-john` skill provides general John orientation; this file is for what's specific to THIS project. -->

## Active John plugin

Codex reads John through the Codex plugin manifest when the `john` plugin is installed, or through project-local skills under `.agents/skills/`.

Claude Code reads John through the Claude plugin manifest and `CLAUDE.md`. Keep this file and `CLAUDE.md` aligned for provider-neutral project decisions.

## Project status

- Scaffolded by John init on {date}
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
        copied.append(str(Path(".john/input") / src.name))
    elif src.is_dir():
        ignore_hidden = shutil.ignore_patterns(".*")
        for item in sorted(src.iterdir()):
            if item.name.startswith("."):
                continue
            target = dest_dir / item.name
            if item.is_file():
                shutil.copy2(item, target)
                copied.append(str(Path(".john/input") / item.name))
            elif item.is_dir():
                shutil.copytree(item, target, ignore=ignore_hidden)
                copied.append(str(Path(".john/input") / item.name) + "/")


def _read_optional(directory: Path | None, filename: str) -> str | None:
    if directory is None:
        return None
    candidate = directory / filename
    if not candidate.is_file():
        return None
    content = candidate.read_text(encoding="utf-8")
    return content if content.strip() else None


def _append_addon(body: str, filename: str, content: str | None) -> str:
    if content is None:
        return body
    return (
        body
        + "\n\n## From active template\n\n"
        + "*Appended by `/john:init` from the merged template's "
        + f"`templates-active/{filename}`. Treat as project memory.*\n\n"
        + content.rstrip()
        + "\n"
    )


def _is_managed_workspace(john_dir: Path) -> bool:
    marker = john_dir / "workspace.json"
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(data, dict) and data.get("name") == "joharnessburg-workspace"


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
            "Delete and recreate .john/ if it already exists. The contents of .john/input/ "
            "are PRESERVED (user-supplied corpus, not derived state). PLAN.md is REGENERATED "
            "from the template (existing project intent + log is lost — back it up first if "
            "you need it). CLAUDE.md and AGENTS.md are never overwritten by --force "
            "(project memory is preserved); delete them manually if you want a clean slate."
        ),
    )
    p.add_argument(
        "--project-name",
        help="Project name used in PLAN.md header. Defaults to current directory name.",
    )
    args = p.parse_args()

    cwd = Path.cwd().resolve()
    john_dir = cwd / ".john"
    stage = cwd / f".john.stage-{uuid.uuid4().hex}"
    backup = cwd / f".john.backup-{uuid.uuid4().hex}"

    # Validate every read source before creating staging state.
    input_src = None
    if args.input_path:
        raw_input = Path(args.input_path).expanduser()
        if raw_input.is_symlink():
            err(f"Input path may not be a symlink: {raw_input}")
            return
        input_src = raw_input.resolve()
        if not input_src.exists():
            err(f"Input path does not exist: {input_src}", exit_code=1)
            return
        try:
            reject_tree_symlinks(input_src, label="input corpus")
        except ValueError as exc:
            err(str(exc))
            return

    if john_dir.is_symlink():
        err(f".john/ may not be a symlink: {john_dir}")
        return
    if john_dir.exists() and not args.force:
        err(
            f".john/ already exists at {john_dir}. Use --force to recreate it, "
            "or delete it manually first.",
            exit_code=1,
        )
        return
    if john_dir.exists() and not _is_managed_workspace(john_dir):
        err(
            f"Refusing --force for {john_dir}: workspace.json lacks John's "
            "provenance marker. Move it aside manually if replacement is intended."
        )
        return

    try:
        templates_active = _resolve_templates_active()
        if templates_active is not None:
            reject_tree_symlinks(templates_active, label="active template metadata")
        template_plan_md = _read_optional(templates_active, "plan_md_template.md")
        project_addon = _read_optional(templates_active, "project_addon.md")
        template_claude_addon = _read_optional(templates_active, "claude_addon.md")
        template_agents_addon = _read_optional(templates_active, "agents_addon.md")
    except (OSError, ValueError) as exc:
        err(f"Active template validation failed: {exc}")
        return

    now = datetime.now(timezone.utc).isoformat()
    date = now[:10]
    project_name = args.project_name or cwd.name
    plan_source = "template" if template_plan_md is not None else "default"
    plan_body = (
        template_plan_md.replace("{project_name}", project_name).replace("{date}", date)
        if template_plan_md is not None
        else PLAN_TEMPLATE.format(project_name=project_name, date=date)
    )
    claude_body = _append_addon(
        CLAUDE_TEMPLATE.format(date=date), "project_addon.md", project_addon
    )
    # Preserve byte-identical legacy behavior when only claude_addon.md exists.
    claude_body = _append_addon(claude_body, "claude_addon.md", template_claude_addon)
    agents_body = _append_addon(
        AGENTS_TEMPLATE.format(date=date), "project_addon.md", project_addon
    )
    agents_body = _append_addon(agents_body, "agents_addon.md", template_agents_addon)

    copied: list[str] = []
    input_preserved = False
    created_files: list[Path] = []
    prior_plan: str | None = None
    prior_plan_existed = (cwd / "PLAN.md").exists()
    workflows_installed: list[str] = []
    workflows_skipped: list[str] = []
    codex_agents_installed: list[str] = []
    codex_agents_skipped: list[str] = []
    published = False

    try:
        ensure_contained(cwd, stage, label="workspace staging")
        stage.mkdir()
        for subdir in SUBDIRS:
            (stage / subdir).mkdir()

        if john_dir.exists():
            old_input = john_dir / "input"
            if old_input.is_dir() and any(old_input.iterdir()):
                reject_tree_symlinks(old_input, label="preserved input corpus")
                shutil.copytree(old_input, stage / "input", dirs_exist_ok=True)
                input_preserved = True
        if input_src is not None:
            copy_input(input_src, stage / "input", copied, cwd)

        workspace_state = {
            "name": "joharnessburg-workspace",
            "schema_version": 1,
            "initialized_at": now,
            "created_by_john_version": _john_version(),
            "current_phase": "bootstrap",
            "session_metadata": {},
        }
        atomic_write_text(
            stage / "workspace.json",
            json.dumps(workspace_state, indent=2) + "\n",
        )

        if john_dir.exists():
            john_dir.rename(backup)
        stage.rename(john_dir)
        published = True

        plan_path = cwd / "PLAN.md"
        plan_written = not plan_path.exists() or args.force
        if plan_written:
            if prior_plan_existed:
                prior_plan = plan_path.read_text(encoding="utf-8")
            atomic_write_text(plan_path, plan_body)

        claude_path = cwd / "CLAUDE.md"
        claude_written = not claude_path.exists()
        if claude_written:
            atomic_write_text(claude_path, claude_body)
            created_files.append(claude_path)

        agents_path = cwd / "AGENTS.md"
        agents_written = not agents_path.exists()
        if agents_written:
            atomic_write_text(agents_path, agents_body)
            created_files.append(agents_path)

        if templates_active is not None:
            wf_src = templates_active / "workflows"
            if wf_src.is_dir():
                wf_dest = cwd / ".claude" / "workflows"
                for wf in sorted(wf_src.iterdir()):
                    if not wf.is_file():
                        continue
                    target = wf_dest / wf.name
                    if target.exists():
                        workflows_skipped.append(wf.name)
                        continue
                    atomic_write_text(target, wf.read_text(encoding="utf-8"))
                    created_files.append(target)
                    workflows_installed.append(wf.name)

        codex_agent_src = Path(__file__).resolve().parent.parent / "codex" / "agents"
        if codex_agent_src.is_dir():
            reject_tree_symlinks(codex_agent_src, label="shipped Codex agents")
            codex_agent_dest = cwd / ".codex" / "agents"
            for source in sorted(codex_agent_src.glob("*.toml")):
                validate_template_slug(source.stem, field="Codex agent name")
                target = codex_agent_dest / source.name
                if target.exists():
                    codex_agents_skipped.append(source.name)
                    continue
                atomic_write_text(target, source.read_text(encoding="utf-8"))
                created_files.append(target)
                codex_agents_installed.append(source.name)

        if backup.exists():
            shutil.rmtree(backup)
        if input_preserved:
            sys.stderr.write(
                "NOTE: existing .john/input/ contents were preserved across --force.\n"
            )
    except Exception as exc:
        for created in reversed(created_files):
            created.unlink(missing_ok=True)
        plan_path = cwd / "PLAN.md"
        if prior_plan_existed and prior_plan is not None:
            atomic_write_text(plan_path, prior_plan)
        elif not prior_plan_existed:
            plan_path.unlink(missing_ok=True)
        if published and john_dir.exists():
            shutil.rmtree(john_dir, ignore_errors=True)
        if backup.exists() and not john_dir.exists():
            backup.rename(john_dir)
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
        err(f"Workspace initialization failed without changing prior state: {exc}")
        return

    emit(
        {
            "project_root": str(cwd),
            "john_dir": ".john",
            "plan_md": "PLAN.md",
            "plan_md_written": plan_written,
            "plan_md_source": plan_source,
            "claude_md": "CLAUDE.md" if claude_path.exists() else None,
            "claude_md_written": claude_written,
            "agents_md": "AGENTS.md" if agents_path.exists() else None,
            "agents_md_written": agents_written,
            "claude_addon_appended": claude_written and template_claude_addon is not None,
            "project_addon_applied": project_addon is not None,
            "agents_addon_appended": agents_written and template_agents_addon is not None,
            "templates_active_used": templates_active is not None
            and any(
                value is not None
                for value in (
                    template_plan_md,
                    project_addon,
                    template_claude_addon,
                    template_agents_addon,
                )
            ),
            "workflows_installed": workflows_installed,
            "workflows_skipped": workflows_skipped,
            "codex_agents_installed": codex_agents_installed,
            "codex_agents_skipped": codex_agents_skipped,
            "copied_input": copied,
            "input_preserved": input_preserved,
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
        raw = Path(override).expanduser()
        if raw.is_symlink():
            raise ValueError(f"active template root may not be a symlink: {raw}")
        p = raw.resolve()
        return p if p.is_dir() else None

    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin_root:
        raw = Path(plugin_root).expanduser()
        if raw.is_symlink():
            raise ValueError(f"plugin trust boundary may not be a symlink: {raw}")
        p = raw.resolve() / "templates-active"
        if p.is_symlink():
            raise ValueError(f"active template root may not be a symlink: {p}")
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
