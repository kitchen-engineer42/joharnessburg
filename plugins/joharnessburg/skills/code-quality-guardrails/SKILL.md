---
name: code-quality-guardrails
description: Apply deterministic quality checks to the code John produces — catch the 80% of issues (leaked API keys, hardcoded prod URLs, broken imports, missing dependencies, infinite spinners, dead error states, debug logs in production) without invoking the LLM at all; only fall back to LLM-driven repair for the residual edge cases. Use this skill whenever you're about to ship produced-app code, after a build phase completes, when the user mentions code quality / security review / production readiness, or when [[ralph-loop]] approaches a deploy phase. Cheap, fast, deterministic-first — guardrails are the floor before the polish.
metadata:
  triggers:
    - code quality
    - security check
    - leaked api keys
    - production readiness
    - lint
    - review the code
    - check the build
    - dependencies declared
    - guardrails
---

# code-quality-guardrails

The produced app is the deliverable. The user trusts it not to leak credentials, not to ship debug noise, not to crash on the first run. This skill is the discipline that makes that trust possible — adapted from skills2app's production quality patterns: inherit those methods, but skill-ify them rather than hardcoding a pipeline.

The principle: **deterministic checks first, LLM repair second.**

## The pattern

When you're about to ship produced-app code (end of a build/polish phase, before deploy, or any time the user signals "is this ready?"):

1. **Run the deterministic checks.** Grep for leaked secrets, check the build, verify imports resolve, lint, smoke-test the entrypoint. These are cheap, fast, predictable. They catch the bulk of real issues. See `references/common-guardrails.md` for categories.
2. **Apply automated fixes where possible.** Dependency missing → install. Import path wrong → fix the path. Leaked secret in a string → flag for user (do NOT auto-redact without confirmation; you might break a config). Many guardrails have obvious fixes; apply them.

## When a guardrail fires but the fix isn't obvious

Deterministic checks are good at pattern matching, not at semantic judgment. When a guardrail fires, decide:

1. **Check context.** Is `api_key` in a comment? In a `.env.example` placeholder? In a test config? In production? Same pattern, different decisions.
2. **If context is ambiguous, flag to user** with the match + line number. Don't auto-fix.
3. **If context is clear, fix and log.** "Leaked sk-* in committed file" is unambiguous; "missing dep in package.json that imports require" is unambiguous; fix.

Examples:
- Match: `api_key = "sk-test-placeholder-12345"` in `.env.example` → flag (might be intentional placeholder).
- Match: `import foo` but `foo` not in package.json → fix (always wrong if foo isn't a stdlib module).
- Match: `console.log("debug")` in `src/` production code → fix (almost always should be removed).
- Match: `localhost:3000` in deploy config → flag (might be intentional for staging).

If false-positive rates are high in a particular category, surface the pattern to the user — the guardrail itself may need adjustment.
3. **For residual issues, dispatch the cross-validation subagent.** A separate reviewer reads the produced code + the design intent (from PLAN.md), flags issues a grep can't catch (subtle UX bugs, missing error states, security-via-obscurity, etc.). See `references/cross-validation-pattern.md`.
4. **Surface to the user** anything still unresolved after steps 1-3.

The reason for the order: deterministic checks are cheap and reliable; LLM checks are expensive and probabilistic. Spend the cheap ones first; reserve the expensive ones for what they're uniquely good at.

## The four guardrail categories

`references/common-guardrails.md` has details; the categories:

- **Security**: leaked API keys / tokens / passwords; hardcoded production URLs / IPs; permissive CORS; unescaped user input rendered as HTML.
- **Code quality**: missing dependencies in package.json/requirements.txt; broken imports; unused imports flagged by linters; obvious syntax errors; type errors (if typed language).
- **UX**: error states unhandled (what if the API returns 500?); infinite spinners (no failure path); console.log/print statements that should be debug-only; placeholder text not replaced.
- **Deployment**: build succeeds (`npm run build`, `python -m build`, etc.); smoke test passes (entrypoint runs without crashing); Dockerfile (if applicable) builds.

For each category, the produced-app phase should run at least one check. Templates can ship more category-specific guardrails (e.g., a slide-deck template might check that the produced HTML opens cleanly in a browser).

## What "deterministic" means here

A guardrail is deterministic if:

- Running it twice on the same code gives the same result.
- It doesn't require LLM judgment to decide pass/fail.
- It can be expressed as a script + a threshold (or grep + a pattern).

Examples:

- ✓ `grep -r 'sk-[a-zA-Z0-9]{40}' produced-app/` (leaked secret pattern)
- ✓ `npm run build` returns exit 0
- ✓ `pylint --errors-only produced-app/` has zero errors
- ✗ "Is the UX confusing?" — requires judgment; not a guardrail, that's cross-validation territory.

When a guardrail fails, the fix is usually obvious (install the dep, escape the input, fix the import). Apply automatically when safe; surface to user when not.

## When deterministic checks aren't enough

Some issues require judgment:

- "The error message reads 'Error: failed to fetch' which is unhelpful for users."
- "The form has no loading state; on slow connections it looks broken."
- "The first paragraph repeats the title."

These are real bugs that grep won't catch. The **cross-validation pattern** (from skills2app's design): a separate reviewer subagent reads the produced code + design intent + a few key files, returns a flagged-issues list. Opt-in via a flag (skills2app gates it behind `AGENT_REVIEW_ENABLED`); slows the pipeline but catches what guardrails miss.

