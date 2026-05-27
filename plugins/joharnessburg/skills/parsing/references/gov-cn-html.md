# Parsing Chinese government regulation HTML pages

gov.cn-style pages wrap regulation text in a nested container (`#UCAP-CONTENT`, `.pages_content`, or `.TRS_Editor`) surrounded by font-resizer widgets ("字号"), nav, and footer cruft. MarkItDown returns garbled or empty output on these. `parse_govcn_html.py` is a narrow purpose-built fallback for this page family.

## When to use

Route to `parse_govcn_html.py` when:
- The input is HTML from `*.gov.cn`, `*.npc.gov.cn`, `*.csrc.gov.cn`, `*.cbirc.gov.cn`, or similar Chinese regulator portals.
- A quick inspection of the HTML shows `<div id="UCAP-CONTENT">`, `<div class="pages_content">`, or `<div class="TRS_Editor">` as the article container.
- markitdown produced output that's clearly broken (empty, just nav text, or missing the law body).

For general HTML (blog posts, ordinary web pages), stay with `markitdown_parse.py`.

## Invocation

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/parse_govcn_html.py" \
    "<project>/.john/input/<file.html>" \
    "<project>/.john/parsed/<source-id>/"
```

Output: `doc.md` (chapters → `##`, articles → `###`, prose preserved) + `metadata.json` with `chapter_count`, `article_count`, `char_count`, and which container attrs matched.

## Scope (what it handles)

- Locates the article container by id/class match.
- Strips script/style.
- Drops font-resizer + nav noise lines (anchor text matching 字号, 大|中|小, 返回, 打印, 分享).
- Splits text on Chinese chapter / article markers (`第一章`, `第十二条`, ...) and emits H2/H3 headings.
- Decodes UTF-8 with GBK fallback (some gov sites still ship GBK encoded HTML).

## Scope (what it does NOT handle)

- Tables: text content captured, but `<table>` structure lost. For table-heavy regulations, route to ppx via PDF conversion.
- Images: ignored.
- Embedded media: ignored.
- Non-`第X条`-numbered laws or articles in other languages: chapter/article detection won't fire; you'll get a flat prose dump. Use markitdown_parse.py for those.

## Failure modes

- "No recognized gov.cn article container" → the HTML doesn't have any of the three known container markers. Either the source is non-gov.cn or uses a different layout; fall back to markitdown.
- "Could not decode as UTF-8 or GBK" → unusual encoding. Use `iconv` to recode the file before parsing.
- Empty body → container found but no readable text inside (e.g., heavy JavaScript-rendered content). Convert the page to PDF first (browser → print to PDF), then route to ppx.
