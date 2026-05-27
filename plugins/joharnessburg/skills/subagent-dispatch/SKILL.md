---
name: subagent-dispatch
description: When and how to spawn subagents for the vertical axis of John's work matrix. Subagents handle per-entry parallel work (extract this chunk, author this skill, generate this slide) so your main context stays clean and the work scales.
metadata:
  triggers:
    - spawn subagents
    - fan out
    - parallel work
    - subagent
    - vertical axis
---

# subagent-dispatch

Subagents are the vertical axis. Your main session is the horizontal axis. Getting the line between them right is what makes John work at hundreds of knowledge entries instead of melting your context.

## When to spawn a subagent

Three triggers, in order of clarity:

1. **Per-entry work that fits one context window per entry but doesn't fit yours in aggregate.** Classic case: 200 chunks to extract knowledge from. Each chunk is small; 200 of them through your context is not.
2. **Work where you want a context firewall.** Some tasks produce large intermediate state (a 50KB raw extraction) that you don't need in your context — you only need the digest. The subagent handles the raw; you see the summary.
3. **Work that benefits from a tighter persona or cheaper model.** A subagent can be given a narrow role ("you are a knowledge extractor; here is the schema; here is one chunk; emit entries to the event log and return a one-line digest") that focuses its output. Per the user's spec §8.3, John core delegates model selection to Claude — Sonnet/Haiku are routinely used for subagents per task requirement, and you should request the cheapest viable model when dispatching. Templates that need workerLLMs (SiliconFlow, DeepSeek, etc. via cheap LLM clients) wire that themselves; John core uses Claude's tier defaults.

## When NOT to spawn a subagent

- **Tasks that fit your context easily.** Spawning has overhead. Don't dispatch for tiny work.
- **Tightly coupled work.** If unit A's output is unit B's input, they're not parallel — they're serial. Do them yourself or in a chain.
- **Work where the result depends on conversation context.** Subagents have their own context; if your conversation with the user is load-bearing for the decision, do it inline.
- **One-off judgment calls.** "Should we use schema X or schema Y?" — that's not a subagent task, it's an Open Decision the user owns. Write it to PLAN.md's Open Decisions section and stop. See [[plan-md-authoring]].

## Briefing a subagent

This is the most common failure mode in John sessions: under-briefing.

A subagent is a fresh Claude with no idea about your project. It does NOT inherit:
- Your conversation with the user
- PLAN.md content (unless you tell it about it)
- The four-structures decisions you made
- Previous extraction results
- Project taste / conventions / glossary

You MUST brief every subagent with the context it needs to do its job. If you don't, the subagent will do something plausible-but-wrong, the reducer will fold nonsense into canonical state, and you'll spend the next iteration cleaning up.

**The briefing checklist:**

1. **What the project is.** One paragraph. Same intent line that's at the top of PLAN.md.
2. **What this subagent's specific job is.** One sentence. Narrow.
3. **The work unit.** The actual chunk / entry / item to be processed.
4. **The schema / output shape.** What does the result look like? What fields? What constraints?
5. **Where to write output.** Event log path: `<project>/.john/events/<phase>/<work-unit-type>/<subagent-id>-<timestamp>.json`. See [[event-log-and-reducer]].
6. **What to return to you.** A short digest, not the full work product. "Extracted 7 entries, IDs in event log, one ambiguity flagged."
7. **What NOT to do.** "Don't write to `<project>/.john/knowledge/` directly; only via events." "Don't ask the user; if blocked, return the question in your digest."

Underspec any of those and you'll regret it. Over-brief is fine — the subagent reads it once at the top and ignores what's not relevant.

## The horizontal × vertical matrix in practice

Inside one phase, the fan-out shape:

```
Phase: extract (horizontal position N)
  Work units (vertical):
    chunk_001 ─► subagent ─► events ─┐
    chunk_002 ─► subagent ─► events ─┤
    chunk_003 ─► subagent ─► events ─┼─► reducer ─► .john/checkpoints/extract/state.json
    ...                              │
    chunk_200 ─► subagent ─► events ─┘
```

You orchestrate: decide the work units, brief each subagent, wait for events, run reducer, check canonical state, advance PLAN.md.

The subagents never talk to each other directly. They only emit events. The reducer is the only thing that reads all events together. This is the [[event-log-and-reducer]] pattern.

## Scaling concerns

**Why thousands actually scale**: the produced app has a *structure* where knowledge entries fit like *content* in a uniform way. Work units are homogeneous — "extract from chunk 042" is the same task shape as "extract from chunk 419"; the reducer folds them with identical logic. As long as the entry structure is uniform, the orchestration cost doesn't grow non-linearly with entry count. That's the architectural reason event-log+reducer beats file-locks at scale — see [[event-log-and-reducer]].

**Tens of work units** (1-50): fan out in waves of ~10 concurrent. Wait for each wave, then dispatch the next. Manageable through Claude Code's Task tool.

**Hundreds** (50-500): batch into smaller work-unit chunks per subagent (e.g., "process chunks 100-110" rather than one subagent per chunk). Keeps total subagent count manageable while still parallel.

**Thousands** (500+): rethink whether all work units are genuinely distinct (often they can be deduplicated or clustered upstream). If still genuinely thousands, partition the event log into sub-directories per work-unit-type and let the reducer handle each partition incrementally. Cost considerations usually limit production runs to 50-300, but the architecture handles thousands without re-engineering.

## Returning condensed digests

**The firewall is the point.** A subagent's large intermediate work (raw extraction, error traces, verbose reasoning, parsed PDFs, big embeddings) stays entirely in the subagent's context. Your main context only ever sees the subagent's final message — the digest. This is your strongest single lever for context budget. Design subagent tasks to *deliberately produce* large intermediate state you don't need; the firewall keeps it out of your way.

So have subagents return:
- Counts, IDs, paths (citations)
- Flagged ambiguities (one line each, "see event abc-123 for detail")
- Yes/no signals ("schema fit: yes / mostly / no")

NOT:
- Full text of what they extracted
- Multi-paragraph explanations
- Raw error traces (those go to `<project>/.john/trace/`)

If you find yourself needing the full content a subagent produced, you have two options: (a) read the event log file directly via Read tool, (b) re-spawn a subagent with a more pointed question. Don't ask the original subagent to "tell you more" — its context is gone.

## Cheaper-model subagents

Not yet a v1 default — John core uses Claude's default subagent model selection. But: an active template that uses workerLLMs (SiliconFlow, DeepSeek) for parallel work can ship a script that calls those providers via OpenAI-compatible API. The pattern is the same: brief them tightly, have them emit events, run the reducer.

If a phase's work is well-defined enough for a cheap model, route it to one. If it requires judgment, use Claude. The boundary is taste; lean toward Claude unless cost demands otherwise.

## Cross-references

- [[event-log-and-reducer]] — the coordination pattern for parallel subagents
- [[ralph-loop]] — what dispatches the fan-out from main loop
- [[phase-design]] — defining the work units up front in PLAN.md
- [[context-management]] — using subagents as context firewalls
- [[workspace-discipline]] — disk-is-truth applies to subagent outputs too
