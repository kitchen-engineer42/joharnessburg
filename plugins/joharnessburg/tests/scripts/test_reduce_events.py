"""Tests for scripts/reduce_events.py."""

import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from tests._helpers import run_script


def _backdate(path: Path, seconds: int = 60):
    """Age a file's mtime past the reducer's fresh-write grace window.

    v0.2.2: an unparseable event file younger than FRESH_GRACE_SECONDS is
    treated as a concurrent write in progress (skipped, not quarantined) —
    tests exercising the quarantine path must use stale files.
    """
    t = time.time() - seconds
    os.utime(path, (t, t))


class TestReduceEvents(unittest.TestCase):
    def test_reduce_errors_when_no_john_dir(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, out, _ = run_script("reduce_events.py", "extract", cwd=tdp)
            self.assertEqual(rc, 1)
            self.assertFalse(out["success"])

    def test_reduce_errors_when_no_phase_dir(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            rc, out, _ = run_script("reduce_events.py", "nonexistent", cwd=tdp)
            self.assertEqual(rc, 1)
            self.assertFalse(out["success"])

    def test_reduce_folds_events_in_timestamp_order(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            phase_dir = tdp / ".john" / "events" / "extract"
            phase_dir.mkdir()
            # Three events out of order; reducer should sort by timestamp
            (phase_dir / "z.json").write_text(json.dumps({
                "event_type": "entry_extracted",
                "work_unit_id": "chunk_001",
                "timestamp": "2026-05-22T03:00:00Z",
                "subagent_id": "sub-aaa",
                "payload": {"entries": 3},
            }))
            (phase_dir / "a.json").write_text(json.dumps({
                "event_type": "entry_extracted",
                "work_unit_id": "chunk_002",
                "timestamp": "2026-05-22T01:00:00Z",
                "subagent_id": "sub-bbb",
                "payload": {"entries": 5},
            }))
            (phase_dir / "m.json").write_text(json.dumps({
                "event_type": "entry_extracted",
                "work_unit_id": "chunk_003",
                "timestamp": "2026-05-22T02:00:00Z",
                "subagent_id": "sub-ccc",
                "payload": {"entries": 7},
            }))

            rc, out, err = run_script("reduce_events.py", "extract", cwd=tdp)
            self.assertEqual(rc, 0, f"stderr: {err}")
            self.assertTrue(out["success"])
            self.assertEqual(out["events_folded"], 3)

            state_file = tdp / ".john" / "checkpoints" / "extract" / "state.json"
            self.assertTrue(state_file.is_file())
            state = json.loads(state_file.read_text())
            self.assertEqual(state["event_count"], 3)
            timestamps = [e["timestamp"] for e in state["events"]]
            self.assertEqual(
                timestamps,
                sorted(timestamps),
                "events should be sorted by timestamp",
            )

    def test_reduce_works_from_project_subdirectory(self):
        # v0.2.3: the reduce walks up to the nearest .john/ — running from a
        # subdirectory folds the root event log and writes the root checkpoint.
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            phase_dir = tdp / ".john" / "events" / "extract"
            phase_dir.mkdir()
            (phase_dir / "evt.json").write_text(json.dumps({
                "timestamp": "2026-05-22T00:00:00Z",
                "payload": {"entry_id": "e_001"},
            }))
            subdir = tdp / "app"
            subdir.mkdir()
            rc, out, err = run_script("reduce_events.py", "extract", cwd=subdir)
            self.assertEqual(rc, 0, f"stderr: {err}")
            self.assertEqual(out["events_folded"], 1)
            self.assertTrue(
                (tdp / ".john" / "checkpoints" / "extract" / "state.json").is_file()
            )

    def test_reduce_is_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            phase_dir = tdp / ".john" / "events" / "extract"
            phase_dir.mkdir()
            (phase_dir / "evt.json").write_text(json.dumps({
                "event_type": "x",
                "timestamp": "2026-05-22T00:00:00Z",
                "subagent_id": "s",
                "payload": {},
            }))

            rc, _, _ = run_script("reduce_events.py", "extract", cwd=tdp)
            self.assertEqual(rc, 0)
            first = (tdp / ".john" / "checkpoints" / "extract" / "state.json").read_text()
            rc, _, _ = run_script("reduce_events.py", "extract", cwd=tdp)
            self.assertEqual(rc, 0)
            second = (tdp / ".john" / "checkpoints" / "extract" / "state.json").read_text()
            # reduced_at timestamp will differ, but the events array structure should match
            first_state = json.loads(first)
            second_state = json.loads(second)
            self.assertEqual(first_state["event_count"], second_state["event_count"])
            self.assertEqual(first_state["events"], second_state["events"])

    def test_reduce_quarantines_malformed_events(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            phase_dir = tdp / ".john" / "events" / "extract"
            phase_dir.mkdir()
            (phase_dir / "good.json").write_text(json.dumps({
                "timestamp": "2026-05-22T00:00:00Z",
                "payload": {"ok": True},
            }))
            (phase_dir / "bad.json").write_text("not valid json {{")
            _backdate(phase_dir / "bad.json")

            rc, out, err = run_script("reduce_events.py", "extract", cwd=tdp)
            self.assertEqual(rc, 0)
            self.assertEqual(out["events_folded"], 1)
            self.assertEqual(out["events_quarantined"], 1)
            self.assertIn("quarantined", err.lower())

            # The malformed file moved into _quarantine/, not just skipped
            self.assertFalse((phase_dir / "bad.json").exists())
            quarantine_path = phase_dir / "_quarantine" / "bad.json"
            self.assertTrue(quarantine_path.exists())
            self.assertEqual(
                quarantine_path.read_text(),
                "not valid json {{",
            )
            err_text_path = phase_dir / "_quarantine" / "bad.json.parse_error.txt"
            self.assertTrue(err_text_path.is_file())
            self.assertIn("JSONDecodeError", err_text_path.read_text())

            # Re-running is idempotent: already-quarantined files are skipped, not re-quarantined
            rc, out2, _ = run_script("reduce_events.py", "extract", cwd=tdp)
            self.assertEqual(rc, 0)
            self.assertEqual(out2["events_folded"], 1)
            self.assertEqual(out2["events_quarantined"], 0)

    # v0.2.2 — concurrent-writer protection: fresh unparseable files are a
    # write in progress, not corruption. Quarantine is permanent, so racing
    # a mid-write event would silently lose it.
    def test_reduce_skips_fresh_malformed_event_without_quarantining(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            phase_dir = tdp / ".john" / "events" / "extract"
            phase_dir.mkdir()
            (phase_dir / "good.json").write_text(json.dumps({
                "timestamp": "2026-05-22T00:00:00Z",
                "payload": {"ok": True},
            }))
            # Freshly written partial file — mtime is "now"
            (phase_dir / "inflight.json").write_text('{"timestamp": "2026-')

            rc, out, err = run_script("reduce_events.py", "extract", cwd=tdp)
            self.assertEqual(rc, 0)
            self.assertEqual(out["events_folded"], 1)
            self.assertEqual(out["events_quarantined"], 0)
            self.assertEqual(out["events_skipped_fresh"], 1)
            self.assertIn("mid-write", err)
            # File left in place for the next reduce; no quarantine dir
            self.assertTrue((phase_dir / "inflight.json").is_file())
            self.assertFalse((phase_dir / "_quarantine").exists())

            # Once the writer finishes (valid JSON now), the next reduce folds it
            (phase_dir / "inflight.json").write_text(json.dumps({
                "timestamp": "2026-05-22T00:00:01Z",
                "payload": {"ok": True},
            }))
            rc, out2, _ = run_script("reduce_events.py", "extract", cwd=tdp)
            self.assertEqual(rc, 0)
            self.assertEqual(out2["events_folded"], 2)
            self.assertEqual(out2["events_skipped_fresh"], 0)

    def test_reduce_dry_run_leaves_malformed_events_in_place(self):
        # v0.1.9 — Codex #5: --dry-run must be read-only.
        # Malformed events should be detected + counted but NOT moved.
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            phase_dir = tdp / ".john" / "events" / "extract"
            phase_dir.mkdir()
            (phase_dir / "good.json").write_text(json.dumps({
                "timestamp": "2026-05-22T00:00:00Z", "payload": {"ok": True},
            }))
            (phase_dir / "bad.json").write_text("not valid json {{")
            _backdate(phase_dir / "bad.json")

            rc, out, err = run_script(
                "reduce_events.py", "extract", "--dry-run", cwd=tdp
            )
            self.assertEqual(rc, 0)
            self.assertTrue(out["dry_run"])
            # Detected — quarantine count still surfaces
            self.assertEqual(out["events_quarantined"], 1)
            # But NOT moved — bad.json must still be at its original location
            self.assertTrue(
                (phase_dir / "bad.json").is_file(),
                "dry-run must not move malformed events",
            )
            # And no _quarantine/ dir should be created
            self.assertFalse(
                (phase_dir / "_quarantine").exists(),
                "dry-run must not create _quarantine/ dir",
            )
            # No checkpoint file written either (existing dry-run contract)
            self.assertFalse(
                (tdp / ".john" / "checkpoints" / "extract" / "state.json").exists(),
            )

    def test_reduce_dry_run_does_not_write_checkpoint(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            phase_dir = tdp / ".john" / "events" / "extract"
            phase_dir.mkdir()
            (phase_dir / "evt.json").write_text(json.dumps({
                "timestamp": "2026-05-22T00:00:00Z",
                "payload": {},
            }))

            rc, out, _ = run_script(
                "reduce_events.py", "extract", "--dry-run", cwd=tdp
            )
            self.assertEqual(rc, 0)
            self.assertTrue(out["dry_run"])
            state_file = tdp / ".john" / "checkpoints" / "extract" / "state.json"
            self.assertFalse(state_file.exists())


    # v0.1.9 — Block 2.5: chunk_echo / chunk_complete completeness check
    def test_reduce_flags_chunk_with_missing_echo(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            phase_dir = tdp / ".john" / "events" / "extract"
            phase_dir.mkdir()
            # chunk-001: has both echo + complete (healthy)
            (phase_dir / "c1-echo.json").write_text(json.dumps({
                "event_type": "chunk_echo", "chunk_id": "chunk-001",
                "timestamp": "2026-05-22T00:00:00Z",
            }))
            (phase_dir / "c1-complete.json").write_text(json.dumps({
                "event_type": "chunk_complete", "chunk_id": "chunk-001",
                "timestamp": "2026-05-22T00:00:01Z",
                "entries_count": 3, "issues": [],
            }))
            # chunk-002: complete but no echo → audit-trail only (chunks_missing_echo, NOT incomplete)
            (phase_dir / "c2-complete.json").write_text(json.dumps({
                "event_type": "chunk_complete", "chunk_id": "chunk-002",
                "timestamp": "2026-05-22T00:00:02Z",
                "entries_count": 2, "issues": [],
            }))
            # chunk-003: echo only, no complete → genuinely incomplete
            (phase_dir / "c3-echo.json").write_text(json.dumps({
                "event_type": "chunk_echo", "chunk_id": "chunk-003",
                "timestamp": "2026-05-22T00:00:03Z",
            }))

            rc, out, err = run_script("reduce_events.py", "extract", cwd=tdp)
            self.assertEqual(rc, 0)
            # chunk-002 has chunk_complete → audit-trail gap only, not incomplete
            self.assertEqual(out["chunks_missing_echo"], ["chunk-002"])
            # chunk-003 has no chunk_complete → the only genuinely incomplete chunk
            incomplete = out["incomplete_chunks"]
            self.assertEqual(len(incomplete), 1)
            by_id = {item["chunk_id"]: item["missing"] for item in incomplete}
            self.assertEqual(by_id["chunk-003"], ["chunk_complete"])
            self.assertIn("missing chunk_complete", err)   # WARNING for the incomplete chunk
            self.assertIn("without a chunk_echo", err)      # INFO for the echo-only chunk

            state = json.loads(
                (tdp / ".john" / "checkpoints" / "extract" / "state.json").read_text()
            )
            self.assertEqual(len(state["incomplete_chunks"]), 1)
            self.assertEqual(state["chunks_missing_echo"], ["chunk-002"])
            self.assertEqual(state["chunks_with_echo"], 2)
            self.assertEqual(state["chunks_with_complete"], 2)

    def test_reduce_completeness_no_op_when_pattern_unused(self):
        # Phases that don't use chunk_echo/chunk_complete (e.g., simple parse)
        # should report empty incomplete_chunks.
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            phase_dir = tdp / ".john" / "events" / "parse"
            phase_dir.mkdir()
            (phase_dir / "p1.json").write_text(json.dumps({
                "event_type": "file_parsed", "source": "a.md",
                "timestamp": "2026-05-22T00:00:00Z",
            }))

            rc, out, _ = run_script("reduce_events.py", "parse", cwd=tdp)
            self.assertEqual(rc, 0)
            self.assertEqual(out["incomplete_chunks"], [])


class TestPhaseGateAndVerify(unittest.TestCase):
    """v0.2.0 — deterministic phase-boundary count gate + disk reconciliation."""

    def _setup_phase(self, tdp, entry_ids, phase="extract"):
        rc, _, _ = run_script("init_workspace.py", cwd=tdp)
        assert rc == 0
        phase_dir = tdp / ".john" / "events" / phase
        phase_dir.mkdir(parents=True, exist_ok=True)
        for i, eid in enumerate(entry_ids):
            (phase_dir / f"e{i:03d}.json").write_text(json.dumps({
                "event_type": "entry_extracted",
                "timestamp": f"2026-06-06T00:00:{i:02d}Z",
                "subagent_id": f"sub-{i}",
                "payload": {"entry_id": eid},
            }))
        return phase_dir

    def _write_knowledge_entry(self, tdp, entry_id, nested=None):
        kdir = tdp / ".john" / "knowledge"
        if nested:
            kdir = kdir / nested
        d = kdir / entry_id
        d.mkdir(parents=True, exist_ok=True)
        (d / "header.md").write_text(f"# {entry_id}\n")

    def test_gate_passes_when_actual_in_range(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            self._setup_phase(tdp, ["e_001", "e_002", "e_003"])
            rc, out, err = run_script(
                "reduce_events.py", "extract", "--expect-entries", "2-4", cwd=tdp
            )
            self.assertEqual(rc, 0, f"stderr: {err}")
            self.assertEqual(out["gate"]["status"], "pass")
            self.assertEqual(out["entries_claimed"], 3)
            self.assertIn("OK", err)

    def test_gate_small_drift_warns_zero_exit(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            self._setup_phase(tdp, [f"e_{i:03d}" for i in range(9)])
            rc, out, err = run_script(
                "reduce_events.py", "extract", "--expect-entries", "10", cwd=tdp
            )
            self.assertEqual(rc, 0)
            self.assertEqual(out["gate"]["status"], "drift")
            self.assertIn("DRIFT", err)
            self.assertIn("9", err)
            self.assertIn("10", err)

    def test_gate_far_short_fails_exit_3_but_writes_checkpoint(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            self._setup_phase(tdp, ["e_001", "e_002", "e_003"])
            rc, out, err = run_script(
                "reduce_events.py", "extract", "--expect-entries", "10", cwd=tdp
            )
            self.assertEqual(rc, 3)
            self.assertFalse(out["success"])
            self.assertEqual(out["gate"]["status"], "fail")
            self.assertIn("FAR SHORT", err)
            # The fold succeeded — the gate blocks advancement, not state derivation.
            self.assertTrue(
                (tdp / ".john" / "checkpoints" / "extract" / "state.json").is_file()
            )

    def test_gate_counts_unique_ids_across_entry_id_and_entry_ids(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            phase_dir = tdp / ".john" / "events" / "extract"
            phase_dir.mkdir()
            (phase_dir / "a.json").write_text(json.dumps({
                "timestamp": "2026-06-06T00:00:00Z",
                "payload": {"entry_id": "e_001"},
            }))
            (phase_dir / "b.json").write_text(json.dumps({
                "timestamp": "2026-06-06T00:00:01Z",
                "payload": {"entry_ids": ["e_002", "e_003"]},
            }))
            # duplicate claim of e_001 (corrective re-emit) must not inflate count
            (phase_dir / "c.json").write_text(json.dumps({
                "timestamp": "2026-06-06T00:00:02Z",
                "payload": {"entry_id": "e_001"},
            }))
            rc, out, _ = run_script(
                "reduce_events.py", "extract", "--expect-entries", "3", cwd=tdp
            )
            self.assertEqual(rc, 0)
            self.assertEqual(out["entries_claimed"], 3)
            self.assertEqual(out["gate"]["status"], "pass")

    def test_gate_overage_warns_zero_exit(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            self._setup_phase(tdp, [f"e_{i:03d}" for i in range(5)])
            rc, out, err = run_script(
                "reduce_events.py", "extract", "--expect-entries", "2-3", cwd=tdp
            )
            self.assertEqual(rc, 0)
            self.assertEqual(out["gate"]["status"], "pass")
            self.assertIn("OVERAGE", err)

    def test_gate_invalid_spec_exits_2(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            self._setup_phase(tdp, ["e_001"])
            rc, _, err = run_script(
                "reduce_events.py", "extract", "--expect-entries", "abc", cwd=tdp
            )
            self.assertEqual(rc, 2)
            self.assertIn("invalid --expect-entries", err)

    def test_verify_reports_orphans_and_missing(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            self._setup_phase(tdp, ["e_002"])
            self._write_knowledge_entry(tdp, "e_001")  # on disk, never claimed
            rc, out, err = run_script(
                "reduce_events.py", "extract", "--verify-knowledge", cwd=tdp
            )
            self.assertEqual(rc, 0)  # report-only: warnings never fail the run
            self.assertEqual(out["verify"]["orphans"], ["e_001"])
            self.assertEqual(out["verify"]["missing_on_disk"], ["e_002"])
            self.assertIn("orphan", err.lower())
            self.assertIn("missing on disk", err)

    def test_verify_never_mutates(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            self._setup_phase(tdp, ["e_002"])
            self._write_knowledge_entry(tdp, "e_001")
            kdir = tdp / ".john" / "knowledge"
            before = sorted(str(p.relative_to(kdir)) for p in kdir.rglob("*"))
            rc, _, _ = run_script(
                "reduce_events.py", "extract", "--verify-knowledge", cwd=tdp
            )
            self.assertEqual(rc, 0)
            after = sorted(str(p.relative_to(kdir)) for p in kdir.rglob("*"))
            self.assertEqual(before, after, "verify must not touch the knowledge tree")

    def test_verify_handles_missing_knowledge_dir(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            self._setup_phase(tdp, ["e_001"])
            kdir = tdp / ".john" / "knowledge"
            if kdir.exists():
                kdir.rmdir()
            rc, out, _ = run_script(
                "reduce_events.py", "extract", "--verify-knowledge", cwd=tdp
            )
            self.assertEqual(rc, 0)
            self.assertEqual(out["verify"]["entries_on_disk"], 0)
            self.assertEqual(out["verify"]["orphans"], [])
            self.assertEqual(out["verify"]["missing_on_disk"], ["e_001"])

    def test_verify_matches_nested_category_dirs(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            self._setup_phase(tdp, ["e_001"])
            self._write_knowledge_entry(tdp, "e_001", nested="factual")
            rc, out, _ = run_script(
                "reduce_events.py", "extract", "--verify-knowledge", cwd=tdp
            )
            self.assertEqual(rc, 0)
            self.assertEqual(out["verify"]["orphans"], [])
            self.assertEqual(out["verify"]["missing_on_disk"], [])

    # v0.3.0 — gate verdicts persist to disk (the scorecard's central column)
    def test_gate_verdict_persisted_to_checkpoints(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            self._setup_phase(tdp, ["e_001", "e_002", "e_003"])
            rc, _, _ = run_script(
                "reduce_events.py", "extract",
                "--expect-entries", "2-4", "--verify-knowledge", cwd=tdp,
            )
            self.assertEqual(rc, 0)
            gates_dir = tdp / ".john" / "checkpoints" / "extract" / "gates"
            records = list(gates_dir.glob("*.json"))
            self.assertEqual(len(records), 1)
            record = json.loads(records[0].read_text())
            self.assertEqual(record["gate"]["status"], "pass")
            self.assertEqual(record["entries_claimed"], 3)
            self.assertEqual(record["exit_code"], 0)
            self.assertIn("verify", record)

            # A second gated reduce appends a second record (append-only history)
            rc, _, _ = run_script(
                "reduce_events.py", "extract", "--expect-entries", "10", cwd=tdp,
            )
            self.assertEqual(rc, 3)
            records = sorted(gates_dir.glob("*.json"))
            self.assertEqual(len(records), 2)
            self.assertEqual(json.loads(records[-1].read_text())["gate"]["status"], "fail")

    def test_gate_verdict_not_persisted_on_dry_run(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            self._setup_phase(tdp, ["e_001"])
            rc, _, _ = run_script(
                "reduce_events.py", "extract",
                "--expect-entries", "1", "--dry-run", cwd=tdp,
            )
            self.assertEqual(rc, 0)
            self.assertFalse(
                (tdp / ".john" / "checkpoints" / "extract" / "gates").exists(),
                "--dry-run must stay fully read-only",
            )

    # v0.2.2 — layout-aware disk reconciliation
    def test_verify_entry_internal_subdirs_are_not_orphans(self):
        # An entry's own subdirectory (assets/, figures/, ...) is part of the
        # entry, not a separate entry — must not be reported as an orphan.
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            self._setup_phase(tdp, ["e_001"])
            self._write_knowledge_entry(tdp, "e_001")
            assets = tdp / ".john" / "knowledge" / "e_001" / "assets"
            assets.mkdir()
            (assets / "diagram.txt").write_text("ascii art")
            rc, out, _ = run_script(
                "reduce_events.py", "extract", "--verify-knowledge", cwd=tdp
            )
            self.assertEqual(rc, 0)
            self.assertEqual(out["verify"]["orphans"], [])
            self.assertEqual(out["verify"]["missing_on_disk"], [])
            self.assertEqual(out["verify"]["entries_on_disk"], 1)

    def test_verify_counts_flat_md_files_as_entries(self):
        # Flat file-per-entry layout: .john/knowledge/e_001.md
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            self._setup_phase(tdp, ["e_001", "e_002"])
            kdir = tdp / ".john" / "knowledge"
            kdir.mkdir(parents=True, exist_ok=True)
            (kdir / "e_001.md").write_text("# e_001\n")
            (kdir / "e_002.md").write_text("# e_002\n")
            rc, out, _ = run_script(
                "reduce_events.py", "extract", "--verify-knowledge", cwd=tdp
            )
            self.assertEqual(rc, 0)
            self.assertEqual(out["verify"]["entries_on_disk"], 2)
            self.assertEqual(out["verify"]["orphans"], [])
            self.assertEqual(out["verify"]["missing_on_disk"], [])

    def test_gate_and_verify_with_dry_run_is_fully_read_only(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            phase_dir = self._setup_phase(tdp, ["e_001"])
            self._write_knowledge_entry(tdp, "e_orphan")
            (phase_dir / "bad.json").write_text("not valid json {{")
            rc, out, _ = run_script(
                "reduce_events.py", "extract",
                "--expect-entries", "10", "--verify-knowledge", "--dry-run",
                cwd=tdp,
            )
            self.assertEqual(rc, 3)  # far short still signals
            self.assertEqual(out["gate"]["status"], "fail")
            self.assertIn("e_orphan", out["verify"]["orphans"])
            # Fully read-only: no checkpoint, no quarantine move
            self.assertFalse(
                (tdp / ".john" / "checkpoints" / "extract" / "state.json").exists()
            )
            self.assertTrue((phase_dir / "bad.json").is_file())
            self.assertFalse((phase_dir / "_quarantine").exists())


if __name__ == "__main__":
    unittest.main()
