#!/usr/bin/env python3
"""Fold append-only events for a phase into canonical state.

Reads all `.json` files under `<project-root>/.john/events/<phase>/`
(project root = nearest dir at or above cwd containing `.john/`), sorts
them deterministically, and writes a canonical state file at
`<project-root>/.john/checkpoints/<phase>/state.json`. Idempotent —
running twice on the same event set produces identical output.

The default fold is **generic**: collects events into a sorted list
without phase-specific semantics. Phase-specific fold logic (e.g.,
deduplicating extraction entries by ID, tallying QC pass/fail) lives in
templates or phase skills; core ships the generic fold. Templates can
ship their own reducer that calls this one or replaces it entirely.

This script runs in **layer-2 sessions** inside the user's project.

Phase-boundary checks (v0.2.0):
  --expect-entries N | MIN-MAX   deterministic count gate. Compares the number
      of unique entry ids claimed in this phase's events against the expected
      count/range from PLAN.md (the CALLER supplies the number; this script
      never parses PLAN.md). Far short (< 90% of min) -> exit 3: do NOT
      advance the phase. Small drift / overage -> warning, exit 0. The
      checkpoint is still written either way — the gate blocks phase
      advancement, not state derivation.
  --verify-knowledge             report-only disk reconciliation. Walks the
      knowledge dir and cross-checks against claimed entry ids: entries on
      disk with no claiming event ("orphans") and claimed ids missing on disk.
      Warns, NEVER mutates. Note: rewrite-phase dedup legitimately merges
      entries, so "missing on disk" after a rewrite is not necessarily
      corruption.

Exit codes:
  0  success (includes drift/overage/reconciliation warnings)
  1  expected failure (no .john/, no events for phase)
  2  unexpected exception / invalid --expect-entries spec
  3  count gate far short — calling skill must not advance the phase
  4  required extraction coverage/grounding audit gate failed
"""

import argparse
import json
import math
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from john_paths import find_john_root
from knowledge_inventory import disk_entry_ids
from path_safety import (
    atomic_write_text,
    ensure_contained,
    reject_tree_symlinks,
    validate_work_id,
)


# An unparseable event file younger than this is treated as a write in
# progress (workflow runs have up to 16 concurrent writers), not corruption:
# skipped this reduce, retried on the next one. Only stale unparseable files
# are quarantined — quarantine is permanent (idempotent-skip on re-runs), so
# racing a mid-write file would silently lose a valid event.
FRESH_GRACE_SECONDS = 5
CANDIDATE_MUTATION_TYPES = {
    "entry_extracted",
    "entry_reextracted",
    "entry_rewritten",
    "entry_corrected",
    "entry_superseded",
    "entry_deleted",
}
AUDIT_EVENT_TYPES = {
    "coverage_gap",
    "coverage_audit_complete",
    "grounding_flag",
    "grounding_check_complete",
}


def emit(payload, success=True, exit_code=0):
    payload["success"] = success
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()
    sys.exit(exit_code)


def err(msg, exit_code=1):
    sys.stderr.write(msg + "\n")
    emit({"error": msg}, success=False, exit_code=exit_code)


