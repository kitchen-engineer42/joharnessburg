# PLAN.md — {project_name}

*Created by `/john:init` on {date}, using the **doc-verification-hamster-build** template (kc_cli-derived, 8 phases). Edit freely; this is your living plan.*

## Project intent

<!--
Fill in:
- Regulation domain (financial reporting, contracts, insurance compliance, code-style, ...).
- What docs get verified (10-K filings? loan agreements? prospectuses? PRs?).
- Who uses the verifier (auditors? compliance officers? researchers? CI bot?).
- Accuracy target per severity tier (e.g., critical ≥99%, high ≥95%, medium ≥90%).
- **Language of the project** (en | zh | ...). Detected in Phase 0 from the rule corpus; all artifacts speak this language.
- **Severity vocabulary** (project-defined controlled vocab, e.g., `critical / high / medium / low / advisory`).
-->

## Knowledge inventory

- Rule corpus: `.john/input/rules/` (regulations, policy, internal-rule .md/.pdf/.docx)
- Sample docs (labeled): `.john/input/samples/` (used for rule-skill testing in Phase 4)
- Production docs: `.john/input/production/` (used in Phase 7 QC)
- Working state: `.john/parsed/`, `.john/chunks/`, `.john/knowledge/`, `.john/events/`, `.john/checkpoints/`
- Produced rule-skills: `<project>/.claude/skills/rule-R*/` — one skill per rule (Phase 3 output)
- Produced glossary skill: `<project>/.claude/skills/glossary/`
- Distilled workflows: `<project>/workflows/R*/workflow.py` (Phase 6 output)
- Release bundle: `<project>/release/v1/` (Phase 8 output; standalone, no John runtime needed)

## Four structures (pre-filled for verification — do not re-litigate)

- **Format of knowledge**: rules + glossary. Rules are the primary unit; glossary holds the shared vocabulary rules cross-reference. Per `claude_addon.md`'s hard constraints, this is locked — no facts, no stories, no wiki.
- **Schema of knowledge**: per the overridden [[schema-design]] skill. Rule and glossary schemas are pre-specified; severity vocabulary is project-defined (declare in Project intent above).
- **Runtime structure**: per the overridden [[app-design-thinking]] skill. Parse → Chunk → Classify(scope) → Apply (per-rule check) → Cross-doc pass → Confidence aggregation → Corner-case lookup → results.json + HTML dashboard + (optional) PDF review dashboard. Locked shape; per-project customization is in dashboard fields and UI labels, not in the pipeline.
- **Production pipeline**: the 8 phases below, mirroring kc_cli's proven 7-phase shape + Phase 0 bootstrap + Phase 5 cross-doc pass.

## Phases

### Phase 0: bootstrap

- **Intent**: read the rule corpus + sample docs at a survey level; detect language; classify the scenario (what kind of verification, what docs, what risks); confirm severity vocabulary + accuracy thresholds with the user; populate the Project intent block above.
- **Skills**: `using-john`, `plan-md-authoring`, `workspace-discipline`, [[parsing]] (light spot-checks only)
- **Required artifacts**: PLAN.md "Project intent" populated; language + severity vocab + accuracy thresholds committed; first read on whether the corpus needs cross-doc rules (informs Phase 5 budget).
- **Done criteria**: user signs off on Project intent block; layer-2 Claude can articulate the scenario in one paragraph.

### Phase 1: parse rule corpus + samples + production docs

- **Intent**: parse everything in `.john/input/` into structured markdown using the platform parser stack. Regulations + labeled samples are needed now; production docs can be parsed lazily before Phase 7.
- **Skills**: [[parsing]]
- **Required artifacts**: `.john/parsed/<source>/doc.md` + `.john/parsed/<source>/metadata.json` for every rule-corpus and sample doc.
- **Done criteria**: every rule corpus + sample doc has parsed output with metadata; parse failures are logged + surfaced as Open Decisions.

### Phase 2: chunk + extract rules + glossary

