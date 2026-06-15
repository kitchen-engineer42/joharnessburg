---
name: phase-design
description: How to decide what phases this project actually needs, when you're sketching PLAN.md or revising it mid-flight. Use this skill whenever you need to design, evaluate, or revise phases for a John project — phases are John's horizontal axis, suggestions not enforcements, and getting them right is what makes ralph-loop work.
metadata:
  triggers:
    - design phases
    - what phases
    - decide phases
    - phase boundary
    - phase plan
    - subdivide phase
    - merge phases
    - drop a phase
    - insert a phase
---

# phase-design

You are layer-2 Claude designing phases for your user's project. The phases will live in their `<project>/PLAN.md` and drive every loop iteration via [[ralph-loop]].

**Phases are suggestions, not enforcement.** John's stance is phases-as-skills with template override room — the engine doesn't gate on phase boundaries; the floor is disk-verifiable artifacts (see [[workspace-discipline]]). You're designing scaffolding that helps work decompose cleanly, not laws that punish deviation. Templates may radically reshape the phase list; users may request changes mid-flight; corpora may surprise you. Stay wide.

A phase is a unit of work with three properties:

1. **An intent.** One sentence. "Extract all rules from the regulation corpus." "Build the runtime UI shell." If you can't say the intent in a sentence, the phase is too big or too unclear.
2. **Disk-verifiable done criteria.** Specific paths/files that must exist, with optional content checks. Not "feels done." Not "the agent says it's done." See [[workspace-discipline]]. For fan-out phases that produce knowledge entries, the done criteria should name an **expected entry count or range** (derived from the corpus survey, recorded in PLAN.md) — that number feeds the reducer's deterministic count gate (`reduce_events.py --expect-entries`, see [[event-log-and-reducer]]), which refuses phase advancement on a large shortfall.
3. **A clean compaction point.** When you finish a phase, the world is in a state where context could compact (or the session could restart) and the next iteration could pick up cleanly from disk.

Phases that don't have all three are not phases — they're tasks within a phase, or arbitrary stopping points, or something else.

## How many phases

For the knowledge/app-intent phases: typically 5-9 phases. The starter from John is now parse/probe → survey → infer intent / optional one-shot question batch → app blueprint / extraction plan → schema pilot → chunk/extract → rewrite → package. You can drop or merge — for example, a corpus that arrives pre-chunked skips "parse" and "chunk."

For the app phases (app building): depends entirely on what's being built. A static-output app (slides, a wiki, a portfolio) might be 3-4 phases; an interactive runtime (a game, a verifier) might be 6-10. The active template usually suggests phases; if not, design them with the user.

Total across both halves: usually 8-15 phases for a moderately ambitious project. Fewer means the matrix isn't decomposed enough; more means you've over-sliced and the iteration overhead dominates.

## Suggested knowledge phases

These are starting points, not requirements. The user or the active template overrides; treat the list below as a default to adapt, not a fixed sequence.

| # | Name | Why it might exist | Why it might not |
|---|---|---|---|
| 1 | parse | Raw input → markdown. PDFs need ppx, others need MarkItDown. | Corpus arrives as clean text already. |
| 2 | survey | Read the corpus shape before designing anything. | Tiny corpus where you can read all of it in one pass. |
| 3 | intent + app blueprint | Infer user intent, ask one product-question batch only if needed, then write `.john/brief/user_intent.json` and `.john/contracts/app_blueprint.json`. | Active template has already fixed the app shape and display contract. |
| 4 | extraction plan + schema-design | Write `.john/contracts/extraction_plan.json`, then derive internal knowledge format/schema from UI slots. | Knowledge IS already structured for the produced app. |
| 5 | chunk | Break large docs into tree of progressive-disclosure chunks. | Short-file-set corpus needs onion-*wrapper* (assemble) instead — see [[chunking]]. |
| 6 | schema pilot + extract | Pilot a diverse 10–20 chunk sample against the extraction plan and draft schema, then sweep chunks for knowledge entries. Subagent fan-out. | Tiny corpus can be extracted inline; active template may have deterministic extraction. |
| 7 | rewrite + cross-link | Progressive disclosure, dedup, cross-link. | Single-entry corpus. |
| 8 | package | Emit SKILL.md to `<project>/.claude/skills/` / `<project>/.agents/skills/` or another app data layer. | Knowledge goes somewhere else (e.g., a database). |

When deciding knowledge phases for a specific project, walk this list and ask "does this project need this phase?" Drop or merge accordingly.

## Long-docs vs short-file-sets: the onion decision

The chunking step has two opposite operations depending on corpus shape:

- **Onion-peeler** (default): one large document → tree of progressively-disclosed chunks. Break the doc down by header hierarchy + token budgets.
- **Onion-wrapper**: many small files → assemble them into a tree by domain/topic/folder. Same progressive-disclosure shape, opposite operation.

Quick rubric (decide in the **survey** phase, before chunking starts):

- One large document (textbook, regulation, long article) → peeler.
- Many small files (folder of 500 short memos, set of tweets, nested folder of snippets) → wrapper.
- Mixed (some long, some short, often the case for messy real-world input) → hybrid: peel the long ones, wrap the short ones, merge at chunk-tree boundaries.

This decision must be visible in PLAN.md's chunk phase (or whatever you name it). Don't defer it to the chunking skill — by the time chunking starts, the phase shape is already locked.

## Suggested app phases

These come from the conversation about app mechanism, not from a fixed list. But common shapes:

- **Static-output apps** (slide deck, portfolio, wiki): scaffold → assemble public modules from the display contract → render → preview-iterate → UI leak guardrails → publish.
- **Interactive runtime apps** (game, quiz, simulator): scaffold → wire core mechanics → seed content from UI-shaped knowledge → wire runtime LLM proxy (if needed) → polish → UI leak guardrails → deploy.
- **Tool apps** (verifier, parser builder): scaffold → wire I/O → wire core logic from skills → test on sample inputs → tune → UI leak guardrails → ship.

Each of those has 4-7 phases. The user and active template shape them.

## What makes a phase "good"

- **Intent fits one sentence.** No ambiguity about the goal.
- **Done criteria are observable on disk.** A test, a file, a count, a structural check. Not a feeling.
- **Vertical fan-out is acknowledged.** If the phase has 200 work units inside, the Subagent matrix says so up front. For a large uniform fan-out, the phase declares its **execution: Workflow yes/no + the worker agent + the cross-check agent + the model** — so the loop knows to launch one workflow run for the phase rather than hand-dispatch. See [[vertical-workflows]].
- **Boundary is a clean compaction point.** If context compacts at the boundary, the next iteration can resume cleanly by reading disk. For fan-out phases this boundary is also the **sign-off seam between workflow runs** — the only place a workflow-driven phase can take user input.
- **No dependencies on phases below it.** Phase 5 doesn't read state that Phase 7 produces.

## What makes a phase "bad"

- **"Refine until satisfied."** Open-ended, no done criterion, will eat unbounded context.
- **"Do X and also unrelated Y."** Two things; should be two phases.
- **"Make the schema better."** Vague intent, no observable check.
- **"Run the test suite."** That's a tool call, not a phase.
- **"Whatever's left."** Phases need shape. Catch-all phases become rolling chaos.

## Iteration on phases

PLAN.md's phase list is not frozen. The mechanics (how to subdivide/merge/drop/insert in PLAN.md, what to log, how to renumber) belong to [[plan-md-evolution]]; this section covers the *design judgment* about when iteration is the right move.

You can:

- **Subdivide** a phase mid-flight if it's bigger than expected (write the subdivision to Log + update PLAN.md).
- **Merge** two phases if their done criteria turn out to be linked.
- **Drop** a phase whose intent no longer applies (e.g., schema-design was already done by the template).
- **Insert** a phase you didn't anticipate (e.g., the corpus turned out to need a coreference-resolution step before extraction).

Each change is a PLAN.md edit + a Log entry. Don't silently change phases — they're the contract.

## Phases vs work units

Be precise:

- **Phase** = horizontal axis position. "Extract knowledge from all chunks."
- **Work unit** = one item the subagent matrix would hold. "Extract knowledge from chunk_042."

A phase has one intent and N work units. The work units are the vertical-axis dimension, handled by [[subagent-dispatch]].

## The "wide tunnel" principle

The most common mistake in phase design is over-specifying. The phase says "extract knowledge from chunks" — that's enough. Don't write "extract knowledge from chunks using a per-chunk LLM call with a 4-part schema and a temperature of 0.2." The skill bodies (e.g., [[knowledge-extraction]]) handle the methodology. The phase just sets the boundary.

If you find yourself writing recipe-style steps inside a phase definition, push those steps into a skill body or a script. Phases are *what*; skills and scripts are *how*.

## Cross-references

- [[plan-md-authoring]] — phases live in PLAN.md
- [[ralph-loop]] — what advances one phase at a time
- [[subagent-dispatch]] — vertical fan-out within a phase
- [[vertical-workflows]] — running a fan-out phase as one workflow run
- [[workspace-discipline]] — disk-verifiable done criteria
- [[plan-md-evolution]] — how to change phases mid-flight
