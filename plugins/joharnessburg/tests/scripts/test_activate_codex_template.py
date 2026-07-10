"""Tests for project-local, additive Codex template activation."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests._helpers import SCRIPTS_DIR


def build_merged(root: Path, name: str = "research-kit") -> Path:
    merged = root / "merged"
    (merged / ".codex-plugin").mkdir(parents=True)
    (merged / ".codex-plugin/plugin.json").write_text(
        json.dumps({"name": "john", "version": "0.5.1"})
    )
    (merged / ".applied-metadata.json").write_text(
        json.dumps({"template_name": name, "template_version": "1.2.3"})
    )
    (merged / "codex/agents").mkdir(parents=True)
    (merged / "codex/agents/researcher.toml").write_text('name = "researcher"\n')
    return merged


def activate(project: Path, merged: Path, *extra: str):
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "activate_codex_template.py"),
            "--project-root", str(project),
            "--merged-plugin", str(merged),
            *extra,
        ],
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout) if result.stdout.strip() else None
    return result, payload


class TestActivateCodexTemplate(unittest.TestCase):
    def test_materializes_local_plugin_marketplace_and_agents(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = root / "project"
            project.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=project, check=True)
            merged = build_merged(root)
            result, payload = activate(project, merged)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(payload["success"])
            self.assertTrue(payload["vanilla_exclusion_required"])
            self.assertFalse(payload["global_state_changed"])
            destination = project / ".john-codex/plugins/research-kit"
            self.assertTrue((destination / ".codex-activation.json").is_file())
            self.assertTrue((project / ".codex/agents/researcher.toml").is_file())
            marketplace = json.loads(
                (project / ".agents/plugins/marketplace.json").read_text()
            )
            self.assertEqual(
                marketplace["plugins"][0]["source"]["path"],
                "./.john-codex/plugins/research-kit",
            )
            exclude_path = subprocess.run(
                ["git", "rev-parse", "--git-path", "info/exclude"],
                cwd=project, capture_output=True, text=True, check=True,
            ).stdout.strip()
            exclude = Path(exclude_path)
            if not exclude.is_absolute():
                exclude = project / exclude
            self.assertIn(".john-codex/", exclude.read_text())
            self.assertTrue(any("Restart Codex" in line for line in payload["instructions"]))
            self.assertIn("codex plugin marketplace add .", payload["instructions"])
            self.assertTrue(any(line.startswith("codex plugin add ") for line in payload["instructions"]))
            self.assertTrue(any("codex plugin list" in line for line in payload["instructions"]))
            self.assertTrue(any("/hooks" in line for line in payload["instructions"]))
            self.assertTrue(any("disable john@joharnessburg" in line for line in payload["instructions"]))

    def test_force_preserves_user_agent_and_merges_existing_marketplace(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = root / "project"
            (project / ".codex/agents").mkdir(parents=True)
            user_agent = project / ".codex/agents/researcher.toml"
            user_agent.write_text("# user-owned\n")
            marketplace_path = project / ".agents/plugins/marketplace.json"
            marketplace_path.parent.mkdir(parents=True)
            marketplace_path.write_text(
                json.dumps({"name": "repo", "plugins": [{"name": "other"}]})
            )
            merged = build_merged(root)
            first, first_payload = activate(project, merged)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(first_payload["codex_agents_skipped"], ["researcher.toml"])
            self.assertEqual(user_agent.read_text(), "# user-owned\n")

            (merged / "new.txt").write_text("replacement")
            second, _ = activate(project, merged, "--force")
            self.assertEqual(second.returncode, 0, second.stderr)
            plugins = json.loads(marketplace_path.read_text())["plugins"]
            self.assertEqual([item["name"] for item in plugins], ["other", "john-research-kit"])
            self.assertEqual(user_agent.read_text(), "# user-owned\n")

    def test_rollback_and_boundary_symlink_rejection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project = root / "project"
            project.mkdir()
            merged = build_merged(root)
            first, _ = activate(project, merged)
            self.assertEqual(first.returncode, 0, first.stderr)
            destination = project / ".john-codex/plugins/research-kit"
            sentinel = destination / "sentinel.txt"
            sentinel.write_text("prior")
            (merged / "codex/agents/bad_name.toml").write_text("bad")
            failed, payload = activate(project, merged, "--force")
            self.assertEqual(failed.returncode, 1)
            self.assertFalse(payload["success"])
            self.assertEqual(sentinel.read_text(), "prior")

            external = root / "external"
            external.mkdir()
            shutil_project = root / "symlink-project"
            shutil_project.mkdir()
            os.symlink(external, shutil_project / ".agents")
            failed, payload = activate(shutil_project, merged)
            self.assertEqual(failed.returncode, 1)
            self.assertIn("symlink", payload["error"])
            self.assertEqual(list(external.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
