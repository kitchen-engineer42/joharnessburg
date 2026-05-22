"""Tests for scripts/set_template.py."""

import json
import os
import tempfile
import unittest
from pathlib import Path

from tests._helpers import run_script


class TestSetTemplate(unittest.TestCase):
    def test_list_mode_with_no_arg(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            # No project context needed for list mode
            rc, out, _ = run_script("set_template.py", cwd=tdp)
            self.assertEqual(rc, 0)
            self.assertTrue(out["success"])
            self.assertEqual(out["action"], "list")
            # installed list may be non-empty on a dev machine, but key must exist
            self.assertIn("installed", out)

    def test_set_errors_with_no_john_dir(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, out, _ = run_script("set_template.py", "doc-verification", cwd=tdp)
            self.assertEqual(rc, 1)
            self.assertFalse(out["success"])

    def test_set_errors_when_template_not_installed(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            rc, out, _ = run_script(
                "set_template.py", "nonexistent-template-xyz", cwd=tdp
            )
            self.assertEqual(rc, 1)
            self.assertFalse(out["success"])
            self.assertIn("not installed", out["error"])

    def test_clear_unsets_active_template(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            # Manually set a value in workspace.json so clear has something to undo
            ws_path = tdp / ".john" / "workspace.json"
            state = json.loads(ws_path.read_text())
            state["active_template"] = "doc-verification"
            ws_path.write_text(json.dumps(state, indent=2))

            rc, out, _ = run_script("set_template.py", "--clear", cwd=tdp)
            self.assertEqual(rc, 0)
            self.assertTrue(out["success"])
            self.assertEqual(out["action"], "clear")
            self.assertEqual(out["previous_template"], "doc-verification")
            self.assertIsNone(out["active_template"])

            new_state = json.loads(ws_path.read_text())
            self.assertIsNone(new_state["active_template"])

    def test_set_and_clear_conflict(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            rc, out, _ = run_script(
                "set_template.py", "anything", "--clear", cwd=tdp
            )
            self.assertEqual(rc, 1)
            self.assertFalse(out["success"])


if __name__ == "__main__":
    unittest.main()
