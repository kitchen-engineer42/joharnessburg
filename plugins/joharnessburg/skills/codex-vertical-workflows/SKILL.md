---
name: codex-vertical-workflows
description: Execute John's high-volume vertical phases with native Codex subagents over the durable `.john/runs` and event contracts. Use for per-chunk extraction, coverage, grounding, per-entry generation, large uniform fan-out, retries, reconciliation, cancellation, or whenever shared John guidance mentions Claude dynamic workflows but the active provider is Codex.
---

# Codex vertical workflows

Keep the phase contract provider-neutral: immutable indexed inputs, stable item
IDs, typed receipts, unique events, audit barriers, and a verified checkpoint.
Use `john_run.py` to create and reconcile the durable ledger before treating
agent returns as completion.

1. Create the run from a deterministic work CSV.
2. Dispatch ordinary native subagents in bounded waves; default concurrency is
   6 and workers remain leaves (`max_depth=1`).
3. Use experimental `spawn_agents_on_csv` only when capability detection says
   it is available and the rows are uniform. Both engines consume the same
   manifest and receipt contract.
4. Record every attempt receipt, then reconcile. A successful thread is not a
   completed item until its referenced events exist, parse, match run/item
   identity, and contain the required terminal event.
5. Run extraction verification, coverage, grounding, adjudication, and typed
   reduction as separate stages with barriers. For extraction, invoke
   `reduce_events.py --require-extraction-audits` before phase advancement.

Use `john_run.py status`, `retry-csv`, and `cancel` for recovery. Never assign
deterministic indexing to one agent, and never let parallel code workers edit
the same files without disjoint ownership or an isolated worktree.
