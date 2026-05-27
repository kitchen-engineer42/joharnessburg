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
                "set_template.py", "nonexistent-template-xyz", "--no-apply", cwd=tdp
            )
            self.assertEqual(rc, 1)
            self.assertFalse(out["success"])
            self.assertIn("not installed", out["error"])

    def test_clear_unsets_active_template(self):
        # Use --no-apply to skip reset_john.py subprocess (which would touch
        # the real ~/.claude/plugins/joharnessburg-applied/). Tests of clear's
        # workspace.json write behavior should be isolated from apply/reset.
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            # Manually set a value in workspace.json so clear has something to undo
            ws_path = tdp / ".john" / "workspace.json"
            state = json.loads(ws_path.read_text())
            state["active_template"] = "doc-verification"
            ws_path.write_text(json.dumps(state, indent=2))

            rc, out, _ = run_script("set_template.py", "--clear", "--no-apply", cwd=tdp)
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
                "set_template.py", "anything", "--clear", "--no-apply", cwd=tdp
            )
            self.assertEqual(rc, 1)
            self.assertFalse(out["success"])

    # v0.1.9 — Codex #2: atomic set_template (apply before workspace.json write)
    def test_set_apply_failure_does_not_mutate_active_template(self):
        # When apply_template.py fails (e.g., can't resolve john_install),
        # workspace.json's active_template field must NOT be set to the new
        # template. Instead, forensic fields go under session_metadata.
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)

            # Create a templates-root containing a template directory so the
            # name validation passes in set_template.
            templates_root = tdp / "templates"
            templates_root.mkdir()
            (templates_root / "test-tpl").mkdir()
            (templates_root / "test-tpl" / "template.json").write_text(
                json.dumps({"name": "test-tpl", "version": "0.1.0"})
            )

            # Init the project workspace so set_template's "needs .john/" check passes
            project = tdp / "project"
            project.mkdir()
            rc, _, _ = run_script("init_workspace.py", cwd=project)
            self.assertEqual(rc, 0)

            # Force apply_template to fail by pointing $JOHN_PLUGIN_INSTALL at a
            # nonexistent dir. set_template invokes apply_template via subprocess,
            # which inherits env; apply_template's resolve_john_install() will
            # see the bad env value and return None.
            rc, out, err = run_script(
                "set_template.py",
                "test-tpl",
                "--templates-root", str(templates_root),
                cwd=project,
                env_override={"JOHN_PLUGIN_INSTALL": str(tdp / "does-not-exist")},
            )
            self.assertEqual(rc, 1, f"stdout: {out}, stderr: {err}")
            self.assertFalse(out["success"])
            self.assertEqual(out["active_template_pending"], "test-tpl")
            self.assertIn("active_template_error", out)
            self.assertIsNone(out["active_template"])  # unchanged

            # workspace.json must NOT show test-tpl as active
            state = json.loads((project / ".john" / "workspace.json").read_text())
            self.assertIsNone(state.get("active_template"))
            # Forensic fields under session_metadata
            self.assertEqual(
                state["session_metadata"].get("active_template_pending"),
                "test-tpl",
            )
            self.assertIn(
                "active_template_error",
                state["session_metadata"],
            )
            self.assertIn(
                "active_template_attempted_at",
                state["session_metadata"],
            )

    def test_set_no_apply_commits_template_without_running_apply(self):
        # The --no-apply escape hatch: skip apply entirely + commit the template.
        # Used for debug/dev or when the user wants to apply manually later.
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            templates_root = tdp / "templates"
            templates_root.mkdir()
            (templates_root / "test-tpl").mkdir()
            (templates_root / "test-tpl" / "template.json").write_text(
                json.dumps({"name": "test-tpl", "version": "0.1.0"})
            )

            project = tdp / "project"
            project.mkdir()
            rc, _, _ = run_script("init_workspace.py", cwd=project)
            self.assertEqual(rc, 0)

            rc, out, err = run_script(
                "set_template.py",
                "test-tpl",
                "--templates-root", str(templates_root),
                "--no-apply",
                cwd=project,
            )
            self.assertEqual(rc, 0, f"stderr: {err}")
            self.assertTrue(out["success"])
            self.assertEqual(out["active_template"], "test-tpl")

            state = json.loads((project / ".john" / "workspace.json").read_text())
            self.assertEqual(state["active_template"], "test-tpl")
            # No pending/error fields when --no-apply succeeds
            self.assertNotIn(
                "active_template_pending",
                state["session_metadata"],
            )

    def test_set_success_clears_stale_pending_forensics(self):
        # If a previous attempt failed (leaving pending/error fields), a
        # subsequent successful attempt should clean them up.
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            templates_root = tdp / "templates"
            templates_root.mkdir()
            (templates_root / "test-tpl").mkdir()
            (templates_root / "test-tpl" / "template.json").write_text(
                json.dumps({"name": "test-tpl", "version": "0.1.0"})
            )

            project = tdp / "project"
            project.mkdir()
            rc, _, _ = run_script("init_workspace.py", cwd=project)
            self.assertEqual(rc, 0)

            # Pre-populate forensic fields as if from a prior failed attempt
            ws_path = project / ".john" / "workspace.json"
            state = json.loads(ws_path.read_text())
            state["session_metadata"]["active_template_pending"] = "stale-attempt"
            state["session_metadata"]["active_template_error"] = "synthetic stale error"
            state["session_metadata"]["active_template_attempted_at"] = "2026-01-01T00:00:00+00:00"
            ws_path.write_text(json.dumps(state, indent=2))

            # Now run a successful --no-apply set (apply is mocked off so this
            # proves the cleanup happens on the success path).
            rc, out, _ = run_script(
                "set_template.py",
                "test-tpl",
                "--templates-root", str(templates_root),
                "--no-apply",
                cwd=project,
            )
            self.assertEqual(rc, 0)
            new_state = json.loads(ws_path.read_text())
            self.assertEqual(new_state["active_template"], "test-tpl")
            self.assertNotIn("active_template_pending", new_state["session_metadata"])
            self.assertNotIn("active_template_error", new_state["session_metadata"])
            self.assertNotIn("active_template_attempted_at", new_state["session_metadata"])


if __name__ == "__main__":
    unittest.main()
