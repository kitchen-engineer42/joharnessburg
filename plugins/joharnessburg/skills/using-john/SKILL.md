---
name: using-john
description: Top-level orientation for John (joharnessburg). Read this skill at the start of every John session and re-read it after every context compaction. Use it whenever the user mentions John, joharnessburg, ralph-loop, knowledge phases, app phases (or their legacy nicknames 2skills/2app), knowledge engineering, or asks you to do knowledge-dense app building. It tells you what John is, the shape of the user's working state, where to look, and what to do at each phase of work — without it, you'll likely under-trigger the other John skills.
---

# using-john

You are running in a Claude Code session where the **joharnessburg** plugin is loaded. The user has installed John because they want you to do **knowledge-dense app building** — take unstructured input (a book, a regulation, a doc set, mixed media) and produce a working app whose every feature traces back to extracted knowledge. John is a harness; you are the agent it harnesses.

This skill is your orientation. Read it once at the start of any John session, and re-read after each context compaction.

## What John actually is

A thin layer of skills, hooks, and a small toolkit on top of Claude Code. It does not replace your reasoning; it shapes how you organize the work so a knowledge-heavy project doesn't fall apart.

The shape John imposes is a **two-axis matrix**:

- **Horizontal axis** (phases): the work moves left-to-right through a small number of phases, one at a time. The **knowledge phases** (knowledge engineering) on the left half; the **app phases** (app building) on the right. You advance one phase before starting the next.
- **Vertical axis** (parallel knowledge entries): within most phases there are many similar units of work — hundreds of chunks to extract, dozens of skills to author, etc. You fan these out to subagents in parallel, not handle them serially in your own context.

Older projects and team shorthand may call the two halves by their legacy nicknames *2skills* and *2app* — same things. Same session, same memory, one PLAN.md spanning both halves.

**Produced apps run standalone by default** — locally or on any host the user owns, configured through `.env`, with no external auth/billing/telemetry platform assumed. Templates may add platform integration; vanilla John never requires it.

## The user's working state — where to look

Everything John writes lives in the **user's project directory** (the current working directory when this session was started). You write here, not into John's plugin install location.

- `<project>/PLAN.md` — the durable plan. Read this first. Has phases, subagent assignments, the app-type definition section, open decisions, an append-only log. It is the source of truth across context compactions.
- `<project>/CLAUDE.md` — project memory. If absent, John's `/john:init` creates a starter; if present, read it for project-specific conventions.
- `<project>/.john/` — working state. Hidden, ephemeral-ish. Contains `workspace.json` (active template + current phase), `input/` (user materials), `parsed/`, `chunks/`, `knowledge/`, `events/` (append-only logs), `checkpoints/`, `trace/` (offloaded large tool results).
- `<project>/.claude/skills/` — the *deliverable* skills produced by the knowledge phases (Claude Code's project-scoped auto-discovery path). The app phases consume these.

If none of this exists yet, John hasn't been initialized for this project. Suggest the user run `/john:init <path-to-input>` to scaffold.

## How to behave in a John session

Six rules. Internalize these — every other John skill builds on them.

1. **Read PLAN.md first, every iteration.** Cheap, keeps you honest. The plan is the contract. And when you start a phase, *invoke* the skills its "Skills to invoke" line names — actually load them; don't work from your memory of what they probably say.
2. **Advance one phase at a time.** Don't try to finish multiple phases in one pass; the matrix is sequential horizontally.
3. **Spawn subagents for vertical-axis parallel work.** Per-chunk extraction, per-entry rewrite, per-skill authoring — these are subagent jobs, not main-agent jobs. See [[subagent-dispatch]]. When a fan-out is large and uniform (dozens-to-thousands of units) and the session is workflow-configured, run it as a dynamic workflow instead of hand-dispatching — see [[vertical-workflows]]. **Check workflow availability before the first fan-out phase**: misconfigured → stop and tell the user the README's config recipe; feature-absent → announced inline fallback (same events, same reducer); endurance goal set → assume configured and proceed without pausing. Record the engine choice in PLAN.md.
4. **Disk is truth.** Never trust your in-memory belief about what's done. Check disk. See [[workspace-discipline]].
5. **When stuck or hitting a judgment call, write it to PLAN.md's Log section and stop.** Ask the user. Don't barrel through ambiguity.
6. **After a phase, update PLAN.md.** Mark done, log decisions, surface blockers, then loop. See [[ralph-loop]] and [[plan-md-evolution]].

## The endurance goal

The user can set a long-running goal for the session via `/john:endurance <goal>`. That goal is pinned to the system prompt and survives context compaction. If an endurance goal is set, treat it as the endurance race you're running — every phase advances the finish line a little closer. If none is set, the project's intent (top of PLAN.md) plays that role.

Set the goal with `/john:endurance <goal>`; inspect or clear via `/john:endurance` (no args) or `/john:endurance --clear`.

## What you should NOT do

- Don't reinvent phases the user already approved in PLAN.md. The plan is the plan.
- Don't put hundreds of knowledge entries into your own context. Fan out.
- Don't write canonical state from a subagent directly — use the event log. See [[event-log-and-reducer]].
- Don't assume the user wants you to advance autonomously without checkpoints. Pause at phase boundaries unless they've said "run to completion."
- Don't reference any files outside `<project>/` and the plugin's `${CLAUDE_PLUGIN_ROOT}/` — those are the only two places that exist for you.
- Don't write a separate `spec.md` for handoff between halves. PLAN.md is the durable contract across the knowledge and app phases in one session — no second contract needed. If you encounter a `spec.md` in a project, it's vestigial — incorporate its content into PLAN.md and stop reading it.

## Cross-references

- [[ralph-loop]] — the iterative plan-advancement pattern this session runs on
- [[plan-md-authoring]] — how to author a PLAN.md at project start
- [[plan-md-evolution]] — how to keep PLAN.md current as work progresses
- [[phase-design]] — how to decide what phases this project needs
- [[subagent-dispatch]] — when and how to spawn subagents
- [[vertical-workflows]] — running a large fan-out phase as a dynamic workflow
- [[event-log-and-reducer]] — the parallel-subagent coordination pattern
- [[context-management]] — surviving multi-day sessions
- [[workspace-discipline]] — disk-is-truth, idempotent operations, checkpoint hygiene

If a skill name in this list doesn't ring a bell, read its SKILL.md. They're all here in this plugin under `${CLAUDE_PLUGIN_ROOT}/skills/`.
