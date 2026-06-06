---
name: packaging
description: Emit each rule as a Claude Code skill at <project>/.claude/skills/rule-R<id>/ (per-rule mode, Phase 3) AND emit the produced app's release bundle at <project>/release/v1/ (release-bundle mode, Phase 8). Use this skill whenever the per-rule authoring phase fires, when the user says "package the rules" / "ship the verifier" / "build the release bundle", or when [[ralph-loop]] signals packaging is next. This overrides John core's general packaging with KC's two-mode shape — DO NOT default to generic per-entry skill emission.
metadata:
  triggers:
    - package the rules
    - emit rule skills
    - ship the rules
    - finalize knowledge phases
    - per-rule skill emission
    - package the verifier
    - build the release bundle
    - emit release bundle
    - packaging phase
    - ready for app phases
---

# packaging (doc-verification override)

For doc-verification projects packaging runs in TWO modes at different phases:

- **Per-rule mode** (Phase 3): emit each extracted rule as a Claude Code skill at `<project>/.claude/skills/rule-R<id>/`.
- **Release-bundle mode** (Phase 8): emit a deployable bundle at `<project>/release/v1/` that runs the verifier without John installed.

Both modes are KC-derived. John core's generic "knowledge entry → skill" emission is the wrong shape here — DO NOT use it. The per-rule shape was chosen because each rule needs its own checker, samples, and references; bundling rules into category skills loses the runtime's per-rule fan-out.

## Per-rule mode (Phase 3)

### Per-rule directory structure

```
<project>/.claude/skills/rule-R<id>/
├── SKILL.md              # required: pushy description + body teaching when + how to apply this rule
├── check_R<id>.py        # required: deterministic check (or hybrid: code + worker LLM)
├── references/
│   ├── source.md         # quoted regulation text + citation
│   ├── decision-tree.md  # the rule's if-then logic, structured
│   └── glossary-refs.md  # cross-links to glossary terms (Markdown links to glossary skill entries)
└── assets/
    ├── samples/
    │   ├── pass-1.md     # labeled samples that should PASS this rule
    │   ├── pass-2.md
    │   ├── fail-1.md     # labeled samples that should FAIL this rule
    │   └── fail-2.md
    └── corner-cases.json  # OPTIONAL — populated by [[corner-case-management]] in Phase 4+
```

Plus a separate **glossary skill** at `<project>/.claude/skills/glossary/SKILL.md` for all shared terms. The glossary skill is bundled (one skill containing all terms), not per-term — terms are dense and benefit from co-location.

### SKILL.md frontmatter per rule

```yaml
---
name: rule-R042
description: Verify quarterly disclosure timing (15-business-day deadline). Apply this skill whenever the user uploads a quarterly financial report, asks "is this filing on time?", or wants to check filings against Article 15.2. Apply for ANY quarterly-filing scenario, even when the user doesn't reference the rule explicitly. Severity: <project-vocab>. Source: 信披办法第十五条 / Reg 15.2.
metadata:
  rule_id: R042
  source_ref: "Reg 15.2"
  severity: "<from project-declared vocab>"
  requirement_type: "quantitative"
  applicable_scope: ["public_fund", "private_fund"]
  cross_doc: false
  triggers:
    - quarterly disclosure
    - quarterly report timing
    - 15.2
    - is the report on time
    - quarterly filing deadline
---
```

Descriptions are **pushy** per [[knowledge-rewrite]]'s description-pushiness pattern (carried from John core). List contexts in which the rule applies, not just what the rule says.

### SKILL.md body per rule

```markdown
# Rule R042: Quarterly disclosure timing

## What the rule says
<one-paragraph plain-language summary, in the project's language>

## Source
<source_ref>: "<verbatim quote from the regulation>"
(Full quote with citation in `references/source.md`.)

## Falsifiability statement
<the precise condition under which this rule FAILS on a document>

## Check logic

1. Extract <entity-1>, <entity-2> from the document. Implementation in `check_R<id>.py`.
2. Apply the judgment: <pass/fail/needs-review criterion>.
3. Return `{verdict, confidence, evidence, citation}`.

Decision tree: see `references/decision-tree.md`.

## Glossary references

- [[glossary-quarterly-report]]
- [[glossary-disclosure-date]]
- [[glossary-business-day]]

## Confidence

<per-rule confidence ceiling/floor, if any — see [[confidence-system]]>
```

