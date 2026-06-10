#!/usr/bin/env python3
"""Fold append-only events for a phase into canonical state.

Reads all `.json` files under `<cwd>/.john/events/<phase>/`, sorts them
deterministically, and writes a canonical state file at
`<cwd>/.john/checkpoints/<phase>/state.json`. Idempotent — running twice
on the same event set produces identical output.

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
"""

import argparse
import json
import math
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path


# An unparseable event file younger than this is treated as a write in
# progress (workflow runs have up to 16 concurrent writers), not corruption:
# skipped this reduce, retried on the next one. Only stale unparseable files
# are quarantined — quarantine is permanent (idempotent-skip on re-runs), so
# racing a mid-write file would silently lose a valid event.
FRESH_GRACE_SECONDS = 5


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
                dest.parent.mkdir(parents=True, exist_ok=True)
                try:
                    evt_file.rename(dest)
                    (dest.parent / f"{dest.name}.parse_error.txt").write_text(
                        f"JSONDecodeError at {datetime.now(timezone.utc).isoformat()}:\n{exc}\n",
                        encoding="utf-8",
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
    """Detect chunks with missing chunk_echo or chunk_complete events.

    A subagent may occasionally skip its chunk_echo (or, less commonly,
    chunk_complete). The reducer flags these so the user can see them.

    Returns a dict like:
      {
        "incomplete_chunks": [{"chunk_id": "...", "missing": ["chunk_echo"]}, ...],
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
    if chunks_with_echo or chunks_with_complete:
        all_chunks = chunks_with_echo | chunks_with_complete
        for cid in sorted(all_chunks):
            missing = []
            if cid not in chunks_with_echo:
                missing.append("chunk_echo")
            if cid not in chunks_with_complete:
                missing.append("chunk_complete")
            if missing:
                incomplete.append({"chunk_id": cid, "missing": missing})

    return {
        "incomplete_chunks": incomplete,
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
        payload = e.get("payload") if isinstance(e.get("payload"), dict) else {}
        for container in (payload, e):
            one = container.get("entry_id")
            if isinstance(one, str) and one:
                ids.add(one)
            many = container.get("entry_ids")
            if isinstance(many, list):
                ids.update(x for x in many if isinstance(x, str) and x)
    return ids


def _disk_entry_ids(knowledge_dir: Path) -> set:
    """Entry ids present on disk (report-only heuristic).

    An entry is either:
    - a directory that directly contains at least one regular file (entry id =
      dir basename). Its OWN subdirectories (assets/, figures/, ...) are
      entry-internal and NOT descended into — they are not separate entries;
    - a top-level `*.md` file (entry id = file stem), covering flat
      file-per-entry layouts.

    Directories with no direct files are category nesting and are descended
    into. Skips hidden names and `_quarantine/`. Returns empty set when the
    dir is missing (graceful).
    """
    ids: set = set()
    if not knowledge_dir.is_dir():
        return ids

    def walk(d: Path, top: bool):
        for child in sorted(d.iterdir()):
            name = child.name
            if name.startswith(".") or name == "_quarantine":
                continue
            if child.is_file():
                if top and child.suffix == ".md":
                    ids.add(child.stem)
                continue
            if child.is_dir():
                has_direct_file = any(
                    g.is_file() and not g.name.startswith(".")
                    for g in child.iterdir()
                )
                if has_direct_file:
                    ids.add(name)  # entry dir; subdirs are entry-internal
                else:
                    walk(child, top=False)  # category nesting

    walk(knowledge_dir, top=True)
    return ids


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

    # Deterministic sort. Primary: timestamp (lexicographic ISO 8601 sorts correctly).
    # Secondary: _source_file (stable tiebreaker for identical timestamps + clock skew).
    # Wrapping above guarantees every entry is a dict, so no isinstance guard needed here.
    def sort_key(e):
        assert isinstance(e, dict), "load_events / reduce_phase wrapping invariant violated"
        return (e.get("timestamp", ""), e.get("_source_file", ""))

    events.sort(key=sort_key)

    completeness = _check_chunk_completeness(events)

    state = {
        "phase": phase_dir.name,
        "reduced_at": datetime.now(timezone.utc).isoformat(),
        "event_count": len(events),
        "events_quarantined": quarantined,
        "events_skipped_fresh": skipped_fresh,
        "incomplete_chunks": completeness["incomplete_chunks"],
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

    cwd = Path.cwd()
    john_dir = cwd / ".john"

    if not john_dir.exists():
        err(
            f"No .john/ directory found in {cwd}. "
            f"Run /john:init first.",
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

    state, seen, quarantined, skipped_fresh = reduce_phase(
        phase_dir, cwd, quarantine=not args.dry_run
    )

    checkpoint_dir = john_dir / "checkpoints" / args.phase
    state_file = checkpoint_dir / "state.json"

    if not args.dry_run:
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

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
            f"NOTE: {len(state['incomplete_chunks'])} chunk(s) missing chunk_echo or "
            f"chunk_complete events. See state.json's incomplete_chunks field.\n"
        )

    # ---- phase-boundary checks (count gate + disk reconciliation) ----
    gate = None
    verify = None
    exit_code = 0
    claimed = None
    if args.expect_entries is not None or args.verify_knowledge:
        claimed = _claimed_entry_ids(state["events"])

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
        on_disk = _disk_entry_ids(kdir)
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

    emit(
        {
            "phase": args.phase,
            "events_seen": seen,
            "events_folded": state["event_count"],
            "events_quarantined": quarantined,
            "events_skipped_fresh": skipped_fresh,
            "incomplete_chunks": state["incomplete_chunks"],
            "quarantine_dir": str((phase_dir / "_quarantine").relative_to(cwd)) if quarantined else None,
            "state_file": str(state_file.relative_to(cwd)) if not args.dry_run else None,
            "dry_run": args.dry_run,
            "entries_claimed": len(claimed) if claimed is not None else None,
            "gate": gate,
            "verify": verify,
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
