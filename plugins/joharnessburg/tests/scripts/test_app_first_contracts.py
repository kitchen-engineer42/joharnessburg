"""Tests for app-first intent and display contract helpers."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests._helpers import SCRIPTS_DIR, run_script

sys.path.insert(0, str(SCRIPTS_DIR))
try:
    import app_first_contracts as contracts
finally:
    sys.path.pop(0)


class TestIntentContracts(unittest.TestCase):
    def test_normalize_user_intent_defaults_without_question_batch(self):
        intent = contracts.normalize_user_intent(
            {"style_preferences": {"language": "zh-CN"}}
        )

        self.assertEqual(intent["version"], "john.user_intent.v1")
        self.assertEqual(intent["site_form"], "guided_reading_site")
        self.assertEqual(intent["audience"], "general_reader")
        self.assertEqual(intent["content_priorities"], ["阅读路径", "章节脉络", "核心概念"])
        self.assertFalse(intent["question_batch_used"])
        self.assertIn("raw_json", intent["must_hide"])
        self.assertIn("english_variable_names", intent["must_hide"])

    def test_validate_questions_requires_options_and_free_text(self):
        valid = {
            "version": "john.intent_questions.v1",
            "question_batch_id": "intent-001",
            "max_questions": 4,
            "reason": "Only unresolved high-impact product choices are included.",
            "questions": [
                {
                    "id": "site_form",
                    "prompt": "这个内容更适合做成哪种网站？",
                    "options": [
                        {"id": "guided_reading", "label": "导读网站", "recommended": True},
                        {"id": "searchable_library", "label": "可检索资料库"},
                    ],
                    "free_text_allowed": True,
                }
            ],
        }

        self.assertEqual(contracts.validate_intent_questions(valid), [])

        invalid = dict(valid)
        invalid["questions"] = [
            {
                "id": "site_form",
                "prompt": "选一个方向",
                "options": [{"id": "guided_reading", "label": "导读网站"}],
                "free_text_allowed": False,
            }
        ]
        errors = contracts.validate_intent_questions(invalid)
        self.assertTrue(any("free_text_allowed" in err for err in errors))
        self.assertTrue(any("options" in err for err in errors))

    def test_validate_questions_rejects_second_batch_shape_over_four(self):
        payload = {
            "version": "john.intent_questions.v1",
            "question_batch_id": "intent-002",
            "max_questions": 5,
            "questions": [
                {
                    "id": f"q{i}",
                    "prompt": "问题",
                    "options": [
                        {"id": "a", "label": "A"},
                        {"id": "b", "label": "B"},
                    ],
                    "free_text_allowed": True,
                }
                for i in range(5)
            ],
        }

        errors = contracts.validate_intent_questions(payload)
        self.assertTrue(any("max_questions" in err for err in errors))
        self.assertTrue(any("questions length" in err for err in errors))

    def test_build_contracts_cli_writes_blueprint_and_extraction_plan(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            intent = tdp / "user_intent.json"
            intent.write_text(
                json.dumps(
                    {
                        "version": "john.user_intent.v1",
                        "site_form": "guided_reading_site",
                        "audience": "general_reader",
                        "content_priorities": ["章节脉络"],
                        "style_preferences": {
                            "language": "zh-CN",
                            "tone": "plain",
                            "visual_density": "medium",
                        },
                    },
                    ensure_ascii=False,
                )
            )
            blueprint = tdp / "contracts" / "app_blueprint.json"
            extraction = tdp / "contracts" / "extraction_plan.json"

            rc, out, err = run_script(
                "app_first_contracts.py",
                "build-contracts",
                "--intent",
                str(intent),
                "--blueprint-output",
                str(blueprint),
                "--extraction-output",
                str(extraction),
                cwd=tdp,
            )

            self.assertEqual(rc, 0, f"stderr: {err}")
            self.assertTrue(out["success"])
            blueprint_json = json.loads(blueprint.read_text())
            extraction_json = json.loads(extraction.read_text())
            self.assertEqual(blueprint_json["version"], "john.app_blueprint.v1")
            self.assertIn("章节脉络", blueprint_json["navigation"])
            self.assertIn("chapter_id", blueprint_json["forbidden_visible_terms"])
            self.assertEqual(extraction_json["version"], "john.extraction_plan.v1")
            self.assertTrue(extraction_json["targets"])
            for target in extraction_json["targets"]:
                self.assertIn("ui_slot", target)
                self.assertIn("extract", target)
                self.assertTrue(target["citation_required"])


class TestUiLeakScan(unittest.TestCase):
    def test_scan_ui_leaks_flags_internal_terms_for_chinese_ui(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            html = tdp / "index.html"
            html.write_text(
                "<main>chapter_id: 01</main>\n"
                "<pre>{\"schema_version\": 1}</pre>\n"
                "<p>/Users/example/source.pdf</p>\n",
                encoding="utf-8",
            )

            result = contracts.scan_ui_leaks(tdp, language="zh-CN")

            self.assertFalse(result["success"])
            categories = {item["category"] for item in result["violations"]}
            self.assertIn("internal_identifier", categories)
            self.assertIn("raw_json", categories)
            self.assertIn("workspace_path", categories)
            self.assertIn("english_internal_term", categories)

    def test_scan_ui_leaks_passes_public_chinese_labels(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / "index.html").write_text(
                "<main><h1>导读</h1><section>核心概念</section></main>\n",
                encoding="utf-8",
            )

            result = contracts.scan_ui_leaks(tdp, language="zh-CN")

            self.assertTrue(result["success"])
            self.assertEqual(result["violations"], [])


if __name__ == "__main__":
    unittest.main()
