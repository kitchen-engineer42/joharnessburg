---
name: event-log-and-reducer
description: The append-only event log + deterministic reducer pattern John uses to coordinate parallel subagent work on shared state. Each subagent emits its own event files; one reducer folds all events into canonical state. Beats file locks, scales to thousands of work units.
metadata:
  triggers:
    - event log
    - reduce events
    - coordinate subagents
    - shared state
    - reducer
---

# event-log-and-reducer

When N subagents are working in parallel on shared state, the naive approach (each subagent writes to a shared catalog file with a lock) is what KC (a sibling verification harness) learned the hard way is fragile at scale. John uses **event log + reducer** instead — same shape that React/Redux and event-sourced systems use, ported to filesystem.

## The pattern in one diagram

```
Subagent A ── events/extract/chunks/A-001.json (append-only, A's own file) ─┐
Subagent B ── events/extract/chunks/B-002.json                              │
Subagent C ── events/extract/chunks/C-003.json                              ├──► reducer ──► .john/checkpoints/extract/state.json
...                                                                         │              (canonical)
Subagent N ── events/extract/chunks/N-200.json                             ─┘
```

- Each subagent invokes `emit_event.py`; the writer assigns a unique filename and atomic envelope. Zero contention and retries never overwrite history.
- The reducer reads all event files for a phase, in deterministic order, and produces canonical state.
- Running the reducer twice yields the same output (idempotent).
- Canonical state is the read source for the next phase.

## Where files live

In the user's project, under `<project>/.john/`:

- `<project>/.john/events/<phase-name>/<work-unit-type>/<subagent-id>-<sequence>.json` — events. One file per subagent emission.
- `<project>/.john/checkpoints/<phase-name>/state.json` — canonical reduced state. Written by reducer.

Conventions:
- Phase, work-unit, agent, and audit-run IDs use letters, digits, `_`, and `-`, beginning with a letter or digit.
- Event files are JSON; canonical state is JSON. Markdown if the canonical state is human-facing.
- Producers do not choose filenames. Pipe one JSON object through the shipped atomic writer:

```bash
printf '%s\n' '{"event_type":"chunk_complete","chunk_id":"chunk-042"}' | \
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/emit_event.py" \
    --phase extract --work-unit-id chunk-042 \
    --agent-id extractor-7 --audit-run-id run-20260709
```

The writer injects a UUID `event_id`, UTC `timestamp`, `agent_id`, and `audit_run_id`. Raw events are append-only.

## Event shape — one valid approach

The only hard requirements (everything else is taste):

1. One event = one self-contained record. No references that require another event to interpret.
2. JSON-parseable.
3. Enough metadata for the reducer to order and deduplicate (timestamp + a sender id is the usual minimum).

A **minimal** schema that satisfies the rules:

```json
{ "timestamp": "ISO 8601", "subagent_id": "string", "payload": {} }
```

A **richer** schema (used in many knowledge-extraction templates) — useful when you need to query the event log by type:

```json
{
  "event_type": "entry_extracted",
  "work_unit_id": "chunk_042",
  "timestamp": "2026-05-21T10:42:33Z",
  "subagent_id": "sub-xx7f3a",
  "payload": { "entry_ids": ["e_001", "e_002"], "notes": "..." }
}
```

Templates and phase-specific skills define their own schemas freely, as long as the three requirements above hold. Neither shape above is canonical — wide tunnel.

## How to write the reducer

The reducer is a script (Python — John ships `scripts/reduce_events.py`) that:

1. **Reads all event files** under `<project>/.john/events/<phase>/`.
2. **Sorts them deterministically** (timestamp + subagent_id is a safe primary key). At thousands-of-events scale, clock skew or identical timestamps happen — `${CLAUDE_PLUGIN_ROOT}/scripts/reduce_events.py` handles the tiebreaker. If your fold function depends on strict ordering, review the tiebreaker before trusting the result.
3. **Folds them into canonical state** using a per-phase fold function. The fold function's exact shape depends on what the phase is producing — for extraction, it concatenates entry lists and indexes by ID; for review, it tallies pass/fail; etc.
4. **Writes canonical state** to `<project>/.john/checkpoints/<phase>/state.json`.
5. **Returns idempotently**: running it twice with the same event set produces the same output, bit-for-bit.

