# log-and-decisions-discipline — what goes where

PLAN.md has three sections that record state-over-time: **Log** (what happened), **Open Decisions** (what's blocked), **Subagent matrix** (where work is). They serve different purposes; don't conflate.

## Log

**Purpose**: append-only history of decisions, phase advances, blockers, restructures. The human-readable diff of the plan over time.

**Format**: most recent first. Dated entries, one-liner or short paragraph each.

```markdown
## Log

- 2026-05-23: Phase 4 subdivided into 4a (summary extraction) and 4b (detail extraction). Rationale: different prompts, different verification.
- 2026-05-23: Phase 3 done. 187 entries extracted across 42 chunks, dedup folded to 173.
- 2026-05-22: Schema iterated to add 'severity' field. Rationale: runtime needs to color-code by severity.
- 2026-05-22: /john:init scaffolded the workspace.
```

**Rules**:
- Append-only. Never edit a prior entry.
- One entry per discrete change. Don't batch.
- Include enough context that future-you can understand the entry without re-reading the whole plan.
- A correction is a new entry: "2026-05-23: Correction — yesterday's note about X was wrong; the actual decision was Y."

## Open Decisions

**Purpose**: questions you need the user to answer. Visible so they can't be forgotten.

**Format**: numbered list, each a clear question.

```markdown
## Open Decisions

1. Should the runtime support both Chinese and English UI, or English only? (affects schema's title fields and packaging)
2. Is the slide deck single-html (offline-shareable) or multi-html (linkable)? (affects packaging strategy)
```

**Rules**:
- **Append questions immediately when they arise.** Don't sit on uncertainty; surface it where the user can see.
- **Clear questions when resolved.** Move the resolution to the Log, remove from Open Decisions. (Or strike through if you prefer keeping history visible — team taste.)
- **Block phase progress on unresolved decisions** when the question affects the current phase. Pause the loop, surface in the next user-facing response.

## Subagent matrix

**Purpose**: live status of vertical-axis fan-out within a phase. Informational; the event log + checkpoint files are truth.

**Format**: per-phase subsection or table.

```markdown
## Subagent matrix

### Phase 3: extract

| Work unit | Status | Events | Entries |
|---|---|---|---|
| chunk_001 | done | 3 | 5 |
| chunk_002 | done | 3 | 7 |
| chunk_003 | in_flight | 1 | — |
| chunk_004 | pending | 0 | — |
...
```

**Rules**:
- Update *between* fan-out waves, not during. Live updates are nice-to-have; not load-bearing.
- The event log is canonical. If the matrix and events disagree, events win.
- After the phase is done, the matrix can be collapsed or archived (move to `.john/checkpoints/plan/subagent-matrix-phase-3.md`).

## What does NOT belong in any of these

- **Reasoning chains** ("I thought X but then Y so therefore Z"). Keep entries factual; rationale is OK in one line but not multi-paragraph reasoning. That belongs in the body of a Log entry or in a separate scratch doc.
- **Verbose error traces**. Offload to `<project>/.john/trace/` per [[context-management]] and reference by path.
- **User conversation transcripts**. The PLAN.md captures *decisions*, not *discussion*. The conversation lives in Claude Code's chat history.

## When the Log gets long

After a long project (50+ phase iterations), the Log can be hundreds of lines. Options:

- **Leave it.** PLAN.md is markdown; nothing breaks at length. A long Log is project history.
- **Archive periodically.** When PLAN.md is over ~1500 lines, move the oldest Log entries to `<project>/.john/checkpoints/plan/log-archive-<month>.md` and leave a pointer in the main PLAN.md Log: `(Earlier entries: see log-archive-2026-04.md.)`.

The archive must be append-only too. Don't edit archived entries.

## Source

Discipline distilled from KC's `events.jsonl` pattern (KC: a sibling verification harness) + an append-only, most-recent-first dev journal practice + Trellis's per-developer journals.
