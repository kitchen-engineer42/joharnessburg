---
name: confidence-system
description: Composite confidence scoring for verification findings — combines method prior, source presence, historical accuracy, and corner-case proximity. Use this skill in Phase 7 when calibrating confidence from rule-testing + production-QC data, when [[production-qc]] needs to pick sampling rates, when the dashboard needs confidence bins, or when designing per-rule confidence floors/ceilings. The composite formula is locked; per-rule overrides + project tuning are open.
metadata:
  triggers:
    - confidence scoring
    - confidence calibration
    - confidence system
    - composite confidence
    - method prior
    - confidence stratification
    - calibrate confidence
    - confidence floor
    - confidence ceiling
---

# confidence-system

Doc-verification findings aren't binary. A rule's verdict on a doc carries a **confidence score** that downstream consumers (production QC sampling, dashboard heatmap, corner-case scope) use to triage review effort. This skill defines the confidence composite + the calibration loop that grounds it in measured data.

## The composite formula

```
confidence = method_prior  ×  source_presence  ×  historical_accuracy  ×  (1 − corner_proximity)
```

Each factor in [0, 1]. The product is the per-finding confidence. From kc_cli, with light naming changes.

### Factor 1: method_prior

How the check produced its verdict matters. Determined by `check_R<id>.py`'s implementation strategy (per overridden [[packaging]]):

