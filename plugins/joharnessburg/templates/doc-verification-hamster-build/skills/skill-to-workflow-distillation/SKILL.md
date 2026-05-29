---
name: skill-to-workflow-distillation
description: REQUIRED Phase 6. Distill expensive SOTA rule-skills (Claude check.py on Opus) into cheap Python + tier-3/4 worker-LLM workflows that preserve accuracy within tolerance. The distilled workflow is the production artifact; the rule-skill is the SOTA reference. Use this skill when Phase 6 fires, when the user mentions distillation / workflow / cheap LLM / production cost, or when [[ralph-loop]] advances out of cross-doc verification. The "method over steps" caveat from kc_cli applies — don't over-specify cheap-LLM prompts.
metadata:
  triggers:
    - distill the rules
    - distill skills to workflows
    - distillation
    - distillation phase
    - skill to workflow
    - workflow distillation
    - phase 6 distillation
    - cheap llm workflow
    - tier 3 workflow
    - production workflow
---

# skill-to-workflow-distillation

After Phases 3 + 4 produce verified per-rule skills that work on SOTA Claude (Opus), Phase 6 distills each into a `<project>/workflows/R<id>/workflow.py` + per-step worker-LLM prompts that run on tier-3/4 cheap models with accuracy within tolerance of the SOTA reference. The distilled workflows are the **production artifact**; the original rule-skills remain as reference + as a fallback.

This phase is **required**, not optional. kc_cli's "skills as production mode" insight (a fully-tested rule-skill on SOTA is already production-viable) is true but expensive — projects ship distilled workflows by default. Skip distillation only as an explicit Open Decision when the cost-per-doc analysis specifically favors SOTA-only.

## Why distill at all

A rule-skill on SOTA Claude is the most accurate way to run a verification — Claude has world knowledge, can read nuanced prose, and handles edge cases gracefully. But:

- SOTA tokens are expensive. Verifying 1000 docs/day × 100 rules each = a lot of Opus.
- SOTA latency is real. A real-time verifier wants sub-second per rule.
- Distilled workflows can use tier-3/4 (Qwen-35B, DeepSeek, GLM-4-Air, etc.) with focused prompts that approach SOTA accuracy on narrow domains.

The distillation translates "Claude's general reasoning applied to this rule" into "a specific Python script + a few cheap LLM prompts that do just this rule." Loses some flexibility; gains a lot of cost + latency.

## The distilled workflow shape

```
<project>/workflows/R<id>/
├── workflow.py             # callable: workflow(document) -> {verdict, confidence, evidence, citation, evidence_method, source_presence}
├── prompt_extract.txt      # worker-LLM prompt for entity extraction step (if needed)
├── prompt_judge.txt        # worker-LLM prompt for judgment step (if needed)
└── README.md               # one-paragraph: what this workflow does, which rule-skill it distills
```

`workflow.py` has the same signature as `check_R<id>.py` from Phase 3 — the runtime swaps one for the other:

```python
def workflow(document):
    # 1. Deterministic: extract structural elements (regex / parsing)
    # 2. Maybe: tier-3 LLM call with prompt_extract.txt for fuzzy entities
    # 3. Deterministic: apply judgment logic (arithmetic / comparison)
    # 4. Maybe: tier-2 LLM call with prompt_judge.txt for nuanced verdict
    # 5. Return {verdict, confidence, evidence, citation, evidence_method, source_presence}
```

Workflows for cross-doc rules take `docs: dict[str, document]` instead — see [[cross-document-verification]].

Tier selection per step, per requirement_type:

| requirement_type | Suggested tier defaults | Why |
|---|---|---|
| quantitative | TIER4 (cheapest) for extraction (regex), no LLM for judgment | Pure arithmetic; cheap is enough |
| imperative / prohibitive | TIER3 for entity extraction, TIER3 for judgment | Semantic but narrow |
| conditional | TIER3 for branch detection, TIER2 for judgment | Branches need slightly more reasoning |
| definitional | TIER2 for matching against glossary | Often pairs with the glossary skill |
| anything cross-doc | One tier higher than above (e.g., TIER2 where per-doc would use TIER3) | Cross-doc reasoning is harder for cheap models |

Per-project overrides in `models.json` in the release bundle.

## The distillation loop per rule

For each rule that passed Phase 4 (and Phase 5 if cross-doc):

1. **Analyze the rule's `check_R<id>.py`**. Identify which parts are:
   - Deterministic (regex, arithmetic, parsing) — port directly to workflow.py.
   - LLM-bounded (semantic extraction, nuanced judgment) — extract the LLM-bounded part into a prompt template.
   - Mixed — split into a deterministic pre-processing step + an LLM step.

2. **Write `workflow.py`**: implement the deterministic parts in Python; insert worker-LLM call points for LLM-bounded parts via the platform's [[workerllm-runtime]] helper.

