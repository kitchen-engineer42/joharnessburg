#!/usr/bin/env python3
"""Parse a PDF into structured markdown + JSON using jyppx (memect-ppx).

Wraps the `memect-ppx` Python package (install: `pip install -e <path-to-jyppx>/ppx`).
Default backend is local (`RapidOCR + RapidLayout + pymupdf`) — offline,
no API keys required. VLM backends (paddle, deepseek, glm) available via
`--backend` for harder layouts.

Writes (in the output directory):
  doc.md           — assembled markdown
  doc.json         — structured: pages -> objects with bbox + type + text
  pages/*.png      — per-page renders
  state.json       — parse timing per stage
  metadata.json    — provenance: original path, backend, timestamp (we add this)

This script runs in **layer-2 sessions** inside the user's project. The
output directory is created if missing.

Exit codes:
  0  success
  1  expected failure (jyppx not installed, bad input, parse error)
  2  unexpected exception
"""

import argparse
import json
import sys
import time
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
        description="Parse a PDF using jyppx (memect-ppx).",
    )
    parser.add_argument("input_path", help="Path to the input PDF.")
    parser.add_argument(
        "output_dir",
        help="Directory to write doc.md, doc.json, pages/, metadata.json. Created if missing.",
    )
    parser.add_argument(
        "--backend",
        default="default",
        choices=["default", "paddle", "deepseek", "glm"],
        help="Parser backend. 'default' is local RapidOCR (free, offline).",
    )
    parser.add_argument(
        "--ocr",
        default="auto",
        choices=["auto", "yes", "no"],
        help="OCR mode. 'auto' = per-region heuristic.",
    )
    parser.add_argument(
        "--table",
        default="auto",
        choices=["auto", "ybk", "wbk", "llm", "no"],
        help="Table parsing mode.",
    )
    parser.add_argument(
        "--no-formula",
        action="store_true",
        help="Skip formula recognition (faster).",
    )
    args = parser.parse_args()

    # Lazy import so we can give a clean error if jyppx isn't installed.
    try:
        from memect.pdf.base import (
            Backend,
            KDocumentFactory,
            OCRMode,
            ParseParams,
            TableMode,
        )
        from memect.pdf.parser import Parser
    except ImportError:
        err(
            "memect-ppx (jyppx) is not installed. Install with: "
            "pip install -e /path/to/jyppx/ppx  "
            "(see https://github.com/memect/memect-ppx)",
            exit_code=1,
        )
        return

    src = Path(args.input_path).expanduser().resolve()
    if not src.exists():
        err(f"Input path does not exist: {src}", exit_code=1)
        return
    if not src.is_file():
        err(f"Input is not a file: {src}", exit_code=1)
        return
    if src.suffix.lower() != ".pdf":
        sys.stderr.write(
            f"WARN: input does not have .pdf extension ({src.suffix}). "
            f"ppx will attempt to parse anyway.\n"
        )

    out_dir = Path(args.output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Map CLI flags to ppx enums
    backend_map = {
        "default": Backend.DEFAULT,
        "paddle": Backend.PADDLE,
        "deepseek": Backend.DEEPSEEK,
        "glm": Backend.GLM,
    }
    ocr_map = {
        "auto": OCRMode.AUTO,
        "yes": OCRMode.YES,
        "no": OCRMode.NO,
    }
    table_map = {
        "auto": TableMode.AUTO,
        "ybk": TableMode.YBK,
        "wbk": TableMode.WBK,
        "llm": TableMode.LLM,
        "no": TableMode.NO,
    }

    params = ParseParams(
        backend=backend_map[args.backend],
        ocr=ocr_map[args.ocr],
        table=table_map[args.table],
        formula=not args.no_formula,
        markdown=True,
        doc_json=True,
    )

    factory = KDocumentFactory(file=src, params=params, out_dir=out_dir)
    doc = factory()

    started = time.time()
    try:
        with Parser() as p:
            p.parse(doc)
    except Exception as exc:
        sys.stderr.write(traceback.format_exc())
        elapsed = time.time() - started
        err(
            f"ppx parse failed after {elapsed:.1f}s: {exc}",
            exit_code=1,
        )
        return
    elapsed = time.time() - started

    # Write our own metadata.json alongside ppx's outputs
    metadata = {
        "source_path": str(src),
        "source_name": src.name,
        "source_size_bytes": src.stat().st_size,
        "parser": "jyppx",
        "backend": args.backend,
        "ocr": args.ocr,
        "table": args.table,
        "formula": not args.no_formula,
        "parsed_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(elapsed, 2),
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")

    doc_md = out_dir / "doc.md"
    doc_json = out_dir / "doc.json"

    emit(
        {
            "input_path": str(src),
            "output_dir": str(out_dir),
            "backend": args.backend,
            "doc_md": str(doc_md) if doc_md.exists() else None,
            "doc_json": str(doc_json) if doc_json.exists() else None,
            "metadata_json": str(out_dir / "metadata.json"),
            "elapsed_seconds": round(elapsed, 2),
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