| Method | method_prior | Why |
|---|---|---|
| regex / pure deterministic | 0.95 | Closed-form check; only fails if extraction parsing breaks |
| python arithmetic / structural | 0.90 | Numeric / structural checks; high reliability but data quality matters |
| hybrid (code extract + LLM judge) | 0.75 | Extraction is reliable; judgment is LLM-bounded |
| pure worker LLM | 0.75 | Same as hybrid; LLM is the bottleneck |
| OCR-derived input | 0.65 | OCR can mis-read characters; degrades any downstream method |
| fallback (couldn't run primary) | 0.50 | Something went wrong; verdict should be reviewed |

`check_R<id>.py` returns `evidence_method: "regex" | "python" | "hybrid" | "llm" | "ocr" | "fallback"`. The runtime maps to the prior. Per-rule overrides are allowed in the rule's SKILL.md frontmatter (`metadata.method_prior_override: 0.85` for a quirky rule).

### Factor 2: source_presence

Did the check find the data it needs in the doc? Returns 1.0 if all required entities/sections were located cleanly; lower if some were missing or ambiguous:

- All required fields present + parseable: **1.0**
- One required field ambiguous (e.g., two candidate dates, unclear which is canonical): **0.7**
- One required field missing: **0.4** (verdict is usually `needs-review`)
- Multiple required fields missing: **0.2** (verdict is usually `needs-review` or `cannot-judge`)

`check_R<id>.py` reports source_presence as part of its return dict. The runtime multiplies it into the composite.

### Factor 3: historical_accuracy

The rule's measured accuracy from Phase 4 testing + Phase 7 QC sampling. Stored per-rule in `<project>/confidence_calibration.json`:

```json
{
  "R042": {
    "phase_4_accuracy": 0.94,
    "phase_7_sampled_accuracy": 0.96,
    "weighted_accuracy": 0.95,
    "sample_count": 50,
    "updated_at": "2026-05-27T10:00:00Z"
  }
}
```

The composite uses `weighted_accuracy` (weighted average of Phase 4 + Phase 7 results, weighted by sample count). Initially (before Phase 7 data lands) it's just `phase_4_accuracy`.

Update the file via `confidence_calibrate.py` (in plugin scripts/) after Phase 4 + after each Phase 7 batch.

### Factor 4: corner_proximity

How close is this finding to a known corner case in the rule's registry? Per [[corner-case-management]]:

- Distance computed by the runtime comparing the finding's evidence + extracted entities against entries in `<rule-id>/assets/corner-cases.json`.
- `0.0` if no corner-case overlap (composite is unchanged).
- `1.0` if exact match (composite collapses to 0; the verdict is the corner-case's `expected_verdict`).
- Intermediate values for partial pattern matches.

The exact distance function depends on the corner-case representation; kc_runtime/confidence.py implements a default (string similarity on evidence + structural match on entities). Projects can customize the distance function in their `kc_runtime/confidence.py` after Phase 8 scaffolding.

## Confidence bins for the dashboard + QC sampling

The composite confidence is a real number in [0, 1]. The dashboard + [[production-qc]] sampling use binned categories:

| Bin | Range | Dashboard | Phase 7 sampling rate |
|---|---|---|---|
| high | ≥ 0.9 | green | 10% (spot-check) |
| mid | 0.6 − 0.9 | yellow | 50% (substantive review) |
| low | < 0.6 | red | 100% (every finding reviewed) |

Bin boundaries are tunable per project (PLAN.md Open Decisions). Defaults are kc_cli's. Tighter boundaries (e.g., high ≥ 0.95) push more findings into review at the cost of reviewer time; looser boundaries (high ≥ 0.8) ship faster but risk under-review of imperfect findings.

## Per-rule confidence floor + ceiling

Some rules have intrinsic confidence ceilings (a pure-LLM judgment-heavy rule can't ever hit 0.95 even when the runtime sees clean data). Others have floors (a deterministic regex check shouldn't drop below 0.85 even when source_presence is low).

Set in the rule's SKILL.md frontmatter:

```yaml
metadata:
  confidence_floor: 0.5   # composite never drops below this
  confidence_ceiling: 0.8 # composite never rises above this
```

Floor + ceiling apply after the composite is computed; clip into the range. Don't go below 0 or above 1.

## Calibration loop

```
Phase 4 (testing)
  → per-rule {accuracy, sample_count} → confidence_calibration.json (initial)

Phase 7 (production QC)
  → per-rule sampled review {accuracy, sample_count}
  → weighted update of confidence_calibration.json
  → re-bin findings if calibration shifted significantly
```

`scripts/confidence_calibrate.py` does the update. Invoke after each Phase 7 batch:

```sh
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/confidence_calibrate.py \
  --testing-results .john/checkpoints/testing/ \
  --qc-results .john/checkpoints/qc/<latest-batch>/ \
  --output <project>/confidence_calibration.json
```

The script:

1. Aggregates per-rule accuracy + sample counts from Phase 4 + Phase 7.
2. Computes weighted_accuracy = (phase_4_acc × phase_4_count + phase_7_acc × phase_7_count) / (phase_4_count + phase_7_count).
3. Updates `<project>/confidence_calibration.json`.
4. Logs deltas (rules whose calibration shifted > 0.05) so the user knows which rules are most volatile.

The release bundle (Phase 8) ships `confidence_calibration.json` alongside `kc_runtime/confidence.py`; production runs read both at startup.

## When confidence shifts after Phase 8

Production batches keep producing data. The dashboard can include a "re-calibrate" workflow that the user runs after every N batches to refresh `confidence_calibration.json`. The composite formula doesn't change; only the historical_accuracy factor updates.

Big shifts (a rule's accuracy drops from 0.95 to 0.80) should trigger an alert + a recommendation to re-run that rule's Phase 4 with new samples drawn from the production batch — the rule's behavior on production data is diverging from its sample-set behavior, and the registry / rule may need re-work.

## What this skill does NOT do

- It doesn't decide WHAT to do with low-confidence findings. That's [[production-qc]]'s sampling logic + the dashboard's UI.
- It doesn't write check_R<id>.py — but it specifies what the check function must return (`{verdict, confidence, evidence, citation, evidence_method, source_presence}`). The overridden [[packaging]] respects this contract.
- It doesn't compute corner_proximity itself — `kc_runtime/confidence.py` (scaffolded by `scaffold_release_bundle.py`) does, using corner-case-registry entries from [[corner-case-management]].

## Cross-references

- [[corner-case-management]] — provides corner-case registries that feed corner_proximity
- [[rule-testing]] — produces phase_4_accuracy
- [[production-qc]] — produces phase_7_accuracy + uses confidence bins for sampling
- [[packaging]] (overridden) — emits check_R<id>.py with the required return contract; emits kc_runtime/confidence.py in release bundle
- [[skill-to-workflow-distillation]] — workflows must report evidence_method + source_presence for confidence to work
- [[dashboard-reporting]] — bins findings by confidence in the dashboard
- [[app-design-thinking]] (overridden) — step 6 of the runtime is confidence aggregation
