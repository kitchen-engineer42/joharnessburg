---
name: ralph-loop
description: The iterative plan-driven advancement pattern John runs on. Read PLAN.md, advance one phase, update PLAN.md, repeat. Adapted from snarktank/ralph for John's longer-horizon, multi-half, subagent-fanout scope.
metadata:
  triggers:
    - advance the plan
    - next phase
    - next iteration
    - continue the loop
    - ralph loop
    - resume work
    - phase boundary
    - mark phase done
    - what's the next unit of work
    - one unit of work
---

# ralph-loop

The loop is simple. The discipline is the work.

Every iteration of substantive work in a John session takes the same shape:

1. **Read `<project>/PLAN.md`.** Re-read. Don't trust your memory of it from earlier in the session — context drifts, plans get edited by the user between iterations, and compaction may have happened.
2. **Find the next incomplete unit of work.** Usually the next phase whose "Done criteria" aren't met. Within a phase, the next work unit in its subagent matrix.
3. **Plan exactly that unit.** Not the whole project. Not the next two phases. The single next unit.
4. **Do the work.** Inline for things that fit one context window. Via subagent for things that don't or that benefit from parallelism — see [[subagent-dispatch]].
5. **Update PLAN.md.** Mark the unit done. Append decisions to the Log section. If something blocked you, write it as an open question for the user.
6. **Stop or loop.** Stop at phase boundaries (clean compaction points, low risk of midway corruption). Loop within a phase if there's clearly more work and you're below ~50% context utilization.

That's it. The rest of this skill is failure modes and nuance.

**Templates may override this pattern.** The active template can define its own iteration model — substitute different phases, run a different loop shape, override what counts as "one unit." If a template ships its own loop instructions in `claude_addon.md` or a sibling skill, follow that instead. This skill is John's default; templates shape the variation. Always check PLAN.md and CLAUDE.md for template-specific overrides before assuming the default applies.

## Why this loop

Three reasons it works for John:

- **PLAN.md is the durable contract.** When context compacts, when the session restarts, when the user opens a fresh Claude Code session to continue tomorrow — PLAN.md is what carries state forward. The loop's first step (re-read) makes the contract real.
- **One unit per iteration prevents drift.** Trying to plan-then-execute three things at once is where agents lose coherence. One unit, finish it, write it down, move on.
- **The Log section converts "I got stuck" from session-ending failure into a checkpoint.** Writing the blocker out is more valuable than burning context retrying.

## When NOT to use this pattern

- **Trivial single-tool tasks.** If the user asks "rename this variable," don't read PLAN.md. The loop is for project work, not editor-level operations.
- **Pure conversation / clarification.** When the user is exploring an idea with you, you're not in the loop yet. Move to the loop when work begins.
- **The plan doesn't exist yet.** First write it ([[plan-md-authoring]]). The loop runs the plan; you can't loop without one.

## Subagent fan-out inside an iteration

Many phases (especially in the 2skills half) have hundreds of similar work units — one per chunk, one per knowledge entry. Don't loop on these serially. Within step 3-4 of the main loop:

- Decide the work units (e.g., the list of chunks).
- Fan out to subagents — one per unit, or batched if units are tiny. See [[subagent-dispatch]].
- Subagents emit events to `<project>/.john/events/<phase>/...` — see [[event-log-and-reducer]].
- Wait for fan-out to complete. Run the reducer. Inspect the canonical state.
- Then update PLAN.md to reflect the phase result.

This is the horizontal/vertical matrix in practice. Main loop is horizontal; per-phase fan-out is vertical.

### A fan-out phase is one workflow run

When the fan-out is large and uniform (dozens-to-thousands of units), the right engine for step 3-4 is a **dynamic workflow**: a script you author that fans the units out off your context, adversarially cross-checks the workers, and returns a compact summary while the per-entry events land on disk. One **fan-out phase = one workflow run**; the **phase boundary is the sign-off seam between runs** (workflows take no user input mid-run, so review, PLAN.md updates, and user questions happen *between* runs, never inside). The loop becomes:

> launch the phase workflow → wait → run `reduce_events.py` → read the checkpoint → update PLAN.md → advance.

The loop is **engine-agnostic** below this line: whether the units were dispatched by a workflow or inline, you still run the reducer and read the checkpoint — that's truth, not the workflow's return value. If the session isn't workflow-capable, dispatch inline; everything else is identical. The mechanics and the John-shaped stages are in [[vertical-workflows]].

## Surviving context compaction

When Claude Code compacts your context mid-session:

- The endurance goal (pinned to system prompt via the SessionStart hook) survives.
- The using-john skill description survives.
- PLAN.md doesn't move — it's on disk. Re-read it as step 1 of the next iteration.
- Open questions in PLAN.md's Log section survive (they're in the file).
- In-memory beliefs about partial work do NOT survive. Check disk before assuming.

See [[context-management]] for the full pattern.

## Surviving a fresh Claude Code session

Same recovery: re-read PLAN.md, check disk for what's done, advance from there. The user can `/clear` or close and reopen the session at any phase boundary. That's a feature, not a bug — John gracefully degrades to ralph-style fresh sessions when context fills.

## When to stop and ask the user

The PLAN.md "Open decisions" section is for you to write questions in. Use it when:

- A schema choice has multiple defensible options and the user has taste preferences.
- A phase's done criteria are ambiguous from the plan as written.
- A subagent fan-out produced contradictory results and you can't determine ground truth from the corpus.
- You've reached the end of an explicitly-approved scope.

Don't use it for: things you can resolve from existing context, judgment calls the user has already signaled they trust you on, or operational questions that have an obvious answer.

## What ralph-loop is NOT

This is not snarktank/ralph reimplemented. We adapted the pattern. Differences (full justification in the workspace's `docs/ralph_in_john_vs_original.md`):

- Original ralph spawns a fresh AI instance per iteration; John uses one long-running session with memory, falling back to fresh-session if context exhausts.
- Original ralph uses a structured `prd.json` task list; John uses markdown `PLAN.md`.
- Original ralph treats a story as one iteration; John treats a phase as one iteration (with subagent fan-out inside).
- Original ralph runs autonomously; John pauses at phase boundaries and at open-decision points.

If you find a behavior in another `ralph` reference that contradicts this skill, this skill wins for John.

## Cross-references

- [[plan-md-authoring]] — write the plan before you can loop on it
- [[plan-md-evolution]] — keep the plan current as you loop; fires at step 5 of every iteration
- [[phase-design]] — what makes a good phase boundary
- [[subagent-dispatch]] — when and how to fan out within an iteration
- [[vertical-workflows]] — running a fan-out phase as one workflow; the sign-off seam between runs
- [[event-log-and-reducer]] — coordinate subagent fan-out
- [[context-management]] — surviving the long haul
- [[workspace-discipline]] — disk-is-truth before you advance
