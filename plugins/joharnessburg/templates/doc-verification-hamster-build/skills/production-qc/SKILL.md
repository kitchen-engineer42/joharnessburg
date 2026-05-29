---
name: production-qc
description: Run distilled workflows on production batches with confidence-stratified sampling for quality control (Phase 7). Use this skill when running the first production batches, when the user mentions QC / sampling / quality control / batch verification, or when calibrating the confidence model with real production evidence. The sampling rates are tunable per project; LLM-as-Judge reviews sampled findings; per-batch calibration feeds back into [[confidence-system]].
metadata:
  triggers:
    - production qc
    - quality control
    - phase 7 qc
    - batch verification
    - production batch
    - confidence stratified sampling
    - sampling rates
    - llm as judge
    - review findings
---

# production-qc

After Phase 6 produces distilled workflows, Phase 7 runs them on the production batch (`.john/input/production/`) and applies **confidence-stratified sampling** to triage which findings need human review.

This phase serves two purposes:
1. **Operational**: actually verify production docs and produce results for the user / auditor.
2. **Calibration**: collect ground-truth-from-review data that updates [[confidence-system]]'s `historical_accuracy` factor.

Both run in the same phase; calibration is a byproduct of operational verification, not a separate exercise.

## Confidence-stratified sampling — the core idea

Reviewing 100% of findings is expensive. Reviewing 0% is unsafe. The compromise: bin findings by confidence, sample at different rates per bin, propagate the sampled accuracy back to the bin.

Default sampling rates per [[confidence-system]] confidence bins:

| Confidence bin | Range | Sampling rate | Reviewer focus |
|---|---|---|---|
| high | ≥ 0.9 | 10% | Spot-check: are we missing anything? |
| mid | 0.6 − 0.9 | 50% | Substantive review: most ambiguity lives here |
| low | < 0.6 | 100% | Every finding reviewed; runtime is uncertain |

Tunable per project in PLAN.md Open Decisions. Tighter rates (e.g., 20/70/100) push more findings to review; loose rates (5/30/100) ship faster but risk under-review of imperfect findings.

## The batch loop

1. **Parse + verify the production batch** — run `release/v1/run.py --batch <input-dir>` (after the release bundle exists; in Phase 7 you might run via the dev-time pipeline before the release bundle is finalized). Produces `.john/checkpoints/qc/<batch-id>/raw_results.json`.

2. **Bin findings** by composite confidence (per [[confidence-system]]).

