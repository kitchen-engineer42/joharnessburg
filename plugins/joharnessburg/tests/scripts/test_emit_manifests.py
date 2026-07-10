"""Tests for scripts/emit_manifests.py.

emit_manifests writes two LOCAL .john/ artifacts (PROVENANCE.json +
SELF_EVAL_MANIFEST.json) so a finished run is auditor-legible without reading app
code. It is standalone-by-default (vanilla runs emit both, template fields null),
idempotent, and reads only structure/metadata/event-timestamps — never corpus
content. Its phase list must agree with the scorecard's event/checkpoint-backed
phase universe.
"""

import json
import tempfile
import unittest
from pathlib import Path

from tests._helpers import run_script


def _build_fixture(tdp: Path):
    """A synthetic .john/ with events across two phases + a checkpoint-only phase."""
    john = tdp / ".john"
    for sub in ("input", "events/extract", "events/parse", "checkpoints/rewrite"):
        (john / sub).mkdir(parents=True)

    (john / "workspace.json").write_text(json.dumps({
        "name": "joharnessburg-workspace",
        "schema_version": 1,
        "initialized_at": "2026-06-12T00:00:00+00:00",
        "created_by_john_version": "0.4.2",
        "current_phase": "extract",
        "session_metadata": {"endurance_goal": "build it"},
    }))
    (john / "input" / "corpus.pdf").write_bytes(b"x" * 100)
    (john / "input" / "notes.md").write_text("y" * 20)

    # extract: two events, earliest + latest define the run window
    (john / "events" / "extract" / "e0.json").write_text(json.dumps({
        "event_type": "entry_extracted", "subagent_id": "sub-a",
        "timestamp": "2026-06-12T00:00:05Z", "entry_id": "e_0",
    }))
    (john / "events" / "extract" / "e1.json").write_text(json.dumps({
        "event_type": "entry_extracted", "subagent_id": "sub-b",
        "timestamp": "2026-06-12T00:09:00Z", "entry_id": "e_1",
    }))
    # parse: dir exists, no events; rewrite: checkpoint only, no events dir
    (john / "checkpoints" / "rewrite" / "state.json").write_text(json.dumps({"phase": "rewrite"}))
    return john


def _load(john: Path, name: str) -> dict:
    return json.loads((john / name).read_text(encoding="utf-8"))


