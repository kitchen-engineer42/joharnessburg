---
name: knowledge-rewrite
description: Turn the raw event-log entries from extraction into clean, cross-linked, deduplicated knowledge ready for packaging. Use after the extract phase has produced events and canonical state, when the user mentions rewriting or polishing, or when [[ralph-loop]] advances into the rewrite phase. Header+body progressive disclosure, two-tier dedup, and cross-link enrichment are the three jobs.
metadata:
  triggers:
    - rewrite the knowledge
    - polish entries
    - cross-link entries
    - deduplicate
    - rewrite phase
    - progressive disclosure
    - finalize the knowledge
---

# knowledge-rewrite

Extraction is fan-out; rewrite is consolidation. The raw event log from [[knowledge-extraction]] has redundancies, near-duplicates, missing cross-references, inconsistent terminology, and entries that don't yet have the header+body split. Rewrite fixes all of that and produces the entries [[packaging]] will emit.

## Three jobs

1. **Header + body progressive disclosure** — every entry gets a one-line header (description + classification + cross-refs) and a full body. The header is what loads cheap; the body is what loads on demand.
2. **Cross-linking** — entries reference each other; shared vocabulary lives in a glossary; relationships are typed where the schema supports it.
3. **Dedup** — two-tier (cheap quick-scan + expensive deep-read) to remove duplicates without false positives or false negatives.

## Where the work happens

- **Inputs**: `<project>/.john/checkpoints/extract/state.json` (from [[event-log-and-reducer]])
- **Working state**: `<project>/.john/knowledge/<entry-id>/{header.md, body.md}` (per-entry directory)
- **Outputs**: cleaned knowledge directory ready for [[packaging]]; an updated `<project>/.john/checkpoints/rewrite/state.json` recording what was merged, dropped, or cross-linked.

## Header + body — what goes where

**Why this matters at scale.** At 1000+ entries, loading all bodies into a context consumes 2M+ tokens — impossible. Loading all *headers* is more like 4K tokens — easy. The header+body split is what makes large knowledge bases work at all; it's not an optimization, it's the only way. Per spec §3a, this design is one of the strengths of the current pipeline worth preserving universally.

**Header** is the entry's "first impression." Pinned in indexes, included in cross-link contexts, cheap to load. Includes:

- One-line description (what this entry says in 20 words or less)
- Classification (e.g., "factual" / "relational" / "skill" — depends on schema)
- Cross-refs (`related_to`, `depends_on`, etc., per schema)
- Source pointer (chunk_id or source_ref)

**Body** is the entry's full content. Loaded when the entry is actually consumed (by extraction subagents in a later phase, by the runtime, by Claude reading the deliverable). Includes:

- Full claim / rule / story / etc.
- Citations + verbatim quotes from the source
- Detailed elaboration (multi-paragraph if needed)
- Optional: examples, edge cases, glossary expansions

The split is universal — applies regardless of format-of-knowledge. Facts, rules, stories, skills, all get header+body.

## Cross-linking

The reducer's canonical state has a flat list of entries. Rewrite enriches with relationships:

- **By name match**: entries that mention the same proper noun likely have a connection. Surface the relationship explicitly in both entries' headers (`related_to: [entry-id-1, entry-id-2]`).
- **By topic clustering**: bucketing (per [[event-log-and-reducer]]'s reducer or per the A2O bucketing pattern in `references/two-tier-dedup.md`) groups entries by similarity. Use the buckets to decide who deserves a cross-link.
- **By schema-defined edges**: if the format-of-knowledge has typed relationships (e.g., A2O's `is-a`, `causes`, etc.), populate those explicitly.

Glossary entries deserve special treatment: a single entry per term, with all uses cross-linked back. KC's pattern (see `references/cross-linking.md`).

## Two-tier dedup

Three-fold reason dedup is hard:

1. The same fact extracted from two chunks is genuinely duplicate.
2. A fact and its rephrasing-with-different-context look similar but aren't duplicates.
3. Two entries that look different but describe the same thing in different vocabulary ARE duplicates.

A2O's two-tier dedup handles this without false positives or false negatives at scale:

- **Tier 1 (cheap)**: a small/cheap model (Haiku, or a workerLLM) does a quick-scan over header pairs from the same bucket. Asks: "Are these two entries describing the same thing?" Outputs yes/no/maybe.
- **Tier 2 (expensive)**: for everything in tier-1's "maybe" or "yes" pile, a SOTA model (Claude Sonnet/Opus) does a deep-read over both bodies and decides definitively.

Tier 1 filters out obvious non-duplicates cheaply (the bulk). Tier 2 spends real tokens only on plausible candidates. The ratio matters — typical run: 10,000 pairs through tier 1, 50 through tier 2.

When duplicates are confirmed, the rewrite phase has options:

1. **Merge** — combine the two entries' bodies, keep both sources in `source_chunk_ids`, drop the duplicate ID.
2. **Supersede** — keep one, emit a corrective event marking the other deprecated.
3. **Cross-link** — keep both as distinct but explicitly mark them as "different views of the same X." Use when both add real value (e.g., user-facing vs developer-facing view).

[[workspace-discipline]]'s "append-only events" applies — the dedup decision is itself an event the reducer folds into the rewrite phase's canonical state.

**Warning — corrective events + dedup interaction.** If the corpus already contains corrective events from prior iterations (entry A superseded by entry A-v2), the tier-2 deep-read may find A and A-v2 highly similar and propose a merge. **Don't merge correction chains.** When tier 2 encounters a candidate pair where one is a supersession of the other (check the `supersedes` field), the right action is to drop the older entry from the canonical state and keep the newer one — which is what supersession already does. Do NOT emit a merge that loses the correction history. The audit dimension: any merge decision against a known-superseded entry should be flagged in the rewrite phase Log.

**Bucket weight tuning.** The default weights (TF-IDF 0.2 / Label 0.3 / Vector 0.5) work for general-purpose corpora; they're tunable per project. Signals to retune: if tier-1 quick-scan flags >50% of pairs as "maybe", the vector weight is too high (too aggressive bucketing). If spot-checks find obvious duplicates that tier 1 missed, TF-IDF or Label weight is too low. Templates that handle specific domains (e.g., legal docs with consistent vocabulary) may want to bump TF-IDF higher. Checkpoint the weights used per run so iterations are reproducible.

## When to iterate vs ship

Rewrite is iterative; you might pass over the corpus 2-3 times before things stabilize. After each pass, spot-check:

- Are header descriptions actually useful? (load 5 headers in isolation; can you tell what each entry covers?)
- Are cross-links pointing at the right entries? (manual sampling)
- Did dedup over-merge? (look for entries marked merged that seem distinct)

If the pass produced obvious improvements, do another. If diminishing returns, ship.

## Cross-references

- [[schema-design]] — defines the schema each entry must conform to; dedup and cross-link decisions reference the schema's classification + relationship fields
- [[knowledge-extraction]] — produces the raw events this skill consolidates, including any `schema_observation` events worth reviewing before dedup
- [[event-log-and-reducer]] — append-only model; rewrite emits corrective events
- [[packaging]] — the next phase
- [[workspace-discipline]] — disk is truth; corrective events not in-place edits
- See `references/` for: progressive-disclosure detail, cross-linking patterns, two-tier dedup
