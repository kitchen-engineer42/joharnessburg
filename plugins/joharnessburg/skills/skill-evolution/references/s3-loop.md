# The worker-skill training loop, John-shaped

The procedure for training a workerLLM skill during a build. Pre-digested and complete — you do not need any external paper or library to run this; the concepts here are the John dialect of a well-corroborated recipe, run entirely on John's own machinery.

## Preconditions (all three, or don't start)

1. **A frozen worker**: a workerLLM (or fixed cheap-model + prompt combination) doing repeated, uniform work — extraction, verification, classification, per-entry generation.
2. **A scorer**: a deterministic or near-deterministic score per item (see `feedback-design.md` for choosing one). The template should have declared it; the corpus often supplies labels for free.
3. **A held-out split**: divide the scored items three ways — **train** (evidence), **selection** (the gate; never trained on), **test** (touched once, at the end, for the honest final number). Small is fine; disjoint is mandatory. With very few items, drop test and keep train/selection — but never gate on training items.

## The loop

Run it as a fan-out phase (workflow when available, inline dispatch otherwise — same events either way). All artifacts to `<project>/.john/events/<training-phase>/`; the reducer gives the audit trail.

```
for each epoch (2–4 is plenty):
  ROLLOUT    fan the frozen worker out over a train batch with the CURRENT skill;
             each item's events carry input ref, output, and score
  REFLECT    two analyses, separately (doer/judge separation):
             - failure analysis over the failed items: what recurring procedural
               error explains them? (batches expose patterns; single failures
               yield anecdotes — analyze groups, not items)
             - success analysis over passed items: what's working that an edit
               must not break?
  PROPOSE    a small set of bounded edits: append / insert-after / replace /
             delete — each a few lines, each tied to the pattern it fixes
  RANK+CLIP  keep only the top few edits per step (the edit budget; 2–4).
             Unbounded rewriting is the documented catastrophic path.
  GATE       apply the clipped edits → candidate skill; run the candidate on
             the SELECTION split. Accept only if STRICTLY better (ties reject).
             Rejected: record the edits + the score drop in a rejected-edits
             note; later proposals must consult it (don't re-propose failures).
  end of epoch: re-run a small sample under previous vs current skill; write
             durable cross-epoch lessons into a PROTECTED region of the skill
             (a fenced block step edits may not touch) — gated like any edit.
stop when:   accepts dry up (an epoch with no accepted edit), the budget is
             spent, or the selection score plateaus. Expect the total win to
             come from a HANDFUL of accepted edits.
```

## Event shapes

Use the standard envelope (`timestamp`, `subagent_id`) plus:

- rollout: `{"event_type": "rollout_scored", "item_id": ..., "score": 0.0-1.0, "skill_version": N}`
- gate: `{"event_type": "edit_gated", "edits": [...], "selection_score_before": x, "selection_score_after": y, "accepted": bool}`

The reducer folds these like any phase; the gate history doubles as the skill's training record.

## The trained artifact

The skill ships with a **provenance header** (a comment block at the top):

```
<!-- trained: 2026-06-12 | items: 40 train / 10 selection / 12 test
     scorer: <name + version of the scorer>
     baseline -> final (selection): 0.61 -> 0.83 | test: 0.79
     accepted edits: 3 (history: .john/events/skill-training-rules/) -->
```

The text stays compact (hundreds of tokens, not thousands), procedural, and inspectable. If training tripled its length, the loop was doing accumulation, not optimization — revisit the edit budget.

## What can go wrong (and the built-in answers)

- **The skill overfits the train items** → that's what the selection gate is for; the once-only test split tells you honestly at the end.
- **The judge gets gamed** (when the scorer is LLM-based) → see `feedback-design.md`; calibrate against ground truth periodically, and prefer verifying judges.
- **Improvements that read well but score worse** → the gate rejects them; that is the point of propose-and-test over self-editing.
- **The loop wants to edit something outside the worker skill** (the schema, the event contract, a core skill) → out of bounds; log a lesson with the appropriate scope instead.
