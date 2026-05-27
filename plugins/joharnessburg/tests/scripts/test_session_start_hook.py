"""Tests for scripts/session_start_hook.py."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests._helpers import SCRIPTS_DIR


def run_hook(stdin_data: dict, cwd: Path = None, env_overrides: dict = None):
    """Run the session_start hook with stdin JSON; return (rc, stdout_json, stderr)."""
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "session_start_hook.py")],
        input=json.dumps(stdin_data),
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        env=env,
    )
    try:
        stdout = json.loads(proc.stdout) if proc.stdout.strip() else None
    except json.JSONDecodeError:
        stdout = None
    return proc.returncode, stdout, proc.stderr


class TestSessionStartHook(unittest.TestCase):
    def test_no_op_when_no_john_dir(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, out, _ = run_hook({"cwd": str(tdp)}, cwd=tdp)
            self.assertEqual(rc, 0)
            self.assertEqual(out, {})

    def test_emits_additional_context_when_john_active(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            # Set up a minimal John workspace (v0.1.15+: no active_template field)
            (tdp / ".john").mkdir()
            workspace_state = {
                "schema_version": 1,
                "initialized_at": "2026-05-22T10:00:00+00:00",
                "current_phase": "extract",
                "session_metadata": {"endurance_goal": "Build a biology quiz app"},
            }
            (tdp / ".john" / "workspace.json").write_text(json.dumps(workspace_state))
            (tdp / "PLAN.md").write_text("# PLAN.md — test project\n\nIntent: a quiz app.\n")

            # Simulate launching with a merged template plugin by pointing
            # CLAUDE_PLUGIN_ROOT at a fake joharnessburg-applied/<name>/ path.
            fake_plugin = Path.home() / ".claude" / "plugins" / "joharnessburg-applied" / "slides-from-textbook"
            rc, out, _ = run_hook(
                {"cwd": str(tdp)},
                cwd=tdp,
                env_overrides={"CLAUDE_PLUGIN_ROOT": str(fake_plugin)},
            )
            self.assertEqual(rc, 0)
            self.assertIn("additionalContext", out)
            ctx = out["additionalContext"]
            # Verify key facts are in the injection
            self.assertIn("Build a biology quiz app", ctx)
            self.assertIn("slides-from-textbook", ctx)
            self.assertIn("extract", ctx)
            self.assertIn("PLAN.md", ctx)
            self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "SessionStart")

    def test_handles_missing_endurance_goal(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()
            workspace_state = {
                "active_template": None,
                "current_phase": "bootstrap",
                "session_metadata": {},
            }
            (tdp / ".john" / "workspace.json").write_text(json.dumps(workspace_state))
            (tdp / "PLAN.md").write_text("# PLAN.md\n")

            rc, out, _ = run_hook({"cwd": str(tdp)}, cwd=tdp)
            self.assertEqual(rc, 0)
            self.assertIn("additionalContext", out)
            # Should fall back to a helpful placeholder
            self.assertIn("/endurance", out["additionalContext"])

    def test_truncates_long_plan_md(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()
            (tdp / ".john" / "workspace.json").write_text(json.dumps({
                "current_phase": "x",
                "active_template": None,
                "session_metadata": {},
            }))
            long_plan = "X" * 10000
            (tdp / "PLAN.md").write_text(long_plan)

            rc, out, _ = run_hook({"cwd": str(tdp)}, cwd=tdp)
            self.assertEqual(rc, 0)
            self.assertIn("truncated", out["additionalContext"])

    def test_handles_missing_plan_md(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()
            (tdp / ".john" / "workspace.json").write_text(json.dumps({"active_template": None}))
            # No PLAN.md

            rc, out, _ = run_hook({"cwd": str(tdp)}, cwd=tdp)
            self.assertEqual(rc, 0)
            self.assertIn("additionalContext", out)
            self.assertIn("no PLAN.md", out["additionalContext"])

    def test_handles_corrupt_workspace_json(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()
            (tdp / ".john" / "workspace.json").write_text("not valid json {{")

            rc, out, _ = run_hook({"cwd": str(tdp)}, cwd=tdp)
            # Hook should not break the session; emit empty
            self.assertEqual(rc, 0)
            self.assertEqual(out, {})

    def test_handles_empty_stdin(self):
        rc, out, _ = run_hook({})
        self.assertEqual(rc, 0)
        # cwd defaults to "."; if "." has no .john/, no-op
        self.assertEqual(out, {})


if __name__ == "__main__":
    unittest.main()
