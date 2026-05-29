# deterministic-vs-llm-fixes — when to use which

skills2app shipped ~15 deterministic guardrails plus a cross-validation flow. The split between them was load-bearing — using LLM judgment where a grep would do is wasteful, and trying to grep for issues that need judgment is wishful thinking. Get the split right.

## When deterministic wins

Use a deterministic check (script, grep, lint, build, smoke test) when:

- **The pattern is unambiguous.** "Is there a string matching `sk-[A-Za-z0-9]{40,}` in any committed file?" — yes/no, no judgment.
- **The fix is mechanical.** "If `package.json` is missing a dep that imports/requires reference, add it." — script can do this without an LLM.
- **You'll run it many times.** Build verification, smoke tests, lint — these run in every loop iteration. LLM cost would dominate.
- **False positives are tolerable.** A grep that flags "api_key = " comments alongside real leaks is fine; the user spends a second to dismiss the comment match.

Deterministic checks are essentially free (cents-per-thousand at most). Run them generously.

## When LLM judgment wins

Use a cross-validation subagent or in-line LLM check when:

- **The pattern requires meaning.** "Is the error message helpful for end-users?" — depends on what the message says, in context. No grep handles this.
- **The check is one-off.** A pre-deployment sanity read of the produced code, run once per project. LLM cost is bounded.
- **Subtlety matters.** "Does this UX have a graceful failure path?" — depends on what "graceful" means in this app's context.
- **You want a second pair of eyes.** Cross-validation as a sanity gate before shipping; the LLM reading the code didn't write it, so it spots different things.

LLM checks cost real money at scale. Budget them; don't make them every-phase defaults.

## The hybrid

Most produced apps benefit from both:

- **Phase 1 (during a build/polish phase)**: run deterministic guardrails after each significant change. Cheap, fast, catches most issues.
- **Phase 2 (before shipping/deploy)**: run cross-validation once. Slower, more expensive, catches what deterministic missed.

Roughly: deterministic checks every iteration; cross-validation once per ship.

## What about auto-fix vs flag-for-user

Even when a guardrail fires, you have two options:

- **Auto-fix**: when the correct fix is obvious and low-risk (add a missing dependency, fix a typo'd import path, escape unescaped user input rendering). Apply the fix, log it in PLAN.md.
- **Flag for user**: when the fix is judgment-dependent or destructive (replace what looks like a leaked API key — it might be a placeholder; remove a hardcoded URL — but it might be intentional for local dev). Surface the finding; let the user decide.

Default to flag-for-user when in doubt. Auto-fixing the wrong thing is worse than not fixing at all.

## Costs from skills2app's experience

Production skills2app's pattern (per `to-skills-backend/docs-internal/` and `skills2app/utils/`):

- Build + smoke test on every produced app: always-on, ~30s per cycle. Catches 60-70% of issues.
- Optional cross-validation: 1-3 minutes per app, ~$0.10-$0.30 in tokens. Catches another 20%.
- Manual review by the developer: the last 10%. Always.

John inherits this shape but doesn't enforce specific costs — templates decide for their domain.

## Source

skills2app's `utils/agent_backends/claude.py` (the cross-validation agent definition) + its `utils/prompts/review.py` (the review prompt template) hold these inherited patterns.
