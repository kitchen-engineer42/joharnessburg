#!/usr/bin/env python3
"""Parse a non-PDF document into markdown using MarkItDown.

Wraps Microsoft's `markitdown` Python package (`pip install markitdown`).
Use for DOCX, PPTX, XLSX, HTML, etc. For PDFs, prefer `ppx_parse.py`
which preserves layout structure.

Writes:
  <output-dir>/doc.md         — the parsed markdown
  <output-dir>/metadata.json  — provenance: original path, parser, timestamp

This script runs in **layer-2 sessions** inside the user's project. The
output directory is created if missing.

Exit codes:
  0  success
  1  expected failure (markitdown not installed, bad input, output exists without --force)
  2  unexpected exception
"""

import argparse
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path


def emit(payload, success=True, exit_code=0):
    payload["success"] = success
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()
    sys.exit(exit_code)


def err(msg, exit_code=1):
    sys.stderr.write(msg + "\n")
    emit({"error": msg}, success=False, exit_code=exit_code)


def main():
    parser = argparse.ArgumentParser(
        description="Parse a non-PDF document into markdown using MarkItDown.",
    )
    parser.add_argument("input_path", help="Path to the input document.")
    parser.add_argument(
        "output_dir",
        help="Directory to write doc.md and metadata.json into. Created if missing.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite output files if they already exist.",
    )
    args = parser.parse_args()

    try:
        from markitdown import MarkItDown
    except ImportError:
        err(
            "markitdown package not installed. Install with: pip install markitdown",
            exit_code=1,
        )
        return

    src = Path(args.input_path).expanduser().resolve()
    if not src.exists():
        err(f"Input path does not exist: {src}", exit_code=1)
        return
    if src.is_dir():
        err(
            f"Input is a directory; pass a single file path. "
            f"For batch parsing, call this script once per file.",
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

    converter = MarkItDown()
    result = converter.convert_local(str(src))
    text = getattr(result, "text_content", None)
    if text is None:
        text = getattr(result, "markdown", None)
    if text is None:
        err(
            f"MarkItDown returned a result object with neither `text_content` "
            f"nor `markdown` attribute (got fields: "
            f"{sorted(a for a in dir(result) if not a.startswith('_'))}). "
            f"Markitdown's API may have changed; check the installed version "
            f"(`pip show markitdown`) against the script's expectations.",
            exit_code=1,
        )
        return

    doc_md_path.write_text(text, encoding="utf-8")

    metadata = {
        "source_path": str(src),
        "source_name": src.name,
        "source_size_bytes": src.stat().st_size,
        "parser": "markitdown",
        "parsed_at": datetime.now(timezone.utc).isoformat(),
        "char_count": len(text),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    emit(
        {
            "input_path": str(src),
            "output_dir": str(out_dir),
            "doc_md": str(doc_md_path),
            "metadata_json": str(metadata_path),
            "char_count": len(text),
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
