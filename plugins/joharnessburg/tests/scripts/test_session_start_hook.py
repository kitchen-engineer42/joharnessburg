"""Tests for scripts/session_start_hook.py.

Contract tests: per the documented SessionStart output schema
(code.claude.com/docs/en/hooks), context must be emitted as
`hookSpecificOutput.additionalContext` — a top-level `additionalContext`
is NOT honored by the harness (the script keeps a top-level copy only for
older harness versions). Assertions read the nested field.
"""

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
            # The documented field: hookSpecificOutput.additionalContext
            self.assertIn("additionalContext", out["hookSpecificOutput"])
            ctx = out["hookSpecificOutput"]["additionalContext"]
            # Verify key facts are in the injection
            self.assertIn("Build a biology quiz app", ctx)
            self.assertIn("slides-from-textbook", ctx)
            self.assertIn("extract", ctx)
            self.assertIn("PLAN.md", ctx)
            # Provider-neutral hook points each runtime at its own adapter.
            self.assertIn("active provider's adapter", ctx)
            self.assertIn("Codex uses native subagents", ctx)
            self.assertNotIn("You are in a Claude Code session", ctx)
            # v0.2.3: invoke-the-phase-skill nudge
            self.assertIn("Invoke skills", ctx)
            self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "SessionStart")
            # Legacy top-level copy kept for older harness versions
            self.assertEqual(out.get("additionalContext"), ctx)

    def test_injects_from_project_subdirectory(self):
        # v0.2.3 regression: a real session compacted while cwd was
        # <project>/app — the hook resolved .john/ only at cwd and silently
        # emitted {}, dropping the PLAN.md + endurance injection. The hook
        # must walk up to the nearest .john/.
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()
            (tdp / ".john" / "workspace.json").write_text(json.dumps({
                "schema_version": 1,
                "current_phase": "build",
                "session_metadata": {"endurance_goal": "ship the RPG"},
            }))
            (tdp / "PLAN.md").write_text("# PLAN.md — subdir test\n")
            subdir = tdp / "app" / "src"
            subdir.mkdir(parents=True)

            rc, out, _ = run_hook({"cwd": str(subdir)}, cwd=subdir)
            self.assertEqual(rc, 0)
            ctx = out["hookSpecificOutput"]["additionalContext"]
            self.assertIn("ship the RPG", ctx)
            self.assertIn("subdir test", ctx)

    def test_codex_uses_nested_supported_context_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".john").mkdir()
            (root / ".john/workspace.json").write_text(
                json.dumps({"current_phase": "extract", "session_metadata": {}})
            )
            (root / "PLAN.md").write_text("# Codex plan\n")
            rc, out, err = run_hook(
                {"cwd": str(root), "turn_id": "turn-codex-1", "source": "startup"},
                cwd=root,
            )
            self.assertEqual(rc, 0, err)
            self.assertEqual(set(out), {"hookSpecificOutput"})
            self.assertIn(
                "Codex plan", out["hookSpecificOutput"]["additionalContext"]
            )

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
            self.assertIn("additionalContext", out["hookSpecificOutput"])
            # Should fall back to a helpful placeholder
            self.assertIn("/john:endurance", out["hookSpecificOutput"]["additionalContext"])

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
            self.assertIn("truncated", out["hookSpecificOutput"]["additionalContext"])

    def test_handles_missing_plan_md(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()
            (tdp / ".john" / "workspace.json").write_text(json.dumps({"active_template": None}))
            # No PLAN.md

            rc, out, _ = run_hook({"cwd": str(tdp)}, cwd=tdp)
            self.assertEqual(rc, 0)
            self.assertIn("additionalContext", out["hookSpecificOutput"])
            self.assertIn("no PLAN.md", out["hookSpecificOutput"]["additionalContext"])

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
