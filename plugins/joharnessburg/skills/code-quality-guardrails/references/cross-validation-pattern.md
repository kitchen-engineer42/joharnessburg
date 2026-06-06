# cross-validation-pattern — the opt-in LLM reviewer

When deterministic guardrails have run and the residual issues need judgment, dispatch a cross-validation subagent. Borrowed from a production app-builder's opt-in review flow.

## The shape

A separate subagent reads:

- The produced-app code (or a curated subset — most relevant files).
- PLAN.md's project intent + the app mechanism from the app-type definition section.
- (Optional) Any prior cross-validation feedback (so improvements compound).

The subagent returns a flagged-issues list — short, specific, actionable.

## Briefing template

```
You are a cross-validation reviewer for a John-produced app. Your job: read the
produced code and the design intent, flag issues that deterministic guardrails
can't catch (subtle UX bugs, missing error states, security-via-obscurity,
mismatches between code behavior and stated intent).

## Project intent
<one paragraph from PLAN.md top>

## App mechanism (the produced app)
<one paragraph from PLAN.md app-type definition section>

## Code to review
<file paths to read; you can use Read tool>

## What to look for

1. Behavior mismatches: the code does something different from what the intent describes.
2. UX failure modes: what happens when the API errors? When the user submits malformed input? When the network is slow?
3. Subtle security issues: timing attacks, unsafe defaults, information leaks in error messages.
4. Maintenance hazards: code that will break in obvious ways when extended.

## What NOT to do

- Don't repeat deterministic guardrails (those already ran).
- Don't suggest "improvements" that aren't issues. Focus on real bugs/risks.
- Don't auto-fix; you're reviewing, not editing.

## Output
A short flagged-issues list. Each item: severity (low/medium/high), file, line, what the issue is, suggested action. Max 10 items; if you'd write more, the deterministic guardrails missed too much and we should re-run them.
```

## When to dispatch

- **Default opt-in**: not every phase. Wasteful on a build that's known to be incomplete.
- **Before deploy**: usually worth it. The cost (~$0.10-$0.30 per produced app) is fine for the production-readiness signal.
- **After a significant restructure**: dispatch to catch regressions.
- **On user request**: "is this ready to ship?" → run guardrails + cross-validation.

## When NOT to dispatch

- **During exploratory development**: churn is high; signal-to-noise is bad.
- **For text-only deliverables**: less code → less to validate; deterministic checks are enough.
- **When you've already cross-validated once and nothing changed**: results will be the same.

## Integration with the loop

Cross-validation fires near the end of a polish or pre-deploy phase. Step 5 of [[ralph-loop]] is the right insertion point:

1. Deterministic guardrails run, auto-fixes applied.
2. Cross-validation subagent dispatched.
3. Subagent returns flagged issues.
4. For high-severity items: pause loop, surface to user, decide before phase-done.
5. For medium/low: log in PLAN.md, may defer to a follow-up polish phase.

## Anti-patterns

- **Treating cross-validation as authoritative**: it's a sanity check, not ground truth. False positives happen; the user still owns the final call.
- **Running it every iteration**: cost explodes; signal flatlines.
- **Bundling it with deterministic guardrails into one "review" step**: confuses two different cost/reliability profiles. Keep them distinct.

## Source

A production app-builder's review-prompt template + reviewer-agent definition (an opt-in review codepath). Its retry-on-issues loop (review → if fail, dispatch back to coder with feedback → re-review) is a possible later adoption; John v1 stops at "surface to user."