def load_events(phase_dir: Path, *, quarantine: bool = True):
    """Yield (event, source_path) for every JSON file under phase_dir.

    Args:
        phase_dir: directory holding event files.
        quarantine: when True (default), malformed events are moved to
            `phase_dir/_quarantine/<orig-relpath>` with a `.parse_error.txt`
            sibling. When False (dry-run mode), malformed events are LEFT IN
            PLACE — the function still detects them and yields the
            '__quarantined__' sentinel for accounting, but no disk mutation
            happens. Dry-run mode is strictly read-only.

    Skips files inside `_quarantine/` subdirs (idempotent re-runs).
    """
    reject_tree_symlinks(phase_dir, label="event log")
    quarantine_dir = phase_dir / "_quarantine"
    for evt_file in phase_dir.rglob("*.json"):
        if not evt_file.is_file():
            continue
        ensure_contained(phase_dir, evt_file, label="event file")
        # Skip files already in _quarantine/ to keep re-runs idempotent
        try:
            evt_file.relative_to(quarantine_dir)
            continue
        except ValueError:
            pass

        try:
            data = json.loads(evt_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            # Freshly-written file? Likely a concurrent writer mid-write —
            # skip without quarantining; the next reduce picks it up.
            try:
                age = time.time() - evt_file.stat().st_mtime
            except OSError:
                age = 0.0  # vanished/renamed mid-check: treat as in-flight
            if age < FRESH_GRACE_SECONDS:
                sys.stderr.write(
                    f"WARN: unparseable event {evt_file} is <{FRESH_GRACE_SECONDS}s old — "
                    f"likely mid-write; skipped this reduce (not quarantined).\n"
                )
                yield "__skipped_fresh__", evt_file
                continue
            if quarantine:
                # Move + write a .parse_error.txt sibling.
                rel = evt_file.relative_to(phase_dir)
                dest = quarantine_dir / rel
                ensure_contained(quarantine_dir, dest, label="quarantine target")
                dest.parent.mkdir(parents=True, exist_ok=True)
                try:
                    evt_file.rename(dest)
                    atomic_write_text(
                        dest.parent / f"{dest.name}.parse_error.txt",
                        f"JSONDecodeError at {datetime.now(timezone.utc).isoformat()}:\n{exc}\n",
                    )
                    sys.stderr.write(
                        f"WARN: quarantined malformed event {evt_file} -> {dest}\n"
                    )
                except OSError as move_exc:
                    # If rename fails (e.g., permission), at least log it
                    sys.stderr.write(
                        f"WARN: could not quarantine {evt_file}: {move_exc} (original parse error: {exc})\n"
                    )
            else:
                # Dry-run: detect but don't move.
                sys.stderr.write(
                    f"WARN: malformed event detected (would quarantine in non-dry-run): {evt_file}: {exc}\n"
                )
            yield "__quarantined__", evt_file
            continue
        yield data, evt_file


def _check_chunk_completeness(events: list[dict]) -> dict:
    """Classify per-chunk completeness by the work-completion signal.

    Two conditions of very different severity, kept separate so a reader is not
    misled into re-extracting work that is actually done:

    - **incomplete_chunks** — chunks with no ``chunk_complete`` event: the work
      unit may genuinely be unfinished (higher risk; worth a look before
      advancing). Each entry records what is missing (always ``chunk_complete``,
      plus ``chunk_echo`` when that is absent too).
    - **chunks_missing_echo** — chunks that HAVE ``chunk_complete`` but skipped
      their ``chunk_echo``: the knowledge was extracted; only the
      self-correction / audit echo is absent (low risk, informational — *not*
      incomplete).

    Returns a dict like:
      {
        "incomplete_chunks": [{"chunk_id": "...", "missing": [...]}, ...],
        "chunks_missing_echo": ["chunk_id", ...],
        "chunks_with_echo": N,
        "chunks_with_complete": M,
      }

    Only fires when there's at least one chunk_echo OR chunk_complete event in
    the phase — if neither is used (e.g., simple phases without per-chunk
    accounting), the check is a no-op + reports empty.
    """
    chunks_with_echo: set[str] = set()
    chunks_with_complete: set[str] = set()
    for e in events:
        if not isinstance(e, dict):
            continue
        ev = e.get("event_type")
        chunk_id = e.get("chunk_id") or e.get("work_unit_id")
        if not chunk_id:
            continue
        if ev == "chunk_echo":
            chunks_with_echo.add(chunk_id)
        elif ev == "chunk_complete":
            chunks_with_complete.add(chunk_id)

    incomplete: list[dict] = []
    missing_echo: list[str] = []
    if chunks_with_echo or chunks_with_complete:
        for cid in sorted(chunks_with_echo | chunks_with_complete):
            has_echo = cid in chunks_with_echo
            has_complete = cid in chunks_with_complete
            if not has_complete:
                # No chunk_complete → the work unit may genuinely be unfinished.
                incomplete.append(
                    {"chunk_id": cid, "missing": ["chunk_complete"] + ([] if has_echo else ["chunk_echo"])}
                )
            elif not has_echo:
                # Has chunk_complete but no echo → audit-trail gap only, not incomplete.
                missing_echo.append(cid)

    return {
        "incomplete_chunks": incomplete,
        "chunks_missing_echo": missing_echo,
        "chunks_with_echo": len(chunks_with_echo),
        "chunks_with_complete": len(chunks_with_complete),
    }


def _parse_expect(spec: str):
    """Parse an --expect-entries spec: 'N' or 'MIN-MAX'. Returns (min, max)."""
    try:
        if "-" in spec:
            lo_s, hi_s = spec.split("-", 1)
            lo, hi = int(lo_s), int(hi_s)
        else:
            lo = hi = int(spec)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"invalid --expect-entries spec {spec!r}: use 'N' or 'MIN-MAX' (e.g. '40' or '35-50')"
        )
    if lo < 0 or hi < lo:
        raise argparse.ArgumentTypeError(
            f"invalid --expect-entries spec {spec!r}: need 0 <= MIN <= MAX"
        )
    return lo, hi


