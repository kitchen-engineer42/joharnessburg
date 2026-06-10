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
import sys
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path


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
            if not is_excluded(root):
                yield root, str(root.relative_to(project_root))
            continue
        for path in root.rglob("*"):
            if any(part in EXCLUDE_NAMES for part in path.parts):
                continue
            if is_excluded(path):
                continue
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

    cwd = Path.cwd()
    john_dir = cwd / ".john"

    if not john_dir.exists():
        err(
            f"No .john/ directory found in {cwd}. Nothing to archive.",
            exit_code=1,
        )
        return

    if args.output:
        out_path = args.output.expanduser().resolve()
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
    roots = [
        cwd / "PLAN.md",
        cwd / "CLAUDE.md",
        cwd / "AGENTS.md",
        cwd / ".claude" / "skills",
        cwd / ".agents" / "skills",
        john_dir,
    ]

    file_count = 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path, arcname in iter_files_for_archive(roots, cwd):
            zf.write(file_path, arcname=arcname)
            file_count += 1

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
