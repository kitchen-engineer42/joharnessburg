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

When N subagents are working in parallel on shared state, the naive approach (each subagent writes to a shared catalog file with a lock) is what kc_cli learned the hard way is fragile at scale. John uses **event log + reducer** instead — same shape that React/Redux and event-sourced systems use, ported to filesystem.

## The pattern in one diagram

```
Subagent A ── events/extract/chunks/A-001.json (append-only, A's own file) ─┐
Subagent B ── events/extract/chunks/B-002.json                              │
Subagent C ── events/extract/chunks/C-003.json                              ├──► reducer ──► .john/checkpoints/extract/state.json
...                                                                         │              (canonical)
Subagent N ── events/extract/chunks/N-200.json                             ─┘
```

- Each subagent writes only to its own event file. Zero contention.
- The reducer reads all event files for a phase, in deterministic order, and produces canonical state.
- Running the reducer twice yields the same output (idempotent).
- Canonical state is the read source for the next phase.

## Where files live

In the user's project, under `<project>/.john/`:

- `<project>/.john/events/<phase-name>/<work-unit-type>/<subagent-id>-<sequence>.json` — events. One file per subagent emission.
- `<project>/.john/checkpoints/<phase-name>/state.json` — canonical reduced state. Written by reducer.

Conventions:
- Subagent-id is a short identifier (e.g., `chunk-042` for "the subagent that processed chunk 042").
- Sequence is an integer or timestamp, in case one subagent emits multiple events.
- Event files are JSON; canonical state is JSON. Markdown if the canonical state is human-facing.

## Event shape (suggested)

```json
{
  "event_type": "<type-from-phase-spec>",
  "work_unit_id": "<unique id for the work unit>",
  "timestamp": "<ISO 8601>",
  "subagent_id": "<who emitted this>",
  "payload": {
    "<phase-defined>": "<phase-defined>"
  }
}
```

The `payload` shape is per-phase. The wrapping fields are universal.

Templates and phase-specific skills can override the schema as long as they:
- Keep one event = one self-contained record (no cross-references that require another event to interpret).
- Stay JSON-parseable.
- Carry enough metadata for the reducer to order/deduplicate them.

## How to write the reducer

The reducer is a script (Python, shipped via `scripts/reduce_events.py` in M2) that:

1. **Reads all event files** under `<project>/.john/events/<phase>/`.
2. **Sorts them deterministically** (by timestamp + subagent_id is a safe choice).
3. **Folds them into canonical state** using a per-phase fold function. The fold function's exact shape depends on what the phase is producing — for extraction, it concatenates entry lists and indexes by ID; for review, it tallies pass/fail; etc.
4. **Writes canonical state** to `<project>/.john/checkpoints/<phase>/state.json`.
5. **Returns idempotently**: running it twice with the same event set produces the same output, bit-for-bit.

Idempotency matters because the reducer may be invoked multiple times during a phase (e.g., after each wave of subagents) without state corruption.

## Failure handling

A subagent crashed mid-write? Its event file is partial or absent. Options for the reducer:

- **Strict**: refuse to fold if any expected event is missing. The phase isn't done; the user must re-dispatch the missing work units.
- **Lenient**: fold what's there, mark the missing work units in canonical state, and surface them in the phase's "Open decisions" or Log. Reducer's choice; document which.

John defaults to **lenient with explicit flagging** — the phase advances on best-effort, but PLAN.md gets a Log entry listing the missing units so they can be re-dispatched.

## Why this beats file locks

The file-lock approach (one shared catalog file, subagents lock-modify-unlock) hits two recurring failures:

1. **Lock held too long.** A subagent that pauses (LLM timeout, slow tool call) holds the lock, blocking everyone else. Eventually the lock-acquire timeout fires, but you've serialized parallel work.
2. **Starvation.** Some subagents repeatedly fail to acquire the lock and never make progress.

Both are structural to the lock pattern, not bugs. Event log + reducer removes both: every subagent has its own file, no contention, no waiting.

It also adds:
- **Replay.** Replay the reducer on a subset of events to see what canonical state would look like.
- **Audit.** Full history of every subagent's emissions, in order, on disk.
- **Recovery.** If a reducer bug corrupts canonical state, you can fix the reducer and re-derive state from events — events are immutable history.

## When NOT to use events

- **Single subagent.** If only one subagent is producing output for a phase, it can just write canonical state directly. Events buy nothing.
- **Strictly sequential pipelines.** If unit B requires unit A's canonical-state output, they're not really parallel. Run A, fold, run B.
- **State that's naturally one file** (e.g., a single `glossary.json` that grows with cross-subagent contributions). Even here, events + reducer often wins because of the audit trail, but a careful append-with-fsync pattern can suffice.

## Scaling thoughts

For thousands of work units, partition events into sub-directories per work-unit-type (`events/extract/chunks/`, `events/extract/figures/`, etc.) and make the reducer incremental (read only events newer than the last canonical state's timestamp). The script in M2 will support this; templates can extend.

## What the subagent skill says about events

Every John skill that dispatches subagents (knowledge-extraction, slide-rendering, app-feature-author, etc.) instructs the subagent to "emit events to `<project>/.john/events/<phase>/...`, do not write canonical state directly." That's the contract. The subagent doesn't need to know how the reducer works; it just emits events in the shape the phase expects.

## Cross-references

- [[subagent-dispatch]] — what triggers the fan-out that emits events
- [[ralph-loop]] — runs reducer at phase end and advances PLAN.md
- [[workspace-discipline]] — disk-is-truth includes checkpoint state
- [[phase-design]] — phases that fan out declare their event schemas
