#!/usr/bin/env python3
from __future__ import annotations

"""Utilities for John's app-first intent and display contracts.

The LLM still makes the product judgment calls. This script keeps the
machine-readable artifacts predictable: normalized intent, app blueprint,
extraction plan, one-shot question batch validation, and UI leak checks.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


INTENT_VERSION = "john.user_intent.v1"
QUESTIONS_VERSION = "john.intent_questions.v1"
BLUEPRINT_VERSION = "john.app_blueprint.v1"
EXTRACTION_PLAN_VERSION = "john.extraction_plan.v1"

DEFAULT_MUST_HIDE = [
    "raw_json",
    "internal_ids",
    "skill_names",
    "schema_keys",
    "chunk_ids",
    "file_paths",
    "english_variable_names",
]

DEFAULT_CONTENT_PRIORITIES_ZH = ["阅读路径", "章节脉络", "核心概念"]
DEFAULT_CONTENT_PRIORITIES_EN = ["reading path", "structure", "key concepts"]

HIDE_KEY_TERMS = {
    "raw_json": ["raw_json", "```json", "{\"version\"", "{\"schema_version\""],
    "internal_ids": ["internal_id", "internal_ids"],
    "skill_names": ["skill_name", "skill_names"],
    "schema_keys": ["schema_key", "schema_keys", "schema_version"],
    "chunk_ids": ["chunk_id", "chunk_ids"],
    "file_paths": [".john/", ".claude/skills/", ".agents/skills/", "/Users/"],
    "english_variable_names": ["chapter_id", "chapter", "schema", "chunk", "skill"],
}

TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".htm",
    ".js",
    ".jsx",
    ".json",
    ".md",
    ".mjs",
    ".ts",
    ".tsx",
    ".txt",
    ".vue",
}

SKIP_DIRS = {".git", "node_modules", "__pycache__"}


def dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]


def is_zh(language: str) -> bool:
    return language.lower().startswith("zh")


def normalize_user_intent(
    payload: dict[str, Any] | None = None,
    *,
    question_batch_used: bool = False,
    default_language: str = "source_language",
) -> dict[str, Any]:
    """Return a complete john.user_intent.v1 object.

    The caller may pass a partial LLM-normalized object. Missing fields get
    conservative ordinary-user defaults.
    """
    source = payload if isinstance(payload, dict) else {}
    style = source.get("style_preferences")
    if not isinstance(style, dict):
        style = {}

    hard_constraints = source.get("hard_constraints")
    if not isinstance(hard_constraints, dict):
        hard_constraints = {}

    language = str(
        style.get("language")
        or source.get("language")
        or default_language
    )
    priorities_default = (
        DEFAULT_CONTENT_PRIORITIES_ZH
        if is_zh(language)
        else DEFAULT_CONTENT_PRIORITIES_EN
    )

    must_hide = string_list(source.get("must_hide"))
    must_hide += string_list(hard_constraints.get("must_hide"))
    must_hide = dedupe(DEFAULT_MUST_HIDE + must_hide)

    assumptions = string_list(source.get("assumptions"))
    if not source:
        assumptions.append("No explicit product preferences were provided; ordinary-user defaults were used.")

    return {
        "version": INTENT_VERSION,
        "site_form": str(source.get("site_form") or "guided_reading_site"),
        "audience": str(source.get("audience") or "general_reader"),
        "content_priorities": string_list(
            source.get("content_priorities")
        ) or priorities_default,
        "style_preferences": {
            "language": language,
            "tone": str(style.get("tone") or "plain"),
            "visual_density": str(style.get("visual_density") or "medium"),
        },
        "must_hide": must_hide,
        "assumptions": dedupe(assumptions),
        "question_batch_used": bool(
            source.get("question_batch_used", question_batch_used)
        ),
    }


def validate_intent_questions(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("version") != QUESTIONS_VERSION:
        errors.append(f"version must be {QUESTIONS_VERSION}")

    max_questions = payload.get("max_questions", 4)
    if not isinstance(max_questions, int) or max_questions < 1 or max_questions > 4:
        errors.append("max_questions must be an integer from 1 to 4")

    questions = payload.get("questions")
    if not isinstance(questions, list) or not questions:
        errors.append("questions must be a non-empty list")
        return errors
    if len(questions) > min(max_questions, 4):
        errors.append("questions length exceeds max_questions or global limit 4")

    for idx, question in enumerate(questions):
        prefix = f"questions[{idx}]"
        if not isinstance(question, dict):
            errors.append(f"{prefix} must be an object")
            continue
        if not question.get("id"):
            errors.append(f"{prefix}.id is required")
        if not question.get("prompt"):
            errors.append(f"{prefix}.prompt is required")
        if question.get("free_text_allowed") is not True:
            errors.append(f"{prefix}.free_text_allowed must be true")
        options = question.get("options")
        if not isinstance(options, list) or len(options) < 2:
            errors.append(f"{prefix}.options must contain at least two options")
            continue
        recommended_count = 0
        for option_idx, option in enumerate(options):
            option_prefix = f"{prefix}.options[{option_idx}]"
            if not isinstance(option, dict):
                errors.append(f"{option_prefix} must be an object")
                continue
            if not option.get("id"):
                errors.append(f"{option_prefix}.id is required")
            if not option.get("label"):
                errors.append(f"{option_prefix}.label is required")
            if option.get("recommended") is True:
                recommended_count += 1
        if recommended_count > 1:
            errors.append(f"{prefix}.options must not mark more than one recommended option")
    return errors


def forbidden_visible_terms(must_hide: list[str]) -> list[str]:
    terms: list[str] = []
    for key in must_hide:
        terms.extend(HIDE_KEY_TERMS.get(key, [key]))
    return dedupe(terms)


def build_app_blueprint(user_intent: dict[str, Any]) -> dict[str, Any]:
    language = str(
        user_intent.get("style_preferences", {}).get("language", "source_language")
    )
    zh = is_zh(language)
    site_form = str(user_intent.get("site_form", "guided_reading_site"))

    if "library" in site_form or "资料库" in site_form:
        navigation = ["导读", "检索", "主题", "原文出处"] if zh else [
            "Guide",
            "Search",
            "Topics",
            "Sources",
        ]
        page_types = ["overview", "search", "topic_index", "source_view"]
    elif "manual" in site_form or "手册" in site_form:
        navigation = ["开始", "学习路径", "核心概念", "练习"] if zh else [
            "Start",
            "Learning Path",
            "Key Concepts",
            "Practice",
        ]
        page_types = ["overview", "lesson", "concept_card", "practice"]
    else:
        navigation = ["导读", "章节脉络", "核心概念", "原文出处"] if zh else [
            "Guide",
            "Structure",
            "Key Concepts",
            "Sources",
        ]
        page_types = ["overview", "section_digest", "concept_card", "source_view"]

    content_modules = ["summary", "key_points", "quotes", "related_items"]
    public_labels = {
        "summary": "摘要" if zh else "Summary",
        "key_points": "要点" if zh else "Key Points",
        "quotes": "原文依据" if zh else "Source Evidence",
        "related_items": "相关内容" if zh else "Related Items",
    }

    return {
        "version": BLUEPRINT_VERSION,
        "public_language": language,
        "site_form": site_form,
        "audience": user_intent.get("audience", "general_reader"),
        "navigation": navigation,
        "page_types": page_types,
        "content_modules": content_modules,
        "public_labels": public_labels,
        "forbidden_visible_terms": forbidden_visible_terms(
            string_list(user_intent.get("must_hide")) or DEFAULT_MUST_HIDE
        ),
    }


def extraction_fields_for_slot(slot: str, zh: bool) -> list[str]:
    normalized = slot.lower()
    if "章节" in slot or "structure" in normalized or "section" in normalized:
        return ["章节标题", "章节摘要", "关键观点", "承接关系", "原文依据"] if zh else [
            "section title",
            "section summary",
            "key points",
            "continuity",
            "source evidence",
        ]
    if "概念" in slot or "concept" in normalized or "topic" in normalized:
        return ["概念名", "通俗解释", "相关章节", "原文依据"] if zh else [
            "concept name",
            "plain explanation",
            "related sections",
            "source evidence",
        ]
    if "检索" in slot or "search" in normalized:
        return ["标题", "别名", "摘要", "关键词", "原文依据"] if zh else [
            "title",
            "aliases",
            "summary",
            "keywords",
            "source evidence",
        ]
    return ["主题简介", "阅读顺序", "入口说明", "原文依据"] if zh else [
        "topic introduction",
        "reading order",
        "entry guidance",
        "source evidence",
    ]


def build_extraction_plan(app_blueprint: dict[str, Any]) -> dict[str, Any]:
    language = str(app_blueprint.get("public_language", "source_language"))
    zh = is_zh(language)
    targets = []
    for slot in string_list(app_blueprint.get("navigation")):
        targets.append(
            {
                "ui_slot": slot,
                "extract": extraction_fields_for_slot(slot, zh),
                "citation_required": True,
                "minimum_viable_content": (
                    "每个 UI 槽至少需要摘要和原文依据"
                    if zh
                    else "Each UI slot needs at least a summary and source evidence"
                ),
            }
        )
    return {
        "version": EXTRACTION_PLAN_VERSION,
        "source_blueprint_version": app_blueprint.get("version"),
        "targets": targets,
    }


def iter_text_files(root: Path):
    if root.is_file():
        if root.suffix.lower() in TEXT_SUFFIXES:
            yield root
        return
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def scan_ui_leaks(root: Path, *, language: str = "source_language") -> dict[str, Any]:
    patterns = [
        ("raw_json", re.compile(r"\{\s*\"(?:version|schema_version|chapter_id|chunk_id|skill_name)\"")),
        ("internal_identifier", re.compile(r"\b(?:chapter_id|schema_version|chunk_id|skill_name|skill_names|raw_json|internal_ids)\b")),
        ("workspace_path", re.compile(r"(?:/Users/[^\s\"'<>]+|\.john/|plugins/joharnessburg)")),
    ]
    if is_zh(language):
        patterns.append(
            (
                "english_internal_term",
                re.compile(
                    r"\b(?:chapter(?:_id)?|schema(?:_version)?|chunk(?:_id)?|skill(?:_name)?|json)\b",
                    re.IGNORECASE,
                ),
            )
        )

    violations = []
    for path in iter_text_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            violations.append(
                {
                    "file": str(path),
                    "line": 0,
                    "category": "read_error",
                    "match": str(exc),
                }
            )
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            for category, pattern in patterns:
                match = pattern.search(line)
                if match:
                    violations.append(
                        {
                            "file": str(path),
                            "line": line_no,
                            "category": category,
                            "match": match.group(0),
                        }
                    )
    return {
        "version": "john.ui_leak_scan.v1",
        "success": not violations,
        "violations": violations,
    }


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(payload: dict[str, Any], path: Path | None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if path is None:
        sys.stdout.write(text)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    sys.stdout.write(json.dumps({"success": True, "path": str(path)}) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    normalize = sub.add_parser("normalize-intent")
    normalize.add_argument("--input", type=Path)
    normalize.add_argument("--output", type=Path)
    normalize.add_argument("--question-batch-used", action="store_true")
    normalize.add_argument("--default-language", default="source_language")

    validate = sub.add_parser("validate-questions")
    validate.add_argument("input", type=Path)

    build = sub.add_parser("build-contracts")
    build.add_argument("--intent", type=Path, required=True)
    build.add_argument("--blueprint-output", type=Path, required=True)
    build.add_argument("--extraction-output", type=Path, required=True)

    scan = sub.add_parser("scan-ui-leaks")
    scan.add_argument("root", type=Path)
    scan.add_argument("--language", default="source_language")

    args = parser.parse_args()

    try:
        if args.cmd == "normalize-intent":
            payload = normalize_user_intent(
                load_json(args.input),
                question_batch_used=args.question_batch_used,
                default_language=args.default_language,
            )
            write_json(payload, args.output)
            return 0
        if args.cmd == "validate-questions":
            errors = validate_intent_questions(load_json(args.input))
            sys.stdout.write(
                json.dumps({"success": not errors, "errors": errors}, ensure_ascii=False)
                + "\n"
            )
            return 0 if not errors else 2
        if args.cmd == "build-contracts":
            intent = normalize_user_intent(load_json(args.intent))
            blueprint = build_app_blueprint(intent)
            extraction = build_extraction_plan(blueprint)
            args.blueprint_output.parent.mkdir(parents=True, exist_ok=True)
            args.extraction_output.parent.mkdir(parents=True, exist_ok=True)
            args.blueprint_output.write_text(
                json.dumps(blueprint, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            args.extraction_output.write_text(
                json.dumps(extraction, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            sys.stdout.write(
                json.dumps(
                    {
                        "success": True,
                        "app_blueprint": str(args.blueprint_output),
                        "extraction_plan": str(args.extraction_output),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            return 0
        if args.cmd == "scan-ui-leaks":
            result = scan_ui_leaks(args.root, language=args.language)
            sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
            return 0 if result["success"] else 3
    except Exception as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        sys.stdout.write(json.dumps({"success": False, "error": str(exc)}) + "\n")
        return 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
