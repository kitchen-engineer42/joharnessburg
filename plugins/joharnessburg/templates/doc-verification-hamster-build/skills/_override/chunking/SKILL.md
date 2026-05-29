---
name: chunking
description: Break parsed markdown into a tree of progressively-disclosed chunks. For doc-verification, prefer the statute-hierarchy mode (Chapter → Section → Article) when the corpus is regulation-shaped; fall back to John core's onion-peeler / wrapper when not. Use this skill whenever a phase needs per-chunk units, when the user mentions chunking or splitting, when transitioning from parsing to extraction, or when the rule corpus + samples need to be prepared for Phase 2 (extract) and Phase 4 (test).
metadata:
  triggers:
    - chunk the docs
    - chunk the corpus
    - chunk the rules
    - chunk the samples
    - split the documents
    - chunking phase
    - prepare for extraction
    - prepare for rule extraction
    - assemble the tree
    - article chunks
    - chapter chunks
---

# chunking (doc-verification override)

Parsed markdown is rarely the right unit for downstream rule extraction or rule testing. Chunking turns parsed output into a **tree of progressively-disclosed pieces** the rule-extraction phase can sweep and the rule-testing phase can match against.

This override adds a third chunking mode specialized for regulation corpora: **statute-hierarchy** (Chapter → Section → Article). It keeps John core's onion-peeler and onion-wrapper as fallbacks. The statute-hierarchy mode is *strongly preferred* whenever the rule corpus exhibits statute-like structure (most do).

## Where the work happens

- **Inputs**: `<project>/.john/parsed/*/doc.md` (from [[parsing]]) for both the rule corpus AND sample docs / production docs
- **Outputs**: `<project>/.john/chunks/<chunk-id>.md` + `<project>/.john/chunks/chunks_index.json` (master map)
- **Each chunk** has YAML frontmatter (chunk_id, parent_id, source_doc, char_count, header_path, **chapter_id**, **article_id** when applicable) + body markdown.

`chapter_id` and `article_id` are critical: they become the `source_chunk_ids`, `chapter_id`, `article_id` provenance fields in extracted rules (see overridden [[schema-design]]).

## The three modes

### Statute-hierarchy mode (preferred for rule corpora)

Most regulations are structured as Chapter → Section → Article. The pattern repeats across jurisdictions:

- **Chinese**: 第一章 (Chapter 1) → 第一节 (Section 1) → 第一条 (Article 1)
- **English**: Chapter 1 / Title 1 / Part 1 → Section 1 / Subpart A → Article 1 / §1
- **Numbered**: 1 → 1.1 → 1.1.1
- **US Code style**: Title 12 § 1001 → (a) → (1)

Detect the pattern by scanning the first N parsed lines for repeated statute-marker tokens. Patterns to look for (extend as needed):

```
# Chinese
第[一二三四五六七八九十百千零〇0-9]+章   # chapter
第[一二三四五六七八九十百千零〇0-9]+节   # section
第[一二三四五六七八九十百千零〇0-9]+条   # article

# English
^(Chapter|Title|Part)\s+\d+              # chapter
^(Section|Subpart)\s+\S+                 # section
^(Article|§)\s*\d+                       # article
```

Once detected, the algorithm:

