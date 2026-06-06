"""Tests for scripts/apply_template.py.

Uses --john-install + --output to redirect away from the user's real plugin install.
Tests build a minimal fake John + a fake template in temp dirs, apply, and verify.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests._helpers import SCRIPTS_DIR


def _build_fake_john(root: Path):
    """Create a minimal joharnessburg install layout."""
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "joharnessburg", "version": "0.1.7"})
    )
    (root / "skills").mkdir()
    (root / "skills" / "chunking").mkdir()
    (root / "skills" / "chunking" / "SKILL.md").write_text(
        "---\nname: chunking\n---\n# core chunking — original\n"
    )
    (root / "skills" / "knowledge-extraction").mkdir()
    (root / "skills" / "knowledge-extraction" / "SKILL.md").write_text(
        "---\nname: knowledge-extraction\n---\n# core extraction\n"
    )
    (root / "skills" / "to-be-deleted").mkdir()
    (root / "skills" / "to-be-deleted" / "SKILL.md").write_text("# I will be deleted\n")
    (root / "scripts").mkdir()
    (root / "scripts" / "init_workspace.py").write_text("# fake\n")


def _build_fake_template(root: Path, name: str = "fake-template"):
    """Create a template that overrides chunking, adds slide-rendering, deletes to-be-deleted."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "template.json").write_text(
        json.dumps({"name": name, "version": "0.1.0", "description": "fake"})
    )
    # Override
    (root / "skills" / "_override" / "chunking").mkdir(parents=True)
    (root / "skills" / "_override" / "chunking" / "SKILL.md").write_text(
        "---\nname: chunking\n---\n# template-overridden chunking (slide-aware)\n"
    )
    # Additive
    (root / "skills" / "slide-rendering").mkdir(parents=True)
    (root / "skills" / "slide-rendering" / "SKILL.md").write_text(
        "---\nname: slide-rendering\n---\n# new skill from template\n"
    )
    # Delete
    (root / "skills" / "_delete").write_text("to-be-deleted\n")
    # Template metadata files
    (root / "claude_addon.md").write_text("# template-specific claude_addon\n")
    (root / "plan_md_template.md").write_text("# template's PLAN.md skeleton\n")


def run_apply(*args, output_parent_override: Path = None):
    """Run apply_template.py with overrides for testability."""
    env = os.environ.copy()
    if output_parent_override:
        env["JOHN_APPLIED_PARENT"] = str(output_parent_override)
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "apply_template.py")] + list(args),
        env=env,
        capture_output=True,
        text=True,
    )
    try:
        stdout_json = json.loads(proc.stdout) if proc.stdout.strip() else None
    except json.JSONDecodeError:
        stdout_json = None
    return proc.returncode, stdout_json, proc.stderr


