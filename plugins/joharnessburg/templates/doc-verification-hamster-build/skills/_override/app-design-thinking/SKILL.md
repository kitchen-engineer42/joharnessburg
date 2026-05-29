---
name: app-design-thinking
description: Runtime structure for doc-verification projects is LOCKED — the produced app is a verifier with a fixed pipeline (parse → chunk → classify → apply → cross-doc → confidence → corner-case → output). Use this skill when the user mentions runtime / UX / production / deploy / "what kind of app", or when [[ralph-loop]] advances from per-rule packaging toward release. The shape is fixed; per-project customization is in dashboard fields, severity color-coding, UI labels — NOT in the pipeline shape.
metadata:
  triggers:
    - design the app
    - app design thinking
    - runtime structure
    - production pipeline
    - how should the app work
    - design the 2app phases
    - what kind of app
    - app shape
    - verifier runtime
    - dashboard design
---

# app-design-thinking (doc-verification override)

For doc-verification projects the runtime shape is locked. John core's `app-design-thinking` is co-authored, taste-driven, open-ended; this template narrows it because the kc_cli methodology only ships one product archetype: a doc-verifier with the pipeline below. Per-project customization happens **within the locked pipeline**, not at the pipeline shape.

If the user wants a fundamentally different runtime (chat app, slide builder, recommendation engine), they need a different template. Surface as Open Decision in PLAN.md; don't drift the runtime here.

## What this skill is NOT (in this template)

- It's not picking a runtime archetype. The archetype is "doc-verifier with confidence-stratified dashboard."
- It's not designing the production pipeline from scratch. The pipeline is the 8 phases in `plan_md_template.md`.
- It's not asking the user "what kind of app?" — that's already decided by picking this template.

## The locked runtime — what the produced app does

```
INPUT
  rule_doc(s):           regulations / policy / internal-rule files (Markdown / PDF / DOCX)
  doc(s)-under-test:     compliance reports, contracts, disclosures, filings — the things to verify

PROCESS (deterministic pipeline at runtime — implemented in release/v1/run.py + kc_runtime/)
  1. Parse        — multi-level: markitdown (cheap) → ppx (PDF heavy) → VLM-OCR (fallback).
                    Uses ${JOHN_PPX_CLIENT_URL} when reachable; falls back gracefully.
  2. Chunk        — hierarchical (statute-hierarchy for regulations, header-peeler for samples).
                    Each chunk tagged with applicable_scope hints.
  3. Classify     — per rule, find chunks in the doc-under-test whose applicable_scope matches.
                    No LLM call here; deterministic match against rule's applicable_scope + chunk metadata.
  4. Apply        — for each (rule, target-chunk) pair:
                      run workflows/R<id>/workflow.py (cheap-LLM Python from Phase 6 distillation)
                      OR if no workflow, fall back to running check_R<id>.py on SOTA (skills-as-production)
                    returns {verdict, confidence, evidence, citation}
  5. Cross-doc    — second pass for rules with cross_doc: true; collects evidence across docs.
                    Skip if no cross-doc rules in catalog.
  6. Confidence   — composite per-finding score via kc_runtime/confidence.py
                    (method_prior × source_presence × historical_accuracy × (1 - corner_proximity))
  7. Corner-case  — lookup each finding in <rule-id>/assets/corner-cases.json;
                    if match, augment verdict (e.g., "would-fail-but-known-exception").
                    NEVER patch the main rule logic with corner-case fixes.
  8. Aggregate    — group by (doc, severity), produce summary stats.

OUTPUT
  <output-dir>/result.json           — verdicts + evidence + confidence + citations per finding
  <output-dir>/dashboard.html        — HTML dashboard (auditor review UI; tabs + heatmap)
  <output-dir>/pdf_review.html       — OPTIONAL — two-column PDF review (left: source, right: findings)
                                       only when the user opted in + source is PDF
```

The pipeline is exposed via `release/v1/run.py` as:

```sh
python release/v1/run.py <input-doc> [--rule R042] [--output result.json] [--dashboard]
```

And, for batch / production runs:

```sh
python release/v1/run.py --batch <input-dir> --output <output-dir>
```

## Per-project customization — what stays open

The pipeline shape is locked, but these per-project pieces ARE the user's call (capture in PLAN.md's Open Decisions, settle by Phase 8):

