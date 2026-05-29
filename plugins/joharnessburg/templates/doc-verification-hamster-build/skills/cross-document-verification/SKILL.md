---
name: cross-document-verification
description: Identify and verify rules whose verdict depends on facts spanning MULTIPLE documents (e.g., consistency between a prospectus + periodic report, or product info disclosed differently across two filings). Use this skill in Phase 5 after per-doc Phase 4 testing, or whenever the user asks about cross-doc rules / consistency rules. Cross-doc rules need different sample setup (folder-per-sample), different check signatures (dict-of-docs not single-doc), and different testing budgets. Skip Phase 5 if the corpus surfaces no cross-doc rules — log "no cross-doc rules" and move on.
metadata:
  triggers:
    - cross document
    - cross-document
    - cross doc rule
    - cross-doc verification
    - multi-document rule
    - consistency rule
    - phase 5 cross doc
    - rule spans documents
---

# cross-document-verification

Some rules can't be verified by looking at one doc-under-test alone. They need facts from multiple documents to produce a verdict. Common examples:

- **Consistency rules**: "The product type disclosed in the quarterly report must match the product type in the original prospectus." Needs both docs.
- **Continuity rules**: "Q2's opening balance must equal Q1's closing balance." Needs both quarters.
- **Triangulation rules**: "Disclosed risk profile in the marketing material must align with the risk assessment in the latest filing." Two docs, possibly different types.
- **Series rules**: "If the fund has more than 4 quarterly reports without an annual report, the late annual report is a violation." A series of docs over time.

Phase 5 runs after Phase 4 (per-doc testing) because cross-doc rules first need to pass per-doc sanity (every rule still has a `falsifiability_statement` + per-doc check; cross-doc rules add a "compare across docs" step on top).

## When does Phase 5 run?

Skip Phase 5 if the corpus has no cross-doc rules. Detection during Phase 2 ([[rule-extraction]]):

- Rules whose `falsifiability_statement` references "consistent with another doc" / "matches the prior period" / "as disclosed elsewhere" → candidate cross-doc rules.
- Rules with `related_rules` cross-references to rules in other source regulations → may be cross-doc if the related rule lives in a sibling doc.

Phase 2 emits these as candidates with `cross_doc: candidate`. Phase 5 confirms or downgrades each.

If Phase 2 surfaces zero candidates, Phase 5 logs "no cross-doc rules found" in PLAN.md Log and moves to Phase 6 immediately. Don't manufacture cross-doc rules where the source doesn't support them.

## Phase 5 confirm-or-downgrade loop

For each candidate cross-doc rule from Phase 2:

1. **Confirm**: read the rule's source text closely. Does it explicitly say the verdict depends on a second doc? Or is the dependency a Phase-2 hallucination?
   - Confirmed → set `cross_doc: true` in the rule's SKILL.md frontmatter, proceed to step 2.
   - Downgraded → set `cross_doc: false`, log the reason in PLAN.md Log, proceed to next rule.

2. **Refactor the per-rule skill**:
   - Update `check_R<id>.py` to accept `docs: dict[str, document]` instead of `document`. Keys identify doc roles (e.g., `{"prospectus": ..., "quarterly": ...}`).
   - Document the expected dict shape in the SKILL.md body (which roles required, which optional).
   - Update `assets/samples/` to be folders: `pass-1/{prospectus.md, quarterly.md}`, `fail-1/{prospectus.md, quarterly.md}`.