3. **Write the prompts** (`prompt_<step>.txt`). Critical: **method over steps**. kc_cli's caveat — don't write the prompt as a step-by-step recipe. Write it as a methodology + constraints + examples. Cheap LLMs handle methodology better than rigid recipes.

   Good prompt structure:
   ```
   You are verifying whether <rule plain-language>.
   The input is <doc excerpt>.
   Method: <how to think about this rule — 2-3 sentences>.
   Constraints: <what must be true / can't be true>.
   Examples (good and bad):
   <2-3 short examples>
   Return JSON: {verdict: "pass" | "fail" | "needs-review", confidence: 0-1, evidence: "<quoted text>"}
   ```

   Bad prompt structure (don't do this):
   ```
   Step 1: extract X.
   Step 2: check if X matches Y.
   Step 3: if X matches Y, return pass.
   Step 4: if not, check whether Z applies. If Z, return needs-review.
   Step 5: otherwise return fail.
   ```

   Cheap LLMs follow brittle steps worse than they follow methodology. The whole point of distillation is that the deterministic parts go in Python (where steps work); the LLM parts express methodology (where steps don't).

4. **Test the workflow** against the same labeled samples Phase 4 used. Measure accuracy_workflow vs accuracy_skill.

5. **Compute the delta**: `delta = accuracy_skill - accuracy_workflow`. Default tolerance: 0.02 (2%).
   - `delta ≤ tolerance` → workflow accepted; emit to `<project>/workflows/R<id>/`.
   - `delta > tolerance` → workflow needs revision; iterate (try higher-tier model, refine prompt, move more logic to deterministic Python).
   - Max 3 distillation iteration rounds.

6. **After 3 rounds, if still `delta > tolerance`**: fall back to running the rule-skill on SOTA in production. Log + surface as Open Decision; the user decides:
   - Ship the fallback (SOTA for this rule, cheap LLMs for others) — cost penalty for one rule.
   - Rework the rule (probably go back to Phase 3, simplify the rule's logic).
   - Drop the rule from v1.

7. **Emit results** to `.john/checkpoints/distillation/<rule-id>/accuracy_delta.json`:
   ```json
   {
     "rule_id": "R042",
     "accuracy_skill": 0.95,
     "accuracy_workflow": 0.93,
     "delta": 0.02,
     "tolerance": 0.02,
     "accepted": true,
     "iteration_count": 1,
     "tier_assignments": {"extract": "TIER3", "judge": "TIER3"},
     "fallback_to_skill": false
   }
   ```

## Subagent fan-out

Phase 6 fans out per rule. One subagent does one rule's distillation loop. Per [[subagent-dispatch]]:

- **Brief**: the rule's SKILL.md + `check_R<id>.py` + the rule's labeled samples + the accuracy tolerance + tier assignments to try + the "method over steps" caveat verbatim.
- **Output**: events to `.john/events/distillation/<rule-id>/` describing each iteration; final workflow.py to `<project>/workflows/R<id>/`.
- **Return digest**: `{accuracy_delta, iteration_count, accepted, fallback_to_skill}`.

## The skills-as-production option

Even though distillation is required by default, the user can pre-decide that distillation isn't worth it for this project. Conditions where this is reasonable:

- Low volume (< 100 docs/week) — SOTA cost is tolerable.
- Highly judgment-heavy rules (verification is inherently a Claude-level task) — distillation hits the floor anyway.
- Audit / regulatory work where every finding gets human review — confidence boost from SOTA outweighs cost.

Surface as Open Decision in PLAN.md BEFORE Phase 6 runs. If accepted, Phase 6 produces stub workflows that just call `check_R<id>.py` via the runtime — no distillation, no cheap-LLM prompts. The release bundle works the same; production just calls SOTA.

Default: distill. Skip only with explicit user sign-off.

## What this skill does NOT do

- It doesn't author check_R<id>.py — that's the overridden [[packaging]] in Phase 3.
- It doesn't test the rule's correctness — that's [[rule-testing]] in Phase 4 (workflows are tested for accuracy parity, not for rule correctness).
- It doesn't bundle the workflows into the release — that's the overridden [[packaging]] in Phase 8 (release-bundle mode).
- It doesn't pick the cheap-LLM provider — [[workerllm-runtime]] handles tier→model resolution from `models.json`.

## Cross-references

- [[rule-testing]] — provides the accuracy baseline (accuracy_skill) for delta computation
- [[packaging]] (overridden) — Phase 3 emits the check.py distillation starts from; Phase 8 bundles the workflows
- [[workerllm-runtime]] — runtime LLM integration; workflows call this for cheap-LLM steps
- [[confidence-system]] — workflows must report evidence_method + source_presence to enable confidence composite
- [[cross-document-verification]] — distillation for cross-doc rules uses the docs: dict signature
- [[corner-case-management]] — workflows do NOT include corner-case logic; the registry stays separate
- [[app-design-thinking]] (overridden) — runtime step 4 invokes the distilled workflow.py per rule