- **Dashboard fields per finding**: minimum is `{rule_id, verdict, confidence, citation, evidence}`. Projects can add domain-specific fields (`auditor_notes`, `regulator_id`, `product_type`, ...) to the result.json and dashboard view.
- **Severity color-coding**: maps the project-declared severity vocab → visual styling. E.g., `critical → red, high → orange, medium → yellow, low → blue, advisory → grey`. Defaults provided in `kc_runtime/dashboard.py`; customize per project.
- **PDF review dashboard**: optional, only when source docs are PDFs AND the user wants page-level navigation. Off by default; turn on in Phase 8 if applicable.
- **Worker LLM tier defaults**: which TIER<N> a workflow uses per requirement_type. Defaults: TIER3 for quantitative, TIER2 for hybrid, TIER1 for pure-LLM. Override per-rule in workflow.py.
- **Sampling rates for QC** (Phase 7): default 10/50/100 (high/mid/low confidence). Tune to project risk tolerance + reviewer capacity.
- **Output language**: per `claude_addon.md`'s single-language rule, the entire dashboard speaks the project's declared language. No bilingual UI.

These are settle-once decisions made by Phase 8; don't re-litigate downstream.

## The runtime as a contract for upstream phases

The locked runtime informs upstream phases:

- **Phase 2 extraction** must produce rules with `applicable_scope` (runtime step 3 needs it).
- **Phase 3 per-rule packaging** must produce `check_R<id>.py` callable as `check(document) -> dict` with the runtime's expected return shape (runtime step 4 calls it directly OR via the distilled workflow).
- **Phase 6 distillation** must preserve the same return shape; workflows are drop-in replacements for check_R<id>.py at runtime.
- **Phase 7 confidence calibration** must produce `confidence_calibration.json` in the schema kc_runtime/confidence.py expects.

The reverse-flow ("runtime informs schema") that John core's app-design-thinking discusses is largely irrelevant here — the runtime is locked, so it doesn't surface schema gaps mid-flight. If it does (e.g., runtime needs `regulator_id` but extraction never captured it), that's an Open Decision per [[plan-md-evolution]] — usually extend the schema's optional fields rather than change the runtime shape.

## Reference archetype — the ONLY archetype this template ships

Verifier + auditor dashboard, kc_cli-style. The 5 reference archetypes in John core's `references/app-archetypes.md` (portfolio, detective game, lesson2slides, mathlab, voteyourapp) don't apply. If a project's runtime starts to resemble one of those, it doesn't belong in this template.

## What the user customizes vs. what's locked

| Decision | Locked / Custom |
|---|---|
| Pipeline shape (parse → chunk → ... → output) | **Locked** |
| Per-rule check function signature `check(document) -> dict` | **Locked** |
| Result JSON schema (verdict + confidence + evidence + citation) | **Locked** core fields; custom fields can be ADDED |
| Severity vocabulary | **Custom** (declared in PLAN.md Phase 0) |
| Dashboard color scheme + custom fields | **Custom** (Phase 8) |
| Worker LLM tier per requirement_type | **Custom** (defaults provided; override in Phase 6) |
| QC sampling rates | **Custom** (Phase 7 Open Decision) |
| PDF review dashboard on/off | **Custom** (Phase 8) |
| Output language | **Custom** (single-language, declared in Phase 0) |

## Working with the user

Unlike John core's app-design-thinking, this is NOT a co-authored design conversation. The runtime is fixed. The user's input is:

1. Phase 0: pick severity vocab + accuracy thresholds + language.
2. Phase 7 (Open Decisions): pick QC sampling rates if defaults aren't right.
3. Phase 8: customize dashboard fields + PDF review on/off + brand styling.

If the user pushes back ("I want a chat-style verifier" / "I want streaming results" / "I want a Slack bot UI"), surface as Open Decision and explain: this template ships ONE runtime shape; alternative shapes require forking the template or picking a different one. Don't drift the runtime to accommodate.

## When to iterate

Iteration applies to the **per-project customization** layer, not the locked pipeline:

- Dashboard customization can iterate based on auditor feedback after Phase 8 hand-off.
- Sampling rates can re-tune after a few production batches.
- Worker LLM tier choices can adjust as Phase 7 QC data reveals cost/accuracy patterns.

The pipeline shape itself does not iterate. If a project repeatedly hits the pipeline as the obstacle, the answer is "wrong template" — surface to the user, propose a sibling template or a core-John change to the platform.

## Cross-references

- [[schema-design]] (overridden) — rule + glossary schemas the runtime consumes
- [[packaging]] (overridden) — emits the per-rule skills AND the release bundle that implements this runtime
- [[skill-to-workflow-distillation]] — produces the cheap-LLM workflows the runtime executes at step 4
- [[cross-document-verification]] — step 5
- [[confidence-system]] — step 6
- [[corner-case-management]] — step 7
- [[dashboard-reporting]] — produces the dashboard.html at the end
- [[production-qc]] — Phase 7 QC, feeds back into the runtime's calibration
- [[plan-md-authoring]] — captures Phase 0 customization decisions
- [[plan-md-evolution]] — handles per-project customization iteration in Phases 7-8
- [[ralph-loop]] — advances through the 8 phases
- [[workerllm-runtime]] — runtime LLM integration for step 4
