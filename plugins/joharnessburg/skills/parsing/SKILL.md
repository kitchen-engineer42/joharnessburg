---
name: parsing
description: Turn raw input materials (PDFs, DOCX, mixed docs) into structured markdown for the rest of John's pipeline. Use whenever the user's `<project>/.john/input/` has unparsed files, when a phase needs to read source documents, or when the user mentions parsing/OCR/ingestion. Teaches a probe-first capability ladder — Claude-native reading → markitdown in-process → ppx when present — and when to escalate because results aren't good enough for the job, not just absent; fails loud with install hints when dependencies are missing.
metadata:
  triggers:
    - parse documents
    - parse PDFs
    - ingest input
    - OCR
    - parse the corpus
    - convert to markdown
    - invoke the parser
    - which parser
---

# parsing

The first useful thing John does on any project: read the user's raw input materials and produce structured markdown the rest of the pipeline can consume. This skill teaches a **capability ladder** — probe what you have, start at the cheapest rung that works, and escalate when the output isn't good enough for the job.

## Probe first

Before parsing anything, take stock of two things and write the result into PLAN.md's parse-phase notes:

1. **The corpus**: file types, counts, sizes, and structure. Is it native-PDF or scanned? Office formats? A folder tree of small files? One 2,000-page monster? A quick inventory (`ls -R` + reading the first KB of representative files) tells you which rungs you'll need.
2. **The environment**: which rungs are available. markitdown is in-process (`pip install markitdown`); ppx is reachable only if `$JOHN_PPX_CLIENT_URL` is set and its health endpoint responds. Probe, don't assume — a missing rung changes routing, and discovering that mid-fan-out wastes a phase.

Echo what you found ("32 PDFs (~8 scanned), 5 DOCX, ppx reachable at :8501") before routing. Cheap self-check: if the inventory is wrong, every downstream decision is wrong.

## The capability ladder

Three rungs, cheapest first. The default path for a fresh `git clone` of John (no servers running) is rungs 0–1 — **never block on rung 2 being absent**.

- **Tier 0 — Claude-native.** You read text, markdown, code, and simple/small PDFs directly. For small or already-clean inputs, no parser at all: copy into `parsed/` with a `metadata.json` for consistency (or reference the file directly at the chunking step).
- **Tier 1 — markitdown, the universal in-process default.** `${CLAUDE_PLUGIN_ROOT}/scripts/markitdown_parse.py`. DOCX, PPTX, XLSX, HTML, plain formats. Pure Python, no server. See `references/markitdown-recipe.md`.
- **Tier 2 — ppx, the high-fidelity PDF path when present.** `${CLAUDE_PLUGIN_ROOT}/scripts/ppx_parse.py`, a thin HTTP client to the server at `$JOHN_PPX_CLIENT_URL` (default `http://localhost:8501`). Layout-aware parsing, table/figure structure, OCR routing for scans, structured `doc.json` alongside `doc.md`. Use it for all PDFs **when the probe found it reachable**; otherwise PDFs fall to Tier 1/0 with the quality caveat below. The URL is the contract — any backend speaking the same HTTP shape can serve this rung (see `references/parser-backend-swapping.md`).

One narrow specialist sits outside the ladder: **Chinese government regulation HTML** (`*.gov.cn` pages with `<div id="UCAP-CONTENT">` / `TRS_Editor` containers) → `parse_govcn_html.py`; markitdown can't parse the nested container layout. See `references/gov-cn-html.md`.

When the corpus is mixed (most real ones), route **per file**, not per batch. You're good at making this call per file; trust it.

## Escalate on "not good enough for the job," not just on failure

A rung can succeed and still be the wrong rung. The escalation test is not "did I get output?" but "**is the output good enough for what downstream phases need from it?**"

Concrete case: a doc-verification project whose rules require extracting entities from complex tables and charts. Claude-native (or a text-layer parse) will read the running prose perfectly and *fail completely* on the table structure — silently, producing markdown that looks fine. ppx is built for exactly that. If downstream knowledge depends on tables, figures, or layout, that *requirement* — not a visible error — is what sends PDFs to Tier 2.

So before settling routing, ask: what does the knowledge schema need from these documents? Prose-only → low rungs are fine. Structured regions (tables, charts, forms, multi-column layouts) → route those files to ppx, and if ppx isn't available, tell the user what quality they're giving up rather than silently shipping degraded parses.