class TestApplyTemplate(unittest.TestCase):
    def test_apply_builds_merged_dir_with_overrides_additive_delete(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            john = tdp / "john"
            template = tdp / "template"
            applied_parent = tdp / "applied"

            _build_fake_john(john)
            _build_fake_template(template, name="fake-template")

            rc, out, err = run_apply(
                "--template-root", str(template),
                "--john-install", str(john),
                output_parent_override=applied_parent,
            )
            self.assertEqual(rc, 0, f"stderr: {err}")
            self.assertTrue(out["success"])
            self.assertEqual(out["template_name"], "fake-template")

            merged = applied_parent / "fake-template"
            self.assertTrue(merged.is_dir())

            # Override applied: chunking SKILL.md content is the template's
            chunking_body = (merged / "skills" / "chunking" / "SKILL.md").read_text()
            self.assertIn("template-overridden", chunking_body)

            # Additive: slide-rendering present
            self.assertTrue((merged / "skills" / "slide-rendering" / "SKILL.md").exists())

            # Delete: to-be-deleted is gone
            self.assertFalse((merged / "skills" / "to-be-deleted").exists())

            # Original (untouched) skill still present
            self.assertTrue((merged / "skills" / "knowledge-extraction" / "SKILL.md").exists())

            # Template metadata in templates-active/
            self.assertTrue((merged / "templates-active" / "claude_addon.md").exists())
            self.assertTrue((merged / "templates-active" / "plan_md_template.md").exists())

            # Applied-metadata.json written
            meta = json.loads((merged / ".applied-metadata.json").read_text())
            self.assertEqual(meta["template_name"], "fake-template")
            self.assertIn("chunking", meta["overrides_applied"])
            self.assertIn("slide-rendering", meta["skills_added"])
            self.assertIn("to-be-deleted", meta["skills_deleted"])

    def test_apply_allows_multiple_templates_coexisting(self):
        # v0.1.8 design: each applied template dir is independent. Per-session
        # isolation means parallel Claude Code sessions with different templates
        # can run side-by-side; applying template B should NOT clobber A.
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            john = tdp / "john"
            t1 = tdp / "template1"
            t2 = tdp / "template2"
            applied_parent = tdp / "applied"

            _build_fake_john(john)
            _build_fake_template(t1, name="template1")
            _build_fake_template(t2, name="template2")

            rc1, _, _ = run_apply(
                "--template-root", str(t1),
                "--john-install", str(john),
                output_parent_override=applied_parent,
            )
            self.assertEqual(rc1, 0)

            # Apply template2 without --reset-all: should succeed; template1 stays
            rc2, out2, _ = run_apply(
                "--template-root", str(t2),
                "--john-install", str(john),
                output_parent_override=applied_parent,
            )
            self.assertEqual(rc2, 0, f"out: {out2}")
            self.assertTrue(out2["success"])
            self.assertTrue((applied_parent / "template1").is_dir())
            self.assertTrue((applied_parent / "template2").is_dir())

    def test_apply_reset_all_wipes_other_templates(self):
        # --reset-all is still useful for explicit "clean slate" scenarios.
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            john = tdp / "john"
            t1 = tdp / "template1"
            t2 = tdp / "template2"
            applied_parent = tdp / "applied"

            _build_fake_john(john)
            _build_fake_template(t1, name="template1")
            _build_fake_template(t2, name="template2")

            rc1, _, _ = run_apply(
                "--template-root", str(t1),
                "--john-install", str(john),
                output_parent_override=applied_parent,
            )
            self.assertEqual(rc1, 0)

            rc2, out2, _ = run_apply(
                "--template-root", str(t2),
                "--john-install", str(john),
                "--reset-all",
                output_parent_override=applied_parent,
            )
            self.assertEqual(rc2, 0, f"out: {out2}")
            self.assertTrue(out2["success"])
            self.assertFalse((applied_parent / "template1").exists())
            self.assertTrue((applied_parent / "template2").exists())

    def test_apply_refuses_to_overwrite_same_template_without_force(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            john = tdp / "john"
            template = tdp / "template"
            applied_parent = tdp / "applied"
            _build_fake_john(john)
            _build_fake_template(template, name="same-tpl")

            rc1, _, _ = run_apply(
                "--template-root", str(template),
                "--john-install", str(john),
                output_parent_override=applied_parent,
            )
            self.assertEqual(rc1, 0)

            # Re-apply without --force: refused
            rc2, out2, _ = run_apply(
                "--template-root", str(template),
                "--john-install", str(john),
                output_parent_override=applied_parent,
            )
            self.assertEqual(rc2, 1)
            self.assertIn("already applied", out2["error"])

            # With --force: succeeds
            rc3, _, _ = run_apply(
                "--template-root", str(template),
                "--john-install", str(john),
                "--force",
                output_parent_override=applied_parent,
            )
            self.assertEqual(rc3, 0)

    def test_apply_errors_when_template_root_missing(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            john = tdp / "john"
            _build_fake_john(john)
            rc, out, _ = run_apply(
                "--template-root", str(tdp / "nonexistent"),
                "--john-install", str(john),
                output_parent_override=tdp / "applied",
            )
            self.assertEqual(rc, 1)
            self.assertIn("does not exist", out["error"])

    def test_apply_errors_when_john_install_missing(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            template = tdp / "template"
            _build_fake_template(template)
            rc, out, _ = run_apply(
                "--template-root", str(template),
                "--john-install", str(tdp / "nonexistent"),
                output_parent_override=tdp / "applied",
            )
            self.assertEqual(rc, 1)
            self.assertIn("joharnessburg", out["error"].lower())

    def test_apply_additive_dirs_skip_collisions_with_core(self):
        # v0.1.9 — Codex #3: scripts/, commands/, agents/ are documented as
        # additive-only. A template trying to ship scripts/init_workspace.py
        # (a core file) should be skipped + warned + tracked in metadata,
        # not silently overwritten.
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            john = tdp / "john"
            template = tdp / "template"
            applied_parent = tdp / "applied"

            _build_fake_john(john)
            _build_fake_template(template, name="collision-tpl")

            # Add a colliding scripts/init_workspace.py to the template
            (template / "scripts").mkdir(parents=True)
            (template / "scripts" / "init_workspace.py").write_text(
                "# template's attempt to override core init_workspace\n"
            )
            # Add a NON-colliding scripts/<new>.py too — should still copy
            (template / "scripts" / "new_helper.py").write_text(
                "# new helper from the template\n"
            )
            # Add a colliding commands/init.md (if exists in core)
            # Our fake_john doesn't have commands/ yet — add one + a collision
            (john / "commands").mkdir(parents=True, exist_ok=True)
            (john / "commands" / "joharnessburg-init.md").write_text(
                "# core init command\n"
            )
            (template / "commands").mkdir(parents=True)
            (template / "commands" / "joharnessburg-init.md").write_text(
                "# template's attempt to overwrite core command\n"
            )
            (template / "commands" / "new-cmd.md").write_text(
                "# new command from template\n"
            )

            rc, out, err = run_apply(
                "--template-root", str(template),
                "--john-install", str(john),
                output_parent_override=applied_parent,
            )
            self.assertEqual(rc, 0, f"stderr: {err}")
            self.assertTrue(out["success"])

            merged = applied_parent / "collision-tpl"
            # The core init_workspace.py and core command should be UNCHANGED
            self.assertEqual(
                (merged / "scripts" / "init_workspace.py").read_text(),
                "# fake\n",
                "core scripts/init_workspace.py should NOT be overwritten",
            )
            self.assertEqual(
                (merged / "commands" / "joharnessburg-init.md").read_text(),
                "# core init command\n",
                "core commands/init.md should NOT be overwritten",
            )
            # The non-colliding additions should be present
            self.assertTrue((merged / "scripts" / "new_helper.py").is_file())
            self.assertTrue((merged / "commands" / "new-cmd.md").is_file())

            # Metadata records the collisions
            meta = json.loads((merged / ".applied-metadata.json").read_text())
            self.assertIn("additive_collisions", meta)
            self.assertIn("init_workspace.py", meta["additive_collisions"]["scripts"])
            self.assertIn(
                "joharnessburg-init.md",
                meta["additive_collisions"]["commands"],
            )

            # Stderr should warn about each collision
            self.assertIn("init_workspace.py", err)
            self.assertIn("skipping", err.lower())

            # Output JSON also surfaces additive_collisions
            self.assertEqual(
                set(out["additive_collisions"].keys()),
                {"scripts", "commands"},
            )

    def test_apply_force_refuses_to_delete_unrelated_dir(self):
        # Safety guard: --force must not rmtree a dir that is neither under the
        # applied parent nor an existing applied template (no marker).
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            john = tdp / "john"
            template = tdp / "template"
            applied_parent = tdp / "applied"
            _build_fake_john(john)
            _build_fake_template(template, name="guard-tpl")

            victim = tdp / "myproject"
            victim.mkdir()
            (victim / "important.txt").write_text("do not delete")

            rc, out, err = run_apply(
                "--template-root", str(template),
                "--john-install", str(john),
                "--output", str(victim),
                "--force",
                output_parent_override=applied_parent,
            )
            self.assertEqual(rc, 1)
            self.assertIn("Refusing to delete", out["error"])
            self.assertTrue((victim / "important.txt").exists())

    def test_apply_copies_template_workflows_into_templates_active(self):
        # v0.1.21 — a template's workflows/ ship into the merged plugin's
        # templates-active/workflows/ (NOT the plugin root — saved workflows
        # aren't a plugin-registered surface; /john:init installs them into the
        # project's .claude/workflows/).
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            john = tdp / "john"
            template = tdp / "template"
            applied_parent = tdp / "applied"

            _build_fake_john(john)
            _build_fake_template(template, name="wf-tpl")
            (template / "workflows").mkdir(parents=True)
            (template / "workflows" / "rule-sweep.js").write_text(
                "// saved dynamic workflow: rule-sweep\n"
            )

            rc, out, err = run_apply(
                "--template-root", str(template),
                "--john-install", str(john),
                output_parent_override=applied_parent,
            )
            self.assertEqual(rc, 0, f"stderr: {err}")
            self.assertTrue(out["success"])

            merged = applied_parent / "wf-tpl"
            shipped = merged / "templates-active" / "workflows" / "rule-sweep.js"
            self.assertTrue(shipped.is_file(), "workflow should land in templates-active/workflows/")
            self.assertIn("rule-sweep", shipped.read_text())

            self.assertIn("rule-sweep.js", out["workflows_copied"])
            meta = json.loads((merged / ".applied-metadata.json").read_text())
            self.assertIn("rule-sweep.js", meta["workflows_copied"])

    def test_apply_uses_template_name_from_template_json(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            john = tdp / "john"
            template = tdp / "weird-dir-name"
            applied_parent = tdp / "applied"
            _build_fake_john(john)
            _build_fake_template(template, name="canonical-name-from-json")

            rc, out, _ = run_apply(
                "--template-root", str(template),
                "--john-install", str(john),
                output_parent_override=applied_parent,
            )
            self.assertEqual(rc, 0)
            self.assertEqual(out["template_name"], "canonical-name-from-json")
            self.assertTrue((applied_parent / "canonical-name-from-json").is_dir())


class TestVersionPinAndCoreDeleteGuard(unittest.TestCase):
    """v0.2.0 — warn-only requires_john check + loud core-skill delete guard."""

    def _apply(self, td, template_mutator=None, john_mutator=None):
        tdp = Path(td)
        john = tdp / "fake-john"
        template = tdp / "fake-template"
        applied = tdp / "applied"
        _build_fake_john(john)
        _build_fake_template(template)
        if john_mutator:
            john_mutator(john)
        if template_mutator:
            template_mutator(template)
        rc, out, err = run_apply(
            "--template-root", str(template),
            "--john-install", str(john),
            output_parent_override=applied,
        )
        return rc, out, err, applied

    # ---- version pin ----

    def test_version_pin_warns_when_unsatisfied(self):
        with tempfile.TemporaryDirectory() as td:
            def mut(t):
                tj = json.loads((t / "template.json").read_text())
                tj["requires_john"] = ">=0.2.0"
                (t / "template.json").write_text(json.dumps(tj))
            rc, out, err, applied = self._apply(td, template_mutator=mut)
            self.assertEqual(rc, 0)  # warn-only: apply still succeeds
            self.assertIn("VERSION PIN WARNING", err)
            self.assertIn(">=0.2.0", err)
            self.assertIn("0.1.7", err)
            self.assertFalse(out["version_check"]["satisfied"])
            self.assertTrue((applied / "fake-template").is_dir())

    def test_version_pin_silent_when_satisfied(self):
        with tempfile.TemporaryDirectory() as td:
            def mut(t):
                tj = json.loads((t / "template.json").read_text())
                tj["requires_john"] = ">=0.1.0"
                (t / "template.json").write_text(json.dumps(tj))
            rc, out, err, _ = self._apply(td, template_mutator=mut)
            self.assertEqual(rc, 0)
            self.assertNotIn("VERSION PIN WARNING", err)
            self.assertTrue(out["version_check"]["satisfied"])

    def test_version_pin_skipped_when_field_absent(self):
        # Backward-compat regression guard: templates predating requires_john
        # apply with no version warning at all.
        with tempfile.TemporaryDirectory() as td:
            rc, out, err, _ = self._apply(td)
            self.assertEqual(rc, 0)
            self.assertNotIn("requires_john", err)
            self.assertIsNone(out["version_check"])

    def test_version_pin_unparseable_spec_warns_and_proceeds(self):
        with tempfile.TemporaryDirectory() as td:
            def mut(t):
                tj = json.loads((t / "template.json").read_text())
                tj["requires_john"] = "~>1.0"
                (t / "template.json").write_text(json.dumps(tj))
            rc, out, err, _ = self._apply(td, template_mutator=mut)
            self.assertEqual(rc, 0)
            self.assertIn("cannot parse requires_john", err)
            self.assertFalse(out["version_check"]["checked"])

    def test_version_pin_handles_missing_installed_version(self):
        with tempfile.TemporaryDirectory() as td:
            def jmut(j):
                (j / ".claude-plugin" / "plugin.json").write_text(
                    json.dumps({"name": "joharnessburg"})  # no version field
                )
            def tmut(t):
                tj = json.loads((t / "template.json").read_text())
                tj["requires_john"] = ">=0.2.0"
                (t / "template.json").write_text(json.dumps(tj))
            rc, out, err, _ = self._apply(td, template_mutator=tmut, john_mutator=jmut)
            self.assertEqual(rc, 0)
            self.assertIn("could not determine the installed John version", err)
            self.assertFalse(out["version_check"]["checked"])

    # ---- core-skill delete guard ----

    def test_core_skill_delete_with_reason_is_loud_but_proceeds(self):
        with tempfile.TemporaryDirectory() as td:
            def jmut(j):
                (j / "skills" / "ralph-loop").mkdir()
                (j / "skills" / "ralph-loop" / "SKILL.md").write_text(
                    "---\nname: ralph-loop\n---\n# the loop\n"
                )
            def tmut(t):
                (t / "skills" / "_delete").write_text(
                    "to-be-deleted\nralph-loop # replaced by template-specific loop\n"
                )
            rc, out, err, applied = self._apply(td, template_mutator=tmut, john_mutator=jmut)
            self.assertEqual(rc, 0)  # warn-don't-block
            self.assertIn("CORE SKILL DELETED", err)
            self.assertIn("ralph-loop", err)
            self.assertIn("replaced by template-specific loop", err)
            self.assertFalse((applied / "fake-template" / "skills" / "ralph-loop").exists())
            core = out["core_skill_deletions"]
            self.assertEqual(len(core), 1)
            self.assertEqual(core[0]["skill"], "ralph-loop")
            self.assertEqual(core[0]["reason"], "replaced by template-specific loop")
            # metadata carries it too
            meta = json.loads(
                (applied / "fake-template" / ".applied-metadata.json").read_text()
            )
            self.assertEqual(len(meta["core_skill_deletions"]), 1)

    def test_core_skill_delete_without_reason_is_extra_loud(self):
        with tempfile.TemporaryDirectory() as td:
            def jmut(j):
                (j / "skills" / "ralph-loop").mkdir()
                (j / "skills" / "ralph-loop" / "SKILL.md").write_text("# loop\n")
            def tmut(t):
                (t / "skills" / "_delete").write_text("ralph-loop\n")
            rc, out, err, applied = self._apply(td, template_mutator=tmut, john_mutator=jmut)
            self.assertEqual(rc, 0)
            self.assertIn("NO REASON STATED", err)
            self.assertIn("ralph-loop #", err)  # tells the author the syntax
            self.assertFalse((applied / "fake-template" / "skills" / "ralph-loop").exists())
            self.assertIsNone(out["core_skill_deletions"][0]["reason"])

    def test_core_delete_warning_names_referrers(self):
        with tempfile.TemporaryDirectory() as td:
            def jmut(j):
                (j / "skills" / "ralph-loop").mkdir()
                (j / "skills" / "ralph-loop" / "SKILL.md").write_text("# loop\n")
                # chunking references ralph-loop and survives the deletion
                (j / "skills" / "chunking" / "SKILL.md").write_text(
                    "---\nname: chunking\n---\nSee [[ralph-loop]] for iteration.\n"
                )
            def tmut(t):
                (t / "skills" / "_delete").write_text("ralph-loop # trimmed\n")
            rc, out, err, _ = self._apply(td, template_mutator=tmut, john_mutator=jmut)
            self.assertEqual(rc, 0)
            self.assertIn("Still referenced by remaining skills", err)
            self.assertIn("chunking", err)
            self.assertIn("chunking", out["core_skill_deletions"][0]["referenced_by"])

    def test_non_core_delete_unchanged_and_comment_parsing(self):
        # `name # comment` now parses for non-core skills too (this also fixes
        # the latent bug where a same-line comment broke the name lookup),
        # with no core warning.
        with tempfile.TemporaryDirectory() as td:
            def tmut(t):
                (t / "skills" / "_delete").write_text(
                    "# full-line comment is still skipped\n"
                    "to-be-deleted # cleanup\n"
                )
            rc, out, err, applied = self._apply(td, template_mutator=tmut)
            self.assertEqual(rc, 0)
            self.assertIn("to-be-deleted", out["skills_deleted"])
            self.assertEqual(out["core_skill_deletions"], [])
            self.assertNotIn("CORE SKILL DELETED", err)
            self.assertFalse(
                (applied / "fake-template" / "skills" / "to-be-deleted").exists()
            )


if __name__ == "__main__":
    unittest.main()
