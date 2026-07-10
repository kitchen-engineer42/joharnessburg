"""Tests for the append-only atomic event writer."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests._helpers import SCRIPTS_DIR, run_script


class TestEmitEvent(unittest.TestCase):
    def test_injects_envelope_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=root)
            self.assertEqual(rc, 0)
            command = [
                sys.executable,
                str(SCRIPTS_DIR / "emit_event.py"),
                "--phase",
                "extract",
                "--work-unit-id",
                "chunk-01",
                "--agent-id",
                "auditor-1",
                "--audit-run-id",
                "run-1",
            ]
            body = json.dumps(
                {
                    "event_type": "coverage_audit_complete",
                    "chunk_id": "chunk-01",
                    "event_id": "caller-must-not-control-this",
                    "timestamp": "1900-01-01T00:00:00Z",
                }
            )
            outputs = []
            for _ in range(2):
                result = subprocess.run(
                    command,
                    input=body,
                    text=True,
                    capture_output=True,
                    cwd=root,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                outputs.append(json.loads(result.stdout))
            self.assertNotEqual(outputs[0]["event_file"], outputs[1]["event_file"])
            files = sorted((root / ".john/events/extract/chunk-01").glob("*.json"))
            self.assertEqual(len(files), 2)
            events = [json.loads(path.read_text()) for path in files]
            self.assertEqual({e["agent_id"] for e in events}, {"auditor-1"})
            self.assertEqual({e["audit_run_id"] for e in events}, {"run-1"})
            self.assertEqual(len({e["event_id"] for e in events}), 2)
            self.assertTrue(all(e["timestamp"].endswith("Z") for e in events))

    def test_rejects_traversal_and_mismatched_work_unit(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_script("init_workspace.py", cwd=root)
            base = [sys.executable, str(SCRIPTS_DIR / "emit_event.py")]
            result = subprocess.run(
                base
                + [
                    "--phase",
                    "../outside",
                    "--agent-id",
                    "a",
                    "--audit-run-id",
                    "r",
                ],
                input='{"event_type":"x"}',
                text=True,
                capture_output=True,
                cwd=root,
            )
            self.assertEqual(result.returncode, 1)
            self.assertFalse((root.parent / "outside").exists())

            result = subprocess.run(
                base
                + [
                    "--phase",
                    "extract",
                    "--work-unit-id",
                    "chunk-1",
                    "--agent-id",
                    "a",
                    "--audit-run-id",
                    "r",
                ],
                input='{"event_type":"x","chunk_id":"chunk-2"}',
                text=True,
                capture_output=True,
                cwd=root,
            )
            self.assertEqual(result.returncode, 1)
            self.assertFalse((root / ".john/events/extract").exists())

    def test_rejects_internal_symlink_component(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_script("init_workspace.py", cwd=root)
            events = root / ".john/events"
            actual = events / "actual"
            actual.mkdir()
            os.symlink(actual, events / "extract")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS_DIR / "emit_event.py"),
                    "--phase",
                    "extract",
                    "--work-unit-id",
                    "chunk-1",
                    "--agent-id",
                    "auditor-1",
                    "--audit-run-id",
                    "audit-1",
                ],
                cwd=root,
                input=json.dumps({"event_type": "chunk_complete"}),
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("symlink", result.stderr)
            self.assertEqual(list(actual.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
