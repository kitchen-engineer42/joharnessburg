---
name: vertical-workflows
description: Author a Claude Code dynamic workflow to run a John fan-out phase at scale. Use this skill whenever a phase has dozens-to-thousands of uniform per-entry work units (extract every chunk, apply every rule to every chapter, render every slide) and the session is configured for workflows. It is John's vertical-axis execution engine — it fans out worker subagents off your context, adversarially cross-checks them before anything folds in, and wires every worker to John's event log. Reach for it instead of hand-dispatching subagents one wave at a time. If workflows are unavailable, fall back to inline dispatch per subagent-dispatch.
metadata:
  triggers:
    - vertical workflow
    - fan-out phase
    - run the extract phase
    - sweep at scale
    - workflow for this phase
    - parallel subagents at scale
    - cross-check the extraction
    - thousands of entries
---

# vertical-workflows

A dynamic workflow is a JavaScript script the Claude Code runtime executes in the background. You describe the work; you write the script with your Workflow tool; the runtime fans out subagents (up to 16 at once, 1,000 per run), keeps every intermediate result in *script variables* instead of your context, and hands you back only the final summary.

For John, that is the **vertical axis** — the hundreds-to-thousands of knowledge entries that each need the same kind of work, done in parallel. Until now you walked down each column by hand, placing one subagent at a time and holding every report in your own context. Past a few dozen entries your context floods. A workflow turns the whole column into an assembly line you write once.

**This skill teaches the *shape* of a John workflow, not the workflow API.** You already have the Workflow tool and know its JavaScript surface; what you need from John is *what a John-shaped fan-out looks like* — where the work-list comes from, how workers wire to the event log, what the cross-check stage checks, and what to return. Map that shape onto the live API yourself.

## The one idea that makes this safe: engine vs truth

John already separates **what's on disk (truth)** from **how the agent produced it (execution)**. The vertical axis writes per-entry **events** to `<project>/.john/events/<phase>/`, and `reduce_events.py` folds them into `<project>/.john/checkpoints/<phase>/state.json`. You never trust a tool-call assertion; you read the checkpoint.

A workflow is just a new **execution engine** under that contract:

- The workflow keeps results in variables for speed and a clean context.
- But its worker agents still **write events to `.john/events/<phase>/`** — the same files inline subagents write.
- After the run, you still run `reduce_events.py` and read the checkpoint. **That is truth, not the script's return value.**

This is why adoption is low-risk: nothing below the execution line changes. Same events, same reducer, same PLAN.md. See [[event-log-and-reducer]].

## When to author a workflow — and when not

If the session is in `ultracode`, your default leans toward orchestrating *everything* as a workflow. **Narrow that to fan-out work.** The decision is three-tier (it mirrors [[subagent-dispatch]]):

```
a few units, result needed in your context     → inline subagent (no workflow)
dozens–hundreds, uniform per-entry work         → ONE workflow run        ← this skill
thousands                                        → batched workflow runs per chunk-range,
                                                    all writing to the same event log
```

Author a workflow when the work is **uniform and high-fan-out**: "extract from every chunk," "apply every rule to every chapter," "render every slide." The per-unit task shape is identical; only the input differs. That homogeneity is exactly what a script loops over cleanly.

Do **not** reach for a workflow when:

- **It's a handful of units.** Spawning a whole runtime has overhead; just dispatch inline.
- **The work is coupled.** If unit A's output is unit B's input, it's serial, not a fan-out.
- **It needs the user mid-task.** A workflow takes no user input once it starts (only agent permission prompts can pause it). Anything needing sign-off belongs in the main session — see the constraints below.
- **The decision depends on your conversation with the user.** Workers start with fresh, isolated context; if the live conversation is load-bearing, do it inline.

A phase boundary — review results, update PLAN.md, ask the user — is the **seam *between* workflow runs**, never inside one. The docs' own guidance: "for sign-off between stages, run each stage as its own workflow." [[ralph-loop]] drives that seam.

## The John-shaped workflow — four stages

Describe these stages to your Workflow tool. They are responsibilities, not a fixed script.

**Stage 0 — get the work-list (an indexing agent).** The script itself has no filesystem or shell access; only agents read and write. So the first agent reads the phase's index — e.g. `<project>/.john/chunks/chunks_index.json` — and returns the list of work units (chunk IDs, rule×chapter pairs, slide specs). The script loops over what this agent returns.

**Stage 1 — fan out one worker per unit.** Dispatch the matching `agents/*.md` worker (e.g. `knowledge-extractor`) once per work unit. Brief each worker fully — workers inherit nothing from your conversation or PLAN.md ([[subagent-dispatch]] has the briefing checklist; it applies verbatim to workflow workers). Each worker **writes its events to `<project>/.john/events/<phase>/<work-unit>/...`** and returns a one-line digest. The script collects digests in a variable; the durable record is the event files on disk.

