#!/usr/bin/env python3
"""Shared trust-boundary validation and atomic filesystem helpers for John."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path


TEMPLATE_SLUG_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
WORK_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*\Z")


def validate_template_slug(value: object, *, field: str = "name") -> str:
    """Return a safe template/skill slug or raise ValueError."""
    if not isinstance(value, str) or not TEMPLATE_SLUG_RE.fullmatch(value):
        raise ValueError(
            f"invalid {field} {value!r}: use lowercase letters/digits separated "
            "by single hyphens"
        )
    return value


def validate_work_id(value: object, *, field: str = "id") -> str:
    """Return a safe phase/work-unit identifier or raise ValueError."""
    if not isinstance(value, str) or not WORK_ID_RE.fullmatch(value):
        raise ValueError(
            f"invalid {field} {value!r}: use letters, digits, '_' or '-', and "
            "start with a letter or digit"
        )
    return value


def ensure_contained(
    root: Path,
    candidate: Path,
    *,
    label: str = "path",
    allow_root: bool = False,
) -> Path:
    """Resolve candidate and prove it remains within resolved root."""
    root_resolved = root.expanduser().resolve()
    candidate_resolved = candidate.expanduser().resolve(strict=False)
    if candidate_resolved == root_resolved:
        if allow_root:
            return candidate_resolved
        raise ValueError(f"unsafe {label}: target is the trust-boundary root")
    if not candidate_resolved.is_relative_to(root_resolved):
        raise ValueError(
            f"unsafe {label}: {candidate} resolves outside {root_resolved}"
        )
    return candidate_resolved


def reject_tree_symlinks(root: Path, *, label: str = "tree") -> None:
    """Reject every symlink below a trust-boundary root.

    John copies local templates, plugin installs, corpora, and archives. Treating
    symlinks as data would either dereference external content or publish a link
    whose target changes after validation, so these boundaries accept regular
    files and directories only.
    """
    if root.is_symlink():
        raise ValueError(f"unsafe {label}: root is a symlink: {root}")
    if not root.exists():
        return
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        base = Path(directory)
        for name in (*dirnames, *filenames):
            path = base / name
            if path.is_symlink():
                raise ValueError(f"unsafe {label}: symlink is not allowed: {path}")


def reject_path_symlinks(root: Path, candidate: Path, *, label: str = "path") -> None:
    """Reject symlinks in existing components from root through candidate.

    Resolved containment prevents escape, while this check also rejects links
    that happen to point elsewhere inside the same trust boundary.
    """
    lexical_root = Path(os.path.abspath(root.expanduser()))
    lexical_candidate = Path(os.path.abspath(candidate.expanduser()))
    try:
        relative = lexical_candidate.relative_to(lexical_root)
    except ValueError as exc:
        raise ValueError(f"unsafe {label}: target is outside the trust boundary") from exc
    current = lexical_root
    if current.is_symlink():
        raise ValueError(f"unsafe {label}: symlink is not allowed: {current}")
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"unsafe {label}: symlink is not allowed: {current}")


def atomic_write_text(
    path: Path,
    text: str,
    *,
    encoding: str = "utf-8",
    mode: int | None = None,
) -> None:
    """Write text through a same-directory temporary file and os.replace()."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp = Path(temp_name)
    try:
        if mode is not None:
            os.fchmod(fd, mode)
        with os.fdopen(fd, "w", encoding=encoding) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        temp.unlink(missing_ok=True)
        raise
