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

- **Inputs**: `<project>/.john/input/` (populated by `/joharnessburg-init`)
- **Outputs**: `<project>/.john/parsed/<source-id>/` — one subdirectory per input file, containing `doc.md`, `doc.json` (when applicable), `metadata.json` (provenance: source path, parser, timestamp).
- **Tools**: `${CLAUDE_PLUGIN_ROOT}/scripts/ppx_parse.py` and `${CLAUDE_PLUGIN_ROOT}/scripts/markitdown_parse.py`

## Routing — which parser for which input

The rule is simple and rarely needs fine-tuning:

- **PDFs** → `ppx_parse.py`. Layout-aware, preserves page structure, emits both `doc.md` and `doc.json` with bounding boxes. Default backend is offline (RapidOCR); paddle/deepseek/glm are VLM escalations for hard cases.
- **DOCX, PPTX, XLSX, HTML, Markdown, images with text** → `markitdown_parse.py`. Microsoft's MarkItDown handles structured office formats well. Emits `doc.md` + `metadata.json` only.
- **Plain text, .md** → no parsing needed; copy as-is into `parsed/` with a metadata.json for consistency, OR skip parsing entirely and reference the file directly in the chunking step.

When the input is mixed (most real corpora), parse each file with the right tool. Don't batch by parser — batch by file, route per file.

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
  "parser": "jyppx" | "markitdown",
  "parsed_at": "<ISO 8601>",
  "backend": "<for ppx only>",
  ...
}
```

The original file *path* is metadata; the original *folder hierarchy* is NOT preserved in `.john/parsed/`. The hierarchy was just where the user happened to have the files; John re-arranges knowledge later and shouldn't be constrained by it (per spec §3a: *"Original folder layer and path is kept as an entry of meta-data and we don't usually restore it or trust/rely on too much."*).

## When parsing fails

The scripts fail loud — JSON error to stdout, traceback to stderr. Typical failures:

1. **Dependency not installed.** `ppx_parse.py` needs `pip install -e /path/to/jyppx/ppx`; `markitdown_parse.py` needs `pip install markitdown`. The script's error message says the install command. Tell the user.
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