3. **Test via [[rule-testing]]** with the cross-doc sample setup. Same systemic-vs-corner-case loop applies. Accuracy threshold may be looser for cross-doc rules (they're harder; consider -5% threshold relative to per-doc rules of same severity).

4. **Emit results** to `.john/checkpoints/testing/<rule-id>/cross_doc_results.json` (same structure as per-doc, plus a `doc_roles` field listing which doc roles each sample had).

## Sample setup for cross-doc rules

Per the overridden [[packaging]]:

```
<project>/.claude/skills/rule-R<id>/
├── SKILL.md                  # marks cross_doc: true; documents doc roles in body
├── check_R<id>.py            # signature: check(docs: dict[str, document]) -> dict
└── assets/
    └── samples/
        ├── pass-1/
        │   ├── prospectus.md
        │   └── quarterly.md
        ├── pass-2/
        │   ├── prospectus.md
        │   └── quarterly.md
        ├── fail-1/
        │   ├── prospectus.md
        │   └── quarterly.md
        └── ...
```

The runtime in Phase 7 (production QC) and beyond knows to load the doc set rather than a single doc when invoking a `cross_doc: true` rule. The orchestration is in `kc_runtime/` per [[app-design-thinking]] overridden runtime step 5.

## Runtime classification for cross-doc rules

At runtime step 3 (classify per overridden [[app-design-thinking]]), cross-doc rules are classified differently:

- **Per-doc rules** match against chunks within ONE doc's parse output.
- **Cross-doc rules** match against a doc SET — the runtime needs to know which docs belong together (a quarterly report belongs with its corresponding prospectus).

Three doc-grouping strategies the runtime supports (project picks one in PLAN.md):

1. **Manifest-driven**: input includes a `<batch>/manifest.json` listing which doc groups exist + which docs are in each group. Most reliable; manual.
2. **Filename convention**: docs in the same group share a prefix or naming pattern (e.g., `BankX_2024Q3_*`). Lighter; brittle to filename drift.
3. **Inferred-from-content**: the runtime uses an LLM call to infer doc groupings from metadata extracted at parse time (product name + period). Heaviest; only when manifest / filename aren't available.

Pick in PLAN.md Open Decisions before Phase 8. Default: manifest-driven (most reliable for production).

## Cross-doc rule accuracy thresholds

Cross-doc rules are systematically harder than per-doc rules — more moving parts, more chances for parse / chunk / extraction noise. Reasonable adjustments to [[rule-testing]]'s default thresholds:

| Severity | Per-doc default | Cross-doc adjustment |
|---|---|---|
| critical | 99% | 97% |
| high | 95% | 92% |
| medium | 90% | 85% |
| low | 85% | 80% |
| advisory | 75% | 70% |

These are starting points. Project tunes in PLAN.md Open Decisions per evidence.

## Cross-doc rule confidence

The composite confidence formula in [[confidence-system]] still applies, but with two changes:

- `source_presence` aggregates across all required docs. If 2 of 3 required docs are clean and 1 has missing fields, source_presence is averaged (with weighting toward the missing-fields doc).
- `method_prior` reflects the cross-doc orchestration overhead — typically 0.05 lower than the equivalent single-doc method.

`kc_runtime/confidence.py` handles this; no per-rule customization needed unless the user wants project-specific weighting.

## When Phase 5 surfaces new corner cases

Cross-doc rule testing often surfaces corner cases related to doc-grouping issues (e.g., "the rule fired on a quarterly that was correctly missing its prospectus because the product was discontinued"). These go in the rule's `assets/corner-cases.json` per [[corner-case-management]], same as per-doc corner cases.

## When Phase 5 fails to find a cross-doc dependency

If Phase 5 starts confirming candidates and discovers that ALL candidates downgrade to per-doc rules (i.e., Phase 2 was over-eager), log it. This is useful information: the rule corpus is simpler than initially modeled. May affect Phase 6 distillation cost estimates favorably.

## What this skill does NOT do

- It doesn't author rules. That's [[rule-extraction]] in Phase 2.
- It doesn't re-extract from scratch — Phase 5 builds on Phase 2's candidates.
- It doesn't change the runtime's per-doc verification path — cross-doc is added on top, doesn't replace per-doc.
- It doesn't handle "rules that span MANY docs over time" (e.g., a 12-month series of monthly reports) — those are conceptually still cross-doc rules but the orchestration is heavier. Treat as cross-doc with N-doc input; if the N becomes large (> ~5), surface to the user; may need a custom doc-grouping strategy.

## Cross-references

- [[rule-extraction]] — emits `cross_doc: candidate` flags Phase 5 acts on
- [[rule-testing]] — runs the same evolution loop on cross-doc rules (with cross-doc sample setup)
- [[packaging]] (overridden) — emits the cross-doc sample folder layout + the `docs: dict` check signature
- [[corner-case-management]] — absorbs cross-doc corner cases
- [[confidence-system]] — adjusts source_presence + method_prior for cross-doc findings
- [[app-design-thinking]] (overridden) — runtime step 5 is the cross-doc pass
- [[skill-to-workflow-distillation]] — distills cross-doc check.py to a cross-doc workflow.py (the workflow takes the same `docs: dict` input)
