#!/usr/bin/env python3
"""PostToolUse hook (matcher: Skill): record skill invocations into .john/skill-log/.

Why: the process scorecard's central question — "which skills did this run
actually invoke, in which phase?" — was previously answerable only by parsing
the session transcript outside the project. This hook makes the workspace
self-contained: one small JSON record per Skill-tool invocation, appended to
`<project>/.john/skill-log/`.

Contract notes (verified live against the harness, 2026-06-12):
- PostToolUse fires for tool name `Skill`; `tool_input.skill` carries the
  (possibly plugin-namespaced) skill name, `tool_input.args` the optional
  argument string.
- Skill invocations made INSIDE subagents flow through the parent session's
  hooks too, so fan-out workers' skill usage is captured.

Privacy: the record stores the LENGTH of the args string, never its content —
skill arguments routinely contain corpus text.

This script (and the scorecard that reads its output) is part of John's
evolution instrumentation: its record format is frozen — amendable by core
maintainers only, never by any automated skill-editing surface.

No-op (emit `{}`) when there's no `.john/` at or above cwd.

Exit codes:
  0  success (always — hook failures shouldn't break the session)
"""

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from john_paths import find_john_root

SCHEMA_VERSION = 1


def emit(payload):
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()
    sys.exit(0)


def _slug(name: str) -> str:
    """Filename-safe slug of a skill name (namespaced names contain ':')."""
    cleaned = "".join(c if (c.isalnum() or c in "-_") else "-" for c in name)
    return cleaned.strip("-") or "unknown"


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        emit({})
        return

    if data.get("tool_name") != "Skill":
        # Defense in depth; the hooks.json matcher should already filter.
        emit({})
        return

    root = find_john_root(Path(data.get("cwd", ".")))
    if root is None:
        emit({})
        return
    john_dir = root / ".john"

    tool_input = data.get("tool_input") or {}
    skill = str(tool_input.get("skill") or "unknown")
    args = tool_input.get("args")

    # Best-effort phase attribution from workspace.json. A session that never
    # advances the phase gets everything attributed to that phase — which is
    # itself a scorecard finding, not a reason to fail here.
    phase = None
    try:
        ws = json.loads((john_dir / "workspace.json").read_text(encoding="utf-8"))
        phase = ws.get("current_phase")
    except (OSError, json.JSONDecodeError):
        pass

    record = {
        "schema_version": SCHEMA_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "skill": skill,
        "args_chars": len(args) if isinstance(args, str) else 0,
        "phase": phase,
        "session_id": data.get("session_id"),
    }

    log_dir = john_dir / "skill-log"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        ts_compact = (
            record["timestamp"].replace(":", "").replace("-", "").replace("+0000", "Z")
        )
        # Timestamp (µs precision) + slug keeps concurrent writers collision-free
        # in practice; the log is append-only, one file per invocation.
        path = log_dir / f"{ts_compact}-{_slug(skill)}.json"
        path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"WARN: could not record skill invocation: {exc}\n")

    emit({})


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.stderr.write(traceback.format_exc())
        emit({})
