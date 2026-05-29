---
name: parsing
description: Turn raw input materials (PDFs, DOCX, mixed docs) into structured markdown for the rest of John's pipeline. Use whenever the user's `<project>/.john/input/` has unparsed files, when a phase needs to read source documents, or when the user mentions parsing/OCR/ingestion. Routes between `ppx_parse.py` (PDFs, layout-aware) and `markitdown_parse.py` (everything else); fails loud with install hints when dependencies are missing.
metadata:
  triggers:
    - parse documents
    - parse PDFs
    - ingest input
    - OCR
    - parse the corpus
    - convert to markdown
    - invoke the parser
---

# parsing

The first useful thing John does on any project: read the user's raw input materials and produce structured markdown the rest of the pipeline can consume. This skill teaches you *when* to use which parser, *how* to invoke them, and *what* to do when something fails.

## Where the work happens

- **Inputs**: `<project>/.john/input/` (populated by `/john:init`)
- **Outputs**: `<project>/.john/parsed/<source-id>/` — one subdirectory per input file, containing `doc.md`, `doc.json` (when applicable), `metadata.json` (provenance: source path, parser, timestamp).
- **Tools**: `${CLAUDE_PLUGIN_ROOT}/scripts/ppx_parse.py` (thin HTTP client to a local ppx-client server) and `${CLAUDE_PLUGIN_ROOT}/scripts/markitdown_parse.py` (in-process).
- **Server URLs** (read from environment): `$JOHN_PPX_CLIENT_URL` (default `http://localhost:8501`). The server is launched separately via `local_clients/ppx/scripts/start.sh` in the John workspace bundle.

## Routing — which parser for which input

Top strategy:

- **PDFs + images** → `ppx_parse.py` (calls the local ppx-client server). ppx has a built-in probe + mode selector for non-scanned PDFs and is fast on them; for scans it routes to OCR. Use ppx for all PDFs by default.
- **DOCX, PPTX, XLSX, HTML, Markdown** → `markitdown_parse.py`. Fast pure-Python; right for office formats and clean HTML.
- **Chinese government regulation HTML** (`*.gov.cn` pages, or anything with `<div id="UCAP-CONTENT">` / `<div class="pages_content">` / `<div class="TRS_Editor">`) → `parse_govcn_html.py`. markitdown can't parse the nested container layout; this is a narrow fallback. See `references/gov-cn-html.md`.
- **Plain text, .md** → no parsing needed; copy as-is into `parsed/` with a metadata.json for consistency, OR skip parsing entirely and reference the file directly in the chunking step.

**Fallback when markitdown gives clearly-off results**: if a 50 MB DOCX (full of images) produces tiny markdown output (a few KB), markitdown stripped too much. Convert the document to PDF (e.g., LibreOffice headless, `pdfgen`, the OS print-to-PDF), then route to ppx. ppx will handle the images + layout properly.

When the input is mixed (most real corpora), parse each file with the right tool. Don't batch by parser — batch by file, route per file. Claude is good at making this call per file; trust it.

## Subagent fan-out for parsing

For corpora with many files, parsing is **embarrassingly parallel**: one subagent per file. Per [[subagent-dispatch]], brief each subagent with:
- The file path (under `.john/input/`)
- The target output path (under `.john/parsed/<source-id>/`)
- Which script to call + flags
- The expected JSON output shape — events to emit per [[event-log-and-reducer]]

For small corpora (≤20 files), parsing inline is fine. The overhead of subagent dispatch isn't worth it.

Each parse subagent emits a `file_parsed` event to `<project>/.john/events/parse/<source-id>/`. The event payload records the source path, the output dir, the parser used, and whether output is `doc.md` only (markitdown) or `doc.md` + `doc.json` (ppx). See [[event-log-and-reducer]] for the event wrapping fields; this skill just provides the payload shape contract.

## Backend escalation for PDFs

`ppx_parse.py --backend default` (RapidOCR + RapidLayout + pymupdf) handles maybe 80% of real PDFs well: digital-native PDFs with extractable text, standard layouts, common languages. Escalate when:

- **Scanned PDFs with poor OCR**: try `--backend paddle` (PaddleOCR-VL) — better Chinese, dense layouts.
- **Mixed text + heavy tables/figures**: try `--backend deepseek` or `--backend glm` — VLM models that understand visual structure.
- **All VLM backends fail** (rare): the input may be genuinely broken (scanned to image-only PDF with bad rendering). Note this in the parse phase Log section of PLAN.md and ask the user before spending more credits.

Don't escalate without observing failure first. Default backend is free and offline; VLM backends cost API credits.

## Preserving source provenance

Every parsed output gets a `metadata.json` with:

```json
{
  "source_path": "<absolute path of original>",
  "source_name": "<basename>",
  "source_size_bytes": <int>,
  "parser": "ppx" | "markitdown",
  "parsed_at": "<ISO 8601>",
  "backend": "<for ppx only>",
  ...
}
```

The original file *path* is metadata; the original *folder hierarchy* is NOT preserved in `.john/parsed/`. The hierarchy was just where the user happened to have the files; John re-arranges knowledge later and shouldn't be constrained by it.

## When parsing fails

The scripts fail loud — JSON error to stdout, traceback to stderr. Typical failures:

1. **Server not running or dependency not installed.** `ppx_parse.py` is a thin HTTP client to a local ppx-client server; if the server isn't running, the script says so + points at `local_clients/ppx/scripts/start.sh`. If the ppx engine (`memect-ppx`) isn't installed in the server's env, the server returns 503 with install guidance. `markitdown_parse.py` runs in-process and needs `pip install markitdown`. Tell the user the exact install/launch command from the error message.
2. **Bad input path.** Script reports it; check `.john/input/` is populated.
3. **Parse exception** (OOM on huge PDF, malformed file, etc.). Capture in the parse phase Log section. For the OOM case, escalate to a smaller-batch approach (parse a subset of pages with `--pages` if ppx supports it).

Don't auto-retry indefinitely. Two strikes per file, then surface to the user in the parse phase Log section of PLAN.md with: the file path, the error message, what was tried, and a suggested next step (manual conversion, escalate backend, skip the file). Don't escalate to VLM backends without explicit user permission — those cost credits.

**Re-running on already-parsed files**: per [[workspace-discipline]] rule 2 (idempotent operations), parse subagents should check whether `<project>/.john/parsed/<source-id>/doc.md` exists before re-parsing. Default: skip if present (work already done). The user can force re-parse with explicit instruction; the script doesn't auto-overwrite.

## What this skill doesn't do

- **Chunking**. Parsing produces `doc.md`; chunking turns it into a tree of progressively-disclosed pieces. See [[chunking]].
- **Schema decisions**. See [[schema-design]].
- **Knowledge extraction**. See [[knowledge-extraction]].

## Cross-references

- [[chunking]] — what to do with parsed markdown next
- [[subagent-dispatch]] — fan out parallel parsing
- [[event-log-and-reducer]] — emit parse-events for a phase
- [[workspace-discipline]] — idempotent writes, preserve provenance
- See `references/` for: ppx invocation recipe, markitdown behavior, production-parser swap note
