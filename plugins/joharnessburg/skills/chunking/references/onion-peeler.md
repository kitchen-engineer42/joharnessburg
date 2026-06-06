# onion-peeler — the design

The peeler turns one large document into a tree of progressively-disclosed chunks. The name and design come from `onion_peeler.py` in a predecessor pipeline, and was carried forward into a research successor's chunking module.

## The metaphor

Imagine the document as an onion:
- **Outermost layer**: H1 chapter titles + one-sentence summaries. Read this and you know what the doc is about.
- **Middle layers**: H2/H3 sections with their own summaries. Read these for a topic and you know its outline.
- **Core**: the actual paragraph text. Read this when you've decided to dig into a specific piece.

Progressive disclosure means a reader (human or Claude) loads only the layers they need. The chunk tree encodes this: chunks at higher tree depths are summaries; chunks at lower depths are full content.

## Why a tree, not a flat list

Real documents have hierarchical structure. Flattening it loses load-bearing context: an extracted entry from "§5.2 disclosure timing" only makes sense if you know it's under "§5 reporting requirements." The tree preserves the path so any downstream skill can reconstruct context as needed.

## The algorithm in practice

1. **Extract header line numbers**. Walk the markdown for `^#+\s+`, record level + text + line number.
2. **Pick the working split level**. Start with H1; if H1 produces too-big chunks, descend to H2; etc.
3. **Recursive split**. For each chunk over the budget, recursively split at the next-deeper header level. Stop when chunks fit.
4. **LLM-wedge fallback**. If a chunk has no internal headers (long flowing prose), use the wedge fallback — see `llm-wedge-chunker.md` in this directory.
5. **Emit each chunk** with frontmatter: `chunk_id`, `parent_id` (or null for root), `source_doc`, `header_path` (e.g., `["Chapter 5", "§5.2 Disclosure timing"]`), `char_count`.
6. **Build the index** at `chunks_index.json`: a tree representation of chunk_id → parent_id with metadata.

## Tradeoffs

- **Bigger chunks are better when they fit.** Per the predecessor's pipeline spec: *"Bigger chunks > smaller chunks. Only chunk when necessary, never over-chunk."* Don't over-shred just because you can.
- **Header hierarchy is approximate.** Some authors use H3 where they mean H2; some skip levels. The peeler shouldn't dogmatically respect levels — it should respect *what makes sense as a unit*.
- **Splits at semantic boundaries beat splits at token boundaries.** If you have to split mid-flow, mid-paragraph is a code smell; revisit your chunk budget.

## Source

A predecessor pipeline's `onion_peeler.py` held the original Python implementation with the recursive-peel + LLM-wedge logic; a later research iteration made it more modular. The algorithm above is the durable part.
