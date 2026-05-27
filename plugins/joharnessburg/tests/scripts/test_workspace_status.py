"""Tests for scripts/workspace_status.py."""

import json
import tempfile
import unittest
from pathlib import Path

from tests._helpers import run_script


class TestWorkspaceStatus(unittest.TestCase):
    def test_status_errors_when_no_john_dir(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, out, err = run_script("workspace_status.py", cwd=tdp)
            self.assertEqual(rc, 1)
            self.assertFalse(out["success"])
            self.assertIn("No .john/", out["error"])

    def test_status_reads_workspace_state(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            # Init first
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            # Now status
            rc, out, err = run_script("workspace_status.py", "--quiet", cwd=tdp)
            self.assertEqual(rc, 0, f"stderr: {err}")
            self.assertTrue(out["success"])
            self.assertEqual(out["workspace"]["current_phase"], "bootstrap")
            self.assertNotIn("active_template", out["workspace"])  # v0.1.15+: field removed
            self.assertTrue(out["plan_md_present"])
            self.assertTrue(out["claude_md_present"])
            inv = out["inventory"]
            self.assertEqual(inv["input_files"], 0)
            self.assertEqual(inv["parsed_dirs"], 0)
            self.assertEqual(inv["events_phases"], [])
            self.assertEqual(inv["produced_skills"], 0)

    def test_status_counts_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            # Add some artifacts
            (tdp / ".john" / "input" / "a.txt").write_text("a")
            (tdp / ".john" / "input" / "b.txt").write_text("b")
            (tdp / ".john" / "events" / "extract").mkdir()
            (tdp / ".john" / "events" / "extract" / "evt1.json").write_text("{}")
            (tdp / ".john" / "knowledge" / "entry-001").mkdir()

            rc, out, _ = run_script("workspace_status.py", "--quiet", cwd=tdp)
            self.assertEqual(rc, 0)
            inv = out["inventory"]
            self.assertEqual(inv["input_files"], 2)
            self.assertEqual(inv["events_phases"], ["extract"])
            self.assertEqual(inv["knowledge_entries"], 1)

    def test_status_errors_on_missing_workspace_json(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()
            rc, out, _ = run_script("workspace_status.py", cwd=tdp)
            self.assertEqual(rc, 1)
            self.assertFalse(out["success"])


if __name__ == "__main__":
    unittest.main()
