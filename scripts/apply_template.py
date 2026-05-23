#!/usr/bin/env python3
"""Apply a John template as a diff onto a copy of the joharnessburg install.

v0.1.7 template architecture:
- Templates are diffs to original John, not session-time overlays.
- This script merges a template's contents (overrides + additive skills/scripts/agents
  + _delete list) onto a snapshot of the joharnessburg plugin, producing a new
  ready-to-run plugin at `~/.claude/plugins/joharnessburg-applied/<template-name>/`.
- After running, the user launches Claude Code with:
    claude --plugin-dir ~/.claude/plugins/joharnessburg-applied/<template-name>/
  The new plugin IS John for that session — no second-class template skills, no
  SessionStart-time content surfacing.

Reset: delete the merged dir (or run `reset_john.py`).

Switching templates: refuses unless --reset-all flag passed; user must explicitly
clear the prior applied template first.

This script runs in **layer-1** (your dev workspace, not in a layer-2 session).

Exit codes:
  0  success
  1  expected failure (template missing, john install missing, refuses switch)
  2  unexpected exception
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path


def resolve_output_parent(override: str = None) -> Path:
    """Where applied-template merged dirs live.

    Resolution: --output CLI arg (used directly, full path) overrides this entirely.
    Otherwise: $JOHN_APPLIED_PARENT env > default `~/.claude/plugins/joharnessburg-applied/`.
    """
    if override:
        return Path(override).expanduser().resolve()
    env = os.environ.get("JOHN_APPLIED_PARENT")
    if env:
        return Path(env).expanduser().resolve()
    return Path.home() / ".claude" / "plugins" / "joharnessburg-applied"


DEFAULT_OUTPUT_PARENT = resolve_output_parent()


def emit(payload, success=True, exit_code=0):
    payload["success"] = success
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    sys.stdout.flush()
    sys.exit(exit_code)


def err(msg, exit_code=1):
    sys.stderr.write(msg + "\n")
    emit({"error": msg}, success=False, exit_code=exit_code)


def resolve_john_install() -> Path | None:
    """Find the active joharnessburg install via Claude Code's installed_plugins.json."""
    registry = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
    if not registry.exists():
        return None
    try:
        data = json.loads(registry.read_text())
    except json.JSONDecodeError:
        return None
    plugins = data.get("plugins", {})
    for key, entries in plugins.items():
        if not key.startswith("joharnessburg"):
            continue
        if not isinstance(entries, list) or not entries:
            continue
        install_path = entries[0].get("installPath")
        if install_path and Path(install_path).is_dir():
            return Path(install_path)
    return None


def list_applied_templates(output_parent: Path) -> list[Path]:
    if not output_parent.is_dir():
        return []
    return sorted(
        [d for d in output_parent.iterdir() if d.is_dir()],
        key=lambda p: p.name,
    )


def load_template_json(template_root: Path) -> dict:
    tj = template_root / "template.json"
    if not tj.exists():
        return {}
    try:
        return json.loads(tj.read_text())
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"WARN: template.json is not valid JSON: {exc}\n")
        return {}


def copy_tree_overlay(src: Path, dst: Path) -> list[str]:
    """Copy src/* over dst/*. Returns list of relative paths that were copied (for the manifest)."""
    copied: list[str] = []
    if not src.is_dir():
        return copied
    for root, _dirs, files in os.walk(src):
        root_p = Path(root)
        rel_dir = root_p.relative_to(src)
        for name in files:
            src_file = root_p / name
            dst_file = dst / rel_dir / name
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)
            copied.append(str((rel_dir / name)))
    return copied