1. Tag every chapter / section / article marker with its location (line number, marker string, level).
2. Build the hierarchy tree. Each leaf is a single article (or sub-article subdivision); inner nodes are chapters / sections.
3. **Emit each ARTICLE as its own chunk** by default — articles are typically rule-atomic units. Chunk body = the article's full text. Frontmatter includes `chapter_id`, `article_id`, `header_path`.
4. Emit inner-node chunks (chapter, section) as well, with body = section/chapter intro text + list of contained article chunk_ids — these are useful for the rule-extraction subagent to see context when needed.
5. If a single article is > MAX_TOKEN_LENGTH (default 4000 tokens for rule corpora — smaller than John core's 100K because articles are usually short and we want one-article-per-extractor-subagent), fall back to header-based or LLM-wedge sub-chunking within the article.

**Token budget for regulation chunks**: 4-8K tokens per article-chunk by default. Drop if extraction struggles; raise if the corpus has long articles and extraction handles the size.

**Token budget for doc-under-test chunks**: 2-4K tokens per chapter/section chunk by default. Doc-under-test chunking uses the regulation's Chapter→Section pattern as a *scope hint* — chunks that match the regulation's chapter categories (disclosure / risk / fees) are tagged with `applicable_scope: [<category>]` for the runtime's rule-classification step.

### Onion-peeler (John-core fallback)

When the rule corpus doesn't fit statute-hierarchy (e.g., a flowing policy document with H1/H2/H3 but no article markers), fall back to John core's onion-peeler:

1. Read the parsed `doc.md`.
2. Extract the header hierarchy with line numbers.
3. Walk top-down, splitting at the highest-level boundary within the token budget.
4. If a section is too large, fall back to **LLM-wedge chunking** (see `references/a2o-wedge-chunker.md`).
5. Emit with frontmatter linking parent/source.

Same algorithm as core; use the standard 100K token budget when running peeler (regulations without article structure are typically smaller anyway).

### Onion-wrapper (for corpus arriving as many small files)

When the rule corpus is a folder of small files (e.g., one regulation per file), fall back to John core's onion-wrapper:

1. Walk the directory tree; classify each leaf.
2. Each leaf → chunk = file content + frontmatter.
3. Each inner node → chunk = LLM-written summary of children.
4. Build `chunks_index.json` mirroring the hierarchy.

Grouping signals (preference order, per core): metadata > folder > filename > LLM clustering.

### Hybrid

A rule corpus may have a long, article-structured central regulation + a sidecar folder of short amendment notes. Apply statute-hierarchy to the central reg + wrapper to the sidecar; merge their trees at a shared root.

## The mode decision

Made at **phase-design time** (per [[phase-design]]), recorded in PLAN.md's chunk phase, executed here. By default this template's `plan_md_template.md` declares **statute-hierarchy** for the rule corpus + **header-driven peeler** for doc-under-test / sample docs (since sample docs typically have report-style chapter structure, not statute markers).

When you start chunking, read PLAN.md's chunk phase first; if it specifies a mode, use it. If the phase says "statute-hierarchy with header-peeler fallback" (the template default), try statute detection; fall through if it fails.

## Chunk-size and downstream coupling

Chunk size for rule corpora is **driven by Phase 2's per-chunk subagent fan-out**:

- Article-sized chunks (typically 200-2000 tokens) → many subagents, each extracting 0-3 rules → high parallelism.
- Section-sized chunks (typically 2-8K tokens) → fewer subagents, each extracting 5-15 rules → less parallelism, deeper context per agent.

Default: article-sized. Switch to section-sized if (a) articles are too tiny to give meaningful context (< 100 tokens), or (b) rules systematically span articles within a section.

Doc-under-test chunks size for **runtime application**, not build-time extraction. The runtime applies each rule to chunks matching its `applicable_scope`. Chunks too large → wasted LLM tokens on irrelevant content. Chunks too small → loss of context the rule needs. 2-4K per section/chapter is the sweet spot from kc_cli's experience.

## Provenance — preserving the citation trail

Every chunk's frontmatter MUST include:

- `chunk_id` — unique within the project
- `source_doc` — path to the parsed source
- `header_path` — list of ancestor headers/markers (for navigation)
- `chapter_id` + `article_id` — when statute-hierarchy mode is active

When [[rule-extraction]] emits a `rule_extracted` event, it copies these into the rule's `source_chunk_ids`, `chapter_id`, `article_id` fields. The runtime later surfaces these in violation reports so an auditor can navigate from "rule R042 fired on doc D's section 3" back to the regulation's Chapter 3 Article 20.

Lose provenance here and the entire pipeline loses citation traceability. Don't drop the IDs.

## When chunking is NOT needed

- A single-file rule corpus < 100K tokens AND a single doc-under-test < 100K tokens → can skip chunking, pass parsed output directly to extraction. Rare for real regulation projects; common for demos.
- A pre-structured input (e.g., a JSON dump of pre-atomized rules) → skip chunking + skip rule-extraction; ingest directly into `.john/knowledge/`.

If you skip chunking, note it explicitly in PLAN.md's chunk phase + Log section, and proceed to [[rule-extraction]] (or skip it too if rules arrive pre-atomized) with the raw parsed output.

## Progressive disclosure outside the tree

Each chunk is eventually a candidate for further progressive disclosure when rules are extracted from it. See [[knowledge-rewrite]] — header + body split happens at the rule level, not just the chunk level. Same metaphor, different layer.

## Cross-references

- [[parsing]] — where parsed markdown comes from
- [[schema-design]] (overridden) — rule schema fields populated from chunk metadata
- [[rule-extraction]] — per-chunk subagent fan-out target
- [[phase-design]] — where the mode decision lives
- [[knowledge-rewrite]] — rule-level header+body split
- See `references/` for: onion-peeler design, onion-wrapper assembly, A2O wedge fallback (from John core, still apply when statute-hierarchy isn't the right mode)
