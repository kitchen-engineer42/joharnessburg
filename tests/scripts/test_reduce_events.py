"""Tests for scripts/reduce_events.py."""

import json
import tempfile
import unittest
from pathlib import Path

from tests._helpers import run_script


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


if __name__ == "__main__":
    unittest.main()