class TestEmitManifests(unittest.TestCase):
    def test_emits_both_manifests_with_expected_fields(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            john = _build_fixture(tdp)
            rc, out, err = run_script("emit_manifests.py", cwd=tdp)
            self.assertEqual(rc, 0, f"stderr: {err}")
            self.assertTrue(out["success"])
            self.assertEqual(len(out["written"]), 2)
            self.assertTrue((john / "PROVENANCE.json").is_file())
            self.assertTrue((john / "SELF_EVAL_MANIFEST.json").is_file())

            prov = _load(john, "PROVENANCE.json")
            self.assertEqual(prov["schema_version"], 1)
            self.assertEqual(prov["john_version"], "0.4.2")
            self.assertEqual(prov["run_id"], "2026-06-12T00:00:00+00:00")
            self.assertEqual(prov["current_phase"], "extract")
            self.assertEqual(prov["phases_observed"], ["extract", "parse", "rewrite"])
            self.assertIn("event/checkpoint-backed", prov["phases_note"])
            # run window = min/max event timestamp
            self.assertEqual(prov["run_started_at"], "2026-06-12T00:00:05Z")
            self.assertEqual(prov["run_completed_at"], "2026-06-12T00:09:00Z")
            self.assertEqual(prov["corpus"]["inputs"], ["corpus.pdf", "notes.md"])
            self.assertIsNone(prov["corpus"]["description"])

            se = _load(john, "SELF_EVAL_MANIFEST.json")
            self.assertEqual(se["process_scorecard_script"], "scripts/process_scorecard.py")
            self.assertIn("process_scorecard.py", se["process_scorecard_command"])
            self.assertEqual(se["schema_version"], 2)
            self.assertIsInstance(se["process_scorecard_argv"], list)
            self.assertEqual(se["process_scorecard_argv"][0], "python3")
            self.assertTrue(se["process_scorecard_command_deprecated"])
            self.assertEqual(se["run_report_location"], ".john/reports/")
            self.assertEqual(se["workspace_metadata"], ".john/workspace.json")

    def test_standalone_vanilla_run_template_fields_null(self):
        # No --applied-metadata: the membership test — a fresh-clone vanilla run
        # still emits both manifests, with template name/version null.
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            john = _build_fixture(tdp)
            rc, out, err = run_script("emit_manifests.py", cwd=tdp)
            self.assertEqual(rc, 0, f"stderr: {err}")
            prov = _load(john, "PROVENANCE.json")
            self.assertIsNone(prov["template_name"])
            self.assertIsNone(prov["template_version"])

    def test_applied_metadata_populates_template_without_leaking_paths(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            john = _build_fixture(tdp)
            meta = tdp / "applied-metadata.json"
            meta.write_text(json.dumps({
                "template_name": "kc-in-john",
                "template_version": "0.2.0",
                "applied_at": "2026-06-12T00:00:00+00:00",
                "template_root_at_apply": "/Users/someone/secret-path/tpl",
                "john_install_at_apply": "/Users/someone/other-path",
            }))
            rc, out, _ = run_script(
                "emit_manifests.py", "--root", str(tdp),
                "--applied-metadata", str(meta), "--quiet", cwd=Path(td),
            )
            self.assertEqual(rc, 0)
            prov = _load(john, "PROVENANCE.json")
            self.assertEqual(prov["template_name"], "kc-in-john")
            self.assertEqual(prov["template_version"], "0.2.0")
            # Local filesystem paths from applied-metadata must NOT flow into the manifest
            self.assertNotIn("secret-path", (john / "PROVENANCE.json").read_text())

    def test_idempotent_modulo_generated_at(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            john = _build_fixture(tdp)
            rc1, _, _ = run_script("emit_manifests.py", "--quiet", cwd=tdp)
            a = _load(john, "PROVENANCE.json")
            a.pop("generated_at", None)
            rc2, _, _ = run_script("emit_manifests.py", "--quiet", cwd=tdp)
            b = _load(john, "PROVENANCE.json")
            b.pop("generated_at", None)
            self.assertEqual(rc1, 0)
            self.assertEqual(rc2, 0)
            self.assertEqual(a, b)

    def test_no_events_leaves_run_window_null(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            john = tdp / ".john"
            john.mkdir()
            (john / "workspace.json").write_text(json.dumps({
                "created_by_john_version": "0.4.2", "current_phase": "bootstrap",
                "initialized_at": "2026-06-12T00:00:00+00:00",
            }))
            rc, out, err = run_script("emit_manifests.py", cwd=tdp)
            self.assertEqual(rc, 0, f"stderr: {err}")
            prov = _load(john, "PROVENANCE.json")
            self.assertIsNone(prov["run_started_at"])
            self.assertIsNone(prov["run_completed_at"])
            self.assertEqual(prov["phases_observed"], [])
            self.assertEqual(prov["corpus"]["inputs"], [])

    def test_event_time_bounds_compare_offsets_as_datetimes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            john = _build_fixture(root)
            events = john / "events/extract"
            for existing in (john / "events").rglob("*.json"):
                existing.unlink()
            (events / "a.json").write_text(json.dumps({
                "timestamp": "2026-01-01T01:30:00+01:00"
            }))
            (events / "b.json").write_text(json.dumps({
                "timestamp": "2026-01-01T00:45:00Z"
            }))
            run_script("emit_manifests.py", "--quiet", cwd=root)
            prov = _load(john, "PROVENANCE.json")
            self.assertEqual(prov["run_started_at"], "2026-01-01T01:30:00+01:00")
            self.assertEqual(prov["run_completed_at"], "2026-01-01T00:45:00Z")

    def test_errors_when_no_workspace(self):
        with tempfile.TemporaryDirectory() as td:
            rc, out, _ = run_script("emit_manifests.py", cwd=Path(td))
            self.assertEqual(rc, 1)
            self.assertFalse(out["success"])

    def test_phases_observed_matches_scorecard(self):
        # Guard against drift: the two scripts must agree on the
        # event/checkpoint-backed phase universe.
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            _build_fixture(tdp)
            run_script("emit_manifests.py", "--quiet", cwd=tdp)
            prov = _load(tdp / ".john", "PROVENANCE.json")
            rc, sc, _ = run_script("process_scorecard.py", "--quiet", cwd=tdp)
            self.assertEqual(rc, 0)
            self.assertEqual(
                prov["phases_observed"],
                sc["phase_provenance"]["event_checkpoint_backed"],
            )

    def test_works_from_project_subdirectory(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            _build_fixture(tdp)
            sub = tdp / "app" / "backend"
            sub.mkdir(parents=True)
            rc, out, err = run_script("emit_manifests.py", "--quiet", cwd=sub)
            self.assertEqual(rc, 0, f"stderr: {err}")
            self.assertTrue((tdp / ".john" / "PROVENANCE.json").is_file())


if __name__ == "__main__":
    unittest.main()
