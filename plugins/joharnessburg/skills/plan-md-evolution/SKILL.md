---
name: plan-md-evolution
description: Keep PLAN.md current as work proceeds — subdivide a phase that turned out bigger, merge phases whose work is coupled, drop a phase whose intent no longer applies, insert one you didn't anticipate, mark TBD phases as concrete once decisions land, manage the append-only Log + Open Decisions + Subagent matrix. Use this skill whenever a phase advances, when the corpus surprises you, when the user changes their mind, when [[ralph-loop]] step 5 ("update PLAN.md") fires — this is what runs at that step. PLAN.md without evolution drifts; this skill keeps it honest.
metadata:
  triggers:
    - update PLAN.md
    - revise the plan
    - subdivide a phase
    - merge phases
    - drop a phase
    - insert a phase
    - mark phase done
    - log a decision
    - plan evolution
    - keep plan current
---

# plan-md-evolution

[[plan-md-authoring]] bootstraps PLAN.md at project start. This skill takes over for the entire rest of the project lifecycle — every phase advance, every decision, every blocker, every iteration. PLAN.md is the durable contract; evolution is what keeps it durable.

This skill fires every time [[ralph-loop]] step 5 runs ("update PLAN.md after each phase"). It's not optional — drift between PLAN.md and disk truth is what KC's hard-tracking principle was designed to prevent (KC: a sibling verification harness). Disk is truth; PLAN.md is the human-readable summary of the truth.

**Soft enforcement.** The six patterns below are John's defaults — suggestions grounded in real project experience. If a template ships its own evolution patterns (different Log format, different renumbering convention, different Open-Decisions schema), follow that instead. The load-bearing principles are: stay auditable (disk is truth, append-only Log), don't silently corrupt PLAN.md, and surface blockers to the user. The specific forms are flexible.

**Relationship to [[phase-design]].** Phase-design teaches the design judgment ("when is iteration the right move? what makes a good phase?"); this skill teaches the maintenance mechanics ("how to subdivide in PLAN.md, what to log, how to renumber"). When you're deciding *whether* to subdivide, consult phase-design. When you're doing the actual subdivide, this skill drives.

## The maintenance jobs

Six recurring patterns. Use the right one for the situation:

1. **Mark a phase done.** When a phase's done criteria are met (verified via [[workspace-discipline]] disk checks), update its section header and append to the Log.
2. **Subdivide a phase.** When you discover mid-flight that a phase has too much in it ("extract knowledge from corpus" turns out to need both summary-extraction and structured-extraction as separate sub-phases). Append a Log entry, split the phase into N sub-phases, keep the original's Done criteria as the union of the children's.
3. **Merge phases.** When two phases turn out to be tightly coupled and can't run independently. Less common than subdivide; collapses two sections into one.
4. **Drop a phase.** When a phase's intent no longer applies (the active template's "research images" phase isn't needed because this corpus is text-only). Mark it dropped in the Log with rationale; keep the section as a struck-through stub for traceability.
5. **Insert a phase.** When you discover a phase you didn't anticipate (the corpus turned out to need a coreference-resolution step). Append a Log entry; insert the new phase at the right position; renumber subsequent ones.
6. **Promote a TBD to concrete.** When you wrote "Phase 5: TBD — decide after Phase 4 ships" and now Phase 4 is done. Settle Phase 5's intent + skills + artifacts + done criteria with the user.

For each of these, the Log records *what changed and why*. Append-only — never edit a prior Log entry. See `references/log-and-decisions-discipline.md`.

## Open Decisions handling

PLAN.md's Open Decisions section is where you write questions you need the user to answer. The discipline:

- **Respect the intent question budget.** Product-preference questions get at most one batch of at most four ordinary-user questions for the whole project. If that batch has already been used, record assumptions or blockers instead of appending another product question.
- **Append only real blockers or unused-budget product questions.** Don't sit on uncertainty, but don't turn every uncertainty into a user interruption.
- **Clear questions when resolved.** When the user answers, append the resolution to the Log + remove the question from Open Decisions. Or move-to-resolved; some users like a struck-through history.
- **One Open Decision can block the loop.** When a non-product blocker or unused-budget product question blocks phase progress, ralph-loop stops there and surfaces it. After the product-question budget is spent, make the best defensible product assumption unless the project truly cannot proceed.

See `references/log-and-decisions-discipline.md` for the formatting + flow.

## Subagent matrix updates

When a phase fans out to subagents (per [[subagent-dispatch]]), the matrix grows:

- Before fan-out: add a row per work unit with status `pending`.
- During: update status to `in_flight` for active units. (Optional; the event log already records this. Update only if the user wants live visibility.)
- After reducer: mark each unit `done` and link to its events / checkpoint.

The matrix is informational, not load-bearing — the event log + checkpoint files are truth. The matrix is for humans skimming PLAN.md.

## Interaction with ralph-loop

The handoff: [[ralph-loop]] step 5 is "update PLAN.md after each phase." That step is this skill in action. The loop's other steps (read PLAN.md, identify next phase, do the work, etc.) don't trigger evolution; only step 5 does.

A common mistake: trying to do evolution mid-phase (e.g., editing the phase definition while the phase is still running). Don't. Wait until the phase boundary, then evolve. Mid-phase changes risk leaving the canonical state inconsistent with the new phase intent.

If a mid-phase observation NEEDS to be captured (e.g., a subagent surfaces that the schema is wrong and you can't continue extraction), use the **Open Decisions** section only if it is a real blocker or the one product-question batch is still unused. Otherwise record it as an assumption or Log entry and continue with the best defensible default.

## Anti-patterns

- **Rewriting prior Log entries.** Log is append-only. If a decision changed, append a new entry that supersedes the old one.
- **Silently restructuring phases.** Always Log the change. Future-you (after a context compaction or fresh session) reads the Log to reconstruct *why* the plan looks the way it does.
- **Editing a phase's done criteria after the phase started.** If the criteria need to change, append a Log entry explaining why, then either (a) restart the phase or (b) accept the current state as meeting the revised criteria. Don't quietly redefine "done."
- **Letting Open Decisions accumulate without surfacing them.** If you've added a question, the user needs to see it. Surface in your next response.

## When to NOT use this skill

- **Pre-PLAN.md** — use [[plan-md-authoring]] instead. Evolution requires something to evolve.
- **Trivial edits** (fixing a typo). Just fix it; no Log entry needed for cosmetic changes.
- **User-driven major restructures** (the user wants to completely rewrite the plan). At that point, archive the old PLAN.md (move to `<project>/.john/checkpoints/plan/PLAN-pre-restructure-<ts>.md` per [[workspace-discipline]] rule 3) and re-author via [[plan-md-authoring]].

## Cross-references

- [[plan-md-authoring]] — bootstrap; this skill's predecessor in the PLAN.md lifecycle
- [[ralph-loop]] — step 5 is where this skill fires every iteration
- [[phase-design]] — what makes a phase good (apply when subdividing or inserting)
- [[workspace-discipline]] — disk-is-truth before marking phases done; checkpoint before restructures
- [[subagent-dispatch]] — populates the Subagent matrix section
- [[app-design-thinking]] — when runtime/pipeline iterates mid-project, this skill captures it
- See `references/` for: phase-iteration patterns with examples, Log/Decisions discipline, ralph-loop interaction detail
