# two-tier-dedup — a research predecessor's pattern, generalized

Naive dedup compares every entry to every other entry. At 1000 entries, that's 500,000 comparisons; at 10,000, it's 50,000,000. Not feasible. Two-tier dedup is the structure that makes dedup tractable at scale (inherited from a research predecessor).

## Stage 1 — bucketing (free, deterministic)

Group entries by similarity using a cheap composite signal:

- **TF-IDF overlap** on header text — weight 0.2.
- **Label Jaccard** on schema-classification fields — weight 0.3.
- **Vector embedding cosine similarity** on body — weight 0.5.

Composite score per pair; threshold (typically ~0.4) puts pairs in the same bucket. Pairs in different buckets aren't compared.

At 1000 entries, bucketing reduces 500,000 pairs to maybe 5,000 same-bucket pairs (1% of the naive count, or less).

Bucketing is **deterministic** (same input → same buckets). The weights are tunable per project — for a domain with consistent vocabulary, bump TF-IDF; for a domain with synonyms, lean on embeddings.

## Stage 2 — quick-scan (cheap LLM)

For each same-bucket pair, a cheap LLM (Haiku, or a workerLLM) reads both headers and answers: *"Are these two entries describing the same thing? yes / no / maybe."*

Cheap because:

- Only header text, not bodies.
- Cheap model.
- Binary-with-maybe classifier prompt, not a creative task.

Most pairs come back as "no" (similar topic, different specifics). A few come back as "yes" (clearly duplicates). A few come back as "maybe" (borderline; needs deeper read).

Tier 2's "no" pile is dropped without further consideration.

## Stage 3 — deep-read (SOTA LLM)

For the "yes" and "maybe" pile, a strong available model does a deep-read over both bodies:

- Are the bodies actually describing the same fact / rule / story / etc.?
- If yes, what's the merge action? (combine bodies, keep both sources; supersede one with the other; cross-link them as distinct views.)
- If no, why did quick-scan flag them? (Useful signal for tuning the bucketing weights.)

Deep-read is the expensive step; it spends real tokens on a small fraction of original pairs (typically <0.1%). Worth it because the alternatives are accepting false dedup (real merges missed) or false positives (entries merged that shouldn't be).

## Why two tiers, not one

- **One cheap tier alone**: catches obvious dupes; misses subtle ones; sometimes wrongly merges entries that LOOK alike but aren't.
- **One expensive tier alone**: catches everything but costs N² API calls at scale. Infeasible.
- **Two tiers**: cheap filter narrows to a manageable candidate set; expensive judge handles the candidates accurately.

## The actions tier 2 emits

For each confirmed duplicate, emit a corrective event to the rewrite event log:

```json
{
  "event_type": "entry_merged",
  "timestamp": "...",
  "payload": {
    "kept_id": "<surviving entry>",
    "merged_ids": ["<dup-1>", "<dup-2>", ...],
    "merged_sources": [...],
    "reason": "<one-liner>"
  }
}
```

Or `entry_superseded` (one supersedes another), or `entries_cross_linked` (two stay distinct but with explicit cross-refs).

The rewrite phase's reducer folds these events into the canonical knowledge state.

## When to skip dedup

- Small projects (<50 entries) — dedup overhead exceeds value. Spot-check manually.
- Highly structured corpora (e.g., a database export) where duplicates are pre-filtered.
- Projects where duplicates are intentional (e.g., multi-source corroboration: same fact from two sources is a *feature*, not a bug).

## Source

- A research predecessor implemented this pattern (bucketing + dedup postprocessors) with concrete numbers.
- The pattern's lineage: standard information-retrieval bucketing, adapted for LLM-driven decision-making.
