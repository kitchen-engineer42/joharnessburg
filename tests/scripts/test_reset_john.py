"""Tests for scripts/reset_john.py.

Uses --applied-parent + JOHN_APPLIED_PARENT env to redirect away from the user's real
~/.claude/plugins/joharnessburg-applied/ during tests.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests._helpers import SCRIPTS_DIR


def run_reset(*args, applied_parent_override: Path = None):
    env = os.environ.copy()
    if applied_parent_override:
        env["JOHN_APPLIED_PARENT"] = str(applied_parent_override)
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "reset_john.py")] + list(args),
        env=env,
        capture_output=True,
        text=True,
    )
    try:
        stdout_json = json.loads(proc.stdout) if proc.stdout.strip() else None
    except json.JSONDecodeError:
        stdout_json = None
    return proc.returncode, stdout_json, proc.stderr


class TestResetJohn(unittest.TestCase):
    def test_reset_noop_when_no_applied_dir(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, out, _ = run_reset("--yes", applied_parent_override=tdp / "nonexistent")
            self.assertEqual(rc, 0)
            self.assertTrue(out["success"])
            self.assertEqual(out["applied_dirs"], [])
            self.assertEqual(out["deleted"], [])

    def test_reset_noop_when_applied_dir_empty(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            applied = tdp / "applied"
            applied.mkdir()
            rc, out, _ = run_reset("--yes", applied_parent_override=applied)
            self.assertEqual(rc, 0)
            self.assertTrue(out["success"])
            self.assertEqual(out["deleted"], [])

    def test_reset_refuses_without_yes_flag(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            applied = tdp / "applied"
            applied.mkdir()
            (applied / "fake-template").mkdir()
            (applied / "fake-template" / "marker.txt").write_text("hi")

            rc, out, _ = run_reset(applied_parent_override=applied)
            self.assertEqual(rc, 1)
            self.assertFalse(out["success"])
            # Dir still exists
            self.assertTrue((applied / "fake-template").is_dir())

    def test_reset_deletes_applied_dirs_with_yes(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            applied = tdp / "applied"
            applied.mkdir()
            (applied / "t1").mkdir()
            (applied / "t1" / "skill.md").write_text("content")
            (applied / "t2").mkdir()
            (applied / "t2" / "skill.md").write_text("content")

            rc, out, _ = run_reset("--yes", applied_parent_override=applied)
            self.assertEqual(rc, 0)
            self.assertTrue(out["success"])
            self.assertEqual(len(out["deleted"]), 2)
            self.assertFalse((applied / "t1").exists())
            self.assertFalse((applied / "t2").exists())

    def test_reset_list_does_not_delete(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            applied = tdp / "applied"
            applied.mkdir()
            (applied / "keep-me").mkdir()
            (applied / "keep-me" / "marker.txt").write_text("hi")

            rc, out, _ = run_reset("--list", applied_parent_override=applied)
            self.assertEqual(rc, 0)
            self.assertIn("applied_dirs", out)
            self.assertEqual(len(out["applied_dirs"]), 1)
            # Still there
            self.assertTrue((applied / "keep-me").exists())


if __name__ == "__main__":
    unittest.main()