def _event_entry_ids(event: dict) -> set[str]:
    ids: set[str] = set()
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    for container in (payload, event):
        one = container.get("entry_id")
        if isinstance(one, str) and one:
            ids.add(one)
        many = container.get("entry_ids")
        if isinstance(many, list):
            ids.update(x for x in many if isinstance(x, str) and x)
    return ids


def _claimed_entry_ids(events: list) -> set:
    """Unique entry ids claimed across the phase's folded events.

    Accepts both documented event shapes: `payload.entry_id` (one entry per
    event) and `payload.entry_ids` (a list), plus top-level `entry_id` /
    `entry_ids` for robustness. Uniqueness keeps the count idempotent —
    re-emitted or corrective events don't inflate it.
    """
    ids: set = set()
    for e in events:
        if not isinstance(e, dict):
            continue
        event_type = e.get("event_type")
        # Legacy events without event_type remain readable. Typed audit events
        # never count merely because they mention an entry ID.
        if event_type in AUDIT_EVENT_TYPES:
            continue
        if event_type and event_type not in CANDIDATE_MUTATION_TYPES:
            continue
        ids.update(_event_entry_ids(e))
    return ids


def _event_datetime(event: dict) -> datetime:
    """Parse ISO timestamps into UTC-aware datetimes for correct offset order."""
    value = event.get("timestamp")
    if not isinstance(value, str) or not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _chunk_id(event: dict) -> str | None:
    value = event.get("chunk_id") or event.get("work_unit_id")
    return value if isinstance(value, str) and value else None


def evaluate_extraction_audits(events: list[dict]) -> dict:
    """Evaluate the latest non-stale coverage and grounding audit per chunk."""
    by_chunk: dict[str, list[dict]] = {}
    for event in events:
        if not isinstance(event, dict):
            continue
        chunk_id = _chunk_id(event)
        if chunk_id:
            by_chunk.setdefault(chunk_id, []).append(event)

    completed = sorted(
        chunk_id
        for chunk_id, chunk_events in by_chunk.items()
        if any(e.get("event_type") == "chunk_complete" for e in chunk_events)
    )
    accepted: set[str] = set()
    chunk_results: list[dict] = []
    all_reasons: list[str] = []

    for chunk_id in completed:
        chunk_events = by_chunk[chunk_id]
        candidates = [
            e for e in chunk_events if e.get("event_type") in CANDIDATE_MUTATION_TYPES
        ]
        candidate_ids: set[str] = set()
        for event in candidates:
            if event.get("event_type") != "entry_deleted":
                candidate_ids.update(_event_entry_ids(event))
        mutation_at = max(
            (_event_datetime(e) for e in candidates),
            default=datetime.min.replace(tzinfo=timezone.utc),
        )

        def latest_fresh(event_type: str) -> dict | None:
            choices = [
                e
                for e in chunk_events
                if e.get("event_type") == event_type
                and _event_datetime(e) > mutation_at
            ]
            return max(
                choices,
                key=lambda e: (_event_datetime(e), e.get("_source_file", "")),
                default=None,
            )

        coverage = latest_fresh("coverage_audit_complete")
        grounding = latest_fresh("grounding_check_complete")
        reasons: list[str] = []
        expected = len(candidate_ids)
        if coverage is None:
            reasons.append("missing or stale coverage_audit_complete")
        else:
            if coverage.get("verdict") != "complete" or coverage.get("gaps_found") != 0:
                reasons.append("coverage audit reports gaps")
            if coverage.get("entries_reviewed") != expected:
                reasons.append(
                    f"coverage checked {coverage.get('entries_reviewed')!r}; expected {expected}"
                )
        if grounding is None:
            reasons.append("missing or stale grounding_check_complete")
        else:
            checked = grounding.get("entries_checked")
            weak = grounding.get("weak")
            ungrounded = grounding.get("ungrounded")
            grounded = grounding.get("grounded")
            if checked != expected:
                reasons.append(f"grounding checked {checked!r}; expected {expected}")
            if weak != 0 or ungrounded != 0:
                reasons.append("grounding audit reports weak or ungrounded entries")
            if not all(isinstance(v, int) and v >= 0 for v in (checked, grounded, weak, ungrounded)):
                reasons.append("grounding summary counts are invalid")
            elif grounded + weak + ungrounded != checked:
                reasons.append("grounding summary counts do not add up")
        if coverage is not None and grounding is not None:
            if coverage.get("entries_reviewed") != grounding.get("entries_checked"):
                reasons.append("coverage and grounding checked-entry counts differ")

        passed = not reasons
        if passed:
            accepted.update(candidate_ids)
        else:
            all_reasons.extend(f"{chunk_id}: {reason}" for reason in reasons)
        chunk_results.append(
            {
                "chunk_id": chunk_id,
                "status": "pass" if passed else "fail",
                "candidate_entry_ids": sorted(candidate_ids),
                "accepted_entry_ids": sorted(candidate_ids) if passed else [],
                "latest_candidate_mutation_at": (
                    mutation_at.isoformat() if candidates else None
                ),
                "reasons": reasons,
            }
        )

    if not completed:
        all_reasons.append("no completed chunks found")
    return {
        "required": True,
        "status": "pass" if completed and not all_reasons else "fail",
        "completed_chunks": len(completed),
        "passed_chunks": sum(c["status"] == "pass" for c in chunk_results),
        "failed_chunks": sum(c["status"] == "fail" for c in chunk_results),
        "accepted_entry_ids": sorted(accepted),
        "reasons": all_reasons,
        "chunks": chunk_results,
    }


