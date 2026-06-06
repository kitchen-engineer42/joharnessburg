---
name: corner-case-management
description: Manage the per-rule corner-case registry — failures from Phase 4 testing that DON'T fit the main rule logic. Use this skill whenever rule-testing surfaces idiosyncratic failures (<10% rate, no shared pattern), when the runtime needs to load corner cases for a rule, or when the user asks how to handle exceptions. The KEY DISCIPLINE is: NEVER patch the main rule logic with corner-case fixes — keep them isolated in the registry, loaded lazily at runtime AFTER the main check.
metadata:
  triggers:
    - corner case
    - corner cases
    - corner-case registry
    - exception case
    - edge case registry
    - handle exception
    - keep the rule clean
    - registry
    - rule exception
---

# corner-case-management

KC's hard-won lesson, kept as discipline: **NEVER patch the main rule logic with corner-case fixes.**

When a rule fails on samples and the failure rate is < 10% AND failures don't share a common pattern, those failures are corner cases. The temptation is to add a special-case branch to the rule's SKILL.md / `check_R<id>.py` to handle each one. **Resist.** Workflows that absorb corner-cases this way accumulate dozens of ad-hoc patches and become unmaintainable. After a year of patches, no one can read the rule's logic anymore — it's a maze of special cases.

Instead: keep the main rule sharp. Stash each corner case in a registry. The runtime checks the registry AFTER the main check and AUGMENTS the verdict.

## The registry per rule

`<project>/.claude/skills/rule-R<id>/assets/corner-cases.json`:

```json
{
  "rule_id": "R042",
  "version": "1.2",
  "entries": [
    {
      "id": "CC042-001",
      "pattern": {
        "kind": "exact_doc_match",
        "fingerprint": "sha256:..."
      },
      "expected_verdict": "pass",
      "actual_main_verdict": "fail",
      "reason": "Q3 2024 quarterly report from BankX — the disclosure date is one day late but a regulator exemption was issued (Notice 2024-15). The rule correctly fires; this is a known exception, not a rule bug.",
      "source": "Phase 4 testing, 2026-05-15, sample fail-7.md",
      "added_at": "2026-05-15T12:00:00Z",
      "added_by": "subagent rule-tester for R042 round 2",
      "expires_at": "2027-01-01T00:00:00Z"
    },
    {
      "id": "CC042-002",
      "pattern": {
        "kind": "structural",
        "matchers": [
          {"path": "doc.product_type", "equals": "money_market_fund"},
          {"path": "doc.reporting_period", "equals": "weekly"}
        ]
      },
      "expected_verdict": "needs-review",
      "actual_main_verdict": "fail",
      "reason": "Weekly money-market reports follow a different disclosure cadence per Notice 2023-11; the 15-day rule technically doesn't apply but it's not a clean pass either. Surface for human review.",
      "source": "Phase 4 testing, 2026-05-16, sample fail-12.md",
      "added_at": "2026-05-16T09:00:00Z",
      "added_by": "user (resolved as Open Decision)",
      "expires_at": null
    }
  ]
}
```

## Pattern kinds

The registry supports multiple pattern kinds for matching a finding to a corner case:

- **exact_doc_match**: SHA-256 fingerprint of the source doc's content. Catches the literal same doc next time. Cheap; useful for "this one specific doc has a known exception."
- **structural**: list of path-matchers against the runtime's extracted entities. Catches a class of docs that share structural features. The path matcher uses dot-notation against the runtime's `evidence` dict.
- **regex**: a regex applied to the doc's text. Catches docs with a common textual pattern (e.g., a specific clause). Use sparingly — regex overlap with main rule logic is what we're trying to avoid.
- **embedding**: optional, for projects with embedding infrastructure. Vector similarity above threshold. Heavy; usually overkill.

Default to `structural`. Use `exact_doc_match` only for one-off exceptions. Use `regex` only when the corner case truly is a textual pattern unrelated to the rule's main extraction.

## When to add a corner case

In Phase 4 ([[rule-testing]]), when a rule fails on a sample AND the failure looks idiosyncratic (not part of a pattern affecting many samples):