Idempotency matters because the reducer may be invoked multiple times during a phase (e.g., after each wave of subagents) without state corruption.

## Phase-boundary checks: count gate + disk reconciliation

`reduce_events.py` ships two deterministic checks for the end of a phase — zero tokens, pure file walking:

- **Count gate** — `--expect-entries N` or `--expect-entries MIN-MAX`. Counts unique entry ids claimed in the phase's events (`payload.entry_id` / `payload.entry_ids`, deduplicated, so corrective re-emits don't inflate it) against the expectation from PLAN.md. The *caller* supplies the number — the script never parses PLAN.md. Below ~90% of the minimum → **exit 3**: do not advance the phase. Small drift or overage → warning, exit 0. The checkpoint is still written on failure — the gate blocks *advancement*, not state derivation. Always prints actual-vs-expected so the number lands in the transcript.
- **Disk reconciliation** — `--verify-knowledge [--knowledge-dir PATH]`. Cross-checks knowledge entries on disk against claimed entry ids: **orphans** (on disk, no claiming event) and **missing-on-disk** (claimed, no entry dir). Strictly report-only — it warns and never mutates or deletes. The orphan policy is *warn, never fix*: a hand-added entry is legitimate; flag it, let a human decide. And missing-on-disk after the rewrite phase is often legitimate dedup, not corruption — the warning says so.

Why a deterministic floor when [[vertical-workflows]] already has LLM cross-check agents: the failures these catch are *infrastructure* failures — a session killed mid-write, a worker whose events never landed, 16 concurrent writers, a full disk. No amount of model intelligence prevents those, and an LLM auditor can sincerely report a truncated phase as complete. Run both checks together at every phase boundary (one disk walk serves both); [[ralph-loop]] shows the invocation.

Every gated (non-dry-run) reduce also **persists its verdict** to `<project>/.john/checkpoints/<phase>/gates/<ts>.json` (append-only history: gate status, counts, verify results, exit code). This makes phase-boundary outcomes readable from the workspace itself — the process scorecard (`${CLAUDE_PLUGIN_ROOT}/scripts/process_scorecard.py`) reads them when assessing how a run actually went.

Extraction has an additional opt-in CLI gate that shipped extraction guidance always enables: `--require-extraction-audits`. For each completed chunk it selects the latest coverage and grounding summaries newer than the latest candidate mutation, requires zero coverage gaps, zero weak/ungrounded entries, and matching checked-entry counts. Failure exits 4 and excludes the entire chunk from `quality_gate.accepted_entry_ids`; the additive `quality_gate` object and reasons remain in checkpoint state. Omitting the flag preserves generic legacy reduction.

## Failure handling

A subagent crashed mid-write? Its event file is partial or absent. Options for the reducer:

- **Strict**: refuse to fold if any expected event is missing. The phase isn't done; the user must re-dispatch the missing work units.
- **Lenient**: fold what's there, mark the missing work units in canonical state, and surface them in the phase's "Open decisions" or Log. Reducer's choice; document which.

John defaults to **lenient with explicit flagging** for generic reduction. Shipped extraction guidance is stricter: its required audit gate must pass before the phase advances.

## Validation + quarantine

Subagents writing JSON events sometimes produce unparseable files — most commonly when string values contain unescaped inner quotes (a real ~10% defect rate is observable on Chinese-language content). The reducer handles this by **quarantining** unparseable events:

1. On read, `json.loads(file.read_text())` is wrapped in a try/except.
2. On parse failure: if the file was modified within the last few seconds, it is treated as a **write in progress** (concurrent writers are normal) — skipped with a warning, NOT quarantined, and picked up by the next reduce. Only *stale* unparseable files move to `<project>/.john/events/<phase>/_quarantine/<original-filename>` with a sibling `<original-filename>.parse_error.txt` carrying the exception message.
3. Continue reducing the remaining events.
4. At end-of-phase: log "N events quarantined" (and any fresh files skipped) prominently in the reducer's stdout output.

