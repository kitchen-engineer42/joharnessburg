---
name: using-john
description: Top-level orientation for John (joharnessburg). Read this skill at the start of every John session and re-read it after every context compaction. Use it whenever the user mentions John, joharnessburg, ralph-loop, knowledge phases, app phases (or their legacy nicknames 2skills/2app), knowledge engineering, or asks you to do knowledge-dense app building. It tells you what John is, the shape of the user's working state, where to look, and what to do at each phase of work — without it, you'll likely under-trigger the other John skills.
---

# using-john

You are running in a Claude Code or Codex session where the **joharnessburg** plugin is loaded. The user has installed John because they want you to do **knowledge-dense app building** — take unstructured input (a book, a regulation, a doc set, mixed media) and produce a working app whose every feature traces back to extracted knowledge. John is a harness; you are the agent it harnesses.

This skill is your orientation. Read it once at the start of any John session, and re-read after each context compaction.

## What John actually is

A thin layer of skills, hooks, and a small toolkit on top of Claude Code or Codex. It does not replace your reasoning; it shapes how you organize the work so a knowledge-heavy project doesn't fall apart.

The shape John imposes is a **two-axis matrix**:

- **Horizontal axis** (phases): the work moves left-to-right through a small number of phases, one at a time. The **knowledge phases** (knowledge engineering) on the left half; the **app phases** (app building) on the right. You advance one phase before starting the next.
- **Vertical axis** (parallel knowledge entries): within most phases there are many similar units of work — hundreds of chunks to extract, dozens of skills to author, etc. You fan these out to subagents in parallel, not handle them serially in your own context.

Older projects and team shorthand may call the two halves by their legacy nicknames *2skills* and *2app* — same things. Same session, same memory, one PLAN.md spanning both halves.

**Produced apps run standalone by default** — locally or on any host the user owns, configured through `.env`, with no external auth/billing/telemetry platform assumed. Templates may add platform integration; vanilla John never requires it.

## The user's working state — where to look

Everything John writes lives in the **user's project directory** (the current working directory when this session was started). You write here, not into John's plugin install location.

- `<project>/PLAN.md` — the durable plan. Read this first. Has phases, subagent assignments, the app-type definition section, open decisions, an append-only log. It is the source of truth across context compactions.
- `<project>/CLAUDE.md` — Claude Code project memory. If absent, John's init creates a starter; if present, read it for project-specific conventions.
- `<project>/AGENTS.md` — Codex project memory. If absent, John's init creates a starter; if present, read it for project-specific conventions.
- `<project>/.john/` — working state. Hidden, ephemeral-ish. Contains `workspace.json` (active template + current phase), `input/` (user materials), `parsed/`, `chunks/`, `knowledge/`, `events/` (append-only logs), `checkpoints/`, `trace/` (offloaded large tool results).
- `<project>/.claude/skills/` — deliverable skills for Claude Code.
- `<project>/.agents/skills/` — deliverable skills for Codex.

If none of this exists yet, John hasn't been initialized for this project. In Claude Code, suggest `/john:init <path-to-input>`; in Codex, use the `init-workspace` skill.

## How to behave in a John session

Six rules. Internalize these — every other John skill builds on them.

1. **Read PLAN.md first, every iteration.** Cheap, keeps you honest. The plan is the contract. And when you start a phase, *invoke* the skills its "Skills to invoke" line names — actually load them; don't work from your memory of what they probably say.
2. **Advance one phase at a time.** Don't try to finish multiple phases in one pass; the matrix is sequential horizontally.
3. **Spawn subagents for vertical-axis parallel work.** Per-chunk extraction, per-entry rewrite, per-skill authoring — these are subagent jobs, not main-agent jobs. See [[subagent-dispatch]]. For a large uniform fan-out, choose the active provider's scale engine: Claude Code dynamic workflows via [[vertical-workflows]], or Codex native waves and the durable run ledger via [[codex-vertical-workflows]]. Both write the same events and checkpoints. Record the engine choice in PLAN.md; announce any inline fallback instead of silently losing scale or audit behavior.
4. **Disk is truth.** Never trust your in-memory belief about what's done. Check disk. See [[workspace-discipline]].
5. **When stuck or hitting a judgment call, write it to PLAN.md's Log section and stop.** Ask the user. Don't barrel through ambiguity.
6. **After a phase, update PLAN.md — and distill what the phase taught you.** Mark done, log decisions, surface blockers, write lessons to `.john/lessons/` (see [[skill-evolution]]), then loop. See [[ralph-loop]] and [[plan-md-evolution]].

## The endurance goal

The user can set a long-running goal for the session via `/john:endurance <goal>` in Claude Code or the `endurance-goal` skill in Codex. That goal is stored in `.john/workspace.json`; provider hooks can inject it at session start when enabled. If an endurance goal is set, treat it as the endurance race you're running — every phase advances the finish line a little closer. If none is set, the project's intent (top of PLAN.md) plays that role.

Set the goal with `/john:endurance <goal>` in Claude Code, or with `endurance-goal` in Codex. Inspect or clear it the same way.

## What you should NOT do

- Don't reinvent phases the user already approved in PLAN.md. The plan is the plan.
- Don't put hundreds of knowledge entries into your own context. Fan out.
- Don't write canonical state from a subagent directly — use the event log. See [[event-log-and-reducer]].
- Don't skip a skill's reference implementation and write your own from scratch — a skill's `references/` hold verified patterns and the pitfalls earlier runs already hit, so they're methodology ground truth the way the filesystem is state ground truth (see [[workspace-discipline]]). The "familiar" tasks — text highlighting, an API call, a scroll position — are exactly where skipping the reference bites; open it and adapt it. If it genuinely doesn't fit (different stack, different requirement), note why in PLAN.md's Log rather than silently diverging.
- Don't expose internal scaffolding — schema keys, skill names, raw JSON, chunk/chapter IDs, file paths, or the source language's machine-words — in the **produced app's public UI**. Those are build-time internals; the end-user sees the knowledge, not the plumbing. See the internal-leak guard in [[code-quality-guardrails]].
- Don't assume the user wants you to advance autonomously without checkpoints. Pause at phase boundaries unless they've said "run to completion."
- Don't reference any files outside `<project>/` and the active John plugin root. In Claude Code the plugin root may be `${CLAUDE_PLUGIN_ROOT}`; in Codex, resolve it from the loaded skill path or the source checkout.
- Don't write a separate `spec.md` for handoff between halves. PLAN.md is the durable contract across the knowledge and app phases in one session — no second contract needed. If you encounter a `spec.md` in a project, it's vestigial — incorporate its content into PLAN.md and stop reading it.

## Cross-references

- [[ralph-loop]] — the iterative plan-advancement pattern this session runs on
- [[plan-md-authoring]] — how to author a PLAN.md at project start
- [[plan-md-evolution]] — how to keep PLAN.md current as work progresses
- [[phase-design]] — how to decide what phases this project needs
- [[subagent-dispatch]] — when and how to spawn subagents
- [[vertical-workflows]] — Claude Code dynamic workflows for large fan-outs
- [[codex-vertical-workflows]] — Codex native waves and durable run ledger
- [[event-log-and-reducer]] — the parallel-subagent coordination pattern
- [[context-management]] — surviving multi-day sessions
- [[workspace-discipline]] — disk-is-truth, idempotent operations, checkpoint hygiene

If a skill name in this list doesn't ring a bell, read its SKILL.md. They're all here in this plugin under the active plugin root's `skills/` directory.
