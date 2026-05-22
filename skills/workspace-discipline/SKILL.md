---
name: workspace-discipline
description: Disk is truth. Never trust your in-memory belief about what's done; check disk. Idempotent operations, checkpoint before risky moves, append-only event logs, observable done criteria. The discipline that makes John recoverable across compaction, crashes, and fresh sessions.
metadata:
  triggers:
    - is it really done
    - check disk
    - verify state
    - workspace state
    - disk is truth
---

# workspace-discipline

Five rules. Internalize each. They're not optional, and they're not "if you have time" — they're the operating contract for working in a John session.

## Rule 1: Disk is truth

When you need to know if something is done, **check disk**. Do not trust:

- Your memory of what you did three messages ago.
- A subagent's report ("I extracted 47 entries").
- A tool result that came back successful 10 minutes ago.
- The Log section of PLAN.md alone (it might say "Phase 3 done" but the artifact directory could be empty).

Check disk means: use `ls`, `find`, `cat`, file existence checks. The phase done-criteria in PLAN.md are disk-verifiable for a reason. Verify them.

This rule is the single most important discipline in John. It is the cleanest learned lesson from kc_cli: agents will assert work is done that isn't, and the engine has to verify from filesystem. You ARE the engine here, so the verifying is on you.

## Rule 2: Idempotent operations

Every operation you take should be re-runnable. If you run it twice in a row, the second run should either:

- Produce the same disk state as the first run, OR
- Be a clean no-op (notices the work is already done and exits)

NOT: corrupt state, double-write, error out, or produce different output.

This matters because:

- Sessions get interrupted; the next session may re-run a phase.
- Subagents may be re-dispatched after partial failures.
- The reducer ([[event-log-and-reducer]]) runs many times during a phase.
- The user may `/clear` mid-flight; recovery should be straightforward.

How to be idempotent:

- **Read before write.** Check if the file/dir/entry exists before producing it. If it does, decide: skip, overwrite, or merge.
- **Use deterministic IDs.** A knowledge entry's ID should be derivable from its source (chunk + position), not random. Re-running extraction on the same chunk yields the same entry IDs.
- **Append-only logs.** Never edit an event file after writing it. Add a new one to supersede.
- **Compute, don't accumulate.** Canonical state is computed from events; don't accumulate it in place across runs.

## Rule 3: Checkpoint before risky moves

Before doing something destructive, irreversible, or hard-to-redo, leave a checkpoint on disk:

- About to rewrite the whole knowledge inventory based on a schema change? Write the current state to `<project>/.john/checkpoints/<phase>/pre-rewrite-<timestamp>.json` first.
- About to delete a directory of stale artifacts? Move it to `<project>/.john/checkpoints/<phase>/archived-<timestamp>/` instead — recovery is possible.
- About to overwrite PLAN.md with a major restructure? Save the prior version as `<project>/.john/checkpoints/plan/PLAN-<timestamp>.md`.

The PreCompact hook (M5) does this automatically before Claude Code compacts context. You should do it manually for the analogous moments in your work.

## Rule 4: Append-only event logs

Events ([[event-log-and-reducer]]) are append-only. Once written, an event file is immutable history. To "correct" an event, write a new event that supersedes it (e.g., `{event_type: "entry_replaced", supersedes: "abc-123", ...}`), and let the reducer fold the supersession.

Why immutable:

- Replay. You can re-run the reducer with any subset of events to see prior states.
- Audit. The full record of what every subagent did, in order.
- Recovery. If the reducer is buggy, you fix the reducer; you don't lose events.

If you find yourself wanting to edit an event file, you're probably trying to hide a mistake. Don't. Emit a corrective event instead.

## Rule 5: Observable done criteria

Every phase in PLAN.md has a "Done criteria" line. It must be observable on disk. Examples:

- ✓ "All chunks in `chunks_index.json` have a corresponding entry in `<project>/.john/checkpoints/extract/state.json` (verified by ID match)."
- ✓ "`<project>/.claude/skills/<skill-name>/SKILL.md` exists for every entry in the packaged set, and each has YAML frontmatter with `name` and `description`."
- ✓ "`<app-output>/<entry-point-file>` returns HTTP 200 when served via the test runner."

NOT:

- ✗ "The extraction looks good."
- ✗ "Most entries are covered."
- ✗ "The app works."

If the user wrote a vague done criterion in PLAN.md, push back. Get it specific before advancing.

To verify a done criterion: run the check (Bash `ls`, `wc -l`, `python -c '...'`, etc.), confirm the result, then mark the phase done in PLAN.md.

## What to check, mechanically

A short list you should be able to execute in any iteration:

```bash
# Where are we in the plan?
cat <project>/PLAN.md | head -50

# What's John's working state?
ls -la <project>/.john/

# What artifacts has this phase produced?
ls <project>/.john/checkpoints/<phase>/ 2>/dev/null

# What events came in?
ls <project>/.john/events/<phase>/<work-unit-type>/ | wc -l

# What's been packaged?
ls <project>/.claude/skills/ 2>/dev/null

# Recent activity (workspace git, if tracked)
cd <project> && git log --oneline -5 2>/dev/null
```

You don't need to run all of these every iteration. You DO need to run the relevant subset when verifying a done criterion or recovering from compaction.

## What this rules out

- Saying "Phase 3 is done" without checking the artifact directory.
- Trusting a subagent's "I extracted N entries" without counting the events.
- Marking PLAN.md complete based on tool results that may have errored silently.
- Editing event files to "fix" them.
- Mutating canonical state without going through events.
- Optimistic done-marking that the next iteration will catch as broken.

## When the user says "is it done?"

Check disk. Tell them what you observed. If the check passes the done criteria, tell them that. If it doesn't, tell them what's missing.

Never tell the user "yes, it's done" based on memory. Memory is wrong.

## Cross-references

- [[ralph-loop]] — runs disk checks at iteration boundaries
- [[event-log-and-reducer]] — append-only, idempotent reducer
- [[phase-design]] — done criteria are disk-verifiable by design
- [[context-management]] — disk-is-truth is why context loss is recoverable
- [[plan-md-evolution]] — PLAN.md updates require disk-state confirmation
