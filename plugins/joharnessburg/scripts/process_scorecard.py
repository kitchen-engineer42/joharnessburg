#!/usr/bin/env python3
"""Process scorecard: deterministic, read-only conformance report for a John run.

Walks `.john/` (never the corpus content itself) and emits the process-quality
rubric as JSON (stdout) + a human summary (stderr): did the run invoke skills,
fan out, run its gates, declare its skips? Zero tokens, byte-comparable across
runs — the primary evolution signal for everything above the template ring,
and the diagnostic complement everywhere else.

THE RUBRIC IS FROZEN (rubric_version below). It is amendable by core
maintainers only — never by any automated skill-editing surface. Skills may
reference this scorecard; no skill edit can change what it counts. (The
evaluator lives outside the evolvable surface.)

What it reads: workspace.json, events/, checkpoints/ (incl. the persisted
gates/ verdicts), skill-log/, lessons/, input/ file names+sizes, and the
produced-skills directory. What it never reads: corpus file contents, PLAN.md
(the scorecard never parses prose).

Known limit, stated in output: human-intervention counting requires the
session transcript, which lives outside the project — reported as "n/a".

Exit codes:
  0  success (scorecard emitted)
  1  no .john/ found at or above cwd / --root
  2  unexpected exception
"""

import argparse
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from john_paths import find_john_root

RUBRIC_VERSION = 1


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


def _manifest(john_dir: Path, applied_metadata: Path | None) -> dict:
    ws = _read_json(john_dir / "workspace.json") or {}
    inputs = []
    input_dir = john_dir / "input"
    if input_dir.is_dir():
        for f in sorted(input_dir.rglob("*")):
            if f.is_file():
                try:
                    inputs.append(
                        {"name": str(f.relative_to(input_dir)), "size_bytes": f.stat().st_size}
                    )
                except OSError:
                    continue
    template = None
    if applied_metadata is not None:
        meta = _read_json(applied_metadata)
        if meta:
            # Names and versions only — applied metadata also carries local
            # filesystem paths, which must not flow into shareable reports.
            template = {
                "template_name": meta.get("template_name"),
                "template_version": meta.get("template_version"),
                "applied_at": meta.get("applied_at"),
            }
    return {
        "workspace_name": ws.get("name"),
        "workspace_schema_version": ws.get("schema_version"),
        "initialized_at": ws.get("initialized_at"),
        "created_by_john_version": ws.get("created_by_john_version"),
        "current_phase": ws.get("current_phase"),
        "endurance_goal_set": bool((ws.get("session_metadata") or {}).get("endurance_goal")),
        "input_files": len(inputs),
        "input_total_bytes": sum(i["size_bytes"] for i in inputs),
        "inputs": inputs,
        "template": template,
    }


def _checkpoint_chunk_counts(state: dict | None) -> dict:
    """Return severity-split chunk counts from a reducer checkpoint.

    New checkpoints already carry `chunks_missing_echo`. Older checkpoints
    stored echo-only audit gaps inside `incomplete_chunks`; normalize them here
    so historical scorecards don't keep overstating low-risk gaps.
    """
    if not isinstance(state, dict):
        return {"incomplete_chunks": None, "chunks_missing_echo": None}

    raw_incomplete = state.get("incomplete_chunks") or []
    if not isinstance(raw_incomplete, list):
        raw_incomplete = []

    high_risk = 0
    legacy_echo_only = 0
    for item in raw_incomplete:
        if not isinstance(item, dict):
            high_risk += 1
            continue
        missing = item.get("missing")
        missing_set = {m for m in missing if isinstance(m, str)} if isinstance(missing, list) else set()
        if missing_set == {"chunk_echo"}:
            legacy_echo_only += 1
        else:
            high_risk += 1

    explicit_missing_echo = state.get("chunks_missing_echo") or []
    if not isinstance(explicit_missing_echo, list):
        explicit_missing_echo = []

    return {
        "incomplete_chunks": high_risk,
        "chunks_missing_echo": len(explicit_missing_echo) + legacy_echo_only,
    }


