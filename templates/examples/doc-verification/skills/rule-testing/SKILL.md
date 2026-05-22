---
name: rule-testing
description: Test each extracted rule-skill against labeled sample documents; measure accuracy; iterate rule body when accuracy is below threshold. Use this skill in Phase 4 of a doc-verification project, after the per-rule skills have been authored (Phase 3) and labeled samples are available. Accuracy threshold default 90%; some rules may need higher.
metadata:
  triggers:
    - test the rules
    - rule testing phase
    - measure rule accuracy
    - validate rule skills
    - run rule against samples
---

# rule-testing (doc-verification template)

After Phase 3 produces per-rule skills, Phase 4 tests each one against labeled sample documents. The output: a measured accuracy per rule, a flagged list of rules below threshold for iteration, and the dataset that calibrates the runtime's confidence model.

## The testing loop per rule

For each rule-skill (at `<project>/.claude/skills/rule-R<id>/`):

1. **Load the rule's samples**. They live at `<project>/.claude/skills/rule-R<id>/assets/samples/`. Each sample is labeled (`pass-N.md` or `fail-N.md`).

2. **Run the rule's `check_R<id>.py` against each sample**. Capture: verdict, confidence, evidence, citation.

3. **Compare against the label**. Pass count + fail count + ambiguous count.

4. **Compute accuracy**: `(correct verdicts) / (total samples)`. Threshold default: 90%.

5. **If accuracy is below threshold**:
   - Read the failures: which samples got the wrong verdict, and why?
   - Iterate the rule's SKILL.md body or `check_R<id>.py` logic.
   - Re-run. Document the change in PLAN.md's Log.
   - Max 3 iteration rounds per rule; after that, flag for human review.

6. **Emit results**: write `<project>/.john/checkpoints/testing/<rule-id>/results.json` with accuracy, per-sample outcomes, iteration history.

## Subagent fan-out

Phase 4 fans out per rule (or batched if rules are tiny). One subagent runs the test loop for one rule. Per [[subagent-dispatch]]:

- Brief: project intent + the specific rule's SKILL.md + the rule's samples.
- Output: events to `<project>/.john/events/testing/<rule-id>/` describing each test result + iteration decision.
- Return digest: accuracy + iteration count + final verdict.

## Accuracy threshold per rule

Default 90%. But:

- **High-stakes compliance rules** (financial, legal): bump to 95% or 99%.
- **Heuristic rules** (style, formatting): 80% may be fine.
- **Judgment-heavy rules** (intent, context-dependent): bias toward higher confidence requirements even at the cost of more "needs-review" verdicts.

Set per-rule thresholds in the rule's SKILL.md frontmatter or in PLAN.md's Open Decisions.

## When a rule consistently fails

If a rule can't reach threshold after 3 iterations, one of:

1. **The rule is over-specified**: it tries to mechanically check a judgment call. Soften to "needs-review" verdict instead of pass/fail.
2. **The samples are wrong**: spot-check the labels — sometimes the labeling itself is inconsistent. Surface to user.
3. **The rule should be split**: the rule might cover two cases that need separate logic. Surface as a schema observation, re-extract.
4. **The rule should be dropped**: some prescriptive language in a regulation is genuinely ambiguous; the verifier can't do better than a human auditor. Drop the rule from v1 with a note.

The decision is the user's. Surface via PLAN.md's Open Decisions.

## Confidence calibration (foundation for Phase 6)

The testing phase doesn't just give pass/fail per rule — it produces the calibration data the runtime's confidence model needs:

- For each rule + label combo, count agreements + disagreements.
- The runtime in production will use this to weight findings: rules with consistent high-accuracy testing get high-confidence verdicts; rules with mixed performance get explicit "low confidence" labels surfaced to the auditor.

Phase 6 (production QC) refines this; Phase 4 lays the foundation.

## What this skill does NOT do

- It doesn't author rules. That's [[rule-extraction]] in Phase 2.
- It doesn't package rules. That's the template-overridden [[packaging]] in Phase 3.
- It doesn't distill rules into cheap-LLM workflows. That's Phase 5 (optional, beyond M5 scope).

## Cross-references

- [[rule-extraction]] — produces the rules tested here
- [[packaging]] (template-overridden) — produces the rule-skill directories tested here
- [[subagent-dispatch]] — fan-out per rule
- [[event-log-and-reducer]] — coordination of per-rule test events
- [[code-quality-guardrails]] — the produced verifier (Phase 7) gets standard quality checks; rule-testing is the rules' quality check
- [[knowledge-rewrite]] — if testing reveals rules need restructuring, this is where the corrective events get folded
