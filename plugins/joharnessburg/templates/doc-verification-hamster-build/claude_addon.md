## Active template: doc-verification (kc_cli-derived, 8-phase)

This is a **doc-verification project**. The produced app verifies one or more *docs-under-test* against a *rule corpus* (regulations, internal policy, contract templates, compliance handbooks). The runtime parses + chunks both, applies each rule to the relevant chapters of each doc-under-test, and surfaces violations with source references, severities, and confidence.

The template is a John-idiom translation of kc_cli's 7-phase methodology, with an explicit Phase 0 added for scenario bootstrap and Phase 5 for cross-document rules. Read `plan_md_template.md` for the phase shape.

### Hard constraints (do not relax without surfacing as Open Decision)

**Knowledge format: rules + glossary, full stop.** Every entry in the knowledge base is either a *rule* or a *glossary term*. No facts, no stories, no wiki entries. If a piece of source content doesn't fit the rule or glossary schema, surface it as an Open Decision — *don't* invent a third format on the fly.

**Source-first principle** (kc_cli's hard-won lesson, kept verbatim): extract rules from the source regulation documents FIRST. Only after a complete first-pass catalog is built do you open sample documents for validation. Reverse the order and you silently drop rules the samples don't exercise. See [[rule-extraction]].

**Falsifiability is mandatory.** Every rule has a `falsifiability_statement`: the precise condition under which the rule fails on a document. Without it, the rule isn't machine-checkable and the runtime can't apply it. Incomplete rules go in PLAN.md's Open Decisions, not into the live catalog.

**Per-rule packaging.** Each rule produces one Claude Code skill at `<project>/.claude/skills/rule-R<id>/` with `SKILL.md` + `check_R<id>.py` + `references/` + `assets/samples/`. See the overridden [[packaging]] skill. Bundling rules into per-category skills is wrong for this template; if you're tempted, you're working with the wrong template.

**Corner cases stay in a registry — NEVER patch the main rule logic with corner-case fixes.** kc_cli learned this the hard way: workflows accumulate hundreds of ad-hoc patches and become unmaintainable. Use [[corner-case-management]] from Phase 4 onward; the registry loads lazily at runtime when a corner-case pattern matches.

**Distillation Phase 6 is required, not optional.** Even when a rule-skill works on SOTA Opus, distill it to a Python + tier-3/4 worker LLM workflow before shipping. Production runs the distilled workflows; rule-skills are intermediate. See [[skill-to-workflow-distillation]].

### Single-language project rule

**Detect the rule corpus's language in Phase 0. Commit to one language. Use it for all project artifacts.**

That means: rule descriptions, source quotes, glossary definitions, `check_R<id>.py` prompt strings, decision-tree prose, dashboard labels, violation messages — **all in the same language as the rule corpus**. Don't mix English and Chinese (or any two languages) within a project. The schema field *names* stay language-agnostic (`source_ref`, not 出处); the field *contents* speak the corpus language.

Layer-3 Claude detects the language during the bootstrap phase reading sample regulation chunks. Capture the choice in PLAN.md's "Project intent" section. From that point on, all subagent briefings, all generated content, all dashboards speak that language.

The skills themselves (the meta-skills layer-2 Claude reads to know what to do) stay in English — they're internal guidance, not user-facing artifacts.

### Skills-as-production-mode is a valid endpoint

Even though distillation is required by default, layer-2 Claude should know: a fully-tested set of rule-skills running on SOTA Claude is *already* a production-ready verifier — just an expensive one. If a project has low-volume, high-stakes verification (audit-level work, regulatory filings reviewed quarterly), and the user signs off, the skills-only path is legitimate. Surface as an Open Decision before Phase 6 if cost-per-doc trade-offs favor it.

### Severity vocabulary is project-defined

The schema accepts `severity` as a controlled vocabulary, but the values are NOT fixed by the template. Pick the values in Phase 0, declare them in PLAN.md's "Project intent" section (e.g., `severity values: critical / high / medium / low / advisory` for financial regulation; `severity values: blocker / warning / info` for code-style checks). Layer-3 Claude uses the declared list for every extracted rule's severity field. The dashboard's color-coding maps to whatever vocab the project picks.

### Avoid scope creep

This template is rules + glossary only. Don't propose adding facts, stories, wiki entries, or schema-less "notes." If the project surfaces non-rule content the verifier needs (e.g., a list of regulator entity names that helps interpret the corpus), surface it as an Open Decision and discuss whether to:
- Extend the glossary schema (cheap, usually right)
- Extend the rule schema (medium cost; re-emit affected entries)
- Build a sibling project with a different template (heavy; only for fundamentally different shapes)

### Skill priority

When two skills offer guidance that conflicts: **meta-meta skills override meta skills**. The meta-meta layer (workshop discipline, plan-md mechanics, ralph_loop, subagent-dispatch, the four-structures cascade) is architectural. The meta layer (the specific verification skills like rule-extraction, rule-testing, confidence-system) is methodology. Architecture wins.
