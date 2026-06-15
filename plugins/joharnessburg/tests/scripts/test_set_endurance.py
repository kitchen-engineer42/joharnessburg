"""Tests for scripts/set_endurance.py."""

import json
import tempfile
import unittest
from pathlib import Path

from tests._helpers import run_script


class TestSetEndurance(unittest.TestCase):
    def test_show_errors_with_no_john_dir(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, out, _ = run_script("set_endurance.py", cwd=tdp)
            self.assertEqual(rc, 1)
            self.assertFalse(out["success"])
            self.assertIn(".john/workspace.json", out["error"])

    def test_set_from_subdirectory_lands_in_root_workspace(self):
        # v0.2.3: setting the goal from a project subdirectory writes to the
        # project root's workspace.json (walk-up resolution).
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            subdir = tdp / "app"
            subdir.mkdir()
            rc, out, _ = run_script("set_endurance.py", "finish the build", cwd=subdir)
            self.assertEqual(rc, 0)
            self.assertEqual(out["endurance_goal"], "finish the build")
            state = json.loads((tdp / ".john" / "workspace.json").read_text())
            self.assertEqual(
                state["session_metadata"]["endurance_goal"], "finish the build"
            )

    def test_show_when_unset(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            rc, out, _ = run_script("set_endurance.py", cwd=tdp)
            self.assertEqual(rc, 0)
            self.assertTrue(out["success"])
            self.assertEqual(out["action"], "show")
            self.assertIsNone(out["endurance_goal"])
            self.assertFalse(out["is_set"])

    def test_set_writes_to_workspace_json(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            rc, out, _ = run_script(
                "set_endurance.py",
                "Build",
                "a",
                "slide",
                "deck",
                "from",
                "this",
                "textbook.",
                cwd=tdp,
            )
            self.assertEqual(rc, 0)
            self.assertTrue(out["success"])
            self.assertEqual(out["action"], "set")
            self.assertEqual(
                out["endurance_goal"],
                "Build a slide deck from this textbook.",
            )

            state = json.loads((tdp / ".john" / "workspace.json").read_text())
            self.assertEqual(
                state["session_metadata"]["endurance_goal"],
                "Build a slide deck from this textbook.",
            )
            self.assertIn("endurance_set_at", state["session_metadata"])

    def test_set_then_show_returns_goal(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            rc, _, _ = run_script("set_endurance.py", "Test goal", cwd=tdp)
            self.assertEqual(rc, 0)
            rc, out, _ = run_script("set_endurance.py", cwd=tdp)
            self.assertEqual(rc, 0)
            self.assertEqual(out["endurance_goal"], "Test goal")
            self.assertTrue(out["is_set"])

    def test_clear_unsets_goal(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            rc, _, _ = run_script("set_endurance.py", "Goal A", cwd=tdp)
            self.assertEqual(rc, 0)

            rc, out, _ = run_script("set_endurance.py", "--clear", cwd=tdp)
            self.assertEqual(rc, 0)
            self.assertTrue(out["success"])
            self.assertEqual(out["action"], "clear")
            self.assertEqual(out["previous_goal"], "Goal A")
            self.assertIsNone(out["endurance_goal"])

            state = json.loads((tdp / ".john" / "workspace.json").read_text())
            self.assertIsNone(state["session_metadata"]["endurance_goal"])

    def test_set_and_clear_conflict(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            rc, out, _ = run_script(
                "set_endurance.py", "some goal", "--clear", cwd=tdp
            )
            self.assertEqual(rc, 1)
            self.assertFalse(out["success"])
            self.assertIn("both", out["error"])

    def test_set_overwrites_previous_goal(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            rc, _, _ = run_script("set_endurance.py", "First goal", cwd=tdp)
            self.assertEqual(rc, 0)
            rc, out, _ = run_script(
                "set_endurance.py", "Second goal", cwd=tdp
            )
            self.assertEqual(rc, 0)
            self.assertEqual(out["previous_goal"], "First goal")
            self.assertEqual(out["endurance_goal"], "Second goal")


if __name__ == "__main__":
    unittest.main()
