## Active template: doc-verification

This is a verification project (KC_CLI-style). The produced app is a doc-verifier: user uploads a batch of documents (financial reports, compliance filings, contracts, etc.), the app applies all extracted rules to all relevant document chapters, surfaces violations with explanations, and shows results in a dashboard.

**Knowledge format**: rules. Full stop. Not facts, not stories, not wiki entries — rules. Every entry in the knowledge base is a rule with the schema: `{id, source_ref, trigger, judgment, decision_tree, glossary_refs, severity, falsifiability_statement, test_case_stub}`. If a piece of source content doesn't fit the rule schema, it goes in the glossary instead.

**Source-first principle** (kc_cli's hard-won lesson): extract rules from the source regulation documents FIRST. Only after a complete first-pass catalog should you open sample documents for validation. Reverse the order and you silently drop rules the samples don't exercise.

**Falsifiability is mandatory**. Every rule has a `falsifiability_statement`: the precise condition under which the rule fails on a document. Without this, the rule isn't machine-checkable and the runtime can't apply it.

**Per-rule packaging**. Each rule produces a single Claude Code skill directory at `<project>/.claude/skills/rule-R<id>/` with SKILL.md + check_R<id>.py + references/ + assets/samples/. The runtime loads only the rule-skills relevant to a given document's classification.

**Phase pipeline mirrors KC's 7 phases**: parse regulations → extract rules → author per-rule skill → test skill against labeled samples → distill skill to workflow (cheap-LLM-friendly) → production QC with confidence calibration → finalize as release bundle. Adapted from kc_cli; see plan_md_template.md.

**Avoid scope creep**: this template is rules-only. Don't propose adding facts, stories, wiki, or generic knowledge entries. If the project surfaces non-rule content the verifier needs, surface it as an Open Decision and discuss whether to extend the template or create a sibling project.
