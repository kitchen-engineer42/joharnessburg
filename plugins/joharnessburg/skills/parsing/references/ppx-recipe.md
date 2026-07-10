# ppx-recipe — concrete invocation

`ppx_parse.py` is an HTTP client for a ppx parse server (reachable at `$JOHN_PPX_CLIENT_URL`). This note captures the practical knobs.

## Minimum invocation

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ppx_parse.py" \
    "<project>/.john/input/<file.pdf>" \
    "<project>/.john/parsed/<source-id>/"
```

That's it for default usage. Backend `default`, OCR `auto`, table `auto`, formula recognition enabled.

## Backend rubric

| Backend | When | Cost |
|---|---|---|
| `default` | Always try first. Local RapidOCR + RapidLayout + pymupdf. | Free, offline |
| `paddle` | Scanned Chinese, dense layouts, default produced garbled text | ~cheapest cloud VLM (SiliconFlow) |
| `deepseek` | Mixed text + heavy tables/figures, layout matters | ~mid cloud VLM |
| `glm` | Last resort for unusual layouts where default+paddle+deepseek all underwhelmed | ~more expensive |

## OCR modes

- `--ocr auto` (default): use embedded text when present per region, OCR otherwise. Right for digital-native PDFs that occasionally have a scanned page.
- `--ocr yes`: force OCR everywhere. Slow but unambiguous for fully-scanned docs.
- `--ocr no`: skip OCR. Only sensible if you know the PDF is digital-native end-to-end.

## Table modes

- `--table auto`: detect bordered/borderless tables and route. Default is fine.
- `--table ybk` / `--table wbk`: force bordered / borderless mode.
- `--table llm`: route table extraction through a VLM. Slow + expensive but best for ambiguous tables.
- `--table no`: skip tables entirely (treat as images). Use when tables aren't meaningful for the project.

## Formula recognition

`--no-formula` skips formula parsing (faster, formulas become images). Useful when the project doesn't care about equations.

## Swapping the backend

Any hosted parse service speaking the same HTTP contract can replace the local ppx client server — point `$JOHN_PPX_CLIENT_URL` at it. The John-equipped agent sees the same script signature; only the backend changes. Don't design around the in-process detail. See `parser-backend-swapping.md`.
