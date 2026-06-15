"""Tests for scripts/precompact_hook.py."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests._helpers import SCRIPTS_DIR


def run_hook(stdin_data: dict, cwd: Path = None):
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "precompact_hook.py")],
        input=json.dumps(stdin_data),
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
    )
    try:
        stdout = json.loads(proc.stdout) if proc.stdout.strip() else None
    except json.JSONDecodeError:
        stdout = None
    return proc.returncode, stdout, proc.stderr


class TestPrecompactHook(unittest.TestCase):
    def test_no_op_when_no_john_dir(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, out, _ = run_hook({"cwd": str(tdp)}, cwd=tdp)
            self.assertEqual(rc, 0)
            self.assertEqual(out, {})

    def test_writes_snapshot_when_john_active(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()
            (tdp / ".john" / "workspace.json").write_text(json.dumps({
                "schema_version": 1,
                "current_phase": "extract",
                "active_template": None,
            }))
            (tdp / "PLAN.md").write_text("# PLAN\n")
            (tdp / "CLAUDE.md").write_text("# CLAUDE\n")

            rc, out, _ = run_hook({"cwd": str(tdp), "reason": "context_full"}, cwd=tdp)
            self.assertEqual(rc, 0)
            self.assertIn("hookSpecificOutput", out)

            # Verify snapshot file exists in .john/checkpoints/
            checkpoints = tdp / ".john" / "checkpoints"
            self.assertTrue(checkpoints.exists())
            snapshots = list(checkpoints.glob("precompact-*.json"))
            self.assertEqual(len(snapshots), 1)

            # Verify snapshot contents
            snap = json.loads(snapshots[0].read_text())
            self.assertEqual(snap["workspace_state"]["current_phase"], "extract")
            self.assertIn("PLAN.md", snap["plan_md_path"])
            self.assertIn("CLAUDE.md", snap["claude_md_path"])

    def test_captures_recent_events(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()
            (tdp / ".john" / "workspace.json").write_text(json.dumps({"current_phase": "extract"}))
            events_dir = tdp / ".john" / "events" / "extract"
            events_dir.mkdir(parents=True)
            for i in range(5):
                (events_dir / f"evt-{i}.json").write_text(json.dumps({"i": i, "timestamp": f"2026-05-22T0{i}:00:00Z"}))

            rc, out, _ = run_hook({"cwd": str(tdp)}, cwd=tdp)
            self.assertEqual(rc, 0)
            snap_path = out["hookSpecificOutput"]["snapshotPath"]
            snap = json.loads(Path(snap_path).read_text())
            self.assertIn("extract", snap["recent_events"])
            self.assertEqual(len(snap["recent_events"]["extract"]), 5)

    def test_snapshots_from_project_subdirectory(self):
        # v0.2.3: compaction frequently hits while cwd is a project
        # subdirectory — the snapshot must land in the root .john/.
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()
            (tdp / ".john" / "workspace.json").write_text(json.dumps({
                "current_phase": "build",
            }))
            subdir = tdp / "app"
            subdir.mkdir()
            rc, out, _ = run_hook({"cwd": str(subdir)}, cwd=subdir)
            self.assertEqual(rc, 0)
            snapshots = list((tdp / ".john" / "checkpoints").glob("precompact-*.json"))
            self.assertEqual(len(snapshots), 1)

    def test_handles_missing_workspace_json(self):
        # .john/ exists but no workspace.json
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()
            rc, out, _ = run_hook({"cwd": str(tdp)}, cwd=tdp)
            self.assertEqual(rc, 0)
            # Should still write a snapshot (with empty workspace_state)
            snap_path = out["hookSpecificOutput"]["snapshotPath"]
            snap = json.loads(Path(snap_path).read_text())
            self.assertEqual(snap["workspace_state"], {})

    def test_handles_empty_stdin(self):
        rc, out, _ = run_hook({})
        self.assertEqual(rc, 0)
        # cwd defaults to "."; if "." has no .john/, no-op
        self.assertEqual(out, {})


if __name__ == "__main__":
    unittest.main()
