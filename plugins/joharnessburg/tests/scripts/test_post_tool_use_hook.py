"""Tests for scripts/post_tool_use_hook.py.

Contract tests: stdin payloads use the DOCUMENTED PostToolUse input schema
(code.claude.com/docs/en/hooks) — `tool_output_text` (string form), with
`tool_output` and `tool_response` as fallbacks. Do not invent field names
here; the suite must validate the harness's contract, not mirror the script.
"""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests._helpers import SCRIPTS_DIR


def run_hook(stdin_data: dict, cwd: Path = None):
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "post_tool_use_hook.py")],
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


class TestPostToolUseHook(unittest.TestCase):
    def test_no_op_when_no_john_dir(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, out, _ = run_hook(
                {"cwd": str(tdp), "tool_name": "Read", "tool_output_text": "x" * 10000},
                cwd=tdp,
            )
            self.assertEqual(rc, 0)
            self.assertEqual(out, {})

    def test_small_result_passes_through(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()
            rc, out, _ = run_hook(
                {"cwd": str(tdp), "tool_name": "Read", "tool_output_text": "small result"},
                cwd=tdp,
            )
            self.assertEqual(rc, 0)
            self.assertEqual(out, {})

    def test_large_result_offloaded(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()
            big_result = "L" * 5000
            rc, out, _ = run_hook(
                {"cwd": str(tdp), "tool_name": "Read", "tool_output_text": big_result},
                cwd=tdp,
            )
            self.assertEqual(rc, 0)
            self.assertIn("hookSpecificOutput", out)
            self.assertIn("updatedToolOutput", out["hookSpecificOutput"])
            digest = out["hookSpecificOutput"]["updatedToolOutput"]
            # Digest should include HEAD + TAIL + offload path reference
            self.assertIn("HEAD", digest)
            self.assertIn("TAIL", digest)
            self.assertIn("trace", digest)

            # Offload file should exist with deterministic SHA-based name
            trace_dir = tdp / ".john" / "trace"
            self.assertTrue(trace_dir.exists())
            files = list(trace_dir.iterdir())
            self.assertEqual(len(files), 1)
            offload = files[0]
            self.assertEqual(offload.read_text(), big_result)
            # Filename should include tool name + SHA prefix
            self.assertTrue(offload.name.startswith("Read-"))
            self.assertTrue(offload.name.endswith(".txt"))

    def test_tool_output_field_accepted(self):
        """`tool_output` (string) is honored when `tool_output_text` is absent."""
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()
            rc, out, _ = run_hook(
                {"cwd": str(tdp), "tool_name": "Bash", "tool_output": "O" * 5000},
                cwd=tdp,
            )
            self.assertEqual(rc, 0)
            self.assertIn("updatedToolOutput", out["hookSpecificOutput"])

    def test_tool_response_dict_serialized_and_offloaded(self):
        """Older-harness `tool_response` may be structured; large ones still offload."""
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()
            rc, out, _ = run_hook(
                {
                    "cwd": str(tdp),
                    "tool_name": "Read",
                    "tool_response": {"content": "R" * 5000, "success": True},
                },
                cwd=tdp,
            )
            self.assertEqual(rc, 0)
            self.assertIn("updatedToolOutput", out["hookSpecificOutput"])
            trace_dir = tdp / ".john" / "trace"
            files = list(trace_dir.iterdir())
            self.assertEqual(len(files), 1)
            # Serialized JSON of the response was offloaded
            self.assertIn("R" * 100, files[0].read_text())

    def test_small_structured_response_passes_through(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()
            rc, out, _ = run_hook(
                {"cwd": str(tdp), "tool_name": "Read", "tool_response": {"ok": True}},
                cwd=tdp,
            )
            self.assertEqual(rc, 0)
            self.assertEqual(out, {})

    def test_legacy_invented_field_is_ignored(self):
        """`tool_result` was never part of the documented contract; the hook
        must not rely on it (regression guard for the pre-v0.2.2 bug where the
        hook read only this field and therefore never fired)."""
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()
            rc, out, _ = run_hook(
                {"cwd": str(tdp), "tool_name": "Read", "tool_result": "x" * 5000},
                cwd=tdp,
            )
            self.assertEqual(rc, 0)
            self.assertEqual(out, {})
            self.assertFalse((tdp / ".john" / "trace").exists())

    def test_threshold_boundary(self):
        """2047 chars passes through; 2048 (== OFFLOAD_THRESHOLD) offloads."""
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()
            rc, out, _ = run_hook(
                {"cwd": str(tdp), "tool_name": "Read", "tool_output_text": "b" * 2047},
                cwd=tdp,
            )
            self.assertEqual(out, {})
            rc, out, _ = run_hook(
                {"cwd": str(tdp), "tool_name": "Read", "tool_output_text": "b" * 2048},
                cwd=tdp,
            )
            self.assertIn("updatedToolOutput", out["hookSpecificOutput"])

    def test_tool_name_path_traversal_sanitized(self):
        """A crafted tool_name must not escape .john/trace/."""
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()
            rc, out, _ = run_hook(
                {
                    "cwd": str(tdp),
                    "tool_name": "../../etc/passwd",
                    "tool_output_text": "T" * 5000,
                },
                cwd=tdp,
            )
            self.assertEqual(rc, 0)
            trace_dir = tdp / ".john" / "trace"
            files = list(trace_dir.iterdir())
            self.assertEqual(len(files), 1)
            # Only the sanitized filename component survives
            self.assertTrue(files[0].name.startswith("passwd-"))
            # Nothing was written outside the trace dir
            self.assertFalse((tdp / "etc").exists())
            self.assertFalse((tdp.parent / "etc").exists())

    def test_offloads_from_project_subdirectory(self):
        # v0.2.3: the session cwd is often a project subdirectory — the
        # offload must land in the project root's .john/trace/, not no-op.
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()
            subdir = tdp / "app"
            subdir.mkdir()
            rc, out, _ = run_hook(
                {"cwd": str(subdir), "tool_name": "Bash", "tool_output_text": "S" * 5000},
                cwd=subdir,
            )
            self.assertEqual(rc, 0)
            digest = out["hookSpecificOutput"]["updatedToolOutput"]
            # Offload written under the PROJECT ROOT's .john/trace/
            files = list((tdp / ".john" / "trace").iterdir())
            self.assertEqual(len(files), 1)
            # Pointer is relative to the session cwd (one level up)
            self.assertIn("../.john/trace/", digest)

    def test_identical_results_dedup(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()
            big_result = "L" * 5000

            # Run twice with the same result
            run_hook({"cwd": str(tdp), "tool_name": "Read", "tool_output_text": big_result}, cwd=tdp)
            run_hook({"cwd": str(tdp), "tool_name": "Read", "tool_output_text": big_result}, cwd=tdp)

            trace_dir = tdp / ".john" / "trace"
            files = list(trace_dir.iterdir())
            # Same content → same SHA → single file (deduped)
            self.assertEqual(len(files), 1)

    def test_different_results_different_files(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()

            run_hook({"cwd": str(tdp), "tool_name": "Read", "tool_output_text": "A" * 5000}, cwd=tdp)
            run_hook({"cwd": str(tdp), "tool_name": "Read", "tool_output_text": "B" * 5000}, cwd=tdp)

            trace_dir = tdp / ".john" / "trace"
            files = list(trace_dir.iterdir())
            self.assertEqual(len(files), 2)

    def test_digest_contains_offload_path(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()
            big_result = "Z" * 5000
            rc, out, _ = run_hook(
                {"cwd": str(tdp), "tool_name": "Bash", "tool_output_text": big_result},
                cwd=tdp,
            )
            digest = out["hookSpecificOutput"]["updatedToolOutput"]
            expected_sha = hashlib.sha256(big_result.encode()).hexdigest()[:16]
            self.assertIn(expected_sha, digest)


if __name__ == "__main__":
    unittest.main()
