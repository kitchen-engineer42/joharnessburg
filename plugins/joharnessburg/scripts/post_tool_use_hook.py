#!/usr/bin/env python3
"""PostToolUse hook: offload large tool results to .john/trace/ + replace with digest.

Wired in hooks/hooks.json for PostToolUse with matcher Read|Bash|Write|Edit.
For each matching tool call: if the tool output exceeds OFFLOAD_THRESHOLD
characters, write the full result to `<cwd>/.john/trace/<sha-prefix>.txt` and
emit a head+tail digest as `updatedToolOutput` that replaces the tool result
in Claude's context.

The tool output is read from the documented PostToolUse input fields
(code.claude.com/docs/en/hooks): `tool_output_text` (string form), falling
back to `tool_output`, then `tool_response` (older harness versions);
non-string values are JSON-serialized before measuring.

Small results (under threshold) pass through unchanged — emit `{}`.

No-op when there's no `.john/` directory.

This script runs in layer-2 sessions inside the user's project.

Exit codes:
  0  success (always — hook failures shouldn't break the session)
"""

import hashlib
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path


OFFLOAD_THRESHOLD = 2048  # bytes; below this, pass through unchanged
HEAD_CHARS = 800
TAIL_CHARS = 800


def emit(payload):
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()
    sys.exit(0)


def make_digest(tool_result: str, offload_path: Path, tool_name: str) -> str:
    """Compose a head+tail digest with a pointer to the offload file."""
    head = tool_result[:HEAD_CHARS]
    tail = tool_result[-TAIL_CHARS:]
    total_chars = len(tool_result)
    truncated_chars = total_chars - HEAD_CHARS - TAIL_CHARS

    return (
        f"--- HEAD (first {HEAD_CHARS} chars of {tool_name} output) ---\n"
        f"{head}\n"
        f"--- [... {truncated_chars} chars truncated; full output offloaded to {offload_path} ...] ---\n"
        f"--- TAIL (last {TAIL_CHARS} chars of {tool_name} output) ---\n"
        f"{tail}\n"
        f"--- end (total {total_chars} chars; read {offload_path} for the full content) ---"
    )


def read_tool_output(data: dict) -> str:
    """Extract the tool's output per the documented PostToolUse input schema.

    Field precedence: `tool_output_text` (current docs, always a string) →
    `tool_output` → `tool_response` (older docs). The latter two may be
    structured (dict/list) for many tools — serialize so large structured
    results still offload.
    """
    for field in ("tool_output_text", "tool_output", "tool_response"):
        value = data.get(field)
        if value is None or value == "":
            continue
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            continue
    return ""


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
        # No John workspace → no-op; pass tool result through unchanged
        emit({})
        return

    raw_tool_name = data.get("tool_name", "unknown")
    # Sanitize: keep only the filename component, alphanumeric + dash + underscore.
    # Prevents path traversal via crafted tool_name (e.g., "../../etc/passwd").
    tool_name = "".join(
        c for c in Path(str(raw_tool_name)).name if c.isalnum() or c in "-_"
    ) or "unknown"
    tool_result = read_tool_output(data)
    if not tool_result:
        emit({})
        return

    if len(tool_result) < OFFLOAD_THRESHOLD:
        # Small enough; pass through
        emit({})
        return

    # Compute deterministic filename (so identical results dedup)
    sha = hashlib.sha256(tool_result.encode("utf-8", errors="replace")).hexdigest()[:16]
    trace_dir = john_dir / "trace"
    trace_dir.mkdir(parents=True, exist_ok=True)

    offload_path = trace_dir / f"{tool_name}-{sha}.txt"

    # Write the full result (idempotent — same sha means same content, fine to overwrite)
    if not offload_path.exists():
        try:
            offload_path.write_text(tool_result, encoding="utf-8")
        except OSError as exc:
            sys.stderr.write(f"WARN: could not offload tool result: {exc}\n")
            emit({})
            return

    # Show a cwd-relative pointer (e.g. .john/trace/<name>.txt) rather than the
    # user's absolute home path.
    try:
        offload_display = offload_path.relative_to(cwd)
    except ValueError:
        offload_display = offload_path
    digest = make_digest(tool_result, offload_display, tool_name)

    emit({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "updatedToolOutput": digest,
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
