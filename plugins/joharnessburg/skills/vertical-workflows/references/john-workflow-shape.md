# A John-shaped workflow — worked sketch (the extract phase)

**This is an illustration of the *shape*, not the workflow API.** You have the Workflow tool and know its real JavaScript surface — agent dispatch, fan-out/pipeline helpers, structured returns. Read this for the stage structure and the event wiring, then write the actual script with your tool. Don't copy the pseudocode literally; the names and call signatures here are stand-ins.

## The shape, in pseudocode

```text
WORKFLOW extract-sweep(project_root):

  # Stage 0 — an agent fetches the work-list (the script can't touch disk).
  index = agent(
    "Read {project_root}/.john/chunks/chunks_index.json and return the list
     of chunk IDs and their file paths as structured data.")
  chunks = index.chunks                       # e.g. ["chunk_001", ... "chunk_412"]

  # Stage 1 — fan out one knowledge-extractor per chunk. 16 run at once;
  # the runtime queues the rest. Each worker WRITES EVENTS to disk and
  # returns only a one-line digest (kept in a script variable, not your context).
  digests = fan_out(chunks, chunk_id =>
    agent(worker="knowledge-extractor", model="sonnet", prompt=brief(
      project_intent = "<one line, same as PLAN.md top>",
      job            = "Extract knowledge entries from ONE chunk.",
      work_unit      = "{project_root}/.john/chunks/{chunk_id}.md",
      schema         = "<the project schema fields, pasted>",
      write_events_to= "{project_root}/.john/events/extract/{chunk_id}/",
      return         = "a one-line digest: count + any flag",
      do_not         = "write checkpoints directly; ask the user; fan out further")))

  # Stage 2 — adversarial cross-check. Independent reviewers re-judge, in
  # parallel, off your context. Disagreements escalate to a stronger model.
  audit = fan_out(chunks, chunk_id => [
    agent(worker="coverage-auditor",  model="sonnet",
          prompt="Re-read {chunk_id}; what entries did the extractor miss?"),
    agent(worker="grounding-checker", model="sonnet",
          prompt="Is every entry from {chunk_id} traceable to source text? "
                 "Flag ungrounded ones; they must not fold in.")])
  # ungrounded / missed entries get flagged here, before the reducer treats
  # anything as canonical. The reviewers also write events (e.g. coverage_gap,
  # grounding_flag) to .john/events/extract/ so the reducer sees them.

  # Stage 3 — return a COMPACT summary only. Never the per-entry payloads.
  return {
    chunks_processed: chunks.length,
    entries_written:  sum(digests.count),
    coverage_flags:   audit.where(missed > 0),
    grounding_flags:  audit.where(ungrounded > 0),
    schema_observations: digests.schema_observations,
    failures:         digests.where(failed),
  }
```

## What happens back in the main session (NOT in the script)

The workflow's return is a convenience summary, not truth. In [[ralph-loop]]:

1. `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/reduce_events.py extract` — fold the events the workers wrote.
2. Read `<project>/.john/checkpoints/extract/state.json`: check `incomplete_chunks` (missing `chunk_complete`) and `chunks_missing_echo` (INFO; echo-only gap, not incomplete), `events_quarantined`, coverage.
3. Fold `schema_observations` + failures into PLAN.md (Log + Open Decisions).
4. Re-dispatch missing/failed chunks if coverage is short (a small follow-up run, or inline).
5. Mark the phase done; advance.

## Scaling past 1,000 units — batch into the same event log

```text
ranges = partition(chunks, size=400)          # 412 chunks fits one run; 4,000 wouldn't
for range in ranges:
    run extract-sweep over `range`            # each run writes to .john/events/extract/
reduce_events.py extract                       # ONE reduce over all runs' events
```

The append-only, one-file-per-agent event design means multiple runs (and the inline fallback) all write into the same `events/extract/` tree with zero contention. Reduce once at the end.

## Other phases, same shape

- **doc-verification rule sweep** — Stage 0 lists (rule × chapter) pairs; Stage 1 a `rule-tester` per pair writing a verdict event; Stage 2 a second agent re-judges a sample, disagreements escalate to a stronger model; reduce into a violations checkpoint.
- **slides-from-textbook** — Stage 0 lists slide specs; Stage 1 a renderer per slide; Stage 2 a checker verifies each slide against its source concept and the deck's aesthetic rule; only passing slides fold in.

The stages are invariant; only the worker agent, the work-unit shape, and the cross-check questions change per project.
