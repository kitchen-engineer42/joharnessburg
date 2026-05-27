"""Tests for scripts/post_tool_use_hook.py."""

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
                {"cwd": str(tdp), "tool_name": "Read", "tool_result": "x" * 10000},
                cwd=tdp,
            )
            self.assertEqual(rc, 0)
            self.assertEqual(out, {})

    def test_small_result_passes_through(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()
            rc, out, _ = run_hook(
                {"cwd": str(tdp), "tool_name": "Read", "tool_result": "small result"},
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
                {"cwd": str(tdp), "tool_name": "Read", "tool_result": big_result},
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

    def test_identical_results_dedup(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()
            big_result = "L" * 5000

            # Run twice with the same result
            run_hook({"cwd": str(tdp), "tool_name": "Read", "tool_result": big_result}, cwd=tdp)
            run_hook({"cwd": str(tdp), "tool_name": "Read", "tool_result": big_result}, cwd=tdp)

            trace_dir = tdp / ".john" / "trace"
            files = list(trace_dir.iterdir())
            # Same content → same SHA → single file (deduped)
            self.assertEqual(len(files), 1)

    def test_different_results_different_files(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()

            run_hook({"cwd": str(tdp), "tool_name": "Read", "tool_result": "A" * 5000}, cwd=tdp)
            run_hook({"cwd": str(tdp), "tool_name": "Read", "tool_result": "B" * 5000}, cwd=tdp)

            trace_dir = tdp / ".john" / "trace"
            files = list(trace_dir.iterdir())
            self.assertEqual(len(files), 2)

    def test_handles_non_string_tool_result(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()
            rc, out, _ = run_hook(
                {"cwd": str(tdp), "tool_name": "Read", "tool_result": {"not": "a string"}},
                cwd=tdp,
            )
            self.assertEqual(rc, 0)
            # Should pass through without crashing
            self.assertEqual(out, {})

    def test_digest_contains_offload_path(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".john").mkdir()
            big_result = "Z" * 5000
            rc, out, _ = run_hook(
                {"cwd": str(tdp), "tool_name": "Bash", "tool_result": big_result},
                cwd=tdp,
            )
            digest = out["hookSpecificOutput"]["updatedToolOutput"]
            expected_sha = hashlib.sha256(big_result.encode()).hexdigest()[:16]
            self.assertIn(expected_sha, digest)


if __name__ == "__main__":
    unittest.main()