def reduce_phase(phase_dir: Path, project_root: Path, *, quarantine: bool = True):
    """Read all events under phase_dir, sort deterministically, return canonical state dict.

    Args:
        phase_dir: directory holding event files.
        project_root: project root for computing relative source paths.
        quarantine: passed through to load_events(); False for dry-run.

    Returns (state, events_seen, events_quarantined, events_skipped_fresh).
    """
    events = []
    quarantined = 0
    skipped_fresh = 0
    seen = 0
    for data, src in load_events(phase_dir, quarantine=quarantine):
        seen += 1
        if data == "__quarantined__":
            quarantined += 1
            continue
        if data == "__skipped_fresh__":
            skipped_fresh += 1
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

    # Deterministic sort. Parse timestamps so offset-bearing ISO strings sort by
    # the instant they represent rather than by lexical spelling.
    # Secondary: _source_file (stable tiebreaker for identical timestamps + clock skew).
    # Wrapping above guarantees every entry is a dict, so no isinstance guard needed here.
    def sort_key(e):
        assert isinstance(e, dict), "load_events / reduce_phase wrapping invariant violated"
        return (_event_datetime(e), e.get("_source_file", ""))

    events.sort(key=sort_key)

    completeness = _check_chunk_completeness(events)

    state = {
        "phase": phase_dir.name,
        "reduced_at": datetime.now(timezone.utc).isoformat(),
        "event_count": len(events),
        "events_quarantined": quarantined,
        "events_skipped_fresh": skipped_fresh,
        "incomplete_chunks": completeness["incomplete_chunks"],
        "chunks_missing_echo": completeness["chunks_missing_echo"],
        "chunks_with_echo": completeness["chunks_with_echo"],
        "chunks_with_complete": completeness["chunks_with_complete"],
        "events": events,
    }
    return state, seen, quarantined, skipped_fresh