1. Determine the pattern that picks out this failure (preferably structural).
2. Determine the `expected_verdict` (what the rule SHOULD have returned for this doc: `pass`, `fail`, `needs-review`, `not-applicable`).
3. Write a one-sentence `reason` explaining why this is an exception, not a rule bug.
4. Optionally set `expires_at` if the exception is time-bound (e.g., a regulator's temporary notice).
5. Append to `<rule-id>/assets/corner-cases.json` via the [[rule-testing]] subagent (or manually if surfaced as Open Decision).

In Phase 7 ([[production-qc]]), when a sampled finding gets re-classified by a human reviewer as a corner case:

1. Same procedure; add via the QC review interface.
2. Re-calibrate confidence (corner_proximity factor in [[confidence-system]] may shift other findings).

## What the runtime does with corner cases

At runtime step 7 (per overridden [[app-design-thinking]]), AFTER the main check has produced a verdict:

1. For each finding, look up the rule's `corner-cases.json`.
2. Compute `corner_proximity` per pattern kind.
3. If any corner case matches above a threshold (default 0.85):
   - Replace `verdict` with the corner case's `expected_verdict`.
   - Augment `evidence` with `{corner_case_id, corner_case_reason}` for the dashboard.
   - Drive `corner_proximity` factor in the confidence composite ([[confidence-system]] factor 4).
4. If multiple corner cases match, pick the highest-proximity one + log the conflict.

The main rule's `check_R<id>.py` NEVER reads `corner-cases.json` — keeps the main logic clean. The runtime in `kc_runtime/` reads the registry separately.

## Registry hygiene

Periodically (e.g., per release tag), prune the registry:

- Remove `expires_at < now()` entries.
- For each remaining entry, check if its pattern still matches anything in current production data — if not, the corner case may no longer be relevant (regulation changed, doc structure evolved). Surface as Open Decision for the user to remove or keep.
- If the registry for one rule grows past 20 entries, that's a yellow flag: maybe the rule SHOULD have been split or rewritten. Surface to the user with the suggestion to re-extract the rule from source.

`scripts/confidence_calibrate.py` does NOT prune the registry — pruning is a user decision. The script may emit a recommendations report.

## The discipline (one more time)

The reason this discipline exists:

A rule that started as

```python
def check(doc):
    return verdict_if_disclosure_late(doc.disclosure_date, doc.quarter_end_date, 15)
```

becomes, after a year of corner-case patches absorbed into the main logic:

```python
def check(doc):
    if doc.is_money_market and doc.is_weekly_reporting: return "needs-review"
    if doc.regulator_notice in EXEMPTIONS_2024: return "pass"
    if doc.fund_type == "REIT" and doc.distribution_quarter: return verdict_if_disclosure_late(...)
    if doc.is_amended_filing: return amended_check(...)
    # ... 30 more branches
    return verdict_if_disclosure_late(doc.disclosure_date, doc.quarter_end_date, 15)
```

No one can read this. No one can fix bugs in it. The original rule's intent is buried. KC watched this happen — and built the corner-case registry pattern in response.

**Keep the rule clean. Stash exceptions in the registry. The runtime handles the augmentation.**

## What this skill does NOT do

- It doesn't decide what's a corner case vs a systemic issue — that's [[rule-testing]]'s 10% threshold.
- It doesn't compute corner_proximity — `kc_runtime/confidence.py` does, at runtime.
- It doesn't run the main check — `check_R<id>.py` does, before corner-case lookup.
- It doesn't store WHY a doc is a corner case beyond a one-sentence `reason` — for deeper rationale, see PLAN.md Log or the source event in `.john/events/testing/`.

## Cross-references

- [[rule-testing]] — surfaces corner cases via the systemic-vs-corner-case split (Phase 4)
- [[production-qc]] — surfaces additional corner cases from sampled QC review (Phase 7)
- [[confidence-system]] — uses corner_proximity as factor 4 of the composite
- [[packaging]] (overridden) — emits assets/corner-cases.json (empty file initially); release bundle includes registries
- [[app-design-thinking]] (overridden) — runtime step 7 looks up the registry
