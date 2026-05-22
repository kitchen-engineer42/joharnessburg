"""Tests for scripts/init_workspace.py."""

import json
import tempfile
import unittest
from pathlib import Path

from tests._helpers import run_script


class TestInitWorkspace(unittest.TestCase):
    def test_init_creates_john_dir_and_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, out, err = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0, f"stderr: {err}")
            self.assertTrue(out["success"])
            self.assertTrue((tdp / ".john").is_dir())
            self.assertTrue((tdp / ".john" / "workspace.json").is_file())
            self.assertTrue((tdp / "PLAN.md").is_file())
            self.assertTrue((tdp / "CLAUDE.md").is_file())
            # Subdirs
            for sd in ["input", "parsed", "chunks", "knowledge", "events", "checkpoints", "trace"]:
                self.assertTrue((tdp / ".john" / sd).is_dir(), f"missing subdir {sd}")
            # Workspace state shape
            state = json.loads((tdp / ".john" / "workspace.json").read_text())
            self.assertEqual(state["schema_version"], 1)
            self.assertIsNone(state["active_template"])
            self.assertEqual(state["current_phase"], "bootstrap")

    def test_init_errors_when_john_exists_without_force(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            # First init succeeds
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            # Second init without --force errors
            rc, out, err = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 1)
            self.assertFalse(out["success"])
            self.assertIn(".john/", out["error"])
            self.assertIn("--force", err)

    def test_init_force_recreates_john_dir(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            # Drop a marker file inside .john so we can confirm it's gone after --force
            marker = tdp / ".john" / "marker.txt"
            marker.write_text("before-force")
            rc, out, err = run_script("init_workspace.py", "--force", cwd=tdp)
            self.assertEqual(rc, 0, f"stderr: {err}")
            self.assertTrue(out["success"])
            self.assertFalse(marker.exists(), "marker should be gone after --force recreate")

    def test_init_copies_input_directory(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            # Build a source dir with some files
            src = tdp / "src-materials"
            src.mkdir()
            (src / "alpha.txt").write_text("alpha contents")
            (src / "beta.md").write_text("# beta")
            # Hidden file should be skipped
            (src / ".hidden").write_text("hidden")

            project = tdp / "project"
            project.mkdir()
            rc, out, err = run_script(
                "init_workspace.py", str(src), cwd=project
            )
            self.assertEqual(rc, 0, f"stderr: {err}")
            self.assertTrue(out["success"])
            self.assertTrue((project / ".john" / "input" / "alpha.txt").is_file())
            self.assertTrue((project / ".john" / "input" / "beta.md").is_file())
            self.assertFalse(
                (project / ".john" / "input" / ".hidden").exists(),
                "hidden files should be skipped",
            )
            self.assertEqual(len(out["copied_input"]), 2)

    def test_init_copies_input_single_file(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            src = tdp / "one.pdf"
            src.write_bytes(b"%PDF-1.4 fake")
            project = tdp / "project"
            project.mkdir()
            rc, out, err = run_script(
                "init_workspace.py", str(src), cwd=project
            )
            self.assertEqual(rc, 0, f"stderr: {err}")
            self.assertTrue((project / ".john" / "input" / "one.pdf").is_file())

    def test_init_errors_on_missing_input_path(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, out, err = run_script(
                "init_workspace.py", str(tdp / "nope"), cwd=tdp
            )
            self.assertEqual(rc, 1)
            self.assertFalse(out["success"])

    def test_init_does_not_overwrite_existing_claude_md(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            existing = tdp / "CLAUDE.md"
            existing.write_text("user's existing content")
            rc, out, err = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            self.assertEqual(existing.read_text(), "user's existing content")
            self.assertFalse(out["claude_md_written"])

    def test_init_does_not_overwrite_existing_plan_md_without_force(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / "PLAN.md").write_text("user's existing plan")
            rc, out, err = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            self.assertEqual((tdp / "PLAN.md").read_text(), "user's existing plan")
            self.assertFalse(out["plan_md_written"])


if __name__ == "__main__":
    unittest.main()