- **Intent**: chunk the rule corpus (hierarchical Chapter→Section→Article per overridden [[chunking]]); **source-first** extract every atomic rule + every glossary term from each chunk; emit via append-only event log; reduce to canonical state.
- **Skills**: [[chunking]] (overridden), [[rule-extraction]] (new), [[subagent-dispatch]], [[event-log-and-reducer]], [[knowledge-rewrite]]
- **Required artifacts**:
  - `.john/chunks/<chunk-id>.md` + `chunks_index.json` (rule corpus + samples)
  - `.john/events/extract/<chunk-id>/` events (one `rule_extracted` per atomic rule, `glossary_term` for each new term, `chunk_echo` per chunk, optional `incomplete_rule` for unfalsifiable candidates)
  - `.john/knowledge/rule-R*/` and `.john/knowledge/glossary/` (rewritten state)
- **Done criteria**: every rule-corpus chunk has at least one extraction event; MECE coverage audit passes (no obvious chapters with prescriptive language but zero rules extracted); every rule has a `falsifiability_statement` or is logged as `incomplete`.

### Phase 3: author per-rule skill (and glossary skill)

- **Intent**: for each rule from Phase 2, write its Claude Code skill (`SKILL.md` + `check_R<id>.py` + `references/` + `assets/samples/`) per the overridden [[packaging]]. Emit the glossary skill in parallel.
- **Skills**: [[packaging]] (overridden), [[subagent-dispatch]]
- **Required artifacts**: `<project>/.claude/skills/rule-R<id>/` for every rule; `<project>/.claude/skills/glossary/`.
- **Done criteria**: every rule from Phase 2 has a corresponding skill directory with all four required pieces; spot-check 5 random rule-skills load cleanly in a Claude Code session (frontmatter parses, body is markdown, cross-links resolve).

### Phase 4: test rules against labeled samples

- **Intent**: run each rule-skill against its labeled samples (`pass-*.md` / `fail-*.md`); measure accuracy per rule; iterate with the evolution loop's **systemic-vs-corner-case split** (≥10% failure = systemic, rewrite the rule; <10% = corner case, move to registry, don't patch main logic).
- **Skills**: [[rule-testing]] (new), [[corner-case-management]] (new), [[subagent-dispatch]]
- **Required artifacts**:
  - `.john/checkpoints/testing/<rule-id>/results.json` (pass/fail per sample + iteration history)
  - `<project>/.claude/skills/rule-R<id>/assets/corner-cases.json` for each rule with corner cases
- **Done criteria**: every rule has accuracy ≥ its severity-tier threshold OR is flagged in Open Decisions; corner cases are isolated to registries; iteration count per rule is bounded (max 3 rewrites).

### Phase 5: cross-document verification (if applicable)

- **Intent**: identify and run rules whose verdict depends on facts across MULTIPLE docs (e.g., consistency between a prospectus and a periodic report; same product disclosed differently across two filings). Second pass after per-doc Phase 4.
- **Skills**: [[cross-document-verification]] (new), [[rule-testing]] (overridden testing budget for cross-doc rules)
- **Required artifacts**:
  - `<project>/.claude/skills/rule-R<id>/SKILL.md` updated with `cross_doc: true` for cross-doc rules
  - `.john/checkpoints/testing/<rule-id>/cross_doc_results.json` for each cross-doc rule
- **Done criteria**: every candidate cross-doc rule from Phase 2 is either confirmed cross-doc (with passing test results) or downgraded to per-doc (with rationale in PLAN.md Log). Skip the phase entirely if the corpus has no cross-doc rules; note "no cross-doc rules surfaced" in the Log.

### Phase 6: distill skills to workflows (required)

