#!/usr/bin/env python3
"""Activate an applied John template through a project-local Codex marketplace."""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
import sys
import traceback
import uuid
from pathlib import Path

from path_safety import (
    atomic_write_text,
    ensure_contained,
    reject_tree_symlinks,
    validate_template_slug,
)


def emit(payload: dict, *, success: bool = True, exit_code: int = 0) -> None:
    payload["success"] = success
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    raise SystemExit(exit_code)


def fail(message: str) -> None:
    sys.stderr.write(message + "\n")
    emit({"error": message}, success=False, exit_code=1)


def load_object(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON object {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def git_exclude(project_root: Path) -> tuple[bool, str | None]:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-path", "info/exclude"],
            cwd=project_root,
            text=True,
            capture_output=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    if result.returncode != 0:
        return False, "not a Git worktree"
    exclude = Path(result.stdout.strip())
    if not exclude.is_absolute():
        exclude = project_root / exclude
    current = exclude.read_text(encoding="utf-8") if exclude.is_file() else ""
    lines = current.splitlines()
    if ".john-codex/" not in lines:
        body = current
        if body and not body.endswith("\n"):
            body += "\n"
        atomic_write_text(exclude, body + ".john-codex/\n")
    return True, None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--merged-plugin", required=True)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    raw_source = Path(args.merged_plugin).expanduser()
    if raw_source.is_symlink():
        fail(f"merged plugin may not be a symlink: {raw_source}")
        return
    source = raw_source.resolve()
    project_root = Path(args.project_root).expanduser().resolve()
    if not source.is_dir() or not project_root.is_dir():
        fail("merged plugin and project root must be existing directories")
        return
    try:
        reject_tree_symlinks(source, label="merged plugin")
        applied = load_object(source / ".applied-metadata.json")
        template = validate_template_slug(
            applied.get("template_name"), field="applied template name"
        )
        manifest = load_object(source / ".codex-plugin" / "plugin.json")
        if manifest.get("name") != "john":
            raise ValueError("merged plugin Codex manifest must have name 'john'")
    except ValueError as exc:
        fail(str(exc))
        return

    for boundary_name in (".john-codex", ".agents", ".codex"):
        boundary = project_root / boundary_name
        if boundary.is_symlink():
            fail(f"project trust boundary may not be a symlink: {boundary}")
            return
    generated_root = ensure_contained(
        project_root,
        project_root / ".john-codex" / "plugins",
        label="generated plugin root",
    )
    destination = ensure_contained(
        generated_root,
        generated_root / template,
        label="project-local generated plugin",
    )
    marketplace_path = ensure_contained(
        project_root,
        project_root / ".agents" / "plugins" / "marketplace.json",
        label="project marketplace",
    )
    marketplace_path.parent.mkdir(parents=True, exist_ok=True)
    marketplace = (
        load_object(marketplace_path)
        if marketplace_path.is_file()
        else {"name": "john-project", "interface": {"displayName": "John project"}, "plugins": []}
    )
    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list):
        fail(f"{marketplace_path} has a non-list plugins field")
        return

    listing_name = f"john-{template}"
    listing = {
        "name": listing_name,
        "source": {"source": "local", "path": f"./.john-codex/plugins/{template}"},
        "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        "category": "Developer Tools",
    }
    retained = [
        item
        for item in plugins
        if not (isinstance(item, dict) and item.get("name") == listing_name)
    ]
    marketplace["plugins"] = retained + [listing]

    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = destination.parent / f".{template}.stage-{uuid.uuid4().hex}"
    backup = destination.parent / f".{template}.backup-{uuid.uuid4().hex}"
    old_marketplace = marketplace_path.read_text(encoding="utf-8") if marketplace_path.is_file() else None
    published = False
    installed_agent_paths: list[Path] = []
    installed_agents: list[str] = []
    skipped_agents: list[str] = []
    try:
        shutil.copytree(source, stage)
        activation = {
            "template_name": template,
            "template_version": applied.get("template_version"),
            "source_john_version": manifest.get("version"),
            "managed_by": "john-codex-template-activation",
        }
        atomic_write_text(
            stage / ".codex-activation.json",
            json.dumps(activation, indent=2) + "\n",
        )
        if destination.exists():
            if not args.force:
                raise ValueError(
                    f"Codex activation already exists at {destination}; use --force to rebuild"
                )
            marker = destination / ".codex-activation.json"
            if not marker.is_file():
                raise ValueError(
                    f"refusing to replace unmarked directory: {destination}"
                )
            destination.rename(backup)
        stage.rename(destination)
        published = True
        atomic_write_text(
            marketplace_path,
            json.dumps(marketplace, indent=2, ensure_ascii=False) + "\n",
        )
        source_agents = destination / "codex" / "agents"
        if source_agents.is_dir():
            for source_agent in sorted(source_agents.glob("*.toml")):
                validate_template_slug(source_agent.stem, field="Codex agent name")
                target = ensure_contained(
                    project_root,
                    project_root / ".codex" / "agents" / source_agent.name,
                    label="project Codex agent",
                )
                if target.exists():
                    skipped_agents.append(source_agent.name)
                    continue
                atomic_write_text(target, source_agent.read_text(encoding="utf-8"))
                installed_agent_paths.append(target)
                installed_agents.append(source_agent.name)
        if backup.exists():
            shutil.rmtree(backup, ignore_errors=True)
    except Exception as exc:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
        if published and destination.exists():
            shutil.rmtree(destination, ignore_errors=True)
        if backup.exists() and not destination.exists():
            backup.rename(destination)
        if old_marketplace is None:
            marketplace_path.unlink(missing_ok=True)
        else:
            atomic_write_text(marketplace_path, old_marketplace)
        for installed_agent in installed_agent_paths:
            installed_agent.unlink(missing_ok=True)
        fail(f"Codex activation failed without changing prior state: {exc}")
        return

    exclude_updated, exclude_warning = git_exclude(project_root)
    instructions = [
        f"cd {shlex.quote(str(project_root))}",
        "codex plugin marketplace add .",
        f"codex plugin add {listing_name}@{marketplace.get('name', 'john-project')}",
        "In the Codex App plugin UI, disable john@joharnessburg for this project session; do not run vanilla and applied John together.",
        f"In the Codex App plugin UI, enable {listing_name}@{marketplace.get('name', 'john-project')} for this project.",
        "Restart Codex in this project so plugin skills, hooks, and agents reload.",
    ]
    emit(
        {
            "template_name": template,
            "plugin_dir": str(destination.relative_to(project_root)),
            "marketplace": str(marketplace_path.relative_to(project_root)),
            "listing_name": listing_name,
            "codex_agents_installed": installed_agents,
            "codex_agents_skipped": skipped_agents,
            "git_exclude_updated": exclude_updated,
            "git_exclude_warning": exclude_warning,
            "vanilla_exclusion_required": True,
            "instructions": instructions,
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
