# llm-wedge-chunker — the LLM-wedge fallback

When a document has no header hierarchy to peel along (long flowing prose, a single huge paragraph, transcription output), the header-based algorithm can't find natural cut points. A research predecessor's LLM chunker solves this with a wedge-based fallback.

## The idea

A "wedge" is a small text-window pair: the last N characters before a proposed cut and the first N characters after. The LLM looks at a rolling window of the source and suggests where to cut, returning a wedge (text-before + text-after + suggested-title). The chunker then fuzzy-matches the suggested cut point back to the source using Levenshtein distance — because the LLM may paraphrase rather than echo verbatim, fuzzy-match is more reliable than exact match.

## The algorithm

1. **Open a rolling window** at the start of the chunk-that-needs-splitting. Window size matches the LLM's effective context (~28K tokens is a good budget).
2. **Ask the LLM**: *"Suggest the next natural cut point in this text. Return text-before (30 chars), text-after (30 chars), and a suggested heading for what comes after."*
3. **Fuzzy-match the wedge** back to the source. Use Levenshtein distance to find the position with the lowest edit distance to the suggested text-before. That's the cut.
4. **Emit the chunk** before the cut + frontmatter with the suggested heading as `header_path`.
5. **Advance** the window past the cut, repeat.

## Why fuzzy-match

The LLM paraphrases. If it suggests text-before = "...quarterly report must include..." but the source actually says "...the quarterly report shall include...", exact match fails. Levenshtein distance ≤ some threshold (maybe 5 edits per 30 chars) catches the intent without requiring verbatim echo.

## Why wedges, not absolute positions

LLMs are bad at counting and at absolute positions. Asking "what character should I cut at?" produces nonsense. Asking "what text comes right before the cut and right after?" produces usable answers because the model is reasoning about content, not arithmetic.

## When to use vs not

- **Use** when peeler hit a chunk with no internal headers AND it's still over the chunk budget.
- **Don't use** when peeler hit a clean H2/H3/H4 boundary it can use — that's free; LLM-wedge costs API tokens.
- **Don't use** for chunks that fit the budget without splitting, even if there's no header structure. Bigger chunks > smaller chunks.

## Source

A research predecessor's LLM chunker implemented this. The Levenshtein library and rolling-window logic are vanilla; the prompt + wedge schema are the design contribution.
