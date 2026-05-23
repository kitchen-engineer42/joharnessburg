---
name: platform-parser
description: When parsing input documents (PDF, DOCX, HTML, scans) for a produced app or during the 2skills `parsing` phase in a platform-integrated project, use this skill. Triggers on "parse PDF", "parse DOCX", "PDF_PARSE_SERVER", "extract text", "OCR", or any decision about which parsing tool to reach for. Teaches the team's standard parser preference order (PDF_PARSE_SERVER → pypdf → vision fallback) and when to deviate.
metadata:
  triggers:
    - parse pdf
    - parse docx
    - pdf parse server
    - extract text from document
    - ocr
    - vision parsing
    - which parser
---

# platform-parser

The team has converged on a clear parser preference order for documents. Use it; don't ad-hoc pick a parser per project.

## The preference order

1. **`PDF_PARSE_SERVER`** (the team's in-house parser via `parse_pdf_util.py`) — first try. Handles native-PDF text extraction, layout-aware chunking, table extraction. Best quality for our docs (Chinese regulations, textbooks, financial filings).
2. **`pypdf` / `markitdown`** — fallback for simple PDFs when `PDF_PARSE_SERVER` is unavailable (dev mode, external customers without platform access), and for non-PDF formats (DOCX, HTML, basic Markdown).
3. **Vision-based OCR** — last resort. Use for scans, image-only PDFs, hand-written documents where layout/text extraction fails. Costs credits; surface to the user before invoking.

## What to do in this project

1. **Inspect input first.** Is it a native PDF (text-extractable) or a scan? `pdfinfo` or a quick read of the first KB tells you. If text-extractable → tier 1 or 2. If scan → tier 3.
2. **Default to `PDF_PARSE_SERVER`** for PDFs in platform-integrated projects. Call via `parse_pdf_util.py` (in `to-skills-backend`); don't re-implement the HTTP client.
3. **Use the John toolkit** `ppx_parse.py` (thin HTTP client to the local ppx server in v0.1.7+; previously a direct ppx import) when you want layout-aware parsing without round-tripping through the team's production parse server. Same quality. The local ppx server is in `/Users/mac/Desktop/john/local_clients/ppx/`; launch with its `scripts/start.sh`. Swapping to the team's production PDF_PARSE_SERVER = change `JOHN_PPX_CLIENT_URL` and restart Claude.
4. **Use `markitdown_parse.py`** for DOCX/HTML/non-PDF formats. Faster than spinning up the parse server when the format isn't PDF.
5. **Document your choice** in PLAN.md's Log so future-Claude knows which parser produced the parsed artifacts.

## What you should NOT do

- Don't write a custom parser for a format the team already handles. If you find yourself reaching for `pdfplumber`-and-some-glue, you're off the path.
- Don't OCR a PDF whose text is extractable. Wastes credits, loses fidelity.
- Don't mix parsers in one project without a clear reason. Consistency matters for downstream chunking + extraction.
- Don't truncate or lose page metadata. Even if the parser gives you flat text, preserve page numbers so the extractor can cite sources accurately.

See `references/source.md` for source paths + when each parser shines.
