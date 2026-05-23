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
    """Yield (event, source_path) for every JSON file under phase_dir. Quarantines malformed files.

    Skips files inside `_quarantine/` subdirs (idempotent re-runs).

    On JSONDecodeError: moves the file to `phase_dir/_quarantine/<orig-relpath>` and
    writes a `.parse_error.txt` sibling. Yields ('__quarantined__', src) sentinel so
    callers can count quarantined events without unpacking them.
    """
    quarantine_dir = phase_dir / "_quarantine"
    for evt_file in phase_dir.rglob("*.json"):
        if not evt_file.is_file():
            continue
        # Skip files already in _quarantine/ to keep re-runs idempotent
        try:
            evt_file.relative_to(quarantine_dir)
            continue
        except ValueError:
            pass

        try:
            data = json.loads(evt_file.read_text())
        except json.JSONDecodeError as exc:
            # Quarantine: preserve relative path under phase_dir so the user can trace
            # where the bad event came from.
            rel = evt_file.relative_to(phase_dir)
            dest = quarantine_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                evt_file.rename(dest)
                (dest.parent / f"{dest.name}.parse_error.txt").write_text(
                    f"JSONDecodeError at {datetime.now(timezone.utc).isoformat()}:\n{exc}\n"
                )
                sys.stderr.write(
                    f"WARN: quarantined malformed event {evt_file} -> {dest}\n"
                )
            except OSError as move_exc:
                # If rename fails (e.g., permission), at least log it
                sys.stderr.write(
                    f"WARN: could not quarantine {evt_file}: {move_exc} (original parse error: {exc})\n"
                )
            yield "__quarantined__", evt_file
            continue
        yield data, evt_file


def reduce_phase(phase_dir: Path, project_root: Path):
    """Read all events under phase_dir, sort deterministically, return canonical state dict.

    Returns (state, events_seen, events_quarantined).
    """
    events = []
    quarantined = 0
    seen = 0
    for data, src in load_events(phase_dir):
        seen += 1
        if data == "__quarantined__":
            quarantined += 1
            continue
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
    # Wrapping above guarantees every entry is a dict, so no isinstance guard needed here.
    def sort_key(e):
        assert isinstance(e, dict), "load_events / reduce_phase wrapping invariant violated"
        return (e.get("timestamp", ""), e.get("_source_file", ""))

    events.sort(key=sort_key)

    state = {
        "phase": phase_dir.name,
        "reduced_at": datetime.now(timezone.utc).isoformat(),
        "event_count": len(events),
        "events_quarantined": quarantined,
        "events": events,
    }
    return state, seen, quarantined


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

    state, seen, quarantined = reduce_phase(phase_dir, cwd)

    checkpoint_dir = john_dir / "checkpoints" / args.phase
    state_file = checkpoint_dir / "state.json"

    if not args.dry_run:
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(state, indent=2) + "\n")

    if quarantined:
        sys.stderr.write(
            f"NOTE: {quarantined} event file(s) quarantined under "
            f"{phase_dir / '_quarantine'}/ — inspect *.parse_error.txt for details.\n"
        )

    emit(
        {
            "phase": args.phase,
            "events_seen": seen,
            "events_folded": state["event_count"],
            "events_quarantined": quarantined,
            "quarantine_dir": str((phase_dir / "_quarantine").relative_to(cwd)) if quarantined else None,
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
