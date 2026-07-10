#!/usr/bin/env python3
"""Atomically append one typed JSON event to the nearest John workspace.

The event body is read from stdin. John owns the audit envelope and filename,
so retries and concurrent agents never overwrite prior history.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

from john_paths import find_john_root
from path_safety import (
    atomic_write_text,
    ensure_contained,
    reject_path_symlinks,
    validate_work_id,
)


def emit(payload: dict, *, success: bool = True, exit_code: int = 0) -> None:
    payload["success"] = success
    sys.stdout.write(json.dumps(payload) + "\n")
    raise SystemExit(exit_code)


def fail(message: str, *, exit_code: int = 1) -> None:
    sys.stderr.write(message + "\n")
    emit({"error": message}, success=False, exit_code=exit_code)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--audit-run-id", required=True)
    parser.add_argument(
        "--work-unit-id",
        default=None,
        help="Optional chunk/work-unit subdirectory under the phase event log.",
    )
    args = parser.parse_args()

    try:
        phase = validate_work_id(args.phase, field="phase")
        agent_id = validate_work_id(args.agent_id, field="agent_id")
        audit_run_id = validate_work_id(args.audit_run_id, field="audit_run_id")
        work_unit_id = (
            validate_work_id(args.work_unit_id, field="work_unit_id")
            if args.work_unit_id is not None
            else None
        )
    except ValueError as exc:
        fail(str(exc))
        return

    root = find_john_root(Path.cwd())
    if root is None:
        fail(f"No .john/ directory found at or above {Path.cwd()}")
        return
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        fail(f"stdin is not valid JSON: {exc}")
        return
    if not isinstance(event, dict):
        fail("stdin event must be one JSON object")
        return
    if not isinstance(event.get("event_type"), str) or not event["event_type"]:
        fail("event_type is required and must be a non-empty string")
        return
    event_chunk = event.get("chunk_id") or event.get("work_unit_id")
    if work_unit_id and event_chunk is not None and event_chunk != work_unit_id:
        fail(
            f"work-unit mismatch: CLI has {work_unit_id!r}, event has {event_chunk!r}"
        )
        return

    event_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    event.update(
        {
            "event_id": event_id,
            "timestamp": timestamp,
            "agent_id": agent_id,
            "audit_run_id": audit_run_id,
        }
    )
    try:
        events_root = root / ".john" / "events"
        raw_target_dir = (
            events_root / phase / work_unit_id if work_unit_id else events_root / phase
        )
        reject_path_symlinks(root, raw_target_dir, label="event output directory")
        target_dir = ensure_contained(
            events_root,
            raw_target_dir,
            label="event output directory",
        )
        compact = timestamp.replace("-", "").replace(":", "").replace(".", "")
        filename = f"{agent_id}-{audit_run_id}-{compact}-{event_id}.json"
        target = ensure_contained(target_dir, target_dir / filename, label="event file")
        atomic_write_text(target, json.dumps(event, ensure_ascii=False, indent=2) + "\n")
    except (OSError, ValueError) as exc:
        fail(str(exc))
        return
    emit(
        {
            "event_id": event_id,
            "event_file": str(target.relative_to(root)),
            "timestamp": timestamp,
        }
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        sys.stderr.write(traceback.format_exc())
        emit(
            {"error": f"unexpected exception: {exc}"},
            success=False,
            exit_code=2,
        )
