---
name: rule-testing
description: Test each rule-skill against labeled sample documents; measure accuracy per rule; iterate with the systemic-vs-corner-case split (≥10% failure = rewrite the rule; <10% = move to corner-case registry, NEVER patch main logic). Use this skill in Phase 4 of a doc-verification project, after per-rule skills have been authored in Phase 3 and labeled samples are available. Accuracy thresholds are severity-tiered (project picks defaults in PLAN.md).
metadata:
  triggers:
    - test the rules
    - rule testing
    - rule testing phase
    - phase 4 testing
    - measure rule accuracy
    - validate rule skills
    - run rule against samples
    - evolution loop
    - iterate on rule
---

# rule-testing

After Phase 3 produces per-rule skills, Phase 4 tests each one against its labeled sample documents. Output: measured accuracy per rule, flagged list of rules below threshold, corner-case registry populated, dataset that calibrates the runtime's confidence model (Phase 7).

## The testing loop per rule

For each rule-skill at `<project>/.claude/skills/rule-R<id>/`:

1. **Load the rule's samples** from `<project>/.claude/skills/rule-R<id>/assets/samples/`. Each sample is labeled by filename prefix: `pass-N.md` (should pass) or `fail-N.md` (should fail). Header comment `<!-- label: pass | reason: ... -->` is optional but useful for debugging.

2. **Run the rule's `check_R<id>.py`** against each sample. Capture: `{verdict, confidence, evidence, citation}`.

3. **Compare against the label**. Tally pass-count + fail-count + ambiguous-count + wrong-verdict-count.

4. **Compute accuracy**: `(correct verdicts) / (total samples)`. The threshold depends on the rule's severity tier (set in PLAN.md Open Decisions; defaults: critical ≥99%, high ≥95%, medium ≥90%, low ≥85%, advisory ≥75%).

5. **If accuracy < threshold**, classify the failure pattern via the **systemic-vs-corner-case split**:

   - **Systemic** (failure rate ≥ 10% AND failures share a common pattern): rewrite the rule's SKILL.md body or `check_R<id>.py` logic. The rule itself is wrong — too narrow, too broad, mis-specified judgment. Re-run after rewriting.
   - **Corner case** (failure rate < 10% OR failures are scattered idiosyncratic cases): DO NOT patch the main rule logic. Move the failing pattern to `<rule-id>/assets/corner-cases.json` per [[corner-case-management]]. The main rule stays clean; the runtime checks the registry at step 7 of the runtime pipeline.

   **This split is the KC evolution-loop's key insight.** Without it, rule-skills accumulate hundreds of ad-hoc patches and become unmaintainable. With it, the main logic stays sharp and the registry holds the exceptions.

6. **Max 3 iteration rounds per rule.** If a rule can't reach its threshold after 3 systemic rewrites, surface for human review (see "When a rule consistently fails" below).

7. **Emit results** to `<project>/.john/checkpoints/testing/<rule-id>/results.json`:
   ```json
   {
     "rule_id": "R042",
     "accuracy": 0.94,
     "threshold": 0.95,
     "passed": false,
     "iteration_count": 2,
     "per_sample": [
       {"sample": "pass-1.md", "label": "pass", "verdict": "pass", "confidence": 0.92, "correct": true},
       {"sample": "fail-2.md", "label": "fail", "verdict": "pass", "confidence": 0.71, "correct": false, "classification": "corner-case"},
       ...
     ],
     "corner_cases_added": 1,
     "iteration_history": [
       {"round": 1, "accuracy": 0.81, "change": "Tightened judgment to require explicit numeric threshold."},
       {"round": 2, "accuracy": 0.94, "change": "Moved 1 idiosyncratic failure to corner-case registry."}
     ]
   }
   ```

## Subagent fan-out

Phase 4 fans out per rule (or batched if rules are tiny). One subagent runs the test loop for one rule. Per [[subagent-dispatch]]:

- **Brief**: project intent + the specific rule's SKILL.md + the rule's samples + the rule's severity-tier threshold + the evolution-loop budget (3 rounds) + the corner-case classification rules.
- **Output**: events to `<project>/.john/events/testing/<rule-id>/` describing each test result + iteration decision.
- **Return digest**: `{accuracy, iteration_count, threshold_met, corner_cases_added, final_verdict}`.

See `agents/rule-tester.md` for the canonical subagent briefing template.

## Accuracy thresholds per severity tier

Defaults (project can override in PLAN.md Open Decisions):

