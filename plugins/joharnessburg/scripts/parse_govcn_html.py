#!/usr/bin/env python3
"""Parse a Chinese government regulation HTML page into structured markdown.

Why this exists: Microsoft's MarkItDown (`markitdown_parse.py`) can't reliably
extract regulation text from gov.cn-style pages, which wrap article content
inside a nested `<div id="UCAP-CONTENT">` or `<div class="pages_content">`
with font-resizer widgets ("字号") and footer cruft around it. This is a
narrow purpose-built fallback for that page family.

Strategy:
1. Read the HTML file as text. Stdlib only (uses html.parser).
2. Locate the article container by id="UCAP-CONTENT" or class="pages_content".
3. Strip nav + font-resizer widgets (anything containing 字号 anchor links).
4. Walk text content, normalize whitespace, split on section markers
   (第一章, 第一条, etc.) to emit H2/H3 headings.
5. Write `doc.md` + `metadata.json` to the output dir.

Out of scope: full DOM rendering, embedded tables, images. This is a narrow
fallback for "markitdown gave me an empty/broken parse on a gov.cn page" —
not a generalist HTML parser.

This script runs in **layer-2 sessions** inside the user's project.

Exit codes:
  0  success
  1  expected failure (bad input, no recognizable container, etc.)
  2  unexpected exception
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import traceback
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


CONTAINER_MARKERS = (
    'id="UCAP-CONTENT"',
    "id='UCAP-CONTENT'",
    'class="pages_content"',
    "class='pages_content'",
    'class="TRS_Editor"',
    "class='TRS_Editor'",
)

# Section / article markers used by Chinese regulations
CHAPTER_PATTERN = re.compile(r"^第[一二三四五六七八九十百千零]+章\s*")
ARTICLE_PATTERN = re.compile(r"^第[一二三四五六七八九十百千零]+条\s*")

# Font-resizer widget anchors (gov.cn boilerplate) — filter out these lines
NOISE_PATTERNS = (
    re.compile(r"^字\s*号\s*[:：]?"),  # "字号:" font-size label
    re.compile(r"^大\s*[\|│]?\s*中\s*[\|│]?\s*小\s*$"),  # 大|中|小 resizer links
    re.compile(r"^返回\s*$"),  # "Back" link
    re.compile(r"^打\s*印\s*$"),  # "Print" link
    re.compile(r"^分\s*享\s*$"),  # "Share" link
)


def emit(payload, success=True, exit_code=0):
    payload["success"] = success
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()
    sys.exit(exit_code)


def err(msg, exit_code=1):
    sys.stderr.write(msg + "\n")
    emit({"error": msg}, success=False, exit_code=exit_code)


class _Stripper(HTMLParser):
    """Collect text content, skipping script/style. Track when we're inside the article container."""

    SKIP_TAGS = {"script", "style", "noscript"}

    def __init__(self, container_attrs):
        super().__init__(convert_charrefs=True)
        self.container_attrs = container_attrs  # set of (attr, value) like {("id", "UCAP-CONTENT")}
        self.depth_inside = 0  # nested-div depth from the container's opening tag
        self.skip_depth = 0  # inside script/style
        self.buffer: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
            return
        attr_dict = dict(attrs)
        # Only ENTER container mode from outside (depth 0). Real pages nest
        # matching containers (e.g. TRS_Editor inside UCAP-CONTENT); resetting
        # the depth there made the inner container's close exit the whole
        # container, silently dropping everything after it.
        if tag == "div" and self.depth_inside == 0 and self._is_container(attr_dict):
            self.depth_inside = 1
            return
        if self.depth_inside > 0 and tag == "div":
            self.depth_inside += 1
        # Treat block tags as line breaks
        if self.depth_inside > 0 and tag in (
            "p", "br", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "table",
        ):
            self.buffer.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.depth_inside > 0 and tag == "div":
            self.depth_inside -= 1

    def handle_data(self, data):
        if self.skip_depth > 0:
            return
        if self.depth_inside > 0:
            self.buffer.append(data)

    def _is_container(self, attr_dict):
        for attr, val in self.container_attrs:
            if attr_dict.get(attr) == val:
                return True
            # Allow class lists to match if val appears in the space-separated list
            if attr == "class" and val in (attr_dict.get("class") or "").split():
                return True
        return False


