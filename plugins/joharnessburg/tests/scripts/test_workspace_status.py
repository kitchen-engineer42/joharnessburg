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
            self.assertTrue(out["agents_md_present"])
            inv = out["inventory"]
            self.assertEqual(inv["input_files"], 0)
            self.assertEqual(inv["parsed_dirs"], 0)
            self.assertEqual(inv["events_phases"], [])
            self.assertEqual(inv["produced_skills"], {"claude": 0, "codex": 0})
            self.assertEqual(out["phase_provenance"]["current_phase"], "bootstrap")
            self.assertFalse(out["phase_provenance"]["current_phase_backed"])
            self.assertEqual(out["phase_provenance"]["skill_log_phases"], [])
            self.assertEqual(out["phase_provenance"]["skill_log_unbacked"], [])

    def test_status_works_from_project_subdirectory(self):
        # v0.2.3: CLI scripts walk up to the nearest .john/ — running from a
        # project subdirectory reports the same workspace.
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            subdir = tdp / "app" / "src"
            subdir.mkdir(parents=True)
            rc, out, err = run_script("workspace_status.py", "--quiet", cwd=subdir)
            self.assertEqual(rc, 0, f"stderr: {err}")
            self.assertEqual(Path(out["project_root"]).resolve(), tdp.resolve())

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
            (tdp / ".john" / "knowledge" / "entry-001" / "entry.md").write_text("# entry")

            rc, out, _ = run_script("workspace_status.py", "--quiet", cwd=tdp)
            self.assertEqual(rc, 0)
            inv = out["inventory"]
            self.assertEqual(inv["input_files"], 2)
            self.assertEqual(inv["events_phases"], ["extract"])
            self.assertEqual(inv["knowledge_entries"], 1)

    def test_status_exposes_current_phase_backing(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            ws_path = tdp / ".john" / "workspace.json"
            ws = json.loads(ws_path.read_text())
            ws["current_phase"] = "extract"
            ws_path.write_text(json.dumps(ws))
            (tdp / ".john" / "events" / "extract").mkdir()
            skill_log = tdp / ".john" / "skill-log"
            skill_log.mkdir(exist_ok=True)
            (skill_log / "app-design.json").write_text(json.dumps({
                "schema_version": 1,
                "timestamp": "2026-06-12T00:00:00+00:00",
                "skill": "john:app-design-thinking",
                "phase": "app-design",
            }))

            rc, out, err = run_script("workspace_status.py", cwd=tdp)
            self.assertEqual(rc, 0, f"stderr: {err}")
            pp = out["phase_provenance"]
            self.assertEqual(pp["event_checkpoint_backed"], ["extract"])
            self.assertEqual(pp["current_phase"], "extract")
            self.assertTrue(pp["current_phase_backed"])
            self.assertEqual(pp["skill_log_phases"], ["app-design"])
            self.assertEqual(pp["skill_log_unbacked"], ["app-design"])
            self.assertNotIn("not backed", err)
            self.assertIn("skill-log", err)

            ws["current_phase"] = "app-build"
            ws_path.write_text(json.dumps(ws))
            rc, out, err = run_script("workspace_status.py", cwd=tdp)
            self.assertEqual(rc, 0)
            pp = out["phase_provenance"]
            self.assertEqual(pp["current_phase"], "app-build")
            self.assertFalse(pp["current_phase_backed"])
            self.assertEqual(pp["skill_log_unbacked"], ["app-design"])
            self.assertIn("current_phase has no event/checkpoint backing", err)

    def test_status_errors_on_missing_workspace_json(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()
            rc, out, _ = run_script("workspace_status.py", cwd=tdp)
            self.assertEqual(rc, 1)
            self.assertFalse(out["success"])


if __name__ == "__main__":
    unittest.main()
