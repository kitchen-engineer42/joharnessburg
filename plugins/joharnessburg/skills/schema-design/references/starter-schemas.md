# Starter schemas per knowledge format

**These are illustrations, not a menu to pick from and not a spec to autocomplete.** Wide tunnel: design the schema for *this* corpus. The shapes below are here only to show the *kind* of fields each format tends to want — read them, then invent what the project actually needs.

A project can have **multiple formats** (e.g. facts + skills + glossary, or storylines + character profiles); they don't have to share a schema.

- **Facts**: `{id, claim, sources[], confidence, related_facts[]}`. Header (one-liner) + body (full elaboration).
- **Rules**: `{id, source_ref, trigger, judgment, decision_tree, glossary_refs[]}`. From KC's design — see `kc-rule-schema.md`.
- **Skills**: SKILL.md frontmatter (name, description) + body + optional `references/`/`scripts/`/`assets/` subdirs. See [[packaging]].
- **Wiki entries**: `{id, title, body, links[], categories[]}`. Plain-old wiki.
- **Storylines**: `{id, narrative_arc, characters[], scenes[], branches[]}`. The mystery-detective-game's GameData type is one concrete shape.
- **Screenplays**: `{scene_id, location, time, dialogue[], action[]}`.
- **Graphs**: nodes `{id, type, attrs}` + edges `{from, to, type, attrs}`.

Whatever you choose, keep **header + body progressive disclosure** (a cheap one-line header pinned in retrieval; full content loaded on demand) — that layer is universal regardless of schema.
