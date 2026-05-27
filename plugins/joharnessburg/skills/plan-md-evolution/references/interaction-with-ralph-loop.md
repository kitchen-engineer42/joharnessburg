# interaction-with-ralph-loop — when this skill fires

[[ralph-loop]] documents the six-step iteration pattern. This skill is the activator at step 5 ("update PLAN.md"). Knowing when it fires (and when it doesn't) helps you not duplicate or miss work.

## Ralph-loop's six steps, annotated

1. **Read PLAN.md.** plan-md-evolution doesn't fire here — you're just consuming the contract.
2. **Find the next incomplete unit.** Plan-md-evolution might fire if the next unit is "promote a TBD" or "decide on the dropped phase's replacement" — those are evolution actions. Otherwise, you're identifying work, not changing the plan.
3. **Plan the unit.** Doesn't fire. You're working out the immediate scope, not updating the durable plan.
4. **Do the work.** Doesn't fire. Subagent fan-out, file emissions, tool calls — the matrix can be updated mid-flight if you want live visibility, but evolution proper waits.
5. **Update PLAN.md.** **This is where plan-md-evolution fires.** Mark phase done, append to Log, manage Open Decisions, update Subagent matrix.
6. **Stop or loop.** Doesn't fire — you're deciding whether to compact or continue, not changing the plan.

## What step 5 must do

Every step-5 invocation:

- **Verify done criteria on disk** per [[workspace-discipline]]. Don't trust your in-memory belief; check.
- **Mark the phase done** in PLAN.md (update section header, e.g., `### Phase 3: extract ✓ done 2026-05-23`).
- **Append to Log**: phase done, counts/artifacts produced, any decisions made during the phase.
- **Clear resolved Open Decisions** (move to Log).
- **Update Subagent matrix** for the phase that just finished.
- **Iterate phase structure** if needed: subdivide if the phase was bigger than expected, drop a future phase if its intent no longer applies, etc.
- **Surface any new Open Decisions** to the user in your response (so they don't get buried).

## When step 5 doesn't fire

- A user-initiated "fix this typo" doesn't go through the loop. No evolution.
- Pre-PLAN.md work (initial conversation, scaffolding) is [[plan-md-authoring]]'s territory. No evolution.
- Trivial in-place edits (correcting a path, fixing a wrong skill name reference) — just edit; no Log entry needed.

## What if step 5 needs MORE than one phase's worth of updates

Sometimes a single phase reveals multiple plan-level changes (e.g., the phase produced findings that imply two future phases need to be redefined). Append separate Log entries for each change; don't bundle them into one ambiguous entry. Future-you reads each entry as an atomic decision.

## Mid-phase plan updates

Sometimes you can't wait for the phase boundary — e.g., the user changes their mind mid-flight about the schema, and you need to capture that. Two clean options:

1. **Pause the phase** at the next safe checkpoint (typically: end of the current subagent wave). Then run step 5: capture the user's new direction in the Log, update the schema-design or Open Decisions, resume the phase under the new contract.
2. **Capture the user's direction in Open Decisions** without pausing the phase. The current phase finishes; at its step 5, the new direction triggers a phase subdivide or restructure.

Option 1 is cleaner; option 2 is faster. Choose based on whether the in-flight work would be invalidated by the new direction.

## Compaction and step 5

If [[context-management]] kicks in mid-loop and the session compacts, step 5 from the prior iteration might be incomplete (you marked the phase done but didn't append the Log yet). Recovery on next iteration:

- Read PLAN.md (step 1). Notice the phase is marked done but the Log doesn't reflect it.
- Verify the phase IS done on disk per [[workspace-discipline]].
- Append the missing Log entry retroactively (note in the entry that it was reconstructed post-compaction).
- Then proceed to step 2.

Post-compaction reconstruction is rare but should be handled gracefully when it happens.

## Source

Pattern integration between ralph-loop's six steps (from [[ralph-loop]] + the snarktank/ralph design) and PLAN.md as a living document. The handoff between steps 4 and 5 is the most failure-prone part of the loop — easy to forget the update; easy to skip the disk verification. Treat step 5 as a discipline checkpoint, not a chore.
