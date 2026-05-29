# onion-wrapper — the reversed operation

Peeler disassembles a long doc into a tree. Wrapper assembles many small files into a tree. Same destination shape, opposite starting point.

## When to use

The corpus arrives as one of:

- A folder full of short files (memos, drafts, posts, snippets) where each file is one logical unit.
- A nested folder hierarchy where the folder structure carries domain meaning (e.g., `topic-A/subtopic-1.md`, `topic-A/subtopic-2.md`, `topic-B/...`).
- A set of files from different sources that you want to group into a coherent tree for downstream extraction.

If the user's `<project>/.john/input/` looks like this, wrapper is the natural mode. Don't try to peel — there's nothing to peel; the files are already at chunk-leaf size.

## The algorithm

1. **Walk the corpus tree.** Identify natural groupings (folder structure, file naming conventions, frontmatter metadata that signals topic).
2. **Leaf chunks first.** For each file, emit a chunk = file content + frontmatter (chunk_id, source_path, kind=leaf, char_count).
3. **Write inner-node summaries.** For each grouping (folder, topic cluster), have a subagent read N leaves at a time and produce a one-paragraph summary. Emit that as an inner-node chunk with frontmatter (chunk_id, kind=inner, children=[<leaf ids>]).
4. **Build the index** at `chunks_index.json` mirroring the assembled hierarchy.

## Why summarize inner nodes

Progressive disclosure works the same as peeler: a reader loading "topic-A overview" should get a one-paragraph summary, not 50 leaf files concatenated. The inner-node summaries are the "outer layers" of the assembled onion.

## Cost consideration

Wrapper is LLM-heavier than peeler because of the inner-node summaries. For corpora with 500 small files and 50 groupings, you're paying for 50 summarization calls. Use cheap models (Haiku, or a workerLLM per template) — these summaries don't need SOTA reasoning, just decent compression.

## When the corpus is mixed (peeler + wrapper)

Real-world projects often have both:
- A long master document (use peeler).
- A folder of short supporting docs (use wrapper).

Build each tree separately, then merge by adding a shared root with both subtrees as children. Update `chunks_index.json` to reflect the merged tree.

## Source

There's no single canonical implementation in our prior projects. The motivating case: when the input is a large number of short files across several layers of folders, the job should be "reversed" into an onion-wrapper. The pattern is documented and John ships it as a skill, not a script. Templates that handle wrapper-shaped corpora may ship their own helper scripts.