See `references/cross-validation-pattern.md` for the briefing and integration.

## Templates extend these

Different app types need different guardrails. A doc-verification template needs guardrails around compliance check accuracy; a slide deck template needs guardrails around in-browser render correctness. Templates ship additional category-specific guardrails as scripts under their `scripts/` directory; this skill teaches the framework, not the exhaustive list.

## When to NOT use this skill

- **During exploratory development** where churn is high and most "issues" are intentional (debug logs you'll remove later). Premature guardrails just create noise.
- **For pure-text deliverables** (a wiki, a knowledge base). These have no "build" — the relevant quality checks are different (typo scanning, broken link detection); use a different skill or template-specific guardrails.
- **For prototype phases** where the user explicitly says "rough draft, fix later." Wait for the polish phase.

## Scheduling guardrails in phases

**Deterministic checks:**
- Default: run at the end of each build/polish phase iteration, before phase-done is marked.
- Frequency: cheap enough to run every iteration; cost is sub-cent per pass.
- Controlled by: the phase's done criteria in PLAN.md (the phase says "build passes + lint passes + grep clean"; [[ralph-loop]] step 5 verifies before marking done).

**Cross-validation:**
- Default: opt-in, run once before deploy or release. Not every iteration.
- Frequency: ~$0.10-$0.30 per app per run depending on size. Budget one per ship decision.
- Controlled by: PLAN.md flag, template default, or explicit user request.

**Who decides opt-in:**
- **Template-level**: a template can set `cross_validation: enabled_by_default` in its `plan_md_template.md`; applies to every project using that template.
- **Project-level**: the user adds (or removes) the flag in PLAN.md's Open Decisions or phase definition.
- **Phase-boundary level**: when [[ralph-loop]] approaches a deploy or pre-release phase, check PLAN.md for the flag. If enabled, dispatch the cross-validation subagent; if not, proceed.

If cross-validation finds high-severity issues, pause the loop and surface them to the user — don't auto-fix security findings.

## Cost note

Deterministic checks are essentially free (grep, build, lint). Cross-validation costs Claude tokens per invocation — significant on a large produced app. Default: deterministic always; cross-validation opt-in per phase. Templates may make it default-on for production-bound app types.

## Cross-references

- [[app-design-thinking]] — informs *what* guardrails matter (different app archetypes have different risks)
- [[phase-design]] — where guardrails get scheduled (typically a polish or pre-deploy phase)
- [[workspace-discipline]] — observable done criteria; guardrail results ARE the verification
- [[subagent-dispatch]] — cross-validation runs in a subagent
- [[ralph-loop]] — typically fires near the end of phases, before phase-done is marked
- See `references/` for: deterministic-vs-LLM cost analysis, four-category guardrail catalog, cross-validation pattern
