"""Cross-artifact consistency tests (v0.2.2).

Cheap structural guards for breakages no behavioral test sees:
- every script compiles (catches syntax errors in scripts with no test
  coverage of their own, e.g. dependency-gated ones like markitdown_parse.py);
- hooks.json parses and only references scripts that exist (a hook-script
  rename would otherwise ship green and break all hooks at runtime);
- apply_template.py's CORE_SKILLS guard names real skill dirs (a skill rename
  would otherwise silently neuter the v0.2.0 core-delete guard).
"""

import json
import py_compile
import re
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

from tests._helpers import SCRIPTS_DIR

PLUGIN_ROOT = SCRIPTS_DIR.parent
REPO_ROOT = PLUGIN_ROOT.parents[1]


class TestScriptsCompile(unittest.TestCase):
    def test_every_script_compiles(self):
        scripts = sorted(SCRIPTS_DIR.glob("*.py"))
        self.assertTrue(scripts, "no scripts found — wrong SCRIPTS_DIR?")
        with tempfile.TemporaryDirectory() as td:
            for script in scripts:
                with self.subTest(script=script.name):
                    py_compile.compile(
                        str(script),
                        doraise=True,
                        cfile=str(Path(td) / f"{script.name}c"),
                    )


class TestCodexAgentGeneration(unittest.TestCase):
    def test_generated_agents_are_in_sync_and_valid_toml(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "sync_codex_agents.py"), "--check"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for path in sorted((PLUGIN_ROOT / "codex/agents").glob("*.toml")):
            parsed = tomllib.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(parsed["name"], path.stem)
            self.assertIn("developer_instructions", parsed)

    def test_shipped_hooks_have_no_duplicate_codex_declaration(self):
        self.assertTrue((PLUGIN_ROOT / "hooks/hooks.json").is_file())
        self.assertFalse((PLUGIN_ROOT / "hooks/codex-hooks.json").exists())


class TestHooksJsonConsistency(unittest.TestCase):
    def test_hooks_reference_existing_scripts(self):
        hooks_file = PLUGIN_ROOT / "hooks" / "hooks.json"
        data = json.loads(hooks_file.read_text(encoding="utf-8"))
        commands = [
            h["command"]
            for matchers in data["hooks"].values()
            for matcher in matchers
            for h in matcher["hooks"]
            if h.get("type") == "command"
        ]
        self.assertTrue(commands, "hooks.json declares no command hooks?")
        for command in commands:
            with self.subTest(command=command):
                m = re.search(r"\$\{CLAUDE_PLUGIN_ROOT\}/(\S+)", command)
                self.assertIsNotNone(
                    m, f"hook command not rooted at CLAUDE_PLUGIN_ROOT: {command}"
                )
                target = PLUGIN_ROOT / m.group(1)
                self.assertTrue(
                    target.is_file(),
                    f"hooks.json references missing script: {m.group(1)}",
                )


class TestCommandsConsistency(unittest.TestCase):
    def test_commands_reference_existing_scripts(self):
        # A command doc naming a ${CLAUDE_PLUGIN_ROOT}/scripts/... path that
        # doesn't exist ships green and breaks at first use — same blindness
        # the hooks.json check closes.
        commands = sorted((PLUGIN_ROOT / "commands").glob("*.md"))
        self.assertTrue(commands, "no command docs found?")
        pattern = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/(scripts/[A-Za-z0-9_]+\.py)")
        referenced = set()
        for doc in commands:
            referenced.update(pattern.findall(doc.read_text(encoding="utf-8")))
        self.assertTrue(referenced, "no script references found in command docs?")
        for rel in sorted(referenced):
            with self.subTest(script=rel):
                self.assertTrue(
                    (PLUGIN_ROOT / rel).is_file(),
                    f"command docs reference missing script: {rel}",
                )


class TestCoreSkillsConsistency(unittest.TestCase):
    def test_core_skills_dict_matches_real_skill_dirs(self):
        import sys

        sys.path.insert(0, str(SCRIPTS_DIR))
        try:
            from apply_template import CORE_SKILLS
        finally:
            sys.path.pop(0)
        skills_dir = PLUGIN_ROOT / "skills"
        existing = {d.name for d in skills_dir.iterdir() if d.is_dir()}
        for name in CORE_SKILLS:
            with self.subTest(skill=name):
                self.assertIn(
                    name,
                    existing,
                    f"CORE_SKILLS names '{name}' but skills/{name}/ does not "
                    f"exist — the core-delete guard is silently dead for it",
                )


class TestReleaseSurfaceConsistency(unittest.TestCase):
    CONTROL_SKILLS = {
        "using-john",
        "init-workspace",
        "workspace-status",
        "endurance-goal",
        "archive-workspace",
    }

    def test_nested_manifest_versions_match(self):
        claude = json.loads(
            (PLUGIN_ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8")
        )
        codex = json.loads(
            (PLUGIN_ROOT / ".codex-plugin/plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(claude["version"], codex["version"])
        self.assertEqual(claude["version"], "0.5.1")

    def test_control_skills_have_openai_metadata(self):
        for name in sorted(self.CONTROL_SKILLS):
            with self.subTest(skill=name):
                path = PLUGIN_ROOT / "skills" / name / "agents/openai.yaml"
                self.assertTrue(path.is_file(), f"missing {path}")
                text = path.read_text(encoding="utf-8")
                self.assertRegex(text, r'(?m)^  display_name: ".+"$')
                self.assertRegex(text, r'(?m)^  short_description: ".{25,64}"$')
                self.assertIn(f"${name}", text)

    def test_run_report_has_provider_neutral_label(self):
        text = (
            PLUGIN_ROOT / "skills/codex-run-report/agents/openai.yaml"
        ).read_text(encoding="utf-8")
        self.assertIn('display_name: "John: Run Report"', text)
        self.assertNotIn("John Codex Run Report", text)

    def test_stale_codex_development_adapters_are_absent(self):
        self.assertFalse((REPO_ROOT / ".codex/migrate-to-codex-report.txt").exists())
        for name in ("init", "status", "endurance", "archive"):
            self.assertFalse(
                (REPO_ROOT / f".agents/skills/source-command-{name}").exists()
            )

    def test_readmes_document_symmetric_plugin_operations(self):
        readmes = [
            (REPO_ROOT / "README.md").read_text(encoding="utf-8"),
            (REPO_ROOT / "README_ZH.md").read_text(encoding="utf-8"),
        ]
        commands = (
            "claude plugin marketplace add kitchen-engineer42/joharnessburg",
            "claude plugin install john@joharnessburg",
            "claude plugin marketplace update joharnessburg",
            "claude plugin update john@joharnessburg",
            "claude plugin list",
            "codex plugin marketplace add kitchen-engineer42/joharnessburg",
            "codex plugin add john@joharnessburg",
            "codex plugin marketplace upgrade joharnessburg",
            "codex plugin list",
        )
        for text in readmes:
            for command in commands:
                with self.subTest(command=command):
                    self.assertIn(command, text)
            self.assertIn("/hooks", text)
            self.assertNotIn("docs/adr", text)


if __name__ == "__main__":
    unittest.main()
