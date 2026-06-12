"""Tests for scripts/skill_invocation_hook.py.

Contract tests: stdin payloads use the documented PostToolUse input schema,
with `tool_name: "Skill"` and `tool_input.skill` / `tool_input.args` —
verified live against the harness (2026-06-12): the Skill matcher fires,
tool_input carries the namespaced skill name, and subagent-side invocations
flow through the parent session's hooks.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests._helpers import SCRIPTS_DIR


def run_hook(stdin_data: dict, cwd: Path = None):
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "skill_invocation_hook.py")],
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


def _scaffold(tdp: Path, phase: str = "extract"):
    (tdp / ".john").mkdir()
    (tdp / ".john" / "workspace.json").write_text(
        json.dumps({"schema_version": 1, "current_phase": phase})
    )


class TestSkillInvocationHook(unittest.TestCase):
    def test_records_invocation_with_phase(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            _scaffold(tdp, phase="extract")
            rc, out, _ = run_hook(
                {
                    "cwd": str(tdp),
                    "tool_name": "Skill",
                    "tool_input": {"skill": "john:chunking", "args": "corpus section 7"},
                },
                cwd=tdp,
            )
            self.assertEqual(rc, 0)
            self.assertEqual(out, {})
            records = list((tdp / ".john" / "skill-log").glob("*.json"))
            self.assertEqual(len(records), 1)
            data = json.loads(records[0].read_text())
            self.assertEqual(data["skill"], "john:chunking")
            self.assertEqual(data["phase"], "extract")
            self.assertEqual(data["schema_version"], 1)
            # Filename carries a sanitized slug
            self.assertIn("john-chunking", records[0].name)

    def test_args_content_never_stored(self):
        # Privacy: skill args routinely contain corpus text — only the LENGTH
        # may be recorded.
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            _scaffold(tdp)
            secret = "CONFIDENTIAL-CONTRACT-CLAUSE-§17"
            run_hook(
                {
                    "cwd": str(tdp),
                    "tool_name": "Skill",
                    "tool_input": {"skill": "john:parsing", "args": secret},
                },
                cwd=tdp,
            )
            record = next((tdp / ".john" / "skill-log").glob("*.json"))
            raw = record.read_text()
            self.assertNotIn(secret, raw)
            self.assertEqual(json.loads(raw)["args_chars"], len(secret))

    def test_no_op_without_john_dir(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, out, _ = run_hook(
                {"cwd": str(tdp), "tool_name": "Skill", "tool_input": {"skill": "x"}},
                cwd=tdp,
            )
            self.assertEqual(rc, 0)
            self.assertEqual(out, {})
            self.assertFalse((tdp / ".john").exists())

    def test_no_op_for_other_tools(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            _scaffold(tdp)
            rc, out, _ = run_hook(
                {"cwd": str(tdp), "tool_name": "Bash", "tool_input": {"command": "ls"}},
                cwd=tdp,
            )
            self.assertEqual(rc, 0)
            self.assertEqual(out, {})
            self.assertFalse((tdp / ".john" / "skill-log").exists())

    def test_records_from_project_subdirectory(self):
        # The session cwd is often a subdirectory — the record must land in
        # the project root's .john/, not no-op (same walk-up as other hooks).
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            _scaffold(tdp)
            sub = tdp / "app" / "src"
            sub.mkdir(parents=True)
            rc, _, _ = run_hook(
                {"cwd": str(sub), "tool_name": "Skill", "tool_input": {"skill": "john:packaging"}},
                cwd=sub,
            )
            self.assertEqual(rc, 0)
            self.assertEqual(len(list((tdp / ".john" / "skill-log").glob("*.json"))), 1)

    def test_malformed_stdin_is_safe(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "skill_invocation_hook.py")],
            input="not json {{",
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(json.loads(proc.stdout), {})

    def test_missing_workspace_json_still_records(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()  # no workspace.json
            rc, _, _ = run_hook(
                {"cwd": str(tdp), "tool_name": "Skill", "tool_input": {"skill": "john:using-john"}},
                cwd=tdp,
            )
            self.assertEqual(rc, 0)
            record = next((tdp / ".john" / "skill-log").glob("*.json"))
            self.assertIsNone(json.loads(record.read_text())["phase"])


if __name__ == "__main__":
    unittest.main()