The body's language follows the project's declared language (see `claude_addon.md`). Field names + headings stay in English.

### check_R<id>.py — the per-rule executable

A Python file with a single function `check(document) -> dict`. Returns `{verdict, confidence, evidence, citation}`.

Three implementation strategies, picked per `requirement_type`:

- **Pure deterministic** (regex / arithmetic / parsing): for quantitative rules with clear numeric thresholds, structural rules (presence/absence of required sections), date arithmetic. Highest confidence per [[confidence-system]]'s method priors. Example: "extract two dates, compute business-day delta, threshold check."
- **Hybrid** (code extracts, worker LLM judges): for imperative / prohibitive / conditional rules where extraction is mechanical but judgment is semantic. Code extracts the candidate entity / passage; worker LLM applies the rule with a tight prompt. Example: "extract the disclosed risks section, ask worker LLM whether it covers all required risk categories." See [[skill-to-workflow-distillation]] for prompt design.
- **Pure worker-LLM** (judgment-heavy rules): when even the extraction is context-dependent. Lowest confidence; surface explicitly to the user during Phase 3 review.

Imports + tier selection are project-side; `check_R<id>.py` calls into the project's workflow infrastructure (Phase 6 produces the `<project>/workflows/R<id>/workflow.py` that's the cheap-LLM-friendly distilled version of the same logic — Phase 3's `check_R<id>.py` is the SOTA Claude version).

### assets/samples/