def _phase_report(john_dir: Path, phase: str) -> dict:
    phase_dir = john_dir / "events" / phase
    events = 0
    unparseable = 0
    quarantined = 0
    subagents = set()
    event_types: dict = {}
    if phase_dir.is_dir():
        for f in phase_dir.rglob("*.json"):
            if not f.is_file():
                continue
            if "_quarantine" in f.relative_to(phase_dir).parts:
                quarantined += 1
                continue
            data = _read_json(f)
            if not isinstance(data, dict):
                unparseable += 1
                continue
            events += 1
            sid = data.get("subagent_id")
            if isinstance(sid, str) and sid:
                subagents.add(sid)
            et = data.get("event_type")
            if isinstance(et, str) and et:
                event_types[et] = event_types.get(et, 0) + 1

    checkpoint = john_dir / "checkpoints" / phase / "state.json"
    state = _read_json(checkpoint) if checkpoint.is_file() else None
    chunk_counts = _checkpoint_chunk_counts(state)

    gates = []
    gates_dir = john_dir / "checkpoints" / phase / "gates"
    if gates_dir.is_dir():
        for f in sorted(gates_dir.glob("*.json")):
            record = _read_json(f)
            if not isinstance(record, dict):
                continue
            gate = record.get("gate") or {}
            verify = record.get("verify") or {}
            gates.append(
                {
                    "timestamp": record.get("timestamp"),
                    "gate_status": gate.get("status"),
                    "entries_claimed": record.get("entries_claimed"),
                    "expected_min": gate.get("expected_min"),
                    "expected_max": gate.get("expected_max"),
                    "verify_orphans": len(verify.get("orphans") or []),
                    "verify_missing_on_disk": len(verify.get("missing_on_disk") or []),
                    "exit_code": record.get("exit_code"),
                }
            )

    return {
        "events": events,
        "unparseable_events": unparseable,
        "quarantined_events": quarantined,
        "distinct_subagents": len(subagents),
        "event_types": dict(sorted(event_types.items())),
        "checkpoint_present": state is not None,
        "incomplete_chunks": chunk_counts["incomplete_chunks"],
        "chunks_missing_echo": chunk_counts["chunks_missing_echo"],
        "gate_runs": len(gates),
        "gates": gates,
    }


def _skill_invocations(john_dir: Path) -> dict:
    per_skill: dict = {}
    per_phase: dict = {}
    total = 0
    unparseable = 0
    log_dir = john_dir / "skill-log"
    available = log_dir.is_dir()
    if available:
        for f in sorted(log_dir.glob("*.json")):
            record = _read_json(f)
            if not isinstance(record, dict):
                unparseable += 1
                continue
            total += 1
            skill = str(record.get("skill") or "unknown")
            per_skill[skill] = per_skill.get(skill, 0) + 1
            phase = record.get("phase") or "(unattributed)"
            per_phase[phase] = per_phase.get(phase, 0) + 1
    return {
        "recording_available": available,
        "total": total,
        "unparseable": unparseable,
        "per_skill": dict(sorted(per_skill.items())),
        "per_phase": dict(sorted(per_phase.items())),
    }