def _detect_container(html_text: str):
    """Return the set of (attr, value) tuples whose container we'll target."""
    found = []
    if 'id="UCAP-CONTENT"' in html_text or "id='UCAP-CONTENT'" in html_text:
        found.append(("id", "UCAP-CONTENT"))
    if 'class="pages_content"' in html_text or "class='pages_content'" in html_text:
        found.append(("class", "pages_content"))
    if 'class="TRS_Editor"' in html_text or "class='TRS_Editor'" in html_text:
        found.append(("class", "TRS_Editor"))
    return found


def extract_text(html_text: str, container_attrs) -> str:
    parser = _Stripper(container_attrs=container_attrs)
    parser.feed(html_text)
    return "".join(parser.buffer)


def normalize_to_markdown(text: str) -> str:
    """Apply the regulation-shape pass: drop noise lines, mark chapters/articles."""
    out_lines: list[str] = []
    chapter_count = 0
    article_count = 0
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if out_lines and out_lines[-1] != "":
                out_lines.append("")
            continue
        if any(p.search(line) for p in NOISE_PATTERNS):
            continue
        if CHAPTER_PATTERN.match(line):
            chapter_count += 1
            out_lines.append("")
            out_lines.append(f"## {line}")
            out_lines.append("")
            continue
        if ARTICLE_PATTERN.match(line):
            article_count += 1
            out_lines.append("")
            out_lines.append(f"### {line}")
            out_lines.append("")
            continue
        out_lines.append(line)

    # Collapse runs of blank lines
    collapsed: list[str] = []
    blank = False
    for ln in out_lines:
        if ln == "":
            if blank:
                continue
            blank = True
        else:
            blank = False
        collapsed.append(ln)
    return "\n".join(collapsed).strip() + "\n", chapter_count, article_count


def main():
    parser = argparse.ArgumentParser(
        description="Parse a Chinese government regulation HTML page into markdown.",
    )
    parser.add_argument("input_path", help="Path to the input HTML file.")
    parser.add_argument(
        "output_dir",
        help="Directory to write doc.md + metadata.json. Created if missing.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite output files if they already exist.",
    )
    args = parser.parse_args()

    src = Path(args.input_path).expanduser().resolve()
    if not src.exists():
        err(f"Input path does not exist: {src}", exit_code=1)
        return
    if not src.is_file():
        err(f"Input is not a file: {src}", exit_code=1)
        return

    try:
        html_text = src.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Some gov sites still ship GB2312/GBK; try those as fallback
        try:
            html_text = src.read_bytes().decode("gbk")
        except UnicodeDecodeError as exc:
            err(f"Could not decode {src} as UTF-8 or GBK: {exc}", exit_code=1)
            return

    container_attrs = _detect_container(html_text)
    if not container_attrs:
        err(
            f"No recognized gov.cn article container found in {src}. "
            f"Expected one of: id=UCAP-CONTENT, class=pages_content, class=TRS_Editor. "
            f"This script is a narrow fallback — for general HTML use markitdown_parse.py.",
            exit_code=1,
        )
        return

    out_dir = Path(args.output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    doc_md_path = out_dir / "doc.md"
    metadata_path = out_dir / "metadata.json"

    if (doc_md_path.exists() or metadata_path.exists()) and not args.force:
        err(
            f"Output files already exist in {out_dir}. Use --force to overwrite.",
            exit_code=1,
        )
        return

    raw_text = extract_text(html_text, container_attrs)
    body, chapter_count, article_count = normalize_to_markdown(raw_text)

    if not body.strip():
        err(
            f"Extracted 0 chars of text from {src} — the container was found "
            f"but had no readable content. Inspect the file manually.",
            exit_code=1,
        )
        return

    doc_md_path.write_text(body, encoding="utf-8")

    metadata = {
        "source_path": str(src),
        "source_name": src.name,
        "source_size_bytes": src.stat().st_size,
        "parser": "parse_govcn_html",
        "parsed_at": datetime.now(timezone.utc).isoformat(),
        "container_attrs_matched": [list(a) for a in container_attrs],
        "chapter_count": chapter_count,
        "article_count": article_count,
        "char_count": len(body),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    emit(
        {
            "input_path": str(src),
            "output_dir": str(out_dir),
            "doc_md": str(doc_md_path),
            "metadata_json": str(metadata_path),
            "chapter_count": chapter_count,
            "article_count": article_count,
            "char_count": len(body),
        }
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        sys.stderr.write(traceback.format_exc())
        emit({"error": f"unexpected exception: {exc}"}, success=False, exit_code=2)
