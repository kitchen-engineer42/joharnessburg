"""Tests for templates/apply.sh — the universal template-apply wrapper.

Regression context (v0.2.1): a bundled template shipped a frozen copy of
apply.sh whose registry-key matcher predated the v0.1.20 plugin rename
(`joharnessburg` -> `john@joharnessburg`), so marketplace-installed users
couldn't apply the template. Two guards here: (1) any apply.sh copy bundled
in a template must be byte-identical to the universal one (the plugin ships
no templates as of v0.2.2, so this passes vacuously until one is ever
promoted again); (2) the universal one must resolve an install registered
under the post-rename key.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent
UNIVERSAL = PLUGIN_ROOT / "templates" / "apply.sh"


class TestApplyShCopiesInSync(unittest.TestCase):
    def test_every_bundled_template_apply_sh_matches_universal(self):
        universal = UNIVERSAL.read_text(encoding="utf-8")
        # Vacuously green while the plugin ships no templates (v0.2.2+);
        # guards any template promoted into templates/ in the future.
        copies = [
            p for p in (PLUGIN_ROOT / "templates").glob("**/apply.sh")
            if p != UNIVERSAL
        ]
        for copy in copies:
            self.assertEqual(
                copy.read_text(encoding="utf-8"),
                universal,
                f"{copy} has drifted from templates/apply.sh — re-sync it "
                f"(frozen copies rot; this is how the v0.1.20 rename bug shipped)",
            )


class TestApplyShResolution(unittest.TestCase):
    def test_resolves_install_via_post_rename_registry_key(self):
        """apply.sh (no $CLAUDE_PLUGIN_ROOT) must find apply_template.py via an
        installed_plugins.json entry keyed `john@joharnessburg`."""
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            # Fake HOME with a registry pointing at the real plugin root
            fake_home = tdp / "home"
            (fake_home / ".claude" / "plugins").mkdir(parents=True)
            (fake_home / ".claude" / "plugins" / "installed_plugins.json").write_text(
                json.dumps({
                    "version": 2,
                    "plugins": {
                        "john@joharnessburg": [
                            {"scope": "user", "installPath": str(PLUGIN_ROOT)}
                        ]
                    },
                })
            )
            # Minimal fake john to merge onto + minimal template around apply.sh
            fake_john = tdp / "fake-john"
            (fake_john / ".claude-plugin").mkdir(parents=True)
            (fake_john / ".claude-plugin" / "plugin.json").write_text(
                json.dumps({"name": "john", "version": "0.2.0"})
            )
            (fake_john / "skills" / "chunking").mkdir(parents=True)
            (fake_john / "skills" / "chunking" / "SKILL.md").write_text("# core\n")

            template = tdp / "template"
            template.mkdir()
            (template / "template.json").write_text(
                json.dumps({"name": "sh-resolution-test", "version": "0.0.1"})
            )
            shutil.copy2(UNIVERSAL, template / "apply.sh")
            os.chmod(template / "apply.sh", 0o755)

            env = os.environ.copy()
            env["HOME"] = str(fake_home)
            env["JOHN_APPLIED_PARENT"] = str(tdp / "applied")
            env.pop("CLAUDE_PLUGIN_ROOT", None)

            proc = subprocess.run(
                ["bash", str(template / "apply.sh"),
                 "--john-install", str(fake_john)],
                env=env, capture_output=True, text=True,
            )
            self.assertEqual(
                proc.returncode, 0,
                f"apply.sh failed to resolve the install via the "
                f"john@joharnessburg registry key.\nstderr: {proc.stderr}",
            )
            self.assertTrue(
                (tdp / "applied" / "sh-resolution-test" / ".applied-metadata.json").is_file()
            )


if __name__ == "__main__":
    unittest.main()