Labeled examples — at minimum 2 pass + 2 fail per rule. The [[rule-testing]] skill in Phase 4 reads these. Real projects ship 10+ each per rule for confidence calibration to be meaningful. Sample format: regulation-language doc-under-test excerpts (one rule's relevant section per file), with a leading comment header `<!-- label: pass | reason: ... -->` or `<!-- label: fail | reason: ... -->`.

### assets/corner-cases.json

Populated by [[corner-case-management]] starting in Phase 4. JSON list of `{pattern, expected_verdict, source, added_at}` entries the runtime checks lazily AFTER the main rule logic — never inside it. Keep this file empty until Phase 4 surfaces actual corner cases.

## Release-bundle mode (Phase 8)

After Phase 7 produces verified, calibrated rule-skills + distilled workflows, Phase 8 packages them into a deployable bundle the team runs without John.

### Bundle structure

```
<project>/release/v1/
├── run.py                       # standalone driver: python run.py <input-doc> [--rule R042] [--dashboard]
├── kc_runtime/
│   ├── __init__.py
│   ├── confidence.py            # composite scoring per [[confidence-system]]
│   └── dashboard.py             # HTML rendering per [[dashboard-reporting]]
├── render_dashboard.py          # re-render HTML from a saved result.json
├── serve.sh                     # optional local HTTP server for browsing dashboards
├── manifest.json                # bundle metadata (rules, models, snapshot tag, build date)
├── catalog.json                 # rule catalog snapshot at release time
├── glossary.json                # project glossary at release time
├── confidence_calibration.json  # per-rule historical accuracy (from Phase 7)
├── models.json                  # tier→model assignments (read by run.py at runtime)
├── workflows/
│   ├── R001/
│   │   ├── workflow.py
│   │   └── prompt_<step>.txt
│   ├── R002/...
│   └── ...
├── fixtures/                    # OPTIONAL — sample inputs for smoke testing
│   └── *.md
└── README.md                    # how to run, what env vars are needed, caveats
```

### Scaffolding the bundle

Don't write `run.py` + `kc_runtime/` by hand. Invoke the platform-shipped `scaffold_release_bundle.py` script:

```sh
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/scaffold_release_bundle.py \
  --project <project-root> \
  --target release/v1 \
  --catalog .john/knowledge/catalog.json \
  --glossary .john/knowledge/glossary.json \
  --calibration .john/checkpoints/qc/confidence_calibration.json \
  --workflows <project>/workflows
```

The script copies templated source files from `${CLAUDE_PLUGIN_ROOT}/scripts/release_bundle_assets/` into the project, populates `manifest.json`, and writes a project-specific `README.md`. Layer-3 Claude then reviews the scaffolded bundle and customizes dashboard fields (see [[dashboard-reporting]]) for the project's domain.

### Bundle is self-contained

The release bundle has NO dependency on John (the plugin) at runtime. Required at runtime:

- Python 3
- `LLM_API_KEY`, `LLM_BASE_URL`, `TIER1..TIER4` env vars (for cheap-LLM calls from workflows)
- Optionally `${JOHN_PPX_CLIENT_URL}` if the input docs need ppx parsing (otherwise markitdown handles parse)

The bundle MAY assume a platform parser is reachable via `${JOHN_PPX_CLIENT_URL}`, but should degrade gracefully — `run.py` should try the URL; if unreachable, fall back to `markitdown` or document the requirement in `README.md`.

## Quality checks before each packaging phase is done

### Phase 3 quality checks

1. **Every rule-skill loads cleanly.** YAML frontmatter parses; body is valid markdown.
2. **Descriptions are pushy.** Spot-check 5: would Claude reliably trigger this skill on a relevant prompt?
3. **Cross-links resolve.** `[[glossary-<term>]]` references resolve to entries in the glossary skill.
4. **No leaked workspace paths.** Skills shouldn't reference `<project>/.john/` (working state).
5. **`check_R<id>.py` is callable.** Importable, has `check(document) -> dict`, doesn't raise on a smoke-test sample.

### Phase 8 quality checks

1. **`run.py` works on the fixtures/.** Output is a valid `result.json`.
2. **`manifest.json` is complete.** All rules, all workflows, all model assignments, build timestamp.
3. **`README.md` is project-specific.** Not the template's generic README; mentions the actual rules + scope.
4. **Dashboard renders.** `python render_dashboard.py result.json output.html` produces a viewable HTML.
5. **No leaked dev-time paths.** Bundle references no path under `<project>/.john/` or `<workspace>/forks/`.

## Asset lifecycle

Template-provided assets (the scaffolding source under `release_bundle_assets/`) are copied by `scaffold_release_bundle.py` into the project. They're then under the project's control — layer-2 Claude can customize `dashboard.py` for the project's color scheme, add fields to `confidence.py` for project-specific scoring tweaks, etc. The template's source assets remain unchanged in the plugin install.

## What ships, what doesn't

Ships in `<project>/.claude/skills/`:
- One directory per rule with all four required pieces.
- The glossary skill.

Ships in `<project>/release/v1/`:
- Standalone runtime + workflows + calibration + dashboard scaffold.

Does NOT ship:
- Raw `<project>/.john/knowledge/` — working state, audit trail material only.
- Event logs — captured separately by `/john:archive` if the user wants them.
- Sample inputs from `<project>/.john/input/samples/` — those are dev-time, not runtime. Fixtures in the release bundle are a curated subset.

## The handoff to the app phases

After Phase 3, PLAN.md's Knowledge inventory section transitions from "pointer to `.john/input/`" to "pointer to `.claude/skills/rule-R*/`" — the app phases (Phase 4 onward, and ultimately Phase 8's release bundle) have a real per-rule deliverable to consume.

After Phase 8, the project is shippable: the user moves `<project>/release/v1/` to wherever the team runs verifiers.

## Cross-references

- [[rule-extraction]] — produces the rules this skill packages (Phase 2)
- [[rule-testing]] — verifies the packaged skills work on samples (Phase 4)
- [[skill-to-workflow-distillation]] — produces the workflows that ship in the bundle (Phase 6)
- [[corner-case-management]] — populates `assets/corner-cases.json` (Phase 4+)
- [[confidence-system]] — produces `confidence_calibration.json` (Phase 7)
- [[dashboard-reporting]] — customizes the bundled `kc_runtime/dashboard.py` (Phase 8)
- [[schema-design]] (overridden) — defines the rule + glossary fields packaged here
- [[knowledge-rewrite]] — dedup + cross-link before packaging
- [[ralph-loop]] — advances out of per-rule packaging into Phase 4 testing, and later into release bundling
- [[app-design-thinking]] (overridden) — runtime shape the release bundle implements