def _lessons(john_dir: Path) -> dict:
    by_scope: dict = {}
    total = 0
    unparseable = 0
    lessons_dir = john_dir / "lessons"
    if lessons_dir.is_dir():
        for f in sorted(lessons_dir.glob("*.json")):
            record = _read_json(f)
            if not isinstance(record, dict):
                unparseable += 1
                continue
            total += 1
            scope = record.get("scope_guess") or "unknown"
            by_scope[scope] = by_scope.get(scope, 0) + 1
    return {
        "total": total,
        "unparseable": unparseable,
        "by_scope": dict(sorted(by_scope.items())),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Emit the deterministic process scorecard for a John run (read-only).",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Project root (default: nearest .john/ at or above cwd).",
    )
    parser.add_argument(
        "--applied-metadata",
        default=None,
        help="Path to the applied template's .applied-metadata.json (adds template name+version to the manifest).",
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

    # Phase universe = union of events/ and checkpoints/ children, so a phase
    # that was checkpointed without events (or vice versa) is still visible.
    phase_names = set()
    for parent in (john_dir / "events", john_dir / "checkpoints"):
        if parent.is_dir():
            phase_names.update(d.name for d in parent.iterdir() if d.is_dir())
    phases = {name: _phase_report(john_dir, name) for name in sorted(phase_names)}
    zero_event_phases = sorted(n for n, p in phases.items() if p["events"] == 0)

    produced_skills_dir = root / ".claude" / "skills"
    produced_skills = (
        len([d for d in produced_skills_dir.iterdir() if d.is_dir()])
        if produced_skills_dir.is_dir()
        else 0
    )

    manifest = _manifest(john_dir, applied_metadata)
    skill_invocations = _skill_invocations(john_dir)

    # Phase provenance: the `phases` list above is event/checkpoint-backed ONLY.
    # current_phase and skill-log are weaker signals (pointers/attributions),
    # not a complete history oracle. Surface the evidence boundary rather than
    # letting a reader mistake the phase list for the full run history. PLAN.md
    # and arbitrary generated artifacts are intentionally not parsed here.
    current_phase = manifest.get("current_phase")
    skill_log_phases = {p for p in skill_invocations["per_phase"] if p != "(unattributed)"}
    phase_provenance = {
        "event_checkpoint_backed": sorted(phase_names),
        "current_phase": current_phase,
        "current_phase_backed": (current_phase in phase_names) if current_phase else None,
        "skill_log_phases": sorted(skill_log_phases),
        "skill_log_unbacked": sorted(skill_log_phases - phase_names),
    }

    scorecard = {
        "rubric_version": RUBRIC_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(root),
        "manifest": manifest,
        "phases": phases,
        "zero_event_phases": zero_event_phases,
        "phase_provenance": phase_provenance,
        "skill_invocations": skill_invocations,
        "lessons": _lessons(john_dir),
        "interventions": "n/a (requires transcript analysis)",
        "produced_skills": produced_skills,
    }

    if not args.quiet:
        sys.stderr.write(_human_summary(scorecard))
        sys.stderr.flush()

    emit(scorecard)


def _human_summary(sc: dict) -> str:
    m = sc["manifest"]
    si = sc["skill_invocations"]
    lines = [
        "",
        f"Process scorecard (rubric v{sc['rubric_version']}) — {sc['project_root']}",
        f"  John version at init: {m['created_by_john_version'] or '?'}"
        + (f" | template: {m['template']['template_name']} {m['template']['template_version']}" if m.get("template") else ""),
        f"  inputs: {m['input_files']} files ({m['input_total_bytes']} bytes) | current phase: {m['current_phase'] or '?'}",
        "",
        "Phases (event/checkpoint-backed — not the full run history):",
    ]
    if not sc["phases"]:
        lines.append("  (none — no events or checkpoints recorded)")
    for name, p in sc["phases"].items():
        gate_bits = (
            ", ".join(f"{g['gate_status']}({g['entries_claimed']})" for g in p["gates"] if g["gate_status"])
            or ("verify-only" if p["gate_runs"] else "NEVER RUN")
        )
        lines.append(
            f"  {name}: {p['events']} events, {p['distinct_subagents']} subagents, "
            f"checkpoint={'yes' if p['checkpoint_present'] else 'NO'}, gates: {gate_bits}"
        )
    if sc["zero_event_phases"]:
        lines.append(f"  ⚠ zero-event phases: {', '.join(sc['zero_event_phases'])}")
    pp = sc["phase_provenance"]
    if pp.get("skill_log_unbacked"):
        lines.append(
            f"  NOTE: phase attributed in skill-log but no event/checkpoint recorded: "
            f"{', '.join(pp['skill_log_unbacked'])}"
        )
    if pp.get("current_phase") and pp.get("current_phase_backed") is False:
        lines.append(
            f"  NOTE: current_phase references '{pp['current_phase']}' with no "
            f"event/checkpoint recorded"
        )
    lines += [
        "",
        f"Skill invocations: {si['total']}"
        + ("" if si["recording_available"] else " (recording unavailable — pre-v0.3.0 run?)"),
    ]
    for skill, n in si["per_skill"].items():
        lines.append(f"  {skill}: {n}")
    lines += [
        f"Lessons: {sc['lessons']['total']} ({json.dumps(sc['lessons']['by_scope']) if sc['lessons']['by_scope'] else 'none'})",
        f"Produced skills: {sc['produced_skills']}",
        f"Interventions: {sc['interventions']}",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        sys.stderr.write(traceback.format_exc())
        emit({"error": f"unexpected exception: {exc}"}, success=False, exit_code=2)
