#!/usr/bin/env python3
"""Emit auditor-legibility manifests for a finished John run.

Writes two small JSON files into the project's `.john/` so an external auditor
(e.g. an evaluation harness) or John's own evolution tooling can discover a run's
IDENTITY and SELF-EVAL entry points WITHOUT reading app code:

  .john/PROVENANCE.json         — run identity: John version, template name+version,
                                  corpus inputs, observed phases, run start/end times.
  .john/SELF_EVAL_MANIFEST.json — how to re-run the process scorecard + where reports
                                  live.

Standalone-by-default: a vanilla John run emits both, with template fields null
(the open-source membership test). Pure stdlib, idempotent (re-running overwrites),
zero-token. It WRITES exactly these two files and nothing else — it never touches
corpus content or canonical state, and reads only `.john/` structure, workspace.json,
the applied template metadata (names + versions only, never local paths), and event
TIMESTAMPS.

Deliberately NOT emitted here: `.john/APP_RESULTS_MANIFEST.json` (where a produced app
wrote its results). John core has no app-results convention — that is template/app
work, emitted by the template that defines the convention.

These are LOCAL `.john/` artifacts, like workspace.json and the scorecard JSON — not
the shareable run report (`.john/reports/*.md`, which is privacy-scrubbed separately).

Exit codes:
  0  success (manifests written)
  1  no .john/ found at or above cwd / --root
  2  unexpected exception
"""

import argparse
import json
import shlex
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from john_paths import find_john_root

SCHEMA_VERSION = 1
SELF_EVAL_SCHEMA_VERSION = 2


def emit(payload, success=True, exit_code=0):
    payload["success"] = success
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    sys.stdout.flush()
    sys.exit(exit_code)


def err(msg, exit_code=1):
    sys.stderr.write(msg + "\n")
    emit({"error": msg}, success=False, exit_code=exit_code)


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _phase_names(john_dir: Path) -> list:
    """Union of events/ and checkpoints/ children — the SAME event/checkpoint-backed
    phase universe the process scorecard reports, so the two never disagree. Weaker
    signals (current_phase, skill-log) are intentionally not folded in here; the
    `phases_note` field states the boundary, mirroring the scorecard's J2 framing."""
    names = set()
    for parent in (john_dir / "events", john_dir / "checkpoints"):
        if parent.is_dir():
            names.update(d.name for d in parent.iterdir() if d.is_dir())
    return sorted(names)


def _event_time_bounds(john_dir: Path):
    """(min, max) ISO `timestamp` across parseable, non-quarantined events, or
    (None, None) when no events carry a timestamp. ISO 8601 strings sort
    chronologically, so lexical min/max is the run window."""
    events_dir = john_dir / "events"
    stamps: list[tuple[datetime, str]] = []
    if events_dir.is_dir():
        for f in events_dir.rglob("*.json"):
            if not f.is_file() or "_quarantine" in f.relative_to(events_dir).parts:
                continue
            data = _read_json(f)
            if isinstance(data, dict):
                ts = data.get("timestamp")
                if isinstance(ts, str) and ts:
                    try:
                        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    except ValueError:
                        continue
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    stamps.append((parsed.astimezone(timezone.utc), ts))
    if not stamps:
        return None, None
    return min(stamps, key=lambda item: item[0])[1], max(stamps, key=lambda item: item[0])[1]


def _corpus_inputs(john_dir: Path) -> list:
    """Relative filenames under `.john/input/` — corpus IDENTITY, not content.
    PROVENANCE.json is a local artifact (like the scorecard JSON, which already
    lists input names), not the scrubbed shareable report."""
    input_dir = john_dir / "input"
    names = []
    if input_dir.is_dir():
        for f in sorted(input_dir.rglob("*")):
            if f.is_file():
                names.append(str(f.relative_to(input_dir)))
    return names


