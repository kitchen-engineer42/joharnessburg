#!/usr/bin/env python3
"""Layout-aware inventory shared by John status and reducer verification."""

from __future__ import annotations

from pathlib import Path


def disk_entry_ids(knowledge_dir: Path) -> set[str]:
    """Return entry IDs for flat Markdown and nested category layouts.

    A directory with a direct regular file is one entry; its nested assets are
    internal. A directory with no direct files is a category and is traversed.
    Top-level Markdown files are flat entries.
    """
    ids: set[str] = set()
    if not knowledge_dir.is_dir():
        return ids

    def walk(directory: Path, *, top: bool) -> None:
        for child in sorted(directory.iterdir()):
            if child.name.startswith(".") or child.name == "_quarantine":
                continue
            if child.is_symlink():
                raise ValueError(
                    f"knowledge inventory does not follow symlinks: {child}"
                )
            if child.is_file():
                if top and child.suffix == ".md":
                    ids.add(child.stem)
                continue
            if child.is_dir():
                direct_files = [
                    item
                    for item in child.iterdir()
                    if item.is_file()
                    and not item.is_symlink()
                    and not item.name.startswith(".")
                ]
                if direct_files:
                    ids.add(child.name)
                else:
                    walk(child, top=False)

    walk(knowledge_dir, top=True)
    return ids