This is a **lenient + surfaced** policy: the phase doesn't fail outright (one bad event shouldn't kill 199 good ones), but the user knows immediately how many events were lost and where to inspect them.

**For agents emitting events**: see the JSON-discipline section in your agent role. Prefer `json.dumps()` and pipe the resulting object through `emit_event.py`; do not handcraft a shared or retry-prone filename.

## Why this beats file locks

The file-lock approach (one shared catalog file, subagents lock-modify-unlock) hits two recurring failures:

1. **Lock held too long.** A subagent that pauses (LLM timeout, slow tool call) holds the lock, blocking everyone else. Eventually the lock-acquire timeout fires, but you've serialized parallel work.
2. **Starvation.** Some subagents repeatedly fail to acquire the lock and never make progress.

Both are structural to the lock pattern, not bugs. Event log + reducer removes both: every subagent has its own file, no contention, no waiting.

The deeper reason event-log+reducer is John's default isn't throughput — typical runs are 50-300 entries (cost-bounded). The reason is **architectural ceiling**: even at 50 entries, locks are fragile under any unusual load (a slow tool call, a retry); event-log isn't. Choosing this pattern from the start gives auditability, recoverability, and freedom to scale to thousands without re-architecting.

It also adds:
- **Replay.** Replay the reducer on a subset of events to see what canonical state would look like.
- **Audit.** Full history of every subagent's emissions, in order, on disk.
- **Recovery.** If a reducer bug corrupts canonical state, you can fix the reducer and re-derive state from events — events are immutable history.

## When NOT to use events

- **Single subagent.** If only one subagent is producing output for a phase, it can just write canonical state directly. Events buy nothing.
- **Strictly sequential pipelines.** If unit B requires unit A's canonical-state output, they're not really parallel. Run A, fold, run B.
- **State that's naturally one file** (e.g., a single `glossary.json` that grows with cross-subagent contributions). Even here, events + reducer often wins because of the audit trail, but a careful append-with-fsync pattern can suffice.

## Scaling thoughts

For thousands of work units, partition events into sub-directories per work-unit-type (`events/extract/chunks/`, `events/extract/figures/`, etc.) — the shipped script already reads nested sub-directories. Incremental folding (read only events newer than the last checkpoint) is a template extension: the shipped script deliberately re-reads the full event set every run, which is what makes it idempotent and recovery-safe.

## What the subagent skill says about events

Every skill that dispatches subagents — core's [[knowledge-extraction]], and template phase skills (rule-extraction, slide-rendering, and the like) — instructs the subagent to "emit events to `<project>/.john/events/<phase>/...`, do not write canonical state directly." That's the contract. The subagent doesn't need to know how the reducer works; it just emits events in the shape the phase expects.

## Workflow agents are also event producers

When a fan-out phase runs as a dynamic workflow ([[vertical-workflows]]) instead of inline dispatch, **nothing here changes.** The workflow's worker agents write the same events to `<project>/.john/events/<phase>/`; you still run this reducer afterward; the checkpoint is still truth. The workflow keeps results in *script variables* for a clean context, but those are a convenience — the durable record is the event files on disk.

Two consequences worth holding onto:

- **The event log, not the runtime, is what survives.** Workflow resume is session-bound: stop a run and it resumes within the session, but exit Claude Code and the workflow restarts fresh. The event log isn't session-bound — it survives restarts, compaction, and crashes. So a workflow-driven phase is durable for the same reason an inline one is: the events are on disk, and the reducer can re-derive state from them at any time.
- **16 concurrent writers, zero contention — by design.** A workflow runs up to 16 agents at once, all potentially writing state. The one-file-per-agent append-only design (the whole reason John chose event-log over file-locks) already eliminates the write contention that naive parallel adoption would hit. John pre-solved the concurrency hazard; running multiple workflow *batches* into the same event tree is equally safe — reduce once at the end.

## Cross-references

- [[subagent-dispatch]] — what triggers the fan-out that emits events
- [[vertical-workflows]] — workflow workers are event producers too; truth lives here, not in the run
- [[ralph-loop]] — runs reducer at phase end and advances PLAN.md
- [[workspace-discipline]] — disk-is-truth includes checkpoint state
- [[phase-design]] — phases that fan out declare their event schemas
