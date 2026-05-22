# cross-linking — making entries useful together

Single entries are individually useful. Cross-linked entries are collectively useful — a reader can navigate from one to related material, and the runtime can pull a coherent set of entries when one is invoked.

## What to cross-link

Three kinds of links matter:

1. **Same-entity links**: two entries that talk about the same entity (a person, a regulation, a concept). Surface in both entries' headers: `mentions: [entity-id]` or `references: [entity-id]`.
2. **Schema-typed links**: relationships the format-of-knowledge defines explicitly. A2O has 13 types (`is-a`, `has-a`, `causes`, etc.). KC's rules have `depends_on` and `glossary_refs`. Use the schema's vocabulary, not a free-form string.
3. **Glossary cross-links**: when an entry uses a term that's defined in the glossary, link to the glossary entry. Bidirectional — the glossary entry should also list which entries use the term.

## How to populate cross-links

Three signals, ordered by reliability:

- **Bucket co-occurrence**: the dedup phase's bucketing (`two-tier-dedup.md`) groups similar entries. Same bucket → strong cross-link candidate.
- **Name match**: entries that mention the same proper noun → cross-link the entries that *aren't* about that noun back to the entry that *is* (the canonical entry).
- **Explicit reference**: an entry's source quote names another concept defined elsewhere → cross-link.

Don't over-link. An entry with 30 cross-refs is noise. Aim for ~3-7 cross-refs per entry, the most load-bearing ones. The rest is body content if it matters.

## Glossary as a shared vocabulary

KC's pattern: a single `glossary.json` (or per-entry glossary files) per project. Each glossary entry is its own object with header+body:

```
glossary/<term-slug>/
├── header.md   # term + definition + classification
└── body.md     # extended definition, examples, related-terms, used-by entries
```

When an entry uses a glossary term, it cross-links to the glossary entry. When the glossary entry is loaded, the reader (or runtime) sees which entries use the term and can navigate to them.

Glossary is especially valuable when:

- The project has a lot of jargon or domain-specific terms.
- Multiple entries use the same term with the same meaning — define once, reference everywhere.
- The runtime needs to define-on-hover (e.g., a wiki app, a verifier with explainer text).

## What cross-linking is NOT

- It's not a guarantee of correctness. Cross-links can be wrong, misleading, or stale. They're a navigation aid, not ground truth.
- It's not a substitute for body content. If two entries truly need to be read together to be understood, they probably should be merged (or one supersedes the other).

## Source

- A2O's `LabelTree` and `RelationType` define typed relationships and a hierarchical taxonomy on the dev machine.
- KC's rule files reference each other via `related_rules` and `glossary_refs`.
- Mystery-detective-game's GameData type uses cross-references heavily for character-to-clue-to-scene navigation.
