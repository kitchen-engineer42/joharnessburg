---
name: dashboard-reporting
description: Generate HTML dashboards for the verification app's auditor / developer user — tabs (Summary, Per-Rule, Exceptions, Confidence Heatmap), optional two-column PDF review dashboard with click-to-page jumps. Use this skill in Phase 8 when scaffolding the release bundle's dashboard, when the user mentions dashboard / report / visualization, or when customizing dashboard fields per project. The base dashboard ships via scaffold_release_bundle.py; per-project customization happens after scaffolding.
metadata:
  triggers:
    - dashboard
    - dashboard reporting
    - generate dashboard
    - html dashboard
    - pdf review dashboard
    - visualize results
    - review ui
    - finalize dashboard
    - render report
    - phase 8 dashboard
---

# dashboard-reporting

The produced verification app outputs `results.json` (machine-readable) AND an `dashboard.html` (human-readable). This skill teaches layer-2 Claude to scaffold the dashboard via `scaffold_release_bundle.py` and customize per project.

The dashboard is for the **dev-time developer user** (the team building the verifier — they want to see what the runtime did) AND the **production auditor user** (the person reviewing flagged findings — they want to navigate violations efficiently). The same dashboard serves both; UI tabs separate concerns.

## What the dashboard shows

Four tabs by default:

### Tab 1: Summary

- Total docs verified, total findings, overall pass/fail breakdown.
- Per-severity counts (using project's declared severity vocab — see [[schema-design]] override).
- Confidence-bin distribution (high/mid/low — see [[confidence-system]]).
- Batch-level stats: when run, how long, any errors.

Quick view for "did the run go well?"

### Tab 2: Per-Rule

- One row per rule.
- Columns: rule_id, description, severity, total findings, pass/fail/needs-review counts, average confidence, accuracy (from `confidence_calibration.json`).
- Sortable by any column; default sort: severity descending, then accuracy ascending (problem rules surface).
- Click a row → expand into per-finding list for that rule.

For developer use: which rules are firing a lot, which have low confidence, which need attention.

### Tab 3: Exceptions

- All findings flagged for review (per [[production-qc]]'s sampling rules + judge disagreements).
- Each finding shows: rule, doc, verdict, confidence, evidence quote, citation, judge-comment (if reviewed).
- Filter by: severity, doc, rule, reviewer-decision.

For auditor use: the actual work queue.

### Tab 4: Confidence Heatmap

- Matrix: rules × docs. Cell color = confidence (red → green).
- Hover over cell → finding details.
- Filter rules / docs by severity / doc-type.

For both users: spot the patterns. A column (one doc) that's mostly red = that doc has many uncertain findings, probably needs human attention. A row (one rule) that's mostly red = that rule is mis-calibrated, may need re-distillation or more corner cases.

## Scaffolding the dashboard

Don't write dashboard.html or kc_runtime/dashboard.py by hand. Invoke `scaffold_release_bundle.py` (which calls into `release_bundle_assets/dashboard.py.tmpl` + `dashboard.html.tmpl`):

```sh
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/scaffold_release_bundle.py \
  --project <project-root> \
  --target release/v1 \
  --catalog .john/knowledge/catalog.json \
  --glossary .john/knowledge/glossary.json \
  --calibration <project>/confidence_calibration.json \
  --workflows <project>/workflows \
  --severity-vocab <space-separated-from-PLAN.md>
```

The script:

1. Copies `kc_runtime/dashboard.py.tmpl` → `release/v1/kc_runtime/dashboard.py` with project-specific substitutions.
2. Copies `dashboard.html.tmpl` → `release/v1/templates/dashboard.html.tmpl` (used by render_dashboard.py).
3. Sets up the severity color-coding map based on the project's declared severity vocab.

After scaffolding, layer-2 Claude reviews and customizes — see below.

## Per-project customization (after scaffolding)

The scaffolded dashboard is generic. Customize for the project:

1. **Severity color-coding**. Default colors map onto the project's severity vocab:
   - 5-tier (critical / high / medium / low / advisory): red / orange / yellow / blue / grey
   - 3-tier (high / medium / low): red / yellow / blue
   - Binary (material / non-material): red / grey
   - Custom: pick colors that fit the user's domain conventions (e.g., financial regulation often uses red/amber/green; code review uses red/yellow/blue).
   
   Edit `release/v1/kc_runtime/dashboard.py`'s `SEVERITY_COLORS` dict.

2. **Custom fields per finding**. If the project's results include domain-specific fields beyond `{rule_id, verdict, confidence, evidence, citation}`, surface them in the Exceptions tab + per-finding expansion view. Edit the Jinja template `release/v1/templates/dashboard.html.tmpl`.

3. **Per-rule grouping**. If the project has natural rule categories (e.g., "Disclosure Rules", "Risk Rules", "Fee Rules"), group the Per-Rule tab by category. Add a `category` field to the rule catalog + group in the template.

4. **Language**. Per `claude_addon.md`'s single-language rule, the dashboard labels speak the project's declared language. The scaffolded dashboard.html.tmpl has placeholder English labels — translate during Phase 8.

5. **Branding**. Optional. A project-specific logo / title / footer. Editable in the dashboard.html.tmpl.

## PDF review dashboard (optional)

For projects where source docs are PDFs AND the user wants page-level navigation, scaffold an additional PDF review dashboard:

```sh
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/scaffold_release_bundle.py \
  ... [as above] ...
  --pdf-review-dashboard
```

Layout: two columns. Left: rendered source PDF (via pdf.js). Right: findings list, each with a "jump to page N" link. Click a finding → left column scrolls to the page; the relevant text gets highlighted.

Useful for compliance review where the reviewer needs to see the finding IN CONTEXT in the source doc. Heavier (ships pdf.js); only opt-in.

## Re-rendering after a new batch

After every batch, the runtime updates results.json. Re-render the dashboard:

```sh
python3 release/v1/render_dashboard.py \
  --results <output-dir>/result.json \
  --calibration <project>/confidence_calibration.json \
  --catalog release/v1/catalog.json \
  --output <output-dir>/dashboard.html
```

`render_dashboard.py` is scaffolded; doesn't need customization unless dashboard structure changes.

## Serving the dashboard

For shared review, serve via `release/v1/serve.sh`:

```sh
release/v1/serve.sh 8080  # serves the latest output dir at http://localhost:8080/
```

For deployment beyond a single reviewer, the dashboard's HTML is fully self-contained (CSS + JS inline) — works as a static file on any web host. Don't add server-side rendering; keep it static + portable.

## What this skill does NOT do

- It doesn't compute results — `release/v1/run.py` does, via the workflows.
- It doesn't decide which findings to review — [[production-qc]] does, via confidence-stratified sampling.
- It doesn't author rule descriptions — [[rule-extraction]] does, in Phase 2.
- It doesn't write `confidence.py` — that's bundled by the overridden [[packaging]] + customized per project.

## Cross-references

- [[packaging]] (overridden) — Phase 8 release-bundle mode includes the dashboard scaffold + render_dashboard.py
- [[confidence-system]] — provides the bins + colors the dashboard surfaces
- [[production-qc]] — provides the sampling status + judge-review data the Exceptions tab shows
- [[schema-design]] (overridden) — defines the severity vocab the color-coding maps onto
- [[corner-case-management]] — finds annotated with corner-case overlap show explicitly in the dashboard
- [[app-design-thinking]] (overridden) — the runtime that produces results.json the dashboard renders
- [[code-quality-guardrails]] — applies to the customized dashboard.py + render_dashboard.py code
