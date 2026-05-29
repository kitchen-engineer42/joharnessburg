#!/usr/bin/env python3
"""Parse a PDF via John's local ppx-client server.

Thin HTTP client. POSTs to `$JOHN_PPX_CLIENT_URL` (default
`http://localhost:8501`) `/parse` endpoint. The server wraps the
`memect-ppx` parser engine.

When a production PDF_PARSE_SERVER is available, swap `JOHN_PPX_CLIENT_URL`
to point at it; this script keeps working without code changes.

Terminology: `ppx` (memect-ppx) is the parser engine. This script talks to
it via the local client server.

Exit codes:
  0  success
  1  expected failure (bad input path, server unreachable, parse error)
  2  unexpected exception
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_CLIENT_URL = "http://localhost:8501"


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
        description="Parse a PDF via John's local ppx-client server.",
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
        "--ocr", default="auto", choices=["auto", "yes", "no"],
        help="OCR mode. 'auto' = per-region heuristic.",
    )
    parser.add_argument(
        "--table", default="auto", choices=["auto", "ybk", "wbk", "llm", "no"],
        help="Table parsing mode.",
    )
    parser.add_argument(
        "--no-formula", action="store_true", help="Skip formula recognition (faster).",
    )
    parser.add_argument(
        "--client-url",
        default=os.environ.get("JOHN_PPX_CLIENT_URL", DEFAULT_CLIENT_URL),
        help=f"ppx-client server URL (default: $JOHN_PPX_CLIENT_URL or {DEFAULT_CLIENT_URL})",
    )
    args = parser.parse_args()

    src = Path(args.input_path).expanduser().resolve()
    if not src.exists():
        err(f"Input path does not exist: {src}", exit_code=1)
        return
    if not src.is_file():
        err(f"Input is not a file: {src}", exit_code=1)
        return

    out_dir = Path(args.output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "input_path": str(src),
        "output_dir": str(out_dir),
        "backend": args.backend,
        "ocr": args.ocr,
        "table": args.table,
        "formula": not args.no_formula,
    }

    url = args.client_url.rstrip("/") + "/parse"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # HTTPError MUST be caught before URLError — it's a subclass of
        # URLError, so the order matters. A server-side 422/500 with a JSON
        # body should surface as a parse error, not as "could not reach server".
        try:
            detail = json.loads(exc.read().decode("utf-8"))
            detail_msg = detail.get("error") or detail.get("detail") or detail
        except Exception:
            detail = {"status": exc.code, "reason": exc.reason}
            detail_msg = f"{exc.code} {exc.reason}"
        err(
            f"ppx-client returned HTTP {exc.code}: {detail_msg}",
            exit_code=1,
        )
        return
    except urllib.error.URLError as exc:
        # Transport-level failure (connection refused, DNS, etc.) — server
        # unreachable, not a server-side error.
        err(
            f"Could not reach ppx-client server at {url}: {exc.reason}. "
            f"Make sure your ppx client server is running and listening at that URL, "
            f"or set $JOHN_PPX_CLIENT_URL (or --url) to point at a reachable server.",
            exit_code=1,
        )
        return

    # Server returns ParseResult fields directly; pass through to stdout.
    if not body.get("success", False):
        err(f"ppx parse failed: {body.get('error', 'unknown error')}", exit_code=1)
        return

    emit(
        {
            "input_path": body.get("input_path"),
            "output_dir": body.get("output_dir"),
            "backend": body.get("backend"),
            "doc_md": body.get("doc_md"),
            "doc_json": body.get("doc_json"),
            "metadata_json": body.get("metadata_json"),
            "elapsed_seconds": body.get("elapsed_seconds"),
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
