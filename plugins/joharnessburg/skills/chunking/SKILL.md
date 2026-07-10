---
name: chunking
description: Break parsed markdown into a tree of progressively-disclosed chunks for downstream extraction. Use this skill whenever a phase needs to work on per-chunk units, when the user mentions chunking or splitting documents, or when transitioning from parsing to extraction — make sure to chunk before extraction unless the user has explicitly OK'd skipping it. Handles both onion-peeler (one long doc → tree) and onion-wrapper (many short files → assembled tree).
metadata:
  triggers:
    - chunk the docs
    - chunk the corpus
    - split the documents
    - chunking phase
    - prepare for extraction
    - assemble the tree
---

# chunking

Parsed markdown is rarely the right unit for downstream extraction — too big to fit one extractor's context, too coarse to fan out subagents over. Chunking turns parsed output into a **tree of progressively-disclosed pieces** the extraction phase can sweep.

## Where the work happens

- **Inputs**: `<project>/.john/parsed/*/doc.md` (from [[parsing]])
- **Outputs**: `<project>/.john/chunks/<chunk-id>.md` + `<project>/.john/chunks/chunks_index.json` (master map)
- **Each chunk** has YAML frontmatter (chunk_id, parent_id, source_doc, char_count, header_path) + body markdown.

## The onion decision lives in phase-design

The peeler-vs-wrapper-vs-hybrid decision is made at **phase-design time**, not chunking time — see [[phase-design]] for the rubric and the decision criteria. By the time this skill runs, PLAN.md's chunk phase already specifies which mode applies (and for hybrid corpora, the per-section mode). Read PLAN.md's chunk phase; execute what it says.

Brief mode reminders so you don't have to context-switch:

- **Peeler**: long doc → tree of pieces via header hierarchy. Default for textbooks, regulations, long articles.
- **Wrapper**: many short files → assembled tree. Default for corpora arriving as folders of small files.
- **Hybrid**: peel the long ones, wrap the short ones, merge their trees at a shared root.

## The peeler algorithm

1. Read the parsed `doc.md`.
2. Extract the header hierarchy (H1/H2/H3...) with line numbers.
3. Walk top-down, splitting at the highest-level boundary that produces chunks within the token budget. Don't pre-decide a level; let content drive it.
4. If a section is still too large after H1/H2/H3 splits, fall back to **LLM-wedge chunking** (see `references/llm-wedge-chunker.md`): ask an LLM to suggest cut points within the running window, fuzzy-match the suggestions back to the source via Levenshtein, slide forward.
5. Emit each chunk with frontmatter linking parent/source. Build `chunks_index.json` as a tree.

Tunable: `MAX_TOKEN_LENGTH` per chunk. Default ~100K tokens (large; we want bigger chunks where possible — "bigger chunks > smaller chunks. Only chunk when necessary, never over-chunk" per the predecessor's pipeline spec). Drop if the extraction phase struggles.

## The wrapper algorithm

1. Walk the corpus directory tree, classify each leaf file by topic/section/folder.
2. For each leaf, emit a chunk = file content + frontmatter (chunk_id, source_path, kind=leaf).
3. For each inner node (folder, topic), emit a chunk = subagent-written one-paragraph summary of its children + frontmatter (chunk_id, kind=inner, children=[...]).
4. Build `chunks_index.json` mirroring the natural hierarchy (folders → topics → leaves).

Wrapper is more LLM-heavy than peeler because the inner-node summaries need to be written. Worth it for corpora where the file-level boundaries are meaningful (otherwise you're just paying to read).

**Grouping signals for wrapper** — order of preference when they conflict:

1. **Explicit metadata** in file frontmatter (e.g., `topic: X`, `tags: [...]`). When present, this is ground truth.
2. **Folder hierarchy**. Usually meaningful; the user organized the corpus this way for a reason.
3. **File name conventions** (e.g., `2025-Q3-...`, `lessons-mathlab-...`). Use when other signals are absent.
4. **LLM-judged topic clustering** as last resort, when the above are unavailable or inconsistent.

When signals conflict (folder says X, frontmatter says Y), trust frontmatter — it was set by the author intentionally. Log conflicts in the chunk phase's events for later review.

## Chunk-size and downstream coupling

Chunk size is downstream-driven. Smaller chunks → more subagents in the extraction phase (more parallelism, more orchestration overhead). Larger chunks → each subagent has more context but the fan-out is narrower. Defer the exact budget choice to the corpus shape after a quick survey:

- **Many short well-bounded sections** (e.g., a regulation with numbered articles): chunk per article. Small chunks (few KB each), many of them.
- **Long flowing prose** (e.g., a textbook chapter): chunk by H2/H3 with budgets in the 20-50K token range. Fewer, bigger chunks.
- **Mixed**: chunk per natural boundary, accept that chunks will vary in size.

## When chunking is NOT needed

- Single-document corpora where the doc already fits one context.
- Pre-structured input (e.g., a database export that arrives as one entry per row).
- Some "wide tunnel" projects where the user wants the John-equipped agent to read the entire corpus in one pass — rare, expensive, but valid.

If you skip chunking, note it in PLAN.md's chunk phase and proceed to [[knowledge-extraction]] with the raw parsed output.

## Progressive disclosure outside the tree

Each chunk is itself eventually a candidate for further progressive disclosure when knowledge is extracted from it. See [[knowledge-rewrite]] — header + body split happens at the entry level, not just the chunk level. Same metaphor, different layer.

## Cross-references

- [[parsing]] — where parsed markdown comes from
- [[schema-design]] — chunk size is informed by what schema we're extracting toward
- [[knowledge-extraction]] — the next phase, which sweeps chunks
- [[phase-design]] — the onion-peeler / wrapper decision rubric (this skill is the *how*)
- See `references/` for: onion-peeler design, onion-wrapper assembly, LLM-wedge fallback