- **Intent**: for each rule-skill that passed Phase 4 (and Phase 5 if applicable), distill it into a `<project>/workflows/R<id>/workflow.py` + per-step worker-LLM prompts. The workflow runs on tier-3/4 cheap models with the same accuracy as the rule-skill on SOTA (within tolerance).
- **Skills**: [[skill-to-workflow-distillation]] (new), [[workerllm-runtime]]
- **Required artifacts**:
  - `<project>/workflows/R<id>/workflow.py` for every passing rule
  - `<project>/workflows/R<id>/prompt_<step>.txt` for each LLM step
  - `.john/checkpoints/distillation/<rule-id>/accuracy_delta.json` (rule-skill vs workflow accuracy gap)
- **Done criteria**: every workflow's accuracy is within tolerance of its rule-skill (default 2% delta); workflows that can't meet tolerance fall back to running the rule-skill on SOTA (logged + surfaced; the user decides whether to ship the fallback or rework the rule).

### Phase 7: production QC

- **Intent**: run the distilled workflows on the production batch (`.john/input/production/`); apply **confidence-stratified sampling** (high-conf ≥0.9 → 10% review; mid 0.6–0.9 → 50%; low <0.6 → 100%); calibrate the confidence model against sample-batch ground truth.
- **Skills**: [[production-qc]] (new), [[confidence-system]] (new), [[corner-case-management]]
- **Required artifacts**:
  - `.john/checkpoints/qc/<batch>/results.json` (verdict + confidence per (rule, doc) pair)
  - `.john/checkpoints/qc/<batch>/sampling_review.json` (LLM-as-Judge results for sampled findings)
  - `<project>/confidence_calibration.json` (per-rule historical accuracy used by the runtime)
- **Done criteria**: calibration is sane (high-confidence findings match labels in sample; low-confidence findings are appropriately uncertain); production batch completes without runtime errors; QC report published.

### Phase 8: finalize release bundle

- **Intent**: package the rule-skills + workflows + calibration + glossary + dashboard scaffolds into a deployable bundle the team can run without John installed.
- **Skills**: [[packaging]] (overridden — release-bundle mode), [[dashboard-reporting]] (new), [[code-quality-guardrails]]
- **Required artifacts**: `<project>/release/v1/` containing `run.py`, `kc_runtime/{confidence.py, dashboard.py, __init__.py}`, `manifest.json`, `catalog.json` (rule catalog snapshot), `glossary.json`, `confidence_calibration.json`, `models.json` (tier→model mapping), `workflows/` (pinned), `fixtures/` (sample inputs if any), `render_dashboard.py`, `serve.sh`, `README.md`.
- **Done criteria**: clean test environment can run `python release/v1/run.py <doc>` and get a valid `result.json`; smoke test on 3 production docs passes; HTML dashboard renders.

## Subagent matrix

*Populated by Phase 2 (per-chunk rule-extractor) and Phase 4 (per-rule rule-tester). See [[subagent-dispatch]] + `agents/rule-extractor.md` + `agents/rule-tester.md`.*

## Open Decisions

*Examples for verification projects — replace with this project's actual decisions as they surface.*

- **Severity vocabulary**: declare here once chosen (e.g., `critical / high / medium / low / advisory`). Pre-Phase-0 default: not set.
- **Accuracy threshold per severity tier**: e.g., critical 99%, high 95%, medium 90%, low 85%, advisory 75%. Adjust based on user's risk tolerance.
- **Cross-document rules expected?** If yes, allocate Phase 5 time. If no, plan to skip Phase 5.
- **Distillation accuracy tolerance**: default 2% delta from rule-skill to workflow. Adjust if the domain is high-stakes (tighter) or cost-sensitive (looser).
- **Skills-as-production option**: skip Phase 6 + go directly to Phase 7 with rule-skills as the production artifact? Only if cost-per-doc analysis favors it. Discuss before Phase 6.
- **Production-QC sampling rates**: default 10/50/100. Adjust based on review-capacity constraints.
- **Cross-corpus glossary**: if multiple regulations share terms with different definitions, how does the glossary disambiguate? Default: scope each definition by source regulation; rules carry source_ref for their applicable definition.

## Log

- {date}: PLAN.md scaffolded by `/john:init` using the `doc-verification-hamster-build` template.