**Stage 2 — adversarial cross-check.** This is the prize, not an afterthought (see below). Independent reviewer agents re-judge the workers' output — `coverage-auditor` ("what did the extractor miss?") and `grounding-checker` ("is every entry traceable to source text?"). Ungrounded or low-confidence entries get dropped or flagged *before* they're treated as canonical. Route this stage to a stronger model than the extract stage if disagreements need adjudication.

**Stage 3 — return a compact summary.** The workflow returns only what you need to advance the phase: counts, coverage flags, `schema_observation`s, and failures. **Never** the per-entry payloads — those live in the event log; pulling them back into your context defeats the whole point.

## The quality upgrade is the real prize

Scale is the obvious win; **accuracy at scale is the bigger one, and it's John's moat.** The lesson John has been *asking for* in skill prose — "models can't reliably grade their own work; separate the doer from the judge" — a workflow finally *enforces* at scale, off your context and in parallel:

- **Coverage audit** — a reviewer re-reads a chunk and asks what the extractor missed (MECE enforcement). Use [[coverage-auditor]].
- **Grounding check** — every extracted entry must trace to source text; ungrounded ones are filtered before fold-in. Use [[grounding-checker]]. This is the `/deep-research` pattern ("claims that didn't survive cross-checking are filtered out") mapped from web sources to source chunks.
- **Confidence cross-validation** — for judgment-heavy work (e.g. rule application), have several independent agents vote and keep only what survives a majority.

"Draft from several angles, weigh them against each other" — applied to *knowledge*, which no single-pass extraction pipeline could afford.

## Constraints that bite (design around them)

- **No mid-run user input.** A workflow can't stop to ask the user. So when a worker finds the schema doesn't fit the corpus, it emits a `schema_observation` event (per [[knowledge-extraction]]) — it does **not** try to ask. You review those observations at the phase boundary, fold them into PLAN.md's Open Decisions, adjust, and re-run. Iteration becomes *between* runs, which is more auditable than mid-stream mutation.
- **No filesystem/shell from the script.** Hence Stage 0's indexing agent. Don't try to read disk in the script body.
- **16 concurrent / 1,000 per run.** For thousands of units, batch over chunk-ranges across multiple runs, each writing to the **same** event log. The append-only one-file-per-agent design means parallel and sequential runs compose without contention or corruption — run them, then reduce once at the end.
- **Cost.** A workflow spawns many agents — more tokens than a conversational pass. Route cheap, uniform work (extraction) to a smaller model and reserve the strong model for the judging stage. This is the in-Claude version of John's workerLLM tiering.
- **Resume is session-bound.** If you stop a run it resumes within the session (completed agents return cached results); but exit Claude Code and the workflow restarts fresh. **The event log is what survives a restart** — so the durable record is always disk, never the run's in-memory state.

## After the workflow returns

You are back in the main session ([[ralph-loop]]). Do not report the phase done from the script's summary alone:

1. Run `reduce_events.py` for the phase.
2. Read `<project>/.john/checkpoints/<phase>/state.json` — check `incomplete_chunks`, coverage, quarantined events.
3. Fold `schema_observation`s and failures into PLAN.md's Log + Open Decisions.
4. Re-dispatch any missing/failed units (a small follow-up workflow or inline) if coverage is short.
5. Then mark the phase done and advance.

## Fallback — when workflows aren't available

Workflows need Claude Code ≥ the version that ships them, a paid plan, and the feature enabled; the README documents the session setup the user is expected to have done. If you are **not** in a workflow-capable session (no ultracode, feature disabled, older Claude Code), do not block — **fall back to inline dispatch** per [[subagent-dispatch]]: fan out subagents in waves, have them write the same events, run the same reducer. Same events, same checkpoint, same PLAN.md. The execution engine changes; nothing below it does. Don't fork John's behavior on availability — just pick the engine you have.

## A worked sketch

`references/john-workflow-shape.md` has one end-to-end pseudocode sketch of the extract phase as a workflow. It is an **illustration of the shape, not the API** — read it for the stage structure and the event wiring, then write the real script with your Workflow tool.

## Cross-references

- [[subagent-dispatch]] — the three-tier decision and the briefing checklist; the inline fallback
- [[event-log-and-reducer]] — the contract every worker writes to; truth lives here, not in the script
- [[ralph-loop]] — launches the phase workflow, runs the reducer, advances PLAN.md at the seam
- [[phase-design]] — a fan-out phase declares its workflow + worker + cross-check agent up front
- [[knowledge-extraction]] — the per-chunk worker behavior (chunk echo, schema_observation)
- [[coverage-auditor]] / [[grounding-checker]] — the adversarial cross-check workers