| Severity | Threshold | Rationale |
|---|---|---|
| critical | ≥99% | False negatives are unacceptable; better to over-fire and flag for human review |
| high | ≥95% | Strong-but-not-perfect; acceptable for most regulatory work |
| medium | ≥90% | KC's default; balances accuracy and dev cost |
| low | ≥85% | Style-ish rules; some noise tolerable |
| advisory | ≥75% | Recommendations, not requirements; high recall preferred over high precision |

Set per-rule overrides in the rule's SKILL.md frontmatter (e.g., `metadata.accuracy_threshold: 0.97` for a specific high-stakes rule in a "medium"-tier vocabulary).

If the project's severity vocab doesn't map cleanly to these 5 tiers, the user picks thresholds per their vocab in PLAN.md Open Decisions.

## The systemic-vs-corner-case decision rule (operational)

When a rule fails on samples, look at the failures:

- **Do the failures share a common pattern?** (e.g., "all failures are reports where the disclosure date is on a weekend") → likely systemic. Rewrite the rule to handle the pattern. Re-run.
- **Are the failures scattered, each with a different cause?** (e.g., "one failure is a weird formatting quirk, another is an unusual edge case, another is a typo in the doc") → likely corner cases. Move each to the registry.
- **Is the failure rate ≥ 10%?** → systemic threshold. If unsure between systemic and corner case, AND failure rate ≥ 10%, lean systemic.
- **Is the failure rate < 10%?** AND failures don't share a pattern → corner cases. Don't iterate the rule; move to registry.

When ambiguous (failure rate near 10%, partial pattern), surface to the user in PLAN.md Open Decisions. Don't decide unilaterally; the wrong call has lasting consequences (a systemic issue dumped into the registry pollutes it; a corner case treated as systemic over-narrows the rule).

## When a rule consistently fails (after 3 iteration rounds)

One of these is true:

1. **The rule is over-specified**: it tries to mechanically check a judgment call. Soften to `verdict: "needs-review"` with confidence floor; let humans triage.
2. **The samples are wrong**: spot-check the labels — sometimes labelers themselves are inconsistent. Surface to user; relabel + re-test.
3. **The rule should be split**: the rule covers two cases that need separate logic. Surface as a Phase-2-reopen request to re-extract the source chapter as two rules.
4. **The rule should be dropped**: some prescriptive language in a regulation is genuinely ambiguous; verifiers can't do better than humans. Drop from v1 with a note in PLAN.md Log.

The decision is the user's. Surface via PLAN.md Open Decisions with the failure pattern + which of the 4 paths you recommend.

## Confidence calibration (foundation for Phase 7)

Phase 4's per-sample results feed Phase 7's confidence calibration. The composite confidence in [[confidence-system]] uses `historical_accuracy` as a factor — for each rule, count the per-sample correct/incorrect from results.json + corner-case overlap rate, store as the rule's historical accuracy baseline.

Phase 7 refines this with production-batch evidence; Phase 4 lays the foundation. **Don't skip the per-sample detail in results.json** — the calibrator needs it.

## Cross-document rules — handled in Phase 5

A rule with `cross_doc: true` (set in Phase 5) needs evidence from multiple docs to produce a verdict. Phase 4 still tests these rules, but the test setup is different:

- Samples are organized as folders, not files: `<rule-id>/assets/samples/pass-1/{doc-A.md, doc-B.md}` etc.
- `check_R<id>.py` is called with a dict-of-docs, not a single doc.
- The iteration loop runs the same; corner-case classification applies the same.

See [[cross-document-verification]] for the additional rules-of-thumb for cross-doc rules' accuracy + confidence.

## What this skill does NOT do

- It doesn't author rules. That's [[rule-extraction]] in Phase 2.
- It doesn't package rules. That's the overridden [[packaging]] in Phase 3.
- It doesn't run on production data. That's [[production-qc]] in Phase 7.
- It doesn't distill rules into cheap-LLM workflows. That's [[skill-to-workflow-distillation]] in Phase 6.
- It doesn't decide whether the rule SHOULD exist — that's the user's call surfaced in Open Decisions.

## Cross-references

- [[rule-extraction]] — produces the rules tested here
- [[packaging]] (overridden) — produces the rule-skill directories tested here
- [[corner-case-management]] — the registry that absorbs corner-case failures
- [[subagent-dispatch]] — per-rule fan-out
- [[event-log-and-reducer]] — coordination of per-rule test events
- [[confidence-system]] — consumes per-sample results for calibration baseline
- [[skill-to-workflow-distillation]] — receives Phase 4's "this rule is testable + passes threshold" signal as the go-ahead for distillation
- [[cross-document-verification]] — additional patterns for cross-doc rule testing
- [[knowledge-rewrite]] — if testing reveals rules need restructuring, this is where the corrective events fold in
- See `agents/rule-tester.md` for the canonical subagent briefing template
