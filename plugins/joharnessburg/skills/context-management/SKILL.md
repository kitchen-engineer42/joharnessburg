---
name: context-management
description: How to survive long-running John sessions where the work spans hours or days. Pin the endurance goal, offload large tool results, use sub-agent firewalls, compact at phase boundaries, and accept graceful degradation to fresh sessions.
metadata:
  triggers:
    - context window
    - compaction
    - endurance goal
    - long session
    - context budget
---

# context-management

John sessions are designed to run long. A knowledge-heavy project might span 4-8 hours of focused work. The active coding agent's context window is large but not infinite. This skill is the five-part discipline that keeps you coherent across long runs and degrades you gracefully when context exhausts.

## The five techniques

You should use all five. They compound.

### 1. Endurance goal pinned in system prompt

If the user has run `/john:endurance <goal>`, that goal is in `<project>/.john/workspace.json` and the SessionStart hook will inject it into your system prompt at the top of every session (and every post-compaction state). It survives compaction because the system prompt isn't windowed.

In Claude Code, set the goal with `/john:endurance <goal>` and inspect or clear it with `/john:endurance` or `/john:endurance --clear`. In Codex, invoke `endurance-goal` with the same intent.

What this gives you: even after compaction wipes most of conversation history, the endurance-race direction is still in front of you. You know what you're working toward.

If no endurance goal is set, the project's intent from PLAN.md's top section serves the same role — read it as step 1 of every loop iteration.

An endurance goal also changes one default: **assume the session is workflow-configured** (`/effort ultracode`, dynamic workflows available) and don't pause a long run to re-confirm config — see [[vertical-workflows]]. The user who set an endurance goal prepared the session; interrupting hours of autonomy to ask about a setting defeats the mode. If the Workflow tool is genuinely absent, fall back to inline dispatch and log it in PLAN.md instead of stopping.

**Wording shapes behavior.** Frame the goal as scope **+** discipline, not scope alone. A pure-scope goal — "complete the entire plan," "finish everything" — quietly biases toward checking phases off fast, and an "and verify carefully" tacked onto the same sentence gets read as decoration. Pair the scope with the bar it must clear: "complete phases 1-3, every done-criterion met before advancing" or "implement strictly from the skill references, quality over speed." Two genuinely-met phases beat five checked-off shells; the goal is a compass for direction, not a deadline that licenses cutting corners. (If you're *setting* the goal for the user, prefer this framing; if it's already set as pure scope, read it that way — as direction, not as permission to rush.)

### 2. Filesystem offload for large tool results

When a tool returns a result that feels heavy (multi-KB parsed data, verbose error trace, raw PDF text), don't keep it in conversation context. Write it to `<project>/.john/trace/<id>.txt` and reference the path; leave a head+tail digest in your context. John's PostToolUse hook auto-wires this for results past a size threshold; do it manually for anything the hook doesn't catch but that still feels large.

When you need the full content again, Read the trace file. Until then, the digest is enough for most decision-making, and your context stays clean.

You can also do this manually: if you produce a long output mid-session, write it to `<project>/.john/trace/` and refer to the path instead of inlining it.

### 3. Sub-agent firewalls

Subagents are their own context windows. When you dispatch a subagent to do a chunk extraction, the subagent reads the chunk (could be 4KB), produces extraction output (could be 8KB), emits events (could be 16KB) — and you, the main agent, only see the subagent's final digest (one or two lines).

This is the strongest single context-saving lever you have. See [[subagent-dispatch]]. Use subagents aggressively for work that produces non-trivial intermediate state.

### 4. Phase boundary as explicit compaction point

The natural rhythm: do a phase, advance PLAN.md, stop or compact. Don't try to do three phases in one context-continuous burst.

Why phase boundaries:
- Canonical state is on disk (`<project>/.john/checkpoints/<phase>/state.json`).
- PLAN.md reflects the new state.
- Any pending decisions are written to PLAN.md's Open Decisions section.

So if context compacts at a phase boundary, the next iteration's first step (read PLAN.md, read latest checkpoint) recovers cleanly. The state is on disk; conversation memory is replaceable.

Don't compact in the middle of a phase if you can avoid it — that's where mid-flight work gets lost.

### 5. Read PLAN.md every iteration

This is point one of [[ralph-loop]] and it's also a context-management technique. Re-reading PLAN.md at the start of every iteration:

- Refreshes your understanding from the durable source.
- Catches user edits between iterations.
- Is cheap (markdown file, maybe 2-5KB).
- Means you don't need to remember the plan — you only need to remember where to look.

## Graceful degradation: fresh sessions

If your context fills past ~80% and a compaction won't help (e.g., a single tool result was huge), the user can:

- In Claude Code, use `/clear`; in either runtime, start a fresh John-equipped session in the same workspace.
- Or open a new terminal tab and start fresh.

The next session, with John plugin loaded:
- SessionStart hook re-injects the endurance goal.
- using-john skill description is pinned.
- The next iteration's "read PLAN.md" step picks up exactly where things left off.

This is the snarktank/ralph fresh-instance pattern, available to John as a fallback when single-session memory fails. Don't apologize for it; it's a feature.

## What survives compaction (and what doesn't)

**Survives:**
- System prompt (endurance goal, skill descriptions)
- Disk state (`PLAN.md`, `.john/`, `.claude/skills/`, `.agents/skills/`)
- The SessionStart hook's re-injected context

**Does NOT survive:**
- Conversation history before the compaction point
- Tool results from before compaction (unless offloaded)
- In-memory beliefs about what was done

After compaction, your first move is always: read PLAN.md + check disk. Never start work from a half-remembered understanding of where you were.

## What if you're running out of context mid-phase

Options, in order of preference:

1. **Push the rest of the phase to subagents.** If the remaining work is per-entry, fan out to subagents and let their digests come back. Their work doesn't cost your context.
2. **Write what you have to disk and pause.** Write the partial state to a checkpoint, write a Log entry in PLAN.md ("Phase X is N% complete; next iteration resumes from event log up to subagent_id Y"), and stop. Next iteration picks up.
3. **Ask the user to compact** with the active runtime's compaction control (`/compact` in Claude Code). They get to decide when.
4. **Last resort: ask the user to open a fresh session.** With PLAN.md and checkpoints on disk, this is recoverable, just costly.

The worst option is to push through and have your context fill silently — your reasoning degrades before you notice, and the work product reflects it.

## Context budget hygiene

Some habits:

- Don't paste the whole PLAN.md into the conversation; reference it by path and Read what you need.
- Don't quote whole files at the user; quote the relevant lines.
- Don't simulate subagents in your own context with `Bash` + a long prompt — use the runtime's subagent mechanism and request a digest.
- Don't keep stale tool results in context — they linger forever otherwise.

## Cross-references

- [[ralph-loop]] — the loop pattern that uses phase boundaries as compaction points
- [[subagent-dispatch]] — the strongest context-saving lever
- [[workspace-discipline]] — disk-is-truth means context loss is recoverable
- [[event-log-and-reducer]] — checkpoint state lives on disk
- [[plan-md-evolution]] — keeping PLAN.md fresh so re-reads are useful (fires at ralph-loop step 5)
