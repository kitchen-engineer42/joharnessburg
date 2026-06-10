#!/usr/bin/env python3
"""Apply a John template as a diff onto a copy of the joharnessburg install.

Template architecture:
- Templates are diffs to original John, not session-time overlays.
- This script merges a template's contents (overrides + additive skills/scripts/agents
  + _delete list) onto a snapshot of the joharnessburg plugin, producing a new
  ready-to-run plugin at `~/.claude/plugins/joharnessburg-applied/<template-name>/`.
- After running, the user launches Claude Code with:
    claude --plugin-dir ~/.claude/plugins/joharnessburg-applied/<template-name>/
  The new plugin IS John for that session — no second-class template skills.

Reset: delete the merged dir (or run `reset_john.py`).

Multiple templates may be applied side-by-side (one merged dir each); re-applying
the SAME template refuses without --force. `--reset-all` clears the other applied
dirs first, for users who want a clean slate.

Exit codes:
  0  success
  1  expected failure (template missing, john install missing, refuses rebuild
     without --force)
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


# Core skills that are load-bearing for John itself (not domain skills that
# templates legitimately replace). Deleting one is allowed — warn-don't-block —
# but it must be loud and carry a stated reason in the _delete file.
# NOTE: hamster's package_template.py keeps an annotated copy of these names;
# this dict is authoritative.
CORE_SKILLS = {
    "using-john": "top-level orientation; pinned by the SessionStart hook",
    "ralph-loop": "the iteration engine the whole session runs on",
    "event-log-and-reducer": "the subagent coordination contract; reduce_events.py's documentation",
    "workspace-discipline": "the disk-is-truth operating contract",
    "context-management": "compaction survival for long sessions",
    "subagent-dispatch": "the vertical-axis fan-out mechanism",
}


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
    """Find the active joharnessburg install via Claude Code's installed_plugins.json.

    Resolution order:
    1. $JOHN_PLUGIN_INSTALL env var (used by tests; useful for power users with
       non-standard install layouts).
    2. ~/.claude/plugins/installed_plugins.json (Claude Code's registry).
    """
    env = os.environ.get("JOHN_PLUGIN_INSTALL")
    if env:
        p = Path(env).expanduser().resolve()
        return p if p.is_dir() else None

    registry = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
    if not registry.exists():
        return None
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    plugins = data.get("plugins", {})
    for key, entries in plugins.items():
        # The plugin is named `john` but ships from the `joharnessburg` marketplace,
        # so the registry key (e.g. "john@joharnessburg" or marketplace-scoped) still
        # contains "joharnessburg". Match on substring to be robust to key format.
        if "joharnessburg" not in key and "john" not in key:
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
        return json.loads(tj.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"WARN: template.json is not valid JSON: {exc}\n")
        return {}


def _parse_version(s: str) -> tuple | None:
    """'0.2.0' -> (0, 2, 0). None when not a dotted-numeric version."""
    try:
        return tuple(int(part) for part in s.strip().split("."))
    except (ValueError, AttributeError):
        return None


def check_version_pin(template_meta: dict, john_install: Path) -> dict | None:
    """Warn-only check of template.json's `requires_john` against the installed
    John version (from <john_install>/.claude-plugin/plugin.json).

    Spec grammar (deliberately minimal): `>=X.Y.Z` (at-least) or bare `X.Y.Z`
    (exact). Absent field -> None (silent skip; templates predating the field
    stay valid). Unparseable spec or undeterminable installed version -> soft
    warning, proceed. Unsatisfied -> prominent warning, STILL proceed.
    """
    spec = template_meta.get("requires_john")
    if not spec:
        return None

    installed = None
    pj = john_install / ".claude-plugin" / "plugin.json"
    try:
        installed = json.loads(pj.read_text(encoding="utf-8")).get("version")
    except (OSError, json.JSONDecodeError):
        pass
    if not installed:
        sys.stderr.write(
            f"WARN: could not determine the installed John version (no readable "
            f"{pj}); skipping the requires_john check.\n"
        )
        return {"checked": False, "requires_john": spec, "installed": None, "satisfied": None}

    spec_str = str(spec).strip()
    if spec_str.startswith(">="):
        wanted = _parse_version(spec_str[2:])
        op = ">="
    else:
        wanted = _parse_version(spec_str)
        op = "=="
    got = _parse_version(installed)
    if wanted is None or got is None:
        sys.stderr.write(
            f"WARN: cannot parse requires_john {spec_str!r} against installed "
            f"version {installed!r}; skipping the check.\n"
        )
        return {"checked": False, "requires_john": spec_str, "installed": installed, "satisfied": None}

    satisfied = (got >= wanted) if op == ">=" else (got == wanted)
    if not satisfied:
        sys.stderr.write(
            "\n"
            "================ VERSION PIN WARNING ================\n"
            f"This template declares requires_john: {spec_str}\n"
            f"but the installed John is version {installed}.\n"
            "The template was built against a different John layout and may\n"
            "misbehave. Proceeding anyway (warn-only).\n"
            "=====================================================\n\n"
        )
    return {"checked": True, "requires_john": spec_str, "installed": installed, "satisfied": satisfied}


def _skill_referrers(output_root: Path, skill_name: str) -> list[str]:
    """Remaining skills whose SKILL.md links [[skill_name]] — computed, not hardcoded."""
    needle = f"[[{skill_name}]]"
    referrers = []
    skills_dir = output_root / "skills"
    if not skills_dir.is_dir():
        return referrers
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        try:
            if needle in skill_md.read_text(encoding="utf-8"):
                referrers.append(skill_md.parent.name)
        except OSError:
            continue
    return referrers


def copy_tree_overlay(src: Path, dst: Path, mode: str = "replace") -> tuple[list[str], list[str]]:
    """Copy src/* over dst/*.

    Modes:
    - "replace" (default): overwrite same-path files. Used for `skills/_override/`
      subtrees where collision IS the point.
    - "additive_only": refuse to overwrite. On collision, skip the source file
      and record the relpath in the returned `collisions` list. Used for
      `scripts/`, `commands/`, `agents/` where the documented policy (per
      templates/README.md) is NOT-OVERRIDE — additive only.

    Returns (copied_relpaths, collisions). `collisions` is empty for mode="replace".
    """
    copied: list[str] = []
    collisions: list[str] = []
    if not src.is_dir():
        return copied, collisions
    for root, _dirs, files in os.walk(src):
        root_p = Path(root)
        rel_dir = root_p.relative_to(src)
        for name in files:
            src_file = root_p / name
            dst_file = dst / rel_dir / name
            relpath_str = str((rel_dir / name))
            if mode == "additive_only" and dst_file.exists():
                collisions.append(relpath_str)
                sys.stderr.write(
                    f"WARN: template '{src.parent.name if src.parent else src.name}' "
                    f"would overlay {relpath_str} over a core file; skipping. "
                    f"Use skills/_override/ for explicit overrides, or rename "
                    f"your file in the template.\n"
                )
                continue
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)
            copied.append(relpath_str)
    return copied, collisions


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


def apply_deletes(output_root: Path, template_root: Path) -> tuple[list[str], list[dict]]:
    """skills/_delete → rm output/skills/<name>/.

    Line format: `<skill-name>` or `<skill-name> # <reason>`. Full-line `#`
    comments are skipped. Deleting a CORE_SKILLS member is allowed but loud:
    it requires a stated same-line reason and the warning names the skill's
    load-bearing role plus the remaining skills that still reference it.
    Warn-don't-block, by design — deliberate trim-downs are legitimate.

    Returns (deleted_names, core_deletions) where each core deletion is
    {"skill", "reason", "referenced_by"}.
    """
    deleted: list[str] = []
    core_deletions: list[dict] = []
    delete_file = template_root / "skills" / "_delete"
    if not delete_file.exists():
        return deleted, core_deletions
    for line in delete_file.read_text(encoding="utf-8").splitlines():
        name, _, comment = line.partition("#")
        name = name.strip()
        reason = comment.strip() or None
        if not name:
            continue  # blank line or full-line comment
        target = output_root / "skills" / name
        if not target.is_dir():
            sys.stderr.write(f"WARN: _delete entry '{name}' not found in core skills; skipping.\n")
            continue
        shutil.rmtree(target)
        deleted.append(name)
        if name in CORE_SKILLS:
            referrers = _skill_referrers(output_root, name)
            lines = [
                "",
                "############ CORE SKILL DELETED ############",
                f"Template deletes core skill '{name}'.",
                f"  Load-bearing role: {CORE_SKILLS[name]}",
            ]
            if reason:
                lines.append(f"  Template's stated reason: {reason}")
            else:
                lines += [
                    "  NO REASON STATED. Core deletions should say why —",
                    f"  add a same-line comment in skills/_delete:",
                    f"      {name} # <why this template removes it>",
                ]
            if referrers:
                lines.append(
                    f"  Still referenced by remaining skills: {', '.join(referrers)}"
                )
            lines += [
                "Proceeding (warn-only) — verify the template replaces what this skill provided.",
                "############################################",
                "",
            ]
            sys.stderr.write("\n".join(lines))
            core_deletions.append(
                {"skill": name, "reason": reason, "referenced_by": referrers}
            )
    return deleted, core_deletions


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


def apply_template_workflows(output_root: Path, template_root: Path) -> list[str]:
    """Copy a template's workflows/ into templates-active/workflows/ in the merged plugin.

    Saved dynamic workflows are NOT a plugin-registered surface — Claude Code reads
    them from the project's `.claude/workflows/`, not from a plugin dir. So a
    template's workflows ride in templates-active/ alongside claude_addon.md /
    plan_md_template.md, and `/john:init` installs them into the project's
    `.claude/workflows/` at scaffold time (see init_workspace.py). This keeps the
    "templates-active is what init consumes" pattern consistent and means workflows
    only land where the runtime actually looks for them.
    """
    copied: list[str] = []
    src = template_root / "workflows"
    if not src.is_dir():
        return copied
    target_dir = output_root / "templates-active" / "workflows"
    target_dir.mkdir(parents=True, exist_ok=True)
    for entry in sorted(src.iterdir()):
        if entry.is_file():
            shutil.copy2(entry, target_dir / entry.name)
            copied.append(entry.name)
    return copied


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Apply a John template as a diff onto a copy of the joharnessburg install.",
    )
    parser.add_argument(
        "--template-root",
        required=True,
        help="Absolute path to the template directory (e.g., ~/.claude/plugins/joharnessburg-templates/your-template/).",
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
            "Ensure it's installed (`claude plugin install john@joharnessburg`) "
            "or pass --john-install <path>.",
        )
        return

    # Warn-only version pin (template.json requires_john vs installed version)
    version_check = check_version_pin(template_meta, john_install)

    # Resolve output
    output_parent = resolve_output_parent()
    output_root = (
        Path(args.output).expanduser().resolve()
        if args.output
        else output_parent / template_name
    )

    # Multi-applied policy:
    # Each applied template dir is an independent merged plugin; parallel Claude Code
    # sessions can point `--plugin-dir` at different applied dirs and run side-by-side
    # without interference (per-session isolation, no shared mutable runtime state).
    # So we DON'T refuse when other templates are already applied — we just allow.
    # `--reset-all` is still available for users who DO want a clean slate.
    if args.reset_all:
        existing = list_applied_templates(output_parent)
        other_existing = [d for d in existing if d != output_root]
        for d in other_existing:
            # Same provenance guard as reset_john.py: only delete dirs that
            # carry the applied-template marker, so a mis-set applied parent
            # (e.g. via $JOHN_APPLIED_PARENT) can't wipe unrelated directories.
            if not (d / ".applied-metadata.json").exists():
                sys.stderr.write(
                    f"WARN: --reset-all skipping {d}: no .applied-metadata.json "
                    f"marker (not an applied template).\n"
                )
                continue
            shutil.rmtree(d)

    # Force-overwrite check for the SAME template
    if output_root.exists() and not args.force:
        # Without --force, refuse unless the existing is for the same template
        meta_file = output_root / ".applied-metadata.json"
        if meta_file.exists():
            try:
                existing_meta = json.loads(meta_file.read_text(encoding="utf-8"))
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
        # Safety guard: with --force we are about to delete output_root. Only do
        # that when it is clearly an applied-template dir — under the applied
        # parent, or already carrying our provenance marker. This stops a stray
        # `--output ~/code/myproject --force` from wiping an unrelated directory.
        is_under_parent = output_parent in output_root.parents
        has_marker = (output_root / ".applied-metadata.json").exists()
        if not (is_under_parent or has_marker):
            err(
                f"Refusing to delete {output_root}: it is neither under the applied "
                f"parent ({output_parent}) nor an existing applied template "
                f"(no .applied-metadata.json). Point --output under {output_parent}, "
                f"or remove the directory yourself first.",
            )
            return
        shutil.rmtree(output_root)

    # 1. Copy John install to output
    shutil.copytree(john_install, output_root, symlinks=True)

    # 2. Apply diff
    deleted, core_deletions = apply_deletes(output_root, template_root)
    overridden = apply_overrides(output_root, template_root)
    added = apply_additive_skills(output_root, template_root)

    # Also copy template's scripts/, commands/, agents/ (additive-only — NOT
    # an override surface; collisions with core files are skipped + warned).
    additive_dirs_copied: dict = {}
    additive_collisions: dict = {}
    for sub in ("scripts", "commands", "agents"):
        src = template_root / sub
        if src.is_dir():
            copied_paths, collisions = copy_tree_overlay(
                src, output_root / sub, mode="additive_only"
            )
            additive_dirs_copied[sub] = copied_paths
            if collisions:
                additive_collisions[sub] = collisions

    template_metadata = apply_template_metadata(output_root, template_root)
    workflows_copied = apply_template_workflows(output_root, template_root)

    # 3. Write applied-metadata
    metadata = {
        "template_name": template_name,
        "template_version": template_meta.get("version"),
        "template_root_at_apply": str(template_root),
        "john_install_at_apply": str(john_install),
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "overrides_applied": overridden,
        "skills_deleted": deleted,
        "core_skill_deletions": core_deletions,
        "skills_added": added,
        "additive_dirs_copied": additive_dirs_copied,
        "additive_collisions": additive_collisions,
        "template_files_copied": template_metadata,
        "workflows_copied": workflows_copied,
        "version_check": version_check,
    }
    (output_root / ".applied-metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )

    launch_command = f"claude --plugin-dir {output_root}"
    sys.stderr.write(
        f"\n✓ Template applied: {template_name}\n"
        f"  Merged plugin: {output_root}\n"
        f"  Launch a new Claude Code session with:\n"
        f"      {launch_command}\n\n"
    )
    sys.stderr.flush()

    emit(
        {
            "template_name": template_name,
            "template_version": template_meta.get("version"),
            "output_dir": str(output_root),
            "overrides_applied": overridden,
            "skills_deleted": deleted,
            "core_skill_deletions": core_deletions,
            "skills_added": added,
            "additive_collisions": additive_collisions,
            "workflows_copied": workflows_copied,
            "version_check": version_check,
            "launch_command": launch_command,
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