def main():
    parser = argparse.ArgumentParser(
        description="Fold a phase's event log into canonical state.",
    )
    parser.add_argument(
        "phase",
        help="Phase name (matches directory under .john/events/). e.g., 'extract'",
    )
    parser.add_argument(
        "--require-extraction-audits",
        action="store_true",
        help=(
            "Require fresh zero-gap coverage and zero-weak/ungrounded audit "
            "summaries for every completed chunk; failure exits 4."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute and print state to stdout but do not write the checkpoint file.",
    )
    parser.add_argument(
        "--expect-entries",
        type=_parse_expect,
        default=None,
        metavar="N|MIN-MAX",
        help=(
            "Deterministic count gate: expected unique entry ids for this phase "
            "(number comes from PLAN.md; supplied by the caller). Far short -> exit 3."
        ),
    )
    parser.add_argument(
        "--verify-knowledge",
        action="store_true",
        help=(
            "Report-only reconciliation: cross-check knowledge entries on disk "
            "against claimed entry ids in the event log. Warns, never mutates."
        ),
    )
    parser.add_argument(
        "--knowledge-dir",
        default=".john/knowledge",
        help="Knowledge dir for --verify-knowledge (default: .john/knowledge).",
    )
    args = parser.parse_args()

    # Operate on the nearest project root at or above cwd (the reduce is
    # frequently invoked from a project subdirectory).
    cwd = find_john_root(Path.cwd()) or Path.cwd()
    john_dir = cwd / ".john"

    if not john_dir.exists():
        err(
            f"No .john/ directory found at or above {Path.cwd()}. "
            f"Run /john:init first.",
            exit_code=1,
        )
        return

    try:
        validate_work_id(args.phase, field="phase")
        phase_dir = ensure_contained(
            john_dir / "events",
            john_dir / "events" / args.phase,
            label="phase event directory",
        )
        checkpoint_dir = ensure_contained(
            john_dir / "checkpoints",
            john_dir / "checkpoints" / args.phase,
            label="phase checkpoint directory",
        )
    except ValueError as exc:
        err(str(exc), exit_code=1)
        return
    if not phase_dir.exists():
        err(
            f"No events directory for phase '{args.phase}'. "
            f"Expected: {phase_dir}",
            exit_code=1,
        )
        return

    state, seen, quarantined, skipped_fresh = reduce_phase(
        phase_dir, cwd, quarantine=not args.dry_run
    )

    state_file = checkpoint_dir / "state.json"

    quality_gate = (
        evaluate_extraction_audits(state["events"])
        if args.require_extraction_audits
        else {
            "required": False,
            "status": "not_required",
            "accepted_entry_ids": [],
            "reasons": [],
        }
    )
    state["quality_gate"] = quality_gate

    if not args.dry_run:
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(state_file, json.dumps(state, indent=2) + "\n")

    if quarantined:
        sys.stderr.write(
            f"NOTE: {quarantined} event file(s) quarantined under "
            f"{phase_dir / '_quarantine'}/ — inspect *.parse_error.txt for details.\n"
        )

    if skipped_fresh:
        sys.stderr.write(
            f"NOTE: {skipped_fresh} fresh unparseable event file(s) skipped (likely "
            f"mid-write by a concurrent agent) — re-run the reduce to pick them up.\n"
        )

    if state["incomplete_chunks"]:
        sys.stderr.write(
            f"WARNING: {len(state['incomplete_chunks'])} chunk(s) missing chunk_complete — "
            f"extraction may be unfinished. See state.json's incomplete_chunks field.\n"
        )

    if state["chunks_missing_echo"]:
        sys.stderr.write(
            f"INFO: {len(state['chunks_missing_echo'])} chunk(s) completed without a "
            f"chunk_echo (audit-trail only; not incomplete). See state.json's "
            f"chunks_missing_echo field.\n"
        )

    # ---- phase-boundary checks (count gate + disk reconciliation) ----
    gate = None
    verify = None
    exit_code = 0
    claimed = None
    if args.expect_entries is not None or args.verify_knowledge:
        claimed = (
            set(quality_gate["accepted_entry_ids"])
            if args.require_extraction_audits
            else _claimed_entry_ids(state["events"])
        )

    if args.expect_entries is not None:
        lo, hi = args.expect_entries
        actual = len(claimed)
        floor = math.ceil(0.9 * lo)
        if actual >= lo:
            status = "pass"
            if actual > hi:
                sys.stderr.write(
                    f"GATE: {actual} entries claimed vs expected {lo}-{hi} — OVERAGE "
                    f"(passes; check for duplicate extraction)\n"
                )
            else:
                sys.stderr.write(
                    f"GATE: {actual} entries claimed vs expected {lo}-{hi} — OK\n"
                )
        elif actual >= floor:
            status = "drift"
            sys.stderr.write(
                f"GATE: {actual} entries claimed vs expected {lo}-{hi} — SMALL DRIFT "
                f"(passes; worth a look)\n"
            )
        else:
            status = "fail"
            exit_code = 3
            extra = ""
            if actual == 0 and state["event_count"] > 0:
                extra = (
                    " No entry ids found in any event — the gate matches "
                    "payload.entry_id / payload.entry_ids; check the event shape."
                )
            sys.stderr.write(
                f"GATE: {actual} entries claimed vs expected {lo}-{hi} — FAR SHORT "
                f"(do not advance phase).{extra}\n"
            )
        gate = {
            "expected_min": lo,
            "expected_max": hi,
            "actual": actual,
            "status": status,
        }

    if args.verify_knowledge:
        kdir = Path(args.knowledge_dir)
        if not kdir.is_absolute():
            kdir = cwd / kdir
        try:
            kdir = ensure_contained(cwd, kdir, label="knowledge directory")
            reject_tree_symlinks(kdir, label="knowledge directory")
            on_disk = disk_entry_ids(kdir)
        except ValueError as exc:
            err(str(exc), exit_code=1)
            return
        orphans = sorted(on_disk - claimed)
        missing = sorted(claimed - on_disk)
        if orphans:
            sys.stderr.write(
                f"WARN: {len(orphans)} knowledge entr(ies) on disk with no "
                f"corresponding event (orphans). Report-only — nothing was changed.\n"
            )
        if missing:
            sys.stderr.write(
                f"WARN: {len(missing)} claimed entr(ies) missing on disk. "
                f"Rewrite-phase dedup legitimately merges entries — verify before "
                f"treating this as corruption. Report-only.\n"
            )
        verify = {
            "knowledge_dir": str(kdir.relative_to(cwd)) if kdir.is_relative_to(cwd) else str(kdir),
            "entries_on_disk": len(on_disk),
            "orphans": orphans,
            "missing_on_disk": missing,
        }

    # Persist gate/verify verdicts (append-only) so phase-boundary outcomes are
    # readable from the workspace itself — the process scorecard's central
    # column. Dry-run stays fully read-only.
    if (gate is not None or verify is not None) and not args.dry_run:
        gates_dir = checkpoint_dir / "gates"
        try:
            gates_dir.mkdir(parents=True, exist_ok=True)
            verdict_ts = datetime.now(timezone.utc).isoformat()
            ts_compact = verdict_ts.replace(":", "").replace("-", "").replace("+0000", "Z")
            atomic_write_text(
                gates_dir / f"{ts_compact}.json",
                json.dumps(
                    {
                        "timestamp": verdict_ts,
                        "phase": args.phase,
                        "gate": gate,
                        "verify": verify,
                        "entries_claimed": len(claimed) if claimed is not None else None,
                        "events_folded": state["event_count"],
                        "quality_gate": quality_gate,
                        "exit_code": 4 if quality_gate["status"] == "fail" else exit_code,
                    },
                    indent=2,
                )
                + "\n",
            )
        except OSError as exc:
            sys.stderr.write(f"WARN: could not persist gate verdict: {exc}\n")

    if quality_gate["status"] == "fail":
        exit_code = 4
        sys.stderr.write(
            "AUDIT GATE: failed — do not advance the phase. "
            + "; ".join(quality_gate["reasons"])
            + "\n"
        )

    emit(
        {
            "phase": args.phase,
            "events_seen": seen,
            "events_folded": state["event_count"],
            "events_quarantined": quarantined,
            "events_skipped_fresh": skipped_fresh,
            "incomplete_chunks": state["incomplete_chunks"],
            "chunks_missing_echo": state["chunks_missing_echo"],
            "quarantine_dir": str((phase_dir / "_quarantine").relative_to(cwd)) if quarantined else None,
            "state_file": str(state_file.relative_to(cwd)) if not args.dry_run else None,
            "dry_run": args.dry_run,
            "entries_claimed": len(claimed) if claimed is not None else None,
            "gate": gate,
            "verify": verify,
            "quality_gate": quality_gate,
        },
        success=(exit_code == 0),
        exit_code=exit_code,
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        sys.stderr.write(traceback.format_exc())
        emit({"error": f"unexpected exception: {exc}"}, success=False, exit_code=2)
