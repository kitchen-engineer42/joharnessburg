"""Tests for scripts/init_workspace.py."""

import json
import tempfile
import unittest
from pathlib import Path

from tests._helpers import run_script


class TestInitWorkspace(unittest.TestCase):
    def test_init_creates_john_dir_and_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, out, err = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0, f"stderr: {err}")
            self.assertTrue(out["success"])
            # Pin the source: a polluted JOHN_TEMPLATES_ACTIVE in the parent
            # env must not silently switch the scaffold to a template plan.
            self.assertEqual(out["plan_md_source"], "default")
            self.assertTrue((tdp / ".john").is_dir())
            self.assertTrue((tdp / ".john" / "workspace.json").is_file())
            self.assertTrue((tdp / "PLAN.md").is_file())
            self.assertTrue((tdp / "CLAUDE.md").is_file())
            # Subdirs
            for sd in ["input", "parsed", "chunks", "knowledge", "events", "checkpoints", "trace"]:
                self.assertTrue((tdp / ".john" / sd).is_dir(), f"missing subdir {sd}")
            # Workspace state shape (v0.1.15+: no active_template field)
            state = json.loads((tdp / ".john" / "workspace.json").read_text())
            self.assertEqual(state["schema_version"], 1)
            self.assertNotIn("active_template", state)
            self.assertEqual(state["current_phase"], "bootstrap")

    def test_init_errors_when_john_exists_without_force(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            # First init succeeds
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            # Second init without --force errors
            rc, out, err = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 1)
            self.assertFalse(out["success"])
            self.assertIn(".john/", out["error"])
            self.assertIn("--force", err)

    def test_init_force_recreates_john_dir(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            # Drop a marker file inside .john so we can confirm it's gone after --force
            marker = tdp / ".john" / "marker.txt"
            marker.write_text("before-force")
            rc, out, err = run_script("init_workspace.py", "--force", cwd=tdp)
            self.assertEqual(rc, 0, f"stderr: {err}")
            self.assertTrue(out["success"])
            self.assertFalse(marker.exists(), "marker should be gone after --force recreate")

    def test_init_copies_input_directory(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            # Build a source dir with some files
            src = tdp / "src-materials"
            src.mkdir()
            (src / "alpha.txt").write_text("alpha contents")
            (src / "beta.md").write_text("# beta")
            # Hidden file should be skipped
            (src / ".hidden").write_text("hidden")

            project = tdp / "project"
            project.mkdir()
            rc, out, err = run_script(
                "init_workspace.py", str(src), cwd=project
            )
            self.assertEqual(rc, 0, f"stderr: {err}")
            self.assertTrue(out["success"])
            self.assertTrue((project / ".john" / "input" / "alpha.txt").is_file())
            self.assertTrue((project / ".john" / "input" / "beta.md").is_file())
            self.assertFalse(
                (project / ".john" / "input" / ".hidden").exists(),
                "hidden files should be skipped",
            )
            self.assertEqual(len(out["copied_input"]), 2)

    def test_init_copies_input_single_file(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            src = tdp / "one.pdf"
            src.write_bytes(b"%PDF-1.4 fake")
            project = tdp / "project"
            project.mkdir()
            rc, out, err = run_script(
                "init_workspace.py", str(src), cwd=project
            )
            self.assertEqual(rc, 0, f"stderr: {err}")
            self.assertTrue((project / ".john" / "input" / "one.pdf").is_file())

    def test_init_errors_on_missing_input_path(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, out, err = run_script(
                "init_workspace.py", str(tdp / "nope"), cwd=tdp
            )
            self.assertEqual(rc, 1)
            self.assertFalse(out["success"])

    def test_init_does_not_overwrite_existing_claude_md(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            existing = tdp / "CLAUDE.md"
            existing.write_text("user's existing content")
            rc, out, err = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            self.assertEqual(existing.read_text(), "user's existing content")
            self.assertFalse(out["claude_md_written"])

    def test_init_does_not_overwrite_existing_plan_md_without_force(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / "PLAN.md").write_text("user's existing plan")
            rc, out, err = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            self.assertEqual((tdp / "PLAN.md").read_text(), "user's existing plan")
            self.assertFalse(out["plan_md_written"])

    # v0.1.9 — Codex #6: hidden files skipped recursively
    def test_init_skips_hidden_files_in_nested_dirs(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            src = tdp / "src"
            src.mkdir()
            (src / "visible.md").write_text("top-level visible")
            # Nested dir with hidden content
            nested = src / "subdir"
            nested.mkdir()
            (nested / "ok.md").write_text("nested visible")
            (nested / ".DS_Store").write_bytes(b"mac junk")
            git_dir = nested / ".git"
            git_dir.mkdir()
            (git_dir / "config").write_text("gitconfig data")

            project = tdp / "project"
            project.mkdir()
            rc, out, err = run_script(
                "init_workspace.py", str(src), cwd=project
            )
            self.assertEqual(rc, 0, f"stderr: {err}")
            input_dir = project / ".john" / "input"
            # Visible files copied
            self.assertTrue((input_dir / "visible.md").is_file())
            self.assertTrue((input_dir / "subdir" / "ok.md").is_file())
            # Hidden files NOT copied (including nested ones)
            self.assertFalse((input_dir / "subdir" / ".DS_Store").exists(),
                             ".DS_Store inside nested dir should be skipped")
            self.assertFalse((input_dir / "subdir" / ".git").exists(),
                             ".git inside nested dir should be skipped")

    # v0.1.9 — Codex #1: init consumes templates-active/ from merged plugin
    def test_init_uses_template_plan_md_when_templates_active_present(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            templates_active = tdp / "templates-active"
            templates_active.mkdir()
            (templates_active / "plan_md_template.md").write_text(
                "# CUSTOM TEMPLATE PLAN — {project_name}\n\n"
                "*Date: {date}*\n\nThis is the template-provided PLAN skeleton.\n"
            )

            project = tdp / "project"
            project.mkdir()
            rc, out, err = run_script(
                "init_workspace.py",
                "--project-name", "my-test-project",
                cwd=project,
                env_override={"JOHN_TEMPLATES_ACTIVE": str(templates_active)},
            )
            self.assertEqual(rc, 0, f"stderr: {err}")
            self.assertEqual(out["plan_md_source"], "template")
            self.assertTrue(out["templates_active_used"])
            plan_body = (project / "PLAN.md").read_text()
            self.assertIn("CUSTOM TEMPLATE PLAN — my-test-project", plan_body)
            self.assertNotIn("Created by `/john:init`", plan_body)

    def test_init_falls_back_to_default_plan_md_when_no_templates_active(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            # No templates-active dir — fallback should use the hardcoded skeleton
            rc, out, err = run_script(
                "init_workspace.py",
                cwd=tdp,
                env_override={"JOHN_TEMPLATES_ACTIVE": str(tdp / "does-not-exist")},
            )
            self.assertEqual(rc, 0, f"stderr: {err}")
            self.assertEqual(out["plan_md_source"], "default")
            self.assertFalse(out["templates_active_used"])
            plan_body = (tdp / "PLAN.md").read_text()
            self.assertIn("Created by `/john:init`", plan_body)

    def test_init_template_plan_md_substitutes_despite_literal_braces(self):
        # v0.2.2: targeted .replace() substitution. Literal `{...}` in code
        # snippets must survive verbatim AND {project_name}/{date} must still
        # substitute. (The old str.format() approach threw on stray braces and
        # fell back to raw content — shipping PLAN.md with unsubstituted
        # placeholders.)
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            templates_active = tdp / "templates-active"
            templates_active.mkdir()
            (templates_active / "plan_md_template.md").write_text(
                "# PLAN.md — {project_name}\n\n"
                "Files: `kc_runtime/{confidence.py, dashboard.py}`\n"
                "A lone closing brace } and a lone { opener.\n"
                "Some {unrecognized_placeholder} stays literal.\n\n"
                "- {date}: scaffolded\n"
            )

            project = tdp / "project"
            project.mkdir()
            rc, out, _ = run_script(
                "init_workspace.py",
                "--project-name", "brace-proj",
                cwd=project,
                env_override={"JOHN_TEMPLATES_ACTIVE": str(templates_active)},
            )
            self.assertEqual(rc, 0)
            self.assertEqual(out["plan_md_source"], "template")
            plan_body = (project / "PLAN.md").read_text()
            # Placeholders substituted
            self.assertIn("# PLAN.md — brace-proj", plan_body)
            self.assertNotIn("{project_name}", plan_body)
            self.assertNotIn("{date}", plan_body)
            # Literal braces preserved verbatim
            self.assertIn("kc_runtime/{confidence.py, dashboard.py}", plan_body)
            self.assertIn("A lone closing brace } and a lone { opener.", plan_body)
            self.assertIn("{unrecognized_placeholder}", plan_body)

    def test_init_force_with_bad_input_path_preserves_existing_workspace(self):
        # v0.2.2: the input path is validated in PRE-FLIGHT — a typo'd path
        # combined with --force must not destroy the existing .john/ contents
        # or regenerate PLAN.md.
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            rc, _, _ = run_script("init_workspace.py", cwd=tdp)
            self.assertEqual(rc, 0)
            knowledge = tdp / ".john" / "knowledge" / "important.md"
            knowledge.write_text("hard-won extraction results")
            (tdp / "PLAN.md").write_text("user's evolved plan")

            rc, out, _ = run_script(
                "init_workspace.py", str(tdp / "no-such-input"), "--force", cwd=tdp
            )
            self.assertEqual(rc, 1)
            self.assertFalse(out["success"])
            self.assertTrue(
                knowledge.exists(),
                ".john/ must survive a failed init (validate before destroy)",
            )
            self.assertEqual((tdp / "PLAN.md").read_text(), "user's evolved plan")

    def test_init_appends_template_claude_addon_to_claude_md(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            templates_active = tdp / "templates-active"
            templates_active.mkdir()
            (templates_active / "claude_addon.md").write_text(
                "## Project-specific conventions\n\n"
                "This is the template's claude_addon content.\n"
            )

            project = tdp / "project"
            project.mkdir()
            rc, out, err = run_script(
                "init_workspace.py",
                cwd=project,
                env_override={"JOHN_TEMPLATES_ACTIVE": str(templates_active)},
            )
            self.assertEqual(rc, 0, f"stderr: {err}")
            self.assertTrue(out["claude_md_written"])
            self.assertTrue(out["claude_addon_appended"])
            claude_body = (project / "CLAUDE.md").read_text()
            self.assertIn("## From active template", claude_body)
            self.assertIn("This is the template's claude_addon content.", claude_body)

    # v0.1.21 — init installs template-shipped workflows into .claude/workflows/
    def test_init_installs_template_workflows_into_dot_claude(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            templates_active = tdp / "templates-active"
            (templates_active / "workflows").mkdir(parents=True)
            (templates_active / "workflows" / "rule-sweep.js").write_text(
                "// saved dynamic workflow\n"
            )

            project = tdp / "project"
            project.mkdir()
            rc, out, err = run_script(
                "init_workspace.py",
                cwd=project,
                env_override={"JOHN_TEMPLATES_ACTIVE": str(templates_active)},
            )
            self.assertEqual(rc, 0, f"stderr: {err}")
            installed = project / ".claude" / "workflows" / "rule-sweep.js"
            self.assertTrue(installed.is_file(), "workflow should be installed into .claude/workflows/")
            self.assertIn("rule-sweep.js", out["workflows_installed"])
            self.assertEqual(out["workflows_skipped"], [])

    def test_init_skips_existing_workflow_in_dot_claude(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            templates_active = tdp / "templates-active"
            (templates_active / "workflows").mkdir(parents=True)
            (templates_active / "workflows" / "rule-sweep.js").write_text(
                "// template version\n"
            )

            project = tdp / "project"
            (project / ".claude" / "workflows").mkdir(parents=True)
            user_wf = project / ".claude" / "workflows" / "rule-sweep.js"
            user_wf.write_text("// user's edited version\n")

            rc, out, err = run_script(
                "init_workspace.py",
                cwd=project,
                env_override={"JOHN_TEMPLATES_ACTIVE": str(templates_active)},
            )
            self.assertEqual(rc, 0, f"stderr: {err}")
            # User's version must be preserved (skip-if-exists)
            self.assertEqual(user_wf.read_text(), "// user's edited version\n")
            self.assertIn("rule-sweep.js", out["workflows_skipped"])
            self.assertEqual(out["workflows_installed"], [])

    def test_init_does_not_append_claude_addon_when_claude_md_already_exists(self):
        # Per existing contract: never overwrite existing CLAUDE.md.
        # The addon should only be appended when CLAUDE.md is being CREATED.
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            templates_active = tdp / "templates-active"
            templates_active.mkdir()
            (templates_active / "claude_addon.md").write_text("template addon content")

            project = tdp / "project"
            project.mkdir()
            (project / "CLAUDE.md").write_text("user's pre-existing CLAUDE.md")

            rc, out, _ = run_script(
                "init_workspace.py",
                cwd=project,
                env_override={"JOHN_TEMPLATES_ACTIVE": str(templates_active)},
            )
            self.assertEqual(rc, 0)
            self.assertFalse(out["claude_md_written"])
            self.assertFalse(out["claude_addon_appended"])
            self.assertEqual(
                (project / "CLAUDE.md").read_text(),
                "user's pre-existing CLAUDE.md",
            )


if __name__ == "__main__":
    unittest.main()
