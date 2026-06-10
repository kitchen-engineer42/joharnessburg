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
import tempfile
import unittest
from pathlib import Path

from tests._helpers import SCRIPTS_DIR

PLUGIN_ROOT = SCRIPTS_DIR.parent


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


if __name__ == "__main__":
    unittest.main()
