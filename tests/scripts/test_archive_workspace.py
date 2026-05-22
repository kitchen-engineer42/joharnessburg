"""Tests for scripts/archive_workspace.py."""

import tempfile
import unittest
import zipfile
from pathlib import Path

from tests._helpers import run_script


class TestArchiveWorkspace(unittest.TestCase):
    def test_archive_errors_when_no_john_dir(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, out, _ = run_script("archive_workspace.py", "test", cwd=tdp)
            self.assertEqual(rc, 1)
            self.assertFalse(out["success"])

    def test_archive_produces_zip_with_expected_paths(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            # Add a fake produced skill
            skill_dir = tdp / ".claude" / "skills" / "fake-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("---\nname: fake\ndescription: x\n---\n")

            rc, out, err = run_script(
                "archive_workspace.py", "shakedown", cwd=tdp
            )
            self.assertEqual(rc, 0, f"stderr: {err}")
            self.assertTrue(out["success"])
            self.assertGreater(out["file_count"], 0)

            archive = Path(out["archive_path"])
            self.assertTrue(archive.is_file())
            with zipfile.ZipFile(archive) as zf:
                names = zf.namelist()
            self.assertIn("PLAN.md", names)
            self.assertIn("CLAUDE.md", names)
            self.assertIn(".john/workspace.json", names)
            self.assertIn(".claude/skills/fake-skill/SKILL.md", names)

    def test_archive_excludes_cruft(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            # Add cruft
            (tdp / ".john" / ".DS_Store").write_text("cruft")
            pyc_dir = tdp / ".john" / "__pycache__"
            pyc_dir.mkdir()
            (pyc_dir / "x.pyc").write_text("cruft")
            (tdp / ".john" / "events" / "extract").mkdir()
            (tdp / ".john" / "events" / "extract" / "evt.pyo").write_text("cruft")

            rc, out, _ = run_script("archive_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            with zipfile.ZipFile(out["archive_path"]) as zf:
                names = zf.namelist()
            for cruft in [".DS_Store", "__pycache__", ".pyc", ".pyo"]:
                for n in names:
                    self.assertNotIn(cruft, n, f"cruft '{cruft}' should not be in archive, found in: {n}")

    def test_archive_errors_on_existing_output_without_force(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            out_path = tdp / "out.zip"
            out_path.write_text("placeholder")
            rc, out, _ = run_script(
                "archive_workspace.py", "--output", str(out_path), cwd=tdp
            )
            self.assertEqual(rc, 1)
            self.assertFalse(out["success"])
            # With --force should succeed
            rc, out, _ = run_script(
                "archive_workspace.py", "--output", str(out_path), "--force", cwd=tdp
            )
            self.assertEqual(rc, 0)
            self.assertTrue(out["success"])


if __name__ == "__main__":
    unittest.main()
