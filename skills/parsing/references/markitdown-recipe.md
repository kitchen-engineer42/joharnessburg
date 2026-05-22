# markitdown-recipe — when MarkItDown earns its keep

Microsoft's MarkItDown is great for office formats it was designed for, mediocre or risky for everything else.

## Strong cases

- **DOCX**: clean structure, headings, lists, tables, inline images. Output is essentially what you'd want.
- **PPTX**: per-slide markdown with image references. Use for slide decks where speaker notes + visible text both matter.
- **XLSX**: per-sheet markdown tables. Right for small spreadsheets; for huge ones, consider extracting structured data directly instead.
- **HTML**: strips markup, retains structure. Good for clean HTML; can struggle with heavily-styled pages.
- **Plain `.md` and `.txt`**: pass-through (mostly). Cheap insurance for consistency.

## Weak/risky cases

- **PDFs**: MarkItDown will accept them but its output is much weaker than ppx. ALWAYS use `ppx_parse.py` for PDFs.
- **Images with text** (PNG, JPG): MarkItDown has OCR but it's basic. Better to convert image → PDF first, then ppx.
- **EPUB**: weak; jyppx has dedicated EPUB handling that should be preferred when available.
- **Audio/video**: out of scope for John v1. Templates for transcription-driven projects will add their own scripts.

## Invocation

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/markitdown_parse.py" \
    "<project>/.john/input/<file.docx>" \
    "<project>/.john/parsed/<source-id>/"
```

Output: `doc.md` + `metadata.json`. No `doc.json` (MarkItDown emits text, not structured AST).

## When MarkItDown isn't installed

The script fails loud with `pip install markitdown`. If the user is offline or doesn't have pip, you have three options:
1. Tell them to install (preferred).
2. Suggest they convert the document manually (e.g., `Save As → PDF` then use ppx).
3. Note the unparsed input in the parse phase Log and proceed with parsed files only.

## Source

MarkItDown is at https://github.com/microsoft/markitdown. Pure Python, MIT-licensed, no system deps. Microsoft maintains it.
