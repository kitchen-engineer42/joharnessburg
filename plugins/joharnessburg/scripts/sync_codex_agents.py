#!/usr/bin/env python3
"""Deterministically generate Codex TOML agents from canonical Claude Markdown."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PLUGIN_ROOT.parents[1]
SOURCE_DIR = PLUGIN_ROOT / "agents"
DESTINATIONS = (PLUGIN_ROOT / "codex" / "agents", REPO_ROOT / ".codex" / "agents")

# Provider-only execution tuning stays here; semantic instructions stay in the
# canonical Markdown agents.
CODEX_OVERRIDES = {
    "code-quality-reviewer": {"model_reasoning_effort": "high", "sandbox_mode": "read-only"},
    "coverage-auditor": {"model_reasoning_effort": "high", "sandbox_mode": "workspace-write"},
    "grounding-checker": {"model_reasoning_effort": "high", "sandbox_mode": "workspace-write"},
    "knowledge-extractor": {"model_reasoning_effort": "medium", "sandbox_mode": "workspace-write"},
    "schema-designer": {"model_reasoning_effort": "high", "sandbox_mode": "workspace-write"},
}


def parse_agent(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError(f"missing frontmatter: {path}")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError(f"unterminated frontmatter: {path}") from exc
    metadata: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition(":")
        if not separator:
            raise ValueError(f"unsupported frontmatter line in {path}: {line!r}")
        metadata[key.strip()] = value.strip()
    for required in ("name", "description", "tools"):
        if not metadata.get(required):
            raise ValueError(f"missing {required} in {path}")
    body = "\n".join(lines[end + 1 :]).strip() + "\n"
    return metadata, body


def render(path: Path) -> tuple[str, str]:
    metadata, body = parse_agent(path)
    name = metadata["name"]
    tools = [tool.strip() for tool in metadata["tools"].split(",") if tool.strip()]
    instructions = (
        body
        + "\n## Tools\n\n"
        + "Claude tool metadata is semantic guidance, not a Codex permission boundary.\n\n"
        + "Use only these capabilities for this role:\n\n"
        + "\n".join(f"- {tool}" for tool in tools)
        + "\n"
    )
    lines = [
        f"name = {json.dumps(name, ensure_ascii=False)}",
        f"description = {json.dumps(metadata['description'], ensure_ascii=False)}",
        f"developer_instructions = {json.dumps(instructions, ensure_ascii=False)}",
    ]
    for key, value in CODEX_OVERRIDES.get(name, {}).items():
        lines.append(f"{key} = {json.dumps(value)}")
    return name, "\n".join(lines) + "\n"


def expected() -> dict[str, str]:
    rendered: dict[str, str] = {}
    for source in sorted(SOURCE_DIR.glob("*.md")):
        name, content = render(source)
        if source.stem != name:
            raise ValueError(f"agent filename/name mismatch: {source}")
        rendered[f"{name}.toml"] = content
    if set(rendered) != {f"{name}.toml" for name in CODEX_OVERRIDES}:
        raise ValueError("CODEX_OVERRIDES must name every canonical agent exactly once")
    return rendered


def write_outputs(rendered: dict[str, str]) -> None:
    for destination in DESTINATIONS:
        destination.mkdir(parents=True, exist_ok=True)
        for stale in destination.glob("*.toml"):
            if stale.name not in rendered:
                stale.unlink()
        for filename, content in rendered.items():
            (destination / filename).write_text(content, encoding="utf-8")


def check_outputs(rendered: dict[str, str]) -> list[str]:
    drift: list[str] = []
    for destination in DESTINATIONS:
        actual_names = {path.name for path in destination.glob("*.toml")}
        if actual_names != set(rendered):
            drift.append(f"{destination}: file set differs")
        for filename, content in rendered.items():
            path = destination / filename
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                drift.append(str(path))
    return drift


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        rendered = expected()
        if args.write:
            write_outputs(rendered)
            print(json.dumps({"success": True, "agents": sorted(rendered)}))
            return 0
        drift = check_outputs(rendered)
        print(json.dumps({"success": not drift, "drift": drift}))
        return 0 if not drift else 1
    except (OSError, ValueError) as exc:
        print(json.dumps({"success": False, "error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
