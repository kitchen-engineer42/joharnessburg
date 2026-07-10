#!/usr/bin/env python3
"""Bundle the John workspace at cwd into a release zip.

Includes: PLAN.md, CLAUDE.md, AGENTS.md, .claude/skills/,
.agents/skills/, and .john/ (working state). Excludes: .git, .DS_Store,
__pycache__, *.pyc, node_modules.

This script runs in **layer-2 sessions** inside the user's project. The
zip lands at `<cwd>/<label>.zip` by default; use --output to override.

Exit codes:
  0  success
  1  expected failure (no .john/, output path already exists without --force)
  2  unexpected exception
"""

import argparse
import json
import os
import sys
import traceback
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from john_paths import find_john_root
from path_safety import ensure_contained, reject_tree_symlinks


EXCLUDE_NAMES = {".git", ".DS_Store", "__pycache__", "node_modules"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}


def emit(payload, success=True, exit_code=0):
    payload["success"] = success
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()
    sys.exit(exit_code)


def err(msg, exit_code=1):
    sys.stderr.write(msg + "\n")
    emit({"error": msg}, success=False, exit_code=exit_code)


def is_excluded(path: Path) -> bool:
    if path.name in EXCLUDE_NAMES:
        return True
    if path.suffix in EXCLUDE_SUFFIXES:
        return True
    return False


def iter_files_for_archive(roots, project_root: Path):
    """Yield (file_path, arcname) tuples for files to include in the zip."""
    for root in roots:
        if not root.exists():
            continue
        if root.is_file():
            if root.is_symlink():
                raise ValueError(f"archive source may not be a symlink: {root}")
            if not is_excluded(root):
                yield root, str(root.relative_to(project_root))
            continue
        for path in root.rglob("*"):
            if any(part in EXCLUDE_NAMES for part in path.parts):
                continue
            if is_excluded(path):
                continue
            if path.is_symlink():
                raise ValueError(f"archive source may not be a symlink: {path}")
            if path.is_file():
                yield path, str(path.relative_to(project_root))


def main():
    parser = argparse.ArgumentParser(
        description="Bundle the John workspace into a release zip.",
    )
    parser.add_argument(
        "label",
        nargs="?",
        default=None,
        help="Label for the archive (used in default filename). Defaults to a timestamp.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Explicit output zip path. Overrides label-based default.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing output file.",
    )
    args = parser.parse_args()

    invoked_from = Path.cwd().resolve()
    cwd = find_john_root(invoked_from)
    if cwd is None:
        err(
            f"No .john/ directory found at or above {invoked_from}. Nothing to archive.",
            exit_code=1,
        )
        return
    john_dir = cwd / ".john"

    if args.output:
        raw_output = args.output.expanduser()
        if raw_output.is_symlink():
            err(f"Output archive may not be a symlink: {raw_output}")
            return
        out_path = raw_output.resolve()
    else:
        label = args.label or datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        safe_label = "".join(c if c.isalnum() or c in "-_." else "_" for c in label)
        out_path = cwd / f"john-archive-{safe_label}.zip"

    if out_path.exists() and not args.force:
        err(
            f"Output already exists: {out_path}. Use --force to overwrite.",
            exit_code=1,
        )
        return

    # Roots to include
    file_roots = [
        cwd / "PLAN.md",
        cwd / "CLAUDE.md",
        cwd / "AGENTS.md",
    ]
    directory_roots = [
        cwd / ".claude" / "skills",
        cwd / ".agents" / "skills",
        john_dir,
    ]
    roots = file_roots + directory_roots

    try:
        for root in roots:
            if root.exists():
                if root.is_dir():
                    reject_tree_symlinks(root, label="archive source")
                elif root.is_symlink():
                    raise ValueError(f"archive source may not be a symlink: {root}")
            resolved_root = root.resolve(strict=False)
            if out_path == resolved_root or (
                root in directory_roots and out_path.is_relative_to(resolved_root)
            ):
                raise ValueError(
                    f"output archive must be outside included source root: {root}"
                )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        ensure_contained(out_path.parent, out_path, label="archive output")
    except ValueError as exc:
        err(str(exc))
        return

    file_count = 0
    staged = out_path.parent / f".{out_path.name}.tmp-{uuid.uuid4().hex}"
    try:
        with zipfile.ZipFile(staged, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for file_path, arcname in iter_files_for_archive(roots, cwd):
                zf.write(file_path, arcname=arcname)
                file_count += 1
        with staged.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(staged, out_path)
    except Exception:
        staged.unlink(missing_ok=True)
        raise

    emit(
        {
            "project_root": str(cwd),
            "archive_path": str(out_path),
            "file_count": file_count,
            "size_bytes": out_path.stat().st_size,
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