def _template(applied_metadata: Path | None) -> dict:
    """Template name+version only (no local paths) — mirrors the scorecard's policy
    of keeping applied-metadata's filesystem paths out of emitted artifacts."""
    if applied_metadata is None:
        return {"template_name": None, "template_version": None}
    meta = _read_json(applied_metadata) or {}
    return {
        "template_name": meta.get("template_name"),
        "template_version": meta.get("template_version"),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Emit auditor-legibility manifests (PROVENANCE + SELF_EVAL) for a John run.",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Project root (default: nearest .john/ at or above cwd).",
    )
    parser.add_argument(
        "--applied-metadata",
        default=None,
        help="Path to the applied template's .applied-metadata.json (adds template name+version).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the human-readable summary on stderr; JSON only.",
    )
    args = parser.parse_args()

    if args.root:
        root = Path(args.root).expanduser().resolve()
        if not (root / ".john").is_dir():
            err(f"No .john/ directory at --root {root}.", exit_code=1)
            return
    else:
        root = find_john_root(Path.cwd())
        if root is None:
            err(
                f"No .john/ directory found at or above {Path.cwd()}. "
                f"Run /john:init to scaffold one.",
                exit_code=1,
            )
            return
    john_dir = root / ".john"

    applied_metadata = (
        Path(args.applied_metadata).expanduser().resolve() if args.applied_metadata else None
    )

    now = datetime.now(timezone.utc).isoformat()
    ws = _read_json(john_dir / "workspace.json") or {}
    template = _template(applied_metadata)
    started, completed = _event_time_bounds(john_dir)

    provenance = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now,
        "run_id": ws.get("initialized_at"),
        "john_version": ws.get("created_by_john_version"),
        "template_name": template["template_name"],
        "template_version": template["template_version"],
        "corpus": {
            "input_dir": ".john/input",
            "inputs": _corpus_inputs(john_dir),
            "description": None,
        },
        "current_phase": ws.get("current_phase"),
        "phases_observed": _phase_names(john_dir),
        "phases_note": (
            "event/checkpoint-backed — not necessarily the full intended phase list "
            "(see PLAN.md)"
        ),
        "run_started_at": started,
        "run_completed_at": completed,
    }

    scorecard_script = Path(__file__).resolve().parent / "process_scorecard.py"
    scorecard_argv = [
        "python3",
        str(scorecard_script),
        "--root",
        str(root),
    ]
    self_eval = {
        "schema_version": SELF_EVAL_SCHEMA_VERSION,
        "generated_at": now,
        "process_scorecard_script": "scripts/process_scorecard.py",
        "process_scorecard_argv": scorecard_argv,
        "process_scorecard_command": shlex.join(scorecard_argv),
        "process_scorecard_command_deprecated": True,
        "run_report_location": ".john/reports/",
        "report_glob": "*.md",
        "report_format": "markdown",
        "workspace_metadata": ".john/workspace.json",
    }

    prov_path = john_dir / "PROVENANCE.json"
    eval_path = john_dir / "SELF_EVAL_MANIFEST.json"
    prov_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    eval_path.write_text(json.dumps(self_eval, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    payload = {
        "project_root": str(root),
        "written": [str(prov_path), str(eval_path)],
        "provenance": provenance,
        "self_eval": self_eval,
    }

    if not args.quiet:
        sys.stderr.write(_human_summary(payload))
        sys.stderr.flush()

    emit(payload)


def _human_summary(p: dict) -> str:
    prov = p["provenance"]
    tmpl = (
        f"{prov['template_name']} {prov['template_version']}"
        if prov["template_name"]
        else "(none — vanilla run)"
    )
    lines = [
        "",
        f"Auditor manifests written — {p['project_root']}",
        f"  John version: {prov['john_version'] or '?'} | template: {tmpl}",
        f"  corpus inputs: {len(prov['corpus']['inputs'])} file(s) under .john/input/",
        f"  phases observed (event/checkpoint-backed): "
        f"{', '.join(prov['phases_observed']) or '(none)'}",
        f"  run window: {prov['run_started_at'] or '?'} → {prov['run_completed_at'] or '?'}",
        "  files written:",
    ]
    for w in p["written"]:
        lines.append(f"    {w}")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        sys.stderr.write(traceback.format_exc())
        emit({"error": f"unexpected exception: {exc}"}, success=False, exit_code=2)