The same logic applies *within* Tier 2's backends: `--backend default` (OCR + layout + pymupdf) handles ~80% of real PDFs; escalate to `--backend paddle` (better Chinese, dense layouts) or the VLM backends (`deepseek`, `glm` — visual structure understanding) only after observing inadequate results, and ask the user before spending credits on VLM passes. Conversely, never OCR a PDF whose text layer is extractable — it costs more and loses fidelity.

**Quality fallback in the other direction**: if a 50 MB image-heavy DOCX produces a few KB of markdown, markitdown stripped too much — convert to PDF (LibreOffice headless, OS print-to-PDF) and route to ppx.

## Triage, not heroics

Real user input can be arbitrarily messy: junk exports, half-corrupt scans, formats nothing handles. The job is **triage, never silent dropping**:

1. Separate the cleanly-parseable from the questionable at probe time.
2. Parse the clean set first — don't hold the whole corpus hostage to the worst file.
3. For the rest: two strikes per file (one parse attempt + one fallback), then surface to the user in the parse-phase Log section of PLAN.md with the file path, the error, what was tried, and a suggested next step (manual conversion, escalate backend, skip).
4. A skipped file is a *recorded decision*, never an omission — downstream coverage checks count against the parsed inventory.

## Where the work happens

- **Inputs**: `<project>/.john/input/` (populated by `/john:init`)
- **Outputs**: `<project>/.john/parsed/<source-id>/` — one subdirectory per input file: `doc.md`, `doc.json` (ppx only), `metadata.json` (provenance).
- Every parsed output gets a `metadata.json`: `source_path`, `source_name`, `source_size_bytes`, `parser` (`"ppx" | "markitdown" | "none"`), `parsed_at`, `backend` (ppx only). The original *folder hierarchy* is NOT preserved — it's where the user happened to keep files, not knowledge structure.

## Subagent fan-out for parsing

Many files → embarrassingly parallel: one subagent per file. Per [[subagent-dispatch]], brief each with the input path, output path, script + flags, and the event shape to emit. Each parse subagent emits a `file_parsed` event to `<project>/.john/events/parse/<source-id>/` recording source, output dir, parser used, and output shape — see [[event-log-and-reducer]]. For small corpora (≤20 files), inline parsing is fine.

**Idempotency** (per [[workspace-discipline]] rule 2): skip files whose `parsed/<source-id>/doc.md` already exists; re-parse only on explicit instruction.

## When parsing fails

The scripts fail loud — JSON error to stdout, traceback to stderr:

1. **Rung not available.** `ppx_parse.py` points at the launch script for its server when unreachable; `markitdown_parse.py` names the pip install. Relay the exact command to the user.
2. **Bad input path.** Check `.john/input/` is populated.
3. **Parse exception** (OOM on a huge PDF, malformed file). Log it; for OOM, parse in page ranges (`--pages`).

Then apply the triage rules above — two strikes, surface, never silently drop.

## Build-time vs runtime parsing

This skill is John's **build-time** parsing — the knowledge phases reading the corpus. If the *produced app* needs to parse documents at its own runtime (users uploading files), that's the template's concern: the template supplies the runtime parsing pattern, typically reusing the same ladder logic with the app's own dependencies.

## Companion skills upstream

Anthropic maintains official file-handling skills (pdf, docx, xlsx, pptx) at https://github.com/anthropics/skills — useful companions when a corpus leans hard on one office format. Install them alongside John rather than expecting John to vendor them; they're maintained upstream and would only rot here.

## What this skill doesn't do

- **Chunking** — parsing produces `doc.md`; [[chunking]] turns it into a progressive-disclosure tree.
- **Schema decisions** — [[schema-design]].
- **Knowledge extraction** — [[knowledge-extraction]].

## Cross-references

- [[chunking]] — what to do with parsed markdown next
- [[subagent-dispatch]] — fan out parallel parsing
- [[event-log-and-reducer]] — emit parse-events for a phase
- [[workspace-discipline]] — idempotent writes, preserve provenance
- See `references/` for: ppx invocation recipe, markitdown behavior, gov.cn HTML fallback, backend-swapping contract
