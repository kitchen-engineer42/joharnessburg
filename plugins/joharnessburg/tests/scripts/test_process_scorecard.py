"""Tests for scripts/process_scorecard.py.

The scorecard is the frozen-rubric evolution instrument: strictly read-only,
deterministic (byte-identical across runs modulo generated_at), and it never
reads corpus content — only .john/ structure and metadata.
"""

import json
import tempfile
import unittest
from pathlib import Path

from tests._helpers import run_script


def _build_fixture(tdp: Path):
    """A synthetic .john/ exercising every rubric section."""
    john = tdp / ".john"
    for sub in ("input", "events/extract", "events/parse", "checkpoints/extract/gates",
                "checkpoints/rewrite", "skill-log", "lessons", "trace"):
        (john / sub).mkdir(parents=True)

    (john / "workspace.json").write_text(json.dumps({
        "name": "joharnessburg-workspace",
        "schema_version": 1,
        "initialized_at": "2026-06-12T00:00:00+00:00",
        "created_by_john_version": "0.3.0",
        "current_phase": "extract",
        "session_metadata": {"endurance_goal": "build it"},
    }))
    (john / "input" / "corpus.pdf").write_bytes(b"x" * 1000)
    (john / "input" / "notes.md").write_text("y" * 50)

    # extract: 3 events from 2 subagents + 1 unparseable + checkpoint + gate record
    for i, sid in enumerate(["sub-a", "sub-a", "sub-b"]):
        (john / "events" / "extract" / f"e{i}.json").write_text(json.dumps({
            "event_type": "entry_extracted", "subagent_id": sid,
            "timestamp": f"2026-06-12T00:00:0{i}Z", "entry_id": f"e_{i}",
        }))
    (john / "events" / "extract" / "bad.json").write_text("not json {{")
    (john / "checkpoints" / "extract" / "state.json").write_text(json.dumps({
        "phase": "extract", "incomplete_chunks": [{"chunk_id": "c9", "missing": ["chunk_echo"]}],
    }))
    (john / "checkpoints" / "extract" / "gates" / "20260612T000100Z.json").write_text(json.dumps({
        "timestamp": "2026-06-12T00:01:00+00:00", "phase": "extract",
        "gate": {"expected_min": 3, "expected_max": 5, "actual": 3, "status": "pass"},
        "verify": {"orphans": ["zz"], "missing_on_disk": []},
        "entries_claimed": 3, "events_folded": 3, "exit_code": 0,
    }))

    # parse: zero events (dir exists, empty); rewrite: checkpoint only, no events dir
    (john / "checkpoints" / "rewrite" / "state.json").write_text(json.dumps({"phase": "rewrite"}))

    # skill-log: 2 invocations, one unattributed
    (john / "skill-log" / "a-john-chunking.json").write_text(json.dumps({
        "schema_version": 1, "timestamp": "2026-06-12T00:00:00+00:00",
        "skill": "john:chunking", "args_chars": 10, "phase": "extract",
    }))
    (john / "skill-log" / "b-john-using-john.json").write_text(json.dumps({
        "schema_version": 1, "timestamp": "2026-06-12T00:00:01+00:00",
        "skill": "john:using-john", "args_chars": 0, "phase": None,
    }))

    (john / "lessons" / "l1.json").write_text(json.dumps({
        "schema_version": 1, "condition": "chunking tables", "lesson": "split by row group",
        "evidence": [".john/events/extract/e0.json"], "scope_guess": "template",
    }))
    return john


def _strip_volatile(report: dict) -> dict:
    report = dict(report)
    report.pop("generated_at", None)
    return report


class TestProcessScorecard(unittest.TestCase):
    def test_scorecard_fields_on_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            _build_fixture(tdp)
            rc, out, err = run_script("process_scorecard.py", cwd=tdp)
            self.assertEqual(rc, 0, f"stderr: {err}")
            self.assertEqual(out["rubric_version"], 1)
            m = out["manifest"]
            self.assertEqual(m["created_by_john_version"], "0.3.0")
            self.assertEqual(m["input_files"], 2)
            self.assertEqual(m["input_total_bytes"], 1050)
            self.assertTrue(m["endurance_goal_set"])

            ph = out["phases"]
            self.assertEqual(set(ph), {"extract", "parse", "rewrite"})
            ex = ph["extract"]
            self.assertEqual(ex["events"], 3)
            self.assertEqual(ex["unparseable_events"], 1)
            self.assertEqual(ex["distinct_subagents"], 2)
            self.assertEqual(ex["event_types"], {"entry_extracted": 3})
            self.assertTrue(ex["checkpoint_present"])
            self.assertEqual(ex["incomplete_chunks"], 1)
            self.assertEqual(ex["gate_runs"], 1)
            self.assertEqual(ex["gates"][0]["gate_status"], "pass")
            self.assertEqual(ex["gates"][0]["verify_orphans"], 1)
            # The silent-skip floor: phases with zero folded events
            self.assertEqual(out["zero_event_phases"], ["parse", "rewrite"])

            si = out["skill_invocations"]
            self.assertTrue(si["recording_available"])
            self.assertEqual(si["total"], 2)
            self.assertEqual(si["per_skill"]["john:chunking"], 1)
            self.assertEqual(si["per_phase"]["(unattributed)"], 1)

            self.assertEqual(out["lessons"]["total"], 1)
            self.assertEqual(out["lessons"]["by_scope"], {"template": 1})
            self.assertIn("n/a", out["interventions"])

    def test_deterministic_and_read_only(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            _build_fixture(tdp)
            before = sorted(str(p) for p in tdp.rglob("*"))
            rc1, out1, _ = run_script("process_scorecard.py", "--quiet", cwd=tdp)
            rc2, out2, _ = run_script("process_scorecard.py", "--quiet", cwd=tdp)
            after = sorted(str(p) for p in tdp.rglob("*"))
            self.assertEqual(rc1, 0)
            self.assertEqual(rc2, 0)
            self.assertEqual(_strip_volatile(out1), _strip_volatile(out2))
            self.assertEqual(before, after, "scorecard must be strictly read-only")

    def test_errors_when_no_workspace(self):
        with tempfile.TemporaryDirectory() as td:
            rc, out, _ = run_script("process_scorecard.py", cwd=Path(td))
            self.assertEqual(rc, 1)
            self.assertFalse(out["success"])

    def test_root_flag_and_template_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            _build_fixture(tdp)
            meta = tdp / "applied-metadata.json"
            meta.write_text(json.dumps({
                "template_name": "doc-verification",
                "template_version": "0.1.1",
                "applied_at": "2026-06-12T00:00:00+00:00",
                "template_root_at_apply": "/Users/someone/secret-path/tpl",
                "john_install_at_apply": "/Users/someone/other-path",
            }))
            rc, out, _ = run_script(
                "process_scorecard.py",
                "--root", str(tdp),
                "--applied-metadata", str(meta),
                "--quiet",
                cwd=Path(td),
            )
            self.assertEqual(rc, 0)
            t = out["manifest"]["template"]
            self.assertEqual(t["template_name"], "doc-verification")
            self.assertEqual(t["template_version"], "0.1.1")
            # Local filesystem paths must NOT flow into the (shareable) scorecard
            self.assertNotIn("secret-path", json.dumps(out))

    def test_works_from_project_subdirectory(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            _build_fixture(tdp)
            sub = tdp / "app"
            sub.mkdir()
            rc, out, _ = run_script("process_scorecard.py", "--quiet", cwd=sub)
            self.assertEqual(rc, 0)
            self.assertEqual(out["manifest"]["input_files"], 2)


if __name__ == "__main__":
    unittest.main()
