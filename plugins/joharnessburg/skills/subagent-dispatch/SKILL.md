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

## Three tiers: inline subagent, one scale-out run, or batched runs

Before *how* to dispatch, decide the **mechanism** by the size and shape of the fan-out:

```
a few units, result needed in your context       → inline subagent (dispatch in waves yourself)
dozens–hundreds, uniform per-entry work           → one provider-native scale-out run
thousands                                         → batched scale-out runs per chunk-range,
                                                       all writing to the same event log
```

A **scale-out run** fans out the same subagents, keeps their results off the main context, adversarially cross-checks them, and returns only a summary. In Claude Code, use a dynamic workflow per [[vertical-workflows]]. In Codex, use native waves over the durable run ledger per [[codex-vertical-workflows]]. This skill covers the inline tier and the briefing discipline all engines share.

In Claude Code, check dynamic-workflow availability before the first fan-out and follow [[vertical-workflows]] when it is misconfigured or absent. In Codex, create the run ledger first and dispatch native waves per [[codex-vertical-workflows]]. Both branches emit the same events and reduce to the same checkpoint. Record the engine choice in PLAN.md either way. The rest of this skill is the inline mechanism and the briefing rules.

## When to spawn a subagent

Three triggers, in order of clarity:

1. **Per-entry work that fits one context window per entry but doesn't fit yours in aggregate.** Classic case: 200 chunks to extract knowledge from. Each chunk is small; 200 of them through your context is not.
2. **Work where you want a context firewall.** Some tasks produce large intermediate state (a 50KB raw extraction) that you don't need in your context — you only need the digest. The subagent handles the raw; you see the summary.
3. **Work that benefits from a tighter persona or cheaper model.** A subagent can be given a narrow role ("you are a knowledge extractor; here is the schema; here is one chunk; emit entries to the event log and return a one-line digest") that focuses its output. John core delegates model selection to the active runtime; request the cheapest viable model when dispatching. Templates that need workerLLMs through external clients wire those themselves.

## When NOT to spawn a subagent

- **Tasks that fit your context easily.** Spawning has overhead. Don't dispatch for tiny work.
- **Tightly coupled work.** If unit A's output is unit B's input, they're not parallel — they're serial. Do them yourself or in a chain.
- **Work where the result depends on conversation context.** Subagents have their own context; if your conversation with the user is load-bearing for the decision, do it inline.
- **One-off judgment calls.** "Should we use schema X or schema Y?" — that's not a subagent task, it's an Open Decision the user owns. Write it to PLAN.md's Open Decisions section and stop. See [[plan-md-authoring]].
- **Work that needs user sign-off mid-task.** Keep it in the main session. This matters doubly for workflows — a workflow takes no user input once it starts, so anything needing a checkpoint belongs *between* runs, not inside one. See [[vertical-workflows]].

## Briefing a subagent

This is the most common failure mode in John sessions: under-briefing.

A subagent is a fresh agent with no idea about your project. It does NOT inherit:
- Your conversation with the user
- PLAN.md content (unless you tell it about it)
- The app-type definition decisions you made
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

**Parallel ≠ finished.** Running five subagents at once *feels* like fast progress, but a wave of green digests is not a completed phase — it's five claims you haven't checked. Before you advance, spot-review each return against its briefing: did the digest actually answer the job, do the event counts and IDs line up, does the output shape match the schema? When something's off, re-dispatching with a sharper briefing beats hand-patching the result. The firewall is a context boundary, not a progress bar.

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

**Tens of work units** (1-50): inline is fine — fan out in bounded waves through the active runtime's subagent mechanism. Wait for each wave, then dispatch the next. Below a dozen or so, a scale-out run's overhead usually isn't worth it.

**Hundreds** (50-500): use a provider-native scale-out run. Claude Code uses [[vertical-workflows]]; Codex uses [[codex-vertical-workflows]] and its run ledger. If the provider's scale engine is unavailable, announce the fallback and batch smaller work-unit ranges per subagent.

**Thousands** (500+): first rethink whether all work units are genuinely distinct. If they are, batch provider-native runs per chunk range, write every batch to the **same** event log, and reduce once at the end. Claude workflow limits and Codex ledger/reconciliation behavior stay provider-specific; the durable event contract does not.

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

John core uses the active runtime's default subagent model selection. An active template that uses workerLLMs for parallel work can ship a script that calls them through an OpenAI-compatible API. The pattern is the same: brief them tightly, have them emit events, run the reducer.

If a phase's work is well-defined enough for a cheap model, route it to one. If it requires judgment, use the strongest suitable available model. The boundary is taste; protect quality unless cost demands otherwise.

## Cross-references

- [[vertical-workflows]] — Claude Code's dynamic-workflow tier
- [[codex-vertical-workflows]] — Codex native waves and durable run ledger
- [[event-log-and-reducer]] — the coordination pattern for parallel subagents
- [[ralph-loop]] — what dispatches the fan-out from main loop
- [[phase-design]] — defining the work units up front in PLAN.md
- [[context-management]] — using subagents as context firewalls
- [[workspace-discipline]] — disk-is-truth applies to subagent outputs too
