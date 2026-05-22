#!/usr/bin/env python3
"""Fold append-only events for a phase into canonical state.

Reads all `.json` files under `<cwd>/.john/events/<phase>/`, sorts them
deterministically, and writes a canonical state file at
`<cwd>/.john/checkpoints/<phase>/state.json`. Idempotent — running twice
on the same event set produces identical output.

The default fold is **generic**: collects events into a sorted list
without phase-specific semantics. Phase-specific fold logic (e.g.,
deduplicating extraction entries by ID, tallying QC pass/fail) lives in
templates or M3+ phase skills. M2 ships the generic fold; templates can
ship their own reducer that calls this one or replaces it entirely.

This script runs in **layer-2 sessions** inside the user's project.

Exit codes:
  0  success
  1  expected failure (no .john/, no events for phase)
  2  unexpected exception
"""

import argparse
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path


def emit(payload, success=True, exit_code=0):
    payload["success"] = success
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()
    sys.exit(exit_code)


def err(msg, exit_code=1):
    sys.stderr.write(msg + "\n")
    emit({"error": msg}, success=False, exit_code=exit_code)


def load_events(phase_dir: Path):
    """Yield (event, source_path) for every JSON file under phase_dir. Skips malformed files with a warning."""
    for evt_file in phase_dir.rglob("*.json"):
        if not evt_file.is_file():
            continue
        try:
            data = json.loads(evt_file.read_text())
        except json.JSONDecodeError as exc:
            sys.stderr.write(
                f"WARN: skipping malformed event file {evt_file}: {exc}\n"
            )
            continue
        yield data, evt_file


def reduce_phase(phase_dir: Path, project_root: Path):
    """Read all events under phase_dir, sort deterministically, return canonical state dict."""
    events = []
    malformed = 0
    seen = 0
    for data, src in load_events(phase_dir):
        seen += 1
        if isinstance(data, dict):
            # Annotate with relative source path for traceability
            data = dict(data)  # avoid mutating the on-disk content if re-read
            data["_source_file"] = str(src.relative_to(project_root))
        else:
            sys.stderr.write(
                f"WARN: event file {src} is not a JSON object; wrapping in payload\n"
            )
            data = {"_payload": data, "_source_file": str(src.relative_to(project_root))}
        events.append(data)

    # Deterministic sort. Primary: timestamp (lexicographic ISO 8601 sorts correctly).
    # Secondary: _source_file (stable tiebreaker for identical timestamps + clock skew).
    def sort_key(e):
        ts = e.get("timestamp", "") if isinstance(e, dict) else ""
        src = e.get("_source_file", "") if isinstance(e, dict) else ""
        return (ts, src)

    events.sort(key=sort_key)

    state = {
        "phase": phase_dir.name,
        "reduced_at": datetime.now(timezone.utc).isoformat(),
        "event_count": len(events),
        "events": events,
    }
    return state, seen, malformed


def main():
    parser = argparse.ArgumentParser(
        description="Fold a phase's event log into canonical state.",
    )
    parser.add_argument(
        "phase",
        help="Phase name (matches directory under .john/events/). e.g., 'extract'",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute and print state to stdout but do not write the checkpoint file.",
    )
    args = parser.parse_args()

    cwd = Path.cwd()
    john_dir = cwd / ".john"

    if not john_dir.exists():
        err(
            f"No .john/ directory found in {cwd}. "
            f"Run /joharnessburg-init first.",
            exit_code=1,
        )
        return

    phase_dir = john_dir / "events" / args.phase
    if not phase_dir.exists():
        err(
            f"No events directory for phase '{args.phase}'. "
            f"Expected: {phase_dir}",
            exit_code=1,
        )
        return

    state, seen, _ = reduce_phase(phase_dir, cwd)

    checkpoint_dir = john_dir / "checkpoints" / args.phase
    state_file = checkpoint_dir / "state.json"

    if not args.dry_run:
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(state, indent=2) + "\n")

    emit(
        {
            "phase": args.phase,
            "events_seen": seen,
            "events_folded": state["event_count"],
            "state_file": str(state_file.relative_to(cwd)) if not args.dry_run else None,
            "dry_run": args.dry_run,
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
