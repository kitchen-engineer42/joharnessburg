#!/usr/bin/env python3
"""PreCompact hook: write a structured snapshot before context compaction.

Wired in hooks/hooks.json for the PreCompact event. Snapshots the user's
workspace state (workspace.json contents + PLAN.md path + recent events)
to `<cwd>/.john/checkpoints/precompact-<ts>.json` so post-compaction
recovery can read it back if needed.

No-op when there's no `.john/` directory.

Does NOT block compaction — emits `{}` (observe) so the harness proceeds.

This script runs in layer-2 sessions inside the user's project.

Exit codes:
  0  success (always — hook failures shouldn't break the session)
"""

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path


RECENT_EVENTS_PER_PHASE = 20


def emit(payload):
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()
    sys.exit(0)


def gather_recent_events(events_dir: Path, limit_per_phase: int):
    """For each phase under events/, collect up to N most-recent event file paths + timestamps."""
    summary = {}
    if not events_dir.exists():
        return summary

    for phase_dir in sorted(events_dir.iterdir()):
        if not phase_dir.is_dir():
            continue
        # Find all .json files under the phase, sorted by mtime (newest first)
        event_files = sorted(
            phase_dir.rglob("*.json"),
            key=lambda p: p.stat().st_mtime if p.exists() else 0,
            reverse=True,
        )[:limit_per_phase]
        summary[phase_dir.name] = [
            {
                "path": str(p.relative_to(events_dir.parent.parent)),
                "size_bytes": p.stat().st_size,
                "mtime": datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat(),
            }
            for p in event_files
        ]
    return summary


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        emit({})
        return

    cwd = Path(data.get("cwd", ".")).resolve()
    john_dir = cwd / ".john"

    if not john_dir.exists():
        emit({})
        return

    workspace_json_path = john_dir / "workspace.json"
    workspace_state = {}
    if workspace_json_path.exists():
        try:
            workspace_state = json.loads(workspace_json_path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            sys.stderr.write(f"WARN: could not read workspace.json: {exc}\n")

    snapshot = {
        "snapshot_taken_at": datetime.now(timezone.utc).isoformat(),
        "compaction_reason": data.get("compaction_reason") or data.get("reason"),
        "session_id": data.get("session_id"),
        "workspace_state": workspace_state,
        "plan_md_path": str(cwd / "PLAN.md") if (cwd / "PLAN.md").exists() else None,
        "claude_md_path": str(cwd / "CLAUDE.md") if (cwd / "CLAUDE.md").exists() else None,
        "recent_events": gather_recent_events(john_dir / "events", RECENT_EVENTS_PER_PHASE),
        "checkpoints_dirs": sorted(
            [d.name for d in (john_dir / "checkpoints").iterdir() if d.is_dir()]
        ) if (john_dir / "checkpoints").exists() else [],
    }

    # Write snapshot
    snapshot_dir = john_dir / "checkpoints"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    snapshot_path = snapshot_dir / f"precompact-{ts}.json"
    try:
        snapshot_path.write_text(json.dumps(snapshot, indent=2) + "\n")
    except OSError as exc:
        sys.stderr.write(f"WARN: could not write precompact snapshot: {exc}\n")
        emit({})
        return

    # Emit observe response (allow compaction to proceed); include snapshot path
    # in hookSpecificOutput so the user can see it via telemetry / logs
    emit({
        "hookSpecificOutput": {
            "hookEventName": "PreCompact",
            "snapshotPath": str(snapshot_path),
        }
    })


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.stderr.write(traceback.format_exc())
        emit({})