3. **Sample within each bin** at the project's declared rates:
   ```
   high_findings = [f for f in findings if f.confidence >= 0.9]
   high_sample   = random.sample(high_findings, k=int(len(high_findings) * 0.1))
   mid_sample    = ...
   low_sample    = all_low_findings  # 100%
   ```

   Random sampling is fine for most projects; stratified-by-rule sampling is better when some rules have few findings (ensures every rule's findings get reviewed at the rate). The default is stratified-by-rule; override to flat random in PLAN.md if your project prefers.

4. **LLM-as-Judge review of sampled findings**. For each sampled finding, dispatch a subagent (or batched LLM call) with:
   - The rule's SKILL.md + the relevant doc chunk + the runtime's verdict + evidence + confidence.
   - Prompt: "Does the verdict look correct? Provide: agree/disagree, reasoning, suggested-verdict if disagree." Use TIER1 (SOTA) for judging — judge accuracy matters more than cost here.
   - Capture in `.john/checkpoints/qc/<batch-id>/sampling_review.json`.

5. **Compute per-bin agreement rate**. For each bin: `agreement_rate = (judge_agreed_count) / (sampled_count)`. This is the bin's "true positive rate."

6. **Extrapolate to the population**: for unsampled findings in each bin, the assumed accuracy is the bin's agreement rate. Surface as `extrapolated_accuracy` per bin.

7. **Flag findings for review**:
   - All disagree-with-judge findings → mandatory review.
   - All low-confidence findings → mandatory review (already 100% sampled).
   - High-confidence findings the judge disagreed with → escalate; if a pattern emerges, may indicate calibration drift.

8. **Update per-rule calibration**. Aggregate per-rule sampled accuracy from sampling_review.json. Feed into `confidence_calibrate.py`:
   ```sh
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/confidence_calibrate.py \
     --testing-results .john/checkpoints/testing/ \
     --qc-results .john/checkpoints/qc/<batch-id>/ \
     --output <project>/confidence_calibration.json
   ```

9. **Emit QC report** to `.john/checkpoints/qc/<batch-id>/qc_report.md`:
   - Per-bin: sampled count, agreement rate, extrapolated accuracy.
   - Per-rule: findings count, agreement rate, calibration shift (if any).
   - Flagged-for-review list (with rationales).
   - Corner cases surfaced (findings the judge classified as exceptions — feed to [[corner-case-management]]).

## Surfacing corner cases from QC review

When the judge disagrees with a runtime verdict AND the disagreement looks idiosyncratic (one weird doc, not a rule-wide issue), it's a candidate corner case. Per [[corner-case-management]]:

1. The user reviews the disagreement.
2. If confirmed as a corner case, add to `<rule-id>/assets/corner-cases.json`.
3. The next QC batch picks up the registry update automatically.

The default flow has the user in the loop for corner-case additions in Phase 7. Don't add corner cases unilaterally from the judge's disagreement — false positives in corner-case classification pollute the registry.

## Subagent fan-out

Phase 7 fans out in two ways:

- **Verification fan-out**: per (rule × doc) pair, but distilled workflows are fast enough that running them sequentially per doc may be fine; the fan-out happens at the doc level.
- **Judge fan-out**: per sampled finding. One subagent (or batched LLM call) per finding. Brief includes the rule's SKILL.md + the chunk + the verdict.

For large batches (> 1000 docs × 100 rules), use scripted fan-out via `run.py --batch` rather than spawning Claude Code subagents for every (rule, doc) pair.

## Calibration update cadence

Every batch updates `confidence_calibration.json`. Big shifts (a rule's accuracy moves by > 0.05) should trigger an alert:

- Maybe the rule is degrading on production data (regulation updated, doc format changed).
- Maybe the calibration was wrong to begin with and is now correcting.
- Maybe the batch is unrepresentative.

Surface big shifts in the QC report's "calibration deltas" section. The user decides whether to act.

## Re-running rules with shifted calibration

If a rule's `weighted_accuracy` drops significantly:

1. Surface as Open Decision in PLAN.md.
2. Options:
   - **Re-extract**: go back to Phase 2 for this rule's source chapter; maybe the regulation interpretation changed.
   - **Re-distill**: go back to Phase 6 for this rule; maybe the prompt or tier needs updating.
   - **Add corner cases**: maybe the production batch just has new patterns that fit the registry.
   - **Accept drift**: log and move on; the dashboard surfaces the lower confidence to reviewers.

Don't decide unilaterally. Drift is information; the user knows whether it's a real signal or batch noise.

## Skipping QC for low-stakes projects

For a quick demo / proof-of-concept, the user may opt out of LLM-as-Judge review. Surface as Open Decision; if accepted, Phase 7 still:

- Runs verification on the production batch.
- Bins findings by confidence.
- Emits results (no judge review, no calibration update).

The composite confidence stays at its Phase-4-based calibration; the dashboard works but with weaker accuracy baselines.

## What this skill does NOT do

- It doesn't run the runtime — that's `release/v1/run.py`, scaffolded by the overridden [[packaging]] in Phase 8.
- It doesn't decide whether to ship — the user reviews the QC report and decides.
- It doesn't fix rules — surfaces issues; rule fixes go back to Phase 3 (re-package) or Phase 6 (re-distill).
- It doesn't compute confidence — [[confidence-system]]'s composite formula does; this skill consumes the bins.

## Cross-references

- [[confidence-system]] — bins findings; this skill samples within bins and updates calibration
- [[corner-case-management]] — receives QC-surfaced corner cases (with user sign-off)
- [[skill-to-workflow-distillation]] — produces the workflows QC runs
- [[packaging]] (overridden) — Phase 8 release bundle is informed by QC's calibration_json output
- [[dashboard-reporting]] — visualizes QC results + sampling status + calibration deltas
- [[app-design-thinking]] (overridden) — the runtime that produces the raw findings QC operates on
- [[subagent-dispatch]] — fan-out for judge review
- [[event-log-and-reducer]] — coordination of per-finding judge events
