# platform-parser — source team work

Source locations:

- `to-skills-backend/app/pipeline/parse_pdf_util.py` — Python client for `PDF_PARSE_SERVER`. Handles auth, retries, response unpacking. Reuse, don't re-implement.
- `${CLAUDE_PLUGIN_ROOT}/scripts/ppx_parse.py` — John's in-process jyppx wrapper (no server round-trip; same quality on most documents). Good for batch.
- `${CLAUDE_PLUGIN_ROOT}/scripts/markitdown_parse.py` — John's markitdown wrapper for DOCX, HTML, basic Markdown.

Performance notes:
- `PDF_PARSE_SERVER` produces layout-aware structured output (tables preserved, sections detected). Best quality; needs network.
- `ppx_parse.py` produces equivalent structure in-process; no network. Use for batch + dev.
- `markitdown_parse.py` produces flat-text-with-headings. Fast; loses table structure.
- Vision OCR via the LLM proxy ([[platform-llm-proxy]]) costs credits and time; reserve for documents where text extraction fails.

Document inspection commands:
- `pdfinfo <file>` — page count, encryption, text-vs-scan.
- `head -c 200 <file> | hexdump -C` — quick "is this a real PDF" check.

For Chinese documents: all three parsers handle Chinese text correctly, but `PDF_PARSE_SERVER` + `ppx_parse.py` preserve full-width punctuation and CJK column layout better than `markitdown`. Prefer them for regulation/textbook corpora.