def apply_overrides(output_root: Path, template_root: Path) -> list[str]:
    """skills/_override/<name>/SKILL.md (+ references/) → output/skills/<name>/.

    The override REPLACES the core skill: deletes the existing skill dir first.
    """
    overridden: list[str] = []
    override_dir = template_root / "skills" / "_override"
    if not override_dir.is_dir():
        return overridden
    for skill_dir in sorted(override_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_name = skill_dir.name
        target = output_root / "skills" / skill_name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(skill_dir, target)
        overridden.append(skill_name)
    return overridden


def apply_deletes(output_root: Path, template_root: Path) -> list[str]:
    """skills/_delete (newline-delimited core skill names) → rm output/skills/<name>/."""
    deleted: list[str] = []
    delete_file = template_root / "skills" / "_delete"
    if not delete_file.exists():
        return deleted
    for line in delete_file.read_text().splitlines():
        name = line.strip()
        if not name or name.startswith("#"):
            continue
        target = output_root / "skills" / name
        if target.is_dir():
            shutil.rmtree(target)
            deleted.append(name)
        else:
            sys.stderr.write(f"WARN: _delete entry '{name}' not found in core skills; skipping.\n")
    return deleted


def apply_additive_skills(output_root: Path, template_root: Path) -> list[str]:
    """skills/<name>/ (NOT under _override/, not the _delete file) → output/skills/<name>/."""
    added: list[str] = []
    src_skills = template_root / "skills"
    if not src_skills.is_dir():
        return added
    for entry in sorted(src_skills.iterdir()):
        if entry.name in ("_override", "_delete"):
            continue
        if not entry.is_dir():
            continue
        target = output_root / "skills" / entry.name
        if target.exists():
            sys.stderr.write(
                f"WARN: additive skill '{entry.name}' would shadow an existing core skill. "
                f"To replace it intentionally, move it to skills/_override/. Skipping.\n"
            )
            continue
        shutil.copytree(entry, target)
        added.append(entry.name)
    return added


def apply_template_metadata(output_root: Path, template_root: Path) -> dict:
    """Copy claude_addon.md + plan_md_template.md into a templates-active/ subdir of the merged plugin."""
    meta = {}
    target_dir = output_root / "templates-active"
    target_dir.mkdir(parents=True, exist_ok=True)
    for fname in ("claude_addon.md", "plan_md_template.md"):
        src = template_root / fname
        if src.is_file():
            shutil.copy2(src, target_dir / fname)
            meta[fname] = str((target_dir / fname).relative_to(output_root))
    return meta


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Apply a John template as a diff onto a copy of the joharnessburg install.",
    )
    parser.add_argument(
        "--template-root",
        required=True,
        help="Absolute path to the template directory (e.g., ~/.claude/plugins/joharnessburg-templates/doc-verification/).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help=f"Output dir for the merged plugin. Default: {DEFAULT_OUTPUT_PARENT}/<template-name>/",
    )
    parser.add_argument(
        "--john-install",
        default=None,
        help="Override the John install path (default: auto-discover via installed_plugins.json).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the output dir even if it already exists for this template.",
    )
    parser.add_argument(
        "--reset-all",
        action="store_true",
        help="Delete ALL existing applied templates before merging this one (use to switch templates).",
    )
    args = parser.parse_args(argv)

    template_root = Path(args.template_root).expanduser().resolve()
    if not template_root.is_dir():
        err(f"Template root does not exist or is not a directory: {template_root}")
        return

    template_meta = load_template_json(template_root)
    template_name = template_meta.get("name") or template_root.name

    # Resolve John install
    if args.john_install:
        john_install = Path(args.john_install).expanduser().resolve()
    else:
        john_install = resolve_john_install()
    if not john_install or not john_install.is_dir():
        err(
            "Could not resolve the joharnessburg plugin install. "
            "Ensure it's installed (`claude plugin install joharnessburg@joharnessburg`) "
            "or pass --john-install <path>.",
        )
        return

    # Resolve output
    output_parent = resolve_output_parent()
    output_root = (
        Path(args.output).expanduser().resolve()
        if args.output
        else output_parent / template_name
    )

    # Switch enforcement: refuse if a DIFFERENT applied template is present, unless --reset-all
    existing = list_applied_templates(output_parent)
    other_existing = [d for d in existing if d != output_root]
    if other_existing and not args.reset_all:
        names = ", ".join(d.name for d in other_existing)
        err(
            f"Cannot apply '{template_name}': other templates already applied ({names}). "
            f"Run with --reset-all to wipe them first, or delete them manually with reset_john.py.",
        )
        return
    if args.reset_all:
        for d in other_existing:
            shutil.rmtree(d)

    # Force-overwrite check for the SAME template
    if output_root.exists() and not args.force:
        # Without --force, refuse unless the existing is for the same template
        meta_file = output_root / ".applied-metadata.json"
        if meta_file.exists():
            try:
                existing_meta = json.loads(meta_file.read_text())
                if existing_meta.get("template_name") == template_name:
                    err(
                        f"Template '{template_name}' is already applied at {output_root}. "
                        f"Use --force to rebuild it.",
                    )
                    return
            except json.JSONDecodeError:
                pass
        # else: leftover dir with no metadata; refuse without --force
        err(f"Output dir {output_root} already exists. Use --force to overwrite.")
        return

    if output_root.exists():
        shutil.rmtree(output_root)

    # 1. Copy John install to output
    shutil.copytree(john_install, output_root, symlinks=True)

    # 2. Apply diff
    deleted = apply_deletes(output_root, template_root)
    overridden = apply_overrides(output_root, template_root)
    added = apply_additive_skills(output_root, template_root)

    # Also copy template's scripts/, commands/, agents/ (additive, NO override semantics here)
    additive_dirs_copied = {}
    for sub in ("scripts", "commands", "agents"):
        src = template_root / sub
        if src.is_dir():
            additive_dirs_copied[sub] = copy_tree_overlay(src, output_root / sub)

    template_metadata = apply_template_metadata(output_root, template_root)

    # 3. Write applied-metadata
    metadata = {
        "template_name": template_name,
        "template_version": template_meta.get("version"),
        "template_root_at_apply": str(template_root),
        "john_install_at_apply": str(john_install),
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "overrides_applied": overridden,
        "skills_deleted": deleted,
        "skills_added": added,
        "additive_dirs_copied": additive_dirs_copied,
        "template_files_copied": template_metadata,
    }
    (output_root / ".applied-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")

    emit(
        {
            "template_name": template_name,
            "template_version": template_meta.get("version"),
            "output_dir": str(output_root),
            "overrides_applied": overridden,
            "skills_deleted": deleted,
            "skills_added": added,
            "launch_command": f"claude --plugin-dir {output_root}",
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
