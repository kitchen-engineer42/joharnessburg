# PLAN.md — {project_name}

*Created by `/joharnessburg:init` on {date}, using the **doc-verification** template (KC_CLI-equivalent). Edit freely; this is your living plan.*

## Project intent

<!-- Which regulation domain (financial reporting, compliance, contracts, ...)? What docs get verified (10-K filings? loan agreements? quarterly reports?)? Who uses the verifier (auditors? compliance officers? researchers?)? Accuracy target (95%? 98%? 99%)? -->

## Knowledge inventory

- Initial input: `.john/input/` (regulation documents — laws, policies, internal rules)
- Sample documents: `.john/samples/` (labeled documents for testing extracted rules)
- Produced skills (after 2skills half): `.claude/skills/rule-R*/` — one skill per rule
- Glossary: `.claude/skills/glossary/` — shared vocabulary

## Four structures (pre-filled for verification)

- **Format of knowledge**: rules + glossary. Rules are the primary unit; glossary is shared vocabulary referenced by rules.
- **Schema of knowledge**: per the rule schema in this template's `schema-design` override — see [[schema-design]] (the active version is the doc-verification override, automatically merged for this project). Headers + bodies per the universal progressive-disclosure pattern.
- **Runtime structure**: doc-upload UI → parse + classify each document → apply all rules in scope → produce violations report + confidence per finding → dashboard for the auditor to review.
- **Production pipeline**: 7 phases below, mirroring KC's verified shape.

## Phases

### Phase 1: parse regulations + samples

- Intent: parse the regulation documents (rules source) and sample documents (testing material) into structured markdown.
- Skills to invoke: `parsing`
- Required artifacts: `.john/parsed/<regulation-source>/doc.md`, `.john/parsed/<sample>/doc.md` for each sample
- Done criteria: every input + sample has parsed output with metadata.json

### Phase 2: extract rules

- Intent: source-first sweep through regulation docs to extract every atomic rule with falsifiability + test_case_stub. Subagent fan-out per chunk.
- Skills to invoke: `rule-extraction` (template-provided), `chunking`, `subagent-dispatch`, `event-log-and-reducer`
- Required artifacts: `.john/checkpoints/extract/state.json` with N rules + glossary entries
- Done criteria: every regulation chunk has at least one rule-extraction event (or an explicit "no rules in this chunk" event); coverage audit shows no obvious gaps

### Phase 3: author skill per rule

- Intent: for each rule, write its Claude Code skill (SKILL.md + check_R<id>.py + references + samples) per [[packaging]]'s override.
- Skills to invoke: `packaging` (template-overridden), `subagent-dispatch` (one subagent per rule)
- Required artifacts: `<project>/.claude/skills/rule-R<id>/` for each rule
- Done criteria: every rule from Phase 2 has a corresponding skill directory with all four files

### Phase 4: test rules against samples

- Intent: run each rule-skill against the labeled samples; measure accuracy; iterate skill body if accuracy is below threshold.
- Skills to invoke: `rule-testing` (template-provided), `subagent-dispatch`
- Required artifacts: `.john/checkpoints/testing/<rule-id>/results.json` with pass/fail per sample
- Done criteria: every rule has accuracy ≥ threshold (default 90%); rules below threshold get iterated or flagged

### Phase 5: distill to workflows (TBD, may skip)

- Intent: translate proven rules into cheaper-model workflows (Python + workerLLM prompts) for production-scale execution. Optional; only if cost-per-doc matters.
- Skills to invoke: TBD; mostly Bash-based scripting outside John's standard skills
- Required artifacts: `<project>/workflows/R<id>/workflow.py`
- Done criteria: workflows match the corresponding rule-skill's accuracy within tolerance

### Phase 6: production QC

- Intent: run the distilled workflows on a production batch; sample stratified by confidence; calibrate the confidence model.
- Skills to invoke: `code-quality-guardrails` for the produced verifier
- Required artifacts: `.john/checkpoints/qc/<batch>/results.json` + `confidence_calibration.json`
- Done criteria: confidence calibration is sane (high-confidence findings match labels; low-confidence findings are appropriately uncertain)

### Phase 7: finalize as release bundle

- Intent: package the rule-skills + workflows + calibration + dashboard into a deployable bundle.
- Skills to invoke: `packaging` (final emission), `code-quality-guardrails`
- Required artifacts: `<app-output>/release/v1/` with all deliverables + README
- Done criteria: bundle installs and runs on a clean test environment; smoke test on 3 sample docs passes

## Subagent matrix

*Populated by Phase 2 (extraction) and Phase 4 (testing).*

## Open Decisions

*Examples for verification projects:*
- Accuracy threshold per rule: 90% default, but some rules may need 99% (high-stakes compliance)?
- Confidence model: built-in calibration or use the team's existing one?
- Which subset of rules to ship in v1 vs defer (some rules may be too ambiguous for v1)?

## Log

- {date}: PLAN.md scaffolded by `/joharnessburg:init` using the doc-verification template.
